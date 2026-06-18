"""party_service.py — PartyService: golden-record creation and identity attachment.

Called by PartySeedService to turn wh_party_seed rows into crm_party + identities.
Normalisation helpers (normalize_phone, normalize_email) port normalize.go exactly.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from domain.entities.party import Party, PartyIdentity
from domain.ports.party_repository import PartyRepository


# ---------------------------------------------------------------------------
# Timestamp helper
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    """Return current UTC time as ISO-8601 with milliseconds and Z suffix."""
    now = datetime.now(timezone.utc)
    ms = now.microsecond // 1000
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms:03d}Z"


# ---------------------------------------------------------------------------
# Normalisation (ports normalize.go)
# ---------------------------------------------------------------------------

_NON_DIGIT_NON_PLUS = re.compile(r"[^\d+]")


def normalize_phone(raw: str) -> str:
    """Convert Vietnamese phone to canonical +84 format.

    Rules (mirrors NormalizePhone in normalize.go):
      - Strip everything except digits and '+'.
      - "+84..." → kept as-is.
      - "84..."  (≥11 chars after strip) → prepend "+".
      - "0..."   → replace leading 0 with "+84".
      - No digit remaining after strip → return "".
      - Other unrecognised formats → returned stripped only.
    """
    s = _NON_DIGIT_NON_PLUS.sub("", raw)
    if not s:
        return ""
    # Must have at least one digit
    if not any(c.isdigit() for c in s):
        return ""
    if s.startswith("+84"):
        return s
    if s.startswith("84") and len(s) >= 11:
        return "+" + s
    if s.startswith("0"):
        return "+84" + s[1:]
    return s


def normalize_email(raw: str) -> str:
    """Lower-case and strip whitespace from an email address."""
    return raw.strip().lower()


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
            now = _utc_now()
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
            party.updated_at = _utc_now()
            self._repo.update(party)

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
            party.updated_at = _utc_now()
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
            created_at=_utc_now(),
            verified_at=None,
        )
        self._repo.upsert_identity(identity)
