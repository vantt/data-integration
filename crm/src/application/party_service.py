"""party_service.py — PartyService: golden-record creation and identity attachment.

Called by PartySeedService to turn wh_party_seed rows into crm_party + identities.
Normalisation helpers delegate to domain value objects (PhoneNumber, Email).
"""
from __future__ import annotations

import uuid
from typing import Optional

from shared.timestamps import utc_now
from domain.entities.party import Party, PartyIdentity
from domain.ports.party_repository import PartyRepository
from domain.value_objects.phone import PhoneNumber
from domain.value_objects.email import Email


# ---------------------------------------------------------------------------
# Normalisation — public free functions kept for backward compatibility;
# logic lives in the value objects.
# ---------------------------------------------------------------------------

def normalize_phone(raw: str) -> str:
    """Convert Vietnamese phone to local VN format. Delegates to PhoneNumber.normalize."""
    return PhoneNumber.normalize(raw)


def phone_to_e164(local: str) -> str:
    """Convert local VN format to E.164. Delegates to PhoneNumber.to_e164."""
    return PhoneNumber.to_e164(local)


def normalize_email(raw: str) -> str:
    """Lower-case and strip whitespace. Delegates to Email.normalize."""
    return Email.normalize(raw)


# ---------------------------------------------------------------------------
# PartyService
# ---------------------------------------------------------------------------

class PartyService:
    """Handles golden-record creation and identity attachment.

    Mirrors Go PartyService in crm/src/internal/application/party_service.go.
    All persistence is delegated to PartyRepository; no direct DB access here.
    """

    def __init__(self, party_repo: PartyRepository) -> None:
        self._repo = party_repo

    # ── Public API ────────────────────────────────────────────────────────────

    def upsert_from_sapo_identity(
        self,
        sapo_id: str,
        phone: str,
        email: str,
        display_name: str,
        src_quality: str,
        quality: str,
        customer_code: str = "",
        address1: str = "",
        ward: str = "",
        district: str = "",
        province: str = "",
    ) -> Party:
        """Ensure a Party exists for the given Sapo customer and attach identities.

        Flow (mirrors Go UpsertFromSapoIdentity):
          1. Normalize phone/email.
          2. Look up party via identity(sapo_customer, sapo_id).
          3. If not found → create Party + sapo_customer identity atomically.
          4. Attach phone/email identities (UNIQUE guard at DB level).
          5. Backfill empty display_name/primary_phone/primary_email (non-destructive).

        Returns the resolved Party.
        """
        norm_phone = normalize_phone(phone)
        norm_email = normalize_email(email)

        # Step 1: find by sapo_customer identity
        party = self._repo.find_by_identity("sapo_customer", sapo_id)

        if party is None:
            # Step 2: create party + sapo_customer identity atomically
            now = utc_now()
            party = Party(
                party_id=str(uuid.uuid4()),
                party_type="person",
                display_name=display_name,
                primary_phone=norm_phone,
                primary_email=norm_email,
                status="active",
                is_merged=False,
                merged_into=None,
                created_at=now,
                updated_at=now,
            )
            sapo_identity = PartyIdentity(
                identity_id=str(uuid.uuid4()),
                party_id=party.party_id,
                source_system="sapo_v2",
                identity_type="sapo_customer",
                identity_value=sapo_id,
                confidence=1.0,
                is_primary=True,
                source_contact_quality=src_quality,
                contact_quality=quality,
                created_at=now,
                verified_at=None,
            )
            self._repo.create_with_identities(party, [sapo_identity])

        # Step 3: attach phone/email/customer_code identities (INSERT OR IGNORE semantics)
        if norm_phone:
            self._upsert_identity(party.party_id, "sapo", "phone", norm_phone, 1.0, False, src_quality, quality)
        if norm_email:
            self._upsert_identity(party.party_id, "sapo", "email", norm_email, 1.0, False, src_quality, quality)
        if customer_code:
            self._upsert_identity(party.party_id, "sapo", "customer_code", customer_code, 1.0, False, src_quality, quality)

        # Step 4: backfill empty golden-record fields (non-destructive)
        dirty = False
        if not party.display_name and display_name:
            party.display_name = display_name
            dirty = True
        if not party.primary_phone and norm_phone:
            party.primary_phone = norm_phone
            dirty = True
        if not party.primary_email and norm_email:
            party.primary_email = norm_email
            dirty = True
        if dirty:
            party.updated_at = utc_now()
            self._repo.update(party)

        # Step 5: non-destructive address seed (only fills NULL slots)
        if any([address1, ward, district, province]):
            self._repo.seed_address(party.party_id, address1 or None, ward or None, district or None, province or None)

        return party

    def backfill_party(
        self,
        party_id: str,
        display_name: str,
        phone: str,
        email: str,
    ) -> None:
        """Fill empty fields on an existing party without overwriting present values."""
        party = self._repo.get_by_id(party_id)
        if party is None:
            return
        norm_phone = normalize_phone(phone)
        norm_email = normalize_email(email)
        dirty = False
        if not party.display_name and display_name:
            party.display_name = display_name
            dirty = True
        if not party.primary_phone and norm_phone:
            party.primary_phone = norm_phone
            dirty = True
        if not party.primary_email and norm_email:
            party.primary_email = norm_email
            dirty = True
        if dirty:
            party.updated_at = utc_now()
            self._repo.update(party)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _upsert_identity(
        self,
        party_id: str,
        source: str,
        id_type: str,
        id_value: str,
        confidence: float,
        is_primary: bool,
        src_quality: str,
        quality: str,
    ) -> None:
        identity = PartyIdentity(
            identity_id=str(uuid.uuid4()),
            party_id=party_id,
            source_system=source,
            identity_type=id_type,
            identity_value=id_value,
            confidence=confidence,
            is_primary=is_primary,
            source_contact_quality=src_quality,
            contact_quality=quality,
            created_at=utc_now(),
            verified_at=None,
        )
        self._repo.upsert_identity(identity)
