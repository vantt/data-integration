"""Unit tests for crm.src.application.worklist_ranking (pure module — no DB/HTTP).

Covers:
- urgency_score: action and task scales, cross-source comparison
- assign_band: all branches including ICT midnight boundary regression
- WorklistRow / sort ordering within each band
- rank_worklist: counts, value_total, band structure, empty input
"""
from __future__ import annotations

import pathlib
import sys
from datetime import date, timedelta

import pytest

# ── path bootstrap (mirrors conftest.py) ──────────────────────────────────────
_REPO_ROOT = str(pathlib.Path(__file__).parents[4])   # .../data-integration
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1]) # .../crm/src
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from crm.src.application.worklist_ranking import (  # noqa: E402
    urgency_score,
    assign_band,
    rank_worklist,
    WorklistRow,
    _parse_date,
    today_ict,
)
from crm.src.domain.entities.task import Task  # noqa: E402
from crm.src.domain.entities.cache_insight import ActionQueueItem  # noqa: E402


# ── helpers / fixture factories ───────────────────────────────────────────────

def _b(result: dict, band_id: int) -> dict:
    """Find band dict by ID — order-independent band lookup."""
    return next(b for b in result["bands"] if b["id"] == band_id)


_TS = "2026-06-23T00:00:00.000Z"
TODAY = date(2026, 6, 23)
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)


def make_action(
    action_id: str = "a-001",
    priority: int = 9,
    pending_since: str | None = None,
    status: str = "open",
    snoozed_until: str | None = None,
    value_at_stake_vnd: int = 0,
    action_type: str = "REORDER_NUDGE",
) -> ActionQueueItem:
    return ActionQueueItem(
        action_id=action_id,
        customer_key="ck-001",
        action_type=action_type,
        rationale_vi="test",
        value_at_stake_vnd=value_at_stake_vnd,
        priority=priority,
        pending_since=pending_since or str(TODAY),
        generated_date=str(TODAY),
        refreshed_at=_TS,
        status=status,
        snoozed_until=snoozed_until,
    )


def make_task(
    task_id: str = "t-001",
    priority: int = 0,
    due_at: str | None = None,
    status: str = "open",
    title: str = "Test task",
) -> Task:
    return Task(
        task_id=task_id,
        title=title,
        priority=priority,
        status=status,
        source="manual",
        created_at=_TS,
        updated_at=_TS,
        due_at=due_at,
    )


# =============================================================================
# urgency_score
# =============================================================================

class TestUrgencyScore:
    """Both priority scales normalize to urgency_score (higher = more urgent)."""

    # ── action scale (priority_rank: lower = more urgent) ─────────────────

    @pytest.mark.parametrize("rank,expected", [
        (1, 9),   # CALL_NOW — highest urgency
        (4, 6),   # WIN_BACK tier
        (9, 1),   # lowest priority (ELSE)
        (8, 2),
        (2, 8),
    ])
    def test_action_urgency_by_rank(self, rank, expected):
        assert urgency_score("action", rank) == expected

    def test_action_call_now_returns_9(self):
        assert urgency_score("action", 1) == 9

    def test_action_win_back_rank4_returns_6(self):
        assert urgency_score("action", 4) == 6

    def test_action_minimum_clamped_to_1(self):
        # rank=9 → 10-9=1, rank=10 → clamped to max(1, 0)=1
        assert urgency_score("action", 9) == 1
        assert urgency_score("action", 10) == 1

    # ── task scale (priority: higher = more urgent) ────────────────────────

    @pytest.mark.parametrize("prio,expected", [
        (0, 7),   # normal
        (1, 8),   # high
        (2, 9),   # urgent
    ])
    def test_task_urgency_by_priority(self, prio, expected):
        assert urgency_score("task", prio) == expected

    def test_task_normal_returns_7(self):
        assert urgency_score("task", 0) == 7

    def test_task_urgent_returns_9(self):
        assert urgency_score("task", 2) == 9

    # ── cross-source comparison ────────────────────────────────────────────

    def test_call_now_action_urgency_equals_urgent_task(self):
        """CALL_NOW(rank=1) and urgent task(priority=2) both produce urgency=9."""
        assert urgency_score("action", 1) == urgency_score("task", 2) == 9

    def test_call_now_action_urgency_gte_normal_task(self):
        """CALL_NOW >= any task urgency (guards cross-scale interleaving)."""
        call_now_urgency = urgency_score("action", 1)
        normal_task_urgency = urgency_score("task", 0)
        assert call_now_urgency >= normal_task_urgency

    def test_action_scale_is_inverted_vs_task_scale(self):
        """Higher priority_rank → lower urgency_score for actions (opposite of tasks)."""
        assert urgency_score("action", 1) > urgency_score("action", 5)
        assert urgency_score("task", 2) > urgency_score("task", 0)


