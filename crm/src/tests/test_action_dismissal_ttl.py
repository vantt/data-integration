"""test_action_dismissal_ttl.py — B5 dismiss-TTL keyed by (party_id, action_type).

Integration tests for SQLiteActionStateRepository.dismiss()/list_active_dismissals()
and SQLiteCacheRepository.list_all_action_queue()'s new crm_action_dismissal filter.

Covers (per AI-10/AI-11):
  - dismiss() creates a crm_action_dismissal record keyed by (party_id, action_type)
  - the dismissal survives the warehouse regenerating a NEW action_id for the same
    (customer, action_type) — the actual bug B5 fixes
  - TTL expiry lets the action reappear
  - re-dismiss after expiry works (upsert, fresh TTL)
  - the OLD per-action_id crm_action_state (snooze) path is unaffected
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

from crm.src.adapters.outbound.sqlite.connection import CRMDatabase                    # noqa: E402
from crm.src.adapters.outbound.sqlite.cache_repository import SQLiteCacheRepository     # noqa: E402
from crm.src.adapters.outbound.sqlite.action_state_repository import (                  # noqa: E402
    SQLiteActionStateRepository,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _setup_cache_tables(cache_conn: sqlite3.Connection) -> None:
    """Create minimal cache tables needed by list_all_action_queue (same as
    test_cache_repository_customer_id.py's fixture)."""
    cache_conn.executescript("""
        CREATE TABLE IF NOT EXISTS wh_customer_base (
            customer_key  TEXT PRIMARY KEY,
            customer_id   INTEGER,
            display_name  TEXT
        );

        CREATE TABLE IF NOT EXISTS wh_action_queue (
            action_id          TEXT PRIMARY KEY,
            customer_key       TEXT,
            action_type        TEXT,
            rationale_vi       TEXT,
            value_at_stake_vnd INTEGER,
            priority           INTEGER,
            generated_date     TEXT,
            pending_since      TEXT,
            refreshed_at       TEXT,
            top_affinity_product    TEXT,
            last_purchased_product  TEXT
        );

        CREATE TABLE IF NOT EXISTS wh_party_seed (
            customer_key  TEXT PRIMARY KEY,
            customer_id   INTEGER
        );

        CREATE TABLE IF NOT EXISTS wh_customer_tier (
            customer_key    TEXT PRIMARY KEY,
            customer_id     INTEGER,
            strategic_tier  TEXT,
            value_group     TEXT,
            is_contactable  INTEGER
        );
    """)
    cache_conn.commit()


def _insert_action(cache_conn: sqlite3.Connection, action_id: str, customer_key: str,
                    action_type: str = "CALL_NOW", customer_id: int | None = None) -> None:
    """Insert a wh_action_queue row. When customer_id is given, also inserts the
    matching wh_party_seed row — required for the action's customer_key to
    resolve to a CRM party_id via crm_party_identity (list_all_action_queue's
    join path: wh_action_queue -> wh_party_seed -> crm_party_identity)."""
    cache_conn.execute(
        """
        INSERT INTO wh_action_queue VALUES
        (?, ?, ?, 'Test rationale', 1000000, 1, '2026-06-25', '2026-06-24',
         '2026-06-25T00:00:00Z', '', '')
        """,
        (action_id, customer_key, action_type),
    )
    if customer_id is not None:
        cache_conn.execute(
            "INSERT OR IGNORE INTO wh_party_seed (customer_key, customer_id) VALUES (?, ?)",
            (customer_key, customer_id),
        )
    cache_conn.commit()


def _link_party(conn: sqlite3.Connection, party_id: str, customer_id: int) -> None:
    """Insert crm_party + crm_party_identity so an action's customer_key resolves
    to a CRM party_id (required for dismissal resolution)."""
    conn.execute(
        "INSERT INTO crm_party (party_id, display_name) VALUES (?, ?)",
        (party_id, f"Party {party_id[:8]}"),
    )
    conn.execute(
        """
        INSERT INTO crm_party_identity
            (identity_id, party_id, source_system, identity_type, identity_value)
        VALUES (?, ?, 'sapo_v2', 'sapo_customer', ?)
        """,
        (str(uuid.uuid4()), party_id, str(customer_id)),
    )
    conn.commit()


def _make_repos(d: str):
    """Return (db, cache_repo, action_state_repo, cache_conn) wired against a
    temp data_dir. Caller is responsible for db.close() / cache_conn.close()."""
    db = CRMDatabase(d)
    db.apply_migrations()
    cache_path = str(pathlib.Path(d) / "cache.db")
    cache_conn = sqlite3.connect(cache_path)
    _setup_cache_tables(cache_conn)
    cache_repo = SQLiteCacheRepository(db.conn)
    action_state_repo = SQLiteActionStateRepository(db.conn)
    return db, cache_repo, action_state_repo, cache_conn


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestDismissCreatesDismissalRecord:
    def test_dismiss_writes_crm_action_dismissal_keyed_by_party_and_type(self):
        with tempfile.TemporaryDirectory() as d:
            db, cache_repo, action_state_repo, cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 111)
            _insert_action(cache_conn, "aq-v1", "ck-111", "CALL_NOW", customer_id=111)
            cache_conn.close()

            action_state_repo.dismiss("aq-v1", user_id="00000000-0000-0000-0000-000000000001")

            row = db.conn.execute(
                "SELECT party_id, action_type, dismissed_by_user_id, dismissed_at, dismissed_until "
                "FROM crm_action_dismissal WHERE party_id = ? AND action_type = ?",
                (party_id, "CALL_NOW"),
            ).fetchone()
            db.close()

        assert row is not None
        assert row["party_id"] == party_id
        assert row["action_type"] == "CALL_NOW"
        assert row["dismissed_by_user_id"] == "00000000-0000-0000-0000-000000000001"
        # dismissed_until must be ~30 days after dismissed_at (lexicographic date compare is fine)
        assert row["dismissed_until"][:10] > row["dismissed_at"][:10]

    def test_dismiss_still_writes_legacy_crm_action_state(self):
        """Old per-action_id status write is unchanged — still needed for the
        C360 reason rail (_fetch_actions), which is out of AI-10's scope."""
        with tempfile.TemporaryDirectory() as d:
            db, cache_repo, action_state_repo, cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 222)
            _insert_action(cache_conn, "aq-v2", "ck-222", "WIN_BACK", customer_id=222)
            cache_conn.close()

            action_state_repo.dismiss("aq-v2", user_id=None)

            row = db.conn.execute(
                "SELECT status FROM crm_action_state WHERE action_id = ?", ("aq-v2",)
            ).fetchone()
            db.close()

        assert row is not None
        assert row["status"] == "dismissed"

    def test_dismiss_unresolvable_action_skips_new_table_without_raising(self):
        """action_id not found in cache (already purged / never existed) → dismiss()
        must not raise; the new dismissal table simply gets no row."""
        with tempfile.TemporaryDirectory() as d:
            db, cache_repo, action_state_repo, cache_conn = _make_repos(d)
            cache_conn.close()

            action_state_repo.dismiss("aq-unknown", user_id=None)  # must not raise

            count = db.conn.execute("SELECT COUNT(*) FROM crm_action_dismissal").fetchone()[0]
            legacy = db.conn.execute(
                "SELECT status FROM crm_action_state WHERE action_id = ?", ("aq-unknown",)
            ).fetchone()
            db.close()

        assert count == 0
        assert legacy is not None and legacy["status"] == "dismissed"


