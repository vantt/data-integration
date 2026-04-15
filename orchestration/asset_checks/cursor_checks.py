"""Factory for cursor-stall @asset_check functions (Sapo assets only).

Detects the "silent dropout" pattern: cursor advances (dlt thinks it's
progressing) but rows_written=0 for N consecutive runs. This is the primary
failure mode for incremental Sapo assets.

Returns WARN (not ERROR) — streak alone is ambiguous (API may return empty
legitimately during off-peak hours). Severity escalation is deferred to Phase 4
digest logic.

Gracefully returns passed=True when cursor columns are not yet populated
(Phase 1 instrumentation not yet wired for this asset).
"""
from __future__ import annotations

from typing import Any

from dagster import AssetChecksDefinition, AssetCheckResult, AssetCheckSeverity, asset_check

from orchestration.asset_checks.health_db import open_readonly, consecutive_empty_with_cursor_move
from orchestration.asset_checks.sla_loader import get_sla

# Assets eligible for cursor-stall detection (Sapo incremental/batch only)
CURSOR_CHECK_ASSET_KEYS: frozenset[str] = frozenset(
    {
        "sapo/sapo_webhook_consumer_asset",
        "sapo/sapo_history_log_asset",
        "sapo/sapo_orders_batch_asset",
        "sapo/sapo_customers_batch_asset",
        "sapo/sapo_products_batch_asset",
    }
)


def make_cursor_stall_check(
    asset_def: Any,
    asset_key_str: str,
) -> AssetChecksDefinition | None:
    """Build a cursor_advanced_but_empty @asset_check, or None if asset not eligible.

    Returns None for non-Sapo assets (caller must filter None values).
    """
    if asset_key_str not in CURSOR_CHECK_ASSET_KEYS:
        return None

    sla = get_sla(asset_key_str)
    streak_threshold: int = int(sla.get("cursor_empty_streak", 3))

    @asset_check(asset=asset_def, name="cursor_advanced_but_empty", blocking=False)
    def _cursor_check(context) -> AssetCheckResult:  # noqa: ANN001
        try:
            with open_readonly() as conn:
                streak = consecutive_empty_with_cursor_move(conn, asset_key_str, streak_threshold)
        except Exception as exc:
            return AssetCheckResult(
                passed=False,
                severity=AssetCheckSeverity.WARN,
                description=f"Could not query health DB: {exc}",
            )

        if streak == 0:
            # Either no streak, or cursor columns not yet instrumented (returns 0)
            return AssetCheckResult(
                passed=True,
                severity=AssetCheckSeverity.WARN,
                description=(
                    "No cursor-advance-but-empty streak detected "
                    "(or cursor fields not yet instrumented)."
                ),
                metadata={"streak": 0, "threshold": streak_threshold},
            )

        passed = streak < streak_threshold
        return AssetCheckResult(
            passed=passed,
            severity=AssetCheckSeverity.WARN,
            description=(
                f"Cursor advanced but rows_written=0 for {streak} consecutive runs "
                f"(threshold={streak_threshold})."
            ),
            metadata={"streak": streak, "threshold": streak_threshold},
        )

    return _cursor_check
