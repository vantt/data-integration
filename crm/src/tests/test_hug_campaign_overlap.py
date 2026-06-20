"""test_hug_campaign_overlap.py — unit tests for campaign_overlap.py.

Coverage matrix:

  Overlap (targeting_can_overlap):
    O01  both empty {} → True  (DEFAULT overlaps DEFAULT)
    O02  list attr disjoint → False
    O03  list attr intersecting → True
    O04  recency_days interval overlap → True
    O05  recency_days interval disjoint → False
    O06  one side unconstrained (absent key) → True
    O07  multi-attr: both must pass (AND semantics)
    O08  op_type list disjoint + tier matching → False (AND across attrs)
    O09  op_type list matching + tier disjoint → False

  Find overlaps (find_overlapping_campaigns):
    F01  no active campaigns → empty list
    F02  overlapping active campaign is returned
    F03  disjoint active campaign is NOT returned
    F04  exclude_id skips the campaign being edited (self-overlap)
    F05  paused/archived campaigns are not included

  Shadow direction (priority comparison):
    S01  other priority < new → shadows_new would be True (other wins)
         (shadow direction computed in render layer; tested via priority values)
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import sys

import pytest

# ── sys.path bootstrap ────────────────────────────────────────────────────────

_REPO_ROOT   = str(pathlib.Path(__file__).parents[3])   # .../data-integration
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])   # .../crm/src
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hug.campaign_overlap import (  # noqa: E402
    _list_overlaps,
    _range_overlaps,
    targeting_can_overlap,
    find_overlapping_campaigns,
)

# ── Migration fixture ─────────────────────────────────────────────────────────

_MIGRATION_PATH = (
    pathlib.Path(__file__).parents[3]
    / "crm" / "migrations" / "0024_hug_campaign_authoring.up.sql"
)


@pytest.fixture()
def crm_conn():
    """In-memory crm.db with the campaign table migration applied."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(_MIGRATION_PATH.read_text(encoding="utf-8"))
    yield c
    c.close()


def _insert_campaign(conn: sqlite3.Connection, *, campaign_id: str, targeting: dict,
                     priority: int = 100, status: str = "active") -> None:
    """Insert a minimal campaign row directly (bypasses upsert validation for speed)."""
    conn.execute(
        """
        INSERT INTO crm_hug_campaign
            (campaign_id, name, targeting, destination_type, destination_url,
             priority, status, created_at, updated_at)
        VALUES (?, ?, ?, 'url', 'https://example.com', ?, ?, datetime('now'), datetime('now'))
        """,
        (campaign_id, f"Test {campaign_id}", json.dumps(targeting), priority, status),
    )
    conn.commit()


# ── _list_overlaps primitive ──────────────────────────────────────────────────

def test_list_overlaps_shared_value():
    assert _list_overlaps(["VIP", "CORE"], ["CORE", "CASUAL"]) is True


def test_list_overlaps_no_shared_value():
    assert _list_overlaps(["VIP"], ["CORE"]) is False


def test_list_overlaps_int_string_coercion():
    """is_contactable: int 1 and string '1' must be treated as the same value."""
    assert _list_overlaps([1], ["1"]) is True
    assert _list_overlaps([0], [1]) is False


# ── _range_overlaps primitive ─────────────────────────────────────────────────

def test_range_overlaps_inclusive_touching():
    """[0,30] and [30,60] share the point 30 → overlap."""
    assert _range_overlaps({"lte": 30}, {"gte": 30}) is True


def test_range_overlaps_no_overlap():
    """[0,20] and [30,60] are disjoint → False."""
    assert _range_overlaps({"lte": 20}, {"gte": 30}) is False


def test_range_overlaps_one_sided_interval():
    """[gte:30] (30..∞) and [lte:60] (0..60) overlap in [30,60]."""
    assert _range_overlaps({"gte": 30}, {"lte": 60}) is True


def test_range_overlaps_no_bound_both_universe():
    """Both rules unbounded (i.e. both {} when called here) → always overlap."""
    assert _range_overlaps({}, {}) is True


# ── targeting_can_overlap core cases ─────────────────────────────────────────

def test_overlap_both_empty_is_true():
    """O01: {} overlaps {} — both DEFAULT campaigns always overlap."""
    assert targeting_can_overlap({}, {}) is True


def test_overlap_list_attr_disjoint_is_false():
    """O02: tier VIP vs CORE — disjoint sets → no overlap."""
    assert targeting_can_overlap({"tier": ["VIP"]}, {"tier": ["CORE"]}) is False


def test_overlap_list_attr_intersecting_is_true():
    """O03: tier [VIP, CORE] vs [CORE] — CORE in common → overlap."""
    assert targeting_can_overlap({"tier": ["VIP", "CORE"]}, {"tier": ["CORE"]}) is True


