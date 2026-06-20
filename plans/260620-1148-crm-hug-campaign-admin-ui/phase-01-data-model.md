# Phase 1 — Data Model: crm.db Migration + Repository

## Context Links
- Edge schema: `webhook_receiver/cloudflareD1/schema_hug.sql` (hug_campaign columns, authoritative)
- Existing migration pattern: `crm/migrations/0023_identity_link_rejected_status.up.sql`
- Migration runner: `crm/src/adapters/outbound/sqlite/migrations.py` — reads `crm/migrations/*.up.sql` in numeric order
- Next migration number: **0024** (latest is 0023)

## Overview
- **Priority:** P1 blocker (all phases depend on this)
- **Status:** pending
- **Goal:** Add `crm_hug_campaign` (authoring source of truth) + `crm_hug_campaign_history` (lightweight versioning) to crm.db. Add a thin repository module for CRUD.

## Key Insights
- crm.db is the right host (not hug.db). hug.db owns the token lifecycle; crm.db owns CRM authoring state. Pattern matches existing CRM tables (segments, campaigns).
- Edge `hug_campaign` columns must be mirrored exactly: `campaign_id, name, targeting, destination_type, destination_url, offer_ref, priority, schedule_start, schedule_end, quota_total, status`. We add `created_at` and do NOT mirror `quota_used` (edge-only counter).
- `crm_hug_campaign_history` is a simple append-only snapshot table (JSON blob of the whole row + ts). No FK enforcement needed — history can outlive a deleted row.
- The repository must be pure data-access (no HTTP, no push). Push lives in Phase 2.

## Requirements

### Functional
- `crm_hug_campaign`: full CRUD (list, get, upsert, soft-delete via status='archived').
- `crm_hug_campaign_history`: insert snapshot on every save (create or update).
- `list_campaigns()`: returns rows ordered by priority ASC, supports optional status filter.
- `get_campaign(campaign_id)`: single row or None.
- `upsert_campaign(row_dict)`: INSERT OR REPLACE + snapshot. Returns saved row.
- `list_history(campaign_id, limit=20)`: recent snapshots for rollback UI.
- `restore_from_snapshot(campaign_id, snapshot_id)`: write snapshot back as current row + new snapshot.
- `suggest_next_priority()`: SELECT MAX(priority)+10 or 10 if empty (soft unique helper).

### Non-Functional
- Repository module ≤ 200 lines. Split SQL strings to a `_queries` sibling if needed.
- FastAPI-free (no imports from `fastapi`) — tests call the module directly.
- Thread-safe for the single crm.db connection (conn passed in, no global state).

## Architecture

```
crm/migrations/
  0024_hug_campaign_authoring.up.sql    ← CREATE TABLE crm_hug_campaign + history
  0024_hug_campaign_authoring.down.sql  ← DROP both tables

crm/src/hug/
  campaign_repository.py               ← CRUD + history helpers (NEW)
```

**Data flow:**
```
Admin UI (Phase 4)
  → campaign_repository.upsert_campaign(row)
    → INSERT/UPDATE crm_hug_campaign
    → INSERT crm_hug_campaign_history (snapshot)
  → campaign_push.run_push(campaign_id)   [Phase 2]
    → POST /hug/campaign/upsert → Worker D1
```

## Related Code Files

**Create:**
- `crm/migrations/0024_hug_campaign_authoring.up.sql`
- `crm/migrations/0024_hug_campaign_authoring.down.sql`
- `crm/src/hug/campaign_repository.py`

**Modify (Phase 4 wires it):**
- `crm/src/composition.py` — pass `conn` to hug campaign router

## Implementation Steps

1. Write `0024_hug_campaign_authoring.up.sql`:
   ```sql
   CREATE TABLE IF NOT EXISTS crm_hug_campaign (
       campaign_id      TEXT PRIMARY KEY,
       name             TEXT NOT NULL,
       targeting        TEXT NOT NULL DEFAULT '{}',
       destination_type TEXT NOT NULL CHECK (destination_type IN ('zalo_oa','cf_pages','url')),
       destination_url  TEXT NOT NULL,
       offer_ref        TEXT,
       priority         INTEGER NOT NULL DEFAULT 100,
       schedule_start   TEXT,
       schedule_end     TEXT,
       quota_total      INTEGER,
       status           TEXT NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active','paused','archived')),
       created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
       updated_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
   );
   CREATE INDEX IF NOT EXISTS idx_crm_hug_campaign_status_priority
       ON crm_hug_campaign(status, priority);

   CREATE TABLE IF NOT EXISTS crm_hug_campaign_history (
       id           INTEGER PRIMARY KEY AUTOINCREMENT,
       campaign_id  TEXT NOT NULL,
       snapshot     TEXT NOT NULL,   -- JSON of full crm_hug_campaign row at save time
       saved_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
   );
   CREATE INDEX IF NOT EXISTS idx_hug_campaign_history_campaign
       ON crm_hug_campaign_history(campaign_id, saved_at DESC);
   ```

2. Write `0024_hug_campaign_authoring.down.sql` (DROP both tables, DROP indexes).

3. Write `crm/src/hug/campaign_repository.py` with functions:
   - `list_campaigns(conn, status=None) → list[sqlite3.Row]`
   - `get_campaign(conn, campaign_id) → sqlite3.Row | None`
   - `upsert_campaign(conn, row: dict) → sqlite3.Row` — validates required fields, sets `updated_at`, inserts history snapshot
   - `archive_campaign(conn, campaign_id) → None` — sets status='archived' + snapshot
   - `list_history(conn, campaign_id, limit=20) → list[sqlite3.Row]`
   - `restore_snapshot(conn, campaign_id, snapshot_id) → sqlite3.Row`
   - `suggest_next_priority(conn) → int`

4. Verify migration runner picks up the new file: `migrations.py:_migration_files()` globs `*.up.sql` sorted numerically — confirmed, no changes needed.

## Todo

- [ ] Write migration UP SQL
- [ ] Write migration DOWN SQL
- [ ] Write `campaign_repository.py` (≤200 lines)
- [ ] Write unit tests: `crm/tests/hug/test_campaign_repository.py` — test upsert, list, history snapshot, restore, suggest_priority using an in-memory SQLite conn with the migration SQL applied

## Success Criteria

- Migration applies cleanly via `CRMDatabase.apply_migrations()` on startup (no error).
- `upsert_campaign` round-trips: saved row matches input fields.
- `list_history` returns a snapshot after every upsert.
- `restore_snapshot` restores prior targeting and creates a new history row.
- All unit tests pass without running the FastAPI app.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Migration number collision (0024 already taken) | Low | Low | Verify glob of `crm/migrations/` before writing; bump to 0025 if needed |
| `targeting` CHECK constraint — SQLite doesn't enforce JSON shape | Low | Low | Validation lives in Phase 3 predicate engine; DB stores raw TEXT |
| `updated_at` not auto-refreshed on UPDATE | Medium | Medium | SET `updated_at=strftime(...)` explicitly in `upsert_campaign` SQL |

## Security Considerations
- `campaign_id` is admin-supplied; sanitise (alphanumeric + hyphen/underscore only) in repository before INSERT to prevent injection via parameterised queries (already safe via `?` binding, but reject obviously malformed IDs early).
- `targeting` JSON is stored as TEXT and validated by Phase 3 before save.

## Next Steps
- Phase 2 (campaign_push.py) can start immediately after migration is applied.
- Phase 3 (predicate engine) is independent and can start in parallel.
