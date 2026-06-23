# Phase 1 — `sku` catalog entry + `not_in` negation operator

## Context links

- Plan overview: `plans/260623-0852-hug-campaign-matching-and-preview/plan.md`
- Research source: `plans/reports/hug-campaign-targeting-criteria-expansion-260623-0852-report.md` §3a, §4a
- TS matcher: `webhook_receiver/cloudflareD1/src/hug-handler.ts:148–189`
- Python mirror: `crm/src/hug/targeting_engine.py:48–106`
- Catalog: `crm/src/hug/targeting_catalog.py:27–68`
- Parity tests: `crm/src/tests/test_hug_targeting_engine.py`

## Overview

- **Priority:** P0 — unblocks product-based routing and clean B2B exclusion
- **Status:** pending
- **Worker deploy required:** No (zero TS changes for `sku`; `not_in` requires TS change + deploy)
- **D1 schema migration:** No

## Verified facts (re-grepped)

- `sku` is already in `hug_token` D1 (`schema_hug.sql:20`), already in `ScanContext` (`hug-handler.ts:89`), and the list branch of `matchesTargeting` (`hug-handler.ts:165–172`) handles it with `String()` coercion. The only missing piece is the catalog entry.
- `matchesTargeting` object-rule branch (`hug-handler.ts:173–180`) currently handles only `gte/gt/lte/lt` numeric range. It does NOT handle `not_in`. Adding `not_in` requires a new sub-branch inside the `typeof rule === 'object'` arm.
- Python `matches_targeting` (`targeting_engine.py:78–92`) mirrors the TS object-rule branch. Same extension point.
- `validate_targeting` currently allows only `list` (OR membership) and `range` (gte/gt/lte/lt) shapes (`targeting_catalog.py:102–146`). It must be extended to allow `{"not_in": [...]}` as a valid dict rule for `list`-type attrs.
- `TARGETING_CATALOG` comment (`targeting_catalog.py:16–17`) explicitly defers `order_value`, `scan_index`, `geo` — not `sku`. Adding `sku` is expressly in scope.
- No `Dockerfile.crm` change needed — `crm/src` is volume-mounted (`docker-compose.yml:187`).

## Requirements

### Functional
1. Campaigns can specify `{"sku": ["FJ-OMEGA3-60", "FJ-COLLAGEN-90"]}` in targeting; the edge matcher routes on it.
2. Campaigns can specify `{"tier": {"not_in": ["WHOLESALE", "STAFF", "KOL"]}}` (or any list-type attr); the edge matcher negates the list.
3. `not_in` shape is accepted by `validate_targeting` for any `list`-type catalog attr.
4. Python `matches_targeting` is semantically identical to the TS version for `not_in` rules.

### Non-functional
- Zero change to existing rule shapes (existing `list` and `range` rules must pass all M01–M18 tests unchanged).
- `sku` domain is open (no fixed values set) — validator skips domain check when `values` is absent.
- `not_in` cannot appear alongside other sub-keys in the same object rule (e.g., `{"not_in": [...], "gte": 5}` is invalid — validator must reject it).

## JSON shape decision for `not_in`

Rule shape: `{"<attr>": {"not_in": ["VAL1", "VAL2"]}}`.

This fits inside the existing `typeof rule === 'object'` branch in `matchesTargeting`. Detection: if `rule` is an object AND `"not_in" in rule` → treat as negation; else existing numeric range handling. The validator distinguishes: if a `list`-type attr receives a dict rule, it must contain `"not_in"` (and only `"not_in"`); any other keys are an error.

This keeps the rule schema self-describing and avoids a top-level convention (`{"tier_not_in": [...]}`) that would require new catalog keys for each negated attr.

## Architecture

```
Campaign save (UI)
  → parse_targeting (form_helpers)
  → validate_targeting (catalog.py)   ← extend: accept {"not_in":[...]} for list attrs
  → upsert_campaign → push to Worker

Scan (edge)
  → matchesTargeting (hug-handler.ts)  ← extend: not_in sub-branch in object-rule arm

Preview (cache.db path, unchanged until Phase 3)
  → matches_targeting (targeting_engine.py) ← extend: not_in sub-branch

Tests
  → test_hug_targeting_engine.py ← new parity cases for not_in
  → index.test.ts ← new matcher unit test for not_in
```

## Data flow

```
Input:  targeting JSON string from hug_campaign.targeting
        ctx: ScanContext (sku present at hug-handler.ts:89 — verified)

sku rule:
  {"sku": ["FJ-OMEGA3"]}
  → existing list branch (hug-handler.ts:165–172)
  → String("FJ-OMEGA3") === String(ctx.sku) → match/no-match

not_in rule:
  {"tier": {"not_in": ["WHOLESALE", "STAFF"]}}
  → object branch (hug-handler.ts:173)
  → detect "not_in" key → check array membership → NEGATE
  → ctx.tier NOT in list → True
  → ctx.tier in list → False

Output: boolean (same contract as existing matchesTargeting)
```

## Files to modify