# =============================================================================
# assign_band
# =============================================================================

class TestAssignBand:
    """First-match wins — exact order tested per band rule."""

    # ── Band 0 — overdue manual task ─────────────────────────────────────

    def test_overdue_manual_task_lands_in_band0(self):
        band = assign_band(
            kind="task",
            urgency=7,
            due_date=YESTERDAY,
            pending_date=None,
            snoozed_until=None,
            status="open",
            today=TODAY,
        )
        assert band == 0

    def test_task_due_two_days_ago_is_band0(self):
        two_days_ago = TODAY - timedelta(days=2)
        band = assign_band("task", 7, two_days_ago, None, None, "open", TODAY)
        assert band == 0

    def test_task_no_due_date_not_band0(self):
        """Task without a due date cannot be overdue."""
        band = assign_band("task", 7, None, None, None, "open", TODAY)
        assert band != 0

    def test_action_never_lands_in_band0(self):
        """Actions have no deadline concept — band 0 is tasks-only."""
        band = assign_band("action", 9, None, None, None, "open", TODAY)
        assert band != 0

    # ── Band 1 — today / urgent ────────────────────────────────────────────

    def test_task_due_today_lands_in_band1(self):
        band = assign_band("task", 7, TODAY, None, None, "open", TODAY)
        assert band == 1

    def test_action_call_now_lands_in_band1(self):
        """CALL_NOW urgency=9 → Band 1 via urgency >= 9 rule."""
        us = urgency_score("action", 1)  # 9
        band = assign_band("action", us, None, None, None, "open", TODAY)
        assert band == 1

    def test_urgent_task_priority2_lands_in_band1(self):
        """Urgent task (priority=2 → urgency=9) → Band 1."""
        us = urgency_score("task", 2)  # 9
        band = assign_band("task", us, None, None, None, "open", TODAY)
        assert band == 1

    def test_snoozed_action_woke_up_lands_in_band1(self):
        """Snoozed action whose snoozed_until is today (past due) wakes into Band 1."""
        band = assign_band(
            kind="action",
            urgency=6,
            due_date=None,
            pending_date=TODAY - timedelta(days=3),
            snoozed_until=YESTERDAY,
            status="snoozed",
            today=TODAY,
        )
        assert band == 1

    def test_snoozed_action_still_snoozed_not_band1(self):
        """Snoozed action where snoozed_until is in the future stays in band 2 or 3."""
        band = assign_band(
            kind="action",
            urgency=6,
            due_date=None,
            pending_date=TODAY - timedelta(days=3),
            snoozed_until=TOMORROW,
            status="snoozed",
            today=TODAY,
        )
        assert band != 1

    def test_snoozed_until_equals_today_wakes_into_band1(self):
        """snoozed_until == today means 'woke up today' → Band 1 (boundary: <=)."""
        band = assign_band(
            kind="action",
            urgency=5,
            due_date=None,
            pending_date=TODAY - timedelta(days=2),
            snoozed_until=TODAY,
            status="snoozed",
            today=TODAY,
        )
        assert band == 1

    # ── Band 3 — neglected actions ─────────────────────────────────────────

    def test_action_pending_7_days_non_urgent_lands_in_band3(self):
        """Action pending >= 7 days with urgency < 9 → Band 3 (neglected)."""
        pending = TODAY - timedelta(days=7)
        band = assign_band("action", 6, None, pending, None, "open", TODAY)
        assert band == 3

    def test_action_pending_exactly_7_days_is_band3(self):
        pending = TODAY - timedelta(days=7)
        band = assign_band("action", 5, None, pending, None, "open", TODAY)
        assert band == 3

    def test_action_pending_8_days_is_band3(self):
        pending = TODAY - timedelta(days=8)
        band = assign_band("action", 4, None, pending, None, "open", TODAY)
        assert band == 3

    def test_action_pending_6_days_not_band3(self):
        """6 days pending is on-track, not neglected."""
        pending = TODAY - timedelta(days=6)
        band = assign_band("action", 6, None, pending, None, "open", TODAY)
        assert band == 2

    def test_urgent_action_pending_10_days_overrides_to_band1(self):
        """Urgency >= 9 wins over neglect rule (band 1 check comes before band 3)."""
        pending = TODAY - timedelta(days=10)
        us = urgency_score("action", 1)  # 9
        band = assign_band("action", us, None, pending, None, "open", TODAY)
        assert band == 1

    # ── Band 2 — on-track / default ────────────────────────────────────────

    def test_normal_open_action_recent_pending_is_band2(self):
        """Action pending 3 days, non-urgent → on-track (Band 2)."""
        pending = TODAY - timedelta(days=3)
        band = assign_band("action", 6, None, pending, None, "open", TODAY)
        assert band == 2

    def test_task_with_future_due_date_is_band2(self):
        """Task due tomorrow → on-track."""
        band = assign_band("task", 7, TOMORROW, None, None, "open", TODAY)
        assert band == 2

    def test_task_no_due_date_normal_priority_is_band2(self):
        """Task without deadline and urgency=7 → Band 2 by default."""
        band = assign_band("task", 7, None, None, None, "open", TODAY)
        assert band == 2

    # ── ICT boundary regression ─────────────────────────────────────────────

    def test_ict_midnight_not_overdue(self):
        """Item timestamped '2026-06-23T00:30:00+07:00' (ICT) is today in ICT.

        Naive UTC would parse this as 2026-06-22 (yesterday) and misfile
        into Band 0.  The due_at stored as '2026-06-23T00:30:00+07:00' parses
        to date 2026-06-23 via _parse_date, so Band 0 must NOT trigger.
        """
        # due_at stores the string that _parse_date will slice to first 10 chars
        # '2026-06-23T00:30:00+07:00' → slice [:10] → '2026-06-23' → TODAY → Band 1
        due_at_ict = "2026-06-23T00:30:00+07:00"
        parsed_due = _parse_date(due_at_ict)
        assert parsed_due == TODAY, (
            f"_parse_date should return today's ICT date but got {parsed_due}"
        )
        # With due_date == TODAY, assign_band must give Band 1 (not Band 0)
        band = assign_band("task", 7, parsed_due, None, None, "open", TODAY)
        assert band == 1, (
            f"Task due ICT today must land in Band 1, not Band 0 (got {band})"
        )

    def test_task_dated_yesterday_utc_midnight_is_overdue_in_ict(self):
        """'2026-06-22' due date → yesterday in ICT → overdue → Band 0."""
        due_at = "2026-06-22"
        parsed_due = _parse_date(due_at)
        assert parsed_due == YESTERDAY
        band = assign_band("task", 7, parsed_due, None, None, "open", TODAY)
        assert band == 0


