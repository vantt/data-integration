# Code Review: Orchestration & Infrastructure Edge Cases
**Date:** 2026-02-27
**Scope:** 5 files, orchestration + provisioning layer
**Focus:** Targeted edge case verification

---

## Edge Case Findings

---

### 1. Dagster Asset Materialization Order Violations
**File:** `orchestration/definitions.py`

**Status: Handled**

**Evidence:**
- Jobs use `AssetSelection` union: ingestion | `all_dbt_assets` | `sapo_serving_db`
- Dagster resolves execution order from asset dependency graph, not job selection order
- `dbt.py` `get_upstream_asset_keys()` injects explicit upstream deps for ALL staging models onto `sapo_history_log_asset`, `sapo_webhook_consumer_asset`, and all three batch assets (lines 74-80)
- `serving.py` declares `deps=[sapo_dbt_assets]` (line 18), enforcing dbt-before-serving order
- Schedule-level mutual exclusion (realtime/incremental yield to each other via `get_runs` checks) prevents concurrent job overlap

**Caveat (low severity):** `sapo_nightly_reconciliation_job` schedule does not check for active `sapo_realtime_sync_job` or `sapo_incremental_sync_job` runs before launching. A slow-running realtime job could overlap with nightly at 04:00 since only nightly checks its own self-overlap.

**Impact:** Low - nightly only runs once at 04:00 and incremental is excluded from 04:xx window.

---

### 2. dbt Asset Key Translation Mismatches
**File:** `orchestration/assets/dbt.py`

**Status: Handled**

**Evidence:**
- `sources.yml` declares exactly 5 sources under `sapo_raw`: `order`, `customer`, `account`, `targets_raw`, `marketing_spend_raw`
- `SapoDbtTranslator.get_asset_key()` maps all 5 (lines 27-39):
  - `order` -> `sapo/sapo_orders_batch_asset`
  - `customer` -> `sapo/sapo_customers_batch_asset`
  - `account` -> `sapo/sapo_accounts_batch_asset`
  - `targets_raw` -> `sheets/sheets_targets_asset`
  - `marketing_spend_raw` -> `sheets/sheets_marketing_spend_asset`
- Falls through to `super().get_asset_key()` for non-source resources (models, tests, snapshots)

**No unmapped sources found.**

---

### 3. Serving DB Generation Before All Marts Materialized
**File:** `orchestration/assets/serving.py`

**Status: Partial**

**Evidence:**
- `sapo_serving_db` declares `deps=[sapo_dbt_assets]` (line 18)
- `sapo_dbt_assets` is a single `@dbt_assets` decorator that runs `dbt build` for ALL models (line 132: `dbt.cli(["build"])`)
- This means serving waits for the entire dbt build to complete, including all marts

**Caveat (medium severity):** The dependency is on the single `sapo_dbt_assets` asset object, not individual mart assets. If dbt partially fails (some models error, some pass), Dagster may mark the `sapo_dbt_assets` step as failed and `sapo_serving_db` will not run. However, dbt's partial failure behavior within a single `dbt build` call means there is no guarantee that ALL mart parquet files exist before serving attempts to read them - dbt will export whatever succeeded. The serving script handles empty folders gracefully (lines 87-96 in `generate_serving_db.py`) but will create/update views only for folders that have parquet files.

**Impact:** Medium - a partial dbt failure (e.g., one mart model fails) results in serving DB being built from incomplete mart data without any warning surfaced to the calling Dagster asset. The asset reports success as long as the subprocess exits 0.

---

### 4. Python venv Not Found for Subprocess
**File:** `orchestration/assets/serving.py`

**Status: Partial**

**Evidence (lines 14-15):**
```python
VENV_PYTHON = os.path.join(PROJECT_ROOT, "dlt", "venv", "Scripts", "python.exe")
PYTHON_EXE = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable
```

