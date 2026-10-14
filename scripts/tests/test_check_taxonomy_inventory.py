"""test_check_taxonomy_inventory.py — the inventory check warns on changed or new taxonomy blocks.

Run:
  python -m pytest scripts/tests/test_check_taxonomy_inventory.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

_SCRIPTS_DIR = str(Path(__file__).resolve().parents[1])
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from checks import check_taxonomy_inventory as cti  # noqa: E402

MODEL = "transformation/models/core/dim_x.sql"
SQL = """select
    -- grade by spend
    case
        when spend >= 100 then 'HIGH'
        else 'LOW'
    end as value_group,
    a is not null as is_flag
from t
"""


def _write(repo: Path, rel: str, text: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _inventory(repo: Path, extra_blocks: list[dict] | None = None) -> dict:
    blocks = cti.find_case_blocks((repo / MODEL).read_text(encoding="utf-8"), MODEL)
    case = next(b for b in blocks if b.alias == "value_group")
    entries = [dict(file=MODEL, line=case.line, alias="value_group", kind="case", sha256=case.sha256)]
    entries += extra_blocks or []
    return {"domains": {"value_group": {"columns": ["value_group"], "blocks": entries}}}


@pytest.fixture
def repo(tmp_path):
    _write(tmp_path, MODEL, SQL)
    (tmp_path / "transformation" / "macros").mkdir(parents=True)
    return tmp_path


def test_unchanged_code_is_silent(repo):
    assert cti.check(repo, _inventory(repo)) == ([], [])


def test_whitespace_and_comment_edits_are_silent(repo):
    inv = _inventory(repo)
    _write(repo, MODEL, SQL.replace("-- grade by spend", "-- reworded").replace("        else", "\n\n   else"))
    assert cti.check(repo, inv) == ([], [])


def test_changed_threshold_warns(repo):
    inv = _inventory(repo)
    _write(repo, MODEL, SQL.replace(">= 100", ">= 200"))
    warns, _ = cti.check(repo, inv)
    assert len(warns) == 1 and "changed" in warns[0] and "value_group" in warns[0]


def test_new_block_for_known_column_warns(repo):
    inv = _inventory(repo)
    _write(repo, "transformation/models/core/other.sql",
           "select case when x then 'A' else 'B' end as value_group from u\n")
    warns, _ = cti.check(repo, inv)
    assert len(warns) == 1 and "new" in warns[0] and "other.sql" in warns[0]


def test_case_for_unrelated_column_is_ignored(repo):
    inv = _inventory(repo)
    _write(repo, "transformation/models/core/other.sql",
           "select case when x then 1 else 0 end as is_something from u\n")
    assert cti.check(repo, inv) == ([], [])


def test_scoped_column_only_matches_its_file(repo):
    inv = _inventory(repo)
    inv["domains"]["value_group"]["columns"].append("only_here.sql:status")
    _write(repo, "transformation/models/core/other.sql", "select case when x then 1 else 0 end as status from u\n")
    assert cti.check(repo, inv) == ([], [])
    _write(repo, "transformation/models/core/only_here.sql", "select case when x then 1 else 0 end as status from u\n")
    warns, _ = cti.check(repo, inv)
    assert len(warns) == 1 and "only_here.sql" in warns[0]


def test_moved_block_is_info_not_warning(repo):
    inv = _inventory(repo)
    _write(repo, MODEL, "-- header\n-- header\n" + SQL)
    warns, infos = cti.check(repo, inv)
    assert warns == [] and len(infos) == 1 and "moved" in infos[0]


def test_expression_snippet_change_warns(repo):
    expr = dict(file=MODEL, line=6, alias="is_flag", kind="expr", snippet="a is not null as is_flag", sha256="x")
    inv = _inventory(repo, [expr])
    assert cti.check(repo, inv) == ([], [])
    _write(repo, MODEL, SQL.replace("a is not null", "a is null"))
    warns, _ = cti.check(repo, inv)
    assert len(warns) == 1 and "is_flag" in warns[0]


def test_missing_file_warns(repo):
    inv = _inventory(repo)
    (repo / MODEL).unlink()
    warns, _ = cti.check(repo, inv)
    assert len(warns) == 1 and "missing" in warns[0]


def test_strings_and_comments_do_not_confuse_case_scan():
    sql = "select case when a = 'case end' then 1 /* case */ else 2 end as value_group -- end\nfrom t"
    blocks = cti.find_case_blocks(sql, "x.sql")
    assert [b.alias for b in blocks] == ["value_group"]


def test_nested_case_gets_own_block_and_outer_alias():
    sql = "select case when a then case when b then 1 else 2 end else 3 end as value_group from t"
    blocks = cti.find_case_blocks(sql, "x.sql")
    assert sorted(b.alias or "" for b in blocks) == ["", "value_group"]


def test_main_exits_zero_even_with_warnings(repo, tmp_path, capsys):
    inv_path = tmp_path / "inv.yaml"
    inv_path.write_text(yaml.safe_dump(_inventory(repo)), encoding="utf-8")
    _write(repo, MODEL, SQL.replace(">= 100", ">= 200"))
    rc = cti.main(["--repo", str(repo), "--inventory", str(inv_path)])
    out = capsys.readouterr().out
    assert rc == 0 and "WARN changed" in out


def test_branch_inventory_matches_code():
    """The committed inventory is current: no warning on this checkout."""
    inv = cti.load_inventory()
    warns, _ = cti.check(cti.REPO, inv)
    assert warns == []


def test_every_inventoried_case_block_is_covered_by_a_declared_column():
    inv = cti.load_inventory()
    cols = cti.taxonomy_columns(inv)
    for dom, spec in inv["domains"].items():
        for blk in spec["blocks"]:
            if blk.get("kind", "case") == "case":
                assert cols.covers(blk["file"], blk["alias"]), (dom, blk["file"], blk["alias"])


def test_spec_document_hashes_match_inventory():
    """TAXONOMY.md quotes the first 16 hex characters of every inventoried hash, and nothing else."""
    import re

    inv = cti.load_inventory()
    spec = (cti.REPO / "transformation" / "docs" / "TAXONOMY.md").read_text(encoding="utf-8")
    quoted = set(re.findall(r"\| `([0-9a-f]{16})` \|", spec))
    recorded = {blk["sha256"][:16] for spec_ in inv["domains"].values() for blk in spec_["blocks"]}
    assert quoted == recorded
