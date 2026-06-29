"""test_hug_campaign_admin_ui.py — tests for the Hug campaign admin UI screens.

Covers the FastAPI-free HTML helpers and the data-flow helpers in the router module.
No live HTTP server needed — mirrors the pattern established in test_hug_mint_reprint.py.

Test groups:
  - render_campaign_list: empty state + rows with status badges
  - render_campaign_form: rule-builder controls + catalog attributes + is_new flag
  - _parse_targeting: list attr, range attr, mixed, empty (no targeting)
  - validate + save path: invalid targeting rejected / valid targeting saved to crm.db
  - push mock: push_campaign is called after a valid save
  - guard: make_hug_campaign_router returns a non-None APIRouter
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import sys
from unittest.mock import MagicMock, patch

import pytest

# ── sys.path bootstrap (mirrors other test files) ────────────────────────────

_REPO_ROOT = str(pathlib.Path(__file__).parents[3])    # .../data-integration
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])  # .../crm/src
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── imports ───────────────────────────────────────────────────────────────────

from hug.targeting_catalog import TARGETING_CATALOG  # noqa: E402
from hug.campaign_repository import upsert_campaign, get_campaign  # noqa: E402
# FastAPI-free HTML helpers are always importable (no FastAPI dep in _html module).
from adapters.inbound.web.screens.hug.screen_hug_campaign_html import (  # noqa: E402
    render_campaign_list,
    render_campaign_form,
    render_preview_panel,
    render_status_result,
    _targeting_summary,
)

# The router module imports FastAPI at module level; guard so the pure-HTML
# and data-layer tests still run in the host Python (FastAPI lives in Docker).
try:
    from adapters.inbound.web.screens.hug.screen_hug_campaign import (  # noqa: E402
        _parse_targeting,
        _build_row,
        _safe_campaign_id,
    )
    _ROUTER_AVAILABLE = True
except ImportError:
    _ROUTER_AVAILABLE = False

    # Provide no-op stubs so tests that skip on the flag can still be collected.
    def _parse_targeting(form):  # type: ignore[misc]
        return {}

    def _build_row(cid, form, targeting):  # type: ignore[misc]
        return {}

    def _safe_campaign_id(cid):  # type: ignore[misc]
        return None

_router_only = pytest.mark.skipif(
    not _ROUTER_AVAILABLE,
    reason="FastAPI not installed in host Python (runs in Docker container)",
)

# ── Migration fixture (same approach as test_hug_campaign_repository.py) ────

_MIGRATION_PATH = (
    pathlib.Path(__file__).parents[3]
    / "crm" / "migrations" / "0024_hug_campaign_authoring.up.sql"
)


@pytest.fixture()
def crm_conn():
    """In-memory crm.db with migration 0024 applied."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(_MIGRATION_PATH.read_text(encoding="utf-8"))
    yield c
    c.close()


def _minimal_campaign(**overrides) -> dict:
    base = {
        "campaign_id": "test-camp-001",
        "name": "Test Campaign",
        "destination_type": "zalo_oa",
        "destination_url": "https://oa.zalo.me/test",
    }
    base.update(overrides)
    return base


# ── render_campaign_list ──────────────────────────────────────────────────────

def test_list_renders_empty_state_message():
    html_out = render_campaign_list([])
    assert "Chưa có campaign nào" in html_out
    assert 'href="/hug/campaign/new"' in html_out


def test_list_renders_campaign_rows():
    campaigns = [
        {
            "campaign_id": "camp-vip",
            "name": "VIP Winback",
            "priority": 10,
            "status": "active",
            "destination_type": "zalo_oa",
            "targeting": '{"tier": ["VIP"]}',
        }
    ]
    html_out = render_campaign_list(campaigns)
    assert "VIP Winback" in html_out
    assert "camp-vip" in html_out
    assert "Đang chạy" in html_out
    assert "Zalo OA" in html_out


def test_list_renders_status_badge_for_all_statuses():
    campaigns = [
        {"campaign_id": "a", "name": "A", "priority": 1, "status": "active",
         "destination_type": "url", "targeting": "{}"},
        {"campaign_id": "b", "name": "B", "priority": 2, "status": "paused",
         "destination_type": "url", "targeting": "{}"},
        {"campaign_id": "c", "name": "C", "priority": 3, "status": "archived",
         "destination_type": "url", "targeting": "{}"},
    ]
    html_out = render_campaign_list(campaigns)
    assert "Đang chạy" in html_out
    assert "Tạm dừng" in html_out
    assert "Đã lưu trữ" in html_out


def test_list_renders_flash_message():
    html_out = render_campaign_list([], flash="Đã tạo thành công", flash_ok=True)
    assert "Đã tạo thành công" in html_out
    # ok flash uses green class
    assert 'class="flash ok"' in html_out


def test_list_flash_warn_class_when_not_ok():
    html_out = render_campaign_list([], flash="Đẩy D1 thất bại", flash_ok=False)
    assert 'class="flash warn"' in html_out


def test_list_escapes_html_in_campaign_name():
    campaigns = [
        {"campaign_id": "x", "name": "<script>alert(1)</script>", "priority": 1,
         "status": "active", "destination_type": "url", "targeting": "{}"},
    ]
    html_out = render_campaign_list(campaigns)
    assert "<script>" not in html_out
    assert "&lt;script&gt;" in html_out


# ── render_campaign_form ──────────────────────────────────────────────────────

def test_form_renders_one_control_per_catalog_attribute():
    """Every attribute in TARGETING_CATALOG must appear in the form output."""
    html_out = render_campaign_form(
        campaign=None,
        errors=[],
        catalog=TARGETING_CATALOG,
        suggested_priority=10,
        is_new=True,
    )
    for attr in TARGETING_CATALOG:
        assert attr in html_out, f"Catalog attribute '{attr}' missing from form output"


def test_form_renders_list_attr_as_checkboxes():
    """List-type attributes must use checkboxes so multiple values can be selected."""
    html_out = render_campaign_form(
        campaign=None,
        errors=[],
        catalog=TARGETING_CATALOG,
        suggested_priority=10,
        is_new=True,
    )
    # tier is a list attr — its values must appear as checkbox inputs
    assert 'name="val_tier"' in html_out
    assert 'type="checkbox"' in html_out
    assert "VIP" in html_out
    assert "CORE" in html_out


def test_form_renders_range_attr_with_gte_lte_inputs():
    """recency_days is a range attr — must render numeric gte/lte inputs."""
    html_out = render_campaign_form(
        campaign=None,
        errors=[],
        catalog=TARGETING_CATALOG,
        suggested_priority=10,
        is_new=True,
    )
    assert 'name="gte_recency_days"' in html_out
    assert 'name="lte_recency_days"' in html_out
    assert 'type="number"' in html_out


def test_form_shows_operators_for_is_contactable():
    """is_contactable is a list attr with values [0, 1] — must have checkboxes."""
    html_out = render_campaign_form(
        campaign=None,
        errors=[],
        catalog=TARGETING_CATALOG,
        suggested_priority=10,
        is_new=True,
    )
    assert 'name="val_is_contactable"' in html_out


def test_form_shows_errors_banner():
    html_out = render_campaign_form(
        campaign=None,
        errors=["unknown attribute 'foo'", "'tier': list must not be empty"],
        catalog=TARGETING_CATALOG,
        suggested_priority=10,
        is_new=True,
    )
    assert "unknown attribute" in html_out
    assert "err-banner" in html_out


def test_form_prefills_existing_campaign_values():
    campaign = {
        "campaign_id": "vip-winback",
        "name": "VIP Winback",
        "destination_type": "zalo_oa",
        "destination_url": "https://oa.zalo.me/test",
        "priority": 10,
        "status": "active",
        "targeting": '{"tier": ["VIP", "CORE"]}',
        "offer_ref": "HUG50",
        "quota_total": 500,
        "schedule_start": None,
        "schedule_end": None,
    }
    html_out = render_campaign_form(
        campaign=campaign,
        errors=[],
        catalog=TARGETING_CATALOG,
        suggested_priority=20,
        is_new=False,
    )
    assert "VIP Winback" in html_out
    assert "HUG50" in html_out
    assert "vip-winback" in html_out
    # In edit mode campaign_id is in a read-only field, not a text input
    assert 'type="text"' not in html_out.split('campaign_id')[0].split('<input')[-1] or \
           'readonly-field' in html_out