# =============================================================================
# rank_worklist — structure, counts, value_total, ordering
# =============================================================================

class TestRankWorklistStructure:
    """rank_worklist always returns 5 bands in order 4→0→1→2→3."""

    def test_empty_input_returns_well_formed_structure(self):
        result = rank_worklist([], [], TODAY)
        assert "bands" in result
        assert "counts" in result
        assert "value_total" in result
        assert "task_open" in result
        assert "urgent_count" in result

    def test_empty_input_has_exactly_5_bands(self):
        result = rank_worklist([], [], TODAY)
        assert len(result["bands"]) == 5

    def test_empty_input_band_ids_ordered_4_0_to_3(self):
        result = rank_worklist([], [], TODAY)
        assert [b["id"] for b in result["bands"]] == [4, 0, 1, 2, 3]

    def test_empty_input_all_bands_have_zero_count(self):
        result = rank_worklist([], [], TODAY)
        for band in result["bands"]:
            assert band["count"] == 0, f"Band {band['id']} should be empty"
            assert band["rows"] == []
            assert band["total_value"] == 0

    def test_empty_input_counts_all_zero(self):
        result = rank_worklist([], [], TODAY)
        assert result["counts"] == {"actions": 0, "tasks": 0, "total": 0}
        assert result["value_total"] == 0
        assert result["task_open"] == 0
        assert result["urgent_count"] == 0

    def test_band_dicts_have_required_keys(self):
        result = rank_worklist([], [], TODAY)
        required = {"id", "label", "icon", "rows", "count", "total_value"}
        for band in result["bands"]:
            assert required.issubset(band.keys()), (
                f"Band {band.get('id')} missing keys: {required - band.keys()}"
            )


