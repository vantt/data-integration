# Phase 2 — `customer_type` edge column + content-diff resync

## Context links

- Plan overview: `plans/260623-0852-hug-campaign-matching-and-preview/plan.md`
- Research source: `plans/reports/hug-campaign-targeting-criteria-expansion-260623-0852-report.md` §3b
- D1 schema: `webhook_receiver/cloudflareD1/schema_hug.sql:35–42`
- Worker upsert handler: `webhook_receiver/cloudflareD1/src/hug-handler.ts:423–473`
- ScanContext + handleHugScan: `webhook_receiver/cloudflareD1/src/hug-handler.ts:79–90`, `225–243`
- Push pipeline: `crm/src/hug/customer_push.py:127–189`
- Source mart: `transformation/models/marts/customer/mart_customer_tier.sql:65`
- Sync reader: `crm/sync/duckdb_reader.py:296–328` (selects `customer_type` at line 308 — VERIFIED)
- Cache schema: `crm/sync/cache_schema.sql:98` (`wh_customer_tier.customer_type TEXT` — VERIFIED)
- Test: `crm/src/tests/test_hug_customer_push.py`
- Test schema helper: `crm/src/tests/test_hug_customer_push.py:48–69` (must add `customer_type`)

## Overview

- **Priority:** P1
- **Status:** pending (blocked on Phase 1 deploy)
- **Worker deploy required:** YES (new column in upsert handler + ScanContext)
- **D1 schema migration:** YES (`ALTER TABLE hug_customer ADD COLUMN customer_type TEXT`)
- **Full resync required:** YES — `_content_str` signature change forces every row to re-push once

## Verified facts

- `customer_type` is already in `mart_customer_tier` (selected at `mart_customer_tier.sql:65`).
- `fetch_customer_tier` in `crm/sync/duckdb_reader.py:308` already fetches `customer_type`.
- `wh_customer_tier` in `crm/sync/cache_schema.sql:98` has `customer_type TEXT` — the column lands in `cache.db` after the next nightly reverse-ETL sync. **No mart or sync-layer changes needed.**
- `_load_tier_rows` in `customer_push.py:106–124` currently selects only `customer_id, strategic_tier, recency_days, value_group, is_contactable` — `customer_type` must be added here.
- `_build_edge_rows` in `customer_push.py:127–149` must pass `customer_type` through to the edge row dict.
- `_content_str` in `customer_push.py:183–189` currently joins 4 fields: `tier|recency_days|value_group|is_contactable`. Adding `customer_type` makes it 5 fields. **This changes the stored content string for every existing row → full resync on first run after deploy.**
- `HugCustomerRow` interface in `hug-handler.ts:415–421` does not have `customer_type` — must add it.
- `handleHugCustomerUpsert` upsert SQL at `hug-handler.ts:449–464` does not include `customer_type` — must add.
- `HugCustomer` interface at `hug-handler.ts:53–60` does not have `customer_type`.
- `ScanContext` at `hug-handler.ts:79–90` does not have `customer_type`.
- `handleHugScan` SQL at `hug-handler.ts:225–230` does not SELECT `customer_type` from `hug_customer` JOIN.
- `ScanContext` build at `hug-handler.ts:232–243` does not assign `customer_type`.
- `index.test.ts` inline schema at `index.test.ts:45–52` mirrors `hug_customer` without `customer_type` — must add.
- `customer_type` domain (from `dim_customers.sql:113–126`): `WHOLESALE`, `CROSSBORDER`, `PARTNER`, `STAFF`, `KOL`, `RETAIL`. Memory note: ~92 RETAIL-labelled Đại-Lý dealers may leak into RETAIL — acceptable for v1.
- CRM Python source is volume-mounted (`docker-compose.yml:187`) — no rebuild needed for Python-only changes. Worker deploy IS needed for TS changes.

## Requirements

