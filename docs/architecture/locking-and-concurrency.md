# Locking & Concurrency Architecture

> Audit date: 2026-04-08
> Scope: every lock / mutex / concurrency primitive in the `data-integration` repo
> Methodology: code scan + empirical verification inside live `data_platform` container

## Executive Summary

- **Overall posture: healthy, with 1 known leak and 1 landmine.**
- **DuckDB writer serialization** works: `duckdb_lock` op pool (slot=1) + `dbt_rw` coordinator tag. No contention seen on `sapo_warehouse.duckdb` today.
- **Metabase + serving `olap.duckdb` coexistence is a non-problem.** Empirically verified today: DuckDB `read_only=true` does not acquire any file lock; RW connect while Metabase up = **13.3 ms, no error**. Historical "Metabase JDBC exclusive lock" narrative is refuted.
- **Subprocess hang risk (16h incident) is fixed** in `orchestration/assets/serving.py` via Popen + streaming read + 1800s timeout + merged stderr. Only one residual non-timeout subprocess exists (`transformation/scripts/run_dbt.py`), and it is standalone-only.
- **One known leak:** Dagster asset-level concurrency pool slots (e.g. `duckdb_lock`) are NOT released on run cancel / container kill. Mitigation: `scripts/maintenance/unstick_concurrency_pools.py` (manual, must run after any incident).
- **One landmine:** `.skills/data-pipeline/templates/dagster-serving-asset-template.py:66` still uses the deadlock-prone `capture_output=True` pattern — any asset copied from this template will inherit the bug.
- **Defensive dead code** in `bootstrap_serving_views.py` docstring still warns "Metabase must NOT be connected" — contradicts the verified behavior and should be updated.
- **Schedules self-overlap check is in place** on all 3 scheduled jobs after today's fix (`realtime`, `incremental`, `nightly`). Coordinator tag `dbt_rw` is applied to all 4 jobs including the manual-only `sheets_sync_job`.

## Layer Map

| Layer             | Primitive                                                                                    | Location                                                            | Scope                       | Status        |
| ----------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | --------------------------- | ------------- |
| DB                | DuckDB file write exclusivity on `sapo_warehouse.duckdb`                                     | intrinsic to DuckDB                                                 | process-wide writer         | 📌 inherent    |
| DB                | dbt `threads: 1`                                                                             | `transformation/profiles.yml:7,14`                                  | in-process                  | ✅ working    |
| Dagster op pool   | `duckdb_lock` slot=1                                                                         | `orchestration/assets/dbt.py:92`, set via `docker-compose.yml:33`   | instance-wide op step       | ⚠️ leak on cancel |
| Dagster run coord | `QueuedRunCoordinator` `tag_concurrency_limits concurrency_group=dbt_rw limit=1`             | `app_data/dagster_home/dagster.yaml:13-21`                          | instance-wide run dequeue   | ✅ working    |
| Dagster schedule  | `_has_active_run()` self-overlap skip                                                        | `orchestration/definitions.py:132-177`                              | per-job queue suppression   | ✅ working (post-fix 2026-04-08) |
| Dagster sensor    | `stuck_run_sensor` (alert-only, 45 min)                                                      | `orchestration/sensors/stuck_run_alerter.py`                        | operator alert              | ✅ working    |
| OS file           | Cross-platform file lock on cookies (`msvcrt.locking` / `fcntl.flock`)                       | `ingestion/src/utils/shared_cookie_manager.py:17-43`                | cross-process               | ✅ working    |
| OS file           | Atomic tmp + `os.replace` (cookies, `.known_tables.json`)                                    | `shared_cookie_manager.py:222-237`, `refresh_rolling.py:86-92`      | writer isolation            | ✅ working    |
| OS file           | Parquet GC PermissionError/OSError retry                                                     | `scripts/provisioning/refresh_rolling.py:46-71`                     | writer vs reader            | ❌ likely dead |
| App (dlt)         | Per-pipeline state dir `/var/dlt/pipelines/<name>/` + internal advisory lock                 | dlt library                                                         | same `pipeline_name` only   | 📌 inherent    |
| Subprocess        | `Popen` streaming + `timeout=1800`                                                           | `orchestration/assets/serving.py:54-77`                             | serving script run          | ✅ working    |
| Subprocess        | `subprocess.run(..., check=True)` no timeout, inherited stdio                                | `transformation/scripts/run_dbt.py:109`                             | standalone dbt CLI wrapper  | ⚠️ hang-possible |
| DB                | dbt manifest `prepare_if_dev()` disabled (`manifest.concurrent-update-lock` workaround)      | `orchestration/assets/dbt.py:16-18`; pre-parse in docker-compose:33 | Dagster code reload race    | ✅ working (documented) |