def test_form_new_mode_has_editable_campaign_id_field():
    html_out = render_campaign_form(
        campaign=None,
        errors=[],
        catalog=TARGETING_CATALOG,
        suggested_priority=10,
        is_new=True,
    )
    # New mode: campaign_id must be an editable text input, not a read-only div.
    assert 'name="campaign_id"' in html_out
    # The read-only div element itself must not be present (CSS class can appear in <style>).
    assert '<div class="readonly-field">' not in html_out


def test_form_edit_mode_has_readonly_campaign_id():
    campaign = _minimal_campaign()
    html_out = render_campaign_form(
        campaign=campaign,
        errors=[],
        catalog=TARGETING_CATALOG,
        suggested_priority=10,
        is_new=False,
    )
    assert "readonly-field" in html_out


# ── render_status_result ──────────────────────────────────────────────────────

def test_status_result_auto_redirects():
    html_out = render_status_result("camp-abc", "paused", push_ok=True)
    assert 'http-equiv="refresh"' in html_out
    assert "/hug/campaigns" in html_out


def test_status_result_shows_push_failure_note():
    html_out = render_status_result("camp-abc", "archived", push_ok=False)
    assert "✗" in html_out or "kiểm tra log" in html_out


# ── _targeting_summary ────────────────────────────────────────────────────────

def test_targeting_summary_empty_is_all_customers():
    assert _targeting_summary("{}") == "Tất cả khách"


def test_targeting_summary_renders_list_attr():
    summary = _targeting_summary('{"tier": ["VIP", "CORE"]}')
    assert "VIP" in summary
    assert "CORE" in summary


def test_targeting_summary_renders_range_attr():
    summary = _targeting_summary('{"recency_days": {"gte": 30, "lte": 180}}')
    assert "gte=30" in summary or "30" in summary


def test_targeting_summary_truncates_long_text():
    long_json = json.dumps({
        "tier": ["VIP", "CORE", "CASUAL", "NEW", "SECOND_ORDER", "DORMANT_VALUABLE"],
        "channel": ["shopee", "tiki", "lazada"],
    })
    summary = _targeting_summary(long_json)
    assert len(summary) <= 83  # max_len=80 + "…"


# ── _parse_targeting ──────────────────────────────────────────────────────────

@_router_only
def test_parse_targeting_list_attr_with_selections():
    form = {"val_tier": ["VIP", "CORE"], "val_channel": ["shopee"]}
    targeting = _parse_targeting(form)
    assert targeting["tier"] == ["VIP", "CORE"]
    assert targeting["channel"] == ["shopee"]


@_router_only
def test_parse_targeting_list_attr_empty_means_absent():
    """An unselected list attr must not appear in the targeting dict."""
    form = {}  # no val_tier
    targeting = _parse_targeting(form)
    assert "tier" not in targeting


@_router_only
def test_parse_targeting_range_gte_and_lte():
    form = {"gte_recency_days": ["30"], "lte_recency_days": ["180"]}
    targeting = _parse_targeting(form)
    assert targeting["recency_days"] == {"gte": 30, "lte": 180}


@_router_only
def test_parse_targeting_range_gte_only():
    form = {"gte_recency_days": ["90"], "lte_recency_days": [""]}
    targeting = _parse_targeting(form)
    assert targeting["recency_days"] == {"gte": 90}
    assert "lte" not in targeting["recency_days"]


@_router_only
def test_parse_targeting_range_empty_means_absent():
    form = {"gte_recency_days": [""], "lte_recency_days": [""]}
    targeting = _parse_targeting(form)
    assert "recency_days" not in targeting