### Functional
1. `customer_type` stored per customer in `hug_customer` D1 (new column, nullable).
2. `handleHugCustomerUpsert` accepts and upserts `customer_type` in each row.
3. `handleHugScan` includes `customer_type` in the JOIN SELECT and in `ScanContext`.
4. `matchesTargeting` requires no change — existing list-branch handles `customer_type` via `String()` coercion.
5. `_load_tier_rows` selects `customer_type` from `wh_customer_tier`.
6. `_build_edge_rows` passes `customer_type` through; null/missing → `None`.
7. `_content_str` includes `customer_type` as the 5th field.
8. `TARGETING_CATALOG` gains a `customer_type` entry (customer-level list attr, closed domain).
9. After deploy, a one-time `HUG_CUSTOMER_PUSH_FULL=1` resync pushes all rows with the new content string.

### Non-functional
- Deploy ordering: D1 migration BEFORE Worker deploy; Worker deploy BEFORE Python push change is activated in production. (Python push sends `customer_type: null` to old Worker = ignored; safe. But old Worker ignores the new column → D1 rows missing `customer_type` until new Worker is live.)
- `customer_type: null` must be tolerated by the Worker upsert (nullable column).
- `ScanContext` type safety: `customer_type: string | null` in TS.

## Architecture

```
Mart (mart_customer_tier) — already has customer_type (verified)
  ↓ nightly via fetch_customer_tier (already fetches it, line 308)
wh_customer_tier (cache.db) — already has customer_type TEXT column (verified)
  ↓ _load_tier_rows (customer_push.py) — ADD customer_type to SELECT
  ↓ _build_edge_rows — ADD customer_type to output dict
  ↓ _content_str — ADD customer_type to content key (triggers full resync once)
  ↓ POST /hug/customer/upsert
Worker handleHugCustomerUpsert — ADD customer_type to INSERT/UPDATE
  ↓ D1 hug_customer (ALTER TABLE — new column)
  ↓ handleHugScan JOIN SELECT — ADD customer_type
  ↓ ScanContext — ADD customer_type field
  ↓ matchesTargeting — NO CHANGE (list branch already handles it)
```

## Data flow

```
Push path:
  cache.db wh_customer_tier.customer_type (TEXT, values: WHOLESALE|CROSSBORDER|PARTNER|STAFF|KOL|RETAIL|null)
  → customer_push._load_tier_rows() → dict["customer_type"]
  → _build_edge_rows() → edge_row["customer_type"] = r["customer_type"] or None
  → _content_str() → "LIVE_CORE|3|HIGH|1|RETAIL"  (5 fields, was 4)
  → POST /hug/customer/upsert body: {"rows": [..., {"customer_type": "RETAIL", ...}]}
  → D1 hug_customer.customer_type = "RETAIL"

Scan path:
  GET /h/:token
  → SQL: SELECT t.*, c.tier, c.recency_days, c.value_group, c.is_contactable, c.customer_type
         FROM hug_token t LEFT JOIN hug_customer c ON c.customer_id = t.customer_id
         WHERE t.token = ? AND t.status = 'bound'
  → ScanContext.customer_type = row.customer_type ?? null
  → matchesTargeting: {"customer_type": {"not_in": ["WHOLESALE", "STAFF"]}} → uses list branch

Preview path (cache.db, until Phase 3):
  preview_match_customers() → ctx dict must include "customer_type": row["customer_type"]
  targeting_engine.py SELECT must add customer_type to wh_customer_tier query
```

## Files to modify

| File | Change |
|------|--------|
| `webhook_receiver/cloudflareD1/schema_hug.sql` | Add D1 migration comment + document new column; actual migration is a separate SQL file run via wrangler |
| `webhook_receiver/cloudflareD1/src/hug-handler.ts` | `HugCustomer` interface: add `customer_type: string \| null` (after line 59); `HugCustomerRow` interface: add `customer_type?: string \| null` (after line 420); `handleHugCustomerUpsert` INSERT/UPDATE SQL: add `customer_type` column + bind param (lines 449–464); `handleHugScan` SELECT: add `c.customer_type` (line 226); `ScanContext` interface: add `customer_type: string \| null` (after line 89); `ScanContext` build block: assign `customer_type: row.customer_type ?? null` (after line 242) |
| `webhook_receiver/cloudflareD1/src/index.test.ts` | Inline `hug_customer` schema (line 45–52): add `customer_type TEXT` column |
| `crm/src/hug/customer_push.py` | `_load_tier_rows` SELECT: add `customer_type` (after line 117); `_build_edge_rows`: add `customer_type: r.get("customer_type")` to output dict (after line 147); `_content_str`: extend to 5 fields including `customer_type` (line 189) |
| `crm/src/hug/targeting_catalog.py` | Add `customer_type` entry (after `value_group` entry, line 53) |
| `crm/src/hug/targeting_engine.py` | `preview_match_customers` SELECT: add `customer_type` (after line 143); `ctx` dict: add `"customer_type": row["customer_type"]` (after line 167) |
| `crm/src/tests/test_hug_customer_push.py` | `_make_cache_db` CREATE TABLE: add `customer_type TEXT` column (after line 59); all `INSERT` fixture rows: add `customer_type` field; C4 shape test: update expected keys set to include `customer_type`; new tests for customer_type passthrough |

