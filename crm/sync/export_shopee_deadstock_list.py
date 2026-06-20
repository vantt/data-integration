"""export_shopee_deadstock_list.py — export MASKED_REPEAT dead-stock targets for Shopee Seller Center ops.

Manual workflow (Shopee has no messaging API for marketplace buyers):
  1. Run this script to produce a CSV at app_data/exports/shopee_deadstock_<YYYYMMDD>.csv
  2. Ops opens Shopee Seller Center → Chat Broadcast (up to 2 msg/buyer/week)
     or enables Repeat Buyer Voucher (passive, auto) + Follow Prize.
  3. Estimated coverage: ~280-350 of 433 MASKED_REPEAT via Chat Broadcast over 2 weeks.
  4. CAVEAT: Shopee Chat Broadcast quota based on MY/SG/PH sources — verify VN quota
     before first campaign send.

Output: app_data/exports/ (outside git — PII, never commit).
Excludes holdout rows so ops only contacts the treatment group.

Usage:
    python -m crm.sync.export_shopee_deadstock_list
    python crm/sync/export_shopee_deadstock_list.py [--output-dir PATH] [--cache-db PATH]
"""

from __future__ import annotations

import argparse
import csv
import datetime
import os
import pathlib
import sqlite3
import sys


# Default export dir is app_data/exports/ relative to repo root.
# This path is outside git-tracked directories — PII must not be committed.
_DEFAULT_EXPORT_DIR = str(
    pathlib.Path(__file__).resolve().parent.parent.parent
    / "app_data" / "exports"
)

# Columns to include in the Shopee ops CSV.
# Excludes full_name (PII beyond what ops needs) and internal warehouse keys.
_EXPORT_COLS = [
    "sku",
    "product_name",
    "strategic_tier",
    "buyer_sku_qty",
    "buyer_sku_last_date",
    "next_purchase_signal",
    "target_rank",
    "reason_fragment",
]


def _ensure_export_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _fetch_shopee_targets(cache_conn: sqlite3.Connection) -> list[dict]:
    """Return MASKED_REPEAT rows, excluding holdout, ordered by target_rank."""
    cur = cache_conn.execute(
        """
        SELECT
            sku,
            product_name,
            strategic_tier,
            buyer_sku_qty,
            buyer_sku_last_date,
            next_purchase_signal,
            target_rank,
            reason_fragment
        FROM wh_deadstock_target
        WHERE route_channel = 'SHOPEE_NATIVE'
          AND is_holdout = 0
        ORDER BY target_rank ASC, sku ASC
        """
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def export(cache_db: str, output_dir: str) -> str:
    """Read from cache.db and write CSV. Returns output file path."""
    if not os.path.exists(cache_db):
        raise FileNotFoundError(f"cache.db not found at: {cache_db}")

    _ensure_export_dir(output_dir)

    conn = sqlite3.connect(cache_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = _fetch_shopee_targets(conn)
    finally:
        conn.close()

    if not rows:
        print("No SHOPEE_NATIVE rows in wh_deadstock_target (mart not yet synced?).")
        return ""

    date_tag = datetime.date.today().strftime("%Y%m%d")
    out_path = os.path.join(output_dir, f"shopee_deadstock_{date_tag}.csv")

    with open(out_path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=_EXPORT_COLS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Exported {len(rows)} SHOPEE_NATIVE targets → {out_path}")
    print("NOTE: This file contains PII (buyer affinity). Delete after use.")
    return out_path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export Shopee dead-stock target list for Seller Center ops.")
    p.add_argument(
        "--cache-db",
        default=os.environ.get("CRM_CACHE_DB", "crm/data/cache.db"),
        help="Path to cache.db (default: crm/data/cache.db or CRM_CACHE_DB env var)",
    )
    p.add_argument(
        "--output-dir",
        default=_DEFAULT_EXPORT_DIR,
        help=f"Output directory for CSV (default: {_DEFAULT_EXPORT_DIR})",
    )
    return p.parse_args(argv)


if __name__ == "__main__":
    # Allow running from repo root or from crm/sync/
    repo_root = str(pathlib.Path(__file__).resolve().parent.parent.parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    args = _parse_args()
    out = export(cache_db=args.cache_db, output_dir=args.output_dir)
    sys.exit(0 if out else 1)
