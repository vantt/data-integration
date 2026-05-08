# Locking & Concurrency Architecture

> Audit date: 2026-04-08
> Status refresh: 2026-04-09 (post-hardening sweep — see §Status Refresh)
> Scope: every lock / mutex / concurrency primitive in the `data-integration` repo
> Methodology: code scan + empirical verification inside live `data_platform` container

## Executive Summary

- **Overall posture: healthy. All P0/P1 findings from 2026-04-08 are now remediated.** Landmine fixed, pool leak auto-remediated at boot, docstring corrected.
- **DuckDB writer serialization** works: `duckdb_lock` op pool (slot=1) + `dbt_rw` coordinator tag. No contention seen on `sapo_warehouse.duckdb` today.
- **Metabase + serving `olap.duckdb` coexistence is a non-problem.** Empirically verified: DuckDB `read_only=true` does not acquire any file lock; RW connect while Metabase up = **13.3 ms, no error**. Historical "Metabase JDBC exclusive lock" narrative is refuted.
- **Subprocess hang risk (16h incident) is fixed** in `orchestration/assets/serving.py` via Popen + streaming read + 1800s timeout + merged stderr. `transformation/scripts/run_dbt.py` now also has `timeout=3600` (2026-04-09).
- **Pool slot leak auto-remediated:** `unstick_concurrency_pools.py` now runs on every container boot before `dagster dev` (docker-compose.yml, commit b2659fb). Manual operator action no longer required after cancel batches.
- **Landmine fixed:** `.skills/data-pipeline/templates/serve/dagster-serving-asset-template.py` replaced with Popen+streaming+timeout pattern (commit 593aa5c).
- **`bootstrap_serving_views.py` docstring rewritten** to reflect the verified "Metabase read_only=true holds no file lock → safe to run while Metabase is up" reality (commit b2659fb).
- **Schedules self-overlap check** in place on all 3 scheduled jobs (`realtime`, `incremental`, `nightly`). Coordinator tag `dbt_rw` applied to all 4 jobs including manual-only `ingest_sheets_sync_job`.
- **Two sensors** monitor run health: `health_alert_failure_sensor` (terminal failures) + `health_alert_stuckrun_sensor` (45-min STARTED threshold, cursor-dedup). Together they cover both crash-path and hang-path failure modes.

## Layer Map

| Layer             | Primitive                                                                                    | Location                                                            | Scope                       | Status        |
| ----------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | --------------------------- | ------------- |
| DB                | DuckDB file write exclusivity on `sapo_warehouse.duckdb`                                     | intrinsic to DuckDB                                                 | process-wide writer         | 📌 inherent    |
| DB                | dbt `threads: 1`                                                                             | `transformation/profiles.yml:7,14`                                  | in-process                  | ✅ working    |
| Dagster op pool   | `duckdb_lock` slot=1                                                                         | `orchestration/assets/dbt.py:92`, set via `docker-compose.yml:33`   | instance-wide op step       | ✅ working (auto-unstick on boot since 2026-04-09) |
| Dagster run coord | `QueuedRunCoordinator` `tag_concurrency_limits concurrency_group=dbt_rw limit=1`             | `app_data/dagster_home/dagster.yaml:13-21`                          | instance-wide run dequeue   | ✅ working    |
| Dagster schedule  | `_has_active_run()` self-overlap skip                                                        | `orchestration/definitions.py:132-177`                              | per-job queue suppression   | ✅ working (post-fix 2026-04-08) |
| Dagster sensor    | `health_alert_failure_sensor` (terminal FAILURE → Lark)                                      | `orchestration/sensors/failure_alerting.py`                         | operator alert (crash path) | ✅ working    |
| Dagster sensor    | `health_alert_stuckrun_sensor` (STARTED > 45 min → Lark, cursor-dedup, no auto-kill)        | `orchestration/sensors/stuck_run_alerter.py`                        | operator alert (hang path)  | ✅ working (fixed `DagsterRun.start_time` bug 2026-04-09) |
| Dagster sensor    | `ingest_sheets_modified_sensor` (sha256 polling every 5 min → ingest_sheets_sync_job)        | `orchestration/sensors/sheets_modified_sensor.py`                   | reactive trigger on edit    | ✅ working (verified live tick 2026-04-09 11:43) |
| OS file           | Cross-platform file lock on cookies (`msvcrt.locking` / `fcntl.flock`)                       | `ingestion/src/utils/shared_cookie_manager.py:17-43`                | cross-process               | ✅ working    |
| OS file           | Atomic tmp + `os.replace` (cookies, `.known_tables.json`)                                    | `shared_cookie_manager.py:222-237`, `refresh_rolling.py:86-92`      | writer isolation            | ✅ working    |
| OS file           | Parquet GC (main `os.remove`) + PermissionError/OSError retry (cold path)                    | `scripts/provisioning/refresh_rolling.py:46-71`                     | writer vs reader            | ✅ working (retry branches never fired, see §Verification 2026-04-09) |
| App (dlt)         | Per-pipeline state dir `/var/dlt/pipelines/<name>/` + internal advisory lock                 | dlt library                                                         | same `pipeline_name` only   | 📌 inherent    |
| Subprocess        | `Popen` streaming + `timeout=1800`                                                           | `orchestration/assets/serving.py:54-77`                             | serving script run          | ✅ working    |
| Subprocess        | `subprocess.run(..., check=True, timeout=3600)` inherited stdio                              | `transformation/scripts/run_dbt.py:109`                             | standalone dbt CLI wrapper  | ✅ working (post-fix 2026-04-09) |
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
- `SYNC_TAGS = {"concurrency_group": "dbt_rw"}` (`definitions.py:68`) is applied to all four asset jobs: `ingest_sapo_realtime_job`, `ingest_sapo_incremental_job`, `ingest_sheets_sync_job`, `transform_batch_nightly_job`.
- **Scope limit (critical)**: `tag_concurrency_limits` gates **dequeue**, not **queue admission**. Queue can grow unbounded unless schedules self-skip. This is the Lesson L19 foot-gun.

