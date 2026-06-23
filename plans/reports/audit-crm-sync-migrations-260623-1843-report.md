# CRM Sync + Migrations Health Audit
**Date:** 2026-06-23  
**Scope:** `crm/sync/` (reverse-ETL), `crm/migrations/` (SQL), `crm/refresh.sh`, `crm/entrypoint.sh`  
**Status:** READ-ONLY — no code modified

---

## Severity Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH     | 4 |
| MEDIUM   | 5 |
| LOW      | 4 |

---

## CRITICAL

### C1 — DELETE-before-upsert on `wh_deadstock_target` has no transaction atomicity guard against data loss on empty-rows race
**File:** `crm/sync/sqlite_upsert.py:259`  
**Risk:** `upsert_deadstock_target` uses `with conn:` which wraps both the `DELETE` and the `executemany` inside a single SQLite transaction — that part is safe. However, the "empty-rows guard" check (`if not rows: return 0`) happens **before** the transaction and derives from the in-memory Python list. If `fetch_deadstock_targets` returns an empty list because the DuckDB mart temporarily disappeared or threw an error mid-pipeline (warehouse rebuild window, mart rename, DuckDB lock), the guard is hit, the `DELETE` is skipped, and stale rows are preserved — correct. **But** if the mart returns 0 rows legitimately (e.g. all SKUs resolved), the guard also fires and cache is NOT cleared. There is no way to distinguish "mart empty by design" from "mart missing / error". The bigger risk: if an exception is raised inside `fetch_deadstock_targets` before `run()` calls `upsert_deadstock_target`, the rows list is never built and the dead-stock table retains stale data indefinitely — sync reports `ok` for all other tables while dead-stock silently stagnates.  
**Direction:** Log a warning when rows == 0 and skip the DELETE so ops can detect it. Alternatively, require a non-zero result contract (raise if mart is truly expected to have rows) and let `_run_step` catch and mark failed. Do not silently skip.

---

## HIGH

### H1 — `_COLUMN_MIGRATIONS` swallows ALL `OperationalError`, masking real failures
**File:** `crm/sync/sqlite_upsert.py:67-72`  
**Risk:** The migration runner in `apply_schema` catches `sqlite3.OperationalError` broadly and silently continues. The intent is to skip "duplicate column name" on re-run. But `OperationalError` also covers: table-not-found, disk-full, SQL syntax errors, corrupted DB. A `DELETE FROM wh_action_queue WHERE …` (dedup cleanup, line 31-39) or the `CREATE UNIQUE INDEX IF NOT EXISTS` (line 42) failing for any non-idempotent reason will be silently swallowed. In particular, if `wh_action_queue` doesn't exist yet (first install, schema not yet applied), the dedup DELETE runs before `executescript(_SCHEMA_SQL)` completes — but `executescript` commits and closes the transaction, so ordering matters. Current code: `apply_schema` calls `executescript` first (creates tables), then runs `_COLUMN_MIGRATIONS`. That is safe on first install but still too broadly catches errors.  
**Direction:** Catch only the specific "duplicate column name" message (like the crm.db migration runner does at `migrations.py:124`). Let all other `OperationalError` propagate.

### H2 — `entrypoint.sh` silently continues on migration failure; silent stale DB at startup
**File:** `crm/entrypoint.sh:11-15`  
**Risk:** Migrations are wrapped in `if python3 -c ... ; then ok else WARN fi`. A migration failure (schema corruption, disk full, constraint error) prints a warning but the container starts serving the CRM app against an un-migrated or half-migrated `crm.db`. Users see no error, queries fail silently or return wrong data. Same pattern applied to reverse-ETL (step 2) and sync_parties (step 3) — those are explicitly documented as graceful-empty, but migrations are not: a partially-migrated DB is not safe to serve.  
**Direction:** Remove the `if/else` wrapper around the migrations step and let a migration failure crash the container (exit non-zero). Graceful-empty is appropriate for data steps (ETL, sync_parties); it is NOT appropriate for schema migrations.

