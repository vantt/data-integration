"""ProfileService — Customer 360 profile read/write business logic.

Depends only on domain entities and port protocols; no adapter imports.

Responsibilities kept here:
  - Party 360 view (get_party_360)
  - Profile upsert / owner assignment
  - Custom field value merge + validation (update_custom)

Tag CRUD → TagService
Note CRUD → NoteService
Custom field definition CRUD → CustomFieldService
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional

from shared.timestamps import utc_now
from domain.result import ValidationResult

if TYPE_CHECKING:
    from adapters.outbound.sqlite.connection import CRMDatabase

from application.custom_field_service import _validate_custom_map

from domain.entities.profile import (
    CustomerProfile,
    CustomFieldDef,
    Party360,
)
from domain.ports.profile_repository import ProfileRepository
from domain.ports.custom_field_repository import CustomFieldRepository


class ProfileService:
    """Orchestrates profile enrichment and custom-field value validation."""

    def __init__(
        self,
        profile_repo: ProfileRepository,
        custom_field_repo: CustomFieldRepository,
        db: Optional[CRMDatabase] = None,
    ) -> None:
        self._profiles = profile_repo
        self._custom_fields = custom_field_repo
        self._db = db

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
        if self._db:
            self._db.commit()
        return profile

    def update_custom(self, party_id: str, field_key: str, value: str) -> ValidationResult:
        """Merge {field_key: value} into the existing custom JSON, validate, then persist.

        Returns ValidationResult; caller checks result.ok rather than catching ValueError.
        """
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

        # 4. Validate full merged map — return errors without persisting
        errors = _validate_custom_map(defs, existing)
        if errors:
            return ValidationResult(errors=errors)

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
        if self._db:
            self._db.commit()
        return ValidationResult()

    # --- Owner ---

    def assign_owner(self, party_id: str, owner_user_id: str) -> None:
        """Set the assigned sales rep (owner_user_id) on the profile."""
        self.upsert_profile(party_id, owner_user_id=owner_user_id)
