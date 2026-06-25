"""CRM LastContact domain entity — per-customer latest contact snapshot.

One row per customer; upserted on every activity log submission.
Links to crm_activity via last_activity_id for full-detail drill-through.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Outcomes that indicate the customer was successfully reached.
POSITIVE_OUTCOMES = frozenset({"answered", "replied", "met"})
# Outcomes that indicate a future follow-up is already scheduled.
PENDING_OUTCOMES = frozenset({"callback"})
# Outcomes that indicate the customer actively rejected contact.
REJECTED_OUTCOMES = frozenset({"refused"})


@dataclass
class LastContact:
    """Snapshot of the most recent contact attempt for one party."""
    party_id: str
    last_activity_id: str           # FK → crm_activity.activity_id
    last_contacted_at: str          # UTC ISO-8601 (occurred_at from activity)
    last_contact_result: str        # enum: answered|no_answer|callback|refused|replied|no_reply|met|not_met|other
    channel: Optional[str] = None   # call|zalo|fb|email|visit|other
    updated_at: str = ""