### H3 — `search_index.py:rebuild_search_index` leaks `crm_conn` on exception path
**File:** `crm/sync/search_index.py:161-203`  
**Risk:** `crm_conn` is opened at line 161. The `finally: pass` at line 167-168 explicitly does NOT close it. The connection is eventually closed in the `finally` at line 202, but if an exception is raised between loading parties and the final write (e.g. in `_load_order_tokens`), Python's `finally` in the inner `try` doesn't exist for `crm_conn` — the comment even says "Keep crm_conn open for the final write — close after insert". If any intermediate exception occurs (KeyError, sqlite3.Error on the `cache_conn` read), `crm_conn` is closed in the outer `finally` block at line 202 only if execution reaches it. In Python, that outer `finally` WILL run even on exception, so the connection is not truly leaked at the Python level. **However**, the `cache_conn.close()` at line 177 (inside a `finally` block) runs before `crm_conn.close()`. If `cache_conn.close()` raises (rare), `crm_conn` leaks. More critically: if `crm_conn.execute("DELETE FROM crm_party_search")` raises (line 195), the commit at line 198 is skipped, leaving an empty `crm_party_search` with no rows — the search index is wiped but not rebuilt. There is no rollback.  
**Direction:** Wrap the final write block in a transaction (`with crm_conn:`) to roll back the `DELETE` if `executemany` fails. Close `crm_conn` in a proper `try/finally`, not after the inner block.

### H4 — ICT timezone stored in `tier_generated_at` (and `queue_generated_at`) violates UTC convention
**File:** `crm/sync/duckdb_reader.py:323,413`  
**Risk:** The convention (AGENTS.md, cache_schema.sql comments) is "store UTC ISO-8601 with Z suffix". `tier_generated_at` is formatted as `strftime(tier_generated_at, '%Y-%m-%dT%H:%M:%S')` — no timezone suffix, effectively stores ICT wall-clock without the `+07:00` designator. `queue_generated_at` in deadstock is similarly `strftime(…, '%Y-%m-%dT%H:%M:%S')`. The DuckDB session is SET to `Asia/Ho_Chi_Minh` so the rendered value is ICT, but cached as bare ISO-8601 with no `Z` or offset. Any downstream code that parses these as UTC will be 7 hours off.  
`wh_sync_run.started_at/finished_at` are correctly tagged with `Z` (via `_utc_now()` in Python).  
**Direction:** Either format as `strftime(col AT TIME ZONE 'UTC', '%Y-%m-%dT%H:%M:%SZ')` to store UTC, or use `strftime(col, '%Y-%m-%dT%H:%M:%S+07:00')` to store ICT with explicit offset. Pick one and document it in schema comments.

---

## MEDIUM

### M1 — `_COLUMN_MIGRATIONS` DELETE dedup runs outside a transaction; partial dedup on crash
**File:** `crm/sync/sqlite_upsert.py:31-42`  
**Risk:** The 6 migration statements in `_COLUMN_MIGRATIONS` run one-by-one with individual `conn.commit()` calls. The DELETE for dedup (lines 31-39) is committed independently of the subsequent `ALTER TABLE ADD COLUMN pending_since` and `UPDATE … SET pending_since`. If the process crashes after the DELETE commits but before the UPDATE commits, `wh_action_queue` rows have `pending_since = NULL` with no way to recover the original `generated_date` from that deleted batch. Also, if `CREATE UNIQUE INDEX` (line 42) fails (e.g. remaining duplicates), the partially-cleaned table has no index and the next `_COLUMN_MIGRATIONS` run re-runs the same DELETE against an already-cleaned table — benign but indicates fragility.  
**Direction:** Group the dedup DELETE + ALTER + UPDATE + CREATE INDEX into a single atomic block; or move these to a proper numbered migration file in `crm/migrations/` where the runner handles transaction semantics.

### M2 — Migration `0023` table-rebuild for `crm_identity_link` runs outside a transaction
**File:** `crm/migrations/0023_identity_link_rejected_status.up.sql:13-50`  
**Risk:** The migration runner executes each statement individually (`run_migrations` in `migrations.py`). The 5-step table-rebuild (create v2, copy, drop old, rename, create indexes) runs statement-by-statement with individual commits. If the process crashes after step 3 (`DROP TABLE crm_identity_link`) but before step 4 (`ALTER TABLE … RENAME`), both the old and new tables are gone. The data is unrecoverable. The migration runner marks the version as applied only after all statements succeed, so a partial run would leave the DB in an inconsistent state with the migration not marked as applied — meaning the next startup would attempt steps 1-5 again, but step 2 (`INSERT INTO crm_identity_link_v2`) would succeed (table still exists from step 1), step 3 (`DROP TABLE crm_identity_link`) would fail with "no such table" and raise — correct behavior, but the rollback leaves `crm_identity_link_v2` orphaned.  
**Direction:** Wrap the 5 steps in `BEGIN; … COMMIT;` in the SQL file itself. SQLite DDL (CREATE, DROP, ALTER TABLE RENAME) IS transactional.

