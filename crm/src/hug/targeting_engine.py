"""targeting_engine.py — Python port of the edge Worker's matchesTargeting().

This module is the AUTHORITATIVE Python mirror of the Cloudflare Worker logic in
webhook_receiver/cloudflareD1/src/hug-handler.ts  (matchesTargeting, lines 148–189).
Any semantic change to the Worker MUST be reflected here, and vice-versa.

Exported surface (consumed by Phase 4 validation and Phase 5 preview/overlap):
  matches_targeting(targeting, ctx)           → bool
  preview_match_customers(targeting, db_path) → dict

Design decisions mapped to TS source lines:
  TS  153–155  malformed JSON string → match-all
               Python: pre-parsed dict arrives here; wrap entire eval in
               try/except → return True on any unexpected error.
  TS  158–159  empty dict → True (DEFAULT campaign).
  TS  165–172  Array rule → ctxValue None → False;
               any(String(v) == String(ctxValue)) — string-coerced OR.
               Python: str(v) == str(ctx_value) on both sides.
  TS  173–180  Object rule → ctxValue not a number → numCtx=None → False;
               check gte/gt/lte/lt bounds.
               Python: isinstance(ctx_value, (int, float)) and not bool.
  TS  182–186  Scalar rule → ctxValue None → False;
               String(rule) != String(ctxValue) → False.

Module is PURE: no DB, no HTTP.  preview_match_customers is the only I/O path
(SQLite read-only) and is kept in this file per spec.

Preview limitation: wh_customer_tier holds customer-level attrs only
(tier, recency_days, value_group, is_contactable). Touchpoint-level attrs
(op_type, channel — marked touchpoint_level=True in TARGETING_CATALOG) are
per-scan and cannot be evaluated in a customer count preview. The preview
treats these attrs as "no constraint" (missing from the customer context dict),
which means the returned count is an UPPER BOUND when such attrs are present.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Any

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core predicate — pure, no I/O
# ---------------------------------------------------------------------------

def matches_targeting(targeting: dict, ctx: dict) -> bool:
    """Evaluate whether targeting matches the given context.

    Exact Python port of TS matchesTargeting (hug-handler.ts lines 148–189).

    Rules:
      {}          → True  (DEFAULT; always matches)
      list rule   → OR membership with str() coercion; None ctx → False
      range rule  → numeric bounds (gte/gt/lte/lt); non-numeric ctx → False
      scalar rule → str() equality; None ctx → False
      AND across all keys (every key must pass)
      Malformed/throwing → True  (graceful degradation, same as edge)
    """
    try:
        # Empty targeting = DEFAULT campaign, always matches.
        if not targeting:
            return True

        for key, rule in targeting.items():
            ctx_value = ctx.get(key)  # missing key → None (no constraint = pass through)

            if isinstance(rule, list):
                # TS lines 165–172: OR membership with String() coercion.
                # A constrained key whose ctx value is None → no match.
                if ctx_value is None:
                    return False
                matched = any(str(v) == str(ctx_value) for v in rule)
                if not matched:
                    return False

            elif isinstance(rule, dict):
                # TS lines 173–180: numeric range.  ctx_value must already be
                # a real number (int or float but NOT bool, which TS typeof
                # would yield 'boolean' not 'number').
                if isinstance(ctx_value, bool) or not isinstance(ctx_value, (int, float)):
                    return False
                num = ctx_value
                if "gte" in rule and not (num >= rule["gte"]):
                    return False
                if "lte" in rule and not (num <= rule["lte"]):
                    return False
                if "gt"  in rule and not (num >  rule["gt"]):
                    return False
                if "lt"  in rule and not (num <  rule["lt"]):
                    return False

            else:
                # TS lines 182–186: scalar equality with String() coercion.
                if ctx_value is None:
                    return False
                if str(rule) != str(ctx_value):
                    return False

        return True

    except Exception:  # noqa: BLE001
        # Mirror edge graceful degradation: malformed targeting → match-all.
        log.warning("matches_targeting: unexpected error evaluating targeting, defaulting to True", exc_info=True)
        return True


# ---------------------------------------------------------------------------
# Preview — customer-level count only (I/O via SQLite read-only)
# ---------------------------------------------------------------------------

def preview_match_customers(targeting: dict, cache_db_path: str) -> dict[str, Any]:
    """Count how many customers in wh_customer_tier match targeting.

    Opens cache.db READ-ONLY.  Maps wh_customer_tier columns to the edge
    context dict: strategic_tier → tier (same rename as customer_push.py).

    Touchpoint-level attrs (op_type, channel) are absent from customer rows and
    are treated as "missing key = no constraint" — the count is an UPPER BOUND
    when those attrs appear in targeting.

    Returns:
        {"matched": int, "total": int, "sample": list[dict]}
        or {"error": str, "matched": 0, "total": 0, "sample": []}  on failure.

    Never raises.
    """
    try:
        conn = sqlite3.connect(f"file:{cache_db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
    except Exception as exc:
        log.warning("preview_match_customers: cannot open cache.db (%s)", exc)
        return {"error": f"cache.db unavailable: {exc}", "matched": 0, "total": 0, "sample": []}

    try:
        cur = conn.execute(
            """
            SELECT customer_id,
                   strategic_tier,
                   recency_days,
                   value_group,
                   is_contactable
            FROM   wh_customer_tier
            WHERE  customer_id IS NOT NULL
            """
        )
        rows = cur.fetchall()
    except Exception as exc:
        log.warning("preview_match_customers: query failed (%s)", exc)
        return {"error": f"query failed: {exc}", "matched": 0, "total": 0, "sample": []}
    finally:
        conn.close()

    total = len(rows)
    matched = 0
    sample: list[dict] = []

    for row in rows:
        ctx: dict[str, Any] = {
            # Map warehouse column → edge context field name.
            "tier":           row["strategic_tier"],
            "recency_days":   row["recency_days"],
            "value_group":    row["value_group"],
            # is_contactable is INTEGER 0|1 in SQLite; keep as int for numeric
            # range rules (unlikely but consistent) and str() coercion in list rules.
            "is_contactable": row["is_contactable"],
        }
        if matches_targeting(targeting, ctx):
            matched += 1
            if len(sample) < 5:
                sample.append({
                    "customer_id":  row["customer_id"],
                    "tier":         row["strategic_tier"],
                    "recency_days": row["recency_days"],
                    "value_group":  row["value_group"],
                    "is_contactable": row["is_contactable"],
                })

    return {"matched": matched, "total": total, "sample": sample}