@_router_only
def test_parse_targeting_is_contactable_as_string_values():
    """is_contactable values "0"/"1" must survive as-is (edge uses String() coercion)."""
    form = {"val_is_contactable": ["1"]}
    targeting = _parse_targeting(form)
    assert targeting["is_contactable"] == ["1"]


@_router_only
def test_parse_targeting_no_form_fields_gives_empty_dict():
    targeting = _parse_targeting({})
    assert targeting == {}


# ── validate + upsert round-trip ──────────────────────────────────────────────

def test_invalid_targeting_is_rejected_and_not_saved(crm_conn):
    """validate_targeting errors must prevent upsert_campaign from being called."""
    from hug.targeting_catalog import validate_targeting

    # is_contactable value "2" is out of domain [0, 1]
    bad_targeting = {"is_contactable": ["2"]}
    errors = validate_targeting(bad_targeting)
    assert errors, "expected validation errors for out-of-domain value"

    # Row must NOT be saved when there are validation errors
    count_before = crm_conn.execute("SELECT COUNT(*) FROM crm_hug_campaign").fetchone()[0]
    assert count_before == 0  # guard: start with empty table

    # Simulate what the router does: only upsert when errors is empty
    if not errors:
        upsert_campaign(crm_conn, _minimal_campaign())

    count_after = crm_conn.execute("SELECT COUNT(*) FROM crm_hug_campaign").fetchone()[0]
    assert count_after == 0, "campaign must not be saved when targeting is invalid"


def test_valid_targeting_is_saved_to_crm_db(crm_conn):
    """A valid campaign row must be persisted to crm.db after upsert."""
    from hug.targeting_catalog import validate_targeting

    good_targeting = {"tier": ["VIP", "CORE"], "recency_days": {"gte": 30}}
    errors = validate_targeting(good_targeting)
    assert not errors

    row = _minimal_campaign(
        targeting=json.dumps(good_targeting, ensure_ascii=False),
        priority=20,
    )
    saved = upsert_campaign(crm_conn, row)
    assert saved["campaign_id"] == "test-camp-001"

    # Verify the row is actually in crm.db
    fetched = get_campaign(crm_conn, "test-camp-001")
    assert fetched is not None
    assert json.loads(fetched["targeting"]) == good_targeting


def test_unknown_attribute_rejected_by_validate_targeting():
    from hug.targeting_catalog import validate_targeting
    errors = validate_targeting({"non_existent_attr": ["foo"]})
    assert any("unknown attribute" in e for e in errors)


# ── push mock: push_campaign called after valid save ─────────────────────────

@_router_only
def test_valid_save_attempts_push(crm_conn):
    """After a successful upsert, push_campaign must be called with the saved row."""
    from hug.targeting_catalog import validate_targeting
    from adapters.inbound.web.screens.hug.screen_hug_campaign import _attempt_push

    row = _minimal_campaign(targeting='{"tier": ["VIP"]}', priority=10)
    errors = validate_targeting(json.loads(row["targeting"]))
    assert not errors

    saved = upsert_campaign(crm_conn, row)

    with patch("adapters.inbound.web.screens.hug.screen_hug_campaign.push_campaign") as mock_push:
        mock_push.return_value = {"ok": True, "skipped": False}
        result = _attempt_push(dict(saved))
        mock_push.assert_called_once()
        call_arg = mock_push.call_args[0][0]
        assert call_arg["campaign_id"] == "test-camp-001"
    assert result is True


@_router_only
def test_push_failure_does_not_crash_and_returns_false(crm_conn):
    """A push network error must be swallowed; local save already committed."""
    from adapters.inbound.web.screens.hug.screen_hug_campaign import _attempt_push

    row = _minimal_campaign()
    saved = upsert_campaign(crm_conn, row)

    with patch("adapters.inbound.web.screens.hug.screen_hug_campaign.push_campaign") as mock_push:
        mock_push.return_value = {"ok": False, "skipped": False, "error": "timeout"}
        result = _attempt_push(dict(saved))
    assert result is False
    # Row must still be present in DB despite push failure
    assert get_campaign(crm_conn, "test-camp-001") is not None


