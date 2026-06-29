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

from application.geography import geo_region
from application.ict_utils import ict_local_to_utc  # noqa: F401 — re-exported for sub-modules

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from domain.entities.activity import Activity
from domain.entities.cache_insight import CacheInsight
from domain.entities.profile import CustomFieldDef, Note, Party360, PartyIdentity, PartyInsight
from domain.entities.task import Task

from adapters.inbound.web.screens.customer360.screen_customer_360_panels import register_panel_routes
from adapters.inbound.web.screens.customer360.screen_customer_360_activity import register_activity_routes
from adapters.inbound.web.screens.customer360.screen_customer_360_notes import register_note_routes
from adapters.inbound.web.screens.customer360.screen_customer_360_tasks import register_task_routes

log = logging.getLogger(__name__)

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


class ActionStateWriter(Protocol):
    """Marks action queue items as dismissed."""
    def dismiss(self, action_id: str, user_id: Optional[str] = None) -> None: ...


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
    approach_repo=None,
    action_state: Optional[ActionStateWriter] = None,
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

        user_map: dict = {}
        if app_users is not None:
            try:
                user_map = {u.user_id: u.full_name for u in app_users.list_active()}
            except Exception as exc:
                log.warning("c360: list_active: %s", exc)

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
                "geo_region": geo_region(party360.province),
                "user_map": user_map,
            },
        )

    # ── Sub-module routes ─────────────────────────────────────────────────────

    register_panel_routes(
        router, templates,
        activities=activities,
        notes=notes,
        party_tasks=party_tasks,
        party_insights=party_insights,
        action_task_resolver=action_task_resolver,
        action_state=action_state,
        customer_timeline=customer_timeline,
        customer_orders=customer_orders,
        customer_dim_metrics=customer_dim_metrics,
        app_users=app_users,
        approach_repo=approach_repo,
        _load_base=_load_base,
        _load_insight=_load_insight,
        _sapo_customer_id=_sapo_customer_id,
    )
    register_activity_routes(
        router, templates,
        profile=profile,
        identities=identities,
        notes=notes,
        activity_log=activity_log,
        task_svc=task_svc,
        app_users=app_users,
    )
    register_note_routes(
        router, templates,
        notes=notes,
        app_users=app_users,
    )
    register_task_routes(
        router, templates,
        party_tasks=party_tasks,
        task_svc=task_svc,
        app_users=app_users,
    )

    return router
