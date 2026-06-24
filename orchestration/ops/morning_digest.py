"""Morning Lark digest for ingestion health.

Runs at 06:00 Asia/Ho_Chi_Minh daily. Reads ingestion_health.db,
composes one Lark card summarising yesterday's ingestion volume (ICT
0h-24h), 7-day median trend, freshness, recon drift, consecutive
zero-row streaks, and recommended actions per source.
Dry-run via DIGEST_DRY_RUN=1.

Architecture: @op inside a job (not an asset — no downstream data graph).
Card delivery failure is caught and logged — never fails the Dagster run.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Literal, Optional

from dagster import job, op

from orchestration.asset_checks.health_db import consecutive_empty_with_cursor_move, open_readonly
from orchestration.ops.ingestion_health import get_db_path
from orchestration.notifications.lark_client import send_lark_card

logger = logging.getLogger("orchestration.morning_digest")

# ---------------------------------------------------------------------------
# Known asset registry: (short_name, asset_key, recon_asset_key | None)
# ---------------------------------------------------------------------------
KNOWN_ASSETS: list[tuple[str, str, Optional[str]]] = [
    ("sapo_webhook",   "sapo/ingest_sapo_v2_webhook_consumer_asset",                    None),
    ("sapo_history",   "sapo/ingest_sapo_v2_history_log_asset",                         None),
    ("sapo_orders",    "sapo/ingest_sapo_v2_orders_batch_asset",                        "recon/sapo_orders_daily"),
    ("sapo_customers", "sapo/ingest_sapo_v2_customers_batch_asset",                     "recon/sapo_customers_daily"),
    ("sapo_products",  "sapo/ingest_sapo_v2_products_batch_asset",                      None),
    ("sapo_accounts",  "sapo/ingest_sapo_v2_accounts_batch_asset",                      None),
    ("sapo_inventory", "sapo/ingest_sapo_v2_inventory_transactions_asset",           None),
    ("shopee",         "shopee/shopee_income_file_drop_asset",                "recon/shopee_daily"),
    ("misa",           "misa_amis/misa_sales_file_drop_asset",                "recon/misa_daily"),
    ("misa_acct",      "misa_amis/misa_account_ledger_file_drop_asset",       None),
    ("sheet_targets",  "sheets/sheets_targets_asset",                         None),
    ("sheet_spend",    "sheets/sheets_marketing_spend_asset",                 None),
    ("sheet_team",     "sheets/sheets_team_config_asset",                     None),
    ("sheet_us_prices","sheets/sheets_us_shipment_prices_asset",              None),
    ("sheet_overhead", "sheets/sheets_overhead_classification_asset",         None),
    ("hug",            "hug/ingest_hug_webhook_consumer_asset",               None),
]

# ---------------------------------------------------------------------------
# Display config: (vietnamese_label, asset_type, unit_label)
# asset_type drives how "no new data" is interpreted in the message:
#   - cursor    : runs every few minutes; "0 dòng mới" is the normal state
#   - batch     : runs once per day on a schedule
#   - file_drop : depends on a source file landing (sheet/CSV)
# unit_label is the noun used for rows (đơn / khách / sản phẩm / dòng …)
# ---------------------------------------------------------------------------
ASSET_DISPLAY: dict[str, tuple[str, str, str]] = {
    "sapo_webhook":   ("Sapo webhook (realtime events)",          "cursor",    "events"),
    "sapo_history":   ("Sapo lịch sử (audit log)",                "cursor",    "dòng"),
    "sapo_orders":    ("Sapo đơn hàng (batch)",                   "batch",     "đơn"),
    "sapo_customers": ("Sapo khách hàng",                         "batch",     "khách"),
    "sapo_products":  ("Sapo sản phẩm",                           "batch",     "sản phẩm"),
    "sapo_accounts":  ("Sapo tài khoản",                          "batch",     "tài khoản"),
    "sapo_inventory": ("Sapo tồn kho (batch)",                    "batch",     "giao dịch"),
    "shopee":         ("Shopee — file thu nhập",                  "file_drop", "dòng"),
    "misa":           ("MISA — file bán hàng",                    "file_drop", "dòng"),
    "misa_acct":      ("MISA — sổ chi tiết tài khoản",            "file_drop", "dòng"),
    "sheet_targets":  ("Google Sheet — Mục tiêu",                 "file_drop", "dòng"),
    "sheet_spend":    ("Google Sheet — Chi marketing",            "file_drop", "dòng"),
    "sheet_team":     ("Google Sheet — Cấu hình nhóm",            "file_drop", "dòng"),
    "sheet_us_prices":("Google Sheet — Giá vận chuyển US",        "file_drop", "dòng"),
    "sheet_overhead": ("Google Sheet — Phân loại overhead",       "file_drop", "dòng"),
    "hug":            ("Hug webhook consumer",                    "cursor",    "events"),
}

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
    runs_24h: int = 0              # how many times asset ran yesterday (ICT 0h-24h)
    last_status: Optional[str] = None  # success | skipped | failed


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
-- Reporting window = yesterday's ICT calendar day (0h-24h Asia/Ho_Chi_Minh).
-- run_started_at is stored as UTC string; '+7 hours' converts to ICT for date bucketing.
WITH last_row AS (
    -- Most recent run per asset for last_status / last_run_id.
    SELECT asset_key, status AS last_status, run_id AS last_run_id
    FROM (
        SELECT asset_key, status, run_id,
               ROW_NUMBER() OVER (PARTITION BY asset_key ORDER BY run_started_at DESC) AS rn
        FROM ingestion_runs
    ) WHERE rn = 1
),
recent AS (
    SELECT
        asset_key,
        MAX(run_started_at) FILTER (WHERE status IN ('success', 'skipped')) AS last_ok,
        MAX(run_started_at)                                                  AS last_any,
        SUM(rows_written)   FILTER (
            WHERE date(run_started_at, '+7 hours') = date('now', '+7 hours', '-1 day')
        )                                                                    AS r_yday,
        COUNT(*)            FILTER (
            WHERE date(run_started_at, '+7 hours') = date('now', '+7 hours', '-1 day')
        )                                                                    AS runs_yday
    FROM ingestion_runs
    GROUP BY asset_key
),
daily AS (
    SELECT asset_key,
           date(run_started_at, '+7 hours') AS d,
           SUM(rows_written)               AS r
    FROM ingestion_runs
    WHERE date(run_started_at, '+7 hours') >= date('now', '+7 hours', '-7 days')
      AND status IN ('success', 'skipped')
    GROUP BY 1, 2
),
med AS (
    -- Median via middle-value trick: works for up to 7 rows per asset.
    SELECT asset_key, AVG(CAST(r AS REAL)) AS med7
    FROM (
        SELECT asset_key, r,
               ROW_NUMBER() OVER (PARTITION BY asset_key ORDER BY r) AS rn,
               COUNT(*)     OVER (PARTITION BY asset_key)            AS cnt
        FROM daily
    )
    WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
    GROUP BY asset_key
)
SELECT r.asset_key, r.last_ok, r.r_yday, m.med7, lr.last_status, lr.last_run_id, r.runs_yday
FROM recent r
LEFT JOIN med m       USING (asset_key)
LEFT JOIN last_row lr USING (asset_key);
"""

