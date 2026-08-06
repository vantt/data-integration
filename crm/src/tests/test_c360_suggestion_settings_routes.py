"""test_c360_suggestion_settings_routes.py — plan 260805-1216 phase-06, route matrix R1-R9.

Builds a minimal FastAPI app with only screen_customer_360_suggestion_settings's routes
registered (mirrors test_claim_context_snooze_r14.py's _build_cockpit_app pattern) — a
real Jinja2Templates against the actual templates dir, a mocked SuggestionSettingsSvc.
"""
from __future__ import annotations

import pathlib
import sys
from unittest.mock import MagicMock

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import APIRouter, FastAPI                                        # noqa: E402
from fastapi.testclient import TestClient                                     # noqa: E402
from fastapi.templating import Jinja2Templates                                # noqa: E402

from adapters.inbound.web.screens.customer360.screen_customer_360_suggestion_settings import (  # noqa: E402
    register_suggestion_settings_routes,
)
from application.suggestion_settings_service import (                        # noqa: E402
    SuggestionSettingGroup, SuggestionSettingRow,
)

_TEMPLATES_DIR = str(
    pathlib.Path(__file__).parents[1] / "adapters" / "inbound" / "web" / "templates"
)
_PARTY_ID = "party-p07-1"


def _make_templates() -> Jinja2Templates:
    import jinja2
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(_TEMPLATES_DIR),
        autoescape=True,
        auto_reload=False,
    )
    return Jinja2Templates(env=env)


def _build_app(settings_svc, dnc_reader=None, activity_log=None):
    templates = _make_templates()
    app = FastAPI()
    router = APIRouter()
    register_suggestion_settings_routes(
        router, templates, settings_svc=settings_svc,
        dnc_reader=dnc_reader, activity_log=activity_log,
    )
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def _one_active_row() -> list[SuggestionSettingGroup]:
    return [SuggestionSettingGroup(scenario_group="at_risk", rows=[
        SuggestionSettingRow(
            action_type="CALL_NOW", source_mart="mart_customer_action_queue",
            description_vi="VIP dang nguoi goi ngay", is_globally_disabled=False,
            is_suppressed=False, is_expired=False, until_date_ict=None, set_by_display=None,
        ),
    ])]


def _one_suppressed_row() -> list[SuggestionSettingGroup]:
    return [SuggestionSettingGroup(scenario_group="at_risk", rows=[
        SuggestionSettingRow(
            action_type="CALL_NOW", source_mart="mart_customer_action_queue",
            description_vi="VIP dang nguoi goi ngay", is_globally_disabled=False,
            is_suppressed=True, is_expired=False, until_date_ict="2026-12-31",
            set_by_display="Lan",
        ),
    ])]


class TestPanelRender:
    def test_r1_get_panel_lists_rows_grouped(self):
        # render_panel isn't a registered GET route (dispatched from
        # screen_customer_360_panels in the real app) — call it directly via the
        # module's return value instead.
        import asyncio
        from unittest.mock import MagicMock as M
        svc = MagicMock()
        svc.get_settings.return_value = _one_active_row()
        templates = _make_templates()
        router = APIRouter()
        render_panel = register_suggestion_settings_routes(router, templates, settings_svc=svc)

        request = M()
        request.state = M()
        request.state.current_user = None
        resp = asyncio.run(render_panel(request, _PARTY_ID))
        body = resp.body.decode()
        assert resp.status_code == 200
        assert "Đang bật" in body
        assert "VIP dang nguoi goi ngay" in body

    def test_r2_empty_catalog_shows_empty_state(self):
        import asyncio
        svc = MagicMock()
        svc.get_settings.return_value = []
        templates = _make_templates()
        router = APIRouter()
        render_panel = register_suggestion_settings_routes(router, templates, settings_svc=svc)
        request = MagicMock()
        request.state.current_user = None
        resp = asyncio.run(render_panel(request, _PARTY_ID))
        assert resp.status_code == 200
        assert "chưa được đồng bộ" in resp.body.decode()


