"""test_party_seed_service.py — unit tests for PartySeedService.sync_parties.

Strategy: mock CacheRepository + PartyRepository so no real DB is needed.
Covers:
  - empty seed list → returns 0, no upsert calls
  - valid seeds → upsert_from_sapo_identity called once per seed, count returned
  - partial failures → loop continues, partial count returned (no RuntimeError)
  - all failures → RuntimeError raised
"""
from __future__ import annotations

import pathlib, sys  # noqa: E401
from unittest.mock import MagicMock
import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from crm.python.application.party_seed_service import PartySeedService  # noqa: E402
from crm.python.domain.entities.party import PartySeed, Party           # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_seed(customer_id: int = 1001, phone: str = "0901000001", email: str = "a@test.vn") -> PartySeed:
    return PartySeed(
        customer_id=customer_id,
        customer_key=f"key-cust-{customer_id}",
        display_name="Test Customer",
        phone=phone,
        email=email,
        source_contact_quality="unverified",
        contact_quality="unverified",
        seen_at="2026-06-15T00:00:00Z",
    )


def _make_party(party_id: str = "p-001") -> Party:
    return Party(
        party_id=party_id,
        party_type="person",
        display_name="Test Customer",
        primary_phone="+84901000001",
        primary_email="a@test.vn",
        status="active",
        is_merged=False,
        created_at="2026-06-15T00:00:00.000Z",
        updated_at="2026-06-15T00:00:00.000Z",
    )


def _make_cache_repo(seeds: list[PartySeed]) -> MagicMock:
    repo = MagicMock()
    repo.list_party_seed.return_value = seeds
    return repo


def _make_party_repo() -> MagicMock:
    repo = MagicMock()
    repo.find_by_identity.return_value = None
    repo.create_with_identities.side_effect = lambda party, ids: party
    repo.upsert_identity.return_value = None
    repo.update.return_value = None
    return repo


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_sync_parties_empty_list_returns_zero():
    cache_repo = _make_cache_repo([])
    party_repo = _make_party_repo()
    svc = PartySeedService(cache_repo, party_repo)

    count = svc.sync_parties(cache_repo)

    assert count == 0
    party_repo.find_by_identity.assert_not_called()
    party_repo.create_with_identities.assert_not_called()


def test_sync_parties_single_seed_calls_upsert_once():
    seed = _make_seed(1001)
    cache_repo = _make_cache_repo([seed])
    party_repo = _make_party_repo()
    svc = PartySeedService(cache_repo, party_repo)

    count = svc.sync_parties(cache_repo)

    assert count == 1
    party_repo.find_by_identity.assert_called_once_with("sapo_customer", "1001")
    party_repo.create_with_identities.assert_called_once()


def test_sync_parties_multiple_seeds_returns_full_count():
    seeds = [_make_seed(1001), _make_seed(1002, "0902000002", "b@test.vn")]
    cache_repo = _make_cache_repo(seeds)
    party_repo = _make_party_repo()
    svc = PartySeedService(cache_repo, party_repo)

    count = svc.sync_parties(cache_repo)

    assert count == 2
    assert party_repo.find_by_identity.call_count == 2
    assert party_repo.create_with_identities.call_count == 2


def test_sync_parties_partial_failure_continues_and_returns_partial_count():
    """One seed raises; service skips it, processes the rest, returns partial count."""
    seeds = [_make_seed(1001), _make_seed(1002, "0902000002", "b@test.vn")]
    cache_repo = _make_cache_repo(seeds)
    party_repo = _make_party_repo()

    # First call raises, second call succeeds
    party_repo.find_by_identity.side_effect = [
        Exception("DB timeout"),
        None,
    ]
    svc = PartySeedService(cache_repo, party_repo)

    count = svc.sync_parties(cache_repo)

    assert count == 1   # only seed-1002 succeeded


def test_sync_parties_all_failures_raises_runtime_error():
    seeds = [_make_seed(1001), _make_seed(1002)]
    cache_repo = _make_cache_repo(seeds)
    party_repo = _make_party_repo()
    party_repo.find_by_identity.side_effect = Exception("connection refused")

    svc = PartySeedService(cache_repo, party_repo)

    with pytest.raises(RuntimeError, match="all .* seeds failed"):
        svc.sync_parties(cache_repo)


def test_sync_parties_existing_party_not_recreated():
    """find_by_identity returns an existing party → create_with_identities NOT called."""
    seed = _make_seed(1001)
    cache_repo = _make_cache_repo([seed])
    party_repo = _make_party_repo()
    party_repo.find_by_identity.return_value = _make_party("p-existing")

    svc = PartySeedService(cache_repo, party_repo)
    count = svc.sync_parties(cache_repo)

    assert count == 1
    party_repo.create_with_identities.assert_not_called()


def test_sync_parties_uses_str_customer_id_as_sapo_id():
    """Seed consumer must pass customer_id as str to upsert (mirrors Go str(seed.customer_id))."""
    seed = _make_seed(9999)
    cache_repo = _make_cache_repo([seed])
    party_repo = _make_party_repo()
    svc = PartySeedService(cache_repo, party_repo)

    svc.sync_parties(cache_repo)

    party_repo.find_by_identity.assert_called_once_with("sapo_customer", "9999")
