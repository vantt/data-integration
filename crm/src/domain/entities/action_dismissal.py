"""action_dismissal.py — B5 dismiss-TTL read model (crm_action_dismissal).

Pure dataclass; no HTTP/DB adapter imports. Populated by
SQLiteActionStateRepository.list_active_dismissals() for the manager
transparency view (AI-11) — read-only, no mutation methods here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ActionDismissal:
    """One active (party_id, action_type) dismissal row, enriched for display.

    party_display/dismissed_by_display are resolved by the repository query
    (name → phone → placeholder fallback, matching TaskService._customer_fallback_label)
    so the template needs no extra lookups.
    """
    party_id: str
    action_type: str
    dismissed_by_user_id: Optional[str]
    dismissed_at: str
    dismissed_until: str
    party_display: str          # crm_party.display_name, else primary_phone, else placeholder
    dismissed_by_display: str   # crm_app_user.full_name, else "Hệ thống"
