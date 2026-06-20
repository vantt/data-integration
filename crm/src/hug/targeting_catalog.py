"""targeting_catalog.py — v1 attribute catalog for Hug campaign targeting.

Defines TARGETING_CATALOG (the fixed set of supported attributes for the
rule-builder and validator) and validate_targeting() which is called on every
campaign save to catch errors before they reach the edge Worker.

Catalog design principles:
  - list attrs  : context value must equal one of the listed values (OR within
                  the list, AND across attrs — mirrors edge matchesTargeting).
  - range attr  : context value is numeric; rule is { gte/gt/lte/lt: N }.
  - touchpoint_level=True : the attr is per-scan (from hug_token), not per-
                  customer; preview_match_customers() can NOT count it
                  (documented in targeting_engine.py).

Only the 6 IMPLEMENTED v1 attrs are listed here.  Deferred attrs (order_value,
scan_index, geo) belong to Phase 7 and must NOT be added here until the Worker
and schema support them.
"""
from __future__ import annotations

from hug.op_types import OP_TYPES

# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

TARGETING_CATALOG: dict[str, dict] = {
    "op_type": {
        "type": "list",
        "description": "Loại thao tác (điểm chạm)",
        # Keys from OP_TYPES are the canonical op_type values.
        "values": list(OP_TYPES.keys()),
        # Per-scan attr: cannot be counted in customer-level preview.
        "touchpoint_level": True,
    },
    "channel": {
        "type": "list",
        "description": "Kênh bán hàng",
        "values": ["shopee", "tiki", "lazada", "website", "pos", "other"],
        "touchpoint_level": True,
    },
    "tier": {
        "type": "list",
        "description": "Phân khúc khách hàng",
        "values": [
            "VIP", "CORE", "CASUAL", "NEW", "SECOND_ORDER",
            "DORMANT_VALUABLE", "LAPSED_VALUABLE", "MASKED_REPEAT", "UNKNOWN",
        ],
    },
    "value_group": {
        "type": "list",
        "description": "Nhóm giá trị đơn",
        "values": ["HIGH", "MID", "LOW", "UNKNOWN"],
    },
    "is_contactable": {
        "type": "list",
        "description": "Có thể liên hệ (0 = không, 1 = có)",
        # Stored as INTEGER 0|1 in SQLite; edge uses String() coercion so both
        # 0/1 int literals and "0"/"1" strings are valid rule values.
        "values": [0, 1],
    },
    "recency_days": {
        "type": "range",
        "description": "Số ngày kể từ đơn cuối",
        # Allowed operators mirror the edge: gte / gt / lte / lt.
        "operators": ["gte", "gt", "lte", "lt"],
    },
}

_RANGE_OPS = frozenset(["gte", "gt", "lte", "lt"])


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

def validate_targeting(targeting: dict) -> list[str]:
    """Return a list of human-readable error strings (empty list = valid).

    Checks performed (mirrors constraints the edge Worker enforces implicitly):
      1. All top-level keys must be in TARGETING_CATALOG.
      2. list-type attrs: rule must be a non-empty list; each value must be in
         the declared domain (where a domain is defined).
      3. range-type attrs: rule must be a dict with at least one of the four
         operators (gte/gt/lte/lt); each operator's value must be numeric.
      4. No other rule shapes are accepted (prevents accidental scalar rules that
         the edge handles but the UI should not produce).

    Raises nothing — all errors are collected and returned.
    """
    if not isinstance(targeting, dict):
        return ["targeting must be a JSON object"]

    errors: list[str] = []

    for key, rule in targeting.items():
        if key not in TARGETING_CATALOG:
            errors.append(f"unknown attribute '{key}'")
            continue

        spec = TARGETING_CATALOG[key]

        if spec["type"] == "list":
            if not isinstance(rule, list):
                errors.append(
                    f"'{key}': expected a list, got {type(rule).__name__}"
                )
                continue
            if len(rule) == 0:
                errors.append(f"'{key}': list must not be empty")
                continue
            domain = spec.get("values")
            if domain is not None:
                # Compare as strings to match edge String() coercion.
                domain_strs = {str(v) for v in domain}
                for v in rule:
                    if str(v) not in domain_strs:
                        errors.append(
                            f"'{key}': value {v!r} not in allowed domain {domain}"
                        )

        elif spec["type"] == "range":
            if not isinstance(rule, dict):
                errors.append(
                    f"'{key}': expected a range object {{gte/gt/lte/lt: N}}, "
                    f"got {type(rule).__name__}"
                )
                continue
            valid_ops = {k: v for k, v in rule.items() if k in _RANGE_OPS}
            unknown_ops = [k for k in rule if k not in _RANGE_OPS]
            if unknown_ops:
                errors.append(
                    f"'{key}': unknown range operator(s) {unknown_ops}; "
                    f"allowed: {sorted(_RANGE_OPS)}"
                )
            if not valid_ops:
                errors.append(
                    f"'{key}': range object must have at least one of "
                    f"gte, gt, lte, lt"
                )
                continue
            for op, val in valid_ops.items():
                if not isinstance(val, (int, float)):
                    errors.append(
                        f"'{key}.{op}': value must be numeric, got {type(val).__name__}"
                    )

    return errors