## Detailed Inventory

### DB-level

#### `sapo_warehouse.duckdb` (dbt internal)

- Path on host: `app_data/data_lake/sapo_warehouse.duckdb`; in container: `/app/data_lake/sapo_warehouse.duckdb`.
- Configured in `transformation/profiles.yml:6`.
- Writers: `sapo_dbt_assets` only (via `dbt.cli(["build"])`). Readers: ad-hoc scripts (`scripts/debug_duckdb.py`, `scripts/testing/*` with `read_only=True`).
- Protected by two independent mutexes:
  - **`duckdb_lock` op pool slot=1** (`orchestration/assets/dbt.py:92`) — ensures even if two runs somehow dequeue, only one dbt op step executes.
  - **`dbt_rw` coordinator tag limit=1** (`dagster.yaml:17-21`) — ensures only one sync run dequeues at a time.
- Empirical: RW connect during idle = 14.5 ms, no lock contention (not expected to be, since no dbt running).

#### `olap.duckdb` (serving layer)

- Path: `/app/data_lake/serving/olap.duckdb`.
- Readers: Metabase JDBC driver (`read_only=true`). Writers: `bootstrap_serving_views.py` (manual, one-shot).
- Empirical (2026-04-08): `duckdb.connect('/app/data_lake/serving/olap.duckdb')` (default RW) succeeded in **13.3 ms** while Metabase container up and serving queries. **No lock contention.**
- `refresh_rolling.py` deliberately does NOT touch the DB file — it only manages parquet files in `data_lake/export/marts/rolling/` and writes `.known_tables.json`. This separation (Pattern C) is the right call, but the original justification ("avoid Metabase lock contention") is wrong. The right justification is "design simplicity — runtime path touches only files, bootstrap path touches DB."

#### dbt manifest race

- `orchestration/assets/dbt.py:16-18`: `dbt_project.prepare_if_dev()` is disabled with comment: `# Disabled to prevent "manifest.concurrent-update-lock" errors during Dagster code reload.`
- Workaround: `dbt parse` runs at container startup (`docker-compose.yml:33`) and `run_dagster.ps1:50`.
- This is a dbt-dagster interaction bug that the team has correctly isolated.

### OS file-level

#### `SharedCookieManager`

- `ingestion/src/utils/shared_cookie_manager.py:17-43`: cross-platform lock:
  - Windows: `msvcrt.locking(fd, LK_NBLCK, 1)` with 10 retries × 100 ms.
  - Linux: `fcntl.flock(fd, LOCK_EX | LOCK_NB)` (single attempt).
- Atomic writes via `tempfile.mkstemp` + `os.replace` (`:222-237`) — correct pattern, survives crash.
- **Inconsistency to note:** `_read_cookie_file()` (`:175-210`) does NOT acquire any lock. The comment acknowledges this and relies on the atomic rename property for coherence. This is fine **only** because the writer does a single atomic replace. It is technically a best-effort read, but safe in practice.
- Linux side is `LOCK_NB` only (no retry loop). If contention occurs the writer will propagate `BlockingIOError` out of `lock_file()` — then `_acquire_lock()` catches it, retries, with 10 s timeout. Correct.
- **Verified cross-process safety**: writes go to unique mkstemp tmp paths, so concurrent writers never collide on the temp filename. ✅

#### `refresh_rolling.py` parquet GC

- Catches `PermissionError` (Windows) and `OSError` (Linux) when deleting old parquet files (`:57-67`).
- Retries once after 0.5 s.
- **Likely dead code on Linux**: DuckDB in the Metabase container opens parquet files only during query execution (streaming scan) and releases the fd on statement finish. Window between reader open and delete is tiny (sub-millisecond) and Linux permits unlink-while-open anyway (rename-on-delete semantics). On Windows this code would matter, but the deployment is Docker Linux. Keep it — low cost, cross-platform safety net.

