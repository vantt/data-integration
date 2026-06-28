"""action_state_port.py — domain port (Protocol) for action state writes."""
from __future__ import annotations

from typing import Optional, Protocol


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
