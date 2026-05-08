"""One-shot backfill for ``ingestion_runs.rows_written`` — reusable template.

When you deploy a fix to ``extract_rows_written`` (e.g. add a parquet-based
fallback because dlt's LoadInfo didn't expose item counts), historical rows
keep their wrong value (usually 0 or NULL). Tomorrow's digest is still wrong
until every asset runs again with the new code.

This script replays each historical run's persisted ``metadata_json.load_info``
through the FIXED extractor and UPDATEs in place. Idempotent — re-running
excludes rows already backfilled via the WHERE filter.

Usage:
    DBT_DATA_LAKE_PATH=/path/to/data_lake \\
    INGESTION_HEALTH_DB=/path/to/ingestion_health.duckdb \\
        python backfill-health-rows-written.py --dry-run
    # review, then:
        python backfill-health-rows-written.py

CRITICAL bug to avoid — composite PK:
    ``ingestion_runs`` PK is (asset_key, run_id). Dagster/Airflow share a
    single run_id across sibling assets in one scheduled job. UPDATE that
    filters only on run_id will corrupt all sibling rows. Always filter on
    BOTH columns. This bug cost us 182 corrupted rows on 2026-04-22.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import duckdb

# Wire these two imports to your project's layout
# from orchestration.ops.dlt_metrics import extract_rows_written
# from orchestration.ops.ingestion_health import get_db_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Report without writing.")
    parser.add_argument("--asset", default=None,
                        help="Limit to a single asset_key (exact match).")
    args = parser.parse_args()

    if not os.environ.get("DBT_DATA_LAKE_PATH"):
        print("ERROR: DBT_DATA_LAKE_PATH unset — parquet fallback can't resolve.",
              file=sys.stderr)
        return 2

    db_path = get_db_path()  # noqa: F821 — wire your project's helper
    print(f"Health DB: {db_path}")
    print(f"Data lake: {os.environ['DBT_DATA_LAKE_PATH']}")
    if args.dry_run:
        print("Mode: DRY-RUN (no writes)")
    if args.asset:
        print(f"Filter: asset_key = {args.asset}")

    conn = duckdb.connect(db_path, read_only=args.dry_run)
    try:
        where = [
            "status IN ('success', 'skipped')",
            "(rows_written IS NULL OR rows_written = 0)",
            "metadata_json IS NOT NULL",
        ]
        params: list = []
        if args.asset:
            where.append("asset_key = ?")
            params.append(args.asset)

        rows = conn.execute(
            f"""SELECT asset_key, run_id, metadata_json
                FROM ingestion_runs
                WHERE {' AND '.join(where)}
                ORDER BY run_started_at""",
            params,
        ).fetchall()
        print(f"\nCandidate rows: {len(rows)}\n")

        stats = {"updated": 0, "unchanged_zero": 0, "no_load_info": 0, "errors": 0}
        per_asset: dict[str, int] = {}

        for asset_key, run_id, metadata_json in rows:
            try:
                meta = json.loads(metadata_json) if isinstance(metadata_json, str) else metadata_json
            except Exception as exc:
                print(f"  [parse-error] {asset_key} {run_id[:8]}: {exc}")
                stats["errors"] += 1
                continue

            load_info = (meta or {}).get("load_info")
            if not load_info:
                stats["no_load_info"] += 1
                continue

            try:
                n = extract_rows_written(load_info)  # noqa: F821
            except Exception as exc:
                print(f"  [extract-error] {asset_key} {run_id[:8]}: {exc}")
                stats["errors"] += 1
                continue

            if not n:
                stats["unchanged_zero"] += 1
                continue

            stats["updated"] += 1
            per_asset[asset_key] = per_asset.get(asset_key, 0) + n

            if not args.dry_run:
                # MUST filter BOTH asset_key AND run_id — composite PK.
                # Run_id is shared across sibling assets in one Dagster job.
                conn.execute(
                    "UPDATE ingestion_runs SET rows_written = ? "
                    "WHERE asset_key = ? AND run_id = ?",
                    [int(n), asset_key, run_id],
                )

        print("--- Summary ---")
        for k, v in stats.items():
            print(f"  {k:<16} {v}")
        if per_asset:
            print("\n--- Rows added per asset ---")
            for k, v in sorted(per_asset.items()):
                print(f"  {k:<45} {v:>10,}")
        if args.dry_run and stats["updated"] > 0:
            print("\nRe-run without --dry-run to persist.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
