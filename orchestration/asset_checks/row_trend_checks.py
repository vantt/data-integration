"""Factory for row-volume trend @asset_check functions.

Checks that today's row count is >= trend_min_ratio * median(trailing 7 days).
Skipped (returns passed=True) when:
  - trend_min_ratio is null in YAML (irregular cadence assets)
  - fewer than 7 days of history available (insufficient baseline)
  - asset has no rows in health DB yet
Severity = WARN (not ERROR) — trend deviation is a soft signal.
"""
from __future__ import annotations

import statistics
from typing import Any

from dagster import AssetChecksDefinition, AssetCheckResult, AssetCheckSeverity, asset_check

from orchestration.asset_checks.health_db import open_readonly, rows_by_day, count_zero_row_runs_last_24h
from orchestration.asset_checks.sla_loader import get_sla

# Minimum days of history before trend check fires
_MIN_HISTORY_DAYS = 7


def make_not_empty_check(
    asset_def: Any,
    asset_key_str: str,
) -> AssetChecksDefinition:
    """Build a not_empty_when_expected @asset_check.

    WARN if asset ran in last 24h and every successful run had rows_written=0.
    """
    @asset_check(asset=asset_def, name="not_empty_when_expected", blocking=False)
    def _not_empty_check(context) -> AssetCheckResult:  # noqa: ANN001
        try:
            with open_readonly() as conn:
                total, zero_rows = count_zero_row_runs_last_24h(conn, asset_key_str)
        except Exception as exc:
            return AssetCheckResult(
                passed=False,
                severity=AssetCheckSeverity.WARN,
                description=f"Could not query health DB: {exc}",
            )

        if total == 0:
            return AssetCheckResult(
                passed=True,
                severity=AssetCheckSeverity.WARN,
                description="No successful runs in last 24h — check suppressed.",
                metadata={"runs_last_24h": 0},
            )

        all_empty = zero_rows == total
        return AssetCheckResult(
            passed=not all_empty,
            severity=AssetCheckSeverity.WARN,
            description=(
                f"All {total} runs in last 24h wrote 0 rows."
                if all_empty
                else f"{total - zero_rows}/{total} runs wrote rows in last 24h."
            ),
            metadata={"runs_last_24h": total, "zero_row_runs": zero_rows},
        )

    return _not_empty_check


def make_row_trend_check(
    asset_def: Any,
    asset_key_str: str,
) -> AssetChecksDefinition | None:
    """Build a row_count_within_trend @asset_check, or return None if disabled.

    Returns None when trend_min_ratio is null in YAML (caller must skip None).
    """
    sla = get_sla(asset_key_str)
    trend_min_ratio = sla.get("trend_min_ratio")

    if trend_min_ratio is None:
        return None

    trend_window_days: int = int(sla.get("trend_window_days", 7))

    @asset_check(asset=asset_def, name="row_count_within_trend", blocking=False)
    def _trend_check(context) -> AssetCheckResult:  # noqa: ANN001
        try:
            with open_readonly() as conn:
                # Fetch window+1 days: index 0 = today, rest = baseline
                daily = rows_by_day(conn, asset_key_str, n_days=trend_window_days + 1)
        except Exception as exc:
            return AssetCheckResult(
                passed=False,
                severity=AssetCheckSeverity.WARN,
                description=f"Could not query health DB: {exc}",
            )

        if not daily:
            return AssetCheckResult(
                passed=True,
                severity=AssetCheckSeverity.WARN,
                description="No history yet — trend check suppressed.",
                metadata={"days_available": 0},
            )

        today_rows = daily[0][1]
        baseline = [r for _, r in daily[1:]]  # exclude today from median

        if len(baseline) < _MIN_HISTORY_DAYS:
            return AssetCheckResult(
                passed=True,
                severity=AssetCheckSeverity.WARN,
                description=(
                    f"Insufficient history ({len(baseline)} days, need {_MIN_HISTORY_DAYS}) "
                    "— trend check suppressed."
                ),
                metadata={"days_available": len(baseline), "min_required": _MIN_HISTORY_DAYS},
            )

        median_rows = statistics.median(baseline)
        threshold = median_rows * trend_min_ratio
        passed = today_rows >= threshold or median_rows == 0

        return AssetCheckResult(
            passed=passed,
            severity=AssetCheckSeverity.WARN,
            description=(
                f"Today: {today_rows} rows, "
                f"7-day median: {median_rows:.0f}, "
                f"threshold: {threshold:.0f} ({int(trend_min_ratio * 100)}%)"
            ),
            metadata={
                "today_rows": today_rows,
                "median_7d": float(median_rows),
                "threshold": float(threshold),
                "trend_min_ratio": float(trend_min_ratio),
            },
        )

    return _trend_check
