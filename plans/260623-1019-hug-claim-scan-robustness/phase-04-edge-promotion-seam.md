# Phase 4 — Edge-Promotion Seam: Generic `attributes` Column + Worker ScanContext Merge

## Context links
- `webhook_receiver/cloudflareD1/schema_hug.sql:13-25` — D1 `hug_token` schema (no `attributes` column yet)
- `webhook_receiver/cloudflareD1/src/hug-handler.ts:79-90` — `ScanContext` interface (10 fixed fields)
- `webhook_receiver/cloudflareD1/src/hug-handler.ts:148-189` — `matchesTargeting` — uses `(ctx as Record<string,unknown>)[key]` at `:163` — already key-generic
- `webhook_receiver/cloudflareD1/src/hug-handler.ts:217-275` — `handleHugScan` — builds `scanContext` at `:232-243` from fixed column set
- `webhook_receiver/cloudflareD1/src/hug-handler.ts:334-408` — `HugTokenRow` interface + `handleHugTokenUpsert` — upsert SQL at `:374-386` lists fixed columns explicitly
- `crm/src/hug/d1_push.py:32-55` — `_row_to_payload` — projects fixed columns to push payload
- `crm/src/hug/d1_push.py:58-82` — `push_bound_token` — sends `{"rows": [payload]}` to `/hug/token/upsert`
- `crm/src/hug/claim_fields.py` — `CLAIM_FIELDS` with `edge: bool` per field (Phase 2 new file)
- `crm/src/hug/repository.py:91-134` — `bind_token` — writes `bind_attributes` JSON column (Phase 2)
- `crm/src/hug/targeting_catalog.py:27-68` — `TARGETING_CATALOG` — add entry per new edge-promoted attr
- Sibling plan: `plans/260623-0852-hug-campaign-matching-and-preview/` — catalog expansion (coordinate entries)

## Overview
- **Priority:** P2 — deferrable. Required only when the first edge-matchable bind field beyond the already-promoted fixed columns (`op_type`, `channel`, `order_code`, etc.) is introduced. For current config (`order_code` edge=True, `is_gift` edge=False), `order_code` is already a fixed column in D1 — no new attributes needed. Phase 4 becomes load-bearing when a genuinely new bind field with `edge=True` is configured.
- **Status:** pending
- **Blocked by:** Phase 2 (`bind_attributes` column + `claim_fields.py` `edge` flag must exist before d1_push can extract them)
- **Scope:** Three coordinated changes across three layers: D1 schema, Worker TS, Python push. Targeting catalog entry (local only). No crm container schema change (SQLite `bind_attributes` already added in Phase 2).

## The "config-only after one-time seam" guarantee

After Phase 4 ships:

```
To add a new edge-matchable bind field:
  1. Append to CLAIM_FIELDS in claim_fields.py  (edge=True, validate=..., ...)
  2. Add one entry to targeting_catalog.py

That's it. No D1 migration. No Worker deploy. No d1_push.py change.
```

Why it works:
- D1 `hug_token.attributes TEXT` is a single JSON blob — new keys land there automatically.
- Worker `handleHugTokenUpsert` writes `attributes` as-is from payload.
- Worker `handleHugScan` parses `attributes` JSON and spreads keys into `ScanContext`.
- `matchesTargeting` at `:163` already does `ctx[key]` — works for any string key.
- `d1_push._row_to_payload` serialises the `edge=True` subset of `bind_attributes` into the `attributes` field — driven by `CLAIM_FIELDS` config.

The `targeting_catalog.py` entry is needed for the rule-builder UI and `validate_targeting()` to accept the new key — not for the Worker to match it.

## Data flows

