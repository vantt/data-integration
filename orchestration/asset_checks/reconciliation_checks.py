"""Asset checks for reconciliation drift thresholds (Phase 3).

One check per recon asset. Reads the most recent recon row from
ingestion_health.db and enforces:
  |drift_pct| > 5%  → ERROR
  |drift_pct| > 1%  → WARN
  source_count=None → WARN (live API unavailable, can't measure drift)

# TODO: expose thresholds in orchestration/config/ingestion_sla.yaml once
#       Phase 2 SLA YAML is extended with a 'recon_drift_warn_pct' key.
#       Until then, thresholds are hardcoded constants here.

RECON_CHECKS is exported and registered in definitions.py alongside ALL_CHECKS.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from dagster import (
    AssetCheckResult,
    AssetCheckSeverity,
    AssetChecksDefinition,
    asset_check,
)

from orchestration.asset_checks.health_db import open_readonly
from orchestration.assets.reconciliation import (
    recon_misa_daily,
    recon_sapo_customers_daily,
    recon_sapo_orders_daily,
    recon_shopee_daily,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Drift thresholds
# ---------------------------------------------------------------------------
_WARN_THRESHOLD = 0.01   # |drift_pct| > 1%  → WARN
_ERROR_THRESHOLD = 0.05  # |drift_pct| > 5%  → ERROR


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def _make_drift_check(
    asset_def,
    health_asset_key: str,
) -> AssetChecksDefinition:
    """Return a drift_within_threshold @asset_check for a recon asset.

    Args:
        asset_def: The Dagster asset object the check is attached to.
        health_asset_key: The asset_key string stored in ingestion_health.db
                          (e.g. 'recon/shopee_daily').
    """

    @asset_check(asset=asset_def, name="drift_within_threshold", blocking=False)
    def _check():
        try:
            with open_readonly() as conn:
                row = conn.execute(
                    """
                    SELECT metadata_json
                    FROM ingestion_runs
                    WHERE asset_key = ?
                    ORDER BY run_started_at DESC
                    LIMIT 1
                    """,
                    [health_asset_key],
                ).fetchone()
        except Exception as exc:
            return AssetCheckResult(
                passed=False,
                severity=AssetCheckSeverity.WARN,
                description=f"Could not read health DB: {exc}",
            )

        if row is None:
            return AssetCheckResult(
                passed=True,
                description=f"No recon run recorded yet for {health_asset_key}.",
            )

        raw_json = row[0]
        try:
            meta = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        except Exception as exc:
            return AssetCheckResult(
                passed=False,
                severity=AssetCheckSeverity.WARN,
                description=f"metadata_json parse error: {exc}",
            )

        drift_pct: Optional[float] = meta.get("drift_pct")
        source_count: Optional[int] = meta.get("source_count")
        dest_count: Optional[int] = meta.get("dest_count")

        # Source unknown → can't measure drift (live API disabled or failed)
        if drift_pct is None:
            return AssetCheckResult(
                passed=False,
                severity=AssetCheckSeverity.WARN,
                description=(
                    f"{health_asset_key}: source_count unavailable (live API disabled or error). "
                    f"dest_count={dest_count}. Set RECON_LIVE_API=1 to enable Sapo counts."
                ),
                metadata={
                    "source_count": source_count,
                    "dest_count": dest_count,
                    "drift_pct": None,
                },
            )

        abs_drift = abs(drift_pct)
        description = (
            f"{health_asset_key}: source={source_count} dest={dest_count} "
            f"drift={drift_pct:.4f} ({drift_pct * 100:.2f}%)"
        )

        if abs_drift > _ERROR_THRESHOLD:
            return AssetCheckResult(
                passed=False,
                severity=AssetCheckSeverity.ERROR,
                description=f"DRIFT EXCEEDS 5% — {description}",
                metadata={"drift_pct": drift_pct, "source_count": source_count, "dest_count": dest_count},
            )

        if abs_drift > _WARN_THRESHOLD:
            return AssetCheckResult(
                passed=False,
                severity=AssetCheckSeverity.WARN,
                description=f"Drift > 1% — {description}",
                metadata={"drift_pct": drift_pct, "source_count": source_count, "dest_count": dest_count},
            )

        return AssetCheckResult(
            passed=True,
            description=f"OK — {description}",
            metadata={"drift_pct": drift_pct, "source_count": source_count, "dest_count": dest_count},
        )

    return _check


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

RECON_CHECKS: list[AssetChecksDefinition] = [
    _make_drift_check(recon_shopee_daily,           "recon/shopee_daily"),
    _make_drift_check(recon_misa_daily,             "recon/misa_daily"),
    _make_drift_check(recon_sapo_orders_daily,      "recon/sapo_orders_daily"),
    _make_drift_check(recon_sapo_customers_daily,   "recon/sapo_customers_daily"),
]
