"""approach_script.py — ApproachScript domain entity.

Holds the full AI-generated JSON approach script for a customer plus a few
derived fields needed for call-mode gate logic (recommended, confidence).
The `data` field keeps the entire parsed dict so callers can access any nested
field without schema coupling — safe when the template schema is still evolving.
"""
from __future__ import annotations

import dataclasses
import logging
from typing import Any

log = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class ApproachScript:
    customer_id: int
    data: dict[str, Any]          # full parsed JSON; never mutated
    recommended: bool              # rút từ data["approach"]["recommended"]
    confidence: str | None         # data.get("confidence")
    refreshed_at: str              # ISO-8601 UTC ("...Z") = file mtime
    model: str | None              # optional LLM meta
    template_version: str | None   # optional schema version

    # ── factory ───────────────────────────────────────────────────────────────

    @classmethod
    def from_json(
        cls,
        customer_id: int,
        data: dict[str, Any],
        refreshed_at: str,
        *,
        model: str | None = None,
        template_version: str | None = None,
    ) -> "ApproachScript":
        """Build entity from parsed JSON dict, safely extracting derived fields."""
        # Rút recommended từ data["approach"]["recommended"]; default True nếu thiếu.
        try:
            recommended = bool(data["approach"]["recommended"])
        except (KeyError, TypeError):
            log.debug("approach_script.from_json: missing approach.recommended for cid=%s, defaulting True", customer_id)
            recommended = True

        # Rút confidence (top-level, optional).
        try:
            confidence = data.get("confidence") or None
        except (AttributeError, TypeError):
            confidence = None

        return cls(
            customer_id=customer_id,
            data=data,
            recommended=recommended,
            confidence=confidence,
            refreshed_at=refreshed_at,
            model=model,
            template_version=template_version,
        )