class TestRankWorklistCounts:
    """counts + value_total aggregations are correct."""

    def test_counts_actions_and_tasks_tracked_separately(self):
        actions = [make_action("a-001"), make_action("a-002")]
        tasks = [make_task("t-001")]
        result = rank_worklist(actions, tasks, TODAY)
        assert result["counts"]["actions"] == 2
        assert result["counts"]["tasks"] == 1
        assert result["counts"]["total"] == 3

    def test_value_total_sums_all_action_values(self):
        a1 = make_action("a-001", value_at_stake_vnd=500_000)
        a2 = make_action("a-002", value_at_stake_vnd=300_000)
        result = rank_worklist([a1, a2], [], TODAY)
        assert result["value_total"] == 800_000

    def test_value_total_excludes_tasks(self):
        """Tasks have value=0; value_total is actions-only."""
        tasks = [make_task("t-001")]
        result = rank_worklist([], tasks, TODAY)
        assert result["value_total"] == 0

    def test_band_total_value_sums_rows_in_that_band(self):
        """total_value per band = sum of values of rows in that band."""
        # CALL_NOW action (rank=1 → urgency=9 → Band 1)
        a1 = make_action("a-001", priority=1, value_at_stake_vnd=1_000_000)
        # Neglected action (pending 8 days, urgency=6 → Band 3)
        a2 = make_action("a-002", priority=4,
                         pending_since=str(TODAY - timedelta(days=8)),
                         value_at_stake_vnd=200_000)
        result = rank_worklist([a1, a2], [], TODAY)

        band1 = next(b for b in result["bands"] if b["id"] == 1)
        band3 = next(b for b in result["bands"] if b["id"] == 3)

        assert band1["total_value"] == 1_000_000
        assert band3["total_value"] == 200_000

    def test_task_open_equals_number_of_tasks_passed(self):
        """All tasks passed in are open (upstream filters done/cancelled out)."""
        tasks = [make_task("t-1"), make_task("t-2"), make_task("t-3")]
        result = rank_worklist([], tasks, TODAY)
        assert result["task_open"] == 3

    def test_urgent_count_is_band0_plus_band1(self):
        # Overdue task → Band 0
        t_overdue = make_task("t-o", due_at=str(YESTERDAY))
        # CALL_NOW action → Band 1
        a_urgent = make_action("a-u", priority=1)
        # On-track action → Band 2
        a_normal = make_action("a-n", priority=5)
        result = rank_worklist([a_urgent, a_normal], [t_overdue], TODAY)
        assert result["urgent_count"] == 2  # band0=1, band1=1


class TestRankWorklistRouting:
    """Items land in correct bands end-to-end through rank_worklist."""

    def test_overdue_task_routes_to_band0(self):
        t = make_task("t-1", due_at=str(YESTERDAY))
        result = rank_worklist([], [t], TODAY)
        band0 = _b(result, 0)
        assert band0["count"] == 1
        assert band0["rows"][0].kind == "task"
        assert band0["rows"][0].ref_id == "t-1"

    def test_task_due_today_routes_to_band1(self):
        t = make_task("t-1", due_at=str(TODAY) + "T00:00:00.000Z")
        result = rank_worklist([], [t], TODAY)
        band1 = _b(result, 1)
        assert any(r.ref_id == "t-1" for r in band1["rows"])

    def test_call_now_action_routes_to_band1(self):
        a = make_action("a-1", priority=1)
        result = rank_worklist([a], [], TODAY)
        band1 = _b(result, 1)
        assert any(r.ref_id == "a-1" for r in band1["rows"])

    def test_neglected_action_routes_to_band3(self):
        a = make_action("a-1", priority=4,
                        pending_since=str(TODAY - timedelta(days=8)))
        result = rank_worklist([a], [], TODAY)
        band3 = _b(result, 3)
        assert any(r.ref_id == "a-1" for r in band3["rows"])

    def test_normal_open_action_routes_to_band2(self):
        a = make_action("a-1", priority=5,
                        pending_since=str(TODAY - timedelta(days=2)))
        result = rank_worklist([a], [], TODAY)
        band2 = _b(result, 2)
        assert any(r.ref_id == "a-1" for r in band2["rows"])

    def test_woken_snoozed_action_routes_to_band1(self):
        a = make_action("a-1", priority=4, status="snoozed",
                        snoozed_until=str(YESTERDAY),
                        pending_since=str(TODAY - timedelta(days=3)))
        result = rank_worklist([a], [], TODAY)
        band1 = _b(result, 1)
        assert any(r.ref_id == "a-1" for r in band1["rows"])


