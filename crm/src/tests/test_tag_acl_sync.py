"""Tests for Phase 03 (260619-0830-crm-tag-acl-sync — inbound sync):

- application.tag_acl_sync_service.TagAclSyncService.reconcile()
- SQLiteTagRepository.list_party_tags_by_source / bulk_attach_synced / bulk_detach_synced
- SQLiteTagRepository.attach_tag() source-upgrade upsert (sync-owned -> crm_user)

Uses the migrated crm.db (crm_ext_tag / crm_ext_tag_map seeded by migration 0040):
  1812239 WHOLESALE -> tag-00000000-0006 (KH Sỉ)
  2421894 US         -> tag-00000000-0007 (KH US giao hộ)
  1812238 RETAIL     -> registered in crm_ext_tag but NO active crm_ext_tag_map row
"""
from __future__ import annotations

import pathlib
import sqlite3
import uuid
from typing import Optional

import pytest

from adapters.outbound.sqlite.tag_note_repository import SQLiteTagRepository
from application.tag_acl_sync_service import TagAclSyncService
from domain.entities.profile import PartyTag

WHOLESALE_GROUP_ID = "1812239"
WHOLESALE_TAG_ID = "tag-00000000-0006"
US_GROUP_ID = "2421894"
US_TAG_ID = "tag-00000000-0007"
RETAIL_GROUP_ID_NO_MAPPING = "1812238"


# ── Fixture helpers ───────────────────────────────────────────────────────────

def _insert_party(db, party_id: str, display_name: str = "Test Party") -> None:
    db.conn.execute(
        "INSERT INTO crm_party (party_id, display_name) VALUES (?, ?)",
        (party_id, display_name),
    )


def _insert_external_id(db, party_id: str, customer_id: int) -> None:
    """Seed the sapo_customer identity row — what PartyService actually writes
    (crm_party_identity), which is what TagAclSyncService resolves party_id from."""
    db.conn.execute(
        "INSERT INTO crm_party_identity "
        "(identity_id, party_id, source_system, identity_type, identity_value) "
        "VALUES (?, ?, 'sapo_v2', 'sapo_customer', ?)",
        (f"ident-{customer_id}", party_id, str(customer_id)),
    )


