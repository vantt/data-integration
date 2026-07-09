"""Unit tests for the pure worklist filter module.

Uses SimpleNamespace as a duck-typed stand-in for ActionQueueItem / Task —
apply_filters reads attributes via getattr, so any object with the right fields
works and the tests stay dependency-free.
"""
from types import SimpleNamespace

from crm.src.application.worklist_filters import (
    active_filter_count,
    apply_filters,
    available_action_types,
    parse_filters,
)


def _action(action_type="CALL_NOW", priority=1, name="A", rationale="", value=0, customer_id=None,
            top_affinity_product="", last_purchased_product="", is_contactable=True):
    return SimpleNamespace(
        action_type=action_type, priority=priority, customer_name=name,
        rationale_vi=rationale, value_at_stake_vnd=value, customer_id=customer_id,
        top_affinity_product=top_affinity_product, last_purchased_product=last_purchased_product,
        is_contactable=is_contactable,
    )


def _task(priority=0, title="T", description=""):
    return SimpleNamespace(priority=priority, title=title, description=description)


# ── parse_filters ──────────────────────────────────────────────────────────

def test_parse_filters_defaults():
    f = parse_filters({})
    # strategic_tier/value_group/adv added by the two-row filter bar (68a6a028) —
    # keep this assertion in sync with parse_filters' actual return shape.
    assert f == {"assignee": "me", "priority": "all", "types": [], "q": "", "min_value": 0,
                 "product": "", "hide_contacted": False, "has_script": False,
                 "contactable_only": True,  # default ON
                 "strategic_tier": "", "value_group": "", "adv": ""}


def test_parse_filters_type_comma_list_and_trim():
    f = parse_filters({"type": "CALL_NOW, WIN_BACK ,"})
    assert f["types"] == ["CALL_NOW", "WIN_BACK"]


def test_parse_filters_min_value_invalid_falls_back_to_zero():
    assert parse_filters({"min_value": "abc"})["min_value"] == 0
    assert parse_filters({"min_value": "500000"})["min_value"] == 500000


# ── available_action_types ──────────────────────────────────────────────────

def test_available_action_types_distinct_sorted_nonempty():
    acts = [_action("WIN_BACK"), _action("CALL_NOW"), _action("CALL_NOW"), _action("")]
    assert available_action_types(acts) == ["CALL_NOW", "WIN_BACK"]


# ── active_filter_count ─────────────────────────────────────────────────────

def test_active_filter_count_excludes_assignee():
    # assignee non-default must NOT be counted (toggle hidden, not applied)
    f = {"assignee": "all", "priority": "all", "types": [], "q": "", "min_value": 0}
    assert active_filter_count(f) == 0


def test_active_filter_count_sums_active():
    f = {"assignee": "me", "priority": "urgent", "types": ["CALL_NOW"], "q": "x", "min_value": 1}
    assert active_filter_count(f) == 4


# ── apply_filters: priority via normalized urgency ──────────────────────────

def test_priority_urgent_keeps_call_now_action():
    # regression: CALL_NOW (rank=1 → urgency=9) must survive the "urgent" filter
    acts = [_action("CALL_NOW", priority=1), _action("WIN_BACK", priority=4)]
    f = parse_filters({"priority": "urgent"})
    out_acts, _ = apply_filters(acts, [], f)
    assert [a.action_type for a in out_acts] == ["CALL_NOW"]


def test_priority_urgent_keeps_urgent_task():
    tasks = [_task(priority=2), _task(priority=0)]
    f = parse_filters({"priority": "urgent"})
    _, out_tasks = apply_filters([], tasks, f)
    assert [t.priority for t in out_tasks] == [2]


def test_priority_high_threshold():
    acts = [_action("CALL_NOW", priority=1), _action("REORDER_NUDGE", priority=2),
            _action("WIN_BACK", priority=4)]
    f = parse_filters({"priority": "high"})  # urgency >= 8 → ranks 1,2
    out_acts, _ = apply_filters(acts, [], f)
    assert {a.action_type for a in out_acts} == {"CALL_NOW", "REORDER_NUDGE"}


# ── apply_filters: type / search / min_value ────────────────────────────────

def test_type_filter_actions_only_tasks_pass_through():
    acts = [_action("CALL_NOW"), _action("WIN_BACK")]
    tasks = [_task()]
    f = parse_filters({"type": "CALL_NOW"})
    out_acts, out_tasks = apply_filters(acts, tasks, f)
    assert [a.action_type for a in out_acts] == ["CALL_NOW"]
    assert len(out_tasks) == 1  # tasks unaffected by type filter