class TestRankWorklistSortOrder:
    """Within-band sort ordering (most important first)."""

    def test_band0_most_overdue_first(self):
        """Band 0: due_at asc (most overdue at top)."""
        t_very_old = make_task("t-old", due_at=str(TODAY - timedelta(days=5)))
        t_recent = make_task("t-recent", due_at=str(YESTERDAY))
        result = rank_worklist([], [t_very_old, t_recent], TODAY)
        band0_rows = _b(result, 0)["rows"]
        assert len(band0_rows) == 2
        # most overdue first (t-old is further past)
        assert band0_rows[0].ref_id == "t-old"
        assert band0_rows[1].ref_id == "t-recent"

    def test_band1_higher_urgency_first(self):
        """Band 1: urgency desc — CALL_NOW (urgency=9) before a snoozed woke-up (urgency=6).

        Both must genuinely land in Band 1: CALL_NOW via urgency>=9, the second
        via snoozed_until past-due (woke-up rule). This tests the within-band sort,
        NOT the band assignment itself.
        """
        # urgency=9 → Band 1 via urgency rule
        a_call_now = make_action("a-call", priority=1, value_at_stake_vnd=100_000)
        # urgency=6 + snoozed woke-up → Band 1 via snoozed rule
        a_woken = make_action(
            "a-woken", priority=4, value_at_stake_vnd=500_000,
            status="snoozed", snoozed_until=str(YESTERDAY),
            pending_since=str(TODAY - timedelta(days=3)),
        )
        result = rank_worklist([a_call_now, a_woken], [], TODAY)
        band1_rows = _b(result, 1)["rows"]
        assert len(band1_rows) == 2
        # urgency=9 (a-call) must sort before urgency=6 (a-woken)
        assert band1_rows[0].ref_id == "a-call"
        assert band1_rows[1].ref_id == "a-woken"

    def test_band1_same_urgency_higher_value_first(self):
        """Band 1: tie on urgency → value desc."""
        a_low_val = make_action("a-low", priority=1, value_at_stake_vnd=100_000)
        a_high_val = make_action("a-high", priority=1, value_at_stake_vnd=900_000)
        result = rank_worklist([a_low_val, a_high_val], [], TODAY)
        band1_rows = _b(result, 1)["rows"]
        assert len(band1_rows) == 2
        assert band1_rows[0].ref_id == "a-high"
        assert band1_rows[1].ref_id == "a-low"

    def test_band2_urgency_desc_then_value_desc(self):
        """Band 2: urgency desc, then value desc on tie."""
        # a-mid: urgency=6 (rank=4), value=1M
        a_mid = make_action("a-mid", priority=4, value_at_stake_vnd=1_000_000,
                            pending_since=str(TODAY - timedelta(days=2)))
        # a-low: urgency=5 (rank=5), value=2M — lower urgency despite higher value
        a_low_urg = make_action("a-low", priority=5, value_at_stake_vnd=2_000_000,
                                pending_since=str(TODAY - timedelta(days=2)))
        result = rank_worklist([a_mid, a_low_urg], [], TODAY)
        band2_rows = _b(result, 2)["rows"]
        assert len(band2_rows) == 2
        assert band2_rows[0].ref_id == "a-mid"   # higher urgency wins
        assert band2_rows[1].ref_id == "a-low"

    def test_band3_value_desc(self):
        """Band 3: value desc (highest opportunity surfaces first)."""
        a_small = make_action("a-small", priority=4, value_at_stake_vnd=50_000,
                              pending_since=str(TODAY - timedelta(days=8)))
        a_big = make_action("a-big", priority=4, value_at_stake_vnd=500_000,
                            pending_since=str(TODAY - timedelta(days=8)))
        result = rank_worklist([a_small, a_big], [], TODAY)
        band3_rows = _b(result, 3)["rows"]
        assert len(band3_rows) == 2
        assert band3_rows[0].ref_id == "a-big"
        assert band3_rows[1].ref_id == "a-small"


