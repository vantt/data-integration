"""Guard the Jinja templates factory configuration.

auto_reload=False in prod (CRM_DEV_RELOAD unset/0): Jinja re-stats the
filesystem on every {% include %}; under the container FS that turns the
worklist (~8.5k icon includes) from ~20ms into ~17s.

auto_reload=True in dev (CRM_DEV_RELOAD=1): template edits are visible on
the next request without restarting the container.

Also contains smoke tests for the banded worklist fragment (S01 redesign).
The fragment is rendered via a plain jinja2.Environment (no HTTP server
needed) wired with the same filters/globals as composition.py.
"""
from __future__ import annotations

import pathlib
from types import SimpleNamespace

import jinja2
import pytest

from adapters.inbound.web.templating import make_templates
from adapters.inbound.web.format_helpers import (
    fmt_vnd, format_date_ict, format_datetime_ict, format_relative,
    format_ict, truncate_str, join_nonempty,
    fmt_pct, fmt_vnd_signed, order_status_tone, payment_tone, ship_tone,
    verdict_tone, verdict_word, fmt_date_key, days_since, recency_days_label,
    bdg_cls_filter, bdg_tip_filter, bdg_label_filter,
)
from adapters.inbound.web.badge_catalog import bdg_lookup
from application.worklist_ranking import WorklistRow, rank_worklist, split_worklist_view
from domain.entities.cache_insight import ActionQueueItem
from domain.entities.task import Task

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_TEMPLATES_DIR = str(
    pathlib.Path(__file__).parents[1]
    / "adapters" / "inbound" / "web" / "templates"
)

# ---------------------------------------------------------------------------
# Shared Jinja environment with all production filters wired
# ---------------------------------------------------------------------------

def _make_env() -> jinja2.Environment:
    """Return a Jinja2 Environment mirroring composition.py filter wiring."""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(_TEMPLATES_DIR),
        autoescape=True,
        auto_reload=False,
    )
    # filters (mirrors composition.py §6)
    env.filters["format_vnd"] = fmt_vnd
    env.filters["fmt_vnd"] = fmt_vnd
    env.filters["format_date_ict"] = format_date_ict
    env.filters["format_datetime_ict"] = format_datetime_ict
    env.filters["format_relative"] = format_relative
    env.filters["format_ict"] = format_ict
    env.filters["truncate_str"] = truncate_str
    env.filters["join_nonempty"] = join_nonempty
    env.filters["fmt_pct"] = fmt_pct
    env.filters["fmt_vnd_signed"] = fmt_vnd_signed
    env.filters["order_status_tone"] = order_status_tone
    env.filters["payment_tone"] = payment_tone
    env.filters["ship_tone"] = ship_tone
    env.filters["verdict_tone"] = verdict_tone
    env.filters["verdict_word"] = verdict_word
    env.filters["fmt_date_key"] = fmt_date_key
    env.filters["days_since"] = days_since
    env.filters["recency_days_label"] = recency_days_label
    env.filters["bdg_cls"] = bdg_cls_filter
    env.filters["bdg_tip"] = bdg_tip_filter
    env.filters["bdg_label"] = bdg_label_filter
    # globals
    env.globals["bdg_lookup"] = bdg_lookup
    return env


# ---------------------------------------------------------------------------
# Fixture factories
# ---------------------------------------------------------------------------

_TS = "2026-06-23T00:00:00.000Z"
_TODAY_STR = "2026-06-23"
_YESTERDAY_STR = "2026-06-22"
_TOMORROW_STR = "2026-06-24"


def _action(
    action_id: str = "a-001",
    action_type: str = "REORDER_NUDGE",
    priority: int = 5,
    value: int = 500_000,
    pending_since: str = _TODAY_STR,
    customer_name: str = "Nguyen Van A",
    customer_key: str = "ck-001",
    party_id: str | None = None,
    status: str = "open",
    snoozed_until: str | None = None,
) -> ActionQueueItem:
    return ActionQueueItem(
        action_id=action_id,
        customer_key=customer_key,
        action_type=action_type,
        rationale_vi="Test rationale",
        value_at_stake_vnd=value,
        priority=priority,
        pending_since=pending_since,
        generated_date=_TODAY_STR,
        refreshed_at=_TS,
        customer_name=customer_name,
        party_id=party_id,
        status=status,
        snoozed_until=snoozed_until,
    )