# ── guard: make_hug_campaign_router returns a non-None APIRouter ─────────────

def test_make_hug_campaign_router_returns_non_none(crm_conn):
    """make_hug_campaign_router MUST return an APIRouter, never None.

    A None return causes FastAPI's include_router(None) to raise or silently
    disable all routes registered after that point. The assert in composition.py
    provides runtime protection; this test provides import-time protection.
    """
    try:
        from fastapi import APIRouter
        from adapters.inbound.web.screens.hug.screen_hug_campaign import make_hug_campaign_router
        from adapters.outbound.sqlite.hug_campaign_repository_adapter import HugCampaignRepositoryAdapter
        port = HugCampaignRepositoryAdapter(crm_conn)
        result = make_hug_campaign_router(port)
        assert result is not None, "make_hug_campaign_router must not return None"
        assert isinstance(result, APIRouter), (
            f"Expected APIRouter, got {type(result).__name__}"
        )
    except ImportError:
        pytest.skip("FastAPI not available in this Python environment")


# ── _safe_campaign_id ─────────────────────────────────────────────────────────

@_router_only
def test_safe_campaign_id_accepts_valid_slugs():
    assert _safe_campaign_id("vip-winback-001") == "vip-winback-001"
    assert _safe_campaign_id("CampaignA_v2") == "CampaignA_v2"
    assert _safe_campaign_id("abc123") == "abc123"


@_router_only
def test_safe_campaign_id_rejects_invalid_slugs():
    assert _safe_campaign_id("bad id with spaces") is None
    assert _safe_campaign_id("bad/path") is None
    assert _safe_campaign_id("../traversal") is None
    assert _safe_campaign_id("") is None
    assert _safe_campaign_id("a" * 129) is None  # exceeds 128 chars


# ── _build_row ────────────────────────────────────────────────────────────────

@_router_only
def test_build_row_assembles_correct_dict():
    form = {
        "name": ["My Campaign"],
        "destination_type": ["zalo_oa"],
        "destination_url": ["https://oa.zalo.me/x"],
        "status": ["active"],
        "priority": ["25"],
        "offer_ref": ["HUG50"],
        "quota_total": ["200"],
        "schedule_start": [""],
        "schedule_end": [""],
    }
    targeting = {"tier": ["VIP"]}
    row = _build_row("camp-new", form, targeting)

    assert row["campaign_id"] == "camp-new"
    assert row["name"] == "My Campaign"
    assert row["priority"] == 25
    assert row["offer_ref"] == "HUG50"
    assert row["quota_total"] == 200
    assert row["schedule_start"] is None
    assert json.loads(row["targeting"]) == {"tier": ["VIP"]}


@_router_only
def test_build_row_handles_missing_optional_fields():
    form = {
        "name": ["Minimal"],
        "destination_type": ["url"],
        "destination_url": ["https://example.com"],
        "status": ["active"],
        "priority": ["100"],
    }
    row = _build_row("camp-min", form, {})
    assert row["offer_ref"] is None
    assert row["quota_total"] is None
    assert row["schedule_start"] is None
    assert row["targeting"] == "{}"


# ── render_preview_panel (Phase 5) ────────────────────────────────────────────

def test_preview_panel_empty_inputs_returns_empty_string():
    """No preview, no overlaps → panel is empty (nothing injected into form)."""
    out = render_preview_panel(preview={}, overlaps=[], new_priority=100)
    assert out.strip() == ""


def test_preview_panel_shows_matched_count():
    preview = {"matched": 42, "total": 7500, "sample": []}
    out = render_preview_panel(preview=preview, overlaps=[], new_priority=100)
    assert "42" in out
    assert "7500" in out