_RECON_QUERY = """
SELECT asset_key,
       CAST(json_extract(metadata_json, '$.drift_pct') AS REAL) AS drift_pct
FROM (
    SELECT asset_key, metadata_json,
           ROW_NUMBER() OVER (PARTITION BY asset_key ORDER BY run_started_at DESC) AS rn
    FROM ingestion_runs
    WHERE asset_key LIKE 'recon/%'
      AND run_started_at >= datetime('now', '-1 day')
)
WHERE rn = 1;
"""

_KPI_QUERY = """
SELECT
    CAST(json_extract(metadata_json, '$.source_revenue')    AS REAL)    AS source_revenue,
    CAST(json_extract(metadata_json, '$.warehouse_revenue') AS REAL)    AS warehouse_revenue,
    CAST(json_extract(metadata_json, '$.drift_pct')         AS REAL)    AS drift_pct,
    CAST(json_extract(metadata_json, '$.date_key')          AS INTEGER) AS date_key,
    status
FROM ingestion_runs
WHERE asset_key = 'kpi/revenue_daily'
  AND run_started_at >= datetime('now', '-1 day')
ORDER BY run_started_at DESC
LIMIT 1;
"""


def _parse_dt(val) -> Optional[datetime]:
    """Coerce a SQLite timestamp value (string or datetime) to timezone-aware UTC datetime.

    MAX(run_started_at) returns a string (not converted by PARSE_DECLTYPES) — this handles it.
    """
    if val is None:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(val))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _fetch_stats(log=None) -> tuple[dict, dict, dict, Optional[KpiData]]:
    """Return (stats_by_asset_key, drift_by_recon_key, zero_streaks, kpi_data) dicts.

    log: callable (e.g. context.log.info) — emits Dagster heartbeat events during
    blocking queries so the stuck-run alerter doesn't kill us after 5 min of silence.
    """
    def _heartbeat(msg: str):
        if log:
            log(msg)
        else:
            logger.info(msg)

    stats: dict = {}
    drift: dict = {}
    zero_streaks: dict = {}
    kpi_data: Optional[KpiData] = None
    try:
        with open_readonly() as conn:
            _heartbeat("morning_digest: running main stats query (window + median)...")
            rows = conn.execute(_MAIN_QUERY).fetchall()
            for asset_key, last_ok, r_24h, med7, last_status, last_run_id, runs_24h in rows:
                # last_ok is MAX() expression — not auto-converted by PARSE_DECLTYPES
                stats[asset_key] = (_parse_dt(last_ok), r_24h, med7, last_status, last_run_id, runs_24h)
            _heartbeat(f"morning_digest: main query done ({len(rows)} assets)")

            _heartbeat("morning_digest: running recon drift query...")
            recon_rows = conn.execute(_RECON_QUERY).fetchall()
            for rk, dp in recon_rows:
                drift[rk] = dp

            _heartbeat(f"morning_digest: scanning zero-streak for {len(KNOWN_ASSETS)} assets...")
            for _, asset_key, _ in KNOWN_ASSETS:
                streak = consecutive_empty_with_cursor_move(conn, asset_key, streak_n=5)
                if streak > 0:
                    zero_streaks[asset_key] = streak

            _heartbeat("morning_digest: running KPI closure query...")
            kpi_row = conn.execute(_KPI_QUERY).fetchone()
            if kpi_row:
                kpi_data = KpiData(
                    source_revenue=kpi_row[0],
                    warehouse_revenue=kpi_row[1],
                    drift_pct=kpi_row[2],
                    date_key=kpi_row[3],
                    status=kpi_row[4],
                )
    except Exception as exc:
        logger.error(f"morning_digest: failed to query health DB: {exc}")
        return {}, {}, {}, None
    return stats, drift, zero_streaks, kpi_data


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------

