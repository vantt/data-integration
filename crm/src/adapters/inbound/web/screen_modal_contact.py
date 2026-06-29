"""Web adapter — M15 Edit Contact / Address / Core modal.

GET  /modals/m15, /customers/{party_id}/modal/edit-contact (open + tab nav),
/customers/{party_id}/contact/{identity_id}/edit-form (identity edit form).
POST /customers/{party_id}/{contact,consent,address,core} and
/customers/{party_id}/contact/{identity_id}/deactivate (form submissions).
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from crm.src.adapters.inbound.web.screen_modal_shared import (
    PartyRepo,
    ProfileSvc,
    redirect_to_customer,
    utc_now,
)
from crm.src.domain.entities.party import PartyIdentity

log = logging.getLogger(__name__)


def make_contact_modal_router(
    templates: Jinja2Templates,
    profile: ProfileSvc,
    party_repo: PartyRepo,
) -> APIRouter:
    router = APIRouter()

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
                    created_at=utc_now(),
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
        return redirect_to_customer(party_id)

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
        return redirect_to_customer(party_id)

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
        return redirect_to_customer(party_id)

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
                updated_at=utc_now(),
            )
        except Exception as exc:
            log.error("post_address %s: %s", party_id, exc)
            return HTMLResponse(f"Lỗi lưu địa chỉ: {exc}", status_code=500)
        return redirect_to_customer(party_id)

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
        return redirect_to_customer(party_id)

    return router
