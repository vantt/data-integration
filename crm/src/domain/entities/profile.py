"""CRM Customer 360 profile entities — CustomerProfile, CustomFieldDef, Tag, Note, Party360.

Pure dataclasses; no HTTP/DB adapter imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from crm.src.domain.entities.party import Party, PartyIdentity

# ---------------------------------------------------------------------------
# Lifecycle stage constants
# ---------------------------------------------------------------------------
LIFECYCLE_LEAD = "lead"
LIFECYCLE_NEW = "new"
LIFECYCLE_ACTIVE = "active"
LIFECYCLE_AT_RISK = "at_risk"
LIFECYCLE_CHURNED = "churned"
VALID_LIFECYCLE_STAGES = [
    LIFECYCLE_LEAD,
    LIFECYCLE_NEW,
    LIFECYCLE_ACTIVE,
    LIFECYCLE_AT_RISK,
    LIFECYCLE_CHURNED,
]

# ---------------------------------------------------------------------------
# Custom field data type constants
# ---------------------------------------------------------------------------
FIELD_TYPE_TEXT = "text"
FIELD_TYPE_NUMBER = "number"
FIELD_TYPE_DATE = "date"
FIELD_TYPE_BOOL = "bool"
FIELD_TYPE_SELECT = "select"
FIELD_TYPE_MULTISELECT = "multiselect"
VALID_CUSTOM_DATA_TYPES = [
    FIELD_TYPE_TEXT,
    FIELD_TYPE_NUMBER,
    FIELD_TYPE_DATE,
    FIELD_TYPE_BOOL,
    FIELD_TYPE_SELECT,
    FIELD_TYPE_MULTISELECT,
]


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

@dataclass
class CustomerProfile:
    """Enrichment data owned by the CRM for one party (1:1 with crm_customer_profile)."""
    party_id: str                           # FK → crm_party (also PK — 1:1)
    consent_contact: bool                   # false = opted out (blocks campaigns)
    created_at: str                         # UTC ISO-8601 with 'Z'
    updated_at: str                         # UTC ISO-8601 with 'Z'
    owner_user_id: Optional[str] = None     # FK → crm_app_user (assigned sales rep)
    lifecycle_stage: Optional[str] = None   # lead|new|active|at_risk|churned
    acquisition_source: Optional[str] = None
    birthday: Optional[str] = None          # YYYY-MM-DD or None
    gender: Optional[str] = None            # male|female|other|unknown; migration 0016
    address: Optional[dict] = None          # {province, district, ward, street}
    preferences: Optional[dict] = None     # manually recorded preferences
    custom: dict = field(default_factory=dict)  # values keyed by CustomFieldDef.field_key


@dataclass
class CustomFieldDef:
    """Describes one dynamic field stored in CustomerProfile.custom JSON blob.

    Registry drives UI rendering and server-side validation without schema migrations.
    """
    field_id: str           # UUID
    entity_type: str        # "party" | "order" (extensible)
    field_key: str          # key inside the JSON custom blob; immutable after creation
    label: str              # human-readable display label
    data_type: str          # text|number|date|bool|select|multiselect
    is_required: bool
    is_active: bool
    sort_order: int
    options: Optional[list] = None      # allowed values for select/multiselect
    section: Optional[str] = None       # free-text grouping label (migration 0014)


@dataclass
class Tag:
    """Label that can be attached to many parties."""
    tag_id: str             # UUID
    name: str               # slug: lowercase, hyphen, machine-readable
    category: Optional[str] = None
    color: Optional[str] = None
    display_label: Optional[str] = None     # human-readable label (Vietnamese OK); falls back to name in UI


@dataclass
class PartyTag:
    """Join record between a party and a tag; carries denormalised tag fields for reads."""
    party_id: str
    tag_id: str
    name: str
    tagged_at: str                          # UTC ISO-8601 with 'Z'
    category: Optional[str] = None
    color: Optional[str] = None
    tagged_by: Optional[str] = None         # FK → crm_app_user (nullable)
    display_label: Optional[str] = None     # denormalised from crm_tag.display_label


@dataclass
class Note:
    """Typed note attached to a party, supporting pins, visibility, and task linkage."""
    note_id: str            # UUID
    party_id: str           # FK → crm_party
    body: str
    created_at: str         # UTC ISO-8601 with 'Z'
    author_user_id: Optional[str] = None    # FK → crm_app_user (nullable)
    # Migration 0010
    note_type: str = "general"      # general|preference|contact_pref|warning|outcome|internal
    pinned: bool = False
    visibility: str = "team"        # team|private
    task_id: Optional[str] = None           # FK → crm_task (retail activation chain)
    source_activity_id: Optional[str] = None  # FK → crm_activity (migration 0019)
    deleted_at: Optional[str] = None  # soft delete


@dataclass
class PartyInsight:
    """Rep-curated insight about a party (migration 0011).

    Distinct from machine-generated wh_customer_insight (cache.db).
    Surfaces in P01 rep_insights_block alongside warehouse signals.
    """
    insight_id: str
    party_id: str
    insight_type: str           # persona|buying_pattern|decision_style|life_event|relationship|advocate_signal
    body: str
    confidence: str             # low|medium|high
    created_at: str             # UTC ISO-8601 with 'Z'
    created_by: Optional[str] = None        # FK → crm_app_user
    source_note_id: Optional[str] = None    # set when promoted from a note via M16
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None        # soft delete


@dataclass
class Party360:
    """Aggregated read model from crm_party_360 view.

    Combines party + profile fields + tags + identities for the detail screen.
    """
    # Core party fields
    party_id: str
    party_type: str
    display_name: str
    primary_phone: str
    primary_email: str
    status: str
    is_merged: bool
    party_created_at: str
    party_updated_at: str
    # Profile fields (zero/None when no profile exists)
    consent_contact: bool = False
    profile_updated_at: str = ""
    owner_user_id: Optional[str] = None
    lifecycle_stage: Optional[str] = None
    acquisition_source: Optional[str] = None
    birthday: Optional[str] = None
    gender: Optional[str] = None            # male|female|other|unknown; migration 0016
    address: Optional[str] = None           # raw JSON string from the view
    preferences: Optional[str] = None      # raw JSON string from the view
    custom: str = ""                        # raw JSON from the view
    # Address fields (migration 0007) — R13: address_source distinguishes sync vs manual
    address_line: Optional[str] = None
    ward: Optional[str] = None
    district: Optional[str] = None
    province: Optional[str] = None
    address_source: str = "sapo_sync"       # sapo_sync | manual
    address_note: Optional[str] = None
    # Relations
    tags: list[PartyTag] = field(default_factory=list)
    identities: list[PartyIdentity] = field(default_factory=list)
