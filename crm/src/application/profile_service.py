"""ProfileService — Customer 360 business logic.

Depends only on domain entities and port protocols; no adapter imports.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Optional

from shared.timestamps import utc_now
from domain.entities.profile import (
    CustomerProfile,
    CustomFieldDef,
    PartyTag,
    Note,
    Party360,
    Tag,
)
from domain.ports.profile_repository import (
    ProfileRepository,
    CustomFieldRepository,
    TagRepository,
    NoteRepository,
)


# ---------------------------------------------------------------------------
# Validator (ported from domain/custom_field_validator.go)
# ---------------------------------------------------------------------------

class CustomFieldError(Exception):
    def __init__(self, field_key: str, message: str) -> None:
        self.field_key = field_key
        self.message = message
        super().__init__(f"custom field {field_key!r}: {message}")


def _validate_custom_field(defn: CustomFieldDef, raw_value: str) -> Optional[CustomFieldError]:
    """Validate one (def, raw_value) pair. Returns error or None."""
    if defn.is_required and not raw_value.strip():
        return CustomFieldError(defn.field_key, "required field is missing or empty")
    if not raw_value:
        return None  # allow clearing optional fields

    dt = defn.data_type
    if dt == "text":
        return None
    if dt == "number":
        try:
            float(raw_value)
        except ValueError:
            return CustomFieldError(defn.field_key, f"expected a number, got {raw_value!r}")
    elif dt == "date":
        try:
            datetime.strptime(raw_value, "%Y-%m-%d")
        except ValueError:
            return CustomFieldError(defn.field_key, f"expected date YYYY-MM-DD, got {raw_value!r}")
    elif dt == "bool":
        if raw_value.lower() not in ("true", "false"):
            return CustomFieldError(defn.field_key, f"expected true or false, got {raw_value!r}")
    elif dt == "select":
        opts = defn.options or []
        if raw_value.strip() not in opts:
            return CustomFieldError(defn.field_key, f"value {raw_value!r} not in allowed options {opts}")
    elif dt == "multiselect":
        opts = defn.options or []
        for item in (p.strip() for p in raw_value.split(",") if p.strip()):
            if item not in opts:
                return CustomFieldError(defn.field_key, f"value {item!r} not in allowed options {opts}")
    # unknown data_type: skip (forward-compatible)
    return None


def _validate_custom_map(
    defs: list[CustomFieldDef], custom_map: dict[str, str]
) -> list[CustomFieldError]:
    """Validate a full key→value map against active defs. Returns all errors (non-short-circuit)."""
    defs_by_key = {d.field_key: d for d in defs if d.is_active}
    errors: list[CustomFieldError] = []

    for key, val in custom_map.items():
        defn = defs_by_key.get(key)
        if defn is None:
            continue  # unknown key — allowed, not validated
        err = _validate_custom_field(defn, val)
        if err:
            errors.append(err)

    # Check required active fields absent from the map
    for key, defn in defs_by_key.items():
        if not defn.is_required:
            continue
        val = custom_map.get(key, "")
        if not val.strip():
            errors.append(CustomFieldError(key, "required field is missing or empty"))

    return errors


# ---------------------------------------------------------------------------
# ProfileService
# ---------------------------------------------------------------------------

class ProfileService:
    """Orchestrates profile enrichment, custom-field validation, tags, and notes."""

    def __init__(
        self,
        profile_repo: ProfileRepository,
        custom_field_repo: CustomFieldRepository,
        tag_repo: TagRepository,
        note_repo: NoteRepository,
    ) -> None:
        self._profiles = profile_repo
        self._custom_fields = custom_field_repo
        self._tags = tag_repo
        self._notes = note_repo

    # --- Profile ---

    def get_party_360(self, party_id: str) -> Optional[Party360]:
        return self._profiles.get_party360(party_id)

    def get_profile(self, party_id: str) -> Optional[CustomerProfile]:
        return self._profiles.get_profile(party_id)

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
    ) -> CustomerProfile:
        """Create or update the profile for party_id.

        Only fields passed with a non-None value are written; omitted fields leave
        an existing profile unchanged. On creation, None fields become the
        CustomerProfile dataclass defaults.
        """
        if not party_id:
            raise ValueError("profile service: upsert: party_id required")
        now = utc_now()
        existing = self._profiles.get_profile(party_id)
        if existing is not None:
            if owner_user_id is not None:
                existing.owner_user_id = owner_user_id
            if lifecycle_stage is not None:
                existing.lifecycle_stage = lifecycle_stage
            if acquisition_source is not None:
                existing.acquisition_source = acquisition_source
            if birthday is not None:
                existing.birthday = birthday
            if gender is not None:
                existing.gender = gender
            if address is not None:
                existing.address = address
            if preferences is not None:
                existing.preferences = preferences
            if consent_contact is not None:
                existing.consent_contact = consent_contact
            if custom is not None:
                existing.custom = custom
            existing.updated_at = now
            profile = existing
        else:
            profile = CustomerProfile(
                party_id=party_id,
                owner_user_id=owner_user_id,
                lifecycle_stage=lifecycle_stage,
                acquisition_source=acquisition_source,
                birthday=birthday,
                gender=gender,
                address=address,
                preferences=preferences,
                consent_contact=consent_contact,
                custom=custom if custom is not None else {},
                created_at=now,
                updated_at=now,
            )
        self._profiles.upsert_profile(profile)
        return profile

    def update_custom(self, party_id: str, field_key: str, value: str) -> None:
        """Merge {field_key: value} into the existing custom JSON, validate, then persist."""
        # 1. Load active field defs for 'party'
        defs = self._custom_fields.list_active_defs("party")

        # 2. Load existing custom dict (reset on corruption)
        existing: dict[str, str] = {}
        profile = self._profiles.get_profile(party_id)
        if profile and profile.custom:
            if isinstance(profile.custom, dict):
                existing = {k: str(v) for k, v in profile.custom.items()}
            else:
                try:
                    raw = json.loads(profile.custom)
                    existing = {k: str(v) for k, v in raw.items()}
                except (json.JSONDecodeError, AttributeError):
                    existing = {}

        # 3. Merge single key
        existing[field_key] = value

        # 4. Validate full merged map
        errors = _validate_custom_map(defs, existing)
        if errors:
            msgs = "; ".join(str(e) for e in errors)
            raise ValueError(f"profile service: custom field validation failed: {msgs}")

        # 5. Persist
        merged_json = json.dumps(existing)
        if profile is None:
            now = utc_now()
            self._profiles.upsert_profile(CustomerProfile(
                party_id=party_id,
                custom=existing,
                created_at=now,
                updated_at=now,
            ))
        else:
            self._profiles.update_custom_json(party_id, merged_json)

    # --- Custom field defs ---

    def list_custom_field_defs(self, entity_type: Optional[str] = None) -> list[CustomFieldDef]:
        return self._custom_fields.list_active_defs(entity_type or "party")

    def create_custom_field_def(self, def_data: CustomFieldDef) -> CustomFieldDef:
        if not def_data.field_id:
            def_data.field_id = str(uuid.uuid4())
        if not def_data.entity_type:
            def_data.entity_type = "party"
        self._custom_fields.create_def(def_data)
        return def_data

    def update_custom_field_def(self, field_id: str, **kwargs) -> None:
        defn = self._custom_fields.get_def(field_id)
        if defn is None:
            raise ValueError(f"profile service: custom field def {field_id!r} not found")
        for k, v in kwargs.items():
            if hasattr(defn, k):
                setattr(defn, k, v)
        self._custom_fields.update_def(defn)

    # --- Tags ---

    def attach_tag(self, party_id: str, tag_id: str, user_id: Optional[str] = None) -> None:
        tag = self._tags.get_tag(tag_id)
        if tag is None:
            raise ValueError(f"profile service: tag {tag_id!r} not found")
        pt = PartyTag(
            party_id=party_id,
            tag_id=tag_id,
            name=tag.name,
            tagged_at=utc_now(),
            category=tag.category,
            color=tag.color,
            tagged_by=user_id,
        )
        self._tags.attach_tag(pt)

    def detach_tag(self, party_id: str, tag_id: str) -> None:
        self._tags.detach_tag(party_id, tag_id)

    def list_party_tags(self, party_id: str) -> list[PartyTag]:
        return self._tags.list_party_tags(party_id)

    def list_tags(self, category: str) -> list[Tag]:
        return self._tags.list_tags(category)

    def get_tag(self, tag_id: str) -> Optional[Tag]:
        return self._tags.get_tag(tag_id)

    def create_tag(self, name: str, category: str, color: str, display_label: str = "") -> Tag:
        tag = Tag(
            tag_id=str(uuid.uuid4()),
            name=name,
            display_label=display_label or None,
            category=category or "general",
            color=color or "default",
        )
        self._tags.create_tag(tag)
        return tag

    def update_tag(self, tag_id: str, name: str, category: str, color: str, display_label: str = "") -> None:
        tag = Tag(
            tag_id=tag_id,
            name=name,
            display_label=display_label or None,
            category=category or "general",
            color=color or "default",
        )
        self._tags.update_tag(tag)

    def delete_tag(self, tag_id: str) -> None:
        self._tags.delete_tag(tag_id)

    # --- Notes ---

    def add_note(self, party_id: str, body: str, author_user_id: Optional[str] = None,
                 note_type: str = "general", pinned: bool = False, visibility: str = "team",
                 source_activity_id: Optional[str] = None) -> Note:
        if not body.strip():
            raise ValueError("profile service: note body must not be empty")
        note = Note(
            note_id=str(uuid.uuid4()),
            party_id=party_id,
            body=body,
            author_user_id=author_user_id,
            created_at=utc_now(),
            note_type=note_type,
            pinned=pinned,
            visibility=visibility,
            source_activity_id=source_activity_id,
        )
        self._notes.add_note(note)
        return note

    def list_notes(self, party_id: str) -> list[Note]:
        return self._notes.list_notes(party_id)

    def update_note(self, note_id: str, body: str, note_type: str = "general",
                    pinned: bool = False, visibility: str = "team") -> None:
        if not body.strip():
            raise ValueError("profile service: note body must not be empty")
        self._notes.update_note(note_id, body, note_type, pinned, visibility)

    def delete_note(self, note_id: str) -> None:
        self._notes.soft_delete_note(note_id)

    # --- Owner ---

    def assign_owner(self, party_id: str, owner_user_id: str) -> None:
        """Set the assigned sales rep (owner_user_id) on the profile."""
        self.upsert_profile(party_id, owner_user_id=owner_user_id)
