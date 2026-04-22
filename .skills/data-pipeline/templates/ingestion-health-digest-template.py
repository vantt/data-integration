"""Morning digest — reusable template for per-source ingestion health summary.

Runs once per day in business TZ AFTER overnight batch+recon have finished
(typical schedule: 06:00 local). Reads the health DB, computes one severity
per asset, renders a Lark/Slack card for yesterday's full calendar day.

Customize for each project:
  - KNOWN_ASSETS registry (short_name, asset_key, recon_key)
  - ASSET_DISPLAY labels + asset_type + unit
  - BIZ_TZ (IANA timezone)
  - SLA_HOURS
  - KPI query + formatting (if doing revenue-closure drift)
  - send_card() delivery adapter

Design invariants:
  - Window = YESTERDAY's business-TZ calendar day (0h-24h), NOT rolling 24h.
  - Freshness is absolute (no window), graded by SLA_HOURS.
  - Classification rules live in code for discoverability, not config.
  - Delivery failure must NEVER fail the run — wrap in try/except.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Literal, Optional

import duckdb

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONFIG — customize per project
# ---------------------------------------------------------------------------

BIZ_TZ = "Asia/Ho_Chi_Minh"      # IANA timezone for calendar-day bucketing
SLA_HOURS = 12                   # freshness SLA — beyond this, asset goes red

# (short_name, asset_key, recon_asset_key_or_None)
KNOWN_ASSETS: list[tuple[str, str, Optional[str]]] = [
    # ("orders",    "source/orders_batch",    "recon/orders_daily"),
    # ("customers", "source/customers_batch", "recon/customers_daily"),
    # ("events",    "source/events_cursor",   None),
]

# (vietnamese_label, asset_type, unit_label)
# asset_type drives messaging: cursor / batch / file_drop
ASSET_DISPLAY: dict[str, tuple[str, str, str]] = {
    # "orders":    ("Orders (batch)",     "batch",     "đơn"),
    # "customers": ("Customers (batch)",  "batch",     "khách"),
    # "events":    ("Events (realtime)",  "cursor",    "sự kiện"),
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class DigestRow:
    short_name: str
    asset_key: str
    status: Literal["green", "yellow", "red", "gray"]
    rows_yday: Optional[int]
    median_7d: Optional[int]
    fresh_age_min: Optional[int]   # minutes since last success (absolute, not windowed)
    drift_pct: Optional[float]     # from recon, if applicable
    note: Optional[str]            # "never run" | "last run failed" | None
    last_run_id: Optional[str] = None
    zero_streak: int = 0
    runs_yday: int = 0
    last_status: Optional[str] = None


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify(row: DigestRow) -> Literal["green", "yellow", "red", "gray"]:
    # Drift overrides everything — actionable even when asset "never ran"
    if row.drift_pct is not None:
        if abs(row.drift_pct) > 5.0: return "red"
        if abs(row.drift_pct) > 1.0: return "yellow"

    if row.note in ("never run", "health DB unreachable"):
        return "gray"

    if row.fresh_age_min is not None and row.fresh_age_min > SLA_HOURS * 60:
        return "red"

    if row.median_7d and row.median_7d > 0 and row.rows_yday is not None:
        if row.rows_yday / row.median_7d < 0.5:
            return "yellow"

    if row.zero_streak >= 3: return "red"
    if row.zero_streak >= 2: return "yellow"

    if row.note == "last run failed":
        return "red"

    return "green"


# ---------------------------------------------------------------------------
# SQL — yesterday's business-day window
# ---------------------------------------------------------------------------

_MAIN_QUERY = f"""
WITH recent AS (
    SELECT asset_key,
           MAX(run_started_at) FILTER (WHERE status IN ('success', 'skipped')) AS last_ok,
           SUM(rows_written)   FILTER (
               WHERE (run_started_at AT TIME ZONE '{BIZ_TZ}')::DATE
                   = ((now()          AT TIME ZONE '{BIZ_TZ}')::DATE - 1)
           )                                                                    AS r_yday,
           COUNT(*)            FILTER (
               WHERE (run_started_at AT TIME ZONE '{BIZ_TZ}')::DATE
                   = ((now()          AT TIME ZONE '{BIZ_TZ}')::DATE - 1)
           )                                                                    AS runs_yday,
           LAST(status ORDER BY run_started_at) AS last_status,
           LAST(run_id ORDER BY run_started_at) AS last_run_id
    FROM ingestion_runs
    GROUP BY asset_key
),
daily AS (
    SELECT asset_key,
           (run_started_at AT TIME ZONE '{BIZ_TZ}')::DATE AS d,
           SUM(rows_written)                              AS r
    FROM ingestion_runs
    WHERE (run_started_at AT TIME ZONE '{BIZ_TZ}')::DATE
        >= ((now() AT TIME ZONE '{BIZ_TZ}')::DATE - 7)
      AND status IN ('success', 'skipped')
    GROUP BY 1, 2
),
med AS (SELECT asset_key, median(r) AS med7 FROM daily GROUP BY 1)
SELECT r.asset_key, r.last_ok, r.r_yday, m.med7,
       r.last_status, r.last_run_id, r.runs_yday
