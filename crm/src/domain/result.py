"""result.py — lightweight Result types for explicit error signaling.

Avoids exception-driven control flow for validation failures.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CustomFieldError:
    """Validation error for a single custom field (key + human message)."""
    field_key: str
    message: str

    def __str__(self) -> str:
        return f"custom field {self.field_key!r}: {self.message}"


@dataclass
class ValidationResult:
    """Returned by service methods that validate structured input.

    Check `result.ok` before using; inspect `result.errors` on failure.
    """
    errors: list[CustomFieldError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors
