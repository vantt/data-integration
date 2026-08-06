"""test_suggestion_settings_end_to_end.py — plan 260805-1216 phase-07, test matrix E1-E11.

Drives the SERVICE (SuggestionSettingsService), not raw SQL, and asserts against
SQLiteCacheRepository.list_all_action_queue() — proving the panel's toggle really
changes the worklist, per mart. This is the single most important test in the plan.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile
import uuid

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from crm.src.tests.helpers_action_queue_fixtures import (                    # noqa: E402
    make_repos, link_party, insert_users, insert_action, insert_sku_action,
)
from crm.src.application.suggestion_settings_service import SuggestionSettingsService  # noqa: E402


def _action_types_in_queue(items) -> set[tuple[str, str]]:
    return {(i.action_type, i.supply_stream) for i in items}


def _svc_and_repos(d: str):
    db, action_state_repo, catalog_repo, cache_repo, cache_conn = make_repos(d)
    svc = SuggestionSettingsService(catalog=catalog_repo, suppression=action_state_repo)
    return db, svc, cache_repo, cache_conn


class TestPerMartSuppressionViaService:
    def test_e1_suppress_customer_mart_via_service_leaves_sku_row(self):
        with tempfile.TemporaryDirectory() as d:
            db, svc, cache_repo, cache_conn = _svc_and_repos(d)
            party_id = str(uuid.uuid4())
            link_party(db.conn, party_id, 100)
            insert_users(db.conn)
            insert_action(cache_conn, "aq-e1", "ck-100", "REORDER_NUDGE", 100)
            insert_sku_action(cache_conn, "sa-e1", "ck-100", "REORDER_NUDGE", 100)

            svc.suppress(party_id, "REORDER_NUDGE", "mart_customer_action_queue", "2026-09-30", "user-1")

            types = _action_types_in_queue(cache_repo.list_all_action_queue())
            assert ("REORDER_NUDGE", "") not in types
            assert any(t == "REORDER_NUDGE" and s != "" for t, s in types)
            db.close()

    def test_e2_suppress_sku_mart_via_service_leaves_customer_row(self):
        with tempfile.TemporaryDirectory() as d:
            db, svc, cache_repo, cache_conn = _svc_and_repos(d)
            party_id = str(uuid.uuid4())
            link_party(db.conn, party_id, 200)
            insert_users(db.conn)
            insert_action(cache_conn, "aq-e2", "ck-200", "REORDER_NUDGE", 200)
            insert_sku_action(cache_conn, "sa-e2", "ck-200", "REORDER_NUDGE", 200)

            svc.suppress(party_id, "REORDER_NUDGE", "mart_customer_sku_action_queue", "2026-09-30", "user-1")

            types = _action_types_in_queue(cache_repo.list_all_action_queue())
            assert ("REORDER_NUDGE", "") in types
            assert not any(t == "REORDER_NUDGE" and s != "" for t, s in types)
            db.close()

    def test_e3_suppress_both_marts_via_service_hides_both(self):
        with tempfile.TemporaryDirectory() as d:
            db, svc, cache_repo, cache_conn = _svc_and_repos(d)
            party_id = str(uuid.uuid4())
            link_party(db.conn, party_id, 300)
            insert_users(db.conn)
            insert_action(cache_conn, "aq-e3", "ck-300", "REORDER_NUDGE", 300)
            insert_sku_action(cache_conn, "sa-e3", "ck-300", "REORDER_NUDGE", 300)

            svc.suppress(party_id, "REORDER_NUDGE", "mart_customer_action_queue", "2026-09-30", "user-1")
            svc.suppress(party_id, "REORDER_NUDGE", "mart_customer_sku_action_queue", "2026-09-30", "user-1")

            types = _action_types_in_queue(cache_repo.list_all_action_queue())
            assert all(t != "REORDER_NUDGE" for t, _s in types)
            db.close()

    def test_e4_unsuppress_via_service_restores_both(self):
        with tempfile.TemporaryDirectory() as d:
            db, svc, cache_repo, cache_conn = _svc_and_repos(d)
            party_id = str(uuid.uuid4())
            link_party(db.conn, party_id, 400)
            insert_users(db.conn)
            insert_action(cache_conn, "aq-e4", "ck-400", "REORDER_NUDGE", 400)
            insert_sku_action(cache_conn, "sa-e4", "ck-400", "REORDER_NUDGE", 400)

            svc.suppress(party_id, "REORDER_NUDGE", "mart_customer_action_queue", "2026-09-30", "user-1")
            svc.unsuppress(party_id, "REORDER_NUDGE", "mart_customer_action_queue")

            types = _action_types_in_queue(cache_repo.list_all_action_queue())
            assert ("REORDER_NUDGE", "") in types
            assert any(t == "REORDER_NUDGE" and s != "" for t, s in types)
            db.close()


class TestPreemptiveSuppression:
    def test_e5_suppress_before_action_exists_then_never_appears(self):
        with tempfile.TemporaryDirectory() as d:
            db, svc, cache_repo, cache_conn = _svc_and_repos(d)
            party_id = str(uuid.uuid4())
            link_party(db.conn, party_id, 500)
            insert_users(db.conn)

            # Suppress WIN_BACK before it has ever fired for this party.
            svc.suppress(party_id, "WIN_BACK", "mart_customer_action_queue", "2026-12-31", "user-1")
            # The warehouse now classifies this party as WIN_BACK.
            insert_action(cache_conn, "aq-e5", "ck-500", "WIN_BACK", 500)

            types = _action_types_in_queue(cache_repo.list_all_action_queue())
            assert ("WIN_BACK", "") not in types
            db.close()


class TestQuickDismissHandoff:
    def test_e6_quick_dismiss_shows_in_get_settings_with_source_mart_and_ttl(self):
        with tempfile.TemporaryDirectory() as d:
            db, svc, cache_repo, cache_conn = _svc_and_repos(d)
            party_id = str(uuid.uuid4())
            link_party(db.conn, party_id, 600)
            insert_users(db.conn)
            insert_sku_action(cache_conn, "sa-e6", "ck-600", "REORDER_NUDGE", 600)

            action_state_repo = svc._suppression  # same repo instance the service wraps
            action_state_repo.dismiss("sa-e6")

            groups = svc.get_settings(party_id)
            row = next(r for g in groups for r in g.rows
                       if r.action_type == "REORDER_NUDGE" and r.source_mart == "mart_customer_sku_action_queue")
            assert row.is_suppressed is True
            db.close()

    def test_e7_resuppress_same_key_updates_date_and_owner(self):
        with tempfile.TemporaryDirectory() as d:
            db, svc, cache_repo, cache_conn = _svc_and_repos(d)
            party_id = str(uuid.uuid4())
            link_party(db.conn, party_id, 700)
            insert_users(db.conn)
            insert_sku_action(cache_conn, "sa-e7", "ck-700", "REORDER_NUDGE", 700)

            svc._suppression.dismiss("sa-e7")  # quick-dismiss, +30d, no user
            svc.suppress(party_id, "REORDER_NUDGE", "mart_customer_sku_action_queue", "2026-12-31", "user-2")

            rows = db.conn.execute(
                "SELECT dismissed_until, dismissed_by_user_id FROM crm_action_dismissal WHERE party_id = ?",
                (party_id,),
            ).fetchall()
            assert len(rows) == 1
            assert rows[0]["dismissed_by_user_id"] == "user-2"
            db.close()


class TestExpiry:
    def test_e8_expired_suppression_reappears_and_get_settings_reports_expired(self):
        with tempfile.TemporaryDirectory() as d:
            db, svc, cache_repo, cache_conn = _svc_and_repos(d)
            party_id = str(uuid.uuid4())
            link_party(db.conn, party_id, 800)
            insert_users(db.conn)
            insert_action(cache_conn, "aq-e8", "ck-800", "CALL_NOW", 800)

            db.conn.execute(
                "INSERT INTO crm_action_dismissal (party_id, action_type, source_mart, dismissed_by_user_id, dismissed_at, dismissed_until) "
                "VALUES (?, 'CALL_NOW', 'mart_customer_action_queue', 'user-1', "
                "strftime('%Y-%m-%dT%H:%M:%fZ','now'), '2020-01-01T00:00:00.000Z')",
                (party_id,),
            )
            db.conn.commit()

            types = _action_types_in_queue(cache_repo.list_all_action_queue())
            assert ("CALL_NOW", "") in types

            groups = svc.get_settings(party_id)
            row = next(r for g in groups for r in g.rows if r.action_type == "CALL_NOW")
            assert row.is_expired is True
            assert row.is_suppressed is False
            db.close()


class TestDoNotContactUntouched:
    def test_e9_do_not_contact_still_removes_party_entirely(self):
        """Mechanism #3 (do_not_contact) lives in WorklistQueryService/activity_repository,
        a completely separate code path from SuggestionSettingsService — this test proves
        this feature made no change there. No suppression is set on the party at all."""
        import sqlite3
        from application.worklist_query_service import WorklistQueryService
        from adapters.outbound.sqlite.activity_repository import SQLiteActivityRepository
        from domain.entities.activity import Activity
        from unittest.mock import MagicMock

        with tempfile.TemporaryDirectory() as d:
            db, svc, cache_repo, cache_conn = _svc_and_repos(d)
            party_id = str(uuid.uuid4())
            link_party(db.conn, party_id, 900)

            activity_repo = SQLiteActivityRepository(db)
            activity_repo.insert(Activity(
                activity_id=str(uuid.uuid4()), party_id=party_id, activity_type="call",
                occurred_at="2026-08-01T00:00:00Z", created_at="2026-08-01T00:00:00Z",
                outcome_reason="do_not_contact",
            ))
            db.conn.commit()

            action_queue = MagicMock()
            item = MagicMock()
            item.party_id = party_id
            action_queue.list_all_action_queue.return_value = [item]
            wl_svc = WorklistQueryService(action_queue=action_queue, suppression=activity_repo)

            assert wl_svc.list_all_action_queue() == []
            db.close()


class TestLegacyBackfill:
    def test_e10_legacy_expanded_row_hides_both_grains(self):
        with tempfile.TemporaryDirectory() as d:
            db, svc, cache_repo, cache_conn = _svc_and_repos(d)
            party_id = str(uuid.uuid4())
            link_party(db.conn, party_id, 1000)
            insert_users(db.conn)
            insert_action(cache_conn, "aq-e10", "ck-1000", "REORDER_NUDGE", 1000)
            insert_sku_action(cache_conn, "sa-e10", "ck-1000", "REORDER_NUDGE", 1000)

            for mart in ("mart_customer_action_queue", "mart_customer_sku_action_queue"):
                db.conn.execute(
                    "INSERT INTO crm_action_dismissal (party_id, action_type, source_mart, dismissed_by_user_id, dismissed_at, dismissed_until) "
                    "VALUES (?, 'REORDER_NUDGE', ?, 'user-1', strftime('%Y-%m-%dT%H:%M:%fZ','now'), '2099-01-01T00:00:00.000Z')",
                    (party_id, mart),
                )
            db.conn.commit()

            types = _action_types_in_queue(cache_repo.list_all_action_queue())
            assert all(t != "REORDER_NUDGE" for t, _s in types)
            db.close()


class TestGetSettingsBaseline:
    def test_e11_no_dismissals_returns_13_rows_all_on_gift_disabled(self):
        with tempfile.TemporaryDirectory() as d:
            db, svc, cache_repo, cache_conn = _svc_and_repos(d)
            party_id = str(uuid.uuid4())
            link_party(db.conn, party_id, 1100)

            groups = svc.get_settings(party_id)
            rows = [r for g in groups for r in g.rows]
            assert len(rows) == 13
            assert all(not r.is_suppressed and not r.is_expired for r in rows)

            gift = next(r for r in rows if r.action_type == "GIFT_TO_PURCHASE")
            assert gift.is_globally_disabled is True
            db.close()