def build_digest_rows(db_path: str, log=None) -> tuple[list[DigestRow], Optional[KpiData]]:
    """Query ingestion_health.db and build one DigestRow per known asset + KPI data."""
    stats, drift, zero_streaks, kpi_data = _fetch_stats(log=log)
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

        last_ok, r_24h, med7, last_status, last_run_id, runs_24h = stats[asset_key]

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
            runs_24h=int(runs_24h or 0),
            last_status=last_status,
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
    """Return a short Vietnamese recommended action string, or None."""
    if dr.note == "last run failed":
        return "→ Xem log Dagster, chạy lại asset"
    if dr.zero_streak >= 3:
        return "→ Source có thể đang rỗng; kiểm tra API/file nguồn"
    if dr.drift_pct is not None and abs(dr.drift_pct) > 5.0:
        return "→ Chạy recon diff, đối chiếu số liệu source"
    if dr.fresh_age_min is not None and dr.fresh_age_min > _SLA_HOURS * 60:
        return "→ Kiểm tra schedule/sensor, chạy lại asset"
    if dr.zero_streak >= 2:
        return "→ Theo dõi lần chạy kế tiếp, nếu vẫn 0 dòng cần kiểm tra source"
    return None


def _fmt_age_vi(minutes: Optional[int]) -> str:
    """Vietnamese-friendly age string."""
    if minutes is None:
        return "chưa rõ"
    if minutes < 60:
        return f"{minutes} phút"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} giờ"
    days = hours // 24
    return f"{days} ngày"


def _fmt_int(n: Optional[int]) -> str:
    if n is None:
        return "?"
    return f"{n:,}".replace(",", ".")  # Vietnamese thousand separator


def _format_vnd(amount: Optional[float]) -> str:
    """Format VND amount with thousand separators."""
    if amount is None:
        return "?"
    return f"{amount:,.0f}"


