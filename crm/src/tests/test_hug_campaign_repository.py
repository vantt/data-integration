"""test_hug_campaign_repository.py — unit tests for campaign_repository.py.

Covers:
  - upsert (insert new + update existing)
  - list_campaigns (all + status filter)
  - get_campaign (found + not found)
  - history snapshot written on every upsert
  - archive_campaign (soft-delete + snapshot)
  - restore_snapshot (restores prior row + new snapshot appended)
  - suggest_next_priority
  - validation errors (missing fields, bad campaign_id, bad destination_type)

All tests use an in-memory SQLite connection with the 0024 migration SQL applied
directly — no FastAPI, no CRMDatabase fixture, no subprocess.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import sys

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[3])    # .../data-integration
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])  # .../crm/src
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hug.campaign_repository import (   # noqa: E402
    archive_campaign,
    get_campaign,
    list_campaigns,
    list_history,
    restore_snapshot,
    suggest_next_priority,
    upsert_campaign,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MIGRATION_PATH = (
    pathlib.Path(__file__).parents[3]
    / "crm" / "migrations" / "0024_hug_campaign_authoring.up.sql"
)


@pytest.fixture()
def conn():
    """In-memory SQLite connection with migration 0024 applied."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(_MIGRATION_PATH.read_text(encoding="utf-8"))
    yield c
    c.close()


