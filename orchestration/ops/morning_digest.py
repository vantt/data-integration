"""Morning Lark digest for ingestion health.

Runs at 08:00 Asia/Ho_Chi_Minh daily. Reads ingestion_health.duckdb,
composes one Lark card summarising 24h volume, 7-day median trend,
freshness, recon drift, consecutive zero-row streaks, and recommended
actions per source. Dry-run via DIGEST_DRY_RUN=1.

Architecture: @op inside a job (not an asset — no downstream data graph).
Card delivery failure is caught and logged — never fails the Dagster run.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Literal, Optional

import duckdb
from dagster import job, op

from orchestration.ops.ingestion_health import get_db_path
from orchestration.notifications.lark_client import send_lark_card

logger = logging.getLogger("orchestration.morning_digest")

# ---------------------------------------------------------------------------
# Known asset registry: (short_name, asset_key, recon_asset_key | None)
# ---------------------------------------------------------------------------
KNOWN_ASSETS: list[tuple[str, str, Optional[str]]] = [
    ("sapo_webhook",   "sapo/sapo_webhook_consumer_asset",   None),
    ("sapo_history",   "sapo/sapo_history_log_asset",        None),
    ("sapo_orders",    "sapo/sapo_orders_batch_asset",       "recon/sapo_orders_daily"),
    ("sapo_customers", "sapo/sapo_customers_batch_asset",    "recon/sapo_customers_daily"),
    ("sapo_products",  "sapo/sapo_products_batch_asset",     None),
    ("sapo_accounts",  "sapo/sapo_accounts_batch_asset",     None),
    ("shopee",         "shopee/shopee_income_file_drop_asset","recon/shopee_daily"),
    ("misa",           "misa_amis/misa_sales_file_drop_asset","recon/misa_daily"),
    ("sheet_targets",  "sheets/sheets_targets_asset",        None),
    ("sheet_spend",    "sheets/sheets_marketing_spend_asset", None),
]

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class DigestRow:
    short_name: str
    asset_key: str
    status: Literal["green", "yellow", "red", "gray"]
    rows_24h: Optional[int]
    median_7d: Optional[int]
    pct_vs_median: Optional[float]
    fresh_age_min: Optional[int]   # minutes since last success
    drift_pct: Optional[float]     # from recon, if applicable
    note: Optional[str]            # e.g. "never run", "recon failed"
    last_run_id: Optional[str] = None
    zero_streak: int = 0           # consecutive cursor-advanced-but-0-rows runs


@dataclass
class KpiData:
    """KPI closure revenue data (Phase 5)."""
    source_revenue: Optional[float]
    warehouse_revenue: Optional[float]
    drift_pct: Optional[float]
    date_key: Optional[int]
    status: Optional[str]  # success, partial, disabled


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

_SLA_HOURS = 12  # freshness SLA — no data > this → red


def classify(row: DigestRow) -> Literal["green", "yellow", "red", "gray"]:
    """Return color for a DigestRow. Gray = never run / no data.

    Drift is checked first even for never-run rows: if recon captured a large
    discrepancy, that is actionable regardless of whether we have direct run data.
    """
    # Recon drift overrides everything — even "never run" gray state
    if row.drift_pct is not None:
        abs_drift = abs(row.drift_pct)
        if abs_drift > 5.0:
            return "red"
        if abs_drift > 1.0:
            return "yellow"

    # After drift check: return gray for never-run / unreachable with no drift signal
    if row.note in ("never run", "health DB unreachable"):
        return "gray"

    # Freshness SLA
    if row.fresh_age_min is not None and row.fresh_age_min > _SLA_HOURS * 60:
        return "red"

    # Row-trend vs 7d median
    if row.median_7d and row.median_7d > 0 and row.rows_24h is not None:
        ratio = row.rows_24h / row.median_7d
        if ratio < 0.5:
            return "yellow"

    # Consecutive zero-row runs (cursor advanced but no data)
    if row.zero_streak >= 3:
        return "red"
    if row.zero_streak >= 2:
        return "yellow"

    # Most-recent run failed
    if row.note == "last run failed":
        return "red"

    return "green"


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------

_MAIN_QUERY = """
WITH recent AS (
    SELECT asset_key,
           MAX(run_started_at) FILTER (WHERE status = 'success') AS last_ok,
           MAX(run_started_at)                                    AS last_any,
           SUM(rows_written)   FILTER (WHERE run_started_at >= now() - INTERVAL 1 DAY) AS r_24h,
           LAST(status ORDER BY run_started_at) AS last_status,
           LAST(run_id ORDER BY run_started_at) AS last_run_id
    FROM ingestion_runs
    GROUP BY asset_key
),
daily AS (
    SELECT asset_key,
           date_trunc('day', run_started_at) AS d,
           SUM(rows_written)                 AS r
    FROM ingestion_runs
    WHERE run_started_at >= now() - INTERVAL 7 DAY
      AND status = 'success'
    GROUP BY 1, 2
),
med AS (
    SELECT asset_key, median(r) AS med7
    FROM daily
    GROUP BY 1
)
SELECT r.asset_key, r.last_ok, r.r_24h, m.med7, r.last_status, r.last_run_id
FROM recent r
LEFT JOIN med m USING (asset_key);
"""

_RECON_QUERY = """
SELECT asset_key, (metadata_json ->> 'drift_pct')::DOUBLE AS drift_pct
FROM ingestion_runs
WHERE asset_key LIKE 'recon/%'
  AND run_started_at >= now() - INTERVAL 1 DAY
