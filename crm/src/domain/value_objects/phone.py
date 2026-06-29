"""PhoneNumber value object — encapsulates Vietnamese phone normalization."""
from __future__ import annotations

import re
from dataclasses import dataclass

_NON_DIGIT_NON_PLUS = re.compile(r"[^\d+]")


@dataclass(frozen=True)
class PhoneNumber:
    """Immutable normalized phone number (local VN format: 09...).

    Construct via PhoneNumber.normalize(raw) rather than the constructor directly.
    """
    value: str

    @classmethod
    def normalize(cls, raw: str) -> str:
        """Convert Vietnamese phone to local VN format (09...).

        Rules (mirrors normalize.go):
          - Strip everything except digits and '+'.
          - "+84..." → '0' + rest.
          - "84..."  (≥11 digits total) → '0' + digits[2:].
          - "0..."   → keep as-is.
          - No digit remaining → return "".
          - Other formats → return stripped digits only.
        """
        s = _NON_DIGIT_NON_PLUS.sub("", raw)
        if not s:
            return ""
        if not any(c.isdigit() for c in s):
            return ""
        if s.startswith("+84"):
            return "0" + s[3:]
        if s.startswith("84") and len(s) >= 11:
            return "0" + s[2:]
        if s.startswith("0"):
            return s
        return s

    @classmethod
    def to_e164(cls, local: str) -> str:
        """Convert local VN format (09...) to E.164 (+84...) for external export.

        Rules:
          - "0..."    → "+84" + rest.
          - "+84..."  → keep as-is.
          - Otherwise → return as-is.
        """
        if local.startswith("0"):
            return "+84" + local[1:]
        if local.startswith("+84"):
            return local
        return local
