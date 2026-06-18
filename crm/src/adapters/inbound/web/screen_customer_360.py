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
from typing import Optional, Protocol

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
    def log_activity(self, a: Activity) -> None: ...


class NoteReader(Protocol):
    def add_note(self, party_id: str, body: str, author_user_id: Optional[str] = None) -> Note: ...
    def list_notes(self, party_id: str) -> list[Note]: ...


class CustomFieldDefReader(Protocol):
    def list_by_entity_type(self, entity_type: str) -> list[CustomFieldDef]: ...


class PartyInsightReader(Protocol):
    def list_by_party(self, party_id: str) -> list[PartyInsight]: ...


class ActionTaskResolver(Protocol):
    """Returns the set of action_ids that have a resolved CRM task (outcome IS NOT NULL)."""
    def resolved_action_ids(self, party_id: str) -> set[str]: ...


class TaskQuerier(Protocol):
    def list_by_party(self, party_id: str) -> list[Task]: ...


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
            return templates.TemplateResponse(
                "fragments/c360_insight_panel.html",
                {**ctx, "insight": ins, "rep_insights": rep_ins, "resolved_action_ids": resolved_ids, "dim_metrics": dim_metrics},
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
            task_list = party_tasks.list_by_party(party_id)
            return templates.TemplateResponse(
                "fragments/c360_tasks_panel.html", {**ctx, "tasks": task_list}
            )
        if panel == "notes":
            note_list = notes.list_notes(party_id)
            type_filter = request.query_params.get("type_filter", "all")
            return templates.TemplateResponse(
                "fragments/c360_notes_panel.html",
                {**ctx, "notes": note_list, "type_filter": type_filter},
            )
        if panel == "status_history":
            if customer_timeline is None:
                return HTMLResponse(
                    '<div class="caveat caveat--warn">Dữ liệu trạng thái chưa sẵn sàng.</div>',
                    status_code=503,
                )
            _, ids = _load_base(party_id)
            customer_id = _sapo_customer_id(ids)
            snapshots = []
            if customer_id:
                try:
                    snapshots = customer_timeline.get_by_customer_id(customer_id)
                except Exception as exc:
                    log.warning("c360 status_history panel: %s: %s", party_id, exc)
            return templates.TemplateResponse(
                "fragments/c360_status_timeline_panel.html",
                {
                    **ctx,
                    "snapshots": snapshots,
                    "timeline_available": True,
                },
            )
        return HTMLResponse("panel not found", status_code=404)

    # ── Note creation ─────────────────────────────────────────────────────────

    @router.post("/customers/{party_id}/notes", response_class=HTMLResponse)
    async def handle_add_note(
        request: Request, party_id: str, body: str = Form(...)
    ) -> Response:
        body = body.strip()
        if not body:
            return HTMLResponse("body required", status_code=400)
        try:
            note = notes.add_note(party_id, body)
        except Exception as exc:
            log.error("c360: add note %s: %s", party_id, exc)
            return HTMLResponse("failed to add note", status_code=500)
        return templates.TemplateResponse(
            "fragments/note_card.html", {"request": request, "note": note}
        )

    # ── Activity log (M08 modal) ──────────────────────────────────────────────

    @router.get("/customers/{party_id}/modal/log-activity", response_class=HTMLResponse)
    async def handle_modal_log_activity(request: Request, party_id: str) -> Response:
        return templates.TemplateResponse(
            "fragments/modal_log_activity.html",
            {"request": request, "party_id": party_id, "conv_id": ""},
        )

    @router.post("/customers/{party_id}/log-activity", response_class=HTMLResponse)
    async def handle_log_activity(
        request: Request,
        party_id: str,
        activity_type: str = Form(default="note"),
        body: str = Form(...),
    ) -> Response:
        body = body.strip()
        if not body:
            return HTMLResponse("body required", status_code=400)
        act = Activity(
            party_id=party_id,
            activity_type=activity_type or "note",
            body=body,
            channel="crm",
        )
        try:
            activity_log.log_activity(act)
        except Exception as exc:
            log.error("log activity party %s: %s", party_id, exc)
            return HTMLResponse("failed to log activity", status_code=500)
        acts = activities.list_activities(party_id)
        return templates.TemplateResponse(
            "fragments/c360_timeline_panel.html",
            {"request": request, "party_id": party_id, "activities": acts},
        )

    return router
