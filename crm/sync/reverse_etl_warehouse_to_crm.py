"""
reverse_etl_warehouse_to_crm.py — orchestrates the warehouse → cache.db ETL.

Run:
    python -m crm.sync.reverse_etl_warehouse_to_crm

Environment variables (see config.py):
    CRM_OLAP_PATH   path to olap.duckdb  (required in production)
    CRM_CACHE_DB    path to cache.db     (default: crm/data/cache.db)

1-writer rule: this script writes ONLY cache.db.
               Go app writes crm.db.  Never cross-write.

wh_party_seed is populated from distinct (customer_id, customer_key) seen across
dim_customers rows so the Go party-seed consumer can create crm_party records
without Python touching crm.db.

wh_order_hdr uses an incremental high-water mark on date_key so repeated runs
do not full-reload a potentially large orders table.
"""

from __future__ import annotations

import os
import pathlib
import sys
import uuid
from datetime import datetime, timezone


# Allow running as `python -m crm.sync.reverse_etl_warehouse_to_crm` from repo root
# or as a standalone script from crm/sync/.
def _ensure_import_path() -> None:
    repo_root = str(pathlib.Path(__file__).resolve().parent.parent.parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


_ensure_import_path()

from crm.sync.config import cache_db_path, olap_path  # noqa: E402
from crm.sync import duckdb_reader as dr  # noqa: E402
from crm.sync import sqlite_upsert as su  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _run_step(
    cache_conn,
    run_group_id: str,
    source_table: str,
    upsert_fn,
    rows: list[dict],
) -> None:
    """Log + execute a single upsert step, writing a wh_sync_run row."""
    started = _utc_now()
    try:
        count = upsert_fn(cache_conn, rows)
        su.insert_sync_run(cache_conn, {
            "run_id": str(uuid.uuid4()),
            "source_table": source_table,
            "row_count": count,
            "status": "ok",
            "started_at": started,
            "finished_at": _utc_now(),
            "error": None,
        })
        print(f"  [{source_table}] {count} rows upserted  ok")
    except Exception as exc:
        su.insert_sync_run(cache_conn, {
            "run_id": str(uuid.uuid4()),
            "source_table": source_table,
            "row_count": 0,
            "status": "failed",
            "started_at": started,
            "finished_at": _utc_now(),
            "error": str(exc),
        })
        print(f"  [{source_table}] FAILED: {exc}", file=sys.stderr)
        raise


def _build_party_seed_rows(
    customer_base_rows: list[dict],
    utc_now: str,
) -> list[dict]:
    """
    Derive wh_party_seed entries from customer_base rows.
    Each distinct customer_id → one seed row (last customer_key wins on duplicates).
    Quality fields (source_contact_quality, contact_quality) are warehouse-computed
    and written once — ON CONFLICT does not update them (first-write wins).
    """
    # The warehouse customer_id is VARCHAR and may hold a non-numeric sentinel
    # (e.g. 'Unknown' for the guest/unmapped bucket). Such rows cannot seed a
    # crm_party_identity (no real Sapo customer_id) — skip them rather than crash.
    seen: dict[int, dict] = {}
    for row in customer_base_rows:
        cid = row.get("customer_id")
        ckey = row.get("customer_key")
        if cid is None or ckey is None:
            continue
        try:
            cid_int = int(cid)
        except (ValueError, TypeError):
            continue
        seen[cid_int] = {
            "customer_key": str(ckey),
            "source_contact_quality": row.get("source_contact_quality") or "real",
            "contact_quality": row.get("contact_quality") or "real",
        }

    return [
        {
            "customer_id": cid,
            "customer_key": data["customer_key"],
            "seen_at": utc_now,
            "source_contact_quality": data["source_contact_quality"],
            "contact_quality": data["contact_quality"],
        }
        for cid, data in seen.items()
    ]


def run(olap_conn=None, cache_db: str | None = None) -> None:
    """
    Main ETL pipeline.

    olap_conn: optional pre-opened DuckDB connection (used in tests to inject a fixture).
               When None, open_warehouse() is called.
    cache_db:  optional override for the cache.db path.
    """
    cache_path = cache_db or cache_db_path()

    # Ensure parent directory exists.
    os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)

    print(f"reverse-ETL: warehouse → {cache_path}")
    now = _utc_now()

    # ── Open connections ──────────────────────────────────────────────────────
    close_olap = False
    if olap_conn is None:
        olap_conn = dr.open_warehouse()
        close_olap = True

    cache_conn = su.open_cache_db(cache_path)

    try:
        # Apply schema (idempotent — CREATE TABLE IF NOT EXISTS).
        su.apply_schema(cache_conn)

        # ── Incremental high-water mark for order_hdr ─────────────────────────
        hwm = su.get_max_order_date_key(cache_conn)
        if hwm is not None:
            print(f"  [wh_order_hdr] incremental: date_key > {hwm}")

        # ── Read from warehouse ───────────────────────────────────────────────
        print("reading from warehouse …")
        customer_insight_rows   = dr.fetch_customer_insight(olap_conn)
        customer_base_rows      = dr.fetch_customer_base(olap_conn)
        product_insight_rows    = dr.fetch_product_insight(olap_conn)
        action_queue_rows       = dr.fetch_action_queue(olap_conn)
        customer_tier_rows      = dr.fetch_customer_tier(olap_conn)
        product_rows            = dr.fetch_products(olap_conn)
        order_hdr_rows          = dr.fetch_order_hdr(olap_conn, since_date_key=hwm)
        deadstock_target_rows   = dr.fetch_deadstock_targets(olap_conn)

        print("upserting into cache.db …")

        # ── Group 2: insight ──────────────────────────────────────────────────
        _run_step(cache_conn, "batch", "wh_customer_insight",
                  su.upsert_customer_insight, customer_insight_rows)

        _run_step(cache_conn, "batch", "wh_product_insight",
                  su.upsert_product_insight, product_insight_rows)

        _run_step(cache_conn, "batch", "wh_action_queue",
                  su.upsert_action_queue, action_queue_rows)

        _run_step(cache_conn, "batch", "wh_customer_tier",
                  su.upsert_customer_tier, customer_tier_rows)

        # ── Group 3: relational source data ───────────────────────────────────
        _run_step(cache_conn, "batch", "wh_customer_base",
                  su.upsert_customer_base, customer_base_rows)

        _run_step(cache_conn, "batch", "wh_product",
                  su.upsert_product, product_rows)

        _run_step(cache_conn, "batch", "wh_order_hdr",
                  su.upsert_order_hdr, order_hdr_rows)

        # ── Dead-stock targeting engine (separate from NBA customer-state) ──────
        _run_step(cache_conn, "batch", "wh_deadstock_target",
                  su.upsert_deadstock_target, deadstock_target_rows)

        # ── Plumbing: party seed (Go reads this to create crm_party) ─────────
        seed_rows = _build_party_seed_rows(customer_base_rows, now)
        _run_step(cache_conn, "batch", "wh_party_seed",
                  su.upsert_party_seed, seed_rows)

        # Best-effort retention trim: keep last 30 days of audit rows.
        try:
            cache_conn.execute(
                "DELETE FROM wh_sync_run WHERE finished_at < datetime('now','-30 days')"
            )
            cache_conn.commit()
        except Exception as trim_exc:
            print(f"  [wh_sync_run] retention trim failed (non-fatal): {trim_exc}", file=sys.stderr)

        print("reverse-ETL complete.")

    finally:
        cache_conn.close()
        if close_olap:
            olap_conn.close()


if __name__ == "__main__":
    run()
