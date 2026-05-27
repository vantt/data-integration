"""Health DB watchdog sensor — detects silent recorder failures.

Fires every 10 minutes. Sends a Lark alert when:
  1. ingestion_health.db cannot be opened in write mode (filesystem error).
  2. No row has been written for > STALE_THRESHOLD_H hours (record_run silently failing).

Alert is suppressed for ALERT_COOLDOWN_H hours after each send to avoid spam.
Alert distinguishes "db error" (stale + write failed) from "recorder bug" (stale + writable).
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from dagster import SensorEvaluationContext, SkipReason, sensor

from orchestration.ops.ingestion_health import get_db_path, check_writable
import orchestration.ops.ingestion_health  # noqa: F401 — registers sqlite3 adapters/converters
from orchestration.notifications.lark_client import send_lark_card

logger = logging.getLogger("orchestration.health_db_watchdog")

# sapo_webhook_consumer_asset fires every 3 min and always records (success|skipped).
# A gap > 2 hours means record_run() is consistently failing.
STALE_THRESHOLD_H = 2
ALERT_COOLDOWN_H = 4  # alert at most once per 4 hours when stuck
RETENTION_DAYS = 90   # rows older than this are deleted during daily cleanup
CLEANUP_INTERVAL_H = 24


def _fmt_age(hours: float) -> str:
    if hours < 1:
        return f"{int(hours * 60)} phút"
    if hours < 24:
        return f"{hours:.1f} giờ"
    return f"{hours / 24:.1f} ngày"


def _check_staleness(db_path: str) -> tuple[bool, Optional[float]]:
    """Return (is_stale, age_hours). Reads DB — safe during ingestion (SQLite WAL)."""
    conn = None
    try:
        conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        row = conn.execute("SELECT MAX(run_started_at) FROM ingestion_runs").fetchone()
        if not row or row[0] is None:
            return True, None
        last_write = row[0]
        # MAX() returns raw string (not auto-converted by PARSE_DECLTYPES)
        if isinstance(last_write, str):
            dt = datetime.fromisoformat(last_write)
            last_write = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        elif hasattr(last_write, "tzinfo") and last_write.tzinfo is None:
            last_write = last_write.replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - last_write).total_seconds() / 3600
        return age_h > STALE_THRESHOLD_H, age_h
    except Exception as exc:
        logger.warning("watchdog: could not read health DB: %s", exc)
        return True, None  # treat unreadable as stale
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _cleanup_old_rows(db_path: str) -> int:
    """Delete rows older than RETENTION_DAYS. Returns deleted count."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.execute(
            "DELETE FROM ingestion_runs WHERE run_started_at < datetime('now', ?)",
            [f"-{RETENTION_DAYS} days"],
        )
        conn.commit()
        return cur.rowcount
    except Exception as exc:
        logger.warning("watchdog: cleanup failed: %s", exc)
        return 0
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


@sensor(minimum_interval_seconds=600)
def health_db_watchdog_sensor(context: SensorEvaluationContext):
    """Watches ingestion_health.db for filesystem errors and silent recorder failures."""
    db_path = get_db_path()
    now_ts = datetime.now(timezone.utc).timestamp()

    # Load cooldown state from cursor
    cursor_state: dict = {}
    if context.cursor:
        try:
            cursor_state = json.loads(context.cursor)
        except (json.JSONDecodeError, TypeError):
            pass

    # --- Daily cleanup of old rows ---
    last_cleanup_ts: float = cursor_state.get("last_cleanup_ts", 0.0)
    if (now_ts - last_cleanup_ts) >= CLEANUP_INTERVAL_H * 3600:
        deleted = _cleanup_old_rows(db_path)
        if deleted:
            logger.info("watchdog: cleaned up %d rows older than %d days", deleted, RETENTION_DAYS)
        cursor_state["last_cleanup_ts"] = now_ts

    last_alert_ts: float = cursor_state.get("last_alert_ts", 0.0)
    if (now_ts - last_alert_ts) < ALERT_COOLDOWN_H * 3600:
        context.update_cursor(json.dumps(cursor_state))
        return SkipReason(f"Alert cooldown active ({ALERT_COOLDOWN_H}h window)")

    # --- Check 1: staleness (read, safe under WAL) ---
    is_stale, age_h = _check_staleness(db_path)
    if not is_stale:
        context.update_cursor(json.dumps(cursor_state))
        return SkipReason("Health DB is current")

    age_str = _fmt_age(age_h) if age_h is not None else "không rõ"

    # --- Check 2: write mode (only when stale — distinguishes db error vs code bug) ---
    write_ok, write_err = check_writable()

    if not write_ok:
        send_lark_card(
            title="ChợPulse BI — 🚨 Health DB lỗi filesystem",
            color="red",
            fields={
                "Vấn đề": f"ingestion_health.db không mở được write mode (stale {age_str})",
                "Lỗi": f"```{write_err[:250]}```",
                "Ảnh hưởng": "record_run() thất bại hoàn toàn — health monitoring đã dừng",
                "Kiểm tra": "docker exec data_platform ls -la /app/var/data_lake/monitoring/",
            },
        )
    else:
        # Writable but stale — record_run() is likely failing in code
        send_lark_card(
            title="ChợPulse BI — ⚠️ Health DB ngừng ghi",
            color="orange",
            fields={
                "Vấn đề": f"Không có ghi nào trong {age_str} dù DB vẫn mở được",
                "Ảnh hưởng": "record_run() đang thất bại silently — health data không cập nhật",
                "Kiểm tra": "docker logs data_platform | grep 'record_run'",
            },
        )

    cursor_state["last_alert_ts"] = now_ts
    context.update_cursor(json.dumps(cursor_state))
    return SkipReason(f"Alert sent: DB stale {age_str}")
