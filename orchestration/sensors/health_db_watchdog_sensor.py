"""Health DB watchdog sensor — detects ghost locks and silent recorder failures.

Fires every 10 minutes. Sends a Lark alert when:
  1. ingestion_health.duckdb cannot be opened in write mode (ghost lock / OS lock).
  2. No row has been written for > STALE_THRESHOLD_H hours (record_run silently failing).

Alert is suppressed for ALERT_COOLDOWN_H hours after each send to avoid spam.
Alert distinguishes "ghost lock" (stale + write locked) from "recorder bug" (stale + writable).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import duckdb
from dagster import SensorEvaluationContext, SkipReason, sensor

from orchestration.ops.ingestion_health import get_db_path, check_writable
from orchestration.notifications.lark_client import send_lark_card

logger = logging.getLogger("orchestration.health_db_watchdog")

# sapo_webhook_consumer_asset fires every 3 min and always records (success|skipped).
# A gap > 2 hours means record_run() is consistently failing.
STALE_THRESHOLD_H = 2
ALERT_COOLDOWN_H = 4  # alert at most once per 4 hours when stuck


def _fmt_age(hours: float) -> str:
    if hours < 1:
        return f"{int(hours * 60)} phút"
    if hours < 24:
        return f"{hours:.1f} giờ"
    return f"{hours / 24:.1f} ngày"


def _check_staleness(db_path: str) -> tuple[bool, Optional[float]]:
    """Return (is_stale, age_hours). Reads DB in read-only mode — safe during ingestion."""
    try:
        conn = duckdb.connect(db_path, read_only=True)
        row = conn.execute("SELECT MAX(run_started_at) FROM ingestion_runs").fetchone()
        conn.close()
        if not row or row[0] is None:
            return True, None
        last_write = row[0]
        if hasattr(last_write, "tzinfo") and last_write.tzinfo is None:
            last_write = last_write.replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - last_write).total_seconds() / 3600
        return age_h > STALE_THRESHOLD_H, age_h
    except Exception as exc:
        logger.warning("watchdog: could not read health DB: %s", exc)
        return True, None  # treat unreadable as stale


@sensor(minimum_interval_seconds=600)
def health_db_watchdog_sensor(context: SensorEvaluationContext):
    """Watches ingestion_health.duckdb for ghost locks and silent recorder failures."""
    db_path = get_db_path()
    now_ts = datetime.now(timezone.utc).timestamp()

    # Load cooldown state from cursor
    cursor_state: dict = {}
    if context.cursor:
        try:
            cursor_state = json.loads(context.cursor)
        except (json.JSONDecodeError, TypeError):
            pass

    last_alert_ts: float = cursor_state.get("last_alert_ts", 0.0)
    if (now_ts - last_alert_ts) < ALERT_COOLDOWN_H * 3600:
        return SkipReason(f"Alert cooldown active ({ALERT_COOLDOWN_H}h window)")

    # --- Check 1: staleness (read-only, safe) ---
    is_stale, age_h = _check_staleness(db_path)
    if not is_stale:
        return SkipReason("Health DB is current")

    age_str = _fmt_age(age_h) if age_h is not None else "không rõ"

    # --- Check 2: write mode (only when stale — distinguishes ghost lock vs code bug) ---
    write_ok, write_err = check_writable()

    if not write_ok:
        # Ghost lock (or OS lock) — most critical, needs manual intervention
        send_lark_card(
            title="🚨 Health DB bị KHÓA — cần can thiệp thủ công",
            color="red",
            fields={
                "Vấn đề": f"ingestion_health.duckdb không mở được write mode (stale {age_str})",
                "Lỗi": f"```{write_err[:250]}```",
                "Ảnh hưởng": "record_run() thất bại hoàn toàn — health monitoring đã dừng",
                "Cách fix": (
                    "1. Xem process giữ lock: check Task Manager → dllhost.exe\n"
                    "2. Stop data_platform container\n"
                    "3. Kill process giữ lock → mở DB từ host để CHECKPOINT\n"
                    "4. Restart container + xác nhận write hoạt động"
                ),
            },
        )
    else:
        # Writable but stale — record_run() is likely failing in code (not a lock issue)
        send_lark_card(
            title="⚠️ Health DB ngừng ghi — recorder có thể lỗi",
            color="orange",
            fields={
                "Vấn đề": f"Không có ghi nào trong {age_str} dù DB vẫn mở được",
                "Ảnh hưởng": "record_run() đang thất bại silently — health data không cập nhật",
                "Kiểm tra": "docker logs data_platform | grep 'record_run failed'",
            },
        )

    cursor_state["last_alert_ts"] = now_ts
    context.update_cursor(json.dumps(cursor_state))
    return SkipReason(f"Alert sent: DB stale {age_str}")