#### `.known_tables.json`

- `refresh_rolling.py:86-92`: atomic tmp + `os.replace`. Correct.

### Process-level

- Single `data_platform` container = single Python process hosting Dagster + all dlt pipelines. No cross-process concurrency concerns inside it.
- Metabase runs in a separate container but only reads `olap.duckdb`.

### Dagster run-level (coordinator)

- `app_data/dagster_home/dagster.yaml`:
  ```yaml
  run_coordinator:
    class: QueuedRunCoordinator
    config:
      max_concurrent_runs: 5
      tag_concurrency_limits:
        - key: "concurrency_group"
          value: "dbt_rw"
          limit: 1
  ```
- `SYNC_TAGS = {"concurrency_group": "dbt_rw"}` (`definitions.py:68`) is applied to all four asset jobs: `sapo_realtime_sync_job`, `sapo_incremental_sync_job`, `sheets_sync_job`, `sapo_nightly_reconciliation_job`.
- **Scope limit (critical)**: `tag_concurrency_limits` gates **dequeue**, not **queue admission**. Queue can grow unbounded unless schedules self-skip. This is the Lesson L19 foot-gun.

### Dagster schedule-level

- `definitions.py:124-177`: `_has_active_run(context, job_name)` queries the instance for runs in `[QUEUED, NOT_STARTED, STARTING, STARTED]` for the **same job name** and skips the tick if any exist.
- Applied to all 3 schedules: `realtime_schedule` (`:146`), `incremental_schedule` (`:161`), `nightly_schedule` (`:173`). ✅
- `incremental_schedule` cron `*/10 0-3,5-23 * * *` excludes the 4 AM hour to avoid piling up ticks while nightly holds the `dbt_rw` slot. Thoughtful.
- Note: `sheets_sync_job` has no schedule — manual trigger only. Coordinator tag still protects it from colliding with active sync runs.

### Dagster op-level

- `orchestration/assets/dbt.py:89-93`:
  ```python
  @dbt_assets(
      manifest=dbt_project.manifest_path,
      dagster_dbt_translator=SapoDbtTranslator(),
      op_tags={"dagster/concurrency_key": "duckdb_lock"},
  )
  ```
- Slot count set to 1 at container startup via:
  - `docker-compose.yml:33`: `dagster instance concurrency set duckdb_lock 1`
  - `run_dagster.ps1:51`: same command for Windows-native dev.
- Empirical right now: `slot=1 active=0 pending=0` (healthy).
- **Leak**: verified today that cancel/kill does not free this slot. Helper: `scripts/maintenance/unstick_concurrency_pools.py` (already in repo). Must be run manually after any cancel batch or container restart.
- **Only `sapo_dbt_assets` has this op tag** — dlt ingest assets don't need it because they write parquet files (not DuckDB). `sapo_serving_db` also doesn't need it (only runs a subprocess that touches files). Correct scoping.

### Application-level (dlt pipeline state)

- dlt state lives in `/var/dlt/pipelines/<pipeline_name>/` inside container (verified empirically).
- Each asset uses a distinct `pipeline_name` (see `run_*.py` in `ingestion/`), so cross-pipeline runs never share state.
- dlt library acquires an internal advisory lock on the pipeline working dir when `pipeline.run()` starts. Two concurrent invocations of the **same** pipeline_name block.
- In practice this is prevented by schedule self-overlap check + same-process execution — the only way to hit it is manual CLI invocation while a Dagster run is active.
- `ingestion/src/utils/pipeline_runner.py:80-100`: 3-attempt retry with exponential backoff (1 s, 2 s, 4 s) on any exception. Would retry on dlt lock contention — acceptable.

### Subprocess patterns

