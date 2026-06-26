"""FastAPI router — modal HTMX fragment endpoints.

Covers M02 (create party) and M04 (assign owner).
Routes mirror screen_shared_modals.go (chi → FastAPI).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Protocol

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from crm.src.domain.entities.app_user import AppUser
from crm.src.domain.entities.party import Party
from crm.src.domain.entities.profile import Party360

log = logging.getLogger(__name__)
router = APIRouter()


# ── Service protocols ─────────────────────────────────────────────────────────

class PartyCreator(Protocol):
    def create_with_identities(self, party: Party, identities: list) -> None: ...

class ProfileQuerier(Protocol):
    def get_party_360(self, party_id: str) -> Optional[Party360]: ...

class OwnerAssigner(Protocol):
    def upsert_profile(self, party_id: str, **kwargs) -> object: ...

class AppUserLister(Protocol):
    def list_active(self) -> list[AppUser]: ...


# ── Deps container (set by mount_web) ─────────────────────────────────────────

class WebDeps:
    party_creator: PartyCreator
    profile_querier: ProfileQuerier
    owner_assigner: OwnerAssigner
    app_users: AppUserLister


_deps: Optional[WebDeps] = None
_templates: Optional[Jinja2Templates] = None


def _get_deps() -> WebDeps:
    if _deps is None:
        raise RuntimeError("modal router not initialised — call init_modals()")
    return _deps


def init_modals(deps: WebDeps, templates: Jinja2Templates) -> None:
    global _deps, _templates
    _deps = deps
    _templates = templates


# ── M02 — Create party ───────────────────────────────────────────────────────

@router.get("/parties/modal/create", response_class=HTMLResponse)
async def get_modal_create_party(request: Request) -> HTMLResponse:
    return _templates.TemplateResponse(
        "modals.html",
        {"request": request, "macro": "modal_create_party"},
    )


@router.post("/parties", response_class=HTMLResponse)
async def post_create_party(
    request: Request,
    display_name: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    note: str = Form(""),
) -> HTMLResponse:
    display_name = display_name.strip()
    phone = phone.strip()
    if not display_name or not phone:
        raise HTTPException(status_code=400, detail="display_name and phone required")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    party_id = str(uuid.uuid4())

    party = Party(
        party_id=party_id,
        party_type="person",
        display_name=display_name,
        primary_phone=phone,
        primary_email=email.strip() or None,
        status="active",
        created_at=now,
        updated_at=now,
    )

    from crm.src.domain.entities.profile import PartyIdentity  # local import avoids circular
    identity = PartyIdentity(
        identity_id=str(uuid.uuid4()),
        party_id=party_id,
        source_system="manual",
        identity_type="phone",
        identity_value=phone,
        confidence=1.0,
        is_primary=True,
        created_at=now,
    )

    try:
        _get_deps().party_creator.create_with_identities(party, [identity])
    except Exception as exc:
        log.error("create party: %s", exc)
        raise HTTPException(status_code=500, detail=f"Lỗi tạo khách hàng: {exc}") from exc

    return HTMLResponse(
        content="",
        headers={"HX-Redirect": f"/customers/{party_id}"},
    )


# ── M04 — Assign owner ────────────────────────────────────────────────────────

@router.get("/customers/{party_id}/modal/assign-owner", response_class=HTMLResponse)
async def get_modal_assign_owner(request: Request, party_id: str) -> HTMLResponse:
    deps = _get_deps()
    current_owner_id: Optional[str] = None
    try:
        p360 = deps.profile_querier.get_party_360(party_id)
        if p360:
            current_owner_id = p360.owner_user_id
    except Exception as exc:
        log.warning("assign owner modal: get party 360: %s", exc)

    try:
        users = deps.app_users.list_active()
    except Exception as exc:
        log.warning("assign owner modal: list users: %s", exc)
        users = []

    return _templates.TemplateResponse(
        "modals.html",
        {"request": request, "macro": "modal_assign_owner",
         "party_id": party_id, "current_owner_id": current_owner_id, "users": users},
    )


@router.post("/customers/{party_id}/assign-owner", response_class=HTMLResponse)
async def post_assign_owner(
    party_id: str,
    owner_user_id: str = Form(""),
) -> HTMLResponse:
    owner_user_id = owner_user_id.strip()
    if not owner_user_id:
        raise HTTPException(status_code=400, detail="owner_user_id required")

    try:
        _get_deps().owner_assigner.upsert_profile(party_id, owner_user_id=owner_user_id)
    except Exception as exc:
        log.error("assign owner %s: %s", party_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return HTMLResponse(
        content="",
        headers={
            "HX-Trigger": '{"closeModal":true}',
            "HX-Redirect": f"/customers/{party_id}",
        },
    )
