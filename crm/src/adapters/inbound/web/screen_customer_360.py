"""Web adapter — S03 Customer 360 Detail screen.

FastAPI router mirroring screen_customer_360.go.
Serves full HTML page + HTMX panel fragments (panels: insight, orders,
timeline, tasks, notes). No business logic — thin adapter only.

Identifier resolution on the full-page route:
  UUID         → direct get_party_360 lookup
  pure digits  → find_by_identity("sapo_customer", value)
  alphanumeric → DuckDB customer_code lookup → sapo_customer identity
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol

_ICT = timezone(timedelta(hours=7))


def _ict_local_to_utc(ict_str: str) -> str:
    """Parse datetime-local input (assumed ICT/UTC+7) → UTC ISO-8601 string."""
    try:
        dt = datetime.strptime(ict_str.strip(), "%Y-%m-%dT%H:%M").replace(tzinfo=_ICT)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except Exception:
        return ""

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from crm.src.domain.entities.activity import Activity
from crm.src.domain.entities.cache_insight import CacheInsight, CustomerDimMetrics
from crm.src.domain.entities.profile import CustomFieldDef, Note, Party360, PartyIdentity, PartyInsight
from crm.src.domain.entities.task import Task

log = logging.getLogger(__name__)

_GEO_HCMC = {'Hồ Chí Minh', 'TP Hồ Chí Minh', 'TP. Hồ Chí Minh', 'HCM', 'Ho Chi Minh'}
_GEO_HANOI = {'Hà Nội', 'Ha Noi', 'Hanoi'}
_GEO_MEKONG = {'An Giang', 'Bạc Liêu', 'Bến Tre', 'Cà Mau', 'Cần Thơ', 'Đồng Tháp', 'Hậu Giang', 'Kiên Giang', 'Long An', 'Sóc Trăng', 'Tiền Giang', 'Trà Vinh', 'Vĩnh Long'}
_GEO_CENTRAL = {'Đà Nẵng', 'Thừa Thiên Huế', 'Quảng Nam', 'Quảng Ngãi', 'Bình Định', 'Phú Yên', 'Khánh Hòa', 'Ninh Thuận', 'Bình Thuận', 'Quảng Bình', 'Quảng Trị', 'Hà Tĩnh', 'Nghệ An', 'Thanh Hóa'}

def _geo_region(province: Optional[str]) -> str:
    if not province:
        return ""
    if province in _GEO_HCMC:
        return "HCMC"
    if province in _GEO_HANOI:
        return "Hà Nội"
    if province in _GEO_MEKONG:
        return "Mekong"
    if province in _GEO_CENTRAL:
        return "Miền Trung"
    return "Khác"

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# ── Service protocols ─────────────────────────────────────────────────────────

class ProfileReader(Protocol):
    def get_party_360(self, party_id: str) -> Optional[Party360]: ...


class PartyFinder(Protocol):
    def find_by_identity(self, identity_type: str, identity_value: str) -> Optional[object]: ...


class CustomerCodeResolver(Protocol):
    def find_customer_id_by_code(self, customer_code: str) -> Optional[str]: ...


class IdentityReader(Protocol):
    def list_identities(self, party_id: str) -> list[PartyIdentity]: ...


class InsightReader(Protocol):
    def get_customer_insight(self, customer_id: int) -> Optional[CacheInsight]: ...


class ActivityReader(Protocol):
    def list_activities(self, party_id: str) -> list[Activity]: ...


class ActivityLogger(Protocol):
    def log_activity(self, activity_data: dict) -> Activity: ...


class NoteReader(Protocol):
    def add_note(self, party_id: str, body: str, author_user_id: Optional[str] = None,
                 note_type: str = "general", pinned: bool = False, visibility: str = "team",
                 source_activity_id: Optional[str] = None) -> Note: ...
    def list_notes(self, party_id: str) -> list[Note]: ...
    def update_note(self, note_id: str, body: str, note_type: str = "general",
                    pinned: bool = False, visibility: str = "team") -> None: ...
    def delete_note(self, note_id: str) -> None: ...


class CustomFieldDefReader(Protocol):
    def list_by_entity_type(self, entity_type: str) -> list[CustomFieldDef]: ...


class PartyInsightReader(Protocol):
    def list_by_party(self, party_id: str) -> list[PartyInsight]: ...


class ActionTaskResolver(Protocol):
    """Returns the set of action_ids that have a resolved CRM task (outcome IS NOT NULL)."""
    def resolved_action_ids(self, party_id: str) -> set[str]: ...


class TaskQuerier(Protocol):
    def list_by_party(self, party_id: str) -> list[Task]: ...


class TaskCreator(Protocol):
    def create_task(self, task_data: dict) -> object: ...
    def get_task(self, task_id: str) -> Optional[object]: ...
    def transition_status(self, task_id: str, new_status: str) -> object: ...
    def update_task(self, task_id: str, data: dict) -> object: ...


class AppUserReader(Protocol):
    def list_active(self) -> list: ...


# ── Router factory ────────────────────────────────────────────────────────────

def make_customer_360_router(
    templates: Jinja2Templates,
    profile: ProfileReader,
    identities: IdentityReader,
    insight: InsightReader,
    activities: ActivityReader,
    activity_log: ActivityLogger,
    notes: NoteReader,
    party_tasks: TaskQuerier,
    custom_field_defs: Optional[CustomFieldDefReader] = None,
    party_insights: Optional[PartyInsightReader] = None,
    action_task_resolver: Optional[ActionTaskResolver] = None,
    party_finder: Optional[PartyFinder] = None,
    customer_code_resolver: Optional[CustomerCodeResolver] = None,
    customer_timeline=None,
    customer_orders=None,
    customer_dim_metrics=None,
    task_svc: Optional[TaskCreator] = None,
    app_users: Optional[AppUserReader] = None,
) -> APIRouter:
    """Return APIRouter wired with all Customer 360 routes."""
    router = APIRouter()

    def _resolve_to_party_id(identifier: str) -> Optional[str]:
        """Resolve any identifier to a party_id string, or None."""
        # 1. UUID → direct
        if _UUID_RE.match(identifier):
            return identifier
        if party_finder is None:
            return None
        # 2. Numeric digits → sapo_customer identity
        if identifier.isdigit():
            party = party_finder.find_by_identity("sapo_customer", identifier)
            if party is not None:
                return getattr(party, "party_id", None)
        # 3. Alphanumeric → customer_code → customer_id → identity
        elif customer_code_resolver is not None:
            try:
                customer_id = customer_code_resolver.find_customer_id_by_code(identifier)
                if customer_id:
                    party = party_finder.find_by_identity("sapo_customer", customer_id)
                    if party is not None:
                        return getattr(party, "party_id", None)
            except Exception as exc:
                log.error("c360 resolve customer_code %r: %s", identifier, exc)
        return None

    def _load_base(party_id: str) -> tuple[Optional[Party360], list[PartyIdentity]]:
        party360 = profile.get_party_360(party_id)
        if party360 is None:
            return None, []
        ids = identities.list_identities(party_id)
        return party360, ids

    def _sapo_customer_id(ids: list[PartyIdentity]) -> int:
        """Resolve Sapo customer_id from a list of party identities; 0 when not found."""
        for pid in ids:
            if pid.identity_type == "sapo_customer":
                try:
                    return int(pid.identity_value)
                except (ValueError, TypeError):
                    pass
        return 0

    def _load_insight(ids: list[PartyIdentity]) -> Optional[CacheInsight]:
        customer_id = _sapo_customer_id(ids)
        if not customer_id:
            return None
        try:
            return insight.get_customer_insight(customer_id)
        except Exception as exc:
            log.warning("c360: load insight for customer_id %d: %s", customer_id, exc)
            return None

    # ── Full page ─────────────────────────────────────────────────────────────

    @router.get("/customers/{identifier}", response_class=HTMLResponse)
    async def handle_customer_360(request: Request, identifier: str) -> Response:
        active_tab = request.query_params.get("tab", "insight")

        # Resolve identifier to party_id (UUID, sapo_customer numeric, or customer_code)
        party_id = _resolve_to_party_id(identifier.strip())
        if party_id is None:
            return HTMLResponse("Không tìm thấy khách hàng", status_code=404)

        party360, ids = _load_base(party_id)
        if party360 is None:
            return HTMLResponse("Không tìm thấy khách hàng", status_code=404)

        ins = _load_insight(ids)

        # Notes split by type for S03 left col (warning banner + contact_pref inline)
        all_notes: list[Note] = []
        try:
            all_notes = notes.list_notes(party_id)
        except Exception as exc:
            log.warning("c360: load notes %s: %s", party_id, exc)

        active_notes = [n for n in all_notes if not n.deleted_at]
        warning_notes = [n for n in active_notes if n.note_type == "warning"]
        contact_pref_notes = [n for n in active_notes if n.note_type == "contact_pref" and n.pinned]

        # Custom field definitions for left col grouped display
        cfd_list: list[CustomFieldDef] = []
        if custom_field_defs is not None:
            try:
                cfd_list = [
                    fd for fd in custom_field_defs.list_by_entity_type("party")
                    if fd.is_active
                ]
            except Exception as exc:
                log.warning("c360: load custom_field_defs: %s", exc)

        return templates.TemplateResponse(
            "customer_360.html",
            {
                "request": request,
                "party": party360,
                "identities": ids,
                "active_tab": active_tab,
                "insight": ins,
                "warning_notes": warning_notes,
                "contact_pref_notes": contact_pref_notes,
                "custom_field_defs": cfd_list,
                "geo_region": _geo_region(party360.province),
            },
        )

    # ── HTMX panel fragments ──────────────────────────────────────────────────

    @router.get("/customers/{party_id}/panels/{panel}", response_class=HTMLResponse)
    async def handle_customer_360_panel(
        request: Request, party_id: str, panel: str
    ) -> Response:
        ctx: dict = {"request": request, "party_id": party_id}
        if panel == "insight":
            _, ids = _load_base(party_id)
            ins = _load_insight(ids)
            rep_ins: list[PartyInsight] = []
            if party_insights is not None:
                try:
                    rep_ins = [
                        i for i in party_insights.list_by_party(party_id)
                        if not i.deleted_at
                    ]
                except Exception as exc:
                    log.warning("c360 insight panel: rep insights %s: %s", party_id, exc)
            resolved_ids: set[str] = set()
            if action_task_resolver is not None:
                try:
                    resolved_ids = action_task_resolver.resolved_action_ids(party_id)
                except Exception as exc:
                    log.warning("c360 insight panel: resolved_ids %s: %s", party_id, exc)
            dim_metrics: Optional[CustomerDimMetrics] = None
            if customer_dim_metrics is not None:
                sapo_id = _sapo_customer_id(ids)
                if sapo_id:
                    try:
                        dim_metrics = customer_dim_metrics.get_by_customer_id(sapo_id)
                    except Exception as exc:
                        log.warning("c360 insight panel: dim_metrics %s: %s", party_id, exc)
            snapshots: list = []
            timeline_available = customer_timeline is not None
            if customer_timeline is not None:
                sapo_id = _sapo_customer_id(ids)
                if sapo_id:
                    try:
                        snapshots = customer_timeline.get_by_customer_id(sapo_id)
                    except Exception as exc:
                        log.warning("c360 insight panel: snapshots %s: %s", party_id, exc)
            return templates.TemplateResponse(
                "fragments/c360_insight_panel.html",
                {**ctx, "insight": ins, "rep_insights": rep_ins, "resolved_action_ids": resolved_ids,
                 "dim_metrics": dim_metrics, "snapshots": snapshots, "timeline_available": timeline_available},
            )
        if panel == "orders":
            _, ids = _load_base(party_id)
            ins = _load_insight(ids)
            orders = ins.recent_orders if ins else []
            if customer_orders is not None:
                customer_id = _sapo_customer_id(ids)
                if customer_id:
                    try:
                        live = customer_orders.get_by_customer_id(customer_id)
                        if live:
                            orders = live
                    except Exception as exc:
                        log.warning("c360 orders panel: live fetch %s: %s", party_id, exc)
            return templates.TemplateResponse(
                "fragments/c360_orders_panel.html", {**ctx, "orders": orders}
            )
        if panel == "timeline":
            acts = activities.list_activities(party_id)
            return templates.TemplateResponse(
                "fragments/c360_timeline_panel.html", {**ctx, "activities": acts}
            )
        if panel == "tasks":
            status_filter = request.query_params.get("filter", "open")
            task_list = party_tasks.list_by_party(party_id)
            user_map: dict = {}
            if app_users is not None:
                try:
                    user_map = {u.user_id: u.full_name for u in app_users.list_active()}
                except Exception as exc:
                    log.warning("c360 tasks: list_active: %s", exc)
            return templates.TemplateResponse(
                "fragments/c360_tasks_panel.html",
                {**ctx, "tasks": task_list, "filter": status_filter, "user_map": user_map,
                 "now_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")},
            )
        if panel == "notes":
            note_list = notes.list_notes(party_id)
            type_filter = request.query_params.get("type_filter", "all")
            return templates.TemplateResponse(
                "fragments/c360_notes_panel.html",
                {**ctx, "notes": note_list, "type_filter": type_filter},
            )
        return HTMLResponse("panel not found", status_code=404)

    # ── M08 modal — serve & tab switching ────────────────────────────────────

    def _m08_ctx(request: Request, party_id: str, mode: str = "log",
                 note_id: str = "", party_name: str = "", task_id: str = "") -> dict:
        # normalize legacy mode names → unified 'log'
        if mode not in ("log", "edit_note", "note_only"):
            mode = "log"
        contact_pref_notes: list[Note] = []
        note_body = ""
        note_type_val = "general"
        note_pinned = False
        note_visibility = "team"
        party_identities: list[PartyIdentity] = []
        task_title = ""
        if mode == "log":
            try:
                contact_pref_notes = [
                    n for n in notes.list_notes(party_id)
                    if not n.deleted_at and n.note_type == "contact_pref" and n.pinned
                ]
            except Exception as exc:
                log.warning("m08: contact_pref_notes %s: %s", party_id, exc)
            try:
                party_identities = identities.list_identities(party_id)
            except Exception as exc:
                log.warning("m08: identities %s: %s", party_id, exc)
            if task_id.strip() and task_svc is not None:
                try:
                    t = task_svc.get_task(task_id.strip())
                    if t is not None:
                        task_title = getattr(t, "title", "")
                except Exception as exc:
                    log.warning("m08: get_task %s: %s", task_id, exc)
        if mode == "edit_note" and note_id:
            try:
                existing = next(
                    (n for n in notes.list_notes(party_id) if n.note_id == note_id), None
                )
                if existing:
                    note_body = existing.body
                    note_type_val = existing.note_type
                    note_pinned = existing.pinned
                    note_visibility = existing.visibility
            except Exception as exc:
                log.warning("m08: load edit_note %s: %s", note_id, exc)
        return {
            "request": request,
            "party_id": party_id,
            "mode": mode,
            "note_id": note_id,
            "party_name": party_name,
            "task_id": task_id,
            "task_title": task_title,
            "identities": party_identities,
            "contact_pref_notes": contact_pref_notes,
            "note_body": note_body,
            "note_type_val": note_type_val,
            "note_pinned": note_pinned,
            "note_visibility": note_visibility,
        }

    @router.get("/modals/m08", response_class=HTMLResponse)
    async def handle_modal_m08(
        request: Request,
        party_id: str,
        mode: str = "activity",
        note_id: str = "",
        party_name: str = "",
        task_id: str = "",
    ) -> Response:
        return templates.TemplateResponse(
            "fragments/modal_log_activity.html",
            _m08_ctx(request, party_id, mode, note_id, party_name, task_id),
        )

    @router.get("/customers/{party_id}/modal/log-activity", response_class=HTMLResponse)
    async def handle_modal_log_activity(
        request: Request, party_id: str,
        mode: str = "activity",
        party_name: str = "",
        task_id: str = "",
    ) -> Response:
        return templates.TemplateResponse(
            "fragments/modal_log_activity.html",
            _m08_ctx(request, party_id, mode, "", party_name, task_id),
        )

    # ── Activity log POST ─────────────────────────────────────────────────────

    _HT_TO_ACT_TYPE = {"call": "call", "zalo": "chat", "fb": "chat",
                       "email": "email", "visit": "visit", "other": "other"}

    @router.post("/customers/{party_id}/log-activity", response_class=HTMLResponse)
    async def handle_log_activity(
        request: Request,
        party_id: str,
        hinh_thuc: str = Form(default="call"),
        channel_identity_id: str = Form(default=""),
        channel_value: str = Form(default=""),
        outcome: str = Form(default=""),
        body: str = Form(default=""),
        occurred_at: str = Form(default=""),
        related_order_code: str = Form(default=""),
        callback_at: str = Form(default=""),
        create_callback_task: str = Form(default=""),
        save_as_note: str = Form(default=""),
        note_type: str = Form(default="outcome"),
        pinned: str = Form(default="0"),
        visibility: str = Form(default="team"),
        schedule_followup_at: str = Form(default=""),
        task_id: str = Form(default=""),
        complete_task: str = Form(default=""),
    ) -> Response:
        utc_occurred = _ict_local_to_utc(occurred_at) if occurred_at.strip() else ""
        act_data: dict = {
            "party_id": party_id,
            "activity_type": _HT_TO_ACT_TYPE.get(hinh_thuc, "other"),
            "direction": "out",
            "channel": channel_value.strip() or None,
            "outcome": outcome.strip() or None,
            "body": body.strip() or None,
            "occurred_at": utc_occurred,
            "related_order_code": related_order_code.strip() or None,
        }
        if outcome == "callback" and callback_at.strip():
            act_data["callback_at"] = _ict_local_to_utc(callback_at)
            act_data["create_callback_task"] = create_callback_task == "1"
        try:
            activity = activity_log.log_activity(act_data)
        except ValueError as exc:
            return HTMLResponse(str(exc), status_code=400)
        except Exception as exc:
            log.error("log activity party %s: %s", party_id, exc)
            return HTMLResponse("Lỗi ghi log hoạt động", status_code=500)
        if save_as_note == "1" and body.strip():
            try:
                notes.add_note(
                    party_id, body.strip(),
                    note_type=note_type or "outcome",
                    pinned=pinned == "1",
                    visibility=visibility or "team",
                    source_activity_id=getattr(activity, "activity_id", None),
                )
            except Exception as exc:
                log.warning("m08: linked note %s: %s", party_id, exc)
        if task_svc is not None and schedule_followup_at.strip():
            try:
                party360 = profile.get_party_360(party_id)
                name = party360.display_name if party360 else party_id
                task_svc.create_task({
                    "party_id": party_id,
                    "title": f"Theo dõi: {name}",
                    "due_at": schedule_followup_at.strip(),
                    "source": "manual",
                    "priority": 0,
                })
            except Exception as exc:
                log.warning("m08: schedule followup task %s: %s", party_id, exc)
        if complete_task == "1" and task_id.strip() and task_svc is not None:
            try:
                task_svc.transition_status(task_id.strip(), "done")
            except Exception as exc:
                log.warning("m08: complete_task %s: %s", task_id, exc)
        return HTMLResponse(content="", headers={"HX-Redirect": f"/customers/{party_id}?tab=timeline"})

    # ── Note CRUD ─────────────────────────────────────────────────────────────

    @router.post("/customers/{party_id}/notes", response_class=HTMLResponse)
    async def handle_add_note(
        request: Request,
        party_id: str,
        body: str = Form(...),
        note_type: str = Form(default="general"),
        pinned: str = Form(default="0"),
        visibility: str = Form(default="team"),
    ) -> Response:
        body = body.strip()
        if not body:
            return HTMLResponse("Nội dung không được bỏ trống", status_code=400)
        try:
            notes.add_note(party_id, body, note_type=note_type,
                           pinned=pinned == "1", visibility=visibility)
        except Exception as exc:
            log.error("c360: add note %s: %s", party_id, exc)
            return HTMLResponse("Lỗi thêm ghi chú", status_code=500)
        return HTMLResponse(content="", headers={"HX-Redirect": f"/customers/{party_id}?tab=notes"})

    @router.post("/customers/{party_id}/notes/{note_id}", response_class=HTMLResponse)
    async def handle_edit_note(
        request: Request,
        party_id: str,
        note_id: str,
        body: str = Form(...),
        note_type: str = Form(default="general"),
        pinned: str = Form(default="0"),
        visibility: str = Form(default="team"),
    ) -> Response:
        body = body.strip()
        if not body:
            return HTMLResponse("Nội dung không được bỏ trống", status_code=400)
        try:
            notes.update_note(note_id, body, note_type=note_type,
                              pinned=pinned == "1", visibility=visibility)
        except Exception as exc:
            log.error("c360: edit note %s: %s", note_id, exc)
            return HTMLResponse("Lỗi cập nhật ghi chú", status_code=500)
        return HTMLResponse(content="", headers={"HX-Redirect": f"/customers/{party_id}?tab=notes"})

    @router.post("/customers/{party_id}/notes/{note_id}/delete", response_class=HTMLResponse)
    async def handle_delete_note(
        request: Request, party_id: str, note_id: str
    ) -> Response:
        try:
            notes.delete_note(note_id)
        except Exception as exc:
            log.error("c360: delete note %s: %s", note_id, exc)
            return HTMLResponse("Lỗi xoá ghi chú", status_code=500)
        return HTMLResponse(content="", headers={"HX-Redirect": f"/customers/{party_id}?tab=notes"})

    # ── Task quick-actions (P04 in-panel mutations) ───────────────────────────

    def _render_tasks_panel(request: Request, party_id: str, filter_val: str = "open") -> Response:
        task_list = party_tasks.list_by_party(party_id)
        user_map: dict = {}
        if app_users is not None:
            try:
                user_map = {u.user_id: u.full_name for u in app_users.list_active()}
            except Exception:
                pass
        return templates.TemplateResponse(
            "fragments/c360_tasks_panel.html",
            {
                "request": request,
                "party_id": party_id,
                "tasks": task_list,
                "filter": filter_val,
                "user_map": user_map,
                "now_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            },
        )

    @router.patch("/customers/{party_id}/tasks/{task_id}/done", response_class=HTMLResponse)
    async def handle_task_done_c360(request: Request, party_id: str, task_id: str) -> Response:
        if task_svc is None:
            return HTMLResponse("task service not available", status_code=503)
        try:
            task_svc.transition_status(task_id, "done")
        except Exception as exc:
            log.error("c360: task done %s: %s", task_id, exc)
            return HTMLResponse("Lỗi cập nhật task", status_code=500)
        filter_val = request.query_params.get("filter", "open")
        return _render_tasks_panel(request, party_id, filter_val)

    @router.patch("/customers/{party_id}/tasks/{task_id}/cancel", response_class=HTMLResponse)
    async def handle_task_cancel_c360(request: Request, party_id: str, task_id: str) -> Response:
        if task_svc is None:
            return HTMLResponse("task service not available", status_code=503)
        try:
            task_svc.transition_status(task_id, "cancelled")
        except Exception as exc:
            log.error("c360: task cancel %s: %s", task_id, exc)
            return HTMLResponse("Lỗi huỷ task", status_code=500)
        filter_val = request.query_params.get("filter", "open")
        return _render_tasks_panel(request, party_id, filter_val)

    @router.patch("/customers/{party_id}/tasks/{task_id}/postpone", response_class=HTMLResponse)
    async def handle_task_postpone_c360(
        request: Request,
        party_id: str,
        task_id: str,
        due_date: str = Form(default=""),
        due_time: str = Form(default=""),
    ) -> Response:
        if task_svc is None:
            return HTMLResponse("task service not available", status_code=503)
        if not due_date.strip():
            return HTMLResponse("Vui lòng chọn ngày", status_code=400)
        time_part = due_time.strip() or "09:00"
        new_due_at = _ict_local_to_utc(f"{due_date.strip()}T{time_part}")
        if not new_due_at:
            return HTMLResponse("Ngày không hợp lệ", status_code=400)
        try:
            t = task_svc.get_task(task_id)
            if t is not None and getattr(t, "status", "") == "doing":
                task_svc.transition_status(task_id, "open")
            task_svc.update_task(task_id, {"due_at": new_due_at})
        except Exception as exc:
            log.error("c360: task postpone %s: %s", task_id, exc)
            return HTMLResponse("Lỗi hoãn task", status_code=500)
        filter_val = request.query_params.get("filter", "open")
        panel_resp = _render_tasks_panel(request, party_id, filter_val)
        return panel_resp

    @router.get("/modals/o03", response_class=HTMLResponse)
    async def handle_modal_o03(
        request: Request,
        task_id: str,
        party_id: str = "",
        due_at: str = "",
    ) -> Response:
        prefill_date = ""
        prefill_time = ""
        if due_at.strip():
            try:
                dt_utc = datetime.fromisoformat(due_at.strip().replace("Z", "+00:00"))
                dt_ict = dt_utc.astimezone(_ICT)
                prefill_date = dt_ict.strftime("%Y-%m-%d")
                prefill_time = dt_ict.strftime("%H:%M")
            except Exception:
                pass
        return templates.TemplateResponse(
            "fragments/overlay_o03_postpone_task.html",
            {
                "request": request,
                "task_id": task_id,
                "party_id": party_id,
                "due_at_prefill_date": prefill_date,
                "due_at_prefill_time": prefill_time,
            },
        )

    return router