def test_overlap_recency_days_overlap_is_true():
    """O04: recency [gte:30] vs [lte:60] → [30,60] non-empty → True."""
    assert targeting_can_overlap(
        {"recency_days": {"gte": 30}},
        {"recency_days": {"lte": 60}},
    ) is True


def test_overlap_recency_days_disjoint_is_false():
    """O05: recency [gte:30] vs [lte:20] → empty intersection → False."""
    assert targeting_can_overlap(
        {"recency_days": {"gte": 30}},
        {"recency_days": {"lte": 20}},
    ) is False


def test_overlap_one_side_unconstrained_is_true():
    """O06: tier VIP on one side, other has no tier key → True (universe)."""
    assert targeting_can_overlap({"tier": ["VIP"]}, {}) is True
    assert targeting_can_overlap({}, {"tier": ["VIP"]}) is True


def test_overlap_multi_attr_and_semantics_all_must_pass():
    """O07: tier matches but recency disjoint → False (AND across attrs)."""
    assert targeting_can_overlap(
        {"tier": ["VIP"], "recency_days": {"gte": 30}},
        {"tier": ["VIP"], "recency_days": {"lte": 20}},
    ) is False


def test_overlap_op_type_disjoint_plus_tier_match_is_false():
    """O08: op_type disjoint → overall False despite tier match."""
    assert targeting_can_overlap(
        {"tier": ["VIP"], "op_type": ["package_insert"]},
        {"tier": ["VIP"], "op_type": ["loyalty_card"]},
    ) is False


def test_overlap_op_type_match_plus_tier_disjoint_is_false():
    """O09: tier disjoint → overall False despite op_type match."""
    assert targeting_can_overlap(
        {"tier": ["VIP"], "op_type": ["package_insert"]},
        {"tier": ["CORE"], "op_type": ["package_insert"]},
    ) is False


# ── find_overlapping_campaigns ────────────────────────────────────────────────

def test_find_overlaps_no_campaigns(crm_conn):
    """F01: no campaigns in DB → empty list."""
    result = find_overlapping_campaigns(crm_conn, {})
    assert result == []


def test_find_overlaps_returns_overlapping_campaign(crm_conn):
    """F02: an active campaign that overlaps new targeting is returned."""
    _insert_campaign(crm_conn, campaign_id="camp-a", targeting={"tier": ["VIP"]}, priority=10)
    result = find_overlapping_campaigns(crm_conn, {"tier": ["VIP"]})
    assert len(result) == 1
    assert result[0]["campaign_id"] == "camp-a"
    assert result[0]["priority"] == 10


def test_find_overlaps_does_not_return_disjoint_campaign(crm_conn):
    """F03: a campaign with non-overlapping targeting is excluded."""
    _insert_campaign(crm_conn, campaign_id="camp-b", targeting={"tier": ["CORE"]}, priority=20)
    result = find_overlapping_campaigns(crm_conn, {"tier": ["VIP"]})
    assert result == []


def test_find_overlaps_skips_exclude_id(crm_conn):
    """F04: the campaign being edited must not flag itself as an overlap."""
    _insert_campaign(crm_conn, campaign_id="self-camp", targeting={"tier": ["VIP"]}, priority=10)
    result = find_overlapping_campaigns(crm_conn, {"tier": ["VIP"]}, exclude_id="self-camp")
    assert result == []


def test_find_overlaps_ignores_non_active_campaigns(crm_conn):
    """F05: paused and archived campaigns are not checked for overlap."""
    _insert_campaign(crm_conn, campaign_id="paused-c", targeting={}, priority=5, status="paused")
    _insert_campaign(crm_conn, campaign_id="archived-d", targeting={}, priority=6, status="archived")
    # {} overlaps {} but these are not active → result must be empty.
    result = find_overlapping_campaigns(crm_conn, {})
    assert result == []


def test_find_overlaps_empty_targeting_overlaps_all(crm_conn):
    """DEFAULT {} targeting overlaps every other targeting by definition."""
    _insert_campaign(crm_conn, campaign_id="specific", targeting={"tier": ["VIP"]}, priority=10)
    result = find_overlapping_campaigns(crm_conn, {})
    assert any(r["campaign_id"] == "specific" for r in result)


def test_find_overlaps_priority_values_present(crm_conn):
    """Priority and name must be present in returned overlap dicts for UI shadow direction."""
    _insert_campaign(crm_conn, campaign_id="high-prio", targeting={}, priority=5)
    _insert_campaign(crm_conn, campaign_id="low-prio",  targeting={}, priority=50)
    result = find_overlapping_campaigns(crm_conn, {})
    ids = {r["campaign_id"] for r in result}
    assert "high-prio" in ids
    assert "low-prio"  in ids
    for r in result:
        assert "priority" in r
        assert "name" in r
