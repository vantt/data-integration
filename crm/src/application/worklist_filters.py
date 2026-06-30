"""Pure worklist filter logic — parse, apply, and count, no HTTP/DB imports.

Kept out of the web adapter so the adapter stays thin and this stays
unit-testable in isolation.
"""
from __future__ import annotations

from typing import Mapping

from application.worklist_ranking import urgency_score
from domain.entities.cache_insight import ActionQueueItem
from domain.entities.task import Task
from domain.product_catalog import CORE_PRODUCTS, CORE_PRODUCT_KEYS, matches_core_product


def parse_filters(query_params: Mapping) -> dict:
    """Normalize raw query params into a canonical filter dict.

    Accepts any string→string mapping (e.g. Starlette QueryParams).
    Uses last-value-wins for params that support hx-vals override: when the
    client sends duplicate keys (hidden form field + hx-vals override), the
    last value in the query string takes precedence.
    """
    def _last(key: str, default: str = "") -> str:
        """Return last value for key — supports HTMX hx-vals override pattern."""
        if hasattr(query_params, "getlist"):
            vals = [v for v in query_params.getlist(key) if v is not None]
            return vals[-1] if vals else default
        return query_params.get(key, default)

    raw_types = _last("type", "")
    types_list = [t.strip() for t in raw_types.split(",") if t.strip()] if raw_types else []
    raw_min = _last("min_value", "")
    try:
        min_value = int(raw_min) if raw_min else 0
    except ValueError:
        min_value = 0
    product = _last("product", "").strip()
    valid_keys = CORE_PRODUCT_KEYS
    strategic_tier = _last("strategic_tier", "").strip()
    value_group = _last("value_group", "").strip()

    # adv controls row-2 visibility. "1" = open, "0" = explicit close, "" = auto.
    # Auto-open when any secondary filter is active (e.g. bookmark reload).
    adv_raw = _last("adv", "")
    sec_active = bool(
        types_list
        or (product if product in valid_keys else "")
        or strategic_tier
        or value_group
    )
    if adv_raw == "1":
        adv = "1"
    elif adv_raw == "0":
        adv = ""  # explicit close wins even when secondary filters are active
    else:
        adv = "1" if sec_active else ""

    return {
        "assignee": _last("assignee", "me"),
        "priority": _last("priority", "all"),
        "types": types_list,        # action_type strings to include (empty = all)
        "q": _last("q", "").strip(),
        "min_value": min_value,
        "product": product if product in valid_keys else "",
        "hide_contacted": _last("hide_contacted", "") == "1",
        "has_script": _last("has_script", "") == "1",
        "strategic_tier": strategic_tier,
        "value_group": value_group,
        "adv": adv,                 # row-2 open state: "1" = open, "" = closed
    }


def available_action_types(actions: list[ActionQueueItem]) -> list[str]:
    """Distinct action_type values present, sorted — drives the filter chips.

    Derived from UNFILTERED data so new mart action types appear automatically.
    """
    return sorted(
        {a.action_type for a in actions if a.action_type}
    )


def available_strategic_tiers(actions: list[ActionQueueItem]) -> list[str]:
    """Distinct strategic_tier values present in unfiltered data, sorted."""
    return sorted({a.strategic_tier for a in actions if a.strategic_tier})


def available_value_groups(actions: list[ActionQueueItem]) -> list[str]:
    """Distinct value_group values present in unfiltered data, in RFM order."""
    order = {v: i for i, v in enumerate(["VIP", "GOLD", "SILVER", "BRONZE"])}
    present = {a.value_group for a in actions if a.value_group}
    return sorted(present, key=lambda v: order.get(v, 99))


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
    if filters.get("has_script"):
        count += 1
    if filters.get("strategic_tier"):
        count += 1
    if filters.get("value_group"):
        count += 1
    return count


def apply_filters(
    actions: list[ActionQueueItem],
    tasks: list[Task],
    filters: dict,
    script_cids: set[int] | None = None,
) -> tuple[list[ActionQueueItem], list[Task]]:
    """Return (actions, tasks) narrowed by priority/type/search/min_value/has_script.

    Priority uses normalized urgency (high = urgency>=8, urgent = urgency>=9) so
    the two opposite raw scales compare correctly — CALL_NOW (rank=1 → urgency=9)
    lands in "urgent" instead of being wrongly excluded by a raw >=2 test.

    script_cids: set of customer_ids that have an approach script (passed in from
    the caller — kept pure, no DB/file access here). When None and has_script is
    active, actions are conservatively kept (safe degraded mode).
    Tasks are NOT filtered by has_script in v1 (manual tasks, no customer_id).
    """
    fp = filters["priority"]
    if fp == "urgent":
        actions = [a for a in actions
                   if urgency_score("action", a.priority or 9) >= 9]
        tasks = [t for t in tasks
                 if urgency_score("task", t.priority) >= 9]
    elif fp == "high":
        actions = [a for a in actions
                   if urgency_score("action", a.priority or 9) >= 8]
        tasks = [t for t in tasks
                 if urgency_score("task", t.priority) >= 8]

    # Type filter: restrict to selected action_types (tasks always pass through).
    if filters["types"]:
        allowed = set(filters["types"])
        actions = [a for a in actions if a.action_type in allowed]

    # Text search: customer_name, rationale, or product affinity (actions) / title or desc (tasks).
    q = filters["q"].lower()
    if q:
        actions = [
            a for a in actions
            if q in a.customer_name.lower()
            or q in a.rationale_vi.lower()
            or q in a.top_affinity_product.lower()
            or q in a.last_purchased_product.lower()
        ]
        tasks = [
            t for t in tasks
            if q in t.title.lower()
            or q in (t.description or "").lower()
        ]

    # Product filter: match top_affinity_product or last_purchased_product (actions only).
    product_key = filters.get("product", "")
    if product_key:
        actions = [
            a for a in actions
            if matches_core_product(a.top_affinity_product, product_key)
            or matches_core_product(a.last_purchased_product, product_key)
        ]

    # Minimum value filter (actions only; tasks have no monetary value).
    if filters["min_value"] > 0:
        mv = filters["min_value"]
        actions = [a for a in actions
                   if int(a.value_at_stake_vnd or 0) >= mv]

    # has_script filter: keep only actions whose customer_id is in the script set.
    # Tasks are not filtered (manual tasks lack customer_id; v1 scope).
    if filters.get("has_script") and script_cids is not None:
        actions = [a for a in actions
                   if a.customer_id in script_cids]

    tier = filters.get("strategic_tier", "")
    if tier:
        actions = [a for a in actions if a.strategic_tier == tier]

    vg = filters.get("value_group", "")
    if vg:
        actions = [a for a in actions if a.value_group == vg]

    return actions, tasks
