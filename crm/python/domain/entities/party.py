"""CRM Party domain entities — golden record, identities, dedup, merge log, seed.

Pure dataclasses; no HTTP/DB adapter imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Party type constants
# ---------------------------------------------------------------------------
PARTY_TYPE_PERSON = "person"
PARTY_TYPE_ORG = "org"
VALID_PARTY_TYPES = [PARTY_TYPE_PERSON, PARTY_TYPE_ORG]

# ---------------------------------------------------------------------------
# Party status constants
# ---------------------------------------------------------------------------
PARTY_STATUS_ACTIVE = "active"
PARTY_STATUS_INACTIVE = "inactive"
PARTY_STATUS_BLOCKED = "blocked"
VALID_PARTY_STATUSES = [PARTY_STATUS_ACTIVE, PARTY_STATUS_INACTIVE, PARTY_STATUS_BLOCKED]

# ---------------------------------------------------------------------------
# Identity type constants
# ---------------------------------------------------------------------------
IDENTITY_TYPE_SAPO_CUSTOMER = "sapo_customer"
IDENTITY_TYPE_PHONE = "phone"
IDENTITY_TYPE_PHONE_SECONDARY = "phone_secondary"
IDENTITY_TYPE_EMAIL = "email"
IDENTITY_TYPE_PSID = "psid"
IDENTITY_TYPE_ZALO_UID = "zalo_uid"
IDENTITY_TYPE_ZALO = "zalo"
IDENTITY_TYPE_FACEBOOK = "facebook"
IDENTITY_TYPE_CUSTOMER_CODE = "customer_code"
VALID_IDENTITY_TYPES = [
    IDENTITY_TYPE_SAPO_CUSTOMER,
    IDENTITY_TYPE_PHONE,
    IDENTITY_TYPE_PHONE_SECONDARY,
    IDENTITY_TYPE_EMAIL,
    IDENTITY_TYPE_PSID,
    IDENTITY_TYPE_ZALO_UID,
    IDENTITY_TYPE_ZALO,
    IDENTITY_TYPE_FACEBOOK,
    IDENTITY_TYPE_CUSTOMER_CODE,
]

# ---------------------------------------------------------------------------
# Contact status constants (migration 0008)
# ---------------------------------------------------------------------------
CONTACT_STATUS_ACTIVE = "active"
CONTACT_STATUS_INVALID = "invalid"
CONTACT_STATUS_UNREACHABLE = "unreachable"
VALID_CONTACT_STATUSES = [
    CONTACT_STATUS_ACTIVE,
    CONTACT_STATUS_INVALID,
    CONTACT_STATUS_UNREACHABLE,
]

# ---------------------------------------------------------------------------
# Contact quality constants
# ---------------------------------------------------------------------------
CONTACT_QUALITY_MASKED = "masked"
CONTACT_QUALITY_UNVERIFIED = "unverified"
CONTACT_QUALITY_VERIFIED = "verified"
VALID_CONTACT_QUALITIES = [
    CONTACT_QUALITY_MASKED,
    CONTACT_QUALITY_UNVERIFIED,
    CONTACT_QUALITY_VERIFIED,
]

# ---------------------------------------------------------------------------
# Dedup candidate status constants
# ---------------------------------------------------------------------------
DEDUP_STATUS_PENDING = "pending"
DEDUP_STATUS_MERGED = "merged"
DEDUP_STATUS_REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

@dataclass
class Party:
    """Golden record for a unique real-world customer/org.

    Multiple Sapo customer IDs, phones, emails, etc. converge to one Party.
    """
    party_id: str                       # UUID (TEXT in SQLite)
    party_type: str                     # person|org
    display_name: str
    primary_phone: str                  # normalised E.164-ish (+84...)
    primary_email: str
    status: str                         # active|inactive|blocked
    is_merged: bool
    created_at: str                     # UTC ISO-8601 with 'Z'
    updated_at: str                     # UTC ISO-8601 with 'Z'
    merged_into: Optional[str] = None   # FK → party_id of surviving party


@dataclass
class PartyIdentity:
    """Maps one identity value (phone, email, Sapo customer ID…) to a Party.

    UNIQUE(identity_type, identity_value) enforces one-owner-per-identity at DB level.
    """
    identity_id: str            # UUID
    party_id: str               # FK → crm_party
    source_system: str          # sapo|messenger|zalo|manual
    identity_type: str          # sapo_customer|phone|phone_secondary|email|psid|zalo|facebook|…
    identity_value: str         # normalised value (E.164 for phone, per R5)
    confidence: float           # 0.0–1.0
    is_primary: bool
    source_contact_quality: str # masked|real — immutable, set at creation
    contact_quality: str        # masked|unverified|verified — mutable
    created_at: str
    verified_at: Optional[str] = None       # nullable UTC ISO-8601
    # Migration 0008
    display_label: Optional[str] = None     # human-readable label e.g. "Số công ty"
    contact_status: str = "active"          # active|invalid|unreachable
    is_preferred: bool = False              # True = preferred channel for outreach


@dataclass
class DedupCandidate:
    """Suspect-match pair queued for manual review."""
    candidate_id: str           # UUID
    party_a: str                # FK → crm_party
    party_b: str                # FK → crm_party
    match_rule: str             # exact_phone|exact_email|fts_name_phone
    match_score: float          # 0.0–1.0
    status: str                 # pending|merged|rejected
    created_at: str
    reviewed_by: Optional[str] = None   # nullable FK → crm_app_user
    reviewed_at: Optional[str] = None   # nullable UTC ISO-8601


@dataclass
class MergeLog:
    """Records every merge operation; carries a JSON snapshot for undo."""
    merge_id: str               # UUID
    surviving_party_id: str     # FK → crm_party (winner)
    merged_party_id: str        # soft ref — the absorbed party
    reason: str
    snapshot: str               # JSON: pre-merge state (identities + party flags)
    merged_at: str              # UTC ISO-8601 with 'Z'
    merged_by: Optional[str] = None    # nullable FK → crm_app_user
    undone_at: Optional[str] = None


@dataclass
class PartySeed:
    """Row from wh_party_seed used by the seed consumer.

    DisplayName/Phone/Email are enriched from wh_customer_base (joined by
    the integer customer_id). Empty when no matching row exists.
    """
    customer_id: int
    customer_key: str
    display_name: str
    phone: str
    email: str
    source_contact_quality: str  # masked|real — warehouse-computed, immutable
    contact_quality: str         # masked|unverified|verified — initial value from warehouse
    seen_at: str = ""