## Files to create

| File | Purpose |
|------|---------|
| `webhook_receiver/cloudflareD1/migrations/add_hug_customer_type_column.sql` | `ALTER TABLE hug_customer ADD COLUMN customer_type TEXT;` — applied via `wrangler d1 execute` before Worker deploy |

## Implementation steps

### Step 1 — Create D1 migration file

Create `webhook_receiver/cloudflareD1/migrations/add_hug_customer_type_column.sql`:

```sql
-- Add customer_type to hug_customer to enable B2B vs retail targeting.
-- Values mirror mart_customer_tier.customer_type: WHOLESALE / CROSSBORDER /
-- PARTNER / STAFF / KOL / RETAIL. NULL = not yet pushed (legacy rows).
-- Run via: wrangler d1 execute fgcare-webhook-db --remote --file=<this file>
-- MUST run before deploying the Worker build that reads this column.
ALTER TABLE hug_customer ADD COLUMN customer_type TEXT;
```

### Step 2 — Update TS `HugCustomer`, `HugCustomerRow`, `ScanContext` interfaces (`hug-handler.ts`)

Three interface additions (all additive, no existing field removed):

- `HugCustomer` (line 53): add `customer_type: string | null;`
- `HugCustomerRow` (line 415): add `customer_type?: string | null;`
- `ScanContext` (line 79): add `customer_type: string | null;`

### Step 3 — Update `handleHugCustomerUpsert` SQL (`hug-handler.ts:449–464`)

Current INSERT columns: `customer_id, tier, recency_days, value_group, is_contactable, updated_at` (6 fields). Extend to 7:

```sql
INSERT INTO hug_customer (customer_id, tier, recency_days, value_group, is_contactable, customer_type, updated_at)
VALUES (?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
ON CONFLICT(customer_id) DO UPDATE SET
  tier           = excluded.tier,
  recency_days   = excluded.recency_days,
  value_group    = excluded.value_group,
  is_contactable = excluded.is_contactable,
  customer_type  = excluded.customer_type,
  updated_at     = excluded.updated_at
```

Bind param order: `r.customer_id, r.tier ?? null, r.recency_days ?? null, r.value_group ?? null, r.is_contactable ?? 0, r.customer_type ?? null`.

### Step 4 — Update `handleHugScan` SELECT and `ScanContext` build (`hug-handler.ts:225–243`)

SQL: add `c.customer_type` to the SELECT list (line 226).

ScanContext build block: add `customer_type: row.customer_type ?? null` after `sku` assignment (after line 242).

### Step 5 — Update `handleHugScan` JSDoc (`hug-handler.ts:132–145`)

Add `customer_type string → in list` to the supported attributes table in the JSDoc.

### Step 6 — Run D1 migration THEN deploy Worker

```bash
# 1. Apply schema migration to remote D1
wrangler d1 execute fgcare-webhook-db --remote \
  --file=webhook_receiver/cloudflareD1/migrations/add_hug_customer_type_column.sql

# 2. Deploy Worker (now reads the new column)
cd webhook_receiver/cloudflareD1 && wrangler deploy
```

**Ordering is critical.** If Worker is deployed before the migration, the INSERT will fail with "table hug_customer has no column named customer_type".

### Step 7 — Update Python push pipeline (`customer_push.py`)

`_load_tier_rows` SELECT — add `customer_type` to column list (after `is_contactable`, before `FROM`):