def _write_wh_customer_base(data_dir: str, rows: list[tuple[int, Optional[str]]]) -> None:
    """rows: (customer_id, customer_group_id). Writes directly to cache.db (mirrors
    how the reverse-ETL pipeline — a separate process — populates this table)."""
    cache_path = str(pathlib.Path(data_dir) / "cache.db")
    conn = sqlite3.connect(cache_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS wh_customer_base ("
            "  customer_id INTEGER PRIMARY KEY,"
            "  customer_group_id TEXT"
            ")"
        )
        conn.executemany(
            "INSERT OR REPLACE INTO wh_customer_base (customer_id, customer_group_id) VALUES (?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def _make_service(db) -> TagAclSyncService:
    return TagAclSyncService(db, SQLiteTagRepository(db))


def _party_tag_row(db, party_id: str, tag_id: str) -> Optional[sqlite3.Row]:
    return db.conn.execute(
        "SELECT source, ext_ref FROM crm_party_tag WHERE party_id = ? AND tag_id = ?",
        (party_id, tag_id),
    ).fetchone()


# ── Case 1: insert new sync-owned tag ─────────────────────────────────────────

class TestReconcileInsertsNewTag:
    def test_wholesale_party_gets_kh_si_tag_with_source_and_ext_ref(self, seeded_crm_db, tmp_data_dir):
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        _insert_external_id(seeded_crm_db, party_id, 5001)
        seeded_crm_db.conn.commit()
        _write_wh_customer_base(tmp_data_dir, [(5001, WHOLESALE_GROUP_ID)])

        stats = _make_service(seeded_crm_db).reconcile()

        assert stats["inserted"] == 1
        assert stats["deleted"] == 0
        row = _party_tag_row(seeded_crm_db, party_id, WHOLESALE_TAG_ID)
        assert row is not None
        assert row["source"] == "sapo_v2_sync"
        assert row["ext_ref"] == WHOLESALE_GROUP_ID


# ── Case 2: party changes group — old sync tag deleted, new one inserted ─────

class TestReconcileGroupChange:
    def test_group_change_deletes_old_tag_and_inserts_new(self, seeded_crm_db, tmp_data_dir):
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        _insert_external_id(seeded_crm_db, party_id, 5002)
        seeded_crm_db.conn.commit()
        _write_wh_customer_base(tmp_data_dir, [(5002, WHOLESALE_GROUP_ID)])

        svc = _make_service(seeded_crm_db)
        svc.reconcile()
        assert _party_tag_row(seeded_crm_db, party_id, WHOLESALE_TAG_ID) is not None

        # Customer moves from WHOLESALE to US in Sapo.
        _write_wh_customer_base(tmp_data_dir, [(5002, US_GROUP_ID)])
        stats = svc.reconcile()

        assert stats["inserted"] == 1
        assert stats["deleted"] == 1
        assert _party_tag_row(seeded_crm_db, party_id, WHOLESALE_TAG_ID) is None
        new_row = _party_tag_row(seeded_crm_db, party_id, US_TAG_ID)
        assert new_row is not None
        assert new_row["source"] == "sapo_v2_sync"
        assert new_row["ext_ref"] == US_GROUP_ID


# ── Case 3: crm_user row on the same pair survives untouched ─────────────────

class TestReconcileDoesNotOverwriteCrmUserRow:
    def test_crm_user_row_not_overwritten_or_deleted(self, seeded_crm_db, tmp_data_dir):
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        _insert_external_id(seeded_crm_db, party_id, 5003)
        # A CRM user already manually assigned the same tag before sync ever ran.
        # tagged_by NULL — crm_app_user FK not needed to exercise this behaviour.
        seeded_crm_db.conn.execute(
            "INSERT INTO crm_party_tag (party_id, tag_id, tagged_by, tagged_at, source) "
            "VALUES (?, ?, NULL, '2026-01-01T00:00:00.000Z', 'crm_user')",
            (party_id, WHOLESALE_TAG_ID),
        )
        seeded_crm_db.conn.commit()
        _write_wh_customer_base(tmp_data_dir, [(5003, WHOLESALE_GROUP_ID)])

        svc = _make_service(seeded_crm_db)
        stats = svc.reconcile()
        row = _party_tag_row(seeded_crm_db, party_id, WHOLESALE_TAG_ID)
        assert row is not None
        assert row["source"] == "crm_user"

        # Second run is likewise a no-op against this pair — never deleted.
        svc.reconcile()
        row2 = _party_tag_row(seeded_crm_db, party_id, WHOLESALE_TAG_ID)
        assert row2 is not None
        assert row2["source"] == "crm_user"


# ── Case 4: attach_tag upgrades a sync-owned tag to crm_user ─────────────────

class TestAttachTagUpgradesSyncOwnedRow:
    def test_manual_attach_upgrades_source_and_survives_next_reconcile(self, seeded_crm_db, tmp_data_dir):
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        _insert_external_id(seeded_crm_db, party_id, 5004)
        seeded_crm_db.conn.commit()
        _write_wh_customer_base(tmp_data_dir, [(5004, WHOLESALE_GROUP_ID)])

        svc = _make_service(seeded_crm_db)
        svc.reconcile()
        assert _party_tag_row(seeded_crm_db, party_id, WHOLESALE_TAG_ID)["source"] == "sapo_v2_sync"

        # A staff member manually (re-)assigns the same tag from the UI.
        # tagged_by NULL — crm_app_user FK not needed to exercise this behaviour.
        repo = SQLiteTagRepository(seeded_crm_db)
        repo.attach_tag(PartyTag(
            party_id=party_id,
            tag_id=WHOLESALE_TAG_ID,
            name="KH Sỉ",
            tagged_at="2026-02-01T00:00:00.000Z",
            tagged_by=None,
            source="crm_user",
        ))
        seeded_crm_db.conn.commit()
        row = _party_tag_row(seeded_crm_db, party_id, WHOLESALE_TAG_ID)
        assert row["source"] == "crm_user"

        # Customer drops out of the warehouse feed entirely (group cleared).
        _write_wh_customer_base(tmp_data_dir, [(5004, None)])
        stats = svc.reconcile()

        assert stats["deleted"] == 0
        row_after = _party_tag_row(seeded_crm_db, party_id, WHOLESALE_TAG_ID)
        assert row_after is not None
        assert row_after["source"] == "crm_user"


# ── Case 5: skip unseeded party / unmapped group — no error, stats counted ───

class TestReconcileSkipsUnresolvedRows:
    def test_skips_no_party_and_no_mapping_without_raising(self, seeded_crm_db, tmp_data_dir):
        # customer 5005: has a group but was never seeded into crm_party_identity.
        # customer 5006: seeded, but its group (RETAIL) has no active crm_ext_tag_map row.
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        _insert_external_id(seeded_crm_db, party_id, 5006)
        seeded_crm_db.conn.commit()
        _write_wh_customer_base(tmp_data_dir, [
            (5005, WHOLESALE_GROUP_ID),
            (5006, RETAIL_GROUP_ID_NO_MAPPING),
        ])

        stats = _make_service(seeded_crm_db).reconcile()

        assert stats["inserted"] == 0
        assert stats["deleted"] == 0
        assert stats["skipped_no_party"] == 1
        assert stats["skipped_no_mapping"] == 1
        assert stats["aborted"] is False


# ── Idempotency ───────────────────────────────────────────────────────────────

class TestReconcileIsIdempotent:
    def test_second_run_with_no_input_change_is_a_noop(self, seeded_crm_db, tmp_data_dir):
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        _insert_external_id(seeded_crm_db, party_id, 5007)
        seeded_crm_db.conn.commit()
        _write_wh_customer_base(tmp_data_dir, [(5007, WHOLESALE_GROUP_ID)])

        svc = _make_service(seeded_crm_db)
        first = svc.reconcile()
        second = svc.reconcile()

        assert first["inserted"] == 1
        assert second["inserted"] == 0
        assert second["deleted"] == 0


# ── Guard: empty desired set + many current rows aborts the delete phase ────

class TestReconcileEmptyFeedGuard:
    def test_aborts_delete_when_feed_is_empty_but_many_rows_are_synced(self, seeded_crm_db, tmp_data_dir):
        # Seed > ABORT_GUARD_MIN_CURRENT (5) sync-owned rows directly, then present
        # an empty wh_customer_base (simulates a broken/empty warehouse feed).
        for i in range(6):
            party_id = str(uuid.uuid4())
            _insert_party(seeded_crm_db, party_id, f"Party {i}")
            seeded_crm_db.conn.execute(
                "INSERT INTO crm_party_tag (party_id, tag_id, tagged_at, source) "
                "VALUES (?, ?, '2026-01-01T00:00:00.000Z', 'sapo_v2_sync')",
                (party_id, WHOLESALE_TAG_ID),
            )
        seeded_crm_db.conn.commit()
        _write_wh_customer_base(tmp_data_dir, [])  # empty feed, no rows at all

        stats = _make_service(seeded_crm_db).reconcile()

        assert stats["aborted"] is True
        assert stats["deleted"] == 0
        remaining = seeded_crm_db.conn.execute(
            "SELECT COUNT(*) AS n FROM crm_party_tag WHERE source = 'sapo_v2_sync'"
        ).fetchone()["n"]
        assert remaining == 6
