"""One-shot backfill for ``ingestion_runs.rows_written``.

Historical rows were persisted with ``rows_written = 0`` because the previous
``extract_rows_written`` implementation could not decode dlt LoadInfo when
items_count was absent (current filesystem / Delta Lake destination does not
populate it). The new implementation resolves row counts by reading the
produced parquet files. This script re-computes every past run's row count
by replaying its persisted ``metadata_json.load_info`` through
``extract_rows_written`` and UPDATEs the row.

Usage::

    DBT_DATA_LAKE_PATH=/path/to/data_lake \
        python scripts/maintenance/backfill_ingestion_health_rows_written.py

Safety:
  * Idempotent — running twice yields the same values.
  * Only updates rows where ``rows_written`` is NULL or 0 (never overwrites
    a non-zero truth).
  * Dry-run via ``--dry-run``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import duckdb

# Project root — script lives at scripts/maintenance/, root is two levels up.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from orchestration.ops.dlt_metrics import extract_rows_written  # noqa: E402
from orchestration.ops.ingestion_health import get_db_path  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would be updated without writing.")
    parser.add_argument("--asset", default=None,
                        help="Limit backfill to a single asset_key (exact match).")
    args = parser.parse_args()

    if not os.environ.get("DBT_DATA_LAKE_PATH"):
        print("ERROR: DBT_DATA_LAKE_PATH is not set. "
              "The parquet fallback cannot resolve file paths without it.",
              file=sys.stderr)
        return 2

    db_path = get_db_path()
    print(f"Health DB: {db_path}")
    print(f"Data lake: {os.environ['DBT_DATA_LAKE_PATH']}")
    if args.dry_run:
        print("Mode: DRY-RUN (no writes)")
    if args.asset:
        print(f"Filter: asset_key = {args.asset}")
    print()

    conn = duckdb.connect(db_path, read_only=args.dry_run)
    try:
        where_clauses = [
            "status IN ('success', 'skipped')",
            "(rows_written IS NULL OR rows_written = 0)",
            "metadata_json IS NOT NULL",
        ]
        params: list = []
        if args.asset:
            where_clauses.append("asset_key = ?")
            params.append(args.asset)

        rows = conn.execute(
            f"""SELECT asset_key, run_id, metadata_json
                FROM ingestion_runs
                WHERE {' AND '.join(where_clauses)}
                ORDER BY run_started_at""",
            params,
        ).fetchall()
        print(f"Candidate rows: {len(rows)}\n")

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
                n = extract_rows_written(load_info)
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
                # Must match on BOTH asset_key and run_id — the primary key is
                # composite because a single Dagster run_id can fan out to
                # multiple assets (daily batch job processes orders + customers
                # + products + accounts + file-drops in the same run_id).
                # Filtering only by run_id would corrupt sibling asset rows.
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