class TestDismissalSurvivesActionIdRegeneration:
    def test_dismissed_action_hidden_from_worklist(self):
        with tempfile.TemporaryDirectory() as d:
            db, cache_repo, action_state_repo, cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 333)
            _insert_action(cache_conn, "aq-v1", "ck-333", "CALL_NOW", customer_id=333)

            action_state_repo.dismiss("aq-v1", user_id=None)
            items = cache_repo.list_all_action_queue()
            cache_conn.close()
            db.close()

        assert items == []

    def test_new_action_id_same_party_and_type_still_hidden(self):
        """The actual B5 bug: warehouse regenerates a NEW action_id next week for
        the same (customer, action_type). The old action_id row is gone from
        wh_action_queue and replaced by a new one — the dismissal must still hide
        it because it's keyed by (party_id, action_type), not action_id."""
        with tempfile.TemporaryDirectory() as d:
            db, cache_repo, action_state_repo, cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 444)
            _insert_action(cache_conn, "aq-week1", "ck-444", "CALL_NOW", customer_id=444)

            action_state_repo.dismiss("aq-week1", user_id=None)

            # Simulate the weekly warehouse refresh: old action_id row replaced.
            cache_conn.execute("DELETE FROM wh_action_queue WHERE action_id = ?", ("aq-week1",))
            _insert_action(cache_conn, "aq-week2", "ck-444", "CALL_NOW", customer_id=444)

            items = cache_repo.list_all_action_queue()
            cache_conn.close()
            db.close()

        assert items == [], (
            "action_id churned but (party_id, action_type) dismissal must still hide it"
        )

    def test_different_action_type_same_party_not_hidden(self):
        """Dismissal is scoped to the specific action_type — a different action
        for the same customer must remain visible."""
        with tempfile.TemporaryDirectory() as d:
            db, cache_repo, action_state_repo, cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 555)
            _insert_action(cache_conn, "aq-a", "ck-555", "CALL_NOW", customer_id=555)
            _insert_action(cache_conn, "aq-b", "ck-555", "WIN_BACK", customer_id=555)

            action_state_repo.dismiss("aq-a", user_id=None)

            items = cache_repo.list_all_action_queue()
            cache_conn.close()
            db.close()

        assert len(items) == 1
        assert items[0].action_id == "aq-b"