def compose_card_fields(rows: list[DigestRow], kpi_data: Optional[KpiData] = None) -> tuple[dict, str]:
    """Return (fields dict for send_lark_card, worst-severity color string).

    Field order in the returned dict matters — the Lark card renders fields
    top-to-bottom in insertion order. Layout:
      1. 📊 Tổng quan       — summary header (always first when rows exist)
      2. 💰 Doanh thu hôm qua — KPI line (only when kpi_data present)
      3. <asset rows>        — one line per known asset
    """
    fields: dict[str, str] = {}
    worst = "green"
    severity_rank = {"green": 0, "gray": 1, "yellow": 2, "red": 3}

    # ---- Pass 1: format asset rows + tally severity counts -------------------
    asset_lines: list[tuple[str, str]] = []  # (display_label, formatted_value)
    counts = {"green": 0, "yellow": 0, "red": 0, "gray": 0}

    for dr in rows:
        counts[dr.status] = counts.get(dr.status, 0) + 1
        if severity_rank.get(dr.status, 0) > severity_rank.get(worst, 0):
            worst = dr.status

        label, asset_type, unit = ASSET_DISPLAY.get(
            dr.short_name, (dr.short_name, "batch", "dòng")
        )
        asset_lines.append((label, _format_row_vi(dr, asset_type, unit)))

    # ---- Pass 2: KPI signal (computes color, doesn't insert yet) -------------
    kpi_field_value: Optional[str] = None
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
            kpi_field_value = (
                f"{kpi_emoji} Sapo: {src} ₫ · Warehouse: {wh} ₫ · "
                f"lệch: {sign}{drift_display:.2f}%"
            )

            if severity_rank.get(kpi_status, 0) > severity_rank.get(worst, 0):
                worst = kpi_status
        elif kpi_data.status == "partial_source":
            kpi_field_value = "⬜ Không đọc được raw DB (raw.duckdb unavailable?)"
        elif kpi_data.status == "partial_warehouse":
            kpi_field_value = "⬜ Không đọc được warehouse (serving DB issue)"
        elif kpi_data.status == "failed":
            kpi_field_value = "❌ Cả Sapo lẫn warehouse đều không truy cập được"
        elif kpi_data.status == "success":
            src = _format_vnd(kpi_data.source_revenue)
            wh = _format_vnd(kpi_data.warehouse_revenue)
            kpi_field_value = (
                f"✅ Sapo: {src} ₫ · Warehouse: {wh} ₫ · lệch: N/A (doanh thu = 0)"
            )

    # ---- Insert in display order: Summary → KPI → Assets --------------------
    if asset_lines:
        total = sum(counts.values())
        summary_parts = [f"{counts['green']}/{total} khoẻ"]
        if counts["yellow"]:
            summary_parts.append(f"{counts['yellow']} cảnh báo")
        if counts["red"]:
            summary_parts.append(f"{counts['red']} lỗi")
        if counts["gray"]:
            summary_parts.append(f"{counts['gray']} chưa chạy")
        fields["📊 Tổng quan"] = " · ".join(summary_parts)

    if kpi_field_value is not None:
        fields["💰 Doanh thu hôm qua"] = kpi_field_value

    for label, val in asset_lines:
        fields[label] = val

    # Empty input → "no data" state, not "all healthy".
    if not rows and kpi_field_value is None:
        worst = "gray"

    return fields, _LARK_COLOR.get(worst, "grey")


