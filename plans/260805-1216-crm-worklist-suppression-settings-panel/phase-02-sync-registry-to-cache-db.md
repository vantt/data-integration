# Phase 02 — Sync the registry into `cache.db`

**Priority:** P2 · **Status:** pending · **Effort:** 2h · **Blocked by:** Phase 01
**File ownership:** `crm/sync/**` only.

## Context

- Reverse-ETL entry: `crm/sync/reverse_etl_warehouse_to_crm.py`
- Reader: `crm/sync/duckdb_reader.py` — opens `olap.duckdb` read-only (`:206`), falls back to
  `sapo_export_latest.duckdb` (`:211-221`), all reads from schema `main_marts`.
- Writer: `crm/sync/sqlite_upsert.py` — `apply_schema()` executes `cache_schema.sql` (`:62`),
  generic `_upsert()` at `:149-179`.
- DDL: `crm/sync/cache_schema.sql`.
- Triggered by Dagster asset `crm_cache_refresh` (`orchestration/assets/crm_sync.py:25-96`) →
  `POST /admin/refresh` → `crm/src/adapters/inbound/http/admin_handler.py:274-306`.

## Key insights

1. **No declarative table registry.** Every synced table is hand-coded across exactly 4 files.
   Adding one costs 4 edits; there is no shortcut and inventing one is out of scope (YAGNI).
2. **`cache.db` is never wiped.** `apply_schema()` is `CREATE TABLE IF NOT EXISTS` + `ALTER` migrations
   (`sqlite_upsert.py:47-145`); rows are replaced in place. So a new table appears on the next sync
   without touching existing data.
3. **Fail-fast on drift is the house pattern** — `duckdb_reader._check_columns()` (`:254`) raises if the
   upstream model lost a column. Reuse it; do not silently degrade.
4. **No dbt seed has ever been synced.** This is the first. Phase 01 makes it look like a normal mart
   so this phase stays on the beaten path.

## Requirements

**Functional**
1. `cache.wh_action_scenario_registry` exists with `(action_type, mart)` PK and columns
   `enabled`, `scenario_group`, `description_vi`.
2. Full-replace semantics (13-row reference table; incremental is pointless).
3. Sync failure must not abort the rest of the reverse-ETL run — degrade to "catalog stale", matching
   the guarded pattern of `upsert_deadstock_target` (`sqlite_upsert.py:379-423`).

**Non-functional**
4. `enabled` stored as INTEGER 0/1 (SQLite has no BOOLEAN).
5. Table lives in `cache.db`, prefix `wh_` per `crm/AGENTS.md` §Conventions.

## Architecture / data flow

```
olap.duckdb main_marts.dim_action_scenario_registry
  → duckdb_reader.fetch_action_scenario_registry()   [+ _check_columns fail-fast]
  → reverse_etl_warehouse_to_crm._run_step(...)
  → sqlite_upsert.upsert_action_scenario_registry()  [DELETE + INSERT, guarded on non-empty]
  → cache.db  wh_action_scenario_registry
  → (Phase 04) SQLiteActionCatalogRepository reads it via the ATTACHed `cache.` schema
```

## Related code files

**Modify**
- `crm/sync/cache_schema.sql` — add `CREATE TABLE IF NOT EXISTS wh_action_scenario_registry`.
- `crm/sync/duckdb_reader.py` — add `_MART_ACTION_SCENARIO_REGISTRY_COLS` + `fetch_action_scenario_registry()`.
- `crm/sync/sqlite_upsert.py` — add `upsert_action_scenario_registry()`.
- `crm/sync/reverse_etl_warehouse_to_crm.py` — fetch + `_run_step` wiring.

**Create** — none. **Delete** — none.

## Implementation steps

1. `cache_schema.sql`, appended in the existing style:
   ```sql
   CREATE TABLE IF NOT EXISTS wh_action_scenario_registry (
     action_type     TEXT    NOT NULL,
     mart            TEXT    NOT NULL,
     enabled         INTEGER NOT NULL DEFAULT 1,
     scenario_group  TEXT    NOT NULL DEFAULT '',
     description_vi  TEXT    NOT NULL DEFAULT '',
     PRIMARY KEY (action_type, mart)
   );
   ```