class TestDismissalTTLExpiry:
    """NOTE on scenario shape: dismiss() intentionally ALSO writes the legacy
    per-episode crm_action_state.status='dismissed' for the dismissed action_id
    (unchanged pre-B5 behavior, still needed for the C360 reason rail) — that
    write has no expiry of its own, so the SAME action_id stays hidden regardless
    of the new table's TTL. The 30-day "reappears normally" guarantee is about
    the (party_id, action_type) semantic action surviving action_id churn — so
    these tests regenerate the action_id (as the warehouse would on its next
    weekly refresh) before checking reappearance, matching the real B5 scenario
    rather than an artificial same-action_id-forever-unrefreshed edge case.
    """

    def test_expired_dismissal_lets_new_action_id_reappear(self):
        with tempfile.TemporaryDirectory() as d:
            db, cache_repo, action_state_repo, cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 666)
            _insert_action(cache_conn, "aq-v1", "ck-666", "CALL_NOW", customer_id=666)

            action_state_repo.dismiss("aq-v1", user_id=None)
            # Warehouse regenerates action_id on its next refresh (weekly, per B5).
            cache_conn.execute("DELETE FROM wh_action_queue WHERE action_id = ?", ("aq-v1",))
            _insert_action(cache_conn, "aq-v2", "ck-666", "CALL_NOW", customer_id=666)
            # Force-expire: set dismissed_until into the past (simulates 30+ days elapsed).
            db.conn.execute(
                "UPDATE crm_action_dismissal SET dismissed_until = '2020-01-01T00:00:00.000Z' "
                "WHERE party_id = ? AND action_type = ?",
                (party_id, "CALL_NOW"),
            )
            db.conn.commit()

            items = cache_repo.list_all_action_queue()
            cache_conn.close()
            db.close()

        assert len(items) == 1
        assert items[0].action_id == "aq-v2"

    def test_redismiss_after_expiry_hides_again_with_fresh_ttl(self):
        with tempfile.TemporaryDirectory() as d:
            db, cache_repo, action_state_repo, cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 777)
            _insert_action(cache_conn, "aq-v1", "ck-777", "CALL_NOW", customer_id=777)

            action_state_repo.dismiss("aq-v1", user_id=None)
            cache_conn.execute("DELETE FROM wh_action_queue WHERE action_id = ?", ("aq-v1",))
            _insert_action(cache_conn, "aq-v2", "ck-777", "CALL_NOW", customer_id=777)
            db.conn.execute(
                "UPDATE crm_action_dismissal SET dismissed_until = '2020-01-01T00:00:00.000Z' "
                "WHERE party_id = ? AND action_type = ?",
                (party_id, "CALL_NOW"),
            )
            db.conn.commit()
            assert len(cache_repo.list_all_action_queue()) == 1  # reappeared as aq-v2

            # Re-dismiss the new action_id (upsert on the same party+type key) —
            # must set a fresh, future dismissed_until.
            action_state_repo.dismiss("aq-v2", user_id=None)
            row = db.conn.execute(
                "SELECT dismissed_until FROM crm_action_dismissal "
                "WHERE party_id = ? AND action_type = ?",
                (party_id, "CALL_NOW"),
            ).fetchone()
            items = cache_repo.list_all_action_queue()
            cache_conn.close()
            db.close()

        assert row["dismissed_until"] > "2020-01-01"
        assert items == []


