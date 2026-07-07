"""test_approach_script_file_repository.py — Unit tests for FileApproachScriptRepository.

Cases:
  - found: valid JSON file → returns ApproachScript with correct fields
  - missing: no file for cid → None
  - malformed: corrupt JSON → None (no raise), warning logged
  - mtime: refreshed_at is non-empty ISO-8601 UTC string ending in Z
  - recommended_false: data["approach"]["recommended"] = false → entity.recommended == False

Run:
  PYTHONPATH="crm/src" python -m pytest crm/src/tests/test_approach_script_file_repository.py -q
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])    # .../data-integration
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])  # .../crm/src
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from adapters.outbound.file.approach_script_file_repository import FileApproachScriptRepository  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

_VALID_DATA = {
    "profile_read": "Test customer profile",
    "value_assessment": {"tier": "SILVER", "lifetime_value_vnd": 5000000, "margin_health": "healthy", "invest_level": "medium"},
    "opportunity": {"headline": "Cơ hội nhắc mua lại", "rationale": "...", "evidence": []},
    "risk": {"headline": "Rủi ro churn", "type": "churn", "rationale": "..."},
    "approach": {
        "recommended": True,
        "reason_if_not_recommended": None,
        "primary_channel": "phone",
        "fallback_channel": "sms",
        "timing": "Sáng sớm",
        "opening_message": "Xin chào",
        "fallback_message": "Tin nhắn dự phòng",
        "talking_points": ["Point 1"],
        "cross_sell": [],
        "objection_handling": [],
        "do_not": [],
    },
    "confidence": "medium",
    "data_gaps": [],
}

_NOT_RECOMMENDED_DATA = {
    **_VALID_DATA,
    "approach": {
        **_VALID_DATA["approach"],
        "recommended": False,
        "reason_if_not_recommended": "Contact quality too low to call.",
    },
}


def _write_json(dir_path: pathlib.Path, customer_id: int, data: dict) -> pathlib.Path:
    p = dir_path / f"{customer_id}.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_found_returns_entity(tmp_path):
    """Valid JSON file → ApproachScript with correct customer_id, recommended, confidence."""
    _write_json(tmp_path, 603264280, _VALID_DATA)
    repo = FileApproachScriptRepository(tmp_path)

    result = repo.get_by_customer_id(603264280)

    assert result is not None
    assert result.customer_id == 603264280
    assert result.recommended is True
    assert result.confidence == "medium"
    assert result.data == _VALID_DATA


def test_missing_returns_none(tmp_path):
    """No file for customer_id → None (graceful empty state)."""
    repo = FileApproachScriptRepository(tmp_path)
    assert repo.get_by_customer_id(999999999) is None


def test_malformed_json_returns_none(tmp_path, caplog):
    """Corrupt JSON → None (no exception raised), warning emitted."""
    bad_file = tmp_path / "12345.json"
    bad_file.write_text("{this is not valid json!!!", encoding="utf-8")
    repo = FileApproachScriptRepository(tmp_path)

    import logging
    with caplog.at_level(logging.WARNING, logger="adapters.outbound.file.approach_script_file_repository"):
        result = repo.get_by_customer_id(12345)

    assert result is None
    assert any("12345" in rec.message for rec in caplog.records)


def test_refreshed_at_is_nonempty_utc_z(tmp_path):
    """refreshed_at comes from file mtime and ends with Z."""
    _write_json(tmp_path, 100, _VALID_DATA)
    repo = FileApproachScriptRepository(tmp_path)

    result = repo.get_by_customer_id(100)

    assert result is not None
    assert result.refreshed_at.endswith("Z")
    assert "T" in result.refreshed_at   # ISO-8601 format


def test_recommended_false_extracted_correctly(tmp_path):
    """data["approach"]["recommended"] = false → entity.recommended is False."""
    _write_json(tmp_path, 777, _NOT_RECOMMENDED_DATA)
    repo = FileApproachScriptRepository(tmp_path)

    result = repo.get_by_customer_id(777)

    assert result is not None
    assert result.recommended is False
    assert result.data["approach"]["reason_if_not_recommended"] == "Contact quality too low to call."


def test_missing_approach_key_defaults_recommended_true(tmp_path):
    """JSON with no approach key → recommended defaults to True (no crash)."""
    data = {"profile_read": "No approach section", "confidence": "low"}
    _write_json(tmp_path, 200, data)
    repo = FileApproachScriptRepository(tmp_path)

    result = repo.get_by_customer_id(200)

    assert result is not None
    assert result.recommended is True
    assert result.confidence == "low"


def test_meta_block_populates_model_and_template_version(tmp_path):
    """Auto-gen scripts embed meta {model, template_version} → entity fields set."""
    data = {**_VALID_DATA, "meta": {"model": "gpt-5.5", "template_version": "v2", "generator": "codex-exec"}}
    _write_json(tmp_path, 300, data)
    repo = FileApproachScriptRepository(tmp_path)

    result = repo.get_by_customer_id(300)

    assert result is not None
    assert result.model == "gpt-5.5"
    assert result.template_version == "v2"


def test_no_meta_block_leaves_model_none(tmp_path):
    """Legacy hand-pasted scripts have no meta → model/template_version stay None."""
    _write_json(tmp_path, 301, _VALID_DATA)
    repo = FileApproachScriptRepository(tmp_path)

    result = repo.get_by_customer_id(301)

    assert result is not None
    assert result.model is None
    assert result.template_version is None


# ── list_customer_ids ──────────────────────────────────────────────────────────

def test_list_customer_ids_returns_int_set(tmp_path):
    """Valid JSON files → set of customer_id ints."""
    _write_json(tmp_path, 100, _VALID_DATA)
    _write_json(tmp_path, 603264280, _VALID_DATA)
    repo = FileApproachScriptRepository(tmp_path)

    result = repo.list_customer_ids()

    assert result == {100, 603264280}


def test_list_customer_ids_empty_dir(tmp_path):
    """Empty directory → empty set (no error)."""
    repo = FileApproachScriptRepository(tmp_path)
    assert repo.list_customer_ids() == set()


def test_list_customer_ids_ignores_non_matching_files(tmp_path):
    """Non-matching filenames (no .json, letters, etc.) are silently ignored."""
    (tmp_path / "garbage.txt").write_text("x")
    (tmp_path / "abc123.json").write_text("{}")
    (tmp_path / "README.md").write_text("doc")
    _write_json(tmp_path, 42, _VALID_DATA)
    repo = FileApproachScriptRepository(tmp_path)

    result = repo.list_customer_ids()

    assert result == {42}


def test_list_customer_ids_reflects_new_file_without_reinit(tmp_path):
    """Newly dropped file appears on next call — no restart / re-init required."""
    _write_json(tmp_path, 10, _VALID_DATA)
    repo = FileApproachScriptRepository(tmp_path)

    first_call = repo.list_customer_ids()
    assert first_call == {10}

    # Drop a new file AFTER the first call (simulates loader/Dagster dropping file).
    _write_json(tmp_path, 20, _VALID_DATA)

    second_call = repo.list_customer_ids()
    assert second_call == {10, 20}   # new file auto-reflected, no restart