def test_search_matches_name_rationale_title_description():
    acts = [_action(name="Nguyễn"), _action(name="Trần", rationale="gọi lại")]
    tasks = [_task(title="khác"), _task(description="gọi gấp")]
    f = parse_filters({"q": "gọi"})
    out_acts, out_tasks = apply_filters(acts, tasks, f)
    assert len(out_acts) == 1 and out_acts[0].rationale_vi == "gọi lại"
    assert len(out_tasks) == 1 and out_tasks[0].description == "gọi gấp"


def test_min_value_filters_actions_only():
    acts = [_action(value=2_000_000), _action(value=500_000)]
    tasks = [_task()]
    f = parse_filters({"min_value": "1000000"})
    out_acts, out_tasks = apply_filters(acts, tasks, f)
    assert [a.value_at_stake_vnd for a in out_acts] == [2_000_000]
    assert len(out_tasks) == 1


def test_no_filters_passes_everything_through():
    acts = [_action(), _action("WIN_BACK", priority=4)]
    tasks = [_task(), _task(priority=2)]
    out_acts, out_tasks = apply_filters(acts, tasks, parse_filters({}))
    assert len(out_acts) == 2 and len(out_tasks) == 2


# ── apply_filters: has_script ───────────────────────────────────────────────

def test_has_script_keeps_only_actions_with_customer_id_in_set():
    """has_script=1 narrows actions to those whose customer_id is in script_cids."""
    acts = [
        _action("CALL_NOW", customer_id=100),
        _action("WIN_BACK", customer_id=200),
        _action("UPSELL",   customer_id=None),
    ]
    tasks = [_task()]
    f = parse_filters({"has_script": "1"})
    script_cids = {100, 300}
    out_acts, out_tasks = apply_filters(acts, tasks, f, script_cids)
    assert [a.customer_id for a in out_acts] == [100]
    assert len(out_tasks) == 1   # tasks not filtered by has_script


def test_has_script_off_returns_all_actions():
    """has_script filter absent — no change regardless of script_cids."""
    acts = [_action(customer_id=100), _action(customer_id=999)]
    f = parse_filters({})
    out_acts, _ = apply_filters(acts, [], f, {100})
    assert len(out_acts) == 2


def test_has_script_none_cids_does_not_filter():
    """When script_cids is None (approach_repo unavailable), actions are kept."""
    acts = [_action(customer_id=100), _action(customer_id=200)]
    f = parse_filters({"has_script": "1"})
    out_acts, _ = apply_filters(acts, [], f, script_cids=None)
    assert len(out_acts) == 2


def test_has_script_counted_in_active_filter_count():
    f = parse_filters({"has_script": "1"})
    assert active_filter_count(f) == 1


def test_parse_filters_has_script_default_false():
    assert parse_filters({})["has_script"] is False


def test_parse_filters_has_script_on():
    assert parse_filters({"has_script": "1"})["has_script"] is True


# ── apply_filters: contactable_only (default ON) ────────────────────────────

def test_contactable_only_default_keeps_only_contactable_actions():
    """No query param — contactable_only defaults to True and filters."""
    acts = [_action("CALL_NOW", is_contactable=True), _action("WIN_BACK", is_contactable=False)]
    tasks = [_task()]
    f = parse_filters({})
    out_acts, out_tasks = apply_filters(acts, tasks, f)
    assert [a.action_type for a in out_acts] == ["CALL_NOW"]
    assert len(out_tasks) == 1  # tasks not filtered by contactable_only


def test_contactable_only_explicit_off_returns_all_actions():
    acts = [_action(is_contactable=True), _action(is_contactable=False)]
    f = parse_filters({"contactable_only": "0"})
    out_acts, _ = apply_filters(acts, [], f)
    assert len(out_acts) == 2


def test_contactable_only_off_counted_in_active_filter_count():
    """Turning OFF the default-on toggle is the non-default state — counts."""
    f = parse_filters({"contactable_only": "0"})
    assert active_filter_count(f) == 1


def test_contactable_only_default_on_not_counted_in_active_filter_count():
    f = parse_filters({})
    assert active_filter_count(f) == 0


def test_parse_filters_contactable_only_default_true():
    assert parse_filters({})["contactable_only"] is True


def test_parse_filters_contactable_only_explicit_off():
    assert parse_filters({"contactable_only": "0"})["contactable_only"] is False


def test_parse_filters_contactable_only_on():
    assert parse_filters({"contactable_only": "1"})["contactable_only"] is True
