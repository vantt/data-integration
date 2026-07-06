"""test_task_service_title_fallback.py — phase-09 R5 regression guard.

Task title fallback (used when rationale_vi is empty) must never expose
action.customer_key — an internal MD5 surrogate key (dbt_utils.generate_surrogate_key)
never meant for display — via claim_action_item() or _process_action(). Fallback
chain: customer_name → phone (via party_repo) → "(chưa xác định)". The
"[action_type]" title prefix must use the short VN label, not the raw mart code.
"""
from __future__ import annotations

import pathlib
import sys
from unittest.mock import MagicMock

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from application.task_service import TaskService  # noqa: E402
from domain.entities.party import Party  # noqa: E402

_HASH_KEY = "d8835eb2200423e5d3295fc7257379f3"  # 32-char MD5-style surrogate key


def _make_service(party_repo=None):
    task_repo = MagicMock()
    task_repo.get_by_source_ref = MagicMock(return_value=None)
    task_repo.exists_by_source_ref = MagicMock(return_value=False)
    task_repo.insert = MagicMock()
    cache_repo = MagicMock()
    svc = TaskService(task_repo, cache_repo, db=None, party_repo=party_repo)
    return svc, task_repo, cache_repo


def _make_action(**overrides):
    action = MagicMock()
    action.action_id = overrides.get("action_id", "aq-001")
    action.action_type = overrides.get("action_type", "CALL_NOW")
    action.rationale_vi = overrides.get("rationale_vi", "")
    action.customer_key = overrides.get("customer_key", _HASH_KEY)
    action.customer_name = overrides.get("customer_name", "")
    action.party_id = overrides.get("party_id", None)
    action.priority = overrides.get("priority", 1)
    return action


def _make_party(primary_phone: str) -> Party:
    return Party(
        party_id="party-1", party_type="person", display_name="",
        primary_phone=primary_phone, primary_email="", status="active",
        is_merged=False, created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


class TestClaimActionItemTitleFallback:
    """claim_action_item(): title fallback when rationale_vi is empty."""

    def test_no_rationale_no_name_no_party_falls_back_to_placeholder(self):
        svc, _, _ = _make_service()
        action = _make_action(rationale_vi="", customer_name="", party_id=None)
        task, is_new = svc.claim_action_item("aq-001", action, "user-1")
        assert is_new is True
        assert _HASH_KEY not in task.title
        assert "(chưa xác định)" in task.title

    def test_no_rationale_uses_customer_name(self):
        svc, _, _ = _make_service()
        action = _make_action(rationale_vi="", customer_name="Nguyễn Văn A")
        task, _ = svc.claim_action_item("aq-001", action, "user-1")
        assert "Nguyễn Văn A" in task.title
        assert _HASH_KEY not in task.title

    def test_no_rationale_no_name_falls_back_to_phone_via_party_repo(self):
        party_repo = MagicMock()
        party_repo.get_by_id.return_value = _make_party("0901234567")
        svc, _, _ = _make_service(party_repo=party_repo)
        action = _make_action(rationale_vi="", customer_name="", party_id="party-1")
        task, _ = svc.claim_action_item("aq-001", action, "user-1")
        assert "0901234567" in task.title
        assert _HASH_KEY not in task.title

    def test_title_uses_short_label_not_raw_action_type_code(self):
        svc, _, _ = _make_service()
        action = _make_action(action_type="CALL_NOW", rationale_vi="Gọi ngay khách VIP")
        task, _ = svc.claim_action_item("aq-001", action, "user-1")
        assert "[Gọi ngay]" in task.title
        assert "[CALL_NOW]" not in task.title


class TestProcessActionTitleFallback:
    """generate_tasks_from_action_queue() → _process_action(): same fallback logic."""

    def test_no_rationale_no_name_no_party_falls_back_to_placeholder(self):
        svc, task_repo, cache_repo = _make_service()
        action = _make_action(rationale_vi="", customer_name="", party_id=None)
        cache_repo.list_all_action_queue.return_value = [action]
        created = svc.generate_tasks_from_action_queue("user-1")
        assert created == 1
        task = task_repo.insert.call_args[0][0]
        assert _HASH_KEY not in task.title
        assert "(chưa xác định)" in task.title

    def test_no_rationale_no_name_falls_back_to_phone_via_party_repo(self):
        party_repo = MagicMock()
        party_repo.get_by_id.return_value = _make_party("0907654321")
        svc, task_repo, cache_repo = _make_service(party_repo=party_repo)
        action = _make_action(rationale_vi="", customer_name="", party_id="party-1")
        cache_repo.list_all_action_queue.return_value = [action]
        svc.generate_tasks_from_action_queue("user-1")
        task = task_repo.insert.call_args[0][0]
        assert "0907654321" in task.title
        assert _HASH_KEY not in task.title