def _task(
    task_id: str = "t-001",
    title: str = "Test task",
    priority: int = 0,
    due_at: str | None = None,
    status: str = "open",
    party_id: str | None = None,
    description: str | None = None,
    source: str = "manual",
    party_name: str | None = None,
) -> Task:
    return Task(
        task_id=task_id,
        title=title,
        priority=priority,
        status=status,
        source=source,
        created_at=_TS,
        updated_at=_TS,
        party_id=party_id,
        due_at=due_at,
        description=description,
        party_name=party_name,
    )


def _render_fragment(ctx: dict) -> str:
    """Render worklist_fragment.html with given context; raises on Jinja error."""
    env = _make_env()
    tmpl = env.get_template("fragments/worklist_fragment.html")
    return tmpl.render(**ctx)


def _base_ctx(**overrides) -> dict:
    """Minimal valid context satisfying every variable referenced in the fragment."""
    ctx = {
        "bands": [],
        "queue_action_bands": [],
        "queue_action_count": 0,
        "claimed_task_bands": [],
        "claimed_task_count": 0,
        "my_task_bands": [],
        "value_total": 0,
        "counts": {"actions": 0, "tasks": 0, "total": 0},
        "task_open": 0,
        "urgent_count": 0,
        "party_extras": {},
        "refreshed_at": "",
        "is_stale": False,
        "available_types": [],
        "active_filter_count": 0,
        "filters": {"assignee": "me", "priority": "all", "types": [], "q": "", "min_value": 0},
        # Starlette's Request.url is a URL object with a `.query` attr; production
        # rendering always has this via fastapi.templating.Jinja2Templates.TemplateResponse
        # (which injects `request` into context). The overflow "Xem thêm" link
        # (_wl_bands.html) reads request.url.query, so tests need a stub too.
        "request": SimpleNamespace(url=SimpleNamespace(query="")),
    }
    ctx.update(overrides)
    # Auto-derive the queue/my-tasks split from a raw rank_worklist() `bands` result
    # when the caller didn't already provide the split explicitly — keeps every
    # existing `_base_ctx(**rank_worklist_result)` call site working unmodified.
    if "bands" in overrides and "queue_action_bands" not in overrides:
        split = split_worklist_view({"bands": ctx["bands"]})
        ctx["queue_action_bands"] = split["queue_action_bands"]
        ctx["queue_action_count"] = split["queue_action_count"]
        ctx["claimed_task_bands"] = split["claimed_task_bands"]
        ctx["claimed_task_count"] = split["claimed_task_count"]
        ctx["my_task_bands"] = split["my_task_bands"]
    return ctx


# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

# ── Jinja env factory ────────────────────────────────────────────────────────

class TestMakeTemplatesFactory:
    def test_prod_disables_auto_reload(self, tmp_data_dir, monkeypatch):
        monkeypatch.delenv("CRM_DEV_RELOAD", raising=False)
        templates = make_templates(tmp_data_dir)
        assert templates.env.auto_reload is False

    def test_dev_enables_auto_reload(self, tmp_data_dir, monkeypatch):
        monkeypatch.setenv("CRM_DEV_RELOAD", "1")
        templates = make_templates(tmp_data_dir)
        assert templates.env.auto_reload is True


# ── Mixed bands smoke test ───────────────────────────────────────────────────