- ✅ `orchestration/assets/serving.py:54-77`: `Popen` + streaming stdout read + `stderr=STDOUT` + `proc.wait(timeout=1800)`. Correct pattern per L17. SERVING_TIMEOUT_SEC env-overridable.
- ⚠️ `transformation/scripts/run_dbt.py:109`: `subprocess.run(cmd, cwd=..., env=..., check=True)`. Default `capture_output=False` means child inherits parent stdio → **no pipe deadlock possible** (the 16 h bug required `capture_output=True`). But also **no timeout** → indefinite hang possible if dbt itself hangs. Mitigation: this script is standalone-only (not imported by Dagster — Dagster goes through `DbtCliResource.cli(["build"]).stream()` directly). Low production risk.
- 🚨 **LANDMINE**: `.skills/data-pipeline/templates/dagster-serving-asset-template.py:66` still contains:
  ```python
  result = subprocess.run(
      ...
      capture_output=True,
      ...
  )
  ```
  This is the exact anti-pattern that caused the 16 h hang. Any future asset copied from this template will inherit the bug. **Fix the template.**

## What's Working Well

1. **Two-layer DuckDB writer mutex** (coordinator tag `dbt_rw` + op pool `duckdb_lock`). Defense in depth for the single legitimate concurrency hazard in the stack.
2. **Serving subprocess streaming + timeout** fixes the real 2026-04-08 bug cleanly. Stderr merged into stdout avoids two-pipe deadlock. Output streamed line-by-line so it is impossible to fill the 64 KB pipe buffer.
3. **Schedule self-overlap check** restored today. Pattern is simple, uses Dagster native run state, and the Active-Status set correctly includes `NOT_STARTED` and `QUEUED`.
4. **SharedCookieManager atomic write** (`mkstemp` → unique tmp → `os.replace`) handles concurrent writers without lock contention. Read path does not lock — which is correct given the atomic replace guarantee.
5. **Stuck-run sensor** (`stuck_run_alerter.py`) fills the gap left by `run_failure_sensor`, which only fires on terminal FAILURE. Cursor-based dedup (max 100 ids) prevents re-alert spam.
6. **Bootstrap / runtime split** (`bootstrap_serving_views.py` vs `refresh_rolling.py`) separates DB-touching logic from file-touching logic. Cleaner blast radius even if the "avoid Metabase lock" justification is obsolete.
7. **Schema drift detection** via `.known_tables.json` marker + hard error on new tables is an elegant, lock-free way to catch "view needs bootstrap" state without opening DuckDB.
8. **`unstick_concurrency_pools.py`** already exists in the repo — team discovered and fixed the leak the same day.

## What's Risky or Fragile

1. **Dagster asset-level pool slot leak on cancel** — inherent to Dagster's semantics for op-level concurrency pools. Workaround exists (`unstick_concurrency_pools.py`) but requires **manual operator action** after every cancel batch or container restart. Post-mortem today showed 28+ runs piled up because of this.
   - **Mitigation (P1)**: run `unstick_concurrency_pools.py` on every container start. Wire it into `docker-compose.yml` command before `dagster dev`.
2. **`run_dbt.py` has no timeout** (`transformation/scripts/run_dbt.py:109`). If a human runs it manually and dbt hangs, the shell hangs too. Low blast radius (not Dagster-invoked) but trivially fixable.
   - **Fix (P2)**: add `timeout=3600` to the `subprocess.run` call.
3. **Incremental schedule `4 AM hour exclusion` is a magic skip window**. If nightly is ever delayed past 5 AM, the incremental job resumes and can enqueue while nightly is still running. Self-overlap on nightly's OWN job prevents double-nightly, and coordinator tag serializes dbt_rw across jobs — so it is correct but subtle.
   - **Mitigation (P2)**: no code change needed. Document it in `nightly_schedule` docstring.
4. **Read-time lock assumption**: `_read_cookie_file()` relies on the fact that the writer uses atomic rename. If anyone ever adds a non-atomic writer path (e.g. edit-in-place), readers will see partial JSON. Add a code comment enforcing invariant.
5. **Retry loops mask lock contention**: `pipeline_runner.py:80-100` retries 3× on any exception. If a real lock bug appears, it will be swallowed into retry noise.

## What's Broken / Leaky

### 🚨 Landmine: template file still has the 16 h bug pattern