- Fallback to `sys.executable` exists, so the asset will not crash on missing venv
- The venv path is hardcoded to `dlt/venv/Scripts/python.exe` (Windows-only path separator and `.exe` suffix)
- On Linux/Docker, `Scripts/` does not exist (Linux uses `bin/`); `os.path.exists()` returns False and fallback to `sys.executable` kicks in correctly
- The `sys.executable` fallback is the Dagster process Python, which may or may not have `duckdb` installed

**Unhandled sub-case:** No validation that `sys.executable` environment has `duckdb` installed before subprocess launch. If neither venv exists nor `duckdb` is in the Dagster Python env, the `subprocess.run` will raise `ModuleNotFoundError` inside the script, which is caught by `CalledProcessError` and surfaced as asset failure - this is acceptable behavior.

**Impact:** Low-Medium - fallback exists but silently uses wrong interpreter context on mismatched environments.

---

### 5. Environment Variable Loading Conflicts (.env.local vs secrets.toml)
**File:** `orchestration/assets/utils.py`

**Status: Partial**

**Evidence - Loading order:**
1. `.env.local` loaded first (lines 19-48), writes keys directly to `os.environ` unconditionally
2. `secrets.toml` loaded second (lines 51-113), uses `if new_prefix not in os.environ` guard (line 76 and 111) - meaning `.env.local` values win over `secrets.toml` values

**Inline comment parsing issues:**

Issue A (lines 32-35): There is a stale `if "#" in line: pass` block that does nothing. The comment stripping logic below it (lines 44-45) only activates for `" #"` (space-hash), not `"#"` immediately after a value. Example:
```
KEY=value#not_a_comment  # would NOT be stripped -> value set to "value#not_a_comment"
KEY=value #comment        # would be stripped correctly -> value set to "value"
```

Issue B: Quote stripping (`value.strip('"').strip("'")`) on line 47 strips all leading/trailing quotes but does not handle mixed quotes like `KEY="value'` correctly - strips outer `"` then outer `'` leaving `value`. This is likely acceptable for real .env files but is fragile.

Issue C: The fallback TOML parser (lines 82-113) handles only single-level `[section]` headers, not nested `[sources.sapo.credentials]`-style sections - it concatenates levels with `__` only for the first level. Nested TOML sections beyond one level deep will be keyed incorrectly in fallback mode (e.g., `[a.b]` becomes section `A__B`, which is correct, but `[a.b.c]` would need `A__B__C` - the fallback correctly walks the `raw_section.replace(".", "__")` so this is actually handled).

**Impact:** Low - `.env.local` wins over secrets.toml (documented by code order), the `pass` block is dead code but harmless. The `#` without space before it is a real parsing bug if values contain `#`.

---

### 6. Parquet Rolling GC Race Condition with Concurrent dbt
**File:** `scripts/provisioning/generate_serving_db.py`

**Status: Partial**

**Evidence:**
- GC runs in `generate_serving_db.py::garbage_collect()` (lines 28-44)
- GC is called AFTER dbt completes (serving asset runs only after `sapo_dbt_assets` finishes, per dep graph)
- There is no concurrent dbt execution possible within the same Dagster run since `sapo_serving_db` depends on `sapo_dbt_assets`

**Actual race window:** Between two SEPARATE job runs (e.g., realtime job N finishes dbt and starts serving, while realtime job N+1 starts and runs dbt simultaneously). The schedule mutual exclusion logic in `definitions.py` prevents this by checking for active runs of the same job before emitting a `RunRequest`.

**Residual risk:** The `PermissionError` catch in `garbage_collect()` (line 41) silently skips locked files - this is the correct Windows behavior for file locking. On Linux (Docker), there is no advisory file locking, so GC could delete a file that a concurrent process is reading. However, because:
- DuckDB reads via `read_parquet()` at view query time (not at view creation time)
- GC keeps the latest file, which is what the view queries

The actual deletion target is the PREVIOUS file (not the one being written by dbt). dbt writes a NEW timestamped file, GC deletes OLD files. This is safe as long as no reader is mid-scan of an old file.

**Unhandled:** No file locking on Linux. If a BI tool is mid-query on an old parquet file via the DuckDB view while GC runs, the query may fail with a file-not-found error on Linux.