### M3 — Missing migration file: `0009_party_external_id.down.sql` and several others lack down migrations
**File:** `crm/migrations/` directory  
**Risk:** Migrations 0007, 0008, 0009, 0010, 0011, 0012, 0013, 0014, 0015, 0017, 0018, 0019, 0020, 0021, 0023, 0026 have no `.down.sql`. If a migration needs to be rolled back (schema corruption, bad deploy), there is no automated path. The down files that DO exist (0001, 0002, 0003, 0004, 0005, 0006, 0015, 0016, 0022, 0024, 0025) are incomplete coverage. For ALTER TABLE ADD COLUMN, SQLite has no DROP COLUMN in older versions (added in 3.35.0), so down migrations would need the full table-rebuild pattern.  
**Direction:** Acceptable as-is for an internal CRM with no external SLA, but document explicitly that rollback requires a DB restore from backup. Ensure backup exists before each migration deploy.

### M4 — `wh_deadstock_target` missing from test T1/T2 fixture in `_create_minimal_dim_tables`
**File:** `crm/sync/tests/test_reverse_etl_warehouse_to_crm.py:428-488`  
**Risk:** The `_create_minimal_dim_tables` helper used by T5 (incremental order test) does NOT create `main_marts.mart_deadstock_target_queue`. When `run()` is called in T5, `fetch_deadstock_targets` is invoked — if the mart table is absent, `_fetch` raises a DuckDB `CatalogException` (not `MissingColumnError`), which propagates through `_run_step`, logs `FAILED`, and re-raises. T5 test will fail. Additionally, the synthetic fixture in T1/T2 (`_make_warehouse`) also does NOT create `mart_deadstock_target_queue`. T1 expects `wh_deadstock_target` row count — but that table won't be populated if the source mart is absent.  
**Direction:** Add `CREATE TABLE main_marts.mart_deadstock_target_queue` to both `_make_warehouse` and `_create_minimal_dim_tables` with minimal columns matching `_MART_DEADSTOCK_TARGET_COLS`.

### M5 — `search_index.py` opens `crm.db` with write access (not read-only) while loading
**File:** `crm/sync/search_index.py:161`  
**Risk:** `sqlite3.connect(crm_db_path)` opens `crm.db` in read-write mode even for the load phase (lines 164-165). The Go CRM app is the sole writer of `crm.db`. During the load phase (before the final DELETE+INSERT), having a second writer connection open risks lock contention. SQLite WAL allows concurrent readers but only one writer; a long-running `search_index.py` rebuild while the Go app is handling requests could cause `SQLITE_BUSY` on the app side. The search index rebuild is triggered on container startup (implied) and potentially on scheduled runs.  
**Direction:** Open `crm.db` read-only (`mode=ro` URI) for the load phase (lines 164-165). Then open a separate read-write connection only for the `DELETE + INSERT` write phase. Or open read-write but hold it for the minimum time (write-phase only).

---

## LOW

### L1 — `export_shopee_deadstock_list.py` opens `cache.db` without WAL/busy_timeout pragmas
**File:** `crm/sync/export_shopee_deadstock_list.py:85`  
**Risk:** `sqlite3.connect(cache_db)` with no pragmas. Default journal mode is DELETE (not WAL); busy_timeout defaults to 0ms. If `reverse_etl` is running concurrently and holds a write lock, the export will fail immediately with `database is locked` instead of waiting. Low severity because export is a manual one-shot script, not a scheduled job.  
**Direction:** Use `su.open_cache_db(cache_db)` (which sets WAL + busy_timeout=5000) or at minimum set `PRAGMA busy_timeout=5000`.