class TestWorlistFragmentMixedBands:
    """Fragment renders mixed actions + tasks; band headers + counts visible; no Jinja error."""

    def _build_ctx(self) -> dict:
        from datetime import date
        actions = [
            _action("a-call",    action_type="CALL_NOW",       priority=1, value=2_000_000,
                    pending_since=_TODAY_STR),
            _action("a-reorder", action_type="REORDER_PREEMPT", priority=4, value=800_000,
                    pending_since=_TODAY_STR),
        ]
        tasks = [
            _task("t-overdue", title="Overdue task", priority=1,
                  due_at=f"{_YESTERDAY_STR}T10:00:00Z"),
            _task("t-today",   title="Today task",   priority=0,
                  due_at=f"{_TODAY_STR}T10:00:00Z"),
        ]
        result = rank_worklist(actions, tasks, today=date(2026, 6, 23))
        return _base_ctx(
            **result,
            party_extras={},
            refreshed_at=_TS,
            is_stale=False,
            available_types=["CALL_NOW", "REORDER_PREEMPT"],
            active_filter_count=0,
            filters={"assignee": "me", "priority": "all", "types": [], "q": "", "min_value": 0},
        )

    def test_renders_without_error(self):
        html = _render_fragment(self._build_ctx())
        assert html  # non-empty

    def test_worklist_container_present(self):
        html = _render_fragment(self._build_ctx())
        assert 'id="worklist-container"' in html

    def test_band_headers_present(self):
        html = _render_fragment(self._build_ctx())
        # At least two bands must be non-empty (band 0 overdue task, band 1 CALL_NOW + today task)
        assert "Quá hạn" in html
        assert "Hôm nay / Khẩn" in html

    def test_band_counts_rendered(self):
        html = _render_fragment(self._build_ctx())
        # Band counts appear inside wl-band__count spans
        assert "wl-band__count" in html

    def test_action_rows_present(self):
        html = _render_fragment(self._build_ctx())
        assert "wl-row--action" in html

    def test_task_rows_present(self):
        html = _render_fragment(self._build_ctx())
        assert "wl-row--task" in html

    def test_kpi_strip_rendered(self):
        html = _render_fragment(self._build_ctx())
        assert "kpi-strip" in html

    def test_progress_bar_rendered_when_total_nonzero(self):
        html = _render_fragment(self._build_ctx())
        assert "wl-progress" in html


# ── Empty input state ────────────────────────────────────────────────────────

class TestWorlistFragmentEmptyState:
    """counts.total == 0 → ST-WORKLIST-EMPTY state div rendered."""

    def test_empty_state_div_present(self):
        ctx = _base_ctx()  # counts.total = 0 by default
        html = _render_fragment(ctx)
        assert 'id="wl-empty-state"' in html

    def test_empty_state_contains_no_task_message(self):
        html = _render_fragment(_base_ctx())
        assert "Hôm nay không có task nào" in html

    def test_empty_state_no_band_headers(self):
        html = _render_fragment(_base_ctx())
        assert "wl-band__header" not in html

    def test_progress_bar_absent_when_total_zero(self):
        html = _render_fragment(_base_ctx())
        assert "wl-progress" not in html


# ── All-done / no open rows ───────────────────────────────────────────────────

class TestWorlistFragmentAllDone:
    """When no rows survive (bands all empty), empty state renders — not an error."""

    def test_all_empty_bands_yields_empty_state(self):
        from datetime import date
        result = rank_worklist([], [], today=date(2026, 6, 23))
        ctx = _base_ctx(**result, party_extras={}, refreshed_at="", is_stale=False,
                        available_types=[], active_filter_count=0,
                        filters={"assignee": "me", "priority": "all",
                                 "types": [], "q": "", "min_value": 0})
        html = _render_fragment(ctx)
        assert 'id="wl-empty-state"' in html

    def test_no_jinja_error_on_all_empty_bands(self):
        from datetime import date
        result = rank_worklist([], [], today=date(2026, 6, 23))
        ctx = _base_ctx(**result, party_extras={})
        # Must not raise
        html = _render_fragment(ctx)
        assert html


# ── Filter bar rendering ─────────────────────────────────────────────────────

