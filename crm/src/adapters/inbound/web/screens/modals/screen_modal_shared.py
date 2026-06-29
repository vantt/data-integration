"""Web adapter — shared helpers and service protocols for S03 party modals.

These are reused across the per-modal sub-routers (m03 tags, m04 owner,
m05 task, m06 custom fields, m15 edit contact/address/core).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional, Protocol

from fastapi.responses import HTMLResponse

from domain.entities.app_user import AppUser
from domain.entities.party import PartyIdentity
from domain.entities.profile import CustomFieldDef, Party360, Tag
from domain.entities.task import Task


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


PRIO_STR_TO_INT: dict[str, int] = {"P1": 2, "P2": 1, "P3": 0, "P4": 0}
PRIO_INT_TO_STR: dict[int, str] = {2: "P1", 1: "P2", 0: "P3"}


def parse_priority(s: str) -> int:
    """Convert P1-P4 code or numeric string to domain int (2=urgent, 1=high, 0=normal)."""
    v = s.strip().upper()
    if v in PRIO_STR_TO_INT:
        return PRIO_STR_TO_INT[v]
    return int(v) if v.isdigit() else 0


def redirect_to_customer(party_id: str) -> HTMLResponse:
    """HTMX redirect back to the Customer 360 screen."""
    return HTMLResponse(content="", headers={"HX-Redirect": f"/customers/{party_id}"})


def parse_custom(raw) -> dict:
    """Coerce a stored custom-fields value (dict or JSON string) into a dict."""
    if isinstance(raw, dict):
        return dict(raw)
    try:
        return json.loads(raw or "{}")
    except Exception:
        return {}


# ── Service protocols ─────────────────────────────────────────────────────────

class ProfileSvc(Protocol):
    def get_party_360(self, party_id: str) -> Optional[Party360]: ...
    def list_tags(self, category: str) -> list[Tag]: ...
    def list_party_tags(self, party_id: str) -> list: ...
    def attach_tag(self, party_id: str, tag_id: str) -> None: ...
    def detach_tag(self, party_id: str, tag_id: str) -> None: ...
    def list_custom_field_defs(self, entity_type: Optional[str] = None) -> list[CustomFieldDef]: ...
    def upsert_profile(
        self,
        party_id: str,
        *,
        owner_user_id: Optional[str] = None,
        lifecycle_stage: Optional[str] = None,
        acquisition_source: Optional[str] = None,
        birthday: Optional[str] = None,
        gender: Optional[str] = None,
        address: Optional[dict] = None,
        preferences: Optional[dict] = None,
        consent_contact: Optional[str] = None,
        custom: Optional[dict] = None,
    ) -> object: ...


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