- **File**: `.skills/data-pipeline/templates/dagster-serving-asset-template.py:66`
- **Code**: `subprocess.run(..., capture_output=True, ...)` — no timeout.
- **Fix priority**: **P0** — anyone writing a new serving-type asset will copy this.
- **Fix**: replace the template with the `Popen` + streaming pattern from `serving.py:54-77`.

### ⚠️ Dead/misleading docstring in bootstrap_serving_views.py

- **File**: `scripts/provisioning/bootstrap_serving_views.py:1-20`
- **Issue**: Says `IMPORTANT: Metabase must NOT be connected to olap.duckdb while this runs, because Metabase's JDBC pool holds the file lock.` Empirically refuted today (Insight 2). The script's own lines 15-17 then contradict this with `After Metabase is configured with duckdb.read_only=true, it holds only a shared lock...` — which is also technically wrong (no lock at all).
- **Fix priority**: **P2** — misleading operators but not actively breaking.
- **Fix**: rewrite the docstring to say "as long as Metabase is `read_only=true`, this is safe to run while Metabase is up; no restart needed".

### ⚠️ Asset-level pool leak is not auto-remediated

- **Mechanism**: Dagster `report_run_canceled()` does not call `free_concurrency_slots_for_run()`.
- **Impact**: every cancel batch can brick `duckdb_lock` until operator runs the helper.
- **Fix priority**: **P1** — wire `unstick_concurrency_pools.py` into the container startup command before `dagster dev`. Idempotent, safe on every restart.

## Inherent Limits (Must Accept)

1. **DuckDB = single writer.** Not a bug, a design choice. Any solution to "run 2 dbt builds at once" is to use 2 files, not to fix DuckDB. Hence `threads: 1` in profiles.yml and the `duckdb_lock` pool.
2. **DuckDB `read_only=true` takes no file lock.** Verified empirically. This is not a problem — it is the reason Metabase + pipeline coexist. But any lock-based reasoning about `olap.duckdb` is incorrect.
3. **Dagster asset-level pool slots don't auto-release on cancel.** Upstream Dagster behavior. We cannot fix it; we can only remediate.
4. **dbt manifest concurrent-update-lock** during Dagster code reload. Upstream dagster-dbt bug, worked around by disabling `prepare_if_dev()` and pre-parsing at startup.
5. **dlt pipeline advisory lock** on pipeline working dir. Cannot run same `pipeline_name` concurrently. Enforced by self-overlap schedule check.
6. **`QueuedRunCoordinator` does not bound queue depth.** It throttles dequeue only. Hence self-overlap check in schedule bodies remains mandatory — **never** rely on coordinator alone.

## Defensive Dead Code (Candidates for Removal or Simplification)

| File:Line | Code | Probably dead because | Verification approach |
|---|---|---|---|
| `scripts/provisioning/refresh_rolling.py:57-67` | PermissionError/OSError retry on parquet unlink | Linux allows unlink-while-open; DuckDB releases fds per query | Instrument the except branches with a print, run nightly for a week |
| `scripts/provisioning/bootstrap_serving_views.py:89-98` | `try: con = duckdb.connect(SERVING_DB_PATH) except... "Could not acquire DuckDB lock"` | DuckDB `read_only=true` mode never holds a lock → this catch never fires for the Metabase case | Empirical — run bootstrap with Metabase up, observe no exception |
| `.skills/data-pipeline/templates/dagster-serving-asset-template.py:66` | `capture_output=True` subprocess.run | This is the ANTI-pattern, not a dead defender — see P0 finding above | n/a — replace |

**Note**: Keep the `PermissionError` catch — it's cheap and does defend Windows dev. But document that the `except OSError: time.sleep(0.5); retry` branch on Linux is belt-and-suspenders.

## Recommended Improvements

### P0 — must-fix

1. **Fix the serving asset template** (`.skills/data-pipeline/templates/dagster-serving-asset-template.py`): replace `subprocess.run(capture_output=True)` with the `Popen` + streaming + timeout pattern. Copy from `orchestration/assets/serving.py:54-77` verbatim. **Effort: 15 min.**

### P1 — should-fix