```
claim_fields.py  CLAIM_FIELDS  (edge=True subset: e.g. {order_code, future_field_x})
      │
      ▼
d1_push._row_to_payload(row)
  - fixed promoted columns: token, customer_id, op_type, order_code, channel, ...
  - NEW: attributes = json.dumps({k: bind_attributes[k]
                                   for f in CLAIM_FIELDS if f["edge"] and not f["key"] in _FIXED_D1_COLS
                                   for k in [f["key"]] if k in bind_attributes})
  → payload includes "attributes": "{\"future_field_x\": \"val\"}"
      │
      ▼
POST /hug/token/upsert  (handleHugTokenUpsert)
  HugTokenRow now has optional "attributes?: string | null"
  UPSERT SQL: ... attributes = excluded.attributes
      │
      ▼
D1 hug_token row: attributes TEXT = '{"future_field_x": "val"}'
      │
      ▼
GET /h/:token  (handleHugScan)
  row = D1 query  (now includes attributes column)
  ScanContext = { ...fixed fields..., ...JSON.parse(row.attributes ?? "{}") }
  → matchesTargeting sees ctx["future_field_x"] = "val"
  → campaign rule {"future_field_x": ["val"]} matches
```

**`_FIXED_D1_COLS`** constant in `d1_push.py`: the set of fields already pushed as dedicated columns (so they are not also serialised into `attributes` JSON). Current value: `{"token", "customer_id", "op_type", "order_code", "channel", "ship_date", "sku", "campaign_hint", "status", "batch_id"}`. This constant is the only place that needs updating when a new field graduates from `attributes` to a dedicated column — a rare, deliberate promotion.

## Requirements

### Functional

#### 1. D1 schema migration (`schema_hug.sql`)

Add nullable `attributes TEXT` column to `hug_token`:

```sql
-- Add to schema_hug.sql after the existing CREATE TABLE IF NOT EXISTS hug_token block:
-- Note: D1 SQLite supports ADD COLUMN but NOT "IF NOT EXISTS" on ALTER TABLE.
-- This migration must be run exactly once via wrangler d1 execute.
ALTER TABLE hug_token ADD COLUMN attributes TEXT;
```

**D1 caveat:** Cloudflare D1 (SQLite dialect) does NOT support `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. This migration must therefore be tracked and applied exactly once. After applying, all existing rows have `attributes = NULL` (no data loss). NULL is handled in the Worker as empty object `{}`.

Apply with:
```bash
wrangler d1 execute fgcare-webhook-db --remote --file=schema_hug.sql
```

The file comment at `schema_hug.sql:5` says "Apply with: wrangler d1 execute fgcare-webhook-db --remote --file=schema_hug.sql" — this command re-applies the whole file. Because `CREATE TABLE IF NOT EXISTS` is safe to re-run, only the new `ALTER TABLE` is net-new. **Risk:** if the file is re-applied after the column already exists, the `ALTER TABLE` will error. Mitigation: wrap in a migration comment and track with a migration marker (or separate file — see Risks).

#### 2. Worker: `HugTokenRow` interface + `handleHugTokenUpsert` (`hug-handler.ts:334-408`)

**`HugTokenRow` interface** (`:334-344`): add optional field:
```typescript
attributes?: string | null;   // JSON blob of dynamic edge-promoted bind attrs
```

**`handleHugTokenUpsert` upsert SQL** (`:374-386`): add `attributes` to the INSERT column list and ON CONFLICT UPDATE SET:
```sql
INSERT INTO hug_token (token, customer_id, op_type, order_code, channel, ship_date, sku,
                        campaign_hint, status, batch_id, attributes)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(token) DO UPDATE SET
  customer_id   = excluded.customer_id,
  ...existing cols...,
  attributes    = excluded.attributes
```

Bind parameter: `r.attributes ?? null` (11th bind arg).

#### 3. Worker: `handleHugScan` — ScanContext merge (`hug-handler.ts:217-275`)

**D1 query** (`:225-230`): the SELECT already does `SELECT t.*` — the new `attributes` column is automatically included.

**ScanContext build** (`:232-243`): after constructing the fixed fields, parse and spread `attributes`:

```typescript
// Parse dynamic attributes from the JSON blob (never throws — bad JSON → {})
let extraAttrs: Record<string, unknown> = {};
if (row.attributes) {
    try { extraAttrs = JSON.parse(row.attributes); } catch { /* ignore */ }
}

