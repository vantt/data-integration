from __future__ import annotations

from typing import Protocol

from domain.entities.app_user import AppUser


class AppUserRepository(Protocol):
    """Outbound port for persisting and querying CRM app users."""

    def get_by_email(self, email: str) -> AppUser | None:
        """Return a user by email address, or None if not found."""
        ...

    def list_active(self) -> list[AppUser]:
        """Return all active app users."""
        ...
