"""Factory for freshness @asset_check functions.

One check per ingestion asset: last success must be within SLA window.
Severity = ERROR when exceeded (not WARN) — staleness is a hard signal.
Returns WARN (not crash) when no rows exist yet for the asset.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from dagster import AssetChecksDefinition, AssetCheckResult, AssetCheckSeverity, asset_check

from orchestration.asset_checks.health_db import open_readonly, last_success
from orchestration.asset_checks.sla_loader import get_sla


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def make_freshness_check(
    asset_def: Any,
    asset_key_str: str,
) -> AssetChecksDefinition:
    """Build a freshness @asset_check for the given asset.

    Args:
        asset_def: The Dagster asset object (passed to @asset_check(asset=...)).
        asset_key_str: Slash-separated key string matching ingestion_sla.yaml,
                       e.g. "sapo/sapo_orders_batch_asset".
    """
    sla = get_sla(asset_key_str)
    sla_hours: float = sla.get("freshness_hours", 24)

    @asset_check(asset=asset_def, name="freshness", blocking=False)
    def _freshness_check(context) -> AssetCheckResult:  # noqa: ANN001
        try:
            with open_readonly() as conn:
                last = last_success(conn, asset_key_str)
        except Exception as exc:
            return AssetCheckResult(
                passed=False,
                severity=AssetCheckSeverity.WARN,
                description=f"Could not query health DB: {exc}",
            )

        if last is None:
            return AssetCheckResult(
                passed=True,
                severity=AssetCheckSeverity.WARN,
                description="No successful runs recorded yet — check suppressed.",
                metadata={"sla_hours": sla_hours},
            )

        # Ensure both datetimes are timezone-aware for comparison
        now = _now_utc()
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)

        age_hours = (now - last).total_seconds() / 3600
        passed = age_hours <= sla_hours

        return AssetCheckResult(
            passed=passed,
            severity=AssetCheckSeverity.ERROR if not passed else AssetCheckSeverity.WARN,
            description=f"Last success {age_hours:.1f}h ago (SLA={sla_hours}h)",
            metadata={
                "age_hours": float(round(age_hours, 2)),
                "sla_hours": float(sla_hours),
                "last_success_utc": last.isoformat(),
            },
        )

    return _freshness_check