const scanContext: ScanContext | null = row ? {
    op_type:        row.op_type,
    tier:           row.tier ?? null,
    channel:        row.channel ?? null,
    value_group:    row.value_group ?? null,
    recency_days:   row.recency_days ?? null,
    is_contactable: row.is_contactable ?? 0,
    customer_id:    row.customer_id ?? null,
    order_code:     row.order_code ?? null,
    ship_date:      row.ship_date ?? null,
    sku:            row.sku ?? null,
    ...extraAttrs,                            // dynamic keys merge on top
} : null;
```

`ScanContext` interface (`:79-90`): add an index signature to accept extra keys without TS error:
```typescript
interface ScanContext {
    op_type: string;
    tier: string | null;
    // ... existing fields ...
    sku: string | null;
    [key: string]: unknown;   // dynamic edge-promoted bind attrs
}
```

`matchesTargeting` at `:163` already casts to `Record<string, unknown>` — no change needed there.

**Performance note:** `JSON.parse` on a small JSON blob (`attributes`) runs in < 1 µs on V8. No measurable hot-path impact for a per-scan operation.

#### 4. Python: `d1_push._row_to_payload` — edge subset serialisation (`d1_push.py:32-55`)

Add `_FIXED_D1_COLS` constant (module level):
```python
_FIXED_D1_COLS = frozenset({
    "token", "customer_id", "op_type", "order_code", "channel",
    "ship_date", "sku", "campaign_hint", "status", "batch_id",
})
```

Update `_row_to_payload` to extract the `edge=True` subset from `bind_attributes` and serialise as `attributes` JSON:

```python
import json
from hug.claim_fields import CLAIM_FIELDS

def _row_to_payload(row: sqlite3.Row) -> dict[str, Any]:
    payload = {
        "token":         row["token"],
        "customer_id":   row["customer_id"],
        "op_type":       row["op_type"],
        "order_code":    row["order_code"],
        "channel":       row["channel"],
        "ship_date":     row["ship_date"],
        "sku":           row["sku"],
        "campaign_hint": row["campaign_hint"],
        "status":        row["status"],
        "batch_id":      row["batch_id"],
    }
    # Build attributes JSON from edge=True CLAIM_FIELDS not already in fixed cols
    bind_attrs_raw = row["bind_attributes"]
    bind_attrs: dict = {}
    if bind_attrs_raw:
        try:
            bind_attrs = json.loads(bind_attrs_raw)
        except (json.JSONDecodeError, TypeError):
            pass
    edge_attrs = {
        f["key"]: bind_attrs[f["key"]]
        for f in CLAIM_FIELDS
        if f.get("edge") and f["key"] not in _FIXED_D1_COLS and f["key"] in bind_attrs
    }
    payload["attributes"] = json.dumps(edge_attrs) if edge_attrs else None
    return payload
```

For current config (`order_code` edge=True but in `_FIXED_D1_COLS`, `is_gift` edge=False): `edge_attrs` is always `{}` → `attributes` is `None`. No change in push behavior until a genuinely new `edge=True` field is added to `CLAIM_FIELDS`. This is correct — the seam is wired and dormant.

#### 5. `targeting_catalog.py` — new entry per edge-promoted bind field

When the first non-fixed `edge=True` bind field is introduced in `CLAIM_FIELDS`, add a corresponding entry to `TARGETING_CATALOG`:

```python
"future_field_x": {
    "type": "list",
    "description": "...",
    "values": [...],
    "touchpoint_level": True,   # it's a per-scan (token) attribute
},
```

Coordinate with `plans/260623-0852-hug-campaign-matching-and-preview/` — no duplicate entries. One entry per attribute, defined once.

For Phase 4 as shipped (no non-fixed edge fields yet), no new catalog entry is needed. This step is documented here so the implementer knows where to look when the first real edge field arrives.

## Deploy order (CRITICAL — must be followed exactly)

```
Step 1: Apply D1 migration
  wrangler d1 execute fgcare-webhook-db --remote --file=schema_hug.sql
  → adds attributes TEXT column to D1 hug_token (existing rows get NULL)
  → Worker still works: SELECT t.* returns attributes=NULL → JSON.parse skipped → ctx unchanged

