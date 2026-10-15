"""Nightly full capture of Sapo product prices and stock into sapo_v2_raw/product_daily_snapshot.

Writes one parquet file per run under
    product_daily_snapshot/ingest_method=daily_snapshot/year=<ICT year>/month=<ICT month>/
using the shared filesystem layout of ingestion/.dlt/config.toml. The raw table is history that
cannot be rebuilt: this runner only appends; it has no full-refresh or reset option.
"""
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import dlt  # noqa: E402

from sapo.products_daily_snapshot import (  # noqa: E402
    COVERAGE_WARN_RATIO,
    INGEST_METHOD,
    build_envelopes,
    coverage_ratio,
    ict_partition,
    new_capture_run_id,
    product_daily_snapshot_resource,
    scan_catalogue,
)

PIPELINE_NAME = "sapo_v2_product_daily_snapshot"
DATASET_NAME = "sapo_v2_raw"


@dataclass
class SnapshotRunResult:
    load_info: Any
    captured_at: datetime
    capture_run_id: str
    products: int
    pages: int
    sapo_total: Optional[int]
    duplicates: int
    coverage_ratio: Optional[float]
    warnings: list = field(default_factory=list)


def run(
    client: Any = None,
    captured_at: Optional[datetime] = None,
    pipelines_dir: Optional[str] = None,
) -> SnapshotRunResult:
    """Scan the whole catalogue, then load it as one append-only package.

    `client`, `captured_at` and `pipelines_dir` exist for tests; production passes none of them.
    Raises on any fetch error before dlt is called, so a failed run loads nothing.
    """
    if client is None:
        try:
            from sapo.client import get_sapo_client
        except ImportError:
            from src.sapo.client import get_sapo_client
        client = get_sapo_client()
    captured_at = captured_at or datetime.now(timezone.utc)
    capture_run_id = new_capture_run_id()
    print(f"[>>] Products daily snapshot: captured_at={captured_at.isoformat()} run={capture_run_id}")

    scan = scan_catalogue(client)
    if not scan.products:
        raise RuntimeError("Sapo returned no products; refusing to record an empty capture")

    ratio = coverage_ratio(len(scan.products), scan.sapo_total)
    warnings = []
    if ratio is None:
        warnings.append("Sapo reported no catalogue total; coverage unknown")
    elif ratio < COVERAGE_WARN_RATIO:
        warnings.append(
            f"captured {len(scan.products)} of {scan.sapo_total} products "
            f"(coverage {ratio:.3f} < {COVERAGE_WARN_RATIO})"
        )
    for w in warnings:
        print(f"[WARN] products daily snapshot: {w}")
    print(
        f"[i] Scanned {scan.pages} pages: {len(scan.products)} products "
        f"(Sapo total {scan.sapo_total}, {scan.duplicates} duplicate rows dropped)"
    )

    envelopes = build_envelopes(scan.products, captured_at, capture_run_id)
    destination = dlt.destinations.filesystem(
        extra_placeholders={"ingest_method": INGEST_METHOD, **ict_partition(captured_at)},
    )
    pipeline_kwargs = {"pipelines_dir": pipelines_dir} if pipelines_dir else {}
    pipeline = dlt.pipeline(
        pipeline_name=PIPELINE_NAME,
        destination=destination,
        dataset_name=DATASET_NAME,
        **pipeline_kwargs,
    )
    load_info = pipeline.run(
        product_daily_snapshot_resource(envelopes), loader_file_format="parquet"
    )
    print(load_info)

    return SnapshotRunResult(
        load_info=load_info,
        captured_at=captured_at,
        capture_run_id=capture_run_id,
        products=len(scan.products),
        pages=scan.pages,
        sapo_total=scan.sapo_total,
        duplicates=scan.duplicates,
        coverage_ratio=ratio,
        warnings=warnings,
    )


if __name__ == "__main__":
    run()
