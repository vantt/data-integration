"""campaign_overlap.py — overlap detection between Hug campaign targetings.

Pure module: no DB reads, no HTTP. Used by the campaign admin UI to warn the
operator when two active campaigns can simultaneously match the same scan context.

Algorithm (v1 — exact pairwise attribute intersection, AND semantics):

  Two targetings OVERLAP if there exists at least one context dict that would
  satisfy BOTH targetings simultaneously.

  For each attribute key:
    - If the key is absent in BOTH targetings: unconstrained on both sides →
      the attr does not block overlap.
    - If the key is absent in ONE targeting: that side is unconstrained
      (matches any value) → the attr does not block overlap.
    - If the key is present in BOTH targetings: check whether a value can
      simultaneously satisfy both rules:
        * list attr : set intersection non-empty
        * range attr: interval intersection non-empty
              [max(a_low, b_low), min(a_high, b_high)] exists iff max_low ≤ min_high
              missing bound on one side = ±∞.

  Overall: overlap iff ALL present-on-both-sides attrs pass (AND).

The rule above is conservative: a joint constraint we cannot compute (e.g. a
future scalar rule produced by something other than the UI) is treated as
overlapping to avoid false negatives. The try/except block at the bottom of
targeting_can_overlap() catches this case.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Attribute-level overlap primitives
# ---------------------------------------------------------------------------

def _list_overlaps(a_vals: list, b_vals: list) -> bool:
    """Return True if the two lists share at least one string-coerced value."""
    a_set = {str(v) for v in a_vals}
    b_set = {str(v) for v in b_vals}
    return bool(a_set & b_set)


def _range_overlaps(a_rule: dict, b_rule: dict) -> bool:
    """Return True if two numeric range rules have a non-empty intersection.

    Each rule may contain any combination of gte/gt/lte/lt.  Missing bound =
    ±∞. Strict vs. inclusive boundary difference is collapsed to an effective
    inclusive bound for the intersection check:
      - gt N  → effective low  = N (exclusive, so we use strict >)
      - gte N → effective low  = N (inclusive)
      - lt N  → effective high = N (exclusive)
      - lte N → effective high = N (inclusive)

    The overlap check is: max_low < min_high  (strict > for exclusive ends)
    OR  max_low == min_high AND both ends are inclusive.

    For simplicity (and because the UI only produces gte/lte), we treat
    gt/lt as open on the boundary: overlap if max_low < min_high strictly,
    or if max_low == min_high and BOTH endpoints at that boundary are
    inclusive (gte on the low side AND lte on the high side, respectively).
    """
    # Extract effective low/high from each rule.
    # Returns (value, inclusive).
    def _low(rule: dict) -> tuple[float, bool]:
        if "gte" in rule:
            return rule["gte"], True
        if "gt" in rule:
            return rule["gt"], False
        return float("-inf"), True

    def _high(rule: dict) -> tuple[float, bool]:
        if "lte" in rule:
            return rule["lte"], True
        if "lt" in rule:
            return rule["lt"], False
        return float("inf"), True

    a_low, a_low_inc  = _low(a_rule)
    a_high, a_high_inc = _high(a_rule)
    b_low, b_low_inc  = _low(b_rule)
    b_high, b_high_inc = _high(b_rule)

    # Combined interval.
    max_low = max(a_low, b_low)
    min_high = min(a_high, b_high)
    max_low_inc = a_low_inc if a_low > b_low else (b_low_inc if b_low > a_low else (a_low_inc and b_low_inc))
    min_high_inc = a_high_inc if a_high < b_high else (b_high_inc if b_high < a_high else (a_high_inc and b_high_inc))

    if max_low < min_high:
        return True
    if max_low == min_high:
        return max_low_inc and min_high_inc
    return False


# ---------------------------------------------------------------------------
# Pairwise targeting overlap check
# ---------------------------------------------------------------------------

def targeting_can_overlap(t_a: dict, t_b: dict) -> bool:
    """Return True if targetings t_a and t_b can BOTH match some context.

    Unconstrained (absent) attribute on either side = universe → never blocks.
    All attributes present in BOTH sides must simultaneously be satisfiable.
    On unexpected rule shapes (not list, not dict) → conservative True.
    """
    try:
        # Collect keys that appear in BOTH targetings — only these can block overlap.
        shared_keys = set(t_a) & set(t_b)
        for key in shared_keys:
            rule_a = t_a[key]
            rule_b = t_b[key]

            if isinstance(rule_a, list) and isinstance(rule_b, list):
                if not _list_overlaps(rule_a, rule_b):
                    return False

            elif isinstance(rule_a, dict) and isinstance(rule_b, dict):
                if not _range_overlaps(rule_a, rule_b):
                    return False

            else:
                # Mixed shapes or scalar rules: conservative → assume overlap.
                # (The UI never produces scalars, but we mustn't false-negative.)
                pass

        return True  # All shared attrs have non-empty intersection.

    except Exception:  # noqa: BLE001
        # If evaluation explodes for any reason, assume overlap (safe default).
        log.warning("targeting_can_overlap: error during evaluation, assuming overlap", exc_info=True)
        return True


# ---------------------------------------------------------------------------
# Campaign-level overlap finder (reads crm.db connection)
# ---------------------------------------------------------------------------

def find_overlapping_campaigns(
    conn: sqlite3.Connection,
    new_targeting: dict,
    exclude_id: str | None = None,
) -> list[dict[str, Any]]:
    """Find active campaigns whose targeting can overlap with new_targeting.

    Returns list of {campaign_id, name, priority}. Shadow direction (which
    campaign wins on first-match-by-priority) is computed in the render layer
    where the new campaign's priority is also known.

    exclude_id: skip this campaign_id (the one being edited — avoid self-overlap).
    """
    from hug.campaign_repository import list_campaigns  # avoid circular at module level

    active_rows = list_campaigns(conn, status="active")
    overlaps: list[dict[str, Any]] = []

    for row in active_rows:
        cid = row["campaign_id"]
        if exclude_id and cid == exclude_id:
            continue

        try:
            other_targeting: dict = json.loads(row["targeting"] or "{}")
        except (json.JSONDecodeError, TypeError):
            other_targeting = {}

        if targeting_can_overlap(new_targeting, other_targeting):
            overlaps.append({
                "campaign_id": cid,
                "name": row["name"],
                "priority": row["priority"],
            })

    return overlaps
