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

from adapters.inbound.web.screens.modals.screen_modal_shared import (
    PartyRepo,
    ProfileSvc,
    redirect_to_customer,
    utc_now,
)
from domain.entities.party import PartyIdentity

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
        request: Request,
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
        inline: str = Form("0"),
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
        # §4 inline collect: return a one-row fragment instead of redirect
        if inline == "1":
            return templates.TemplateResponse(
                "fragments/_s14_collect_row.html",
                {"request": request, "party_id": party_id,
                 "field": add_identity_type, "value": add_identity_value.strip(),
                 "done": True},
            )
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

    @router.post("/customers/{party_id}/custom-field-inline", response_class=HTMLResponse)
    async def post_custom_field_inline(
        request: Request,
        party_id: str,
        field_key: str = Form(""),
        value: str = Form(""),
        inline: str = Form("0"),
    ) -> Response:
        """Item 1 (Phase 06) + health_context_raw (Phase 02, 260706-0833):
        inline custom field save from S14 collect row.

        Saves a single key→value pair into party.custom JSON blob and returns
        the updated _s14_collect_row.html fragment (saved=True). Rendered
        `kind` depends on field: custom_select fields (skin_type,
        preferred_contact) show a saved pill; custom_text fields
        (health_context_raw) show a done-tick value (row fragment variant A).
        """
        field_key = field_key.strip()
        value = value.strip()
        if not field_key or not value:
            return HTMLResponse("field_key and value are required", status_code=400)
        # Only allow known safe field keys to prevent arbitrary key injection
        _ALLOWED_KEYS = {"skin_type", "preferred_contact", "health_context_raw"}
        if field_key not in _ALLOWED_KEYS:
            return HTMLResponse(f"Unknown field_key: {field_key}", status_code=400)
        # health_context_raw is free text — enforce the same 200-char cap server-side
        # that the S14 input already applies client-side (maxlength=200).
        if field_key == "health_context_raw" and len(value) > 200:
            return HTMLResponse("Ghi chú sức khỏe tối đa 200 ký tự", status_code=400)
        try:
            profile.upsert_profile(party_id, custom={field_key: value})
        except Exception as exc:
            log.warning("custom_field_inline %s %s: %s", party_id, field_key, exc)
            return HTMLResponse("Lỗi lưu custom field", status_code=500)
        # Return updated row fragment — show saved value + toast (Item 6)
        # tuple: (label, kind, options) — options only meaningful for custom_select
        _FIELD_META = {
            "skin_type": ("Loại da", "custom_select", ["dầu", "khô", "hỗn hợp", "nhạy cảm", "thường"]),
            "preferred_contact": ("Kênh ưu thích", "custom_select", ["phone", "zalo", "messenger", "email"]),
            "health_context_raw": ("Ghi chú sức khỏe", "custom_text", []),
        }
        label, kind, options = _FIELD_META.get(field_key, (field_key, "custom_select", []))
        return templates.TemplateResponse(
            "fragments/_s14_collect_row.html",
            {
                "request": request,
                "party_id": party_id,
                "row": {
                    "key": field_key,
                    "label": label,
                    "kind": kind,
                    "options": options,
                    "current": value,
                },
                "saved": True,
            },
        )

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
        request: Request,
        party_id: str,
        display_name: str = Form(""),
        primary_email: str = Form(""),
        birthday: str = Form(""),
        gender: str = Form(""),
        consent_contact: str = Form("na"),
        inline: str = Form("0"),
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
        # §4 inline collect: return a one-row fragment instead of redirect
        if inline == "1":
            return templates.TemplateResponse(
                "fragments/_s14_collect_row.html",
                {"request": request, "party_id": party_id,
                 "field": "core", "value": display_name.strip(),
                 "done": True},
            )
        return redirect_to_customer(party_id)

    return router
