"""test_suggestion_settings_service.py — plan 260805-1216 phase-04, test matrix U2-U12.

U1 (customer-level dismiss -> source_mart) is already covered by
test_action_dismissal_ttl.py::TestDismissCreatesDismissalRecord. This file covers:
  U2  dismiss() on a SKU-level action -> source_mart='mart_customer_sku_action_queue'
  U3  dismiss() on SKU REORDER_NUDGE does NOT create a customer-level row (D4)
  U4  suppress() with no matching action anywhere in cache -> pre-emptive, no exception
  U5  suppress() twice, different dates -> 1 row, latest call wins
  U6  unsuppress() -> row gone
  U7  list_dismissals_for_party -> includes expired rows; other parties excluded
  U8  list_active_dismissals -> source_mart populated
  U9  catalog repo when wh_action_scenario_registry absent -> [], no raise
  U10 service.suppress() with an (action_type, mart) pair absent from the catalog -> ValueError
  U11 service.suppress() on a globally-disabled type -> ValueError
  U12 date conversion: future/past/beyond-horizon
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from crm.src.adapters.outbound.sqlite.connection import CRMDatabase                     # noqa: E402
from crm.src.adapters.outbound.sqlite.action_state_repository import (                   # noqa: E402
    SQLiteActionStateRepository,
)
from crm.src.adapters.outbound.sqlite.action_catalog_repository import (                 # noqa: E402
    SQLiteActionCatalogRepository,
)
from crm.src.application.suggestion_settings_service import (                            # noqa: E402
    SuggestionSettingsService, _until_date_ict_to_utc,
)


def _setup_cache_tables(cache_conn: sqlite3.Connection) -> None:
    cache_conn.executescript("""
        CREATE TABLE IF NOT EXISTS wh_action_queue (
            action_id TEXT PRIMARY KEY, customer_key TEXT, action_type TEXT,
            rationale_vi TEXT, value_at_stake_vnd INTEGER, priority INTEGER,
            generated_date TEXT, pending_since TEXT, refreshed_at TEXT,
            top_affinity_product TEXT, last_purchased_product TEXT
        );
        CREATE TABLE IF NOT EXISTS wh_sku_action_queue (
            action_id TEXT PRIMARY KEY, customer_key TEXT, sku TEXT,
            product_display_name TEXT, action_type TEXT, rationale_vi TEXT,
            days_until_depletion INTEGER, estimated_depletion_date TEXT,
            priority INTEGER, pending_since TEXT, generated_date TEXT,
            last_purchase_date TEXT, last_order_code TEXT,
            last_sku_discount_rate REAL, last_net_unit_price INTEGER,
            supply_stream TEXT, refreshed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS wh_party_seed (
            customer_key TEXT PRIMARY KEY, customer_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS wh_action_scenario_registry (
            action_type TEXT NOT NULL, mart TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            scenario_group TEXT NOT NULL DEFAULT '',
            description_vi TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (action_type, mart)
        );
    """)
    cache_conn.execute(
        "INSERT INTO wh_action_scenario_registry VALUES "
        "('CALL_NOW', 'mart_customer_action_queue', 1, 'at_risk', 'VIP dang nguoi goi ngay'),"
        "('REORDER_NUDGE', 'mart_customer_sku_action_queue', 1, 'reorder_cadence', 'Het lieu trinh hom nay'),"
        "('REORDER_NUDGE', 'mart_customer_action_queue', 1, 'reorder_cadence', 'Qua han nhip mua'),"
        "('GIFT_TO_PURCHASE', 'mart_customer_sku_action_queue', 0, 'gift_conversion', 'Tung tang chua tung mua')"
    )
    cache_conn.commit()


def _link_party(conn: sqlite3.Connection, party_id: str, customer_id: int) -> None:
    conn.execute("INSERT INTO crm_party (party_id, display_name) VALUES (?, ?)",
                 (party_id, f"Party {party_id[:8]}"))
    conn.execute(
        "INSERT INTO crm_party_identity (identity_id, party_id, source_system, identity_type, identity_value) "
        "VALUES (?, ?, 'sapo_v2', 'sapo_customer', ?)",
        (str(uuid.uuid4()), party_id, str(customer_id)),
    )
    conn.commit()


def _insert_users(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO crm_app_user (user_id, email, full_name) VALUES "
        "('user-1', 'user1@test.vn', 'Test User 1'), "
        "('user-2', 'user2@test.vn', 'Test User 2')"
    )
    conn.commit()


def _insert_sku_action(cache_conn: sqlite3.Connection, action_id: str, customer_key: str,
                        action_type: str, customer_id: int) -> None:
    cache_conn.execute(
        "INSERT INTO wh_sku_action_queue VALUES (?, ?, 'SKU-A', 'Product A', ?, "
        "'rationale', 5, '2026-08-10', 1, '2026-08-01', '2026-08-01T00:00:00Z', "
        "NULL, NULL, NULL, NULL, 'purchased', '2026-08-01T00:00:00Z')",
        (action_id, customer_key, action_type),
    )
    cache_conn.execute("INSERT OR IGNORE INTO wh_party_seed (customer_key, customer_id) VALUES (?, ?)",
                        (customer_key, customer_id))
    cache_conn.commit()


def _make_repos(d: str):
    db = CRMDatabase(d)
    db.apply_migrations()
    cache_path = str(pathlib.Path(d) / "cache.db")
    cache_conn = sqlite3.connect(cache_path)
    _setup_cache_tables(cache_conn)
    action_state_repo = SQLiteActionStateRepository(db.conn)
    catalog_repo = SQLiteActionCatalogRepository(db.conn)
    return db, action_state_repo, catalog_repo, cache_conn


# ── U2, U3: mart-aware dismiss ────────────────────────────────────────────────

class TestMartAwareDismiss:
    def test_u2_dismiss_sku_action_records_sku_mart(self):
        with tempfile.TemporaryDirectory() as d:
            db, action_state_repo, _, cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 222)
            _insert_sku_action(cache_conn, "sa-v1", "ck-222", "REORDER_NUDGE", 222)

            action_state_repo.dismiss("sa-v1")

            row = db.conn.execute(
                "SELECT source_mart FROM crm_action_dismissal WHERE party_id = ?", (party_id,)
            ).fetchone()
            assert row["source_mart"] == "mart_customer_sku_action_queue"
            db.close()

    def test_u3_sku_dismiss_does_not_hide_customer_level_same_type(self):
        """D4 behaviour change: dismissing SKU REORDER_NUDGE no longer creates a row
        for (mart_customer_action_queue, REORDER_NUDGE) — intended, pinned here."""
        with tempfile.TemporaryDirectory() as d:
            db, action_state_repo, _, cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 333)
            _insert_sku_action(cache_conn, "sa-v2", "ck-333", "REORDER_NUDGE", 333)

            action_state_repo.dismiss("sa-v2")

            row = db.conn.execute(
                "SELECT * FROM crm_action_dismissal WHERE party_id = ? AND source_mart = 'mart_customer_action_queue'",
                (party_id,),
            ).fetchone()
            assert row is None
            db.close()


# ── U4-U6: direct suppress/unsuppress ────────────────────────────────────────

class TestDirectSuppress:
    def test_u4_suppress_with_no_active_action_is_preemptive(self):
        with tempfile.TemporaryDirectory() as d:
            db, action_state_repo, _, _cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 444)
            _insert_users(db.conn)

            until = _until_date_ict_to_utc("2026-12-31")
            action_state_repo.suppress(party_id, "CALL_NOW", "mart_customer_action_queue", until, "user-1")

            row = db.conn.execute(
                "SELECT dismissed_until FROM crm_action_dismissal WHERE party_id = ?", (party_id,)
            ).fetchone()
            assert row["dismissed_until"] == until
            db.close()

    def test_u5_resuppress_overwrites_date_and_user(self):
        with tempfile.TemporaryDirectory() as d:
            db, action_state_repo, _, _cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 555)
            _insert_users(db.conn)

            action_state_repo.suppress(party_id, "CALL_NOW", "mart_customer_action_queue",
                                        _until_date_ict_to_utc("2026-09-01"), "user-1")
            later = _until_date_ict_to_utc("2026-12-31")
            action_state_repo.suppress(party_id, "CALL_NOW", "mart_customer_action_queue",
                                        later, "user-2")

            rows = db.conn.execute(
                "SELECT dismissed_until, dismissed_by_user_id FROM crm_action_dismissal WHERE party_id = ?",
                (party_id,),
            ).fetchall()
            assert len(rows) == 1
            assert rows[0]["dismissed_until"] == later
            assert rows[0]["dismissed_by_user_id"] == "user-2"
            db.close()

    def test_u6_unsuppress_deletes_row(self):
        with tempfile.TemporaryDirectory() as d:
            db, action_state_repo, _, _cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 666)
            _insert_users(db.conn)

            action_state_repo.suppress(party_id, "CALL_NOW", "mart_customer_action_queue",
                                        _until_date_ict_to_utc("2026-12-31"), "user-1")
            action_state_repo.unsuppress(party_id, "CALL_NOW", "mart_customer_action_queue")

            row = db.conn.execute(
                "SELECT * FROM crm_action_dismissal WHERE party_id = ?", (party_id,)
            ).fetchone()
            assert row is None
            db.close()


# ── U7, U8: list reads ───────────────────────────────────────────────────────

class TestListReads:
    def test_u7_list_dismissals_for_party_includes_expired_and_excludes_others(self):
        with tempfile.TemporaryDirectory() as d:
            db, action_state_repo, _, _cache_conn = _make_repos(d)
            party_a = str(uuid.uuid4())
            party_b = str(uuid.uuid4())
            _link_party(db.conn, party_a, 771)
            _link_party(db.conn, party_b, 772)
            _insert_users(db.conn)

            past = "2020-01-01T00:00:00.000Z"  # already expired
            db.conn.execute(
                "INSERT INTO crm_action_dismissal (party_id, action_type, source_mart, dismissed_until) "
                "VALUES (?, 'CALL_NOW', 'mart_customer_action_queue', ?)", (party_a, past),
            )
            action_state_repo.suppress(party_b, "CALL_NOW", "mart_customer_action_queue",
                                        _until_date_ict_to_utc("2026-12-31"), "user-1")
            db.conn.commit()

            rows = action_state_repo.list_dismissals_for_party(party_a)
            assert len(rows) == 1
            assert rows[0].dismissed_until == past
            db.close()

    def test_u8_list_active_dismissals_has_source_mart(self):
        with tempfile.TemporaryDirectory() as d:
            db, action_state_repo, _, _cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 881)
            _insert_users(db.conn)
            action_state_repo.suppress(party_id, "CALL_NOW", "mart_customer_action_queue",
                                        _until_date_ict_to_utc("2026-12-31"), "user-1")

            rows = action_state_repo.list_active_dismissals()
            assert rows[0].source_mart == "mart_customer_action_queue"
            db.close()


# ── U9: catalog repo graceful-empty ───────────────────────────────────────────

class TestCatalogRepoGracefulEmpty:
    def test_u9_missing_table_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as d:
            db = CRMDatabase(d)
            db.apply_migrations()
            # No cache.db schema applied at all -> wh_action_scenario_registry absent.
            catalog_repo = SQLiteActionCatalogRepository(db.conn)
            assert catalog_repo.list_catalog() == []
            db.close()


# ── U10, U11: service-level validation ───────────────────────────────────────

class TestServiceValidation:
    def test_u10_unknown_action_type_mart_pair_raises(self):
        with tempfile.TemporaryDirectory() as d:
            db, action_state_repo, catalog_repo, _cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 1010)
            service = SuggestionSettingsService(catalog_repo, action_state_repo)

            with pytest.raises(ValueError):
                service.suppress(party_id, "NOT_A_REAL_TYPE", "mart_customer_action_queue",
                                  "2026-12-31", "user-1")

            assert db.conn.execute("SELECT COUNT(*) c FROM crm_action_dismissal").fetchone()["c"] == 0
            db.close()

    def test_u11_globally_disabled_type_raises(self):
        with tempfile.TemporaryDirectory() as d:
            db, action_state_repo, catalog_repo, _cache_conn = _make_repos(d)
            party_id = str(uuid.uuid4())
            _link_party(db.conn, party_id, 1111)
            service = SuggestionSettingsService(catalog_repo, action_state_repo)

            with pytest.raises(ValueError):
                service.suppress(party_id, "GIFT_TO_PURCHASE", "mart_customer_sku_action_queue",
                                  "2026-12-31", "user-1")
            db.close()


# ── U12: date conversion ──────────────────────────────────────────────────────

class TestDateConversion:
    def test_u12_future_date_converts_to_end_of_day_ict_in_utc(self):
        until_utc = _until_date_ict_to_utc("2026-12-31")
        dt = datetime.strptime(until_utc, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        # 23:59:59.999 ICT (UTC+7) on 2026-12-31 == 16:59:59.999 UTC same day.
        assert dt.strftime("%Y-%m-%d %H:%M:%S") == "2026-12-31 16:59:59"
        assert dt > datetime.now(timezone.utc)

    def test_u12_past_date_rejected(self):
        with pytest.raises(ValueError):
            _until_date_ict_to_utc("2020-01-01")

    def test_u12_beyond_one_year_horizon_rejected(self):
        far_future = (datetime.now(timezone.utc) + timedelta(days=400)).strftime("%Y-%m-%d")
        with pytest.raises(ValueError):
            _until_date_ict_to_utc(far_future)