2. **Wire `unstick_concurrency_pools.py` into container startup**: modify `docker-compose.yml:33` command to call it before `dagster dev`. Example:
   ```sh
   ... && python scripts/maintenance/unstick_concurrency_pools.py || true && dagster dev ...
   ```
   The `|| true` ensures a first-run failure doesn't block boot. **Effort: 10 min + 1 restart.**
3. **Update `bootstrap_serving_views.py` docstring** to reflect Insight 2. Rewrite lines 8-17 to say: "Safe to run with Metabase running in `read_only=true` mode; no stop required." **Effort: 5 min.**

### P2 — nice-to-have

4. **Add `timeout=3600` to `transformation/scripts/run_dbt.py:109`**. Standalone script, low risk, but removes the last hang-prone subprocess call. **Effort: 2 min.**
5. **Add a unit test** that imports `definitions.py` and asserts every schedule's function references `_has_active_run` (guard against future regressions). **Effort: 30 min.**
6. **Document the 4 AM incremental-skip window** in `nightly_schedule` docstring and in `AGENTS.md`. **Effort: 5 min.**
7. **Add invariant comment** in `SharedCookieManager._read_cookie_file` forbidding future edit-in-place writers. **Effort: 2 min.**
8. **Consider a Dagster sensor** that inspects `duckdb_lock` pool every 5 minutes and auto-frees slots whose owning run is terminal. Replaces manual `unstick_concurrency_pools.py`. **Effort: 2-4 h.**

## Verification History

Tests run inside `data_platform` container during this audit (2026-04-08 23:35+07):

| Test | Result |
|---|---|
| `duckdb.connect('/app/data_lake/serving/olap.duckdb')` (default RW) with Metabase up | ✅ connected in **13.3 ms**, no exception |
| `duckdb.connect('/app/data_lake/sapo_warehouse.duckdb')` (default RW) idle | ✅ connected in **14.5 ms**, no exception |
| `event_log_storage.get_concurrency_info('duckdb_lock')` | ✅ `slot=1 active=0 pending=0 active_runs=[]` |
| Find dbt internal DB file path | ✅ `/app/data_lake/sapo_warehouse.duckdb` (via `profiles.yml`) |
| Find dlt pipelines state dir | ✅ `/var/dlt/pipelines/<pipeline_name>/` — each pipeline isolated |
| Grep for `subprocess.run(..., capture_output=True, ...)` | Only 1 hit: `templates/dagster-serving-asset-template.py:66` (LANDMINE) |
| Grep for `subprocess.run` without timeout | 1 hit: `transformation/scripts/run_dbt.py:109` — standalone-only, inherited stdio |
| Verify `concurrency_group: dbt_rw` applied to all sync jobs | ✅ `SYNC_TAGS` applied to `sapo_realtime_sync_job`, `sapo_incremental_sync_job`, `sheets_sync_job`, `sapo_nightly_reconciliation_job` |
| Verify `_has_active_run` check in all schedules | ✅ in `realtime_schedule`, `incremental_schedule`, `nightly_schedule` (no schedule for sheets_sync_job) |

## Unresolved Questions

1. **`pipeline_runner.py` retry loop** — is the 3-attempt exponential backoff ever triggered by dlt internal lock contention in production? No telemetry distinguishes lock errors from network errors. Suggest adding an exception-type breakdown to logs.
2. **`bootstrap_serving_views.py` exclusive lock claim** — it says "requires exclusive DB lock" in its docstring L1. If Metabase is `read_only=true`, does `CREATE OR REPLACE VIEW` actually block any active Metabase queries even briefly? Would need a load-test to confirm whether a query issued during a `CREATE OR REPLACE VIEW` retries, errors, or blocks. Not urgent.
3. **dbt `prepare_if_dev()` manifest lock** — what exactly caused the "manifest.concurrent-update-lock" errors during code reload? Is it the same Dagster code-server reload race, and does newer dagster-dbt fix it? Worth checking on upgrade.
4. **Why do `sapo_orders_batch / customers / accounts` have no dlt state dirs** in `/var/dlt/pipelines/` right now? Either they have not run since the state volume was created, or they use different pipeline_name conventions. Not a locking issue but worth confirming the state path assumption.
5. **`sheets_sync_job` with no schedule** — intentional (manual-only) or missing-schedule bug? Only affects whether sheets re-syncs outside the nightly window.