**Impact:** Low-Medium on Linux/Docker; effectively zero on Windows due to OS-level file locking.

---

### 7. Empty Rolling Directories (No Parquet Files Found)
**File:** `scripts/provisioning/generate_serving_db.py`

**Status: Handled**

**Evidence (lines 87-95):**
```python
latest_filename = get_latest_file(table_dir)
if not latest_filename:
    print(f"  [!] Empty folder: {table_name}")
    if not db_locked and con:
        try:
            con.sql(f"DROP VIEW IF EXISTS {table_name}")
            print(f"      [Cleanup] Dropped empty view: {table_name}")
        except Exception as e:
            print(f"      [!] Failed to drop view: {e}")
    continue
```

- Empty folder: logs warning, drops existing view if DB available, continues to next table - no crash
- `get_latest_file()` returns `None` if no `.parquet` files exist (lines 46-52)
- `ROLLING_DIR` non-existence is also handled at line 60-62 (early return with log message)
- `subdirs` empty case handled at lines 78-81 (early return)

**No issues found for this case.**

**Impact:** None.

---

## Summary Table

| # | Edge Case | Status | Severity | Resolution (2026-04-03) |
|---|-----------|--------|----------|------------------------|
| 1 | Dagster asset materialization order | ✅ Resolved | Low | Nightly schedule now checks for active realtime/incremental jobs |
| 2 | dbt asset key translation mismatches | ✅ Handled | None | No action needed |
| 3 | Serving DB before all marts materialized | ✅ Resolved | Medium | serving.py parses stdout for error indicators, logs warnings, attaches to metadata |
| 4 | Python venv not found | ✅ Resolved | Low-Medium | Platform-aware path: `bin/python` (Linux) vs `Scripts/python.exe` (Windows) |
| 5 | Env var loading conflicts / comment parsing | ✅ Resolved | Low | Dead code removed, comment parser rewritten with quote-awareness |
| 6 | Parquet GC race condition with concurrent dbt | ✅ Resolved | Low-Medium (Linux) | GC retries once after 0.5s on OSError for Linux compatibility |
| 7 | Empty rolling directories | ✅ Handled | None | No action needed |
| NEW | Duplicate `sapo_accounts_batch_asset` in nightly job | ✅ Resolved | Low | Removed duplicate line in definitions.py |

---

## Recommended Actions — ALL RESOLVED (2026-04-03)

1. ~~**[Medium] Partial dbt failure transparency** (`serving.py`)~~ — ✅ Parses stdout for `error`/`[!]` markers, logs warnings, attaches to asset metadata
2. ~~**[Medium] Linux GC file locking** (`generate_serving_db.py`)~~ — ✅ Retry-once pattern with 0.5s delay on OSError
3. ~~**[Low] Dead code removal** (`utils.py`)~~ — ✅ Dead `pass` block removed, parser rewritten to handle quoted values and `#` without space
4. ~~**[Low] Venv path cross-platform** (`serving.py`)~~ — ✅ `sys.platform` check resolves correct venv subdir
5. ~~**[Low] Nightly schedule overlap guard** (`definitions.py`)~~ — ✅ Checks active realtime/incremental before launching

---

## Unresolved Questions (from original review)

1. **dbt parquet atomicity** — ⚠️ **Open** → tracked separately in [`plans/code-review/parquet-atomicity-investigation.md`](./parquet-atomicity-investigation.md)
2. **PORTABLE_ROOT vs DBT_EXPORT_PATH** — ✅ **Closed (by-design)**: `PORTABLE_ROOT` is intentionally `DATA_LAKE_ROOT` because the SQL view path is relative to the container mount. `DBT_EXPORT_PATH` only affects where dbt writes; the view SQL hardcodes the known container path.
3. **sheets_sync_job skipping** — ✅ **Closed (not an issue)**: `get_upstream_asset_keys()` adds sapo batch assets only to `stg_sapo_*` models. `sheets_sync_job` only selects sheets assets (no dbt), so no staging models run and no skip occurs.