class TestSuppressRoute:
    def test_r3_suppress_valid_writes_and_rerenders(self):
        svc = MagicMock()
        svc.suppress.return_value = None
        svc.get_settings.return_value = _one_suppressed_row()
        client = _build_app(svc)

        r = client.post(
            f"/customers/{_PARTY_ID}/suggestion-settings/suppress",
            data={"action_type": "CALL_NOW", "source_mart": "mart_customer_action_queue",
                  "until_date": "2026-12-31"},
        )
        assert r.status_code == 200
        assert "Đã tắt tới" in r.text
        svc.suppress.assert_called_once_with(
            _PARTY_ID, "CALL_NOW", "mart_customer_action_queue", "2026-12-31", None
        )

    def test_r4_unknown_action_type_returns_400_vietnamese(self):
        svc = MagicMock()
        svc.suppress.side_effect = ValueError("Không tìm thấy loại gợi ý (X, Y) trong danh mục")
        client = _build_app(svc)

        r = client.post(
            f"/customers/{_PARTY_ID}/suggestion-settings/suppress",
            data={"action_type": "NOT_REAL", "source_mart": "mart_customer_action_queue",
                  "until_date": "2026-12-31"},
        )
        assert r.status_code == 400
        assert "Không tìm thấy" in r.text
        svc.get_settings.assert_not_called()  # no re-render on failure

    def test_r5_globally_disabled_returns_400(self):
        svc = MagicMock()
        svc.suppress.side_effect = ValueError("GIFT_TO_PURCHASE đang tắt toàn hệ thống — không thể tắt riêng cho khách")
        client = _build_app(svc)

        r = client.post(
            f"/customers/{_PARTY_ID}/suggestion-settings/suppress",
            data={"action_type": "GIFT_TO_PURCHASE", "source_mart": "mart_customer_sku_action_queue",
                  "until_date": "2026-12-31"},
        )
        assert r.status_code == 400

    def test_r6_past_date_returns_400(self):
        svc = MagicMock()
        svc.suppress.side_effect = ValueError("Ngày kết thúc phải ở tương lai")
        client = _build_app(svc)

        r = client.post(
            f"/customers/{_PARTY_ID}/suggestion-settings/suppress",
            data={"action_type": "CALL_NOW", "source_mart": "mart_customer_action_queue",
                  "until_date": "2020-01-01"},
        )
        assert r.status_code == 400

    def test_r8_resuppress_overwrites_via_same_route(self):
        """Row pre-created by quick-dismiss or a prior suppress call — POST suppress again
        overwrites (same underlying table, verified at the service layer in Phase 04; here
        we only confirm the route calls suppress() again rather than special-casing)."""
        svc = MagicMock()
        svc.get_settings.return_value = _one_suppressed_row()
        client = _build_app(svc)

        for until in ("2026-09-01", "2026-12-31"):
            r = client.post(
                f"/customers/{_PARTY_ID}/suggestion-settings/suppress",
                data={"action_type": "CALL_NOW", "source_mart": "mart_customer_action_queue",
                      "until_date": until},
            )
            assert r.status_code == 200
        assert svc.suppress.call_count == 2

    def test_r9_no_current_user_passes_none_owner(self):
        """No request.state.current_user (unauthenticated dev/test path) -> user_id
        argument is None, never "" (FK requires NULL or a real user_id)."""
        svc = MagicMock()
        svc.get_settings.return_value = _one_suppressed_row()
        client = _build_app(svc)

        r = client.post(
            f"/customers/{_PARTY_ID}/suggestion-settings/suppress",
            data={"action_type": "CALL_NOW", "source_mart": "mart_customer_action_queue",
                  "until_date": "2026-12-31"},
        )
        assert r.status_code == 200
        args = svc.suppress.call_args[0]
        assert args[-1] is None


class TestUnsuppressRoute:
    def test_r7_unsuppress_deletes_and_rerenders(self):
        svc = MagicMock()
        svc.unsuppress.return_value = None
        svc.get_settings.return_value = _one_active_row()
        client = _build_app(svc)

        r = client.post(
            f"/customers/{_PARTY_ID}/suggestion-settings/unsuppress",
            data={"action_type": "CALL_NOW", "source_mart": "mart_customer_action_queue"},
        )
        assert r.status_code == 200
        assert "Đã tắt tới" not in r.text
        svc.unsuppress.assert_called_once_with(_PARTY_ID, "CALL_NOW", "mart_customer_action_queue")


class TestBulkSuppressRoute:
    def test_r10_bulk_suppress_applies_date_to_every_checked_row(self):
        svc = MagicMock()
        svc.get_settings.return_value = _one_active_row()
        client = _build_app(svc)

        r = client.post(
            f"/customers/{_PARTY_ID}/suggestion-settings/bulk-suppress",
            data={
                "row_keys": ["CALL_NOW|mart_customer_action_queue", "WIN_BACK|mart_customer_action_queue"],
                "until_date": "2026-12-31",
            },
        )
        assert r.status_code == 200
        assert svc.suppress.call_count == 2
        svc.suppress.assert_any_call(_PARTY_ID, "CALL_NOW", "mart_customer_action_queue", "2026-12-31", None)
        svc.suppress.assert_any_call(_PARTY_ID, "WIN_BACK", "mart_customer_action_queue", "2026-12-31", None)

    def test_r11_bulk_suppress_no_rows_selected_returns_400(self):
        svc = MagicMock()
        client = _build_app(svc)

        r = client.post(
            f"/customers/{_PARTY_ID}/suggestion-settings/bulk-suppress",
            data={"until_date": "2026-12-31"},
        )
        assert r.status_code == 400
        svc.suppress.assert_not_called()

    def test_r12_bulk_suppress_no_date_returns_400(self):
        svc = MagicMock()
        client = _build_app(svc)

        r = client.post(
            f"/customers/{_PARTY_ID}/suggestion-settings/bulk-suppress",
            data={"row_keys": ["CALL_NOW|mart_customer_action_queue"]},
        )
        assert r.status_code == 400
        svc.suppress.assert_not_called()

    def test_bulk_suppress_one_row_failing_does_not_block_the_rest(self):
        svc = MagicMock()
        svc.get_settings.return_value = _one_active_row()
        svc.suppress.side_effect = [ValueError("bad row"), None]
        client = _build_app(svc)

        r = client.post(
            f"/customers/{_PARTY_ID}/suggestion-settings/bulk-suppress",
            data={
                "row_keys": ["NOT_REAL|mart_customer_action_queue", "CALL_NOW|mart_customer_action_queue"],
                "until_date": "2026-12-31",
            },
        )
        assert r.status_code == 200
        assert svc.suppress.call_count == 2