class TestLegacySnoozeUnaffected:
    def test_snooze_only_writes_crm_action_state_not_dismissal_table(self):
        with tempfile.TemporaryDirectory() as d:
            db, cache_repo, action_state_repo, cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 888)
            _insert_action(cache_conn, "aq-v1", "ck-888", "REORDER_NUDGE", customer_id=888)
            cache_conn.close()

            action_state_repo.snooze("aq-v1", "2099-01-01", user_id=None)

            state_row = db.conn.execute(
                "SELECT status, snoozed_until FROM crm_action_state WHERE action_id = ?",
                ("aq-v1",),
            ).fetchone()
            dismissal_count = db.conn.execute(
                "SELECT COUNT(*) FROM crm_action_dismissal"
            ).fetchone()[0]
            db.close()

        assert state_row is not None
        assert state_row["status"] == "snoozed"
        assert state_row["snoozed_until"] == "2099-01-01"
        assert dismissal_count == 0

    def test_dismiss_then_snooze_different_actions_do_not_interfere(self):
        with tempfile.TemporaryDirectory() as d:
            db, cache_repo, action_state_repo, cache_conn = _make_repos(d)
            party_a = str(uuid.uuid4())
            party_b = str(uuid.uuid4())
            _link_party(db.conn, party_a, 901)
            _link_party(db.conn, party_b, 902)
            _insert_action(cache_conn, "aq-dismiss", "ck-901", "CALL_NOW", customer_id=901)
            _insert_action(cache_conn, "aq-snooze", "ck-902", "CALL_NOW", customer_id=902)

            action_state_repo.dismiss("aq-dismiss", user_id=None)
            action_state_repo.snooze("aq-snooze", "2099-01-01", user_id=None)

            items = cache_repo.list_all_action_queue()
            cache_conn.close()
            db.close()

        # Dismissed action hidden; snoozed-until-future action also hidden (existing
        # snooze filter) — but via completely independent mechanisms/tables.
        assert items == []


