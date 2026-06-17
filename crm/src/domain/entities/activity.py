"""CRM Activity domain entity — recorded touchpoints between staff and a party.

Pure dataclasses; no HTTP/DB adapter imports.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Activity type constants
# ---------------------------------------------------------------------------
ACTIVITY_TYPE_CALL = "call"
ACTIVITY_TYPE_NOTE = "note"
ACTIVITY_TYPE_VISIT = "visit"
ACTIVITY_TYPE_EMAIL = "email"
ACTIVITY_TYPE_CHAT = "chat"
ACTIVITY_TYPE_OTHER = "other"
VALID_ACTIVITY_TYPES = [
    ACTIVITY_TYPE_CALL,
    ACTIVITY_TYPE_NOTE,
    ACTIVITY_TYPE_VISIT,
    ACTIVITY_TYPE_EMAIL,
    ACTIVITY_TYPE_CHAT,
    ACTIVITY_TYPE_OTHER,
]

# ---------------------------------------------------------------------------
# Direction constants
# ---------------------------------------------------------------------------
DIRECTION_IN = "in"
DIRECTION_OUT = "out"


# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------

@dataclass
class Activity:
    """One recorded touchpoint between a staff member and a party."""
    activity_id: str            # UUID
    party_id: str               # FK → crm_party
    activity_type: str          # call|note|visit|email|chat|other
    occurred_at: str            # UTC ISO-8601
    created_at: str             # UTC ISO-8601
    direction: Optional[str] = None         # in|out — None when not applicable
    channel: Optional[str] = None           # phone|messenger|zalo|store|...
    subject: Optional[str] = None
    body: Optional[str] = None
    outcome: Optional[str] = None
    related_order_code: Optional[str] = None  # soft ref; order lives in warehouse
    staff_user_id: Optional[str] = None     # FK → crm_app_user (nullable)