class TestWorlistFilterBar:
    """Filter bar renders action_type chips, clear-all, active-filter badge."""

    def _ctx(self, available_types=None, active_filter_count=0, filters=None) -> dict:
        return _base_ctx(
            available_types=available_types or [],
            active_filter_count=active_filter_count,
            filters=filters or {"assignee": "me", "priority": "all",
                                 "types": [], "q": "", "min_value": 0},
        )

    def test_filter_bar_container_present(self):
        html = _render_fragment(self._ctx())
        assert 'id="wl-filter-bar"' in html

    def test_priority_toggles_present(self):
        html = _render_fragment(self._ctx())
        assert "Tất cả" in html
        assert "Cao" in html
        assert "Khẩn" in html

    def test_action_type_chips_rendered_for_available_types(self):
        # The "Loại" (type) select lives in row 2, which only renders when
        # adv=1 (WlfTwoRow redesign, 68a6a028) — must open it to see the options.
        html = _render_fragment(self._ctx(
            available_types=["CALL_NOW", "WIN_BACK", "REORDER_PREEMPT"],
            filters={"assignee": "me", "priority": "all", "types": [], "q": "",
                     "min_value": 0, "adv": "1"},
        ))
        # Filter bar renders a <select> with <option value="<action_type>"> per type.
        assert 'value="CALL_NOW"' in html
        assert 'value="WIN_BACK"' in html
        assert 'value="REORDER_PREEMPT"' in html

    def test_no_chips_when_available_types_empty(self):
        html = _render_fragment(self._ctx(available_types=[]))
        assert 'class="tab chip"' not in html

    def test_clear_all_absent_when_no_active_filters(self):
        html = _render_fragment(self._ctx(active_filter_count=0))
        assert "Xóa filter" not in html

    def test_active_filter_badge_and_clear_all_shown_when_filters_active(self):
        # "badge--primary" was the pre-WlfTwoRow badge class (removed in 68a6a028);
        # the current design's sole active-filter signal is the "Xóa filter" button,
        # gated by active_filter_count > 0.
        html = _render_fragment(self._ctx(active_filter_count=2))
        assert "Xóa filter" in html

    def test_all_new_action_types_have_chips(self):
        """All types reachable from the full mart type set appear as select options."""
        types = ["CALL_NOW", "REORDER_NUDGE", "REORDER_PREEMPT",
                 "WIN_BACK", "SECOND_ORDER", "HIGH_CANCEL_RISK",
                 "UPSELL", "CROSS_SELL", "COLLECT_FEEDBACK"]
        html = _render_fragment(self._ctx(
            available_types=types,
            filters={"assignee": "me", "priority": "all", "types": [], "q": "",
                     "min_value": 0, "adv": "1"},
        ))
        for t in types:
            assert f'value="{t}"' in html, f"select option for {t!r} not found"


# ── Badge catalog coverage for mart action types ─────────────────────────────

class TestActionTypeBadges:
    """action_type badge renders a styled (non-empty) CSS class — guards badge_catalog gaps."""

    MART_TYPES = [
        "CALL_NOW",
        "REORDER_PREEMPT",
        "SECOND_ORDER",
        "HIGH_CANCEL_RISK",
        "WIN_BACK",
    ]

    def _render_action_row(self, action_type: str) -> str:
        from datetime import date
        a = _action("a-badge", action_type=action_type, priority=1)
        result = rank_worklist([a], [], today=date(2026, 6, 23))
        ctx = _base_ctx(**result, party_extras={})
        return _render_fragment(ctx)

    @pytest.mark.parametrize("action_type", MART_TYPES)
    def test_badge_class_is_styled_not_neutral(self, action_type: str):
        """Each mart action type must produce a non-neutral badge (bdg--warn or bdg--bad)."""
        html = self._render_action_row(action_type)
        # Template renders: class="{{ a.action_type | bdg_cls('action_type') }}"
        # bdg_full_cls returns 'bdg bdg--<mod>' for known types; 'bdg' (neutral) for unknowns
        # Badge TEXT is now the short VN label (phase-09 R3), not the raw mart code.
        from adapters.inbound.web.badge_catalog import bdg_label
        short_label = bdg_label("action_type", action_type)
        assert f'>{short_label}<' in html, f"action_type {action_type!r} short label not in output"
        # Assert the badge span contains a modifier class (bdg--warn or bdg--bad)
        # Grab the span that carries the action_type value and check it has a modifier
        from adapters.inbound.web.badge_catalog import bdg_lookup
        defn = bdg_lookup("action_type", action_type.lower())
        assert defn.css_mod != "", (
            f"{action_type!r} resolved to neutral badge — add entry to badge_catalog.py"
        )

    @pytest.mark.parametrize("action_type", MART_TYPES)
    def test_badge_class_in_rendered_html(self, action_type: str):
        """Rendered HTML contains the expected modifier class for each mart type."""
        from adapters.inbound.web.format_helpers import bdg_cls_filter
        expected_class = bdg_cls_filter(action_type, "action_type")
        html = self._render_action_row(action_type)
        assert expected_class in html, (
            f"Expected class {expected_class!r} for {action_type!r} not found in rendered HTML"
        )


# ── Phase-09: worklist label clarity (R1/R3/R4) ─────────────────────────────