class TestResolvePartyId:
    """Phase-03 (260711-1227) IDOR fix: resolve_party_id() is a thin wrapper
    around _resolve_party_and_action_type() — exercised here against the real
    DB-backed cache-join, not a mock, so the actual SQL path (shared with
    dismiss()'s own internal TTL-dismissal write) is verified."""

    def test_resolves_customer_level_action_to_its_party_id(self):
        with tempfile.TemporaryDirectory() as d:
            db, cache_repo, action_state_repo, cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 2001)
            _insert_action(cache_conn, "aq-resolve-1", "ck-2001", "CALL_NOW", customer_id=2001)
            cache_conn.close()

            resolved = action_state_repo.resolve_party_id("aq-resolve-1")
            db.close()

        assert resolved == party_id

    def test_unknown_action_id_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            db, cache_repo, action_state_repo, cache_conn = _make_repos(d)
            cache_conn.close()

            resolved = action_state_repo.resolve_party_id("aq-does-not-exist")
            db.close()

        assert resolved is None

    def test_action_not_yet_linked_to_a_party_returns_none(self):
        """customer_id present in wh_action_queue/wh_party_seed but no
        crm_party_identity row yet (customer not linked to a CRM party) —
        must fail closed, not resolve to a stray/empty value."""
        with tempfile.TemporaryDirectory() as d:
            db, cache_repo, action_state_repo, cache_conn = _make_repos(d)
            _insert_action(cache_conn, "aq-unlinked", "ck-2002", "CALL_NOW", customer_id=2002)
            cache_conn.close()

            resolved = action_state_repo.resolve_party_id("aq-unlinked")
            db.close()

        assert resolved is None


class TestListActiveDismissals:
    def test_list_active_dismissals_returns_enriched_row(self):
        with tempfile.TemporaryDirectory() as d:
            db, cache_repo, action_state_repo, cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            db.conn.execute(
                "INSERT INTO crm_party (party_id, display_name) VALUES (?, ?)",
                (party_id, "Nguyen Van Test"),
            )
            db.conn.execute(
                """
                INSERT INTO crm_party_identity
                    (identity_id, party_id, source_system, identity_type, identity_value)
                VALUES (?, ?, 'sapo_v2', 'sapo_customer', '999')
                """,
                (str(uuid.uuid4()), party_id),
            )
            db.conn.commit()
            _insert_action(cache_conn, "aq-v1", "ck-999", "UPSELL", customer_id=999)
            cache_conn.close()

            action_state_repo.dismiss(
                "aq-v1", user_id="00000000-0000-0000-0000-000000000001"
            )
            dismissals = action_state_repo.list_active_dismissals()
            db.close()

        assert len(dismissals) == 1
        row = dismissals[0]
        assert row.party_id == party_id
        assert row.action_type == "UPSELL"
        assert row.party_display == "Nguyen Van Test"
        assert row.dismissed_by_display == "System Admin"  # seeded admin full_name

    def test_list_active_dismissals_excludes_expired(self):
        with tempfile.TemporaryDirectory() as d:
            db, cache_repo, action_state_repo, cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 1000)
            _insert_action(cache_conn, "aq-v1", "ck-1000", "CROSS_SELL", customer_id=1000)
            cache_conn.close()

            action_state_repo.dismiss("aq-v1", user_id=None)
            db.conn.execute(
                "UPDATE crm_action_dismissal SET dismissed_until = '2020-01-01T00:00:00.000Z' "
                "WHERE party_id = ?",
                (party_id,),
            )
            db.conn.commit()

            dismissals = action_state_repo.list_active_dismissals()
            db.close()

        assert dismissals == []

    def test_party_display_falls_back_to_phone_then_placeholder(self):
        with tempfile.TemporaryDirectory() as d:
            db, cache_repo, action_state_repo, cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            # No display_name — only primary_phone.
            db.conn.execute(
                "INSERT INTO crm_party (party_id, display_name, primary_phone) VALUES (?, NULL, ?)",
                (party_id, "+84900000000"),
            )
            db.conn.execute(
                """
                INSERT INTO crm_party_identity
                    (identity_id, party_id, source_system, identity_type, identity_value)
                VALUES (?, ?, 'sapo_v2', 'sapo_customer', '1001')
                """,
                (str(uuid.uuid4()), party_id),
            )
            db.conn.commit()
            _insert_action(cache_conn, "aq-v1", "ck-1001", "SECOND_ORDER", customer_id=1001)
            cache_conn.close()

            action_state_repo.dismiss("aq-v1", user_id=None)
            dismissals = action_state_repo.list_active_dismissals()
            db.close()

        assert len(dismissals) == 1
        assert dismissals[0].party_display == "+84900000000"
