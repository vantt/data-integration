"""Pure worklist filter logic — parse, apply, and count, no HTTP/DB imports.

Kept out of the web adapter so the adapter stays thin and this stays
unit-testable in isolation.
"""
from __future__ import annotations

from typing import Mapping

from .worklist_ranking import urgency_score

# Fine Japan 8 core SKUs — (url_key, display_label).
# Matching uses keyword logic in _matches_core_product().
CORE_PRODUCTS: list[tuple[str, str]] = [
    ("cordyceps_vien",    "Cordyceps Viên"),
    ("cordyceps_plus",    "Cordyceps Plus"),
    ("fucoidan",          "Fucoidan"),
    ("collagen_plus",     "Collagen Plus"),
    ("collagen_swallow",  "Collagen Swallow's Nest"),
    ("shark_cartilage",   "Shark Cartilage"),
    ("natto",             "Natto Kinase"),
    ("metabo",            "Metabo"),
]


def _matches_core_product(product_str: str, key: str) -> bool:
    """Return True if product_str belongs to the given core product key."""
    s = (product_str or "").lower()
    if key == "cordyceps_vien":
        return "cordyceps" in s and "plus" not in s
    if key == "cordyceps_plus":
        return "cordyceps plus" in s
    if key == "fucoidan":
        return "fucoidan" in s
    if key == "collagen_plus":
        return "collagen plus" in s
    if key == "collagen_swallow":
        return "swallow" in s
    if key == "shark_cartilage":
        return "shark" in s
    if key == "natto":
        return "natto" in s
    if key == "metabo":
        return "metabo" in s
    return False


def parse_filters(query_params: Mapping) -> dict:
    """Normalize raw query params into a canonical filter dict.

    Accepts any string→string mapping (e.g. Starlette QueryParams).
    """
    raw_types = query_params.get("type", "")
    types_list = [t.strip() for t in raw_types.split(",") if t.strip()] if raw_types else []
    raw_min = query_params.get("min_value", "")
    try:
        min_value = int(raw_min) if raw_min else 0
    except ValueError:
        min_value = 0
    product = query_params.get("product", "").strip()
    valid_keys = {k for k, _ in CORE_PRODUCTS}
    return {
        "assignee": query_params.get("assignee", "me"),
        "priority": query_params.get("priority", "all"),
        "types": types_list,        # action_type strings to include (empty = all)
        "q": query_params.get("q", "").strip(),
        "min_value": min_value,
        "product": product if product in valid_keys else "",
        "hide_contacted": query_params.get("hide_contacted", "") == "1",
    }


def available_action_types(actions: list) -> list[str]:
    """Distinct action_type values present, sorted — drives the filter chips.

    Derived from UNFILTERED data so new mart action types appear automatically.
    """
    return sorted(
        {getattr(a, "action_type", "") for a in actions if getattr(a, "action_type", "")}
    )


def active_filter_count(filters: dict) -> int:
    """Count non-default active filters for the badge.

    assignee is excluded: it is not applied yet (no auth/user context) and its
    toggle is not rendered, so counting it would inflate the badge.
    """
    count = 0
    if filters["priority"] != "all":
        count += 1
    if filters["types"]:
        count += 1
    if filters["q"]:
        count += 1
    if filters["min_value"] > 0:
        count += 1
    if filters.get("product"):
        count += 1
    if filters.get("hide_contacted"):
        count += 1
    return count


def apply_filters(actions: list, tasks: list, filters: dict) -> tuple[list, list]:
    """Return (actions, tasks) narrowed by priority/type/search/min_value.

    Priority uses normalized urgency (high = urgency>=8, urgent = urgency>=9) so
    the two opposite raw scales compare correctly — CALL_NOW (rank=1 → urgency=9)
    lands in "urgent" instead of being wrongly excluded by a raw >=2 test.
    """
    fp = filters["priority"]
    if fp == "urgent":
        actions = [a for a in actions
                   if urgency_score("action", getattr(a, "priority", 9) or 9) >= 9]
        tasks = [t for t in tasks
                 if urgency_score("task", getattr(t, "priority", 0) or 0) >= 9]
    elif fp == "high":
        actions = [a for a in actions
                   if urgency_score("action", getattr(a, "priority", 9) or 9) >= 8]
        tasks = [t for t in tasks
                 if urgency_score("task", getattr(t, "priority", 0) or 0) >= 8]

    # Type filter: restrict to selected action_types (tasks always pass through).
    if filters["types"]:
        allowed = set(filters["types"])
        actions = [a for a in actions if getattr(a, "action_type", "") in allowed]

    # Text search: customer_name, rationale, or product affinity (actions) / title or desc (tasks).
    q = filters["q"].lower()
    if q:
        actions = [
            a for a in actions
            if q in (getattr(a, "customer_name", "") or "").lower()
            or q in (getattr(a, "rationale_vi", "") or "").lower()
            or q in (getattr(a, "top_affinity_product", "") or "").lower()
            or q in (getattr(a, "last_purchased_product", "") or "").lower()
        ]
        tasks = [
            t for t in tasks
            if q in (getattr(t, "title", "") or "").lower()
            or q in (getattr(t, "description", "") or "").lower()
        ]

    # Product filter: match top_affinity_product or last_purchased_product (actions only).
    product_key = filters.get("product", "")
    if product_key:
        actions = [
            a for a in actions
            if _matches_core_product(getattr(a, "top_affinity_product", "") or "", product_key)
            or _matches_core_product(getattr(a, "last_purchased_product", "") or "", product_key)
        ]

    # Minimum value filter (actions only; tasks have no monetary value).
    if filters["min_value"] > 0:
        mv = filters["min_value"]
        actions = [a for a in actions
                   if int(getattr(a, "value_at_stake_vnd", 0) or 0) >= mv]

    return actions, tasks