class TestRankWorklistMixedItems:
    """Mixed actions + tasks correctly merged and routed."""

    def test_actions_and_tasks_coexist_in_same_band(self):
        """Band 1 can contain both an urgent action and a task due today."""
        a = make_action("a-1", priority=1)
        t = make_task("t-1", due_at=str(TODAY) + "T00:00:00.000Z")
        result = rank_worklist([a], [t], TODAY)
        band1 = _b(result, 1)
        kinds = {r.kind for r in band1["rows"]}
        assert "action" in kinds
        assert "task" in kinds

    def test_total_count_includes_both_actions_and_tasks(self):
        actions = [make_action(f"a-{i}") for i in range(3)]
        tasks = [make_task(f"t-{i}") for i in range(2)]
        result = rank_worklist(actions, tasks, TODAY)
        assert result["counts"]["total"] == 5

    def test_each_row_has_correct_kind_field(self):
        a = make_action("a-1")
        t = make_task("t-1")
        result = rank_worklist([a], [t], TODAY)
        all_rows = [r for band in result["bands"] for r in band["rows"]]
        action_rows = [r for r in all_rows if r.kind == "action"]
        task_rows = [r for r in all_rows if r.kind == "task"]
        assert len(action_rows) == 1
        assert len(task_rows) == 1

    def test_task_rows_have_value_zero(self):
        t = make_task("t-1")
        result = rank_worklist([], [t], TODAY)
        all_rows = [r for band in result["bands"] for r in band["rows"]]
        for row in all_rows:
            if row.kind == "task":
                assert row.value == 0


class TestWorklistRowFields:
    """WorklistRow fields are populated correctly from source entities."""

    def test_action_row_ref_id_matches_action_id(self):
        a = make_action("a-xyz", priority=9)
        result = rank_worklist([a], [], TODAY)
        all_rows = [r for band in result["bands"] for r in band["rows"]]
        row = next(r for r in all_rows if r.kind == "action")
        assert row.ref_id == "a-xyz"

    def test_task_row_ref_id_matches_task_id(self):
        t = make_task("t-xyz")
        result = rank_worklist([], [t], TODAY)
        all_rows = [r for band in result["bands"] for r in band["rows"]]
        row = next(r for r in all_rows if r.kind == "task")
        assert row.ref_id == "t-xyz"

    def test_action_row_value_matches_value_at_stake(self):
        a = make_action("a-1", priority=9, value_at_stake_vnd=999_999)
        result = rank_worklist([a], [], TODAY)
        all_rows = [r for band in result["bands"] for r in band["rows"]]
        row = next(r for r in all_rows if r.kind == "action")
        assert row.value == 999_999

    def test_action_row_payload_is_original_entity(self):
        a = make_action("a-1")
        result = rank_worklist([a], [], TODAY)
        all_rows = [r for band in result["bands"] for r in band["rows"]]
        row = next(r for r in all_rows if r.kind == "action")
        assert row.payload is a

    def test_task_row_payload_is_original_entity(self):
        t = make_task("t-1")
        result = rank_worklist([], [t], TODAY)
        all_rows = [r for band in result["bands"] for r in band["rows"]]
        row = next(r for r in all_rows if r.kind == "task")
        assert row.payload is t

    def test_overdue_task_neglect_days_equals_days_since_due(self):
        due_3_days_ago = TODAY - timedelta(days=3)
        t = make_task("t-1", due_at=str(due_3_days_ago))
        result = rank_worklist([], [t], TODAY)
        band0_rows = _b(result, 0)["rows"]
        assert len(band0_rows) == 1
        assert band0_rows[0].neglect_days == 3

    def test_action_neglect_days_equals_days_since_pending(self):
        pending_5_days_ago = TODAY - timedelta(days=5)
        a = make_action("a-1", pending_since=str(pending_5_days_ago))
        result = rank_worklist([a], [], TODAY)
        all_rows = [r for band in result["bands"] for r in band["rows"]]
        row = next(r for r in all_rows if r.kind == "action")
        assert row.neglect_days == 5


# =============================================================================
# _parse_date — helper robustness
# =============================================================================

class TestParseDateHelper:
    """_parse_date handles warehouse (YYYY-MM-DD) and ISO-8601 datetime strings."""

    @pytest.mark.parametrize("date_str,expected", [
        ("2026-06-23", date(2026, 6, 23)),
        ("2026-06-23T00:30:00.000Z", date(2026, 6, 23)),
        ("2026-06-23T00:30:00Z", date(2026, 6, 23)),
        ("2026-06-23T00:30:00", date(2026, 6, 23)),
        ("2026-06-23T00:30:00+07:00", date(2026, 6, 23)),
        ("2026-06-22T17:00:00+00:00", date(2026, 6, 22)),  # midnight ICT in UTC
    ])
    def test_parse_date_formats(self, date_str, expected):
        assert _parse_date(date_str) == expected

    def test_parse_date_none_returns_none(self):
        assert _parse_date(None) is None

    def test_parse_date_empty_string_returns_none(self):
        assert _parse_date("") is None

    def test_parse_date_invalid_returns_none(self):
        assert _parse_date("not-a-date") is None