```sql
SELECT customer_id,
       strategic_tier,
       recency_days,
       value_group,
       is_contactable,
       customer_type
FROM   wh_customer_tier
WHERE  customer_id IS NOT NULL
```

`_build_edge_rows` — add to output dict:

```python
out.append({
    "customer_id":    cid,
    "tier":           r["strategic_tier"] or "UNKNOWN",
    "recency_days":   int(r["recency_days"] or 0),
    "value_group":    r["value_group"] or "UNKNOWN",
    "is_contactable": 1 if (wh_contactable or crm_contactable_flag) else 0,
    "customer_type":  r.get("customer_type"),   # None if not set in mart
})
```

`_content_str` — extend to 5 fields:

```python
def _content_str(row: dict[str, Any]) -> str:
    """Pipe-join the 5 edge-pushed fields into a stable comparison key.

    Field order must never change after rollout — changing it invalidates all
    stored content strings and triggers a full resync. customer_type added as
    the 5th field; prior 4-field strings are shorter, so all existing stored
    values will differ from new 5-field strings on first run → full resync.
    This is intentional and expected; run with HUG_CUSTOMER_PUSH_FULL=1 after deploy.
    """
    return (
        f"{row['tier']}|{row['recency_days']}|{row['value_group']}"
        f"|{row['is_contactable']}|{row.get('customer_type') or ''}"
    )
```

The stored 4-field strings (`"LIVE_CORE|3|HIGH|1"`) will never match new 5-field strings (`"LIVE_CORE|3|HIGH|1|RETAIL"`) → all rows detected as changed → one full push on first run. This is the designed recovery mechanism (`force` / `HUG_CUSTOMER_PUSH_FULL=1` is equivalent but not needed here since the diff naturally triggers it).

### Step 8 — Add `customer_type` to `TARGETING_CATALOG` (`targeting_catalog.py`)

Insert after the `value_group` entry (line 53):

```python
"customer_type": {
    "type": "list",
    "description": "Loại khách hàng (B2B vs bán lẻ)",
    "values": ["WHOLESALE", "CROSSBORDER", "PARTNER", "STAFF", "KOL", "RETAIL"],
    # customer_level: present in hug_customer → countable in D1 preview (Phase 3).
},
```

No `touchpoint_level` key → defaults to False (customer-level). This means Phase 3 D1 preview will count it exactly.

### Step 9 — Update `preview_match_customers` in `targeting_engine.py`

Add `customer_type` to:
1. The SQL SELECT (after `is_contactable`, before `FROM wh_customer_tier`).
2. The `ctx` dict build (after `is_contactable` assignment, line 167):
   ```python
   "customer_type": row["customer_type"],
   ```

This enables `{"customer_type": {"not_in": ["WHOLESALE"]}}` to work in the cache.db preview path as well, before Phase 3 is deployed.

### Step 10 — Full resync after deploy

Trigger once after Steps 6 + 7 are live:

```bash
# Option A: via env var on nightly refresh
HUG_CUSTOMER_PUSH_FULL=1 <trigger admin refresh>

# Option B: direct Python call (inside crm container)
python -c "from hug.customer_push import run; run(force=True)"
```

This pushes all ~7.5k rows with 5-field content strings to D1. Subsequent runs revert to incremental (only changed rows).

### Step 11 — Update tests (`test_hug_customer_push.py`)

Changes required:
1. `_make_cache_db` CREATE TABLE: add `customer_type TEXT` to the schema (after `is_contactable INTEGER`, line 59).
2. All seed fixture dicts (`_ROW_1`, `_ROW_2`): add `"customer_type": "LIVE_CORE_TIER"` or appropriate value — but note `_ROW_1` uses `"strategic_tier": "LIVE_CORE"` which is the tier, not customer_type. Add `"customer_type": "RETAIL"` to both.
3. `INSERT` statement in `_make_cache_db` (line 63–65): add `customer_type` to column list and `:customer_type` to values.
4. C4 shape test (`test_edge_row_shape_matches_contract`, line 184–193): update expected keys set: `{"customer_id", "tier", "recency_days", "value_group", "is_contactable", "customer_type"}`.
5. C5 body test (line 251–252): update `set(row.keys())` to include `customer_type`.
6. D1 content string test (line 334): update `"LIVE_CORE|3|VIP|1"` → `"LIVE_CORE|3|VIP|1|RETAIL"`.
7. D3 content string assertions (line 384): update both expected strings.