FROM recent r LEFT JOIN med m USING (asset_key);
"""

_RECON_QUERY = """
SELECT asset_key, (metadata_json ->> 'drift_pct')::DOUBLE AS drift_pct
FROM ingestion_runs
WHERE asset_key LIKE 'recon/%'
  AND run_started_at >= now() - INTERVAL 1 DAY
QUALIFY row_number() OVER (PARTITION BY asset_key ORDER BY run_started_at DESC) = 1;
"""


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------

def build_digest_rows(db_path: str) -> list[DigestRow]:
    rows: list[DigestRow] = []
    stats: dict = {}
    drift: dict = {}
    zero_streaks: dict = {}

    try:
        conn = duckdb.connect(db_path, read_only=True)
        try:
            for r in conn.execute(_MAIN_QUERY).fetchall():
                asset_key, last_ok, r_yday, med7, last_status, last_run_id, runs_yday = r
                stats[asset_key] = (last_ok, r_yday, med7, last_status, last_run_id, runs_yday)
            for rk, dp in conn.execute(_RECON_QUERY).fetchall():
                drift[rk] = dp
            # Optional: compute zero_streak per known asset via
            # orchestration.ops.ingestion_health.consecutive_empty_with_cursor_move
        finally:
            conn.close()
    except Exception as exc:
        logger.error("digest: health DB unreachable: %s", exc)
        return [
            DigestRow(
                short_name=s, asset_key=ak,
                status="gray", rows_yday=None, median_7d=None,
                fresh_age_min=None, drift_pct=None,
                note="health DB unreachable",
            )
            for s, ak, _ in KNOWN_ASSETS
        ]

    now_utc = datetime.now(timezone.utc)
    for short_name, asset_key, recon_key in KNOWN_ASSETS:
        drift_val = drift.get(recon_key) if recon_key else None
        streak = zero_streaks.get(asset_key, 0)

        if asset_key not in stats:
            dr = DigestRow(
                short_name=short_name, asset_key=asset_key,
                status="gray", rows_yday=None, median_7d=None,
                fresh_age_min=None, drift_pct=drift_val,
                note="never run", zero_streak=streak,
            )
            dr.status = classify(dr)
            rows.append(dr)
            continue

        last_ok, r_yday, med7, last_status, last_run_id, runs_yday = stats[asset_key]

        fresh_age_min: Optional[int] = None
        if last_ok is not None:
            if hasattr(last_ok, "tzinfo") and last_ok.tzinfo is None:
                last_ok = last_ok.replace(tzinfo=timezone.utc)
            fresh_age_min = int((now_utc - last_ok).total_seconds() / 60)

        note: Optional[str] = None
        if last_status == "failed":
            note = "last run failed"

        dr = DigestRow(
            short_name=short_name, asset_key=asset_key,
            status="green",
            rows_yday=int(r_yday) if r_yday is not None else 0,
            median_7d=int(med7) if med7 is not None else None,
            fresh_age_min=fresh_age_min,
            drift_pct=drift_val,
            note=note,
            last_run_id=last_run_id,
            zero_streak=streak,
            runs_yday=int(runs_yday or 0),
            last_status=last_status,
        )
        dr.status = classify(dr)
        rows.append(dr)

    return rows


# ---------------------------------------------------------------------------
# Message formatting — asset-type aware
# ---------------------------------------------------------------------------

_EMOJI = {"green": "✅", "yellow": "⚠️", "red": "❌", "gray": "⬜"}


def format_row(dr: DigestRow) -> str:
    em = _EMOJI[dr.status]
    label, asset_type, unit = ASSET_DISPLAY.get(
        dr.short_name, (dr.short_name, "batch", "dòng")
    )
    age = _fmt_age(dr.fresh_age_min)
    rows_str = _fmt_int(dr.rows_yday)
    rows_int = dr.rows_yday or 0

    # Special states override standard format
    if dr.note == "never run":
        return f"{em} {label}: Chưa từng chạy"
    if dr.note == "last run failed":
        return f"{em} {label}: Lần chạy gần nhất LỖI · {age} trước"
    if dr.drift_pct is not None and abs(dr.drift_pct) > 5.0:
        sign = "+" if dr.drift_pct >= 0 else ""
        return f"{em} {label}: Lệch source {sign}{dr.drift_pct:.1f}% · {age} trước"
    if dr.fresh_age_min is not None and dr.fresh_age_min > SLA_HOURS * 60:
        return f"{em} {label}: Quá hạn — {age} chưa cập nhật"

    # Standard rendering by asset_type
    if asset_type == "cursor":
        if rows_int > 0:
            return f"{em} {label}: {rows_str} {unit} mới · chạy {dr.runs_yday} lần hôm qua"
        return f"{em} {label}: Không có {unit} mới (đã chạy {dr.runs_yday} lần hôm qua)"
    if asset_type == "batch":
        if rows_int > 0:
            return f"{em} {label}: Batch hôm qua {rows_str} {unit} mới"
        return f"{em} {label}: Batch hôm qua — không có {unit} mới"
    # file_drop
    if rows_int > 0:
        return f"{em} {label}: File mới có {rows_str} {unit}"
    return f"{em} {label}: File nguồn chưa thay đổi"


def _fmt_age(minutes: Optional[int]) -> str:
    if minutes is None: return "chưa rõ"
    if minutes < 60:    return f"{minutes} phút"
    hours = minutes // 60
    if hours < 24:      return f"{hours} giờ"
    return f"{hours // 24} ngày"


def _fmt_int(n: Optional[int]) -> str:
    if n is None: return "?"
    return f"{n:,}".replace(",", ".")   # VN thousand separator


# ---------------------------------------------------------------------------
# Compose + deliver
# ---------------------------------------------------------------------------

def compose_card(rows: list[DigestRow]) -> tuple[dict, str]:
    """Return (fields_dict, worst_color) ready for send_card()."""
    severity_rank = {"green": 0, "gray": 1, "yellow": 2, "red": 3}
    worst = "green"
    counts = {"green": 0, "yellow": 0, "red": 0, "gray": 0}
    fields: dict[str, str] = {}

    lines: list[str] = []
    for dr in rows:
        counts[dr.status] = counts.get(dr.status, 0) + 1
        if severity_rank.get(dr.status, 0) > severity_rank.get(worst, 0):
            worst = dr.status
        lines.append(format_row(dr))

    if rows:
        total = sum(counts.values())
        parts = [f"{counts['green']}/{total} khoẻ"]
        if counts["yellow"]: parts.append(f"{counts['yellow']} cảnh báo")
        if counts["red"]:    parts.append(f"{counts['red']} lỗi")
        if counts["gray"]:   parts.append(f"{counts['gray']} chưa chạy")
        fields["📊 Tổng quan"] = " · ".join(parts)

    for i, line in enumerate(lines):
        fields[f"row_{i:02d}"] = line  # adjust key scheme per delivery format

    return fields, worst


def run_digest(get_db_path_fn, send_card_fn) -> None:
    """Entry point — wire this into Dagster @op, Airflow task, or cron.

    get_db_path_fn: callable returning path to health DB
    send_card_fn:   callable(title, fields, color) — NEVER let it raise past here
    """
    db_path = get_db_path_fn()
    dry_run = os.getenv("DIGEST_DRY_RUN", "0") == "1"
    rows = build_digest_rows(db_path)
    if not rows:
        logger.warning("digest: no rows to report")
        return

    fields, color = compose_card(rows)
    title = f"Ingestion Health — {_yesterday_biz_str()}"

    if dry_run:
        print(f"\n[DRY-RUN] {title}  [{color.upper()}]")
        for k, v in fields.items():
            print(f"  {v}")
        return

    try:
        send_card_fn(title=title, fields=fields, color=color)
    except Exception as exc:
        logger.error("digest: delivery failed: %s", exc)


def _yesterday_biz_str() -> str:
    ict = timezone(timedelta(hours=7))   # adjust offset per BIZ_TZ
    return (datetime.now(ict) - timedelta(days=1)).strftime("%Y-%m-%d")