class TestDoNotContactRoute:
    def test_r13_do_not_contact_logs_activity_with_correct_shape(self):
        svc = MagicMock()
        svc.get_settings.return_value = _one_active_row()
        activity_log = MagicMock()
        client = _build_app(svc, activity_log=activity_log)

        r = client.post(f"/customers/{_PARTY_ID}/suggestion-settings/do-not-contact")
        assert r.status_code == 200
        activity_log.log_activity.assert_called_once()
        payload = activity_log.log_activity.call_args[0][0]
        assert payload["party_id"] == _PARTY_ID
        assert payload["contact_outcome"] == "refused"
        assert payload["outcome_reason"] == "do_not_contact"
        assert payload["staff_user_id"] is None  # no current_user in this test app

    def test_do_not_contact_service_unavailable_returns_503(self):
        svc = MagicMock()
        client = _build_app(svc, activity_log=None)

        r = client.post(f"/customers/{_PARTY_ID}/suggestion-settings/do-not-contact")
        assert r.status_code == 503

    def test_do_not_contact_failure_returns_400(self):
        svc = MagicMock()
        activity_log = MagicMock()
        activity_log.log_activity.side_effect = RuntimeError("db error")
        client = _build_app(svc, activity_log=activity_log)

        r = client.post(f"/customers/{_PARTY_ID}/suggestion-settings/do-not-contact")
        assert r.status_code == 400


class TestDoNotContactBanner:
    def test_r14_panel_shows_dnc_badge_when_party_is_do_not_contact(self):
        import asyncio
        svc = MagicMock()
        svc.get_settings.return_value = _one_active_row()
        dnc_reader = MagicMock()
        dnc_reader.list_do_not_contact_party_ids.return_value = {_PARTY_ID}
        templates = _make_templates()
        router = APIRouter()
        render_panel = register_suggestion_settings_routes(
            router, templates, settings_svc=svc, dnc_reader=dnc_reader,
        )
        request = MagicMock()
        request.state.current_user = None
        resp = asyncio.run(render_panel(request, _PARTY_ID))
        body = resp.body.decode()
        assert "Đang: Đừng gọi nữa" in body
        # Explainer prose mentions the label too — assert on the button's endpoint, not the label text.
        assert "suggestion-settings/do-not-contact" not in body  # button hidden when already set

    def test_r15_panel_shows_button_when_party_not_do_not_contact(self):
        import asyncio
        svc = MagicMock()
        svc.get_settings.return_value = _one_active_row()
        dnc_reader = MagicMock()
        dnc_reader.list_do_not_contact_party_ids.return_value = set()
        templates = _make_templates()
        router = APIRouter()
        render_panel = register_suggestion_settings_routes(
            router, templates, settings_svc=svc, dnc_reader=dnc_reader,
        )
        request = MagicMock()
        request.state.current_user = None
        resp = asyncio.run(render_panel(request, _PARTY_ID))
        body = resp.body.decode()
        assert "suggestion-settings/do-not-contact" in body
        assert "Đang: Đừng gọi nữa" not in body


class TestBulkToolbarMarkup:
    def test_bulk_date_input_has_name_attr_so_hx_include_actually_submits_it(self):
        """Regression guard: hx-include serializes by `name`, not `id`. The bulk-date
        input previously had only `id="p07-bulk-date"` — htmx never sent it, so the
        server always saw until_date missing even though the UI showed a picked date."""
        import asyncio
        svc = MagicMock()
        svc.get_settings.return_value = _one_active_row()
        templates = _make_templates()
        router = APIRouter()
        render_panel = register_suggestion_settings_routes(router, templates, settings_svc=svc)
        request = MagicMock()
        request.state.current_user = None
        resp = asyncio.run(render_panel(request, _PARTY_ID))
        body = resp.body.decode()

        assert 'hx-include="[name=\'row_keys\']:checked, #p07-bulk-date"' in body
        # The element that id-selector targets must itself carry a `name` for
        # htmx's hx-include to serialize it into the request.
        assert 'name="until_date" id="p07-bulk-date"' in body