New tests:
- `test_customer_type_passed_through_to_edge_row` — verify `customer_type` in edge row dict matches mart value.
- `test_customer_type_none_when_missing_from_mart` — row with no `customer_type` produces `None` in edge row (not an error).
- `test_content_str_includes_customer_type` — direct unit test on `_content_str` output format.

## Test matrix

| Layer | Tool | Scope |
|-------|------|-------|
| TS upsert handler | vitest (index.test.ts) | `handleHugCustomerUpsert` accepts + stores `customer_type`; `handleHugScan` returns `customer_type` in context |
| Python push unit | pytest (test_hug_customer_push.py) | _build_edge_rows passthrough; _content_str 5-field format; C4/C5 shape; D1/D3 content string assertions |
| Python preview | pytest (test_hug_targeting_engine.py) | preview_match_customers with `customer_type` in ctx and targeting |
| Full resync E2E | manual trigger + log inspection | `HUG_CUSTOMER_PUSH_FULL=1` → total=7543, ok=7543 in push log |

## Success criteria

- `wrangler d1 execute` migration runs without error (idempotent `ADD COLUMN` — safe to re-run on SQLite's `ALTER TABLE`).
- Worker deploy succeeds; `handleHugCustomerUpsert` stores `customer_type`; scan context includes `customer_type`.
- After full resync: `hug_customer` rows have `customer_type` populated for all customers with mart data.
- `{"customer_type": {"not_in": ["WHOLESALE", "STAFF"]}}` correctly routes scan events (manual QA: scan a known WHOLESALE customer token → should NOT match a campaign with this rule).
- All existing D1–D7 push tests pass with updated fixture schema.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Worker deploy before D1 migration: INSERT fails for all push rows | High (if order skipped) | High — push entirely broken until migration applied | Enforce order via step checklist; document in deploy notes; test migration first in a local D1 dev environment |
| Full resync overwrites D1 rows during a concurrent scan burst (TOCTOU on D1 upsert) | Low | Low — D1 upsert is idempotent; worst case is a stale read between upsert batches (~1s window) | Acceptable; D1 batch upsert is atomic per batch |
| `wh_customer_tier.customer_type` null for some customers (e.g. very old accounts not in dim_customers) | Medium | Low — targeting `customer_type not_in [...]` will treat null as "not in excluded list" (True) | Document in catalog entry; null means "not classified" = included in non-exclusion rules |
| `_content_str` field order change in future breaks stored content strings silently | Low | Medium — triggers spurious full resync | Document field order as locked in `_content_str` docstring; add a unit test asserting the exact format |

## Rollback

- **D1 migration:** SQLite's `ALTER TABLE ADD COLUMN` cannot be rolled back natively. Mitigation: the new column is nullable; if Worker is reverted to a build that doesn't use it, the column is silently ignored (no breakage). No data is lost.
- **Worker:** redeploy previous Worker build. Column in D1 stays but is unused.
- **Python push:** revert `_content_str` to 4-field format + remove `customer_type` from SELECT/build. On next run the stored 5-field strings won't match 4-field strings → another full resync (acceptable).
- **Catalog entry:** remove `customer_type` from `targeting_catalog.py`. Existing campaigns using `customer_type` targeting will error on next validate; warn user before removing.

## Unresolved questions

1. **Null `customer_type` semantics in `not_in` rule:** chosen to treat null as "passes the not_in check" (not excluded). Confirm this is the desired behavior — alternative is null → excluded (fails).
2. **`wh_customer_tier.customer_type` coverage:** confirmed the column exists in the cache schema and is fetched by `fetch_customer_tier`. However, the column is populated from `dim_customers` and the mart note says ~92 RETAIL-labelled dealer accounts exist. No action needed for v1 — flag for monitoring.
3. **Migration naming convention:** the `migrations/` directory doesn't appear to exist yet in `webhook_receiver/cloudflareD1/`. Verify if there's a convention for tracking applied migrations, or if the file is just run once and discarded.