def test_preview_panel_shows_sample_rows():
    preview = {
        "matched": 1, "total": 1,
        "sample": [{"customer_id": 999, "tier": "VIP", "recency_days": 15,
                    "value_group": "HIGH", "is_contactable": 1}],
    }
    out = render_preview_panel(preview=preview, overlaps=[], new_priority=100)
    assert "999" in out
    assert "VIP" in out
    assert "HIGH" in out


def test_preview_panel_shows_upper_bound_warning():
    """op_type/channel upper-bound notice must appear when flagged."""
    preview = {
        "matched": 100, "total": 200, "sample": [],
        "upper_bound_warning": "op_type là thuộc tính theo lượt quét",
    }
    out = render_preview_panel(preview=preview, overlaps=[], new_priority=100)
    assert "op_type" in out
    assert "upper_bound_warning" not in out  # key name must not leak into HTML


def test_preview_panel_shows_error_gracefully():
    """cache.db unavailable → error message shown, no exception."""
    preview = {"error": "cache.db unavailable: no such file", "matched": 0, "total": 0, "sample": []}
    out = render_preview_panel(preview=preview, overlaps=[], new_priority=100)
    assert "unavailable" in out or "cache.db" in out


def test_preview_panel_shows_overlap_warning_with_name():
    overlaps = [{"campaign_id": "other-camp", "name": "Other VIP", "priority": 10}]
    out = render_preview_panel(preview={}, overlaps=overlaps, new_priority=100)
    assert "Other VIP" in out
    assert "other-camp" in out


def test_preview_panel_overlap_shadow_direction_other_wins():
    """Other campaign has lower priority number (higher precedence) → shadow note."""
    overlaps = [{"campaign_id": "high-prio", "name": "Flash Sale", "priority": 5}]
    out = render_preview_panel(preview={}, overlaps=overlaps, new_priority=100)
    # Priority 5 < 100 → other campaign wins
    assert "Flash Sale" in out
    assert "ưu tiên cao hơn" in out or "thắng" in out


def test_preview_panel_overlap_shadow_direction_new_wins():
    """New campaign has lower priority number → new campaign wins."""
    overlaps = [{"campaign_id": "low-prio", "name": "Fallback", "priority": 200}]
    out = render_preview_panel(preview={}, overlaps=overlaps, new_priority=10)
    assert "Fallback" in out
    assert "ưu tiên thấp hơn" in out or "thắng" in out


def test_form_includes_preview_button():
    """The 'Xem trước' button must be present in the rendered form."""
    out = render_campaign_form(
        campaign=None, errors=[], catalog=TARGETING_CATALOG,
        suggested_priority=10, is_new=True,
    )
    assert "Xem trước" in out
    assert 'value="preview"' in out
    assert 'value="save"' in out


def test_form_injects_preview_panel_when_provided():
    """When preview result is supplied, the panel HTML must appear inside the page."""
    preview = {"matched": 55, "total": 7500, "sample": []}
    out = render_campaign_form(
        campaign=None, errors=[], catalog=TARGETING_CATALOG,
        suggested_priority=10, is_new=True,
        preview=preview, overlaps=[],
    )
    assert "55" in out
    assert "7500" in out


# ── Phase 6: history page HTML ────────────────────────────────────────────────

from adapters.inbound.web.screens.hug.screen_hug_campaign_html_history import render_history_page  # noqa: E402


class _FakeRow(dict):
    """dict subclass that also supports attribute access for sqlite3.Row compat."""
    def __getitem__(self, key):
        return super().__getitem__(key)


def _make_snap_row(snap_id: int, campaign_id: str, name: str, saved_at: str,
                   status: str = "active", targeting: str = "{}") -> _FakeRow:
    """Build a fake history row matching the crm_hug_campaign_history schema."""
    import json
    snapshot = json.dumps({
        "campaign_id": campaign_id,
        "name": name,
        "status": status,
        "targeting": targeting,
    })
    return _FakeRow(id=snap_id, campaign_id=campaign_id, snapshot=snapshot, saved_at=saved_at)


def test_history_page_renders_empty_state():
    out = render_history_page("camp-001", [])
    assert "camp-001" in out
    assert "Chưa có lịch sử" in out