2. `duckdb_reader.py` — declare the pinned column tuple next to the other `_MART_*_COLS` constants,
   then mirror `fetch_customer_tier()` (`:394-428`):
   ```python
   def fetch_action_scenario_registry(conn) -> list[dict]:
       """Read the opportunity-type catalog from main_marts.dim_action_scenario_registry."""
       cols = ", ".join(_MART_ACTION_SCENARIO_REGISTRY_COLS)
       rows = _fetch(conn, f"SELECT {cols} FROM main_marts.dim_action_scenario_registry")
       _check_columns(rows, _MART_ACTION_SCENARIO_REGISTRY_COLS,
                      "main_marts.dim_action_scenario_registry")
       return rows
   ```
3. `sqlite_upsert.py` — full-replace guarded on non-empty input, same shape as
   `upsert_deadstock_target` (`:379-423`): if `rows` is empty, log a warning and return without
   deleting (never blank out a working catalog because a dbt run half-failed). Cast `enabled` to
   `int(bool(...))` explicitly — DuckDB returns Python `bool`.
4. `reverse_etl_warehouse_to_crm.py` — add the fetch next to the other `dr.fetch_*` calls
   (~`:161-169`) and the `_run_step(..., su.upsert_action_scenario_registry, registry_rows)`
   alongside the other steps (~`:174-201`). Place it FIRST among the steps: it is tiny, and a hard
   failure there is a clear signal that Phase 01 was not deployed.
5. Add a sync unit test in `crm/sync/tests/` mirroring the existing test style there: feed 13 fake
   dicts → assert 13 rows in a temp `cache.db`; feed `[]` → assert prior rows survive.
6. Run the reverse-ETL locally against the dev warehouse and verify:
   `sqlite3 crm/data/cache.db "SELECT mart, COUNT(*) FROM wh_action_scenario_registry GROUP BY 1"`
   → 6 sku + 7 customer.

## Todo list

- [x] `cache_schema.sql` table
- [x] `duckdb_reader.fetch_action_scenario_registry()` + pinned column tuple
- [x] `sqlite_upsert.upsert_action_scenario_registry()` (guarded full-replace)
- [x] `reverse_etl_warehouse_to_crm.py` wiring (first step, wrapped fetch — `_run_step` does NOT isolate failures, confirmed by reading it; fetch itself wrapped separately)
- [x] Sync unit test (happy + empty-input guard: T7; column-drift: T8) — both pass
- [x] Manual reverse-ETL run verified — 13 rows, 7 customer / 6 sku split, GIFT_TO_PURCHASE enabled=0

## Success criteria

- After one reverse-ETL run, `cache.wh_action_scenario_registry` has 13 rows,
  `GIFT_TO_PURCHASE` has `enabled = 0`.
- Re-running the sync is idempotent (still 13 rows, no duplicates).
- An empty fetch leaves the previous catalog intact and logs a warning.
- All other synced tables unaffected (row counts unchanged before/after).

## Risk assessment

| Risk | L×I | Mitigation |
|---|---|---|
| Phase 01 not deployed → `main_marts.dim_action_scenario_registry` missing → whole reverse-ETL aborts | Med×High | Step 4 makes it the first step so the failure is unambiguous; `_run_step` already isolates step failures — confirm that when wiring, and if it does not, wrap in try/except that logs and continues |
| Fresh env: CRM app starts before any sync → empty catalog | High×Med | Phase 06 renders an explicit "Danh mục gợi ý chưa đồng bộ" empty state, never a hardcoded fallback list |
| `enabled` arrives as Python `bool` → stored as `b'\x01'` or `'True'` | Med×Med | Explicit `int(bool(...))` cast in step 3 + assertion in the unit test |
| Someone edits the seed but never re-runs `dbt seed` → CRM catalog stale | Med×Low | Accepted. Catalog changes are rare and already require a dbt run today for the marts to honour `enabled` |

## Rollback

Revert the 4 files. `wh_action_scenario_registry` can be left in `cache.db` (orphan table, harmless)
or dropped manually. No CRM read path depends on it until Phase 06.

## Security considerations

Reference data only. `cache.db` is ATTACHed read-only by the app (`connection.py:70-74`), so the app
can never mutate the catalog — only the sync process writes it. Correct blast radius.

## Next steps

Unblocks Phase 06 (panel reads the catalog). Independent of Phases 03-05.