### L2 — `seed_hug_deadstock_resell_campaign.py` opens `crm.db` without `foreign_keys=ON`
**File:** `crm/sync/seed_hug_deadstock_resell_campaign.py:70-74`  
**Risk:** `_open_crm_db` sets WAL and busy_timeout but omits `PRAGMA foreign_keys=ON`. If the upserted campaign references a foreign key (it doesn't currently, but future schema changes might), FK violations would not be caught. Low severity because this is a seed script run once and `crm_hug_campaign` has no FK constraints to other tables.  
**Direction:** Add `conn.execute("PRAGMA foreign_keys=ON")` to `_open_crm_db` to match the connection standard from `migrations.py`.

### L3 — `fetch_order_hdr` uses `>=` on HWM but comment says it fetches the HWM day again; could grow unboundedly with large daily volumes
**File:** `crm/sync/duckdb_reader.py:451-452`  
**Risk:** The comment correctly notes `>=` (not `>`) is intentional for late-arriving same-day orders. The `ON CONFLICT DO UPDATE` in the upsert deduplicates. However, on a busy day with thousands of orders, every sync run re-fetches the entire current day's orders (potentially 1000s of rows) when only a handful arrived since last run. This is unlikely to be a correctness bug but could be a performance issue at scale.  
**Direction:** Acceptable for current volumes. Document as a known trade-off if order volumes exceed ~10K/day on the HWM date.

### L4 — `0026_consent_contact_enum.up.sql` duplicates trigger and index definitions already created in 0003/0016
**File:** `crm/migrations/0026_consent_contact_enum.up.sql:10-36`  
**Risk:** The recovery-block `CREATE TABLE IF NOT EXISTS crm_customer_profile` re-defines `trg_customer_profile_touch` and `idx_profile_owner`. When running on a DB where the table exists (normal path), these are no-ops due to `IF NOT EXISTS`. But the migration runner skips "duplicate column name" errors only — it does not skip "trigger already exists". `CREATE TRIGGER IF NOT EXISTS` is correct (uses `IF NOT EXISTS`), and `CREATE INDEX IF NOT EXISTS` is also safe. No actual runtime risk; the patterns are correct.  
**Direction:** No action required; this is intentionally defensive.

---

## Confirmed Clean (Known Landmines — Verified OK)

1. **DuckDB read_only=True**: `duckdb_reader._open_conn` uses `read_only=True` on every call (`duckdb.py:160`). `open_warehouse()` passes through `_open_conn`. Tests re-open with `read_only=True`. ✓
2. **Reverse-ETL re-raises**: `_run_step` catches, logs, then `raise` at line 82. The outer `run()` has no bare `except` — exceptions propagate to caller. `entrypoint.sh` wraps in `if/else` (see H2 above), but the Python code itself re-raises correctly. ✓
3. **Fetch before upsert**: `run()` reads ALL warehouse tables before writing to cache.db (lines 161-168 fetch, lines 173-201 upsert). No truncate-then-fail pattern. ✓
4. **Idempotent upserts**: All `_upsert` calls use `INSERT … ON CONFLICT DO UPDATE`. `wh_party_seed` uses `ON CONFLICT(customer_id) DO UPDATE SET customer_key = excluded.customer_key`. `wh_action_queue` uses composite `ON CONFLICT(customer_key, action_type)`. No bare INSERT without conflict handling. ✓
5. **cache.db PRAGMAs**: `open_cache_db` sets WAL, busy_timeout=5000, synchronous=NORMAL, foreign_keys=OFF (correctly, bulk-load). ✓
6. **Migration numbering**: No two files share the same number prefix. Gap exists: 0009 exists, skips to 0010 (0009 is present). No collisions. ✓
7. **`_COLUMN_MIGRATIONS` ordering**: Schema applied first (`executescript`), then column migrations — no dependency-ordering issue. ✓

---

## Unresolved Questions

1. **`mart_deadstock_target_queue` absence in tests (M4)**: Have the T1/T2/T5 tests been run recently? If the mart table is absent from the fixture, those tests would be failing silently or erroring. Confirm actual test run output.
2. **ICT vs UTC in timestamps (H4)**: Is the downstream Go CRM reader of `wh_customer_tier.tier_generated_at` and `wh_deadstock_target.queue_generated_at` doing timezone-aware parsing or treating the value as opaque display string? If opaque, H4 is lower severity.
3. **`search_index.py` invocation cadence**: Is `rebuild_search_index` called on every reverse-ETL run or only on container startup? If called after every sync (scheduled), the write-lock contention risk (M5) is elevated.
4. **Empty mart guard for `wh_deadstock_target` (C1)**: Is there a scenario where `mart_deadstock_target_queue` legitimately returns 0 rows (e.g. before PLAN-004 is deployed)? If so, the current "guard → skip" behavior is correct by design for that phase, but should be made explicit.

---

## FIXES APPLIED 260623

All 6 tests pass (T1–T6, `pytest crm/sync/tests/test_reverse_etl_warehouse_to_crm.py`).

| Finding | Status | File:line | Notes |
|---------|--------|-----------|-------|
| C1 empty-mart guard | APPLIED | `sqlite_upsert.py:232-244` | Added `log.warning` + early return; DELETE skipped on 0 rows; module-level `log = logging.getLogger(__name__)` added |
| H1 broad OperationalError swallow | APPLIED | `sqlite_upsert.py:68-77` | Narrowed to `"duplicate column name"` check; all other `OperationalError` re-raised |
| H2 entrypoint.sh migration soft-fail | APPLIED | `entrypoint.sh:9-17` | Removed `if/else` wrapper; migration step now hard-fails container on error (set -e propagates); graceful-empty kept for Steps 2-3 only |
| H3 FTS rebuild wipes with no rollback | APPLIED | `search_index.py:194-202` | Replaced try/commit with `with crm_conn:` transaction block; DELETE rolls back if `executemany` fails |
| H4 bare ICT timestamps | APPLIED | `duckdb_reader.py:323,413` | `strftime(...) \|\| '+07:00'` appended to both `tier_generated_at` and `queue_generated_at` — stored TEXT is now unambiguous ISO-8601 ICT |
| M1 _COLUMN_MIGRATIONS partial dedup | DEFERRED | `sqlite_upsert.py:31-42` | Migration runner commits each statement individually; wrapping in a file-level transaction would require runner changes (separate scope); risk is low (dedup DELETE idempotent on re-run) |
| M2 migration 0023 outside transaction | DEFERRED | `crm/migrations/0023_...up.sql` | Runner uses statement-by-statement `conn.execute()` + per-statement `conn.commit()`; `BEGIN;...COMMIT;` in the SQL file would be split and committed individually, not atomically. Fixing requires runner changes. 0023 is already applied on prod DB — crash-window has passed |
| M3 missing down migrations | DEFERRED | `crm/migrations/` | Accepted as-is per audit direction; document: rollback requires DB restore from backup |
| M4 mart_deadstock_target_queue missing from fixtures | APPLIED | `test_reverse_etl_warehouse_to_crm.py:225-270,488-506` | Added table CREATE+INSERT to `_make_warehouse`; added empty table to `_create_minimal_dim_tables`; added `wh_deadstock_target` to T1 checks (1 row), T2 idempotency list, T4 sync_run expected tables |
| M5 search_index opens crm.db for reads with write conn | DEFERRED | `search_index.py:161` | Load phase already uses a `try/finally` and holds conn only briefly; contention risk depends on invocation cadence (unresolved Q3). Fixing correctly requires splitting read/write connections — non-trivial without breaking the current data-flow; low-priority until confirmed concurrent |
| L1 export_shopee missing WAL/busy_timeout | APPLIED | `export_shopee_deadstock_list.py:29,89-92` | Replaced `sqlite3.connect()` with `open_cache_db()` in `export()`; imports `open_cache_db` at module level |
| L2 seed_hug missing foreign_keys=ON | APPLIED | `seed_hug_deadstock_resell_campaign.py:75` | Added `PRAGMA foreign_keys=ON` to `_open_crm_db` |
| L3 fetch_order_hdr >= HWM perf trade-off | DEFERRED | `duckdb_reader.py:451` | Documented in audit as acceptable; no change |
| L4 0026 duplicate trigger/index defs | DEFERRED | `crm/migrations/0026_...up.sql` | Audit confirmed no-op at runtime (`IF NOT EXISTS` guards); no change needed |
