"""hug_qr_print.py — CLI: render a minted batch as printable QR labels (HTML).

Usage:
    python hug_qr_print.py --batch-id B-20260619-...  [--out labels.html] [--data ./data]
    python hug_qr_print.py --latest                    # most recent batch

HTML rendering logic lives in hug.labels (crm/src/hug/labels.py) so it can be
imported by the web UI without a CLI dependency.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

# Ensure crm/src is on sys.path when run directly from crm/ops or the repo root.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from hug import db as hug_db  # noqa: E402
from hug import repository  # noqa: E402
from hug.labels import render_labels_html  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Hug QR labels for a batch.")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--batch-id", help="Batch id to print.")
    g.add_argument("--latest", action="store_true", help="Print the most recent batch.")
    parser.add_argument("--out", default=None, help="Output HTML path (default: hug_labels_<batch>.html).")
    parser.add_argument("--data", default=None, help="Override data dir (else CRM_DATA_DIR / HUG_DB).")
    args = parser.parse_args()

    if args.data:
        os.environ["CRM_DATA_DIR"] = args.data

    conn = hug_db.connect()
    try:
        if args.latest:
            batches = repository.list_recent_batches(conn, limit=1)
            if not batches:
                log.error("no batches found in hug.db")
                sys.exit(1)
            batch_id = batches[0]["batch_id"]
        else:
            batch_id = args.batch_id
        rows = repository.list_batch(conn, batch_id)
    finally:
        conn.close()

    if not rows:
        log.error("batch %s has no tokens", batch_id)
        sys.exit(1)

    tokens = [r["token"] for r in rows]
    # op_type is uniform across a mint batch — read it off the first row.
    op_type = rows[0]["op_type"] if "op_type" in rows[0].keys() else "package_insert"
    out = args.out or f"hug_labels_{batch_id}.html"
    html_doc = render_labels_html(tokens, batch_id, op_type)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html_doc)

    print(f"wrote {len(tokens)} labels for batch {batch_id} -> {out}")
    print("Open it and Ctrl-P -> Save as PDF (or print to a label sheet).")


if __name__ == "__main__":
    main()