def _format_row_vi(dr: DigestRow, asset_type: str, unit: str) -> str:
    """Render a single asset row in Vietnamese, contextual to asset_type.

    asset_type:
      - cursor    : runs every few minutes; "0 dòng mới" is normal — emphasise runs_24h
      - batch     : runs once a day; emphasise rows ingested vs schedule
      - file_drop : depends on a file; "0 dòng" usually means file unchanged
    """
    em = _EMOJI[dr.status]
    age = _fmt_age_vi(dr.fresh_age_min)

    # Special states (override standard format) ---------------------------
    if dr.note == "never run":
        return f"{em} Chưa từng chạy — kiểm tra job/schedule"
    if dr.note == "health DB unreachable":
        return f"{em} Không đọc được DB sức khoẻ"
    if dr.note == "last run failed":
        link = _run_link(dr.last_run_id)
        suffix = f" · run {link}" if link else ""
        line = f"{em} Lần chạy gần nhất LỖI · {age} trước{suffix}"
        action = _recommend(dr)
        return f"{line}\n{action}" if action else line

    # Drift overrides — most actionable signal -----------------------------
    if dr.drift_pct is not None and abs(dr.drift_pct) > 5.0:
        sign = "+" if dr.drift_pct >= 0 else ""
        line = f"{em} Lệch source {sign}{dr.drift_pct:.1f}% (recon) · cập nhật {age} trước"
        action = _recommend(dr)
        return f"{line}\n{action}" if action else line

    # Stale beyond SLA -----------------------------------------------------
    if dr.fresh_age_min is not None and dr.fresh_age_min > _SLA_HOURS * 60:
        line = f"{em} Quá hạn — {age} chưa cập nhật (SLA {_SLA_HOURS}h)"
        action = _recommend(dr)
        return f"{line}\n{action}" if action else line

    # Standard healthy/warning rendering by asset_type --------------------
    rows_str = _fmt_int(dr.rows_24h)
    rows_int = dr.rows_24h or 0

    if asset_type == "cursor":
        # Cursor jobs run every few minutes — "0" is normal. Show frequency over yesterday.
        runs = dr.runs_24h
        if rows_int > 0:
            line = f"{em} {rows_str} {unit} mới · chạy {runs} lần hôm qua · cập nhật {age} trước"
        else:
            line = f"{em} Không có {unit} mới (đã chạy {runs} lần hôm qua) · cập nhật {age} trước"
    elif asset_type == "batch":
        # Batch jobs run once a day. Show what was ingested yesterday (ICT 0h–24h).
        if rows_int > 0:
            line = f"{em} Batch hôm qua: {rows_str} {unit} mới · cập nhật {age} trước"
        else:
            line = f"{em} Batch hôm qua: không có {unit} mới · cập nhật {age} trước"
    else:  # file_drop
        if rows_int > 0:
            line = f"{em} File mới có {rows_str} {unit} · cập nhật {age} trước"
        else:
            line = f"{em} File nguồn chưa thay đổi · cập nhật {age} trước"

    # Drift annotation (small, < 5% — doesn't override main message)
    if dr.drift_pct is not None and abs(dr.drift_pct) <= 5.0:
        sign = "+" if dr.drift_pct >= 0 else ""
        line += f" · lệch source: {sign}{dr.drift_pct:.1f}%"

    # Zero-streak warning
    if dr.zero_streak >= 2:
        line += f" · ⚠ {dr.zero_streak} lần liên tiếp 0 dòng"

    # Run link for non-green
    if dr.status in ("yellow", "red") and dr.last_run_id:
        line += f" · run {_run_link(dr.last_run_id)}"

    # Recommendation
    action = _recommend(dr)
    return f"{line}\n{action}" if action else line


def _today_ict() -> str:
    """Return current date string in Asia/Ho_Chi_Minh (+07:00)."""
    utc_now = datetime.now(timezone.utc)
    ict_now = utc_now + timedelta(hours=7)
    return ict_now.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Op + job
# ---------------------------------------------------------------------------

def _check_db_staleness() -> Optional[float]:
    """Return age in hours of the last health DB write, or None if unreadable."""
    try:
        with open_readonly() as conn:
            row = conn.execute("SELECT MAX(run_started_at) FROM ingestion_runs").fetchone()
        if not row or row[0] is None:
            return None
        last_write = _parse_dt(row[0])
        if last_write is None:
            return None
        return (datetime.now(timezone.utc) - last_write).total_seconds() / 3600
    except Exception:
        return None


@op
def compose_and_send_digest(context) -> None:
    """Read ingestion_health.db and post morning Lark card."""
    db_path = get_db_path()
    dry_run = os.getenv("DIGEST_DRY_RUN", "0") == "1"

    kpi_data: Optional[KpiData] = None
    stale_age_h: Optional[float] = None

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
        # Check for stale monitoring data before building rows.
        # sapo_webhook writes every 3 min; a gap > 6h means the recorder is broken.
        stale_age_h = _check_db_staleness()
        rows, kpi_data = build_digest_rows(db_path, log=context.log.info)

    if not rows:
        logger.warning("morning_digest: build_digest_rows returned empty list")
        return

    fields, color = compose_card_fields(rows, kpi_data)

    # Prepend stale-data banner when health monitoring itself is broken.
    # Threshold 6h: lenient enough to not fire for brief restarts, strict
    # enough to catch the "8 days frozen" scenario on the next morning report.
    if stale_age_h is not None and stale_age_h > 6:
        days = int(stale_age_h // 24)
        hours = int(stale_age_h % 24)
        age_str = f"{days} ngày {hours} giờ" if days else f"{int(stale_age_h)} giờ"
        # Insert as the first field so it's always visible at the top of the card
        stale_banner = (
            f"⚠️ Health monitoring bị gián đoạn {age_str} — "
            "dữ liệu bên dưới có thể không phản ánh thực tế. "
            "Xem logs: `grep 'record_run failed' docker logs data_platform`"
        )
        fields = {"🚨 Cảnh báo hệ thống monitoring": stale_banner, **fields}
        color = "red"  # Override card color to red regardless of asset status

    title = f"ChợPulse BI — Morning Report {_today_ict()}"

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
