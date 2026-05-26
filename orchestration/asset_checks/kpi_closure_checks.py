"""Asset checks for KPI closure (Phase 5) — revenue drift thresholds.

Reads last kpi/revenue_daily run from ingestion_health.db and checks:
- drift_pct > 0.5% → ERROR
- drift_pct > 0.1% → WARN
"""
from __future__ import annotations

import logging

from dagster import (
    asset_check,
    AssetCheckResult,
    AssetCheckSeverity,
)

from orchestration.asset_checks.health_db import open_readonly

logger = logging.getLogger(__name__)

# Thresholds (as ratios, not percentages)
_DRIFT_ERROR_THRESHOLD = 0.005  # 0.5%
_DRIFT_WARN_THRESHOLD = 0.001   # 0.1%


def _get_last_kpi_drift() -> tuple[float | None, int | None, str | None]:
    """Return (drift_pct, date_key, status) from the most recent kpi/revenue_daily run.

    Returns (None, None, None) if no data or DB unavailable.
    """
    try:
        with open_readonly() as conn:
            row = conn.execute(
                """
                SELECT
                    CAST(json_extract(metadata_json, '$.drift_pct') AS REAL),
                    CAST(json_extract(metadata_json, '$.date_key') AS INTEGER),
                    status
                FROM ingestion_runs
                WHERE asset_key = 'kpi/revenue_daily'
                ORDER BY run_started_at DESC
                LIMIT 1
                """
            ).fetchone()
        if row:
            return row[0], row[1], row[2]
        return None, None, None
    except Exception as exc:
        logger.warning("kpi_closure_checks: failed to query health DB — %s", exc)
        return None, None, None


# Import the asset for check binding
try:
    from orchestration.assets.kpi_closure import kpi_revenue_daily
except ImportError:
    kpi_revenue_daily = None  # type: ignore[assignment]


if kpi_revenue_daily is not None:
    @asset_check(asset=kpi_revenue_daily, name="revenue_drift_threshold", blocking=False)
    def kpi_revenue_drift_check(context) -> AssetCheckResult:
        """Check that revenue drift between Sapo source and warehouse is within tolerance.

        - ERROR if |drift| > 0.5%
        - WARN if |drift| > 0.1%
        - PASS otherwise
        """
        drift_pct, date_key, status = _get_last_kpi_drift()

        # KPI not enabled or never ran
        if status == "disabled":
            return AssetCheckResult(
                passed=True,
                severity=AssetCheckSeverity.WARN,
                description="KPI closure disabled (KPI_CLOSURE_ENABLED=0)",
                metadata={"status": "disabled"},
            )

        if drift_pct is None:
            # Handle various partial/failure states
            if status == "partial_source":
                desc = "Sapo API unavailable — cannot compute drift"
            elif status == "partial_warehouse":
                desc = "Warehouse query failed — cannot compute drift"
            elif status == "failed":
                desc = "Both source and warehouse unavailable"
            else:
                desc = "No KPI data available — never ran or unknown error"
            return AssetCheckResult(
                passed=True,
                severity=AssetCheckSeverity.WARN,
                description=desc,
                metadata={"date_key": date_key or 0, "status": status or "unknown"},
            )

        abs_drift = abs(drift_pct)
        drift_pct_display = drift_pct * 100

        if abs_drift > _DRIFT_ERROR_THRESHOLD:
            return AssetCheckResult(
                passed=False,
                severity=AssetCheckSeverity.ERROR,
                description=f"Revenue drift {drift_pct_display:+.2f}% exceeds 0.5% threshold (date_key={date_key})",
                metadata={
                    "drift_pct": drift_pct_display,
                    "threshold_pct": _DRIFT_ERROR_THRESHOLD * 100,
                    "date_key": date_key,
                },
            )

        if abs_drift > _DRIFT_WARN_THRESHOLD:
            return AssetCheckResult(
                passed=False,
                severity=AssetCheckSeverity.WARN,
                description=f"Revenue drift {drift_pct_display:+.2f}% exceeds 0.1% threshold (date_key={date_key})",
                metadata={
                    "drift_pct": drift_pct_display,
                    "threshold_pct": _DRIFT_WARN_THRESHOLD * 100,
                    "date_key": date_key,
                },
            )

        return AssetCheckResult(
            passed=True,
            severity=AssetCheckSeverity.WARN,
            description=f"Revenue drift {drift_pct_display:+.2f}% within tolerance (date_key={date_key})",
            metadata={
                "drift_pct": drift_pct_display,
                "date_key": date_key,
            },
        )

    KPI_CHECKS = [kpi_revenue_drift_check]
else:
    KPI_CHECKS = []
