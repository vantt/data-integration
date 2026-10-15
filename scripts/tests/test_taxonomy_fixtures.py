"""test_taxonomy_fixtures.py — unit-test fixtures of the classification engine are byte copies of the seeds.

The customer_type unit tests (transformation/models/core/intermediate/taxonomy/_taxonomy__models.yml)
must run on the real Fine Japan rules, so their rule fixture must stay identical to the seed.

Run:
  python -m pytest scripts/tests/test_taxonomy_fixtures.py -q
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TRANSFORMATION = REPO / "transformation"

# fixture (tests/fixtures/<name>.csv) -> seed it copies
FIXTURE_SEEDS = {
    "taxonomy_rule_tenant_customer_type": "seeds/tenants/fine_japan/taxonomy_rule_tenant.csv",
}


@pytest.mark.parametrize("fixture,seed", sorted(FIXTURE_SEEDS.items()))
def test_fixture_is_a_byte_copy_of_the_seed(fixture, seed):
    fixture_bytes = (TRANSFORMATION / "tests" / "fixtures" / f"{fixture}.csv").read_bytes()
    seed_bytes = (TRANSFORMATION / seed).read_bytes()
    assert fixture_bytes == seed_bytes, (
        f"tests/fixtures/{fixture}.csv differs from {seed}: copy the seed over the fixture "
        f"(cp transformation/{seed} transformation/tests/fixtures/{fixture}.csv) and re-run the unit tests")


def test_unit_tests_reference_the_fixture():
    spec = (TRANSFORMATION / "models" / "core" / "intermediate" / "taxonomy" / "_taxonomy__models.yml").read_text(encoding="utf-8")
    for fixture in FIXTURE_SEEDS:
        assert f"fixture: {fixture}" in spec