### Dagster schedule-level

- `definitions.py:124-177`: `_has_active_run(context, job_name)` queries the instance for runs in `[QUEUED, NOT_STARTED, STARTING, STARTED]` for the **same job name** and skips the tick if any exist.
- Applied to all 3 schedules: `ingest_sapo_realtime_schedule` (`:146`), `ingest_sapo_incremental_schedule` (`:161`), `transform_batch_nightly_schedule` (`:173`). ✅
- `ingest_sapo_incremental_schedule` cron `*/10 0-3,5-23 * * *` excludes the 4 AM hour to avoid piling up ticks while nightly holds the `dbt_rw` slot. Thoughtful.
- Note: `ingest_sheets_sync_job` has no schedule. Trigger paths: (1) manual via Dagster UI / CLI, (2) `ingest_sheets_modified_sensor` (content-hash polling every 5 min, auto-fires on real sheet edits — see commit 2026-04-09), (3) nightly reconciliation (includes sheet assets in its selection). Coordinator tag still protects it from colliding with active sync runs.

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
- 🚨 **LANDMINE**: `.skills/data-pipeline/templates/serve/dagster-serving-asset-template.py:66` still contains:
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
5. **Paired run-health sensors**. Two complementary sensors cover every failure mode:
   - `health_alert_failure_sensor` (`failure_alerting.py`) — built on Dagster's `@run_failure_sensor`, fires on any terminal FAILURE and pushes a red Lark card. Handles the "job crashed loudly" path.
   - `health_alert_stuckrun_sensor` (`stuck_run_alerter.py`) — custom `@sensor` ticking every 10 min, scans `DagsterRunStatus.STARTED`, alerts on any run older than 45 min with an orange Lark card. Handles the "job silently hung, no failure event" path (the 16 h serving-db incident would have been caught here). Cursor-based dedup (max 100 ids) prevents re-alert spam, and no auto-kill means operator owns the recovery decision. The 45-min threshold is deliberately longer than `SERVING_TIMEOUT_SEC` (1800 s) so the subprocess timeout path gets a chance to raise naturally first.
