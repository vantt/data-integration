"""helpers_action_queue_fixtures.py — shared cache.db fixture builders for action-queue tests.

Extracted (plan 260805-1216 phase-07) once a 4th test file needed the same synthetic
cache.db shape that test_action_dismissal_ttl.py, test_suggestion_settings_service.py,
and test_worklist_suppression_per_mart.py each built independently. Existing files are
left as-is (already green, low value in a risky migration) — only new tests import this.
"""
from __future__ import annotations

import pathlib
import sqlite3
import uuid

from adapters.outbound.sqlite.connection import CRMDatabase
from adapters.outbound.sqlite.action_state_repository import SQLiteActionStateRepository
from adapters.outbound.sqlite.action_catalog_repository import SQLiteActionCatalogRepository
from adapters.outbound.sqlite.cache_repository import SQLiteCacheRepository

# Mirrors transformation/seeds/seed_action_scenario_registry.csv (13 rows) — kept in sync
# manually; Phase 02's success criterion (7 customer / 6 sku, GIFT_TO_PURCHASE disabled)
# is the fixture-drift guard.
_REGISTRY_ROWS = [
    ("REORDER_OVERDUE", "mart_customer_sku_action_queue", 1, "reorder_cadence", "Het lieu trinh qua han"),
    ("REORDER_NUDGE", "mart_customer_sku_action_queue", 1, "reorder_cadence", "Het lieu trinh hom nay"),
    ("REORDER_PREEMPT", "mart_customer_sku_action_queue", 1, "reorder_cadence", "Sap het lieu trinh"),
    ("PROGRESS_CHECK", "mart_customer_sku_action_queue", 1, "journey", "Hoi cam nhan D12-16"),
    ("USAGE_FOLLOWUP", "mart_customer_sku_action_queue", 1, "journey", "Xac nhan bat dau dung D5-9"),
    ("GIFT_TO_PURCHASE", "mart_customer_sku_action_queue", 0, "gift_conversion", "Tung tang chua tung mua"),
    ("CALL_NOW", "mart_customer_action_queue", 1, "at_risk", "VIP dang nguoi goi ngay"),
    ("MANUAL_RISK_REVIEW", "mart_customer_action_queue", 1, "risk", "NV gan tag rui ro"),
    ("REORDER_NUDGE", "mart_customer_action_queue", 1, "reorder_cadence", "Qua han nhip mua"),
    ("REORDER_PREEMPT", "mart_customer_action_queue", 1, "reorder_cadence", "Sap toi han nhip mua"),
    ("WIN_BACK", "mart_customer_action_queue", 1, "winback", "Da churn can offer"),
    ("SECOND_ORDER", "mart_customer_action_queue", 1, "activation", "Mua 1 lan day don 2"),
    ("HIGH_CANCEL_RISK", "mart_customer_action_queue", 1, "risk", "Ty le huy cao"),
]


def setup_cache_tables(cache_conn: sqlite3.Connection) -> None:
    """Create every wh_* table list_all_action_queue()/SuggestionSettingsService touch."""
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
        CREATE TABLE IF NOT EXISTS wh_customer_base (
            customer_key TEXT PRIMARY KEY, customer_id INTEGER, display_name TEXT
        );
        CREATE TABLE IF NOT EXISTS wh_customer_tier (
            customer_key TEXT PRIMARY KEY, strategic_tier TEXT, value_group TEXT, is_contactable INTEGER
        );
        CREATE TABLE IF NOT EXISTS wh_action_scenario_registry (
            action_type TEXT NOT NULL, mart TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            scenario_group TEXT NOT NULL DEFAULT '',
            description_vi TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (action_type, mart)
        );
    """)
    cache_conn.executemany(
        "INSERT INTO wh_action_scenario_registry VALUES (?, ?, ?, ?, ?)", _REGISTRY_ROWS
    )
    cache_conn.commit()


def insert_action(cache_conn: sqlite3.Connection, action_id: str, customer_key: str,
                   action_type: str, customer_id: int) -> None:
    cache_conn.execute(
        "INSERT INTO wh_action_queue VALUES (?, ?, ?, 'rationale', 1000000, 1, "
        "'2026-08-01', '2026-07-31', '2026-08-01T00:00:00Z', '', '')",
        (action_id, customer_key, action_type),
    )
    cache_conn.execute("INSERT OR IGNORE INTO wh_party_seed (customer_key, customer_id) VALUES (?, ?)",
                        (customer_key, customer_id))
    cache_conn.commit()


def insert_sku_action(cache_conn: sqlite3.Connection, action_id: str, customer_key: str,
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


def link_party(conn: sqlite3.Connection, party_id: str, customer_id: int) -> None:
    conn.execute("INSERT INTO crm_party (party_id, display_name) VALUES (?, ?)",
                 (party_id, f"Party {party_id[:8]}"))
    conn.execute(
        "INSERT INTO crm_party_identity (identity_id, party_id, source_system, identity_type, identity_value) "
        "VALUES (?, ?, 'sapo_v2', 'sapo_customer', ?)",
        (str(uuid.uuid4()), party_id, str(customer_id)),
    )
    conn.commit()


def insert_users(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO crm_app_user (user_id, email, full_name) VALUES "
        "('user-1', 'user1@test.vn', 'Test User 1'), "
        "('user-2', 'user2@test.vn', 'Test User 2')"
    )
    conn.commit()


def make_repos(d: str):
    """Return (db, action_state_repo, catalog_repo, cache_repo, cache_conn)."""
    db = CRMDatabase(d)
    db.apply_migrations()
    cache_path = str(pathlib.Path(d) / "cache.db")
    cache_conn = sqlite3.connect(cache_path)
    cache_conn.row_factory = sqlite3.Row
    setup_cache_tables(cache_conn)
    action_state_repo = SQLiteActionStateRepository(db.conn)
    catalog_repo = SQLiteActionCatalogRepository(db.conn)
    cache_repo = SQLiteCacheRepository(db.conn)
    return db, action_state_repo, catalog_repo, cache_repo, cache_conn