QUALIFY row_number() OVER (PARTITION BY asset_key ORDER BY run_started_at DESC) = 1;
"""

_KPI_QUERY = """
SELECT
    (metadata_json ->> 'source_revenue')::DOUBLE AS source_revenue,
    (metadata_json ->> 'warehouse_revenue')::DOUBLE AS warehouse_revenue,
    (metadata_json ->> 'drift_pct')::DOUBLE AS drift_pct,
    (metadata_json ->> 'date_key')::INTEGER AS date_key,
    status
FROM ingestion_runs
WHERE asset_key = 'kpi/revenue_daily'
  AND run_started_at >= now() - INTERVAL 1 DAY
ORDER BY run_started_at DESC
LIMIT 1;
"""


def _fetch_stats(db_path: str) -> tuple[dict, dict, dict, Optional[KpiData]]:
    """Return (stats_by_asset_key, drift_by_recon_key, zero_streaks, kpi_data) dicts."""
    stats: dict = {}
    drift: dict = {}
    zero_streaks: dict = {}
    kpi_data: Optional[KpiData] = None
    try:
        conn = duckdb.connect(db_path, read_only=True)
        try:
            from orchestration.asset_checks.health_db import consecutive_empty_with_cursor_move

            rows = conn.execute(_MAIN_QUERY).fetchall()
            for asset_key, last_ok, r_24h, med7, last_status, last_run_id in rows:
                stats[asset_key] = (last_ok, r_24h, med7, last_status, last_run_id)

            recon_rows = conn.execute(_RECON_QUERY).fetchall()
            for rk, dp in recon_rows:
                drift[rk] = dp

            for _, asset_key, _ in KNOWN_ASSETS:
                streak = consecutive_empty_with_cursor_move(conn, asset_key, streak_n=5)
                if streak > 0:
                    zero_streaks[asset_key] = streak

            # Fetch KPI closure data (Phase 5)
            kpi_row = conn.execute(_KPI_QUERY).fetchone()
            if kpi_row:
                kpi_data = KpiData(
                    source_revenue=kpi_row[0],
                    warehouse_revenue=kpi_row[1],
                    drift_pct=kpi_row[2],
                    date_key=kpi_row[3],
                    status=kpi_row[4],
                )
        finally:
            conn.close()
    except Exception as exc:
        logger.error(f"morning_digest: failed to query health DB: {exc}")
        return {}, {}, {}, None
    return stats, drift, zero_streaks, kpi_data


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------

def build_digest_rows(db_path: str) -> tuple[list[DigestRow], Optional[KpiData]]:
    """Query ingestion_health.duckdb and build one DigestRow per known asset + KPI data."""
    stats, drift, zero_streaks, kpi_data = _fetch_stats(db_path)
    now_utc = datetime.now(timezone.utc)
    rows: list[DigestRow] = []

    for short_name, asset_key, recon_key in KNOWN_ASSETS:
        drift_val = drift.get(recon_key) if recon_key else None
        streak = zero_streaks.get(asset_key, 0)
        if asset_key not in stats:
            dr = DigestRow(
                short_name=short_name, asset_key=asset_key,
                status="gray", rows_24h=None, median_7d=None,
                pct_vs_median=None, fresh_age_min=None,
                drift_pct=drift_val, note="never run",
                zero_streak=streak,
            )
            dr.status = classify(dr)
            rows.append(dr)
            continue

        last_ok, r_24h, med7, last_status, last_run_id = stats[asset_key]

        fresh_age_min: Optional[int] = None
        if last_ok is not None:
            if hasattr(last_ok, "tzinfo") and last_ok.tzinfo is None:
                last_ok = last_ok.replace(tzinfo=timezone.utc)
            fresh_age_min = int((now_utc - last_ok).total_seconds() / 60)

        rows_24h_int = int(r_24h) if r_24h is not None else 0
        med7_int = int(med7) if med7 is not None else None

        pct: Optional[float] = None
        if med7_int and med7_int > 0:
            pct = round((rows_24h_int / med7_int - 1) * 100, 1)

        note: Optional[str] = None
        if last_status == "failed":
            note = "last run failed"

        dr = DigestRow(
            short_name=short_name, asset_key=asset_key,
            status="green",
            rows_24h=rows_24h_int,
            median_7d=med7_int,
            pct_vs_median=pct,
            fresh_age_min=fresh_age_min,
            drift_pct=drift_val,
            note=note,
            last_run_id=last_run_id,
            zero_streak=streak,
        )
        dr.status = classify(dr)
        rows.append(dr)

    return rows, kpi_data


# ---------------------------------------------------------------------------
# Card formatting
# ---------------------------------------------------------------------------

_EMOJI = {"green": "✅", "yellow": "⚠️", "red": "❌", "gray": "⬜"}
_LARK_COLOR = {"green": "green", "yellow": "orange", "red": "red", "gray": "grey"}

_DAGSTER_BASE = os.getenv("DAGSTER_URL", f"http://localhost:{os.getenv('DAGSTER_PORT', '3001')}")


def _run_link(run_id: Optional[str]) -> str:
    if not run_id:
        return ""
    short = run_id[:8]
    return f"[{short}]({_DAGSTER_BASE}/runs/{run_id})"


def _recommend(dr: "DigestRow") -> Optional[str]:
    """Return a short recommended action string, or None."""
    if dr.note == "last run failed":
        return "→ check logs, re-materialize"
    if dr.zero_streak >= 3:
        return "→ source may be empty; verify API/file"
    if dr.drift_pct is not None and abs(dr.drift_pct) > 5.0:
        return "→ run recon diff, check source counts"
    if dr.fresh_age_min is not None and dr.fresh_age_min > _SLA_HOURS * 60:
        return "→ check schedule/sensor, re-materialize"
    if dr.zero_streak >= 2:
        return "→ monitor next run for zero-rows"
    return None


def _fmt_age(minutes: Optional[int]) -> str:
    if minutes is None:
        return "unknown"
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    return f"{hours}h"


def _fmt_pct(pct: Optional[float]) -> str:
    if pct is None:
        return ""
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.0f}%"


def _format_vnd(amount: Optional[float]) -> str:
    """Format VND amount with thousand separators."""
    if amount is None:
        return "?"
    return f"{amount:,.0f}"


def compose_card_fields(rows: list[DigestRow], kpi_data: Optional[KpiData] = None) -> tuple[dict, str]:
    """Return (fields dict for send_lark_card, worst-severity color string)."""
    fields: dict[str, str] = {}
    worst = "green"
    severity_rank = {"green": 0, "gray": 1, "yellow": 2, "red": 3}

    # KPI revenue line at the top (Phase 5)
    if kpi_data is not None and kpi_data.status not in ("disabled", None):
        kpi_drift = kpi_data.drift_pct
        if kpi_drift is not None:
            abs_drift = abs(kpi_drift)
            drift_display = kpi_drift * 100
            if abs_drift > 0.005:  # > 0.5%
                kpi_emoji = "❌"
                kpi_status = "red"
            elif abs_drift > 0.001:  # > 0.1%
                kpi_emoji = "⚠️"
                kpi_status = "yellow"
            else:
                kpi_emoji = "✅"
                kpi_status = "green"

            src = _format_vnd(kpi_data.source_revenue)
            wh = _format_vnd(kpi_data.warehouse_revenue)
            sign = "+" if drift_display >= 0 else ""
            fields["💰 Revenue"] = f"{kpi_emoji} sapo={src} ₫ | warehouse={wh} ₫ | drift={sign}{drift_display:.2f}%"

            if severity_rank.get(kpi_status, 0) > severity_rank.get(worst, 0):
                worst = kpi_status
        elif kpi_data.status == "partial_source":
            fields["💰 Revenue"] = "⬜ Sapo API unavailable (RECON_LIVE_API=0?)"
        elif kpi_data.status == "partial_warehouse":
            fields["💰 Revenue"] = "⬜ warehouse unavailable (serving DB issue)"
        elif kpi_data.status == "failed":
            fields["💰 Revenue"] = "❌ both source & warehouse unavailable"
        elif kpi_data.status == "success":
            # Success but drift=None means source=0 (no orders yesterday)
            src = _format_vnd(kpi_data.source_revenue)
            wh = _format_vnd(kpi_data.warehouse_revenue)
            fields["💰 Revenue"] = f"✅ sapo={src} ₫ | warehouse={wh} ₫ | drift=N/A (zero base)"

    for dr in rows:
        em = _EMOJI[dr.status]
        run_link = _run_link(dr.last_run_id)

        if dr.note == "never run":
            val = f"{em} never run"
        elif dr.note == "health DB unreachable":
            val = f"{em} health DB unreachable"
        elif dr.drift_pct is not None and abs(dr.drift_pct) > 5.0:
            sign = "+" if dr.drift_pct >= 0 else ""
            val = f"{em} RECON DRIFT {sign}{dr.drift_pct:.1f}%"
        else:
            rows_str = f"{dr.rows_24h:,}" if dr.rows_24h is not None else "?"
            med_str = f"{dr.median_7d:,}" if dr.median_7d else "?"
            pct_str = _fmt_pct(dr.pct_vs_median)
            age_str = _fmt_age(dr.fresh_age_min)
            med_part = f"med {med_str}"
            if pct_str:
                med_part += f", {pct_str}"
            val = f"{em} 24h: {rows_str} ({med_part}) · fresh: {age_str}"
            if dr.drift_pct is not None:
                sign = "+" if dr.drift_pct >= 0 else ""
                val += f" · drift: {sign}{dr.drift_pct:.1f}%"

        if dr.zero_streak >= 2:
            val += f" · ⚠ {dr.zero_streak}x zero-rows"

        if run_link and dr.status in ("yellow", "red"):
            val += f" · run: {run_link}"

        action = _recommend(dr)
        if action:
            val += f"\n{action}"

        fields[dr.short_name] = val

        if severity_rank.get(dr.status, 0) > severity_rank.get(worst, 0):
            worst = dr.status

    return fields, _LARK_COLOR.get(worst, "grey")


def _today_ict() -> str:
    """Return current date string in Asia/Ho_Chi_Minh (+07:00)."""
    utc_now = datetime.now(timezone.utc)
    ict_now = utc_now + timedelta(hours=7)
    return ict_now.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Op + job
# ---------------------------------------------------------------------------

@op
def compose_and_send_digest(_context) -> None:
    """Read ingestion_health.duckdb and post morning Lark card."""
    db_path = get_db_path()
    dry_run = os.getenv("DIGEST_DRY_RUN", "0") == "1"

    kpi_data: Optional[KpiData] = None

    # Graceful degradation: DB may not exist yet on first boot
    if not os.path.exists(db_path):
        logger.warning(f"morning_digest: health DB not found at {db_path}")
        rows = [
            DigestRow(
                short_name=s, asset_key=ak, status="gray",
                rows_24h=None, median_7d=None, pct_vs_median=None,
                fresh_age_min=None, drift_pct=None, note="never run",
            )
            for s, ak, _ in KNOWN_ASSETS
        ]
        # Reclassify so note="never run" → gray
        for r in rows:
            r.status = classify(r)
    else:
        rows, kpi_data = build_digest_rows(db_path)

    if not rows:
        logger.warning("morning_digest: build_digest_rows returned empty list")
        return

    fields, color = compose_card_fields(rows, kpi_data)
    title = f"Data Ingestion Morning Report — {_today_ict()}"

    if dry_run:
        print(f"\n[DIGEST DRY-RUN] {title}  [{color.upper()}]")
        for k, v in fields.items():
            print(f"  {k:<16} {v}")
        return

    try:
        send_lark_card(title=title, fields=fields, color=color)
    except Exception as exc:
        # Must not fail the Dagster run
        logger.error(f"morning_digest: Lark send raised unexpectedly: {exc}")


@job
def health_report_digest_job():
    compose_and_send_digest()