6. **Bootstrap / runtime split** (`bootstrap_serving_views.py` vs `refresh_rolling.py`) separates DB-touching logic from file-touching logic. Cleaner blast radius even if the "avoid Metabase lock" justification is obsolete.
7. **Schema drift detection** via `.known_tables.json` marker + hard error on new tables is an elegant, lock-free way to catch "view needs bootstrap" state without opening DuckDB.
8. **`unstick_concurrency_pools.py`** already exists in the repo — team discovered and fixed the leak the same day.

## What's Risky or Fragile

1. ~~**Dagster asset-level pool slot leak on cancel**~~ → **RESOLVED 2026-04-09** (commit b2659fb). `unstick_concurrency_pools.py` now runs on every container boot via `docker-compose.yml` command: `... && python scripts/maintenance/unstick_concurrency_pools.py || true && dagster dev ...`. First boot verified: `Pool 'duckdb_lock': slot=1 active=0 pending=0 / Total slots freed: 0`. Leak still exists in Dagster upstream, but blast radius bounded to "one container restart = auto-healed".
2. ~~**`run_dbt.py` has no timeout**~~ → **RESOLVED 2026-04-09** (commit 2aa55d8). `timeout=3600` + `TimeoutExpired` handler added.
3. **Incremental schedule `4 AM hour exclusion` is a magic skip window**. If nightly is ever delayed past 5 AM, the incremental job resumes and can enqueue while nightly is still running. Self-overlap on nightly's OWN job prevents double-nightly, and coordinator tag serializes dbt_rw across jobs — so it is correct but subtle.
   - **Status 2026-04-09**: documented in `transform_batch_nightly_schedule` docstring (commit 2aa55d8). ✅
4. ~~**Read-time lock assumption** in `_read_cookie_file()`~~ → **DOCUMENTED 2026-04-09** (commit 2aa55d8). INVARIANT comment added forbidding future edit-in-place writer paths.
5. **Retry loops mask lock contention**: `pipeline_runner.py:80-100` retries 3× on any exception. If a real lock bug appears, it will be swallowed into retry noise. (Still open — observational.)

## What's Broken / Leaky

_All items in this section from the 2026-04-08 audit have been resolved on 2026-04-09. Kept as historical record._

### ✅ Landmine: template file had the 16 h bug pattern — FIXED

- **File**: `.skills/data-pipeline/templates/serve/dagster-serving-asset-template.py:66`
- **Was**: `subprocess.run(..., capture_output=True, ...)` — no timeout, pipe-deadlock prone.
- **Resolution**: replaced with `Popen` + streaming stdout + `stderr=STDOUT` + `wait(timeout=1800)` pattern from `serving.py:54-77`. Commit 593aa5c (2026-04-09).

### ✅ Misleading docstring in bootstrap_serving_views.py — FIXED

- **File**: `scripts/provisioning/bootstrap_serving_views.py`
- **Was**: `IMPORTANT: Metabase must NOT be connected to olap.duckdb while this runs`. Refuted empirically (Insight 2: `read_only=true` takes no file lock).
- **Resolution**: docstring rewritten to state "safe to run while Metabase is up in read_only=true mode, no restart required". Connect-error message also updated. Commit b2659fb (2026-04-09).

### ✅ Asset-level pool leak — AUTO-REMEDIATED

