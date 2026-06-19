"""hug_mint.py — CLI to pre-print a batch of Hug tokens into hug.db.

Generates N unique random-12 Crockford-base32 tokens, inserts them as
status='printed' under a shared batch_id, and prints the batch summary. The
hug.db UNIQUE index is the single registry — no token is ever printed before it
is recorded, so batches never collide across prints.

Usage:
    python hug_mint.py --count 20 [--op-type package_insert] [--batch-id B-...] [--data ./data]

Environment:
    CRM_DATA_DIR   directory containing the SQLite files (default: ./data)
    HUG_DB         explicit hug.db path (overrides CRM_DATA_DIR)
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone

# Ensure crm/src is on sys.path when run directly from repo root or crm/src.
sys.path.insert(0, os.path.dirname(__file__))

from hug import config as hug_config  # noqa: E402
from hug import db as hug_db  # noqa: E402
from hug import repository  # noqa: E402
from hug.tokens import human_code  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger(__name__)


def _default_batch_id() -> str:
    return "B-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-print a batch of Hug tokens.")
    parser.add_argument("--count", type=int, required=True, help="Number of tokens to mint.")
    parser.add_argument(
        "--op-type",
        default="package_insert",
        help="op_type stamped on every token in the batch (default: package_insert).",
    )
    parser.add_argument(
        "--batch-id",
        default=None,
        help="Batch id (default: B-<UTC timestamp>).",
    )
    parser.add_argument(
        "--data",
        default=None,
        help="Override data dir (else CRM_DATA_DIR / HUG_DB).",
    )
    args = parser.parse_args()

    if args.count <= 0:
        log.error("--count must be >= 1")
        sys.exit(2)

    if args.data:
        os.environ["CRM_DATA_DIR"] = args.data

    db_path = hug_config.hug_db_path()
    batch_id = args.batch_id or _default_batch_id()
    log.info("mint: hug.db=%s batch=%s count=%d op_type=%s", db_path, batch_id, args.count, args.op_type)

    conn = hug_db.connect(db_path)
    try:
        tokens = repository.mint_batch(
            conn, args.count, batch_id=batch_id, op_type=args.op_type
        )
    finally:
        conn.close()

    print(f"minted {len(tokens)} tokens · batch_id={batch_id} · op_type={args.op_type}")
    for t in tokens:
        print(f"  {t}  {human_code(t)}  {hug_config.scan_url(t)}")
    print(f"\nNext: python hug_qr_print.py --batch-id {batch_id}")


if __name__ == "__main__":
    main()
