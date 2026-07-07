"""tag_acl_sync_service.py — TagAclSyncService: mirror-reconcile crm_party_tag
from wh_customer_base.customer_group_id (cache.db) via the tag ACL tables
(crm_ext_tag / crm_ext_tag_map, migration 0039/0040).

Desired state = wh_customer_base rows with a non-NULL customer_group_id, resolved
through:
  - crm_party_identity (source_system='sapo_v2', identity_type='sapo_customer',
    identity_value=customer_id) -> party_id. NOTE: the phase doc originally specified
    crm_party_external_id (migration 0009) for this lookup, following the same ACL
    pattern doc'd there — but that table is never written by sync_parties.py /
    PartyService.upsert_from_sapo_identity() in practice (verified empirically: a
    live reconcile run against crm_party_external_id skipped 100% of rows as
    "no party"). PartyService instead writes crm_party_identity
    (identity_type='sapo_customer'), so resolution uses that table instead.
  - crm_ext_tag + crm_ext_tag_map (is_active=1, direction IN ('inbound','both')) -> tag_id(s)

Reconcile is a MIRROR for source='sapo_v2_sync' rows only: insert desired pairs
that don't yet exist, delete sync-owned pairs no longer desired. Rows with
source='crm_user' are never read (list_party_tags_by_source filters by source)
and never deleted (bulk_detach_synced always filters source=? in SQL) — a CRM
user's tag always wins over a would-be sync insert (ON CONFLICT DO NOTHING).

See plan 260619-0830-crm-tag-acl-sync/phase-03-inbound-sync.md for the full
algorithm and conflict-rule table.
"""
from __future__ import annotations

import logging
import sqlite3
from collections import defaultdict
from typing import TYPE_CHECKING

from shared.timestamps import utc_now

if TYPE_CHECKING:
    from adapters.outbound.sqlite.connection import CRMDatabase
    from adapters.outbound.sqlite.tag_note_repository import SQLiteTagRepository

log = logging.getLogger(__name__)

SYNC_SOURCE = "sapo_v2_sync"
SOURCE_SYSTEM = "sapo_v2"

# Guard against a broken/empty warehouse feed wiping all synced tags: if the
# desired set resolves to empty while more rows than this are currently
# sync-owned, abort the delete phase entirely instead of reconciling to zero.
ABORT_GUARD_MIN_CURRENT = 5


def _is_missing_table(exc: sqlite3.OperationalError) -> bool:
    return "no such table" in str(exc).lower()


class TagAclSyncService:
    """Mirror-reconciles crm_party_tag(source='sapo_v2_sync') from wh_customer_base."""

    def __init__(self, db: "CRMDatabase", tag_repo: "SQLiteTagRepository") -> None:
        self._db = db
        self._conn = db.conn
        self._tags = tag_repo

    def reconcile(self) -> dict[str, object]:
        """Run one mirror-reconcile pass in a single transaction.

        Returns stats: {inserted, deleted, skipped_no_party, skipped_no_mapping, aborted}.
        """
        desired, skipped_no_party, skipped_no_mapping = self._load_desired()
        current = set(self._tags.list_party_tags_by_source(SYNC_SOURCE))
        desired_pairs = set(desired.keys())

        aborted = False
        if not desired_pairs and len(current) > ABORT_GUARD_MIN_CURRENT:
            log.error(
                "tag_acl_sync: ABORT — desired set is empty but %d rows are currently "
                "source=%r; refusing to delete (broken/empty warehouse feed guard)",
                len(current), SYNC_SOURCE,
            )
            aborted = True
            to_insert_pairs: set[tuple[str, str]] = set()
            to_delete_pairs: set[tuple[str, str]] = set()
        else:
            to_insert_pairs = desired_pairs - current
            to_delete_pairs = current - desired_pairs

        now = utc_now()
        insert_rows = [
            (party_id, tag_id, None, now, desired[(party_id, tag_id)])
            for (party_id, tag_id) in to_insert_pairs
        ]
        delete_pairs = list(to_delete_pairs)

        self._tags.bulk_attach_synced(insert_rows)
        self._tags.bulk_detach_synced(delete_pairs, source=SYNC_SOURCE)
        self._db.commit()

        stats: dict[str, object] = {
            "inserted": len(insert_rows),
            "deleted": len(delete_pairs),
            "skipped_no_party": skipped_no_party,
            "skipped_no_mapping": skipped_no_mapping,
            "aborted": aborted,
        }
        log.info(
            "tag_acl_sync: inserted=%d deleted=%d skipped_no_party=%d skipped_no_mapping=%d aborted=%s",
            stats["inserted"], stats["deleted"], stats["skipped_no_party"],
            stats["skipped_no_mapping"], aborted,
        )
        return stats

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_desired(self) -> tuple[dict[tuple[str, str], str], int, int]:
        """Return {(party_id, tag_id): customer_group_id} plus skip counters."""
        party_by_customer_id = self._load_party_lookup()
        tags_by_group = self._load_tag_mapping()

        try:
            rows = self._conn.execute(
                "SELECT customer_id, customer_group_id FROM cache.wh_customer_base "
                "WHERE customer_group_id IS NOT NULL"
            ).fetchall()
        except sqlite3.OperationalError as exc:
            if _is_missing_table(exc):
                rows = []
            else:
                raise

        desired: dict[tuple[str, str], str] = {}
        skipped_no_party = 0
        skipped_no_mapping = 0
        for row in rows:
            customer_id_str = str(row["customer_id"])
            group_id = row["customer_group_id"]
            party_id = party_by_customer_id.get(customer_id_str)
            if party_id is None:
                skipped_no_party += 1
                continue
            tag_ids = tags_by_group.get(group_id)
            if not tag_ids:
                skipped_no_mapping += 1
                continue
            for tag_id in tag_ids:
                desired[(party_id, tag_id)] = group_id

        return desired, skipped_no_party, skipped_no_mapping

    def _load_party_lookup(self) -> dict[str, str]:
        """Return {identity_value (customer_id as str): party_id} for the sapo_customer identity.

        See module docstring: uses crm_party_identity (what PartyService actually
        writes), not crm_party_external_id.
        """
        rows = self._conn.execute(
            "SELECT identity_value, party_id FROM crm_party_identity "
            "WHERE source_system = ? AND identity_type = 'sapo_customer'",
            (SOURCE_SYSTEM,),
        ).fetchall()
        return {row["identity_value"]: row["party_id"] for row in rows}

    def _load_tag_mapping(self) -> dict[str, list[str]]:
        """Return {ext_key (customer_group_id): [crm_tag_id, ...]} for active inbound mappings."""
        rows = self._conn.execute(
            """
            SELECT et.ext_key, m.crm_tag_id
            FROM crm_ext_tag et
            JOIN crm_ext_tag_map m ON m.ext_tag_id = et.ext_tag_id
            WHERE et.source_system = ? AND m.is_active = 1
              AND m.direction IN ('inbound', 'both')
            """,
            (SOURCE_SYSTEM,),
        ).fetchall()
        mapping: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            mapping[row["ext_key"]].append(row["crm_tag_id"])
        return dict(mapping)