def test_history_page_renders_snapshot_rows():
    snaps = [
        _make_snap_row(1, "camp-001", "Version A", "2026-06-20T10:00:00Z"),
        _make_snap_row(2, "camp-001", "Version B", "2026-06-20T11:00:00Z"),
    ]
    out = render_history_page("camp-001", snaps)
    assert "Version A" in out
    assert "Version B" in out
    assert "Khôi phục" in out


def test_history_page_has_restore_post_forms():
    snaps = [_make_snap_row(7, "camp-abc", "My Camp", "2026-06-01T00:00:00Z")]
    out = render_history_page("camp-abc", snaps)
    # Each restore form POSTs to the correct endpoint.
    assert 'action="/hug/campaign/camp-abc/restore/7"' in out
    assert 'method="post"' in out


def test_history_page_has_back_link_to_edit():
    out = render_history_page("my-camp", [])
    assert "/hug/campaign/my-camp/edit" in out


def test_history_page_escapes_html_in_campaign_id():
    out = render_history_page("<script>", [])
    assert "<script>" not in out.split("<style>")[1]  # not in body/attrs after <style>
    assert "&lt;script&gt;" in out


# ── Phase 6: edit form has "Lịch sử" link ─────────────────────────────────────

def test_edit_form_shows_history_link():
    campaign = _minimal_campaign()
    out = render_campaign_form(
        campaign=campaign, errors=[], catalog=TARGETING_CATALOG,
        suggested_priority=10, is_new=False,
    )
    assert "/history" in out
    assert "Lịch sử" in out


def test_new_form_has_no_history_link():
    out = render_campaign_form(
        campaign=None, errors=[], catalog=TARGETING_CATALOG,
        suggested_priority=10, is_new=True,
    )
    # New campaigns have no history; the link must be absent.
    assert "Lịch sử" not in out


# ── Phase 6: flash banner on edit form ────────────────────────────────────────

def test_edit_form_shows_flash_green_on_success():
    campaign = _minimal_campaign()
    out = render_campaign_form(
        campaign=campaign, errors=[], catalog=TARGETING_CATALOG,
        suggested_priority=10, is_new=False,
        flash="Đã khôi phục phiên bản #3. Đẩy D1: ✓",
        flash_ok=True,
    )
    assert "Đã khôi phục" in out
    assert "#14532d" in out  # green background


def test_edit_form_shows_flash_amber_on_failure():
    campaign = _minimal_campaign()
    out = render_campaign_form(
        campaign=campaign, errors=[], catalog=TARGETING_CATALOG,
        suggested_priority=10, is_new=False,
        flash="Đẩy D1: ✗",
        flash_ok=False,
    )
    assert "#78350f" in out  # amber background


# ── Phase 6: priority duplicate warning ──────────────────────────────────────

def test_priority_duplicate_warning_no_collision(crm_conn):
    """No other campaign at same priority → no warning."""
    from adapters.inbound.web.screens.hug.screen_hug_campaign_form_helpers import priority_duplicate_warning
    from adapters.outbound.sqlite.hug_campaign_repository_adapter import HugCampaignRepositoryAdapter
    port = HugCampaignRepositoryAdapter(crm_conn)
    upsert_campaign(crm_conn, _minimal_campaign(priority=50))
    # Checking own ID against itself must produce no warning.
    warn = priority_duplicate_warning(port, 50, "test-camp-001")
    assert warn == ""


def test_priority_duplicate_warning_collision_detected(crm_conn):
    """Another active campaign at same priority → warning mentions its name + next suggestion."""
    from adapters.inbound.web.screens.hug.screen_hug_campaign_form_helpers import priority_duplicate_warning
    from adapters.outbound.sqlite.hug_campaign_repository_adapter import HugCampaignRepositoryAdapter
    port = HugCampaignRepositoryAdapter(crm_conn)
    upsert_campaign(crm_conn, _minimal_campaign(campaign_id="camp-a", priority=50))
    upsert_campaign(crm_conn, _minimal_campaign(campaign_id="camp-b", name="Camp B", priority=50))
    # camp-b shares priority with camp-a — checking from camp-a's perspective.
    warn = priority_duplicate_warning(port, 50, "camp-a")
    assert "Camp B" in warn
    assert "⚠️" in warn
    # Suggestion should be present (MAX+10 = 50+10 = 60).
    assert "60" in warn


