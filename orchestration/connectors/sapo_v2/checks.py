"""Connector-specific asset checks of sapo_v2 (listed in ASSET_CHECKS of the package).

capture_coverage: the nightly product capture must hold at least COVERAGE_WARN_RATIO of the
Sapo catalogue total. The asset records `coverage_ratio` and `sapo_total` in the metadata of its
ingestion_health row; this check reads the latest successful run there (the Dagster event log is
purged after a day, ingestion_health keeps 90 days). Severity WARN: the capture is still kept.
"""
from __future__ import annotations

import json

from dagster import AssetCheckResult, AssetCheckSeverity, asset_check

from .assets import ingest_sapo_v2_product_daily_snapshot_asset

SNAPSHOT_ASSET_KEY = "sapo/ingest_sapo_v2_product_daily_snapshot_asset"
# Same threshold as the capture's own WARN log (ingestion/src/sapo/products_daily_snapshot.py).
COVERAGE_WARN_RATIO = 0.98


def _latest_success_metadata(conn) -> tuple[str, dict] | None:
    row = conn.execute(
        """
        SELECT run_started_at, metadata_json
        FROM ingestion_runs
        WHERE asset_key = ? AND status = 'success'
        ORDER BY run_started_at DESC
        LIMIT 1
        """,
        [SNAPSHOT_ASSET_KEY],
    ).fetchone()
    if row is None:
        return None
    try:
        meta = json.loads(row[1]) if row[1] else {}
    except (TypeError, ValueError):
        meta = {}
    return str(row[0]), meta if isinstance(meta, dict) else {}


@asset_check(asset=ingest_sapo_v2_product_daily_snapshot_asset, name="capture_coverage", blocking=False)
def product_daily_snapshot_coverage(context) -> AssetCheckResult:  # noqa: ANN001
    """Latest successful capture holds >= 98% of the Sapo catalogue total."""
    # Imported here: the orchestration.asset_checks package imports every connector at load time.
    from orchestration.asset_checks.health_db import open_readonly

    try:
        with open_readonly() as conn:
            latest = _latest_success_metadata(conn)
    except Exception as exc:
        return AssetCheckResult(
            passed=False,
            severity=AssetCheckSeverity.WARN,
            description=f"Could not query health DB: {exc}",
        )

    if latest is None:
        return AssetCheckResult(
            passed=True,
            severity=AssetCheckSeverity.WARN,
            description="No successful capture recorded yet — check suppressed.",
        )

    run_started_at, meta = latest
    ratio = meta.get("coverage_ratio")
    products = meta.get("products")
    total = meta.get("sapo_total")
    if not isinstance(ratio, (int, float)):
        return AssetCheckResult(
            passed=False,
            severity=AssetCheckSeverity.WARN,
            description=f"Latest capture ({run_started_at}) has no coverage: Sapo reported no catalogue total.",
            metadata={"run_started_at": run_started_at},
        )

    passed = ratio >= COVERAGE_WARN_RATIO
    return AssetCheckResult(
        passed=passed,
        severity=AssetCheckSeverity.WARN,
        description=(
            f"Latest capture ({run_started_at}): {products} of {total} products "
            f"(coverage {ratio:.3f}, threshold {COVERAGE_WARN_RATIO})"
        ),
        metadata={
            "coverage_ratio": float(ratio),
            "threshold": COVERAGE_WARN_RATIO,
            "products": int(products) if isinstance(products, int) else -1,
            "sapo_total": int(total) if isinstance(total, int) else -1,
            "run_started_at": run_started_at,
        },
    )