class TestActionRowLabelClarity:
    """Action rows show short VN badge labels + never leak the raw customer_key hash."""

    _HASH_KEY = "d8835eb2200423e5d3295fc7257379f3"  # 32-char MD5-style surrogate key

    def _render_action_row(self, **action_overrides) -> str:
        from datetime import date
        a = _action("a-clarity", **action_overrides)
        result = rank_worklist([a], [], today=date(2026, 6, 23))
        ctx = _base_ctx(**result, party_extras={})
        return _render_fragment(ctx)

    @pytest.mark.parametrize("action_type,expected_label", [
        ("CALL_NOW", "Gọi ngay"),
        ("REORDER_NUDGE", "Nhắc tái đặt"),
    ])
    def test_badge_shows_short_label_not_raw_code(self, action_type, expected_label):
        html = self._render_action_row(action_type=action_type)
        assert f'>{expected_label}<' in html
        assert f'>{action_type}<' not in html

    def test_no_customer_name_falls_back_to_placeholder_not_hash(self):
        """customer_key must never leak into the rendered row when name/phone are absent."""
        html = self._render_action_row(customer_name="", customer_key=self._HASH_KEY)
        assert self._HASH_KEY not in html
        assert "(chưa xác định)" in html

    def test_no_customer_name_falls_back_to_phone_when_available(self):
        from datetime import date
        pref_id = SimpleNamespace(identity_type="phone", identity_value="0901234567")
        a = _action("a-clarity-phone", customer_name="", customer_key=self._HASH_KEY,
                    party_id="party-1")
        result = rank_worklist([a], [], today=date(2026, 6, 23))
        ctx = _base_ctx(**result, party_extras={
            "party-1": {"preferred_identity": pref_id, "contact_pref_notes": []},
        })
        html = _render_fragment(ctx)
        assert "0901234567" in html
        assert self._HASH_KEY not in html

    def test_customer_name_present_uses_name_not_phone_or_hash(self):
        html = self._render_action_row(customer_name="Nguyễn Văn A", customer_key=self._HASH_KEY)
        assert "Nguyễn Văn A" in html
        assert self._HASH_KEY not in html


class TestTaskRowLabelClarity:
    """Task rows must show the joined party_name, never the raw party_id UUID.

    Regression guard: the row previously read `a.customer_name` — a field
    Task does not have (only `party_name`, populated by task_repository's
    LEFT JOIN) — so Jinja's Undefined silently fell through to the raw
    party_id on every task row, claimed or not.
    """

    _PARTY_ID = "bf9904af-c395-47c9-a932-fd8f9c053fb1"

    def _render_task_row(self, **task_overrides) -> str:
        from datetime import date
        t = _task("t-clarity", party_id=self._PARTY_ID, **task_overrides)
        result = rank_worklist([], [t], today=date(2026, 6, 23))
        ctx = _base_ctx(**result, party_extras={})
        return _render_fragment(ctx)

    def test_party_name_present_uses_name_not_uuid(self):
        html = self._render_task_row(party_name="Chị Yến", source="action_queue_claim")
        assert "Chị Yến" in html
        # party_id legitimately appears in href="/customers/{pid}" links; only the
        # anchor TEXT (what the staff reads) must never be the raw UUID.
        assert f">{self._PARTY_ID}</a>" not in html

    def test_no_party_name_falls_back_to_placeholder_not_uuid(self):
        html = self._render_task_row(party_name=None, source="action_queue_claim")
        assert f">{self._PARTY_ID}</a>" not in html
        assert "(chưa xác định)" in html


