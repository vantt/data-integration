# Phase 3 — Targeting Predicate Engine (Python port of matchesTargeting)

## Context Links
- Edge source of truth: `webhook_receiver/cloudflareD1/src/hug-handler.ts` — `matchesTargeting()` lines 148–189, `ScanContext` lines 79–90
- Design spec: `discussion-hug.md §7` — AND-between-keys, OR-within-list, range object
- Implemented attributes (v1 scope, from scout): `op_type, tier, channel, value_group, is_contactable` (list/scalar) + `recency_days` (gte/lte/gt/lt range)
- Deferred attributes: `order_value, scan_index, geo` (need Worker + schema changes, Phase 7)
- Customer data available for preview: `cache.db wh_customer_tier` columns: `customer_id, strategic_tier, recency_days, value_group, is_contactable`

## Overview
- **Priority:** P1 (shared by Phases 4 and 5)
- **Status:** pending (independent — can start in parallel with Phase 2)
- **Goal:** Python module that (a) validates targeting JSON against the v1 catalog, (b) evaluates targeting against a context dict (port of TS `matchesTargeting`), (c) exposes the attribute catalog for UI dropdown generation.

## Key Insights
- The TS `matchesTargeting` logic is ~40 lines; the Python port is similarly compact. Do NOT invent new semantics — match the edge exactly.
- Three rule forms in the edge: Array (OR), Range object (gte/lte/gt/lt), Scalar equality. Python port handles the same three.
- Catalog is a fixed list of v1 attrs with their type and allowed operators. The UI dropdowns and the validator both derive from this single catalog object (DRY).
- Customer-level attrs (`tier, recency_days, value_group, is_contactable`) can be previewed against `wh_customer_tier`. Touchpoint-level attrs (`op_type, channel`) are per-scan — preview cannot count them (document this limitation clearly in the module docstring and in UI).
- `is_contactable` is stored as 0/1 INTEGER but targeting uses a list: `{"is_contactable": [1]}` or `{"is_contactable": 1}` (scalar). Handle both.

## Requirements

### Functional
- `TARGETING_CATALOG: dict` — maps attr name → `{type: "list"|"range"|"scalar", description: str, values?: list}`. Values list for enum attrs (op_type, tier, channel, value_group).
- `validate_targeting(targeting: dict) → list[str]` — returns list of error strings (empty = valid). Checks: keys must be in catalog; list values must be non-empty; range must have at least one of gte/lte/gt/lt as number.
- `matches_targeting(targeting: dict, context: dict) → bool` — exact Python port of TS `matchesTargeting`. Returns True for `{}` (DEFAULT). No exceptions (malformed targeting → True, same as edge).
- `preview_match_customers(targeting: dict, cache_db_path: str) → dict` — queries `wh_customer_tier`, runs `matches_targeting` on each row (mapping `strategic_tier → tier`), returns `{"matched": int, "total": int, "sample": list[dict]}` (sample = up to 5 rows). Customer-level only.

### Non-Functional
- Module ≤ 200 lines. Split into `targeting_catalog.py` + `targeting_engine.py` if needed.
- Zero external dependencies (stdlib only).
- FastAPI-free — tested directly.

## Architecture

```
crm/src/hug/
  targeting_catalog.py   ← TARGETING_CATALOG constant + validate_targeting()
  targeting_engine.py    ← matches_targeting() + preview_match_customers()
```

**Data flow (validation on UI save):**
```
UI form submit → targeting_catalog.validate_targeting(targeting_dict)
              → [] (ok) or ["error msg", ...] → return 400 with errors
```

**Data flow (preview):**
```
UI preview request → targeting_engine.preview_match_customers(targeting, cache_db_path)
                   → open cache.db (read_only) → SELECT wh_customer_tier
                   → matches_targeting() per row → {"matched": N, "total": M, "sample": [...]}
```

## Related Code Files

**Create:**
- `crm/src/hug/targeting_catalog.py`
- `crm/src/hug/targeting_engine.py`

**Read-only references:**
- `webhook_receiver/cloudflareD1/src/hug-handler.ts` lines 148–203 — matchesTargeting + selectCampaign
- `crm/src/hug/op_types.py` — existing op_type constants (reuse for catalog values)
- `crm/src/hug/customer_push.py:_load_tier_rows()` — wh_customer_tier query pattern to copy

## Implementation Steps