def _minimal(campaign_id: str = "camp-001", **overrides) -> dict:
    base = {
        "campaign_id": campaign_id,
        "name": "Test Campaign",
        "destination_type": "zalo_oa",
        "destination_url": "https://oa.zalo.me/test",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Migration smoke-test
# ---------------------------------------------------------------------------

def test_migration_creates_tables(conn):
    """Both tables must exist after applying the migration."""
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "crm_hug_campaign" in tables
    assert "crm_hug_campaign_history" in tables


# ---------------------------------------------------------------------------
# upsert — insert
# ---------------------------------------------------------------------------

def test_upsert_insert_returns_saved_row(conn):
    saved = upsert_campaign(conn, _minimal())
    assert saved["campaign_id"] == "camp-001"
    assert saved["name"] == "Test Campaign"
    assert saved["destination_type"] == "zalo_oa"
    assert saved["status"] == "active"
    assert saved["priority"] == 100
    assert saved["targeting"] == "{}"


def test_upsert_insert_with_all_optional_fields(conn):
    row = _minimal(
        "camp-full",
        targeting='{"tier": ["VIP"]}',
        offer_ref="HUG50",
        priority=10,
        schedule_start="2026-07-01T00:00:00Z",
        schedule_end="2026-07-31T23:59:59Z",
        quota_total=500,
        status="paused",
    )
    saved = upsert_campaign(conn, row)
    assert saved["offer_ref"] == "HUG50"
    assert saved["priority"] == 10
    assert saved["quota_total"] == 500
    assert saved["status"] == "paused"
    assert json.loads(saved["targeting"]) == {"tier": ["VIP"]}


# ---------------------------------------------------------------------------
# upsert — update (idempotent round-trip)
# ---------------------------------------------------------------------------

def test_upsert_update_changes_fields(conn):
    upsert_campaign(conn, _minimal())

    updated = upsert_campaign(conn, _minimal(name="Updated Name", priority=50))
    assert updated["name"] == "Updated Name"
    assert updated["priority"] == 50

    # Only one row in main table
    count = conn.execute("SELECT COUNT(*) FROM crm_hug_campaign").fetchone()[0]
    assert count == 1


def test_upsert_update_preserves_created_at(conn):
    first = upsert_campaign(conn, _minimal())
    created_at_first = first["created_at"]

    second = upsert_campaign(conn, _minimal(name="Changed"))
    assert second["created_at"] == created_at_first


def test_upsert_update_refreshes_updated_at(conn):
    first = upsert_campaign(conn, _minimal())
    second = upsert_campaign(conn, _minimal(name="Changed"))
    # updated_at must be >= created_at (may be equal if sub-millisecond)
    assert second["updated_at"] >= first["updated_at"]


# ---------------------------------------------------------------------------
# get_campaign
# ---------------------------------------------------------------------------

def test_get_campaign_returns_row(conn):
    upsert_campaign(conn, _minimal())
    row = get_campaign(conn, "camp-001")
    assert row is not None
    assert row["campaign_id"] == "camp-001"


def test_get_campaign_returns_none_for_missing(conn):
    assert get_campaign(conn, "does-not-exist") is None


# ---------------------------------------------------------------------------
# list_campaigns
# ---------------------------------------------------------------------------

def test_list_campaigns_returns_all_by_priority(conn):
    upsert_campaign(conn, _minimal("c-high", priority=10))
    upsert_campaign(conn, _minimal("c-low", priority=200))
    upsert_campaign(conn, _minimal("c-mid", priority=100))

    rows = list_campaigns(conn)
    assert len(rows) == 3
    assert rows[0]["campaign_id"] == "c-high"
    assert rows[1]["campaign_id"] == "c-mid"
    assert rows[2]["campaign_id"] == "c-low"


def test_list_campaigns_filters_by_status(conn):
    upsert_campaign(conn, _minimal("c-active", status="active"))
    upsert_campaign(conn, _minimal("c-paused", status="paused"))

    active = list_campaigns(conn, status="active")
    assert len(active) == 1
    assert active[0]["campaign_id"] == "c-active"

    paused = list_campaigns(conn, status="paused")
    assert len(paused) == 1
    assert paused[0]["campaign_id"] == "c-paused"


# ---------------------------------------------------------------------------
# History snapshot written on every upsert
# ---------------------------------------------------------------------------

def test_upsert_writes_history_snapshot_on_insert(conn):
    upsert_campaign(conn, _minimal())
    hist = list_history(conn, "camp-001")
    assert len(hist) == 1
    snap = json.loads(hist[0]["snapshot"])
    assert snap["campaign_id"] == "camp-001"
    assert snap["name"] == "Test Campaign"


def test_upsert_writes_history_snapshot_on_each_update(conn):
    upsert_campaign(conn, _minimal())
    upsert_campaign(conn, _minimal(name="V2"))
    upsert_campaign(conn, _minimal(name="V3"))

    hist = list_history(conn, "camp-001")
    assert len(hist) == 3
    # Newest snapshot first
    assert json.loads(hist[0]["snapshot"])["name"] == "V3"
    assert json.loads(hist[1]["snapshot"])["name"] == "V2"
    assert json.loads(hist[2]["snapshot"])["name"] == "Test Campaign"


def test_list_history_limit_is_respected(conn):
    for i in range(5):
        upsert_campaign(conn, _minimal(name=f"Version {i}"))
    hist = list_history(conn, "camp-001", limit=3)
    assert len(hist) == 3


# ---------------------------------------------------------------------------
# archive_campaign
# ---------------------------------------------------------------------------

def test_archive_sets_status_archived(conn):
    upsert_campaign(conn, _minimal())
    archive_campaign(conn, "camp-001")
    row = get_campaign(conn, "camp-001")
    assert row["status"] == "archived"


def test_archive_writes_snapshot(conn):
    upsert_campaign(conn, _minimal())
    archive_campaign(conn, "camp-001")
    hist = list_history(conn, "camp-001")
    # insert snapshot + archive snapshot = 2 entries
    assert len(hist) == 2
    assert json.loads(hist[0]["snapshot"])["status"] == "archived"


# ---------------------------------------------------------------------------
# restore_snapshot
# ---------------------------------------------------------------------------

def test_restore_snapshot_restores_prior_state(conn):
    upsert_campaign(conn, _minimal(targeting='{"tier": ["VIP"]}'))
    upsert_campaign(conn, _minimal(targeting='{"tier": ["CORE"]}', name="V2"))

    hist = list_history(conn, "camp-001")
    # hist[1] is the first snapshot (VIP targeting)
    original_snap_id = hist[-1]["id"]

    restored = restore_snapshot(conn, "camp-001", original_snap_id)
    assert json.loads(restored["targeting"]) == {"tier": ["VIP"]}


def test_restore_snapshot_appends_new_history_entry(conn):
    upsert_campaign(conn, _minimal())                       # snap 1
    upsert_campaign(conn, _minimal(name="V2"))              # snap 2

    hist_before = list_history(conn, "camp-001")
    original_snap_id = hist_before[-1]["id"]

    restore_snapshot(conn, "camp-001", original_snap_id)    # snap 3

    hist_after = list_history(conn, "camp-001")
    assert len(hist_after) == 3


def test_restore_snapshot_raises_for_unknown_snapshot(conn):
    upsert_campaign(conn, _minimal())
    with pytest.raises(KeyError):
        restore_snapshot(conn, "camp-001", 99999)


def test_restore_snapshot_raises_for_wrong_campaign(conn):
    upsert_campaign(conn, _minimal("c-a"))
    upsert_campaign(conn, _minimal("c-b"))
    hist_b = list_history(conn, "c-b")
    snap_id_b = hist_b[0]["id"]
    with pytest.raises(KeyError):
        restore_snapshot(conn, "c-a", snap_id_b)


# ---------------------------------------------------------------------------
# suggest_next_priority
# ---------------------------------------------------------------------------

def test_suggest_next_priority_returns_10_when_empty(conn):
    assert suggest_next_priority(conn) == 10


def test_suggest_next_priority_returns_max_plus_10(conn):
    upsert_campaign(conn, _minimal("c1", priority=50))
    upsert_campaign(conn, _minimal("c2", priority=90))
    assert suggest_next_priority(conn) == 100


def test_suggest_next_priority_ignores_archived(conn):
    upsert_campaign(conn, _minimal("c-live", priority=40))
    upsert_campaign(conn, _minimal("c-dead", priority=999))
    archive_campaign(conn, "c-dead")
    # MAX of active/paused is 40 → suggest 50
    assert suggest_next_priority(conn) == 50


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

def test_upsert_raises_for_missing_required_field(conn):
    with pytest.raises(ValueError, match="missing required field"):
        upsert_campaign(conn, {"campaign_id": "x", "name": "N", "destination_type": "url"})


def test_upsert_raises_for_invalid_campaign_id(conn):
    with pytest.raises(ValueError, match="campaign_id"):
        upsert_campaign(conn, _minimal("bad id with spaces"))


def test_upsert_raises_for_invalid_destination_type(conn):
    with pytest.raises(ValueError, match="destination_type"):
        upsert_campaign(conn, _minimal(destination_type="whatsapp"))


def test_upsert_raises_for_invalid_status(conn):
    with pytest.raises(ValueError, match="status"):
        upsert_campaign(conn, _minimal(status="deleted"))
