"""FastAPI router — Customer 360 HTTP handlers.

Auth: DEFERRED — LAN-trust only, no auth middleware.
Routes mirror customer360_handler.go (chi → FastAPI).
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Protocol

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from crm.python.domain.entities.cache_insight import CacheInsight
from crm.python.domain.entities.party import Party
from crm.python.domain.entities.profile import (
    CustomerProfile,
    CustomFieldDef,
    Note,
    Party360,
    VALID_CUSTOM_DATA_TYPES,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ── Service protocols (dependency-inversion; handler owns no concrete types) ──

class ProfileQuerier(Protocol):
    def get_profile(self, party_id: str) -> Optional[CustomerProfile]: ...
    def get_party_360(self, party_id: str) -> Optional[Party360]: ...


class PartyLookup(Protocol):
    def get_by_id(self, party_id: str) -> Optional[Party]: ...


class ProfileWriter(Protocol):
    def upsert_profile(self, party_id: str, **kwargs: Any) -> CustomerProfile: ...
    def update_custom(self, party_id: str, field_key: str, value: str) -> None: ...


class TagManager(Protocol):
    def attach_tag(self, party_id: str, tag_id: str, user_id: Optional[str] = None) -> None: ...
    def detach_tag(self, party_id: str, tag_id: str) -> None: ...


class NoteManager(Protocol):
    def add_note(self, party_id: str, body: str, author_user_id: Optional[str] = None) -> Note: ...
    def list_notes(self, party_id: str) -> list[Note]: ...


class CustomFieldAdmin(Protocol):
    def list_custom_field_defs(self, entity_type: Optional[str] = None) -> list[CustomFieldDef]: ...
    def create_custom_field_def(self, def_data: CustomFieldDef) -> CustomFieldDef: ...


class InsightQuerier(Protocol):
    def get_customer_insight(self, customer_id: int) -> Optional[CacheInsight]: ...


# ── Pydantic request/response models ─────────────────────────────────────────

class PutProfileBody(BaseModel):
    owner_user_id: Optional[str] = None
    lifecycle_stage: Optional[str] = None
    acquisition_source: Optional[str] = None
    birthday: Optional[str] = None
    address: Optional[str] = None
    preferences: Optional[str] = None
    consent_contact: bool = True
    custom_fields: Optional[dict[str, str]] = None


class AttachTagBody(BaseModel):
    tag_id: str
    tagged_by: Optional[str] = None


class AddNoteBody(BaseModel):
    body: str
    author_user_id: Optional[str] = None


class CreateCustomFieldBody(BaseModel):
    field_id: Optional[str] = None
    entity_type: str = "party"
    field_key: str
    label: str
    data_type: str
    is_required: bool = False
    is_active: bool = True
    sort_order: int = 0
    options: Optional[list[str]] = None


# ── Handler factory ───────────────────────────────────────────────────────────

def make_customer360_router(
    profile_q: ProfileQuerier,
    profile_w: ProfileWriter,
    tags: TagManager,
    notes: NoteManager,
    cf_admin: CustomFieldAdmin,
    party_lookup: PartyLookup,
    insight_q: Optional[InsightQuerier] = None,
) -> APIRouter:
    """Return a configured APIRouter with all Customer 360 endpoints wired."""

    # GET /api/parties/{id}/360
    @router.get("/parties/{id}/360")
    def get_party360(id: str) -> Any:
        v = profile_q.get_party_360(id)
        if v is None:
            party = party_lookup.get_by_id(id)
            if party is not None and party.is_merged:
                raise HTTPException(
                    status_code=409,
                    detail={"error": "party_merged", "merged_into": party.merged_into or ""},
                )
            raise HTTPException(status_code=404, detail="party not found")
        return v

    # GET /api/parties/{id}/profile
    @router.get("/parties/{id}/profile")
    def get_profile(id: str) -> Any:
        p = profile_q.get_profile(id)
        if p is None:
            raise HTTPException(status_code=404, detail="profile not found")
        return p

    # PUT /api/parties/{id}/profile
    @router.put("/parties/{id}/profile")
    def put_profile(id: str, body: PutProfileBody) -> Any:
        kwargs: dict[str, Any] = {
            k: v for k, v in body.model_dump(exclude={"custom_fields"}).items()
            if v is not None
        }
        profile_w.upsert_profile(id, **kwargs)
        if body.custom_fields:
            for field_key, value in body.custom_fields.items():
                try:
                    profile_w.update_custom(id, field_key, value)
                except ValueError as exc:
                    raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"status": "ok", "party_id": id}

    # GET /api/parties/{id}/insight
    @router.get("/parties/{id}/insight")
    def get_insight(id: str) -> Any:
        if insight_q is None:
            raise HTTPException(status_code=503, detail="insight service unavailable")
        party = party_lookup.get_by_id(id)
        if party is None:
            raise HTTPException(status_code=404, detail="party not found")
        # customer_id resolved from party identities — caller must pass a querier
        # that bridges party_id → customer_id internally
        result = insight_q.get_customer_insight(0)  # placeholder; override via subclass
        if result is None:
            raise HTTPException(status_code=404, detail="insight not found")
        return result

    # GET /api/custom-fields?entity_type=party
    @router.get("/custom-fields")
    def list_custom_fields(entity_type: str = "party") -> Any:
        defs = cf_admin.list_custom_field_defs(entity_type)
        return {"entity_type": entity_type, "fields": defs or []}

    # POST /api/custom-fields
    @router.post("/custom-fields", status_code=201)
    def create_custom_field(body: CreateCustomFieldBody) -> Any:
        if body.data_type not in VALID_CUSTOM_DATA_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"data_type must be one of: {', '.join(VALID_CUSTOM_DATA_TYPES)}",
            )
        defn = CustomFieldDef(
            field_id=body.field_id or "",
            entity_type=body.entity_type,
            field_key=body.field_key,
            label=body.label,
            data_type=body.data_type,
            is_required=body.is_required,
            is_active=body.is_active,
            sort_order=body.sort_order,
            options=body.options,
        )
        created = cf_admin.create_custom_field_def(defn)
        return created

    # POST /api/parties/{id}/tags
    @router.post("/parties/{id}/tags")
    def attach_tag(id: str, body: AttachTagBody) -> Any:
        try:
            tags.attach_tag(id, body.tag_id, body.tagged_by)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"status": "ok"}

    # DELETE /api/parties/{id}/tags/{tag_id}
    @router.delete("/parties/{id}/tags/{tag_id}")
    def detach_tag(id: str, tag_id: str) -> Any:
        tags.detach_tag(id, tag_id)
        return {"status": "ok"}

    # POST /api/parties/{id}/notes
    @router.post("/parties/{id}/notes", status_code=201)
    def add_note(id: str, body: AddNoteBody) -> Any:
        if not body.body.strip():
            raise HTTPException(status_code=400, detail="body required")
        try:
            note = notes.add_note(id, body.body, body.author_user_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return note

    # GET /api/parties/{id}/notes
    @router.get("/parties/{id}/notes")
    def list_notes(id: str) -> Any:
        items = notes.list_notes(id)
        return {"party_id": id, "notes": items or []}

    return router