| File | Change |
|------|--------|
| `crm/src/hug/targeting_catalog.py` | Add `sku` entry (lines after 67); extend `validate_targeting` to accept `{"not_in": [...]}` for list attrs (after line 120) |
| `crm/src/hug/targeting_engine.py` | Add `not_in` sub-branch in object-rule arm (after line 92); update module docstring mapping (line 19) |
| `webhook_receiver/cloudflareD1/src/hug-handler.ts` | Add `not_in` sub-branch in `matchesTargeting` object-rule arm (after line 180); update JSDoc comment (lines 135–145) |
| `crm/src/tests/test_hug_targeting_engine.py` | New parity tests for `not_in` (extend M-series); new validate test for `not_in` shape acceptance and rejection of mixed shapes |
| `webhook_receiver/cloudflareD1/src/index.test.ts` | New describe block for `not_in` matcher cases |

## Files to create

None.

## Implementation steps

### Step 1 — Add `sku` to `TARGETING_CATALOG` (`targeting_catalog.py`)

Insert after the `channel` entry (line 41) or at end of catalog:

```python
"sku": {
    "type": "list",
    "description": "SKU sản phẩm chính trên đơn hàng",
    # No fixed domain: SKU set is open (new products added continuously).
    # validate_targeting skips domain check when 'values' is absent.
    "touchpoint_level": True,
},
```

No `values` key → `validate_targeting` skips domain check (already supported at `targeting_catalog.py:112–119`: `domain = spec.get("values"); if domain is not None: ...`).

### Step 2 — Extend `validate_targeting` for `not_in` shape (`targeting_catalog.py`)

In the `if spec["type"] == "list":` block (line 103), currently accepts only a `list` rule. Extend:

After the existing `if not isinstance(rule, list):` check, add:

```python
# Also accept {"not_in": [...]} object rule for list-type attrs.
if isinstance(rule, dict):
    not_in_val = rule.get("not_in")
    extra_keys = [k for k in rule if k != "not_in"]
    if extra_keys:
        errors.append(f"'{key}': not_in object must contain only 'not_in' key; "
                      f"unexpected keys: {extra_keys}")
    elif not isinstance(not_in_val, list) or len(not_in_val) == 0:
        errors.append(f"'{key}': not_in value must be a non-empty list")
    else:
        domain = spec.get("values")
        if domain is not None:
            domain_strs = {str(v) for v in domain}
            for v in not_in_val:
                if str(v) not in domain_strs:
                    errors.append(f"'{key}': not_in value {v!r} not in allowed domain {domain}")
    continue  # skip existing list-rule checks below
```

Also add `"not_in"` to the error message when a plain list is required, so the validator message stays helpful.

### Step 3 — Add `not_in` sub-branch to Python `matches_targeting` (`targeting_engine.py`)

Inside `elif isinstance(rule, dict):` (line 78), currently handles only numeric range. Extend BEFORE the numeric range check:

```python
elif isinstance(rule, dict):
    # TS lines 173–180: object rule — two shapes:
    #   {"not_in": [...]}  → negated list membership (new)
    #   {"gte":N,...}      → numeric range (existing)
    if "not_in" in rule:
        # ctx_value None with a not_in constraint: treat as "not in the list" (= True)?
        # Decision: ctx_value None → False (same as list rule; a constrained attr
        # with no value cannot be asserted to be outside a list meaningfully).
        if ctx_value is None:
            return False
        in_list = any(str(v) == str(ctx_value) for v in rule["not_in"])
        if in_list:
            return False
        # Not in the excluded list → passes this key; continue to next key.
    else:
        # existing numeric range logic (unchanged)
        if isinstance(ctx_value, bool) or not isinstance(ctx_value, (int, float)):
            return False
        num = ctx_value
        ...
```

Update module docstring (line 19) to document the new shape with TS line citation.

### Step 4 — Add `not_in` sub-branch to TS `matchesTargeting` (`hug-handler.ts`)

Inside `} else if (typeof rule === 'object' && rule !== null) {` (line 173), extend:

```typescript
} else if (typeof rule === 'object' && rule !== null) {
    const ruleObj = rule as Record<string, unknown>;
    if ('not_in' in ruleObj) {
        // Negated list membership: ctxValue must NOT be in the not_in array.
        // ctxValue null/undefined → no value to exclude → treat as no match
        // (same semantics as list rule: a constrained attr with no ctx value fails).
        if (ctxValue === null || ctxValue === undefined) return false;
        const notInList = ruleObj['not_in'] as unknown[];
        const inList = notInList.some((v) => String(v) === String(ctxValue));
        if (inList) return false;
    } else {
        // Existing numeric range: { gte?, gt?, lte?, lt? }
        const numCtx = typeof ctxValue === 'number' ? ctxValue : null;
        if (numCtx === null) return false;
        const r = ruleObj as Record<string, number>;
        if (r.gte !== undefined && !(numCtx >= r.gte)) return false;
        if (r.lte !== undefined && !(numCtx <= r.lte)) return false;
        if (r.gt  !== undefined && !(numCtx >  r.gt))  return false;
        if (r.lt  !== undefined && !(numCtx <  r.lt))  return false;
    }
}
```

