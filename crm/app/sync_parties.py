"""sync_parties.py — CLI entrypoint replacing Go syncparties binary.

Reads wh_party_seed from cache.db (read-only) and upserts crm_party +
sapo_customer identity rows into crm.db.

Usage:
    python sync_parties.py [--data <dir>]

Environment:
    CRM_DATA_DIR   directory containing crm.db and cache.db (default: ./data)
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

# Ensure crm/app is on the path when run directly from repo root.
sys.path.insert(0, os.path.dirname(__file__))

from adapters.outbound.sqlite.connection import CRMDatabase
from adapters.outbound.sqlite.party_repository import SQLitePartyRepository
from adapters.outbound.sqlite.cache_repository import SQLiteCacheRepository
from application.party_seed_service import PartySeedService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Upsert crm_party rows from wh_party_seed.")
    parser.add_argument(
        "--data",
        default=os.environ.get("CRM_DATA_DIR", "./data"),
        help="Directory containing crm.db and cache.db (default: ./data or $CRM_DATA_DIR)",
    )
    args = parser.parse_args()

    log.info("syncparties: data dir = %s", args.data)

    db = CRMDatabase(args.data)
    try:
        db.apply_migrations()

        party_repo = SQLitePartyRepository(db.conn)
        cache_repo = SQLiteCacheRepository(db.conn)

        svc = PartySeedService(cache_repo, party_repo)
        n = svc.sync_parties(cache_repo)
        print(f"syncparties: {n} parties upserted")
    except Exception as exc:
        log.error("syncparties: %s", exc)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
