"""Web adapter — S03 party modal HTMX fragment routes.

Covers GET /modals/m03-m06, /modals/m15 (open modal endpoints) and all
related POST form-submission handlers for the Customer 360 sidebar and topbar.

Modals served:
  M03 — Tag Management       GET /modals/m03?party_id=
  M04 — Assign Owner         GET /modals/m04?party_id=
  M05 — Create Task          GET /modals/m05?party_id=
  M06 — Custom Fields        GET /modals/m06?party_id=
  M15 — Edit Contact/Addr    GET /modals/m15?party_id=&tab=contacts|address|core
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Protocol

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from crm.src.domain.entities.app_user import AppUser
from crm.src.domain.entities.party import PartyIdentity
from crm.src.domain.entities.profile import CustomFieldDef, Party360, Tag
from crm.src.domain.entities.task import Task

log = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_PRIO_STR_TO_INT: dict[str, int] = {"P1": 2, "P2": 1, "P3": 0, "P4": 0}
_PRIO_INT_TO_STR: dict[int, str] = {2: "P1", 1: "P2", 0: "P3"}


def _parse_priority(s: str) -> int:
    """Convert P1-P4 code or numeric string to domain int (2=urgent, 1=high, 0=normal)."""
    v = s.strip().upper()
    if v in _PRIO_STR_TO_INT:
        return _PRIO_STR_TO_INT[v]
    return int(v) if v.isdigit() else 0


# ── Service protocols ─────────────────────────────────────────────────────────

class ProfileSvc(Protocol):
    def get_party_360(self, party_id: str) -> Optional[Party360]: ...
    def list_tags(self, category: str) -> list[Tag]: ...
    def list_party_tags(self, party_id: str) -> list: ...
    def attach_tag(self, party_id: str, tag_id: str) -> None: ...
    def detach_tag(self, party_id: str, tag_id: str) -> None: ...
    def list_custom_field_defs(self, entity_type: Optional[str] = None) -> list[CustomFieldDef]: ...
    def upsert_profile(self, party_id: str, **kwargs) -> object: ...


class PartyRepo(Protocol):
    def get_by_id(self, party_id: str) -> Optional[object]: ...
    def update(self, party: object) -> None: ...
    def list_identities(self, party_id: str) -> list[PartyIdentity]: ...
    def update_party_address(
        self, party_id: str,
        address_line: Optional[str], ward: Optional[str], district: Optional[str],
        province: Optional[str], address_note: Optional[str], updated_at: str,
    ) -> None: ...
    def deactivate_identity(self, identity_id: str) -> None: ...
    def insert_identity_full(self, identity: PartyIdentity) -> None: ...
    def update_identity_info(
        self, identity_id: str, display_label: Optional[str],
        contact_status: str, is_preferred: bool,
    ) -> None: ...


class TaskSvc(Protocol):
    def create_task(self, task_data: dict) -> object: ...
    def get_task(self, task_id: str) -> Optional[Task]: ...
    def update_task(self, task_id: str, data: dict) -> Task: ...


class AppUserRepo(Protocol):
    def list_active(self) -> list[AppUser]: ...


# ── Router factory ────────────────────────────────────────────────────────────

def make_party_modals_router(
    templates: Jinja2Templates,
    profile: ProfileSvc,
    party_repo: PartyRepo,
    task_svc: TaskSvc,
    app_users: AppUserRepo,
) -> APIRouter:
    """Return APIRouter for all /modals/m* GET routes and related POST handlers."""
    router = APIRouter()

    def _redirect(party_id: str) -> HTMLResponse:
        return HTMLResponse(content="", headers={"HX-Redirect": f"/customers/{party_id}"})

    def _parse_custom(raw) -> dict:
        if isinstance(raw, dict):
            return dict(raw)
        try:
            return json.loads(raw or "{}")
        except Exception:
            return {}

    # ── GET /modals/m03 — Tag Management ──────────────────────────────────────

    @router.get("/modals/m03", response_class=HTMLResponse)
    async def get_modal_m03(request: Request, party_id: str) -> Response:
        all_tags = profile.list_tags("")
        current = profile.list_party_tags(party_id)
        party_tag_ids = {t.tag_id for t in current}
        party_name = ""
        try:
            p360 = profile.get_party_360(party_id)
            if p360:
                party_name = p360.display_name
        except Exception:
            pass
        return templates.TemplateResponse(
            "fragments/modal_m03_tags.html",
            {"request": request, "party_id": party_id,
             "all_tags": all_tags, "party_tag_ids": party_tag_ids,
             "party_name": party_name},
        )

    # ── GET /modals/m04 — Assign Owner ────────────────────────────────────────

    @router.get("/modals/m04", response_class=HTMLResponse)
    async def get_modal_m04(request: Request, party_id: str) -> Response:
        current_owner_id: Optional[str] = None
        p360 = profile.get_party_360(party_id)
        if p360:
            current_owner_id = p360.owner_user_id
        users = []
        try:
            users = app_users.list_active()
        except Exception as exc:
            log.warning("m04: list_active: %s", exc)
        return templates.TemplateResponse(
            "modals.html",
            {"request": request, "macro": "modal_assign_owner",
             "party_id": party_id, "current_owner_id": current_owner_id, "users": users},
        )

    # ── GET /modals/m05 — Create / Edit Task ─────────────────────────────────

    @router.get("/modals/m05", response_class=HTMLResponse)
    async def get_modal_m05(
        request: Request,
        party_id: str = "",
        task_id: str = "",
        source: str = "",
        source_ref: str = "",
        prefill_title: str = "",
        prefill_priority: str = "",
    ) -> Response:
        au = []
        try:
            au = app_users.list_active()
        except Exception as exc:
            log.warning("m05: list_active: %s", exc)
        task: Optional[Task] = None
        if task_id:
            try:
                task = task_svc.get_task(task_id)
            except Exception as exc:
                log.warning("m05: get_task %s: %s", task_id, exc)
            if task and not party_id:
                party_id = task.party_id or ""
        # Resolve party name for the Khách hàng display field
        party_name = ""
        if party_id:
            try:
                p360 = profile.get_party_360(party_id)
                if p360:
                    party_name = p360.display_name
            except Exception as exc:
                log.debug("m05: get_party_360 %s: %s", party_id, exc)
        # Compute P-code for priority select
        if task:
            prio_code = _PRIO_INT_TO_STR.get(task.priority, "P3")
        else:
            prio_code = "P2"  # prototype default for new tasks
        # Split due_at into date/time parts for the two inputs
        due_date_val = ""
        due_time_val = "10:00"
        if task and task.due_at:
            due_date_val = task.due_at[:10]
            if len(task.due_at) > 10:
                due_time_val = task.due_at[11:16]
        return templates.TemplateResponse(
            "fragments/modal_m05_create_task.html",
            {
                "request": request,
                "party_id": party_id,
                "party_name": party_name,
                "app_users": au,
                "task": task,
                "prefill_source": source,
                "prefill_source_ref": source_ref,
                "prefill_title": prefill_title,
                "prio_code": prio_code,
                "due_date_val": due_date_val,
                "due_time_val": due_time_val,
            },
        )

    # ── PATCH /tasks/{task_id}/edit — Save task edits ────────────────────────

    @router.patch("/tasks/{task_id}/edit", response_class=HTMLResponse)
    async def patch_task_edit(
        request: Request,
        task_id: str,
        title: str = Form(...),
        description: str = Form(default=""),
        due_at: str = Form(default=""),
        priority: str = Form(default="P3"),
        assignee_user_id: str = Form(default=""),
        party_id: str = Form(default=""),
    ) -> Response:
        title = title.strip()
        if not title:
            return HTMLResponse("Tiêu đề không được bỏ trống", status_code=400)
        try:
            task_svc.update_task(task_id, {
                "title": title,
                "description": description.strip(),
                "due_at": due_at.strip() or None,
                "priority": _parse_priority(priority),
                "assignee_user_id": assignee_user_id.strip() or None,
            })
        except Exception as exc:
            log.error("m05 edit task %s: %s", task_id, exc)
            return HTMLResponse("Lưu thất bại", status_code=500)
        redirect = f"/customers/{party_id}?tab=tasks" if party_id else "/tasks"
        return Response(status_code=200, headers={"HX-Redirect": redirect})

    # ── GET /modals/m06 — Custom Fields ──────────────────────────────────────

    @router.get("/modals/m06", response_class=HTMLResponse)
    async def get_modal_m06(request: Request, party_id: str) -> Response:
        cf_defs = profile.list_custom_field_defs("party")
        p360 = profile.get_party_360(party_id)
        custom_vals = {k: str(v) for k, v in _parse_custom(p360.custom if p360 else "").items()}
        return templates.TemplateResponse(
            "fragments/modal_m06_custom_fields.html",
            {"request": request, "party_id": party_id,
             "custom_field_defs": cf_defs, "custom_values": custom_vals},
        )

    # ── GET /modals/m15 — Edit Contact / Address / Core ──────────────────────

    @router.get("/modals/m15", response_class=HTMLResponse)
    async def get_modal_m15(request: Request, party_id: str, tab: str = "contacts") -> Response:
        p360 = profile.get_party_360(party_id)
        if p360 is None:
            return HTMLResponse("Không tìm thấy khách hàng", status_code=404)
        ids = party_repo.list_identities(party_id)
        return templates.TemplateResponse(
            "fragments/modal_m15_edit_contact.html",
            {"request": request, "party": p360, "identities": ids, "active_tab": tab},
        )

    # ── GET /customers/{party_id}/modal/edit-contact — M15 tab navigation ────

    @router.get("/customers/{party_id}/modal/edit-contact", response_class=HTMLResponse)
    async def get_modal_edit_contact(
        request: Request, party_id: str, tab: str = "contacts"
    ) -> Response:
        p360 = profile.get_party_360(party_id)
        if p360 is None:
            return HTMLResponse("Không tìm thấy", status_code=404)
        ids = party_repo.list_identities(party_id)
        return templates.TemplateResponse(
            "fragments/modal_m15_edit_contact.html",
            {"request": request, "party": p360, "identities": ids, "active_tab": tab},
        )

    # ── GET /customers/{party_id}/contact/{identity_id}/edit-form ────────────

    @router.get("/customers/{party_id}/contact/{identity_id}/edit-form", response_class=HTMLResponse)
    async def get_identity_edit_form(
        request: Request, party_id: str, identity_id: str
    ) -> Response:
        ids = party_repo.list_identities(party_id)
        identity = next((i for i in ids if i.identity_id == identity_id), None)
        if identity is None:
            return HTMLResponse("Không tìm thấy kênh liên lạc", status_code=404)
        return templates.TemplateResponse(
            "fragments/m15_identity_edit_form.html",
            {"request": request, "party_id": party_id, "identity": identity},
        )

    # ── POST /customers/{party_id}/tags ───────────────────────────────────────

    @router.post("/customers/{party_id}/tags", response_class=HTMLResponse)
    async def post_tags(
        party_id: str,
        tag_ids: List[str] = Form(default=[]),
    ) -> Response:
        current = profile.list_party_tags(party_id)
        current_ids = {t.tag_id for t in current}
        submitted = set(tag_ids)
        try:
            for tid in current_ids - submitted:
                profile.detach_tag(party_id, tid)
            for tid in submitted - current_ids:
                profile.attach_tag(party_id, tid)
        except Exception as exc:
            log.error("post_tags %s: %s", party_id, exc)
            return HTMLResponse(f"Lỗi lưu tags: {exc}", status_code=500)
        return _redirect(party_id)

    # ── POST /customers/{party_id}/tasks ──────────────────────────────────────

    @router.post("/customers/{party_id}/tasks", response_class=HTMLResponse)
    async def post_task(
        party_id: str,
        title: str = Form(""),
        description: str = Form(""),
        due_at: str = Form(""),
        assignee_user_id: str = Form(""),
        priority: str = Form("P3"),
        source: str = Form("manual"),
        source_ref: str = Form(""),
    ) -> Response:
        title = title.strip()
        if not title:
            return HTMLResponse("Tiêu đề không được bỏ trống", status_code=400)
        try:
            task_svc.create_task({
                "party_id": party_id,
                "title": title,
                "description": description.strip() or None,
                "due_at": due_at.strip() or None,
                "assignee_user_id": assignee_user_id.strip() or None,
                "priority": _parse_priority(priority),
                "source": source.strip() or "manual",
                "source_ref": source_ref.strip() or None,
            })
        except Exception as exc:
            log.error("post_task %s: %s", party_id, exc)
            return HTMLResponse(f"Lỗi tạo task: {exc}", status_code=500)
        return _redirect(party_id)

    # ── POST /customers/{party_id}/contact ────────────────────────────────────

    @router.post("/customers/{party_id}/contact", response_class=HTMLResponse)
    async def post_contact(
        party_id: str,
        action: str = Form("add_channel"),
        add_identity_type: str = Form("phone_secondary"),
        add_identity_value: str = Form(""),
        add_display_label: str = Form(""),
        add_is_preferred: str = Form("0"),
        identity_id: str = Form(""),
        edit_display_label: str = Form(""),
        edit_contact_status: str = Form("active"),
        edit_is_preferred: str = Form("0"),
    ) -> Response:
        try:
            if action == "add_channel":
                val = add_identity_value.strip()
                if not val:
                    return HTMLResponse("Giá trị không được bỏ trống", status_code=400)
                identity = PartyIdentity(
                    identity_id=str(uuid.uuid4()),
                    party_id=party_id,
                    source_system="manual",
                    identity_type=add_identity_type or "phone_secondary",
                    identity_value=val,
                    confidence=1.0,
                    is_primary=False,
                    source_contact_quality="unverified",
                    contact_quality="unverified",
                    created_at=_utc_now(),
                    display_label=add_display_label.strip() or None,
                    contact_status="active",
                    is_preferred=add_is_preferred == "1",
                )
                party_repo.insert_identity_full(identity)
            elif action == "edit_channel" and identity_id:
                party_repo.update_identity_info(
                    identity_id=identity_id,
                    display_label=edit_display_label.strip() or None,
                    contact_status=edit_contact_status or "active",
                    is_preferred=edit_is_preferred == "1",
                )
        except Exception as exc:
            log.error("post_contact %s: %s", party_id, exc)
            return HTMLResponse(f"Lỗi lưu kênh liên lạc: {exc}", status_code=500)
        return _redirect(party_id)

    # ── POST /customers/{party_id}/consent ────────────────────────────────────

    @router.post("/customers/{party_id}/consent", response_class=HTMLResponse)
    async def post_consent(
        party_id: str,
        consent_contact: str = Form("na"),
    ) -> Response:
        value = consent_contact if consent_contact in ("allowed", "denied", "na") else None
        try:
            profile.upsert_profile(party_id, consent_contact=value)
        except Exception as exc:
            log.error("post_consent %s: %s", party_id, exc)
            return HTMLResponse(f"Lỗi cập nhật đồng ý liên lạc: {exc}", status_code=500)
        return _redirect(party_id)

    # ── POST /customers/{party_id}/contact/{identity_id}/deactivate ──────────

    @router.post(
        "/customers/{party_id}/contact/{identity_id}/deactivate",
        response_class=HTMLResponse,
    )
    async def post_deactivate_identity(party_id: str, identity_id: str) -> Response:
        try:
            party_repo.deactivate_identity(identity_id)
        except Exception as exc:
            log.error("deactivate_identity %s: %s", identity_id, exc)
            return HTMLResponse(f"Lỗi huỷ kích hoạt: {exc}", status_code=500)
        return _redirect(party_id)

    # ── POST /customers/{party_id}/address ────────────────────────────────────

    @router.post("/customers/{party_id}/address", response_class=HTMLResponse)
    async def post_address(
        party_id: str,
        address_line: str = Form(""),
        ward: str = Form(""),
        district: str = Form(""),
        province: str = Form(""),
        address_note: str = Form(""),
    ) -> Response:
        try:
            party_repo.update_party_address(
                party_id=party_id,
                address_line=address_line.strip() or None,
                ward=ward.strip() or None,
                district=district.strip() or None,
                province=province.strip() or None,
                address_note=address_note.strip() or None,
                updated_at=_utc_now(),
            )
        except Exception as exc:
            log.error("post_address %s: %s", party_id, exc)
            return HTMLResponse(f"Lỗi lưu địa chỉ: {exc}", status_code=500)
        return _redirect(party_id)

    # ── POST /customers/{party_id}/core ───────────────────────────────────────

    @router.post("/customers/{party_id}/core", response_class=HTMLResponse)
    async def post_core(
        party_id: str,
        display_name: str = Form(""),
        primary_email: str = Form(""),
        birthday: str = Form(""),
        gender: str = Form(""),
        consent_contact: str = Form("na"),
    ) -> Response:
        display_name = display_name.strip()
        if not display_name:
            return HTMLResponse("Tên hiển thị không được bỏ trống", status_code=400)
        consent_value = consent_contact if consent_contact in ("allowed", "denied", "na") else None
        try:
            party = party_repo.get_by_id(party_id)
            if party is not None:
                party.display_name = display_name
                party.primary_email = primary_email.strip() or ""
                party_repo.update(party)
            profile.upsert_profile(
                party_id,
                birthday=birthday.strip() or None,
                gender=gender.strip() or None,
                consent_contact=consent_value,
            )
        except Exception as exc:
            log.error("post_core %s: %s", party_id, exc)
            return HTMLResponse(f"Lỗi lưu thông tin: {exc}", status_code=500)
        return _redirect(party_id)

    # ── POST /customers/{party_id}/custom-fields ──────────────────────────────

    @router.post("/customers/{party_id}/custom-fields", response_class=HTMLResponse)
    async def post_custom_fields(request: Request, party_id: str) -> Response:
        form_data = await request.form()
        cf_defs = profile.list_custom_field_defs("party")
        valid_keys = {d.field_key for d in cf_defs}
        try:
            p360 = profile.get_party_360(party_id)
            merged = _parse_custom(p360.custom if p360 else "")
            for key in valid_keys:
                raw = form_data.get(key)
                if raw is not None:
                    merged[key] = str(raw).strip()
            profile.upsert_profile(party_id, custom=merged)
        except Exception as exc:
            log.error("post_custom_fields %s: %s", party_id, exc)
            return HTMLResponse(f"Lỗi lưu thông tin bổ sung: {exc}", status_code=500)
        return _redirect(party_id)

    return router