Update JSDoc comment block (lines 135–145) to document `not_in` shape.

### Step 5 — Worker deploy

Run `wrangler deploy` from `webhook_receiver/cloudflareD1/`. This is the only Worker change in Phase 1.

### Step 6 — Tests

**Python (`test_hug_targeting_engine.py`):**

New parity tests (M-series extension):
- `test_not_in_ctx_value_absent_from_excluded_list_passes` — `{"tier": {"not_in": ["WHOLESALE"]}}` + ctx `tier="VIP"` → True
- `test_not_in_ctx_value_in_excluded_list_fails` — `{"tier": {"not_in": ["WHOLESALE"]}}` + ctx `tier="WHOLESALE"` → False
- `test_not_in_ctx_value_none_fails` — constrained attr with None ctx → False
- `test_not_in_with_str_coercion` — rule `{"is_contactable": {"not_in": [0]}}` + ctx `is_contactable=0` → False (str coercion)
- `test_not_in_and_list_combined_in_same_targeting` — `{"tier": {"not_in": ["WHOLESALE"]}, "op_type": ["package_insert"]}` → AND semantics

New validate tests (V-series extension):
- `test_validate_accepts_not_in_for_list_attr` — `{"tier": {"not_in": ["WHOLESALE"]}}` → no errors
- `test_validate_rejects_not_in_with_extra_keys` — `{"tier": {"not_in": [...], "gte": 1}}` → error
- `test_validate_rejects_not_in_on_range_attr` — `{"recency_days": {"not_in": [30]}}` → error (range attr cannot use not_in)
- `test_validate_rejects_empty_not_in_list` — `{"tier": {"not_in": []}}` → error
- `test_validate_not_in_sku_open_domain` — `{"sku": {"not_in": ["ANY-SKU-CODE"]}}` → no errors (open domain, no check)
- Update `test_validate_accepts_all_six_catalog_attrs` → add sku to coverage (V09 update); also add a new V10 covering all 7 attrs.

**TypeScript (`index.test.ts`):**

Add a describe block `matchesTargeting — not_in operator`:
- `not_in: value absent from excluded list → true`
- `not_in: value in excluded list → false`
- `not_in: null ctx value → false`
- `not_in: string coercion parity with Python`

## Test matrix

| Layer | Tool | Scope |
|-------|------|-------|
| TS matcher unit | vitest (index.test.ts) | not_in True/False/null |
| Python matcher parity | pytest (test_hug_targeting_engine.py) | not_in parity M-series |
| Python validator | pytest (test_hug_targeting_engine.py) | not_in V-series |
| Python preview (sku) | pytest P02 variant | sku in targeting → upper-bound count unchanged |

## Success criteria

- All existing M01–M18, V01–V09 tests pass unchanged.
- New not_in tests pass in both Python and TS.
- `{"sku": [...]}` accepted by validator with no errors; `{"sku": {"not_in": [...]}}` also accepted.
- `{"recency_days": {"not_in": [...]}}` rejected by validator (range attr, not list type).
- Worker deploys cleanly (`wrangler deploy` exits 0).

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| TS↔Python semantic drift on `not_in` (esp. `null` ctx handling) | Medium | High — silently routes wrong customers | Parity test cases must cover null-ctx and coercion in BOTH languages; cross-cite TS line in Python docstring |
| `not_in` object shape conflicts with future numeric range extensions (e.g. someone passes `{"gte": 5, "not_in": [...]}`) | Low | Medium | Validator rejects mixed keys; Worker rejects if `not_in` co-exists with range keys (add explicit check) |
| Open `sku` domain causes validator to accept typo SKU codes silently | Low | Low | Acceptable by design (report §3a confirms values:None is per-spec); document in catalog entry comment |

## Rollback

- TS: `wrangler deploy` of the previous commit (additive change only — no existing route touched).
- Python: `crm/src` is volume-mounted; reverting catalog + engine files + container restart is instant, no rebuild.
- No D1 schema to rollback.
- Existing campaigns with list or range rules are unaffected (no shape changes — new sub-branch only executes when `"not_in" in rule`).

## Unresolved questions

1. **`not_in` + `null` ctx semantics:** Chosen `ctx_value None → False` (same as list rule). Alternative: `None → True` (absent value is "not in the excluded list"). Current choice is more conservative. Confirm with user before implementation.
2. **`sku` in the admin UI rule-builder:** The rule-builder renders catalog attrs as tag-list dropdowns. `sku` with open domain needs a free-text input, not a dropdown. UI detail out of scope for this plan — needs UI design decision before the CRM form is updated to expose `sku` as a targeting field.
3. **`not_in` UI representation:** Same issue — the rule-builder dropdown needs an "include/exclude" toggle or a separate "Exclude" field. Needs UI design. The backend (matcher + validator) can be shipped without the UI; campaigns using `not_in` can be created via direct API/SQL until the UI is updated.