1. **`targeting_catalog.py`** — define `TARGETING_CATALOG`:
   ```python
   TARGETING_CATALOG = {
       "op_type": {
           "type": "list",
           "description": "Loại thao tác (điểm chạm)",
           "values": ["package_insert", "loyalty_card", "winback_flyer", "receipt", "acquire"],
           "touchpoint_level": True,   # per-scan; cannot be previewed against customers
       },
       "tier": {
           "type": "list",
           "description": "Phân khúc khách hàng",
           "values": ["VIP", "CORE", "CASUAL", "NEW", "SECOND_ORDER",
                      "DORMANT_VALUABLE", "LAPSED_VALUABLE", "MASKED_REPEAT", "UNKNOWN"],
       },
       "channel": {
           "type": "list",
           "description": "Kênh bán hàng",
           "values": ["shopee", "tiki", "lazada", "website", "pos", "other"],
           "touchpoint_level": True,
       },
       "value_group": {
           "type": "list",
           "description": "Nhóm giá trị đơn",
           "values": ["HIGH", "MID", "LOW", "UNKNOWN"],
       },
       "is_contactable": {
           "type": "list",
           "description": "Có thể liên hệ",
           "values": [0, 1],
       },
       "recency_days": {
           "type": "range",
           "description": "Số ngày kể từ đơn cuối",
       },
   }
   ```

   Then `validate_targeting(targeting: dict) → list[str]`: iterate keys, check catalog membership, check value types per rule form.

2. **`targeting_engine.py`** — `matches_targeting(targeting, context)`:
   - Parse targeting (already a dict here, not JSON string — caller parses).
   - Empty dict → True.
   - For each key: array rule → any(str(v)==str(ctx[key]) for v in rule); range rule → numeric bounds; scalar → str equality. Missing context value for a constrained key → False.
   - `preview_match_customers(targeting, cache_db_path)`: open `file:path?mode=ro`, SELECT, map rows to context dicts (`strategic_tier → tier`), run `matches_targeting`, return result dict.

3. **Tests** `crm/tests/hug/test_targeting_engine.py`:
   - `{}` matches any context.
   - `{"tier": ["VIP", "CORE"]}` matches VIP, misses CASUAL.
   - `{"recency_days": {"gte": 30, "lte": 90}}` matches 60, misses 20 and 100.
   - `{"is_contactable": [1]}` matches 1, misses 0.
   - `{"tier": ["VIP"], "op_type": ["package_insert"]}` — AND: both must match.
   - Malformed targeting (invalid JSON or unknown key) — validate catches it; matches_targeting on malformed dict → True (graceful).
   - `validate_targeting` rejects unknown key; accepts valid range; rejects range with no operators.

## Todo

- [ ] Write `targeting_catalog.py` with `TARGETING_CATALOG` + `validate_targeting`
- [ ] Write `targeting_engine.py` with `matches_targeting` + `preview_match_customers`
- [ ] Unit tests — all cases above
- [ ] Verify catalog values match `op_types.py` constants (no duplication — import from there)

## Success Criteria

- `matches_targeting` output is identical to the TS `matchesTargeting` for all rule forms.
- `validate_targeting` catches: unknown attr key, empty list value, range with no operators, non-numeric range value.
- `preview_match_customers` returns correct matched count against a test fixture of `wh_customer_tier` rows.
- All tests pass with no FastAPI import.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Python `str(v) == str(ctx[key])` coercion mismatch with TS (e.g. `is_contactable` stored as int 1 vs string "1") | Medium | Medium | Mirror TS exactly: `String(v) === String(ctxValue)` → use `str()` on both sides in Python |
| wh_customer_tier column name `strategic_tier` vs edge field `tier` | High (certain) | High | Map explicitly in `preview_match_customers`: `context["tier"] = row["strategic_tier"]` |
| cache.db not available during preview | Low | Low | Return `{"error": "cache.db unavailable", "matched": 0, "total": 0}` — never raise |
| op_type values diverge between `op_types.py` and catalog | Low | Medium | Import `OP_LABELS` keys from `op_types.py` for the catalog values list |

## Security Considerations
- `preview_match_customers` opens `cache.db` read-only (`file:path?mode=ro`). No write path.
- Targeting dict comes from UI form — validated by `validate_targeting` before `matches_targeting` is called in the preview path.

## Next Steps
- Phase 4 imports `validate_targeting` for save-time validation.
- Phase 5 imports `matches_targeting` + `preview_match_customers` for the preview endpoint and overlap check.
