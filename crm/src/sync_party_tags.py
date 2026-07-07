"""sync_party_tags.py — CLI entrypoint: mirror-reconcile crm_party_tag from
wh_customer_base.customer_group_id (cache.db, read-only) into crm.db, via the
tag ACL tables (crm_ext_tag / crm_ext_tag_map).

MUST run AFTER sync_parties.py — party identity rows (crm_party_identity,
identity_type='sapo_customer') must already be seeded so customer_id -> party_id
resolution succeeds; unresolved rows are skipped and self-heal on the next run
once the party is seeded.

Usage:
    python sync_party_tags.py [--data <dir>]

Environment:
    CRM_DATA_DIR   directory containing crm.db and cache.db (default: ./data)
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

# Ensure crm/src is on the path when run directly from repo root.
sys.path.insert(0, os.path.dirname(__file__))

from adapters.outbound.sqlite.connection import CRMDatabase
from adapters.outbound.sqlite.tag_note_repository import SQLiteTagRepository
from application.tag_acl_sync_service import TagAclSyncService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mirror-reconcile crm_party_tag from wh_customer_base.customer_group_id."
    )
    parser.add_argument(
        "--data",
        default=os.environ.get("CRM_DATA_DIR", "./data"),
        help="Directory containing crm.db and cache.db (default: ./data or $CRM_DATA_DIR)",
    )
    args = parser.parse_args()

    log.info("sync_party_tags: data dir = %s", args.data)

    db = CRMDatabase(args.data)
    try:
        db.apply_migrations()

        tag_repo = SQLiteTagRepository(db)
        svc = TagAclSyncService(db, tag_repo)
        stats = svc.reconcile()

        print(
            f"sync_party_tags: inserted={stats['inserted']} deleted={stats['deleted']} "
            f"skipped_no_party={stats['skipped_no_party']} skipped_no_mapping={stats['skipped_no_mapping']} "
            f"aborted={stats['aborted']}"
        )
        if stats["aborted"]:
            # Guard tripped — desired set empty while sync-owned rows exist. Surface as a
            # failure so the container log / ops sees it, but crm.db itself was left untouched.
            log.error("sync_party_tags: reconcile aborted by empty-feed guard")
            sys.exit(1)
    except Exception as exc:
        log.error("sync_party_tags: %s", exc)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