Step 2: wrangler deploy  (Worker update)
  → HugTokenRow accepts attributes field
  → handleHugScan parses attributes and spreads into ScanContext
  → handleHugTokenUpsert writes attributes column
  Safe: existing rows have attributes=NULL → no targeting change for existing tokens

Step 3: docker compose restart crm  (d1_push update)
  → _row_to_payload now sends attributes field in upsert payload
  → For current config: attributes=null (no non-fixed edge fields yet) → no-op
  → When first edge=True non-fixed field is added, push starts propagating it

Step 4 (per new field, config-only):
  → Add dict to CLAIM_FIELDS (edge=True)
  → Add entry to targeting_catalog.py
  → docker compose restart crm (picks up CLAIM_FIELDS change)
  → No D1 migration. No wrangler deploy.
```

**Why Step 1 before Step 2:** Worker deploy before schema migration would cause the SELECT to not return `attributes` (column absent) → `row.attributes` undefined → `JSON.parse(undefined)` throws → ScanContext build might fail. With schema first, `row.attributes` is NULL → guard `if (row.attributes)` skips parse safely.

**Why Step 2 before Step 3:** If crm sends `attributes` in the upsert payload before the Worker's `handleHugTokenUpsert` accepts it, the extra field is silently ignored by D1 (extra JSON keys in body are discarded; the INSERT doesn't list `attributes` yet). No breakage — just wasted bytes. But ordered deploy is cleaner.

## Files to modify

| File | Change |
|------|--------|
| `webhook_receiver/cloudflareD1/schema_hug.sql` | Add `ALTER TABLE hug_token ADD COLUMN attributes TEXT;` after existing table block |
| `webhook_receiver/cloudflareD1/src/hug-handler.ts` | `HugTokenRow`: add `attributes?`; `handleHugTokenUpsert`: add to INSERT + UPDATE SET; `ScanContext`: add index signature; `handleHugScan`: parse + spread `attributes` into `scanContext` |
| `crm/src/hug/d1_push.py` | Add `_FIXED_D1_COLS` constant; update `_row_to_payload` to build + include `attributes` JSON |

## Files to create
None.

## Test matrix

| Layer | What | How |
|-------|------|-----|
| Unit | `_row_to_payload` — no non-fixed edge fields → `attributes=None` | pytest, mock `row` with empty `bind_attributes` |
| Unit | `_row_to_payload` — edge=True non-fixed field present in `bind_attributes` → `attributes='{"field_x":"v"}'` | Add test field temporarily to CLAIM_FIELDS in test scope |
| Unit | `_row_to_payload` — `bind_attributes` is NULL/malformed JSON → `attributes=None`, no exception | pytest |
| Unit | `_FIXED_D1_COLS` covers all 10 current promoted columns | Assertion test |
| TS unit | `handleHugScan`: `row.attributes = '{"field_x":"val"}'` → `scanContext["field_x"] === "val"` | Vitest with D1 mock |
| TS unit | `handleHugScan`: `row.attributes = null` → `scanContext` has no extra keys (no crash) | Same |
| TS unit | `handleHugScan`: `row.attributes = 'INVALID'` → `scanContext` has no extra keys (JSON.parse fails → `{}`) | Same |
| TS unit | `handleHugTokenUpsert`: payload with `attributes` field → D1 upsert includes it | Vitest with D1 mock |
| TS unit | `matchesTargeting`: targeting `{"field_x": ["val"]}` + ctx with `field_x="val"` → true | Direct function test (no D1) |
| Integration | D1 migration applied → `PRAGMA table_info(hug_token)` shows `attributes` column | `wrangler d1 execute --local` in CI |
| Manual | Push a bound token → verify `attributes` column in D1 (Worker logs or `wrangler d1 execute SELECT`) | Post-deploy smoke |
| Manual | Set campaign targeting `{"field_x":["val"]}` + scan token with that attr → correct campaign selected | End-to-end with a test campaign |

## Success criteria
- D1 `hug_token` table has `attributes TEXT` column (nullable) after migration.
- `wrangler deploy` succeeds with no TS errors (index signature addition may require a minor TS cast adjustment).
- `_row_to_payload` returns `attributes=None` for current config (no non-fixed edge fields). No regression in existing D1 push.
- `handleHugScan` with `attributes=NULL` → `scanContext` identical to pre-Phase-4 behavior. Existing campaigns still match.
- `handleHugScan` with `attributes='{"field_x":"val"}'` → `scanContext["field_x"] === "val"` → campaign targeting on that key works.
- All unit + integration tests pass.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| D1 `ALTER TABLE ADD COLUMN` has no `IF NOT EXISTS` → error if re-applied | Medium | Medium | Track as a one-time migration; add a comment at top of the new statement "-- migration: run once, 2026-06-23"; separate migration tracking or a guard script |
| `schema_hug.sql` being re-run in CI/CD or by new dev → duplicate column error | Medium | Medium | Either separate the `ALTER TABLE` into a versioned migration file `schema_hug_v2.sql` (preferred), or add a CI check that guards re-application |
| `ScanContext` index signature `[key: string]: unknown` conflicts with existing typed fields | Low | Low | TS requires that all explicit fields be assignable to the index type (`unknown`); they are, since all existing field types are subtypes of `unknown`. Verify with `tsc --noEmit` |
| `...extraAttrs` spread overwrites fixed ScanContext fields if `attributes` JSON happens to contain same key | Low | Low | Fixed fields are constructed BEFORE the spread; if `extraAttrs` has e.g. `"op_type"` it would overwrite. Mitigation: build `extraAttrs` by excluding keys already in fixed set: `const safeAttrs = Object.fromEntries(Object.entries(extraAttrs).filter(([k]) => !(k in fixedKeys)))` |
| `JSON.parse` cost on every scan (hot path) | Very Low | Very Low | V8 parses small JSON blobs in < 1 µs; negligible vs D1 query latency (~5-10 ms); no mitigation needed |
| `_row_to_payload` imports `CLAIM_FIELDS` at module load — circular import if `claim_fields` imports from `d1_push` | Low | Low | `claim_fields.py` imports only `sapo_order_proxy` (Phase 2); no circular dependency. Verify with `python -c "from hug.d1_push import push_bound_token"` |
| `targeting_catalog.py` entry added without corresponding `claim_fields.py` entry (or vice versa) | Low | Medium | Document contract: every `edge=True` non-fixed CLAIM_FIELDS entry MUST have a catalog entry. Add a startup assertion in `targeting_catalog.py` that checks this if desired |

## Rollback

Reverse deploy order:
1. Revert `d1_push.py` → `docker compose restart crm`. Push payloads stop including `attributes` field. Worker still reads the column (harmless — column exists in D1, values may persist).
2. Revert Worker (`git revert` + `wrangler deploy`). Worker no longer reads `attributes` from D1 row or spreads into ScanContext. Targeting reverts to fixed columns only. Existing campaigns unaffected (they don't target dynamic fields yet).
3. D1 column: **do NOT drop `attributes` column** (D1/SQLite does not support `DROP COLUMN` reliably; data loss risk). Leave as unused nullable column. Harmless.

## Unresolved questions
1. **`schema_hug.sql` re-application safety:** should the `ALTER TABLE` be moved to a separate versioned file `schema_hug_v2_add_attributes.sql` to prevent accidental re-application? Recommended yes — avoids the "apply whole file" footgun. Implementer to decide and note in PR.
2. **`extraAttrs` overwrite guard:** should the Worker explicitly exclude known fixed-column keys from `extraAttrs` spread (preventing a malicious/buggy payload from overwriting `op_type`, `channel`, etc.)? Low risk in practice (only crm can push via HMAC-signed admin route), but a defense-in-depth filter adds < 5 lines. Implementer to decide.
3. **Current config is dormant:** for `order_code` (edge=True, in `_FIXED_D1_COLS`) and `is_gift` (edge=False), `edge_attrs` is always `{}` → `attributes=None`. Phase 4 ships "wired but dormant." Is this the intended behavior, or should we wait until there is an actual non-fixed edge field to justify the D1 migration + Worker deploy? User-confirmed: build the seam now (requirement stated "some fields WILL need edge matching"). Ship Phase 4 as specified.
