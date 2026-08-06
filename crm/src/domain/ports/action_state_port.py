"""action_state_port.py — domain port (Protocol) for action state writes."""
from __future__ import annotations

from typing import Optional, Protocol

from domain.entities.action_dismissal import ActionDismissal


class ActionStatePort(Protocol):
    """Outbound port for crm_action_state lifecycle mutations."""

    def dismiss(self, action_id: str, user_id: Optional[str] = None) -> None:
        """Mark an action as dismissed (optionally record who dismissed it)."""
        ...

    def snooze(self, action_id: str, until_date: str, user_id: Optional[str] = None) -> None:
        """Snooze an action until a given ISO-8601 date string."""
        ...

    def reopen(self, action_id: str) -> None:
        """Reset a dismissed or snoozed action back to open."""
        ...

    def resolve_party_id(self, action_id: str) -> Optional[str]:
        """Resolve action_id to its true party_id (cache-join lookup) —
        used to verify an action genuinely belongs to the party a
        bulk-resolve request claims it does, before dismiss/snooze mutates
        it. Returns None when the action cannot be resolved."""
        ...


class ActionSuppressionPort(Protocol):
    """Outbound port for explicit per-(party, action_type, mart) suppression.

    Separate from ActionStatePort (not fattened onto it) — access pattern differs:
    the Suggestion Settings panel writes/reads suppression directly, with no
    active action_id required, unlike the quick-dismiss card flow above.
    """

    def suppress(self, party_id: str, action_type: str, source_mart: str,
                 until_utc: str, user_id: Optional[str] = None) -> None:
        """Turn an opportunity type off for a party until `until_utc` (bound param)."""
        ...

    def unsuppress(self, party_id: str, action_type: str, source_mart: str) -> None:
        """Turn a suggestion back on for a party."""
        ...

    def list_dismissals_for_party(self, party_id: str) -> list[ActionDismissal]:
        """Return all suppression rows for one party, including expired ones."""
        ...