def test_priority_duplicate_warning_archived_ignored(crm_conn):
    """Archived campaign at same priority must not trigger a warning."""
    from adapters.inbound.web.screens.hug.screen_hug_campaign_form_helpers import priority_duplicate_warning
    from adapters.outbound.sqlite.hug_campaign_repository_adapter import HugCampaignRepositoryAdapter
    from hug.campaign_repository import archive_campaign
    port = HugCampaignRepositoryAdapter(crm_conn)
    upsert_campaign(crm_conn, _minimal_campaign(campaign_id="camp-live", priority=30))
    upsert_campaign(crm_conn, _minimal_campaign(campaign_id="camp-dead", name="Dead", priority=30))
    archive_campaign(crm_conn, "camp-dead")
    warn = priority_duplicate_warning(port, 30, "camp-live")
    assert warn == ""


# ── Phase 6: restore + history integration (FastAPI-free) ────────────────────

def test_restore_reverts_fields_and_appends_history(crm_conn):
    """Restore a snapshot: the campaign row reverts to the older state + new history row added."""
    from hug.campaign_repository import restore_snapshot

    # Save V1 then V2.
    upsert_campaign(crm_conn, _minimal_campaign(name="V1 Name", priority=10))
    upsert_campaign(crm_conn, _minimal_campaign(name="V2 Name", priority=20))

    # V1 snapshot is the oldest → last in list (list_history returns newest-first).
    from hug.campaign_repository import list_history
    hist = list_history(crm_conn, "test-camp-001")
    assert len(hist) == 2  # V1 + V2
    v1_snap_id = hist[-1]["id"]  # oldest = V1

    restored = restore_snapshot(crm_conn, "test-camp-001", v1_snap_id)
    assert restored["name"] == "V1 Name"
    assert restored["priority"] == 10

    # A new history row must have been appended (total = 3: V1, V2, restore).
    hist_after = list_history(crm_conn, "test-camp-001")
    assert len(hist_after) == 3


def test_restore_triggers_push(crm_conn):
    """Restore must call push_campaign with the restored row (best-effort)."""
    from hug.campaign_repository import restore_snapshot, list_history
    from adapters.inbound.web.screens.hug.screen_hug_campaign_form_helpers import attempt_push

    upsert_campaign(crm_conn, _minimal_campaign(name="V1"))
    upsert_campaign(crm_conn, _minimal_campaign(name="V2"))
    hist = list_history(crm_conn, "test-camp-001")
    v1_snap_id = hist[-1]["id"]

    restored = restore_snapshot(crm_conn, "test-camp-001", v1_snap_id)

    with patch("adapters.inbound.web.screens.hug.screen_hug_campaign_form_helpers.push_campaign") as mock_push:
        mock_push.return_value = {"ok": True, "skipped": False}
        result = attempt_push(dict(restored))
        mock_push.assert_called_once()
        call_arg = mock_push.call_args[0][0]
        assert call_arg["campaign_id"] == "test-camp-001"
    assert result is True


def test_suggest_next_priority_non_colliding(crm_conn):
    """suggest_next_priority always returns a value > current max priority."""
    upsert_campaign(crm_conn, _minimal_campaign(campaign_id="c1", priority=50))
    upsert_campaign(crm_conn, _minimal_campaign(campaign_id="c2", priority=70))
    from hug.campaign_repository import suggest_next_priority
    suggestion = suggest_next_priority(crm_conn)
    assert suggestion > 70
    # Must not collide with any existing priority.
    from hug.campaign_repository import list_campaigns
    existing_priorities = {r["priority"] for r in list_campaigns(crm_conn)}
    assert suggestion not in existing_priorities
