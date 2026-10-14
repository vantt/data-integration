"""seed_path finds a dbt seed by name wherever it sits under the seeds directory.

Run:
  python -m pytest ingestion/tests/test_seed_paths.py -q
"""
from __future__ import annotations

import pytest

from ingestion.src.utils.seed_paths import (
    AmbiguousSeedError,
    SeedNotFoundError,
    seed_path,
)


@pytest.fixture
def seeds(tmp_path):
    (tmp_path / "taxonomy").mkdir()
    (tmp_path / "taxonomy" / "ref_brands.csv").write_text("a\n")
    (tmp_path / "seed_cashflow_budget.csv").write_text("a\n")
    return tmp_path


def test_finds_seed_in_subfolder(seeds):
    assert seed_path("ref_brands", seeds) == seeds / "taxonomy" / "ref_brands.csv"


def test_finds_seed_at_top_level(seeds):
    assert seed_path("seed_cashflow_budget", seeds) == seeds / "seed_cashflow_budget.csv"


def test_missing_seed_is_an_error(seeds):
    with pytest.raises(SeedNotFoundError):
        seed_path("ref_unknown", seeds)


def test_duplicate_basename_is_an_error(seeds):
    (seeds / "ref_brands.csv").write_text("a\n")
    with pytest.raises(AmbiguousSeedError, match="ref_brands"):
        seed_path("ref_brands", seeds)


@pytest.mark.parametrize("bad", ["", "taxonomy/ref_brands", "ref_brands.csv"])
def test_rejects_names_that_are_not_bare(seeds, bad):
    with pytest.raises(ValueError):
        seed_path(bad, seeds)


def test_default_directory_is_this_checkouts_seeds():
    # Every taxonomy seed resolves to exactly one file in the real project.
    for name in ("ref_order_sources", "ref_brands", "ref_tag_categories", "ref_misa_channel_codes",
                 "ref_payment_methods", "ref_spend_category", "ref_gl_accounts", "ref_branch_locations"):
        p = seed_path(name)
        assert p.parent.name == "taxonomy" and p.is_file()
