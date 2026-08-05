"""test_worklist_suppression_per_mart.py — plan 260805-1216 phase-05, test matrix W1-W8.

Proves cache_repository.list_all_action_queue() matches crm_action_dismissal on
(party_id, action_type, source_mart) — a customer-level and SKU-level suppression of
the same action_type are independent (the core promise of this feature).
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys
import tempfile
import uuid

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from crm.src.adapters.outbound.sqlite.cache_repository import SQLiteCacheRepository      # noqa: E402
from crm.src.tests.test_action_dismissal_ttl import _insert_action                       # noqa: E402
from crm.src.tests.test_suggestion_settings_service import (                             # noqa: E402
    _make_repos, _link_party, _insert_users, _insert_sku_action,
)


def _make(d: str):
    db, action_state_repo, catalog_repo, cache_conn = _make_repos(d)
    # list_all_action_queue() LEFT JOINs these two — _setup_cache_tables (imported from
    # test_suggestion_settings_service) doesn't create them since its own tests never
    # call list_all_action_queue(). A LEFT JOIN against a genuinely absent table raises
    # OperationalError, which the graceful-empty house rule turns into [] — not a crash,
    # but it would silently make every assertion below pass on an empty set for the
    # wrong reason. Add minimal versions here, local to this file.
    cache_conn.executescript("""
        CREATE TABLE IF NOT EXISTS wh_customer_base (
            customer_key TEXT PRIMARY KEY, customer_id INTEGER, display_name TEXT
        );
        CREATE TABLE IF NOT EXISTS wh_customer_tier (
            customer_key TEXT PRIMARY KEY, strategic_tier TEXT, value_group TEXT, is_contactable INTEGER
        );
    """)
    cache_conn.commit()
    cache_repo = SQLiteCacheRepository(db.conn)
    return db, action_state_repo, cache_repo, cache_conn


def _action_types_in_queue(items) -> set[tuple[str, str]]:
    """(action_type, supply_stream) — supply_stream is NULL for customer-grain rows,
    non-NULL for SKU-grain rows, per cache_repository.py's own discriminator."""
    return {(i.action_type, i.supply_stream) for i in items}