- **Mechanism**: Dagster `report_run_canceled()` still does not call `free_concurrency_slots_for_run()` (upstream behavior unchanged).
- **Resolution**: `docker-compose.yml` command now runs `python scripts/maintenance/unstick_concurrency_pools.py || true` before `dagster dev`. Idempotent, safe, first-boot friendly. Commit b2659fb (2026-04-09). Manual operator action no longer required after cancel batches — just restart the container (which was usually the operator's first instinct anyway).
- **Residual risk**: if the container runs for many weeks and accumulates cancels without a restart, the helper is still available for manual invocation.

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
| `scripts/provisioning/refresh_rolling.py:57-67` | PermissionError/OSError retry on parquet unlink | Linux allows unlink-while-open; DuckDB releases fds per query | **Verified 2026-04-09**: 10 consecutive runs show `deleted=17 skipped=0` on every table. Main `os.remove()` succeeds first try. Retry branches are cold. **Keep** — cheap cross-platform safety net for future Windows-native dev. |
| `scripts/provisioning/bootstrap_serving_views.py:89-98` | `try: con = duckdb.connect(SERVING_DB_PATH) except... "Could not acquire DuckDB lock"` | DuckDB `read_only=true` mode never holds a lock → this catch never fires for the Metabase case | Empirical — run bootstrap with Metabase up, observe no exception |
| `.skills/data-pipeline/templates/serve/dagster-serving-asset-template.py:66` | `capture_output=True` subprocess.run | This is the ANTI-pattern, not a dead defender — see P0 finding above | n/a — replace |

**Note**: Keep the `PermissionError` catch — it's cheap and does defend Windows dev. But document that the `except OSError: time.sleep(0.5); retry` branch on Linux is belt-and-suspenders.

## Recommended Improvements

### P0 — must-fix

1. ~~Fix the serving asset template~~ → **DONE 2026-04-09 (commit 593aa5c).**

### P1 — should-fix

2. ~~Wire `unstick_concurrency_pools.py` into container startup~~ → **DONE 2026-04-09 (commit b2659fb).**
3. ~~Update `bootstrap_serving_views.py` docstring~~ → **DONE 2026-04-09 (commit b2659fb).**

### P2 — nice-to-have

4. ~~Add `timeout=3600` to `transformation/scripts/run_dbt.py`~~ → **DONE 2026-04-09 (commit 2aa55d8).**
5. **Add a unit test** that imports `definitions.py` and asserts every schedule's function references `_has_active_run` (guard against future regressions). **Still open.**
6. ~~Document the 4 AM incremental-skip window~~ → **DONE 2026-04-09 (commit 2aa55d8, `transform_batch_nightly_schedule` docstring).**
7. ~~Add invariant comment in `SharedCookieManager._read_cookie_file`~~ → **DONE 2026-04-09 (commit 2aa55d8).**
8. **Sensor-based auto-unstick** — inspect `duckdb_lock` pool every N minutes and free slots whose owning run is terminal. Would replace boot-time helper with runtime healing. **Still open** — current boot-time workaround is good enough; only worth it if cancels happen frequently between restarts.

## Status Refresh — 2026-04-09

Post-audit hardening sweep (commits 593aa5c, b2659fb, 2aa55d8) resolved 6 of 8 recommendations:

| # | Item | Status | Commit |
|---|---|---|---|
| P0-1 | Serving asset template landmine | ✅ Fixed | 593aa5c |
| P1-2 | Auto-unstick on boot | ✅ Fixed | b2659fb |
| P1-3 | bootstrap_serving_views docstring | ✅ Fixed | b2659fb |
| P2-4 | run_dbt.py timeout | ✅ Fixed | 2aa55d8 |
| P2-5 | Schedule self-overlap unit test | ⏸ Open | — |
| P2-6 | 4 AM skip-window docs | ✅ Fixed | 2aa55d8 |
| P2-7 | Cookie read-lock invariant comment | ✅ Fixed | 2aa55d8 |
| P2-8 | Sensor-based pool auto-free | ⏸ Open | — |

**New findings during refresh**: `health_alert_failure_sensor` (commit e8b1f4a) was missing from the original Layer Map — added in this refresh. It complements `health_alert_stuckrun_sensor` by covering the crash path.

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
| Verify `concurrency_group: dbt_rw` applied to all sync jobs | ✅ `SYNC_TAGS` applied to `ingest_sapo_realtime_job`, `ingest_sapo_incremental_job`, `ingest_sheets_sync_job`, `transform_batch_nightly_job` |
| Verify `_has_active_run` check in all schedules | ✅ in `ingest_sapo_realtime_schedule`, `ingest_sapo_incremental_schedule`, `transform_batch_nightly_schedule` (no schedule for ingest_sheets_sync_job) |

### Follow-up verification 2026-04-09 11:10+07

| Test | Result |
|---|---|
| Parquet GC `skipped` counter across last 10 serving runs | ✅ every run: `tables=24 deleted=17 skipped=0` — main `os.remove()` always succeeds first try |
| `ls /app/data_lake/export/marts/rolling/<table>/` post-GC | ✅ each dir has exactly 1 file (latest timestamp) — no accumulation |
| `ls /var/dlt/pipelines/` | ✅ only `sapo_history_log_pipeline`, `sapo_webhook_consumer` (post-09:55 restart) |
| Container boot time via `stat /proc/1` | 2026-04-09 09:55:31 +0700 |
| Last nightly run with `sapo_orders_batch_asset` | ✅ `73b8ee34-2e0f-469f-8fdd-609b5b6783b2`, 2026-04-09 04:00:15–04:09:30, STEP_SUCCESS |
| Destination-side dlt state presence | ✅ `sapo_{orders,customers,accounts}_batch__*.jsonl` in `/app/data_lake/sapo_raw/_dlt_pipeline_state/` — incremental cursors persistent across container restart |
| Anomaly spotted | `/app/data_lake/export/marts/rolling/dim_time.parquet` — stray top-level file from pre-refactor layout (mtime Feb 3). Harmless: GC only scans subdirs. Candidate for cleanup. |

## Unresolved Questions

1. **`pipeline_runner.py` retry loop** — is the 3-attempt exponential backoff ever triggered by dlt internal lock contention in production? No telemetry distinguishes lock errors from network errors. Suggest adding an exception-type breakdown to logs.
2. **`bootstrap_serving_views.py` exclusive lock claim** — it says "requires exclusive DB lock" in its docstring L1. If Metabase is `read_only=true`, does `CREATE OR REPLACE VIEW` actually block any active Metabase queries even briefly? Would need a load-test to confirm whether a query issued during a `CREATE OR REPLACE VIEW` retries, errors, or blocks. Not urgent.
3. **dbt `prepare_if_dev()` manifest lock** — what exactly caused the "manifest.concurrent-update-lock" errors during code reload? Is it the same Dagster code-server reload race, and does newer dagster-dbt fix it? Worth checking on upgrade.
4. ~~**Why do `sapo_orders_batch / customers / accounts` have no dlt state dirs** in `/var/dlt/pipelines/` right now?~~ **RESOLVED 2026-04-09.** Three-part answer:
   1. **`/var/dlt/pipelines/` is ephemeral** — not bind-mounted in `docker-compose.yml`. Every container restart wipes it. Container boot time today: 2026-04-09 09:55:31 (`stat /proc/1`).
   2. **Batch pipelines only run at 04:00 nightly** (`transform_batch_nightly_job`, cron `0 4 * * *`). Last successful run: 2026-04-09 04:00:15–04:09:30 (verified in dagster compute logs, run `73b8ee34`). That state was wiped by the 09:55 container restart. Next re-creation: 2026-04-10 04:00. Meanwhile only `sapo_history_log_pipeline` (every 10 min) and `sapo_webhook_consumer` (every 3 min) have recreated their state dirs post-restart.
   3. **True pipeline state is NOT in `/var/dlt/`** — it lives in the destination, at `/app/data_lake/sapo_raw/_dlt_pipeline_state/` (bind-mounted, persistent). dlt's `restore_from_destination=True` default re-reads this on every `pipeline.run()` init. Verified presence of `sapo_orders_batch__*.jsonl`, `sapo_customers_batch__*.jsonl`, `sapo_accounts_batch__*.jsonl` files in this dir. So incremental cursors survive container restarts even though `/var/dlt/` does not.
   - **Implication**: `/var/dlt/` is a scratch dir only. No action needed. If we ever wanted faster restart warm-up, we could add a volume mount — but it would be pure optimization, not correctness.
5. ~~**`ingest_sheets_sync_job` with no schedule**~~ **RESOLVED 2026-04-09.** Intentional — by design it's reactive, not scheduled. Three trigger paths now exist:
   - **Manual** (UI Launchpad or `dagster job launch -j ingest_sheets_sync_job`)
   - **`ingest_sheets_modified_sensor`** (new — content-hash polls CSV export URLs every 5 min, fires RunRequest on real byte change; cold-start records baseline without firing; fetch errors preserve prior hash to avoid false positives)
   - **Nightly reconciliation** (includes sheet assets in its selection)
   Job selection was also expanded (commit 2026-04-09) to cascade downstream: `_sources | _sources.downstream() | sapo_serving_db` = 7 assets total (2 raw + 2 staging + 2 marts + 1 serving_db). Surgical rebuild, not full dbt graph. Pattern packaged into `.skills/data-pipeline/` Lesson 7 + L21/L22/L23.
