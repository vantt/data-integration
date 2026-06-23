"""hug.claim_fields — config-driven claim form field definitions + validator registry.

CLAIM_FIELDS drives the claim station form: which fields to show, how to validate
them, which go into D1 (edge=True), and which URL param pre-fills each field.

Adding a new bind field = append ONE dict to CLAIM_FIELDS.  If the field needs
validation, add ONE callable to VALIDATORS keyed by the new "validate" value.
No schema change, no router change, no frontend change (Phase 3 renders from
JSON-serialised CLAIM_FIELDS automatically).

Fields promoted to dedicated SQLite columns (order_code, is_gift) are listed in
_PROMOTED_COLS in screen_hug_claim.py so the AJAX bind endpoint can split them
from bind_attributes correctly.

Validator contract:
  callable(value: str, session_id: str | None) -> dict
    {"ok": True,  "message": str}   — valid (green)
    {"ok": False, "message": str}   — invalid (red)  — use sparingly; prefer amber
    {"ok": None,  "message": str}   — unknown/soft-fail (amber) — allow proceed
"""
from __future__ import annotations

from hug import sapo_order_proxy

# ── Field registry ────────────────────────────────────────────────────────────

CLAIM_FIELDS: list[dict] = [
    {
        "key":      "order_code",
        "label":    "Mã đơn hàng",
        "type":     "text",
        "input":    "type",       # staff types or scanner pre-fills from ?order=
        "required": True,
        "validate": "sapo_order", # dispatches to VALIDATORS["sapo_order"]
        "prefill":  "order",      # URL query-param name that pre-populates this field
        "edge":     True,         # include in D1 attributes payload (Phase 4)
    },
    {
        "key":      "is_gift",
        "label":    "Quà tặng",
        "type":     "bool",
        "input":    "type",
        "required": False,
        "validate": None,         # boolean toggle — no external check needed
        "prefill":  None,
        "edge":     False,
    },
]

# Build a lookup dict by key for O(1) access in endpoints.
_FIELDS_BY_KEY: dict[str, dict] = {f["key"]: f for f in CLAIM_FIELDS}


def get_field(key: str) -> dict | None:
    """Return field definition by key, or None if not found."""
    return _FIELDS_BY_KEY.get(key)


def claim_fields_json() -> list[dict]:
    """Return CLAIM_FIELDS serialisable subset for the frontend (Phase 3).

    Strips the 'validate' key (backend-only) to keep the payload minimal.
    The frontend only needs: key, label, type, input, required, prefill, edge.
    """
    keep = {"key", "label", "type", "input", "required", "prefill", "edge"}
    return [{k: v for k, v in f.items() if k in keep} for f in CLAIM_FIELDS]


# ── Validators ────────────────────────────────────────────────────────────────

def _validate_sapo_order(value: str, session_id: str | None) -> dict:  # noqa: ARG001
    """Validate an order code via the hybrid cache-first strategy.

    Delegates to sapo_order_proxy which owns all the HTTP / cache logic.
    session_id is not used in order validation but accepted for interface symmetry
    (future validators that check session context can use it).
    """
    return sapo_order_proxy.check_order_exists(value)


# Registry maps validate-key → callable.
# None-validate fields are short-circuited in the endpoint (never reach here).
VALIDATORS: dict[str, callable] = {
    "sapo_order": _validate_sapo_order,
}