class TestPerMartSuppression:
    def test_w1_suppress_customer_mart_hides_only_customer_row(self):
        with tempfile.TemporaryDirectory() as d:
            db, action_state_repo, cache_repo, cache_conn = _make(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 100)
            _insert_users(db.conn)
            _insert_action(cache_conn, "aq-1", "ck-100", "REORDER_NUDGE", customer_id=100)
            _insert_sku_action(cache_conn, "sa-1", "ck-100", "REORDER_NUDGE", 100)

            action_state_repo.suppress(party_id, "REORDER_NUDGE", "mart_customer_action_queue",
                                        "2099-01-01T00:00:00.000Z", "user-1")

            types = _action_types_in_queue(cache_repo.list_all_action_queue())
            assert ("REORDER_NUDGE", "") not in types       # customer row hidden
            assert any(t == "REORDER_NUDGE" and s != "" for t, s in types)  # SKU row visible
            db.close()

    def test_w2_suppress_sku_mart_hides_only_sku_row(self):
        with tempfile.TemporaryDirectory() as d:
            db, action_state_repo, cache_repo, cache_conn = _make(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 200)
            _insert_users(db.conn)
            _insert_action(cache_conn, "aq-2", "ck-200", "REORDER_NUDGE", customer_id=200)
            _insert_sku_action(cache_conn, "sa-2", "ck-200", "REORDER_NUDGE", 200)

            action_state_repo.suppress(party_id, "REORDER_NUDGE", "mart_customer_sku_action_queue",
                                        "2099-01-01T00:00:00.000Z", "user-1")

            types = _action_types_in_queue(cache_repo.list_all_action_queue())
            assert ("REORDER_NUDGE", "") in types            # customer row visible
            assert not any(t == "REORDER_NUDGE" and s != "" for t, s in types)  # SKU row hidden
            db.close()

    def test_w3_suppress_both_marts_hides_both(self):
        with tempfile.TemporaryDirectory() as d:
            db, action_state_repo, cache_repo, cache_conn = _make(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 300)
            _insert_users(db.conn)
            _insert_action(cache_conn, "aq-3", "ck-300", "REORDER_NUDGE", customer_id=300)
            _insert_sku_action(cache_conn, "sa-3", "ck-300", "REORDER_NUDGE", 300)

            action_state_repo.suppress(party_id, "REORDER_NUDGE", "mart_customer_action_queue",
                                        "2099-01-01T00:00:00.000Z", "user-1")
            action_state_repo.suppress(party_id, "REORDER_NUDGE", "mart_customer_sku_action_queue",
                                        "2099-01-01T00:00:00.000Z", "user-1")

            types = _action_types_in_queue(cache_repo.list_all_action_queue())
            assert all(t != "REORDER_NUDGE" for t, _s in types)
            db.close()

    def test_w4_expired_suppression_reappears(self):
        with tempfile.TemporaryDirectory() as d:
            db, action_state_repo, cache_repo, cache_conn = _make(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 400)
            _insert_users(db.conn)
            _insert_action(cache_conn, "aq-4", "ck-400", "CALL_NOW", customer_id=400)

            action_state_repo.suppress(party_id, "CALL_NOW", "mart_customer_action_queue",
                                        "2020-01-01T00:00:00.000Z", "user-1")  # already expired

            types = _action_types_in_queue(cache_repo.list_all_action_queue())
            assert ("CALL_NOW", "") in types
            db.close()

    def test_w5_suppression_for_different_party_does_not_leak(self):
        with tempfile.TemporaryDirectory() as d:
            db, action_state_repo, cache_repo, cache_conn = _make(d)
            party_a = str(uuid.uuid4())
            party_b = str(uuid.uuid4())
            _link_party(db.conn, party_a, 501)
            _link_party(db.conn, party_b, 502)
            _insert_users(db.conn)
            _insert_action(cache_conn, "aq-5", "ck-502", "CALL_NOW", customer_id=502)

            action_state_repo.suppress(party_a, "CALL_NOW", "mart_customer_action_queue",
                                        "2099-01-01T00:00:00.000Z", "user-1")

            types = _action_types_in_queue(cache_repo.list_all_action_queue())
            assert ("CALL_NOW", "") in types  # party_b's row untouched by party_a's suppression
            db.close()

    def test_w6_fallback_sql_when_sku_table_absent_still_applies_customer_suppression(self):
        with tempfile.TemporaryDirectory() as d:
            db, action_state_repo, cache_repo, cache_conn = _make(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 600)
            _insert_users(db.conn)
            _insert_action(cache_conn, "aq-6", "ck-600", "CALL_NOW", customer_id=600)
            cache_conn.execute("DROP TABLE wh_sku_action_queue")
            cache_conn.commit()

            action_state_repo.suppress(party_id, "CALL_NOW", "mart_customer_action_queue",
                                        "2099-01-01T00:00:00.000Z", "user-1")

            items = cache_repo.list_all_action_queue()
            assert all(i.action_type != "CALL_NOW" for i in items)
            db.close()

    def test_w7_legacy_expanded_rows_hide_both_grains(self):
        """Simulates a pre-0046 dismissal that migration 0046 expanded into 2 rows
        (row-expansion backfill, D2) — both grains must stay hidden."""
        with tempfile.TemporaryDirectory() as d:
            db, action_state_repo, cache_repo, cache_conn = _make(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 700)
            _insert_users(db.conn)
            _insert_action(cache_conn, "aq-7", "ck-700", "REORDER_NUDGE", customer_id=700)
            _insert_sku_action(cache_conn, "sa-7", "ck-700", "REORDER_NUDGE", 700)

            # Simulate the 0046 backfill directly (both mart rows from one legacy dismiss).
            for mart in ("mart_customer_action_queue", "mart_customer_sku_action_queue"):
                db.conn.execute(
                    "INSERT INTO crm_action_dismissal "
                    "  (party_id, action_type, source_mart, dismissed_by_user_id, dismissed_at, dismissed_until) "
                    "VALUES (?, 'REORDER_NUDGE', ?, 'user-1', "
                    "        strftime('%Y-%m-%dT%H:%M:%fZ','now'), '2099-01-01T00:00:00.000Z')",
                    (party_id, mart),
                )
            db.conn.commit()

            types = _action_types_in_queue(cache_repo.list_all_action_queue())
            assert all(t != "REORDER_NUDGE" for t, _s in types)
            db.close()

    def test_w8_fetch_actions_ignores_suppression_d5_pinned(self):
        with tempfile.TemporaryDirectory() as d:
            db, action_state_repo, cache_repo, cache_conn = _make(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 800)
            _insert_users(db.conn)
            _insert_action(cache_conn, "aq-8", "ck-800", "CALL_NOW", customer_id=800)

            action_state_repo.suppress(party_id, "CALL_NOW", "mart_customer_action_queue",
                                        "2099-01-01T00:00:00.000Z", "user-1")

            items = cache_repo._fetch_actions("ck-800")
            assert any(i.action_type == "CALL_NOW" for i in items)
            db.close()