class TestUnassignedQueueRowRedesign:
    """Hàng Đợi Chung rows render through wl_row() (priority pill, description,
    due date) instead of the old stripped-down bare markup, with a single
    "Nhận" CTA swapped in for the assigned-only controls."""

    def _render_queue(self, current_user_id: str = "u-1", **task_overrides) -> str:
        t = _task("t-queue", priority=2, description="Gọi xác nhận đơn hàng", **task_overrides)
        row = WorklistRow(kind="task", band=-1, urgency=0, value=0, neglect_days=0,
                           ref_id=t.task_id, payload=t)
        ctx = _base_ctx(unassigned_tasks=[row], current_user_id=current_user_id)
        return _render_fragment(ctx)

    def test_shows_priority_pill_and_description(self):
        html = self._render_queue()
        assert 'prio prio--P1' in html  # priority=2 → urgent → P1
        assert "Gọi xác nhận đơn hàng" in html

    def test_shows_nhan_button_when_authenticated(self):
        html = self._render_queue(current_user_id="u-1")
        assert 'hx-patch="/tasks/t-queue/assign-me"' in html
        assert ">Nhận<" in html

    def test_hides_nhan_button_when_not_authenticated(self):
        html = self._render_queue(current_user_id="")
        assert 'hx-patch="/tasks/t-queue/assign-me"' not in html

    def test_no_assigned_only_controls(self):
        """Trả việc / Dời hạn / Hủy / snooze all assume an existing owner — must not render."""
        html = self._render_queue()
        assert "Trả việc" not in html
        assert "Dời hạn" not in html
        assert ">Hủy<" not in html


class TestClaimedTaskSection:
    """Claimed tasks (source='action_queue_claim') render under their own
    '🙋 Đã Claim' header, not mixed into the plain urgency-band area."""

    def _ctx_with_claimed_task(self, **task_overrides) -> dict:
        from datetime import date
        t = _task("t-claim", priority=2, due_at=str(_TODAY_STR),
                  source="action_queue_claim", **task_overrides)
        result = rank_worklist([], [t], today=date(2026, 6, 23))
        return _base_ctx(**result, party_extras={})

    def test_shows_da_claim_header_with_count(self):
        html = _render_fragment(self._ctx_with_claimed_task())
        assert "🙋 Đã Claim" in html
        assert "t-claim" in html

    def test_no_da_claim_header_when_no_claimed_tasks(self):
        from datetime import date
        t = _task("t-manual", priority=2, due_at=str(_TODAY_STR), source="manual")
        result = rank_worklist([], [t], today=date(2026, 6, 23))
        html = _render_fragment(_base_ctx(**result, party_extras={}))
        assert "Đã Claim" not in html

    def test_claimed_task_not_duplicated_in_plain_urgency_area(self):
        """The claimed row must render exactly once — under Đã Claim, not also
        under the generic urgency bands below it."""
        html = _render_fragment(self._ctx_with_claimed_task())
        assert html.count('id="task-t-claim"') == 1


# ── Band collapse/expand and overflow ("Xem thêm") ──────────────────────────

