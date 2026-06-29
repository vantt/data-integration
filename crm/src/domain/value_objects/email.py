"""Email value object — encapsulates email normalization."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Email:
    """Immutable normalized email address.

    Construct via Email.normalize(raw) rather than the constructor directly.
    """
    value: str

    @classmethod
    def normalize(cls, raw: str) -> str:
        """Lower-case and strip whitespace from an email address."""
        return raw.strip().lower()