class TestBandCollapseAndOverflow:
    """Band 3 has no `open` attr (collapsed); Bands 0/1/2 are expanded.
       'Xem thêm' appears when a band exceeds its cap (10 for B0/1/2; 5 for B3)."""

    def _ctx_with_band3_rows(self, n: int) -> dict:
        """n actions all landing in Band 3 (pending >= 7 days, non-urgent priority)."""
        from datetime import date
        old_pending = "2026-06-10"  # 13 days ago → band 3
        actions = [
            _action(f"a-b3-{i}", action_type="WIN_BACK", priority=4,
                    pending_since=old_pending)
            for i in range(n)
        ]
        result = rank_worklist(actions, [], today=date(2026, 6, 23))
        return _base_ctx(**result, party_extras={})

    def test_band3_has_no_open_attribute(self):
        """Band 3 details element must NOT have the `open` attribute (collapsed by default)."""
        ctx = self._ctx_with_band3_rows(1)
        html = _render_fragment(ctx)
        # The band 3 header is: <details class="wl-band" [NO open]>
        # Bands 0/1/2 have: <details class="wl-band" open>
        # We check that the Band 3 block does NOT have "open" on its details tag
        # Strategy: find the wl-band--b3 or the Treo lâu label region
        assert "Treo lâu" in html
        # After "Treo lâu" we should not immediately see <details class="wl-band" open>
        # Instead the template emits: {% if band.id != 3 %}open{% endif %}
        # We verify by checking that the rendered HTML does NOT contain a collapsed+open combo
        # — the simplest invariant: since B3 is the only band with content, check
        # that 'open' does NOT appear on the wl-band details that contains "Treo lâu"
        import re
        # Find the details block around "Treo lâu"
        pattern = re.compile(
            r'<details class="wl-band"([^>]*)>.*?Treo lâu', re.DOTALL
        )
        m = pattern.search(html)
        assert m is not None, "Band 3 details block not found"
        attrs = m.group(1)
        assert "open" not in attrs, f"Band 3 should be collapsed but has 'open' in attrs: {attrs!r}"

    def test_bands_012_expanded(self):
        """Bands 0, 1, 2 each have the `open` attribute when they contain rows."""
        from datetime import date
        actions = [_action("a-b2", action_type="REORDER_NUDGE", priority=5)]
        tasks = [
            _task("t-b0", due_at=f"{_YESTERDAY_STR}T10:00:00Z"),
            _task("t-b1", due_at=f"{_TODAY_STR}T10:00:00Z"),
        ]
        result = rank_worklist(actions, tasks, today=date(2026, 6, 23))
        ctx = _base_ctx(**result, party_extras={})
        html = _render_fragment(ctx)
        # Bands 0, 1, 2 must all have `open` on their details elements
        import re
        open_details = re.findall(r'<details class="wl-band" open>', html)
        assert len(open_details) >= 3, (
            f"Expected at least 3 expanded bands, found {len(open_details)}: {html[:3000]}"
        )

    def test_xem_them_shown_when_band_exceeds_cap(self):
        """Xem thêm toggle appears when a band has > 10 rows (cap for B0/1/2)."""
        from datetime import date
        # 12 CALL_NOW actions → all land in Band 1 (urgency=9); cap=10 → overflow=2
        actions = [
            _action(f"a-c{i}", action_type="CALL_NOW", priority=1)
            for i in range(12)
        ]
        result = rank_worklist(actions, [], today=date(2026, 6, 23))
        ctx = _base_ctx(**result, party_extras={})
        html = _render_fragment(ctx)
        assert "Xem thêm" in html

    def test_xem_them_shown_when_band3_exceeds_cap_5(self):
        """Xem thêm appears when Band 3 has > 5 rows (tighter cap = 5)."""
        ctx = self._ctx_with_band3_rows(7)  # 7 > 5 → 2 overflow
        html = _render_fragment(ctx)
        assert "Xem thêm" in html

    def test_no_xem_them_when_band_within_cap(self):
        """No Xem thêm when each band has ≤ cap rows."""
        from datetime import date
        actions = [_action("a-only", action_type="CALL_NOW", priority=1)]
        result = rank_worklist(actions, [], today=date(2026, 6, 23))
        ctx = _base_ctx(**result, party_extras={})
        html = _render_fragment(ctx)
        assert "Xem thêm" not in html

    def test_my_task_bands_never_show_xem_them_even_when_over_cap(self):
        """my_task_bands renders eager/uncapped (show_overflow=false) — regression guard
        for the band-id collision the code review caught: /worklist/band/{id}/more always
        re-ranks actions-only, so band ids 1/2 can't safely be shared between
        queue_action_bands (lazy-paginated) and my_task_bands (owned tasks) — if
        my_task_bands ever re-enabled that toggle, clicking it would fetch action rows
        into a task band. Cap is 10 for band 1 — 12 urgent tasks exceeds it.
        """
        from datetime import date
        tasks = [_task(f"t-urgent-{i}", priority=2, due_at="2026-06-23") for i in range(12)]
        result = rank_worklist([], tasks, today=date(2026, 6, 23))
        ctx = _base_ctx(**result, party_extras={})
        html = _render_fragment(ctx)
        assert "Xem thêm" not in html
        # All 12 must actually render (uncapped), not silently truncated to 10.
        for i in range(12):
            assert f"t-urgent-{i}" in html

    def test_queue_and_my_tasks_overflow_do_not_collide_on_shared_band_id(self):
        """Band 1 exists in both queue_action_bands and my_task_bands simultaneously —
        the queue side's 'Xem thêm' must be present (its overflow route is safe/actions-
        only), while the task side must not offer one at all."""
        from datetime import date
        actions = [_action(f"a-c{i}", action_type="CALL_NOW", priority=1) for i in range(12)]
        tasks = [_task(f"t-urgent-{i}", priority=2, due_at="2026-06-23") for i in range(12)]
        result = rank_worklist(actions, tasks, today=date(2026, 6, 23))
        ctx = _base_ctx(**result, party_extras={})
        html = _render_fragment(ctx)
        assert html.count("Xem thêm") == 1  # only the queue section's toggle
        for i in range(12):
            assert f"t-urgent-{i}" in html  # all 12 tasks rendered directly, no truncation
