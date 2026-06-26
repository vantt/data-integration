---
title: "Durable Serving-Ready Trigger"
description: "Replace fire-and-forget CRM trigger with version-poll + durable ACK; CRM self-heals automatically when behind on serving versions."
status: pending
priority: P1
effort: 2h
branch: main
tags: [crm, serving, trigger, observability, idempotency]
created: 2026-06-24
---

## Context Links

- Research report: `plans/reports/from-research-to-planner-boundary-hardening-findings-260624-1952-report.md`
- Parent plan: `plans/260624-1952-warehouse-app-boundary-hardening/plan.md`
- Depends on: `plans/260624-1952-warehouse-app-boundary-hardening/phase-04-serving-snapshot-isolation.md` (produces `serving_version.json`)
- Informs: `plans/260624-1952-warehouse-app-boundary-hardening/phase-06-crm-service-boundary-adr.md`
- Source: `orchestration/assets/crm_sync.py` (fire-and-forget asset :25-96)
- Source: `orchestration/assets/serving.py` (build_standalone_export asset :140-171)
- Source: `orchestration/definitions.py` (job chains :80-204)
- Source: `crm/sync/cache_schema.sql` (wh_sync_run :129-138; crm_etl_run to be added — see phase-03)
- Source: `crm/src/config.py` (CRM_OLAP_PATH :34-38)
- Source: `orchestration/notifications/lark_client.py` (send_lark_card; graceful no-op when env unset :65-67)
- Source: `orchestration/ops/morning_digest.py:686` (Lark usage pattern)

---

## Overview

**Priority:** P1 — current `crm_cache_refresh` asset (`crm_sync.py:37-96`) is fire-and-forget: POSTs `POST /admin/refresh` with a 10s timeout, treats 200/202/409 as success, never polls for completion, never verifies the CRM actually consumed the new data. If CRM is down during the trigger, the miss is silent — CRM stays stale until the next pipeline run (potentially 24h for nightly).

**Current status:** Pending. Depends on phase-04 (requires `serving_version.json` to exist).

**What this phase does:**
1. CRM gains a lightweight poller: periodically reads `serving_version.json` and refreshes when `version > last_consumed_version`.
2. CRM records `last_consumed_version` in `crm_etl_run` table (introduced in phase-03; this phase adds the version column usage).
3. Dagster `crm_cache_refresh` asset is simplified: still sends the push trigger for low-latency refresh, but now the push is redundant safety (not the only mechanism). Asset records the current `serving_version` in its metadata for observability.
4. `morning_digest.py` computes and surfaces lag = current `serving_version` − CRM `last_consumed_version`.

**Recommended trigger model:** CRM polls `serving_version.json` (Option A) — see Architecture section for the full tradeoff analysis.

---

## Key Insights

- **Fire-and-forget gap** (`crm_sync.py:68-88`): 200/202/409 treated as success, no retry, no ACK, no completion poll. CRM miss = silent. If CRM is down or refresh fails internally, warehouse pipeline succeeds regardless (by design — correct to not block pipeline on CRM).
- **Temporal coupling** (`crm_sync.py:8-22`): Dagster must know CRM's URL and be network-reachable to it. CRM must be up exactly when Dagster fires. Both sides must be healthy simultaneously.
- **Current health state is ephemeral** (research report, `admin_handler.py:197-198`): `_state` dict is in-memory, lost on CRM restart. Zero durable record of last successful refresh.
- **`crm_etl_run` table** (phase-03): phase-03 adds this table to `cache.db` as a run-level health record (complements per-step `wh_sync_run`). This phase adds a `serving_version_consumed` column to that table, enabling lag computation.
- **`serving_version.json` location** (phase-04): `{DATA_LAKE_ROOT}/serving/standalone/serving_version.json`. CRM already has read-only access to the data_lake volume (`docker-compose.yml:204`, `./app_data/data_lake:/app/var/data_lake:ro`). The file is accessible inside the CRM container at `/app/var/data_lake/serving/standalone/serving_version.json` without any new volume mount.
- **Lark alerting**: CRM has no Lark integration today (research report: "CRM has NO Lark integration at all"). Adding Lark to CRM would require importing/reimplementing the client. The simpler approach: Dagster's `morning_digest.py` reads lag from `crm_etl_run` (via the existing `crm_data` volume read-mount on `data_platform`: `docker-compose.yml:41`) and surfaces it there. No Lark code in CRM needed.
- **Idempotency**: re-processing the same `serving_version` is a no-op — CRM checks `version > last_consumed_version` before refreshing. Push trigger arriving while CRM is already processing the same version returns HTTP 409 (already handled as success in `crm_sync.py:71`).

---

## Trigger Model Decision (Open Question #6)

### Option A: CRM polls `serving_version.json` (recommended)

CRM runs a background goroutine that reads the version file every N seconds (e.g., 60s). When `version > last_consumed`, triggers an internal refresh.

**Pros:**
- CRM is self-sufficient — no dependency on Dagster network reachability at trigger time.
- CRM catches up automatically if it was down when Dagster fired (self-healing).
- Eliminates the Dagster→CRM temporal coupling entirely.
- `serving_version.json` is a flat JSON file on a volume-mount — zero network overhead.
- Fits the "build boundaries first" goal: CRM owns its own data refresh lifecycle.

**Cons:**
- Up to N seconds of additional latency after snapshot is built (poll interval).
- CRM must implement a background goroutine with file-read loop (small new code, ~30 lines Go).
- Poll interval must be tuned: too short = unnecessary disk reads; too long = staleness window.

**Recommended poll interval:** 60s. At 60s, Metabase staleness window is already set by snapshot build time (after-every-serving-build from phase-04); CRM 60s lag is acceptable. Ops context does not require sub-minute CRM freshness.

### Option B: Dagster push with durable ACK

Dagster sends push trigger (as today). CRM records ACK in `crm_etl_run`. Dagster polls `crm_etl_run` (via the `crm_data` volume) until ACK matches current `serving_version`, with timeout.

**Pros:**
- Low latency (near-immediate trigger).
- Dagster asset can surface CRM completion timing as metadata.

**Cons:**
- Temporal coupling remains: Dagster must poll CRM state, CRM must respond.
- Dagster polling `crm_etl_run` (SQLite WAL) is safe (read-only) but adds coupling in the wrong direction (orchestrator reading app internal state).
- CRM down = Dagster asset times out or must skip poll → back to best-effort.
- Does not self-heal if CRM was down when the push fired.

**Decision: Option A (poll).** Option B's ACK mechanism adds complexity without solving the core problem (missed trigger during CRM downtime). The poll approach makes CRM resilient to Dagster timing independently.

### Hybrid (recommended implementation)

Keep the Dagster push trigger (`crm_cache_refresh` asset) as a low-latency hint — it causes an immediate refresh when both systems are healthy. The poll loop acts as the durable catch-up. This requires no change to CRM's HTTP handler, only adding the poller goroutine.

---

## Requirements

### Functional

1. CRM background goroutine reads `serving_version.json` every 60s; triggers internal refresh when `version > last_consumed_version`.
2. CRM records `serving_version_consumed` (int) in `crm_etl_run` after each successful refresh (phase-03 table, new column).
3. Re-processing the same `serving_version` is a no-op (idempotency guard).
4. If `serving_version.json` is absent (pre-phase-04 deploy or fresh environment), the poller skips gracefully — existing push-trigger behavior is unchanged.
5. `crm_cache_refresh` Dagster asset: reads current `serving_version` from `serving_version.json` before the push; records it as Dagster asset metadata. No behavior change to the push itself.
6. `morning_digest.py` surfaces CRM lag: reads `crm_etl_run.serving_version_consumed` (latest row) from `cache.db` and compares to `serving_version.json` version. Reports lag as a field in the digest.
7. CRM poller non-fatal: if file read fails or JSON is malformed, log warning and continue polling next cycle. Never crashes the CRM process.

### Non-functional

- Poll loop must not hold a file lock on `serving_version.json` between reads (open, read, close each cycle).
- SQLite WAL mode on `cache.db` (already set per system design); `crm_etl_run` write from poller goroutine must use the same connection pool as the HTTP handler.
- Polling goroutine started once at CRM application startup; no external trigger needed.
- Windows/Linux dual-runtime: file path construction must use `os.path.join` equivalents in Go (`filepath.Join`).

---

## Architecture

### Data Flow

```
build_standalone_export (Dagster asset, phase-04)
  └─ writes serving_version.json (version N) to serving/standalone/
        │
        ├─► [push path, low-latency hint]
        │     crm_cache_refresh asset (Dagster)
        │       └─ POST /admin/refresh → CRM (fire-and-forget, as today)
        │             └─ CRM: immediate refresh if not already running
        │
        └─► [poll path, durable catch-up]
              CRM poller goroutine (every 60s)
                └─ reads serving_version.json
                └─ version > last_consumed? → trigger internal refresh
                      └─ refresh completes
                            └─ write crm_etl_run row: serving_version_consumed=N
                                  │
                                  └─► morning_digest.py (Dagster, reads cache.db)
                                            lag = current_version − last_consumed
                                            → Lark digest field
```

### CRM: New Poller Goroutine

Location: CRM Go application startup (alongside existing HTTP server startup).

```
func startServingVersionPoller(cfg Config, refreshFn func(), interval time.Duration) {
    go func() {
        for range time.NewTicker(interval).C {
            v, err := readServingVersion(cfg.ServingVersionPath)
            if err != nil { log.Warn(...); continue }
            last := getLastConsumedVersion(cfg.CacheDB)  // reads crm_etl_run
            if v.Version > last {
                refreshFn()  // reuses existing /admin/refresh logic
            }
        }
    }()
}
```

`cfg.ServingVersionPath` = env var `CRM_SERVING_VERSION_PATH`, default `/app/var/data_lake/serving/standalone/serving_version.json`.

No new volume mount needed — the path is within the existing `:ro` data_lake mount at `docker-compose.yml:204`.

### `crm_etl_run` Table (phase-03 + this phase)

Phase-03 creates this table. This phase adds the `serving_version_consumed` column:

```sql
-- Added by this phase to the crm_etl_run table defined in phase-03
ALTER TABLE crm_etl_run ADD COLUMN serving_version_consumed INTEGER DEFAULT 0;
```

The poller updates this column after a successful refresh run. The `morning_digest.py` reads the max value to compute lag.

### Dagster Asset: `crm_cache_refresh` (minimal change)

Current: POSTs trigger, logs result.

Change: Before the POST, read `serving_version.json` if present; extract `version`; include it as Dagster output metadata key `serving_version_triggered`. No retry logic change, no completion poll. The push remains best-effort/fire-and-forget — the poll loop is the durability mechanism.

```python
# Read current serving version for metadata (best-effort; absent = no-op)
serving_version = _read_serving_version(SERVING_VERSION_PATH)

# ... existing POST logic ...

return Output(
    value=result_value,
    metadata={
        "http_status": ...,
        "response_body": ...,
        **({"serving_version_triggered": serving_version} if serving_version else {}),
    },
)
```

`SERVING_VERSION_PATH` = `os.path.join(DATA_LAKE_ROOT, "serving", "standalone", "serving_version.json")`. Since `crm_sync.py` runs inside `data_platform` container, the path resolves via the existing volume mount.

### morning_digest.py: Lag Field

Add a helper that:
1. Opens `cache.db` read-only (existing `crm_data` volume on `data_platform`: `docker-compose.yml:41`).
2. Queries `SELECT MAX(serving_version_consumed) FROM crm_etl_run`.
3. Reads `serving_version.json` for current version.
4. Lag = current − consumed. Emit as a Lark card field: `CRM serving lag: {lag} version(s)` (0 = up-to-date).
5. If table absent or file absent: emit `CRM lag: unknown (pre-v2 deploy)` — non-fatal.

---

## Related Code Files

### Modify
- `crm/sync/cache_schema.sql` — add `serving_version_consumed INTEGER DEFAULT 0` column to `crm_etl_run` (phase-03 creates the table; this phase extends it)
- `orchestration/assets/crm_sync.py` — add `serving_version` metadata field to `crm_cache_refresh` asset output
- `orchestration/ops/morning_digest.py` — add CRM lag field to digest

### Create
- CRM Go: new file `crm/src/infrastructure/serving_version_poller.go` (or equivalent path per CRM Go package layout) — poller goroutine + `readServingVersion()` + `getLastConsumedVersion()`

### No change
- `docker-compose.yml` — no new volumes; existing `:ro` data_lake mount covers the version file path
- `crm/src/config.py` — `CRM_SERVING_VERSION_PATH` env var added to config (new key, backward-compatible default)

---

## Implementation Steps

1. **`crm/sync/cache_schema.sql`: add column to `crm_etl_run`**

   After phase-03 creates the `crm_etl_run` table definition, add:
   ```sql
   -- Tracks which serving snapshot version was last consumed by this CRM refresh run.
   -- 0 = unknown (pre-version-sidecar deploys). Used to compute CRM data lag.
   ALTER TABLE crm_etl_run ADD COLUMN IF NOT EXISTS serving_version_consumed INTEGER DEFAULT 0;
   ```
   Use `ADD COLUMN IF NOT EXISTS` (SQLite ≥3.37) for idempotent migration safety.

2. **CRM Go: `serving_version_poller.go`**

   Create the poller goroutine file with:
   - `ServingVersionFile` struct: `Version int`, `BuiltAt string`, `TableListHash string`.
   - `readServingVersion(path string) (ServingVersionFile, error)` — opens, reads, JSON-decodes, closes.
   - `getLastConsumedVersion(db *sql.DB) int` — `SELECT COALESCE(MAX(serving_version_consumed), 0) FROM crm_etl_run`; returns 0 on any error.
   - `StartServingVersionPoller(cfg Config, db *sql.DB, refreshFn func())` — ticker loop at `cfg.ServingVersionPollInterval` (default 60s from env `CRM_SERVING_VERSION_POLL_INTERVAL_S`).
   - Idempotency guard: read `getLastConsumedVersion` inside the tick before calling `refreshFn`. After `refreshFn` completes successfully, INSERT a row into `crm_etl_run` with `serving_version_consumed = v.Version`.
   - On file-absent: `os.IsNotExist(err)` → `log.Debug("serving version file not present, skipping")` — no warning spam on fresh deployments before phase-04 is active.
   - On JSON parse error: `log.Warn(...)`, continue.

3. **CRM startup: wire poller**

   In the CRM application entry point (wherever the HTTP server is started), after DB initialization:
   ```go
   infrastructure.StartServingVersionPoller(cfg, cacheDB, adminRefreshFn)
   ```
   `adminRefreshFn` is the same function called by `POST /admin/refresh` — no duplication of refresh logic.

4. **`crm/src/config.py` (or Go equivalent config): add `CRM_SERVING_VERSION_PATH`**

   Add env var with default:
   ```python
   # In crm/src/config.py (Python side, for any Python CRM components reading config)
   CRM_SERVING_VERSION_PATH = os.environ.get(
       "CRM_SERVING_VERSION_PATH",
       "/app/var/data_lake/serving/standalone/serving_version.json"
   )
   ```
   Go config struct: add `ServingVersionPath string` with same default.
   No `docker-compose.yml` change needed (default path resolves on existing volume).

5. **`orchestration/assets/crm_sync.py`: add serving_version metadata**

   Add `_read_serving_version(path)` helper:
   ```python
   def _read_serving_version(path: str) -> int | None:
       try:
           with open(path, "r", encoding="utf-8") as f:
               return json.load(f).get("version")
       except (OSError, ValueError, TypeError):
           return None
   ```
   
   Add constant at module level:
   ```python
   DATA_LAKE_ROOT = os.environ.get("DBT_DATA_LAKE_PATH", "/app/var/data_lake")
   SERVING_VERSION_PATH = os.path.join(
       DATA_LAKE_ROOT, "serving", "standalone", "serving_version.json"
   )
   ```
   
   In `crm_cache_refresh` asset, before the POST:
   ```python
   serving_version = _read_serving_version(SERVING_VERSION_PATH)
   ```
   
   In the `return Output(...)`, add:
   ```python
   **({"serving_version_triggered": MetadataValue.int(serving_version)} if serving_version else {}),
   ```

6. **`orchestration/ops/morning_digest.py`: add CRM lag field**

   Add a helper `_crm_serving_lag()`:
   - Path for `cache.db`: construct from `CRM_DATA_DIR` env, same pattern as `system_backup.py` uses for the crm_data volume path.
   - Path for `serving_version.json`: same constant as step 5.
   - Return `(current_version, last_consumed, lag)` or `None` on any error.
   
   In the digest Lark card fields list, add:
   ```python
   lag_info = _crm_serving_lag()
   if lag_info:
       current_v, consumed_v, lag = lag_info
       fields.append({
           "label": "CRM serving lag",
           "value": f"{lag} version(s) (v{consumed_v} → v{current_v})" if lag > 0 else "up-to-date"
       })
   ```
   
   Non-fatal: wrapped in try/except; missing table or file = omit field (no digest failure).

7. **Deploy and verify**

   ```
   # 1. Ensure phase-04 is deployed (serving_version.json must exist)
   
   # 2. Rebuild CRM (picks up new poller goroutine)
   docker compose up -d --build crm
   
   # 3. Check CRM logs for poller startup
   docker compose logs crm | grep "serving version"
   
   # 4. Trigger a pipeline run to produce a new serving_version.json
   # Wait 60s; check crm_etl_run for serving_version_consumed row
   
   # 5. Verify lag = 0 in next morning_digest (or manually call digest trigger)
   ```

---

## Todo List

- [ ] Add `serving_version_consumed` column to `crm_etl_run` in `crm/sync/cache_schema.sql` (step 1)
- [ ] Create CRM Go poller: `readServingVersion`, `getLastConsumedVersion`, `StartServingVersionPoller` (step 2)
- [ ] Wire poller at CRM startup (step 3)
- [ ] Add `CRM_SERVING_VERSION_PATH` to CRM config (step 4)
- [ ] Add `_read_serving_version` + metadata field to `crm_sync.py` (step 5)
- [ ] Add CRM lag field to `morning_digest.py` (step 6)
- [ ] Deploy and verify (step 7)

---

## Success Criteria

1. **Self-healing catch-up**: stop CRM, run a pipeline (advances `serving_version.json`), restart CRM → within 60s CRM logs show refresh triggered; `crm_etl_run` row with `serving_version_consumed = N` appears.
2. **Idempotency**: trigger the same serving version twice (re-run `build_standalone_export` without change) → CRM logs show "version not newer, skip"; `crm_etl_run` is not double-written.
3. **Lag = 0 steady state**: in morning digest, CRM serving lag field shows "up-to-date" on a normal day where CRM was healthy throughout.
4. **Non-zero lag visible**: manually set `crm_etl_run.serving_version_consumed = 0`, wait for next digest → lag field shows correct non-zero value.
5. **File-absent graceful**: remove `serving_version.json`, wait 60s → CRM poller logs debug (no warning spam), no crash, HTTP endpoints unaffected.
6. **Dagster asset metadata**: `crm_cache_refresh` asset in Dagster UI shows `serving_version_triggered` metadata key with the correct integer after a pipeline run.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| CRM Go package layout unknown — poller file path may need adjustment | Medium | Low | Implementer reads existing CRM Go file structure before placing file; adjust package name accordingly |
| `crm_etl_run` not yet created (phase-03 not deployed) | Medium | Medium | `getLastConsumedVersion` returns 0 on any DB error (table absent = 0) — poller still functions; `ADD COLUMN IF NOT EXISTS` is idempotent for later migration |
| SQLite write contention: poller goroutine + HTTP refresh handler both write `crm_etl_run` | Low | Medium | Use single shared `*sql.DB` connection pool (SQLite WAL mode handles concurrent readers + one writer); poller write is a brief INSERT after refresh completes — low collision probability |
| Poll interval 60s causes CRM to lag behind snapshot during high-frequency pipeline days | Low | Low | 60s is well within acceptable CRM staleness for ops use. Tunable via `CRM_SERVING_VERSION_POLL_INTERVAL_S` if needed |
| `morning_digest.py` reads `cache.db` path incorrectly (wrong volume mount path) | Low | Low | Verify path via `docker compose exec data_platform ls /app/var/crm_data/cache.db` before implementation |
| Phase-03 `crm_etl_run` schema differs from what this phase expects | Medium | Low | Phase-03 is designed in tandem; coordinate column list. `serving_version_consumed` is additive — backward compatible |

---

## Security Considerations

- `serving_version.json` contains only structural metadata (version int, timestamp, table-name hash). No PII, no credentials. Read-only access within CRM container is sufficient.
- `crm_etl_run.serving_version_consumed` is internal health data in `cache.db` (not exposed externally).
- `morning_digest.py` opens `cache.db` read-only from the `data_platform` container (via `crm_data:/app/var/crm_data:ro` volume mount, `docker-compose.yml:41`). No write path to CRM data from Dagster.
- The push trigger path (`POST /admin/refresh`) retains its `CRM_REFRESH_TOKEN` auth header (`crm_sync.py:44-45`). The polling path has no network surface — purely file-based.

---

## Next Steps

- **Phase-06** (CRM service-boundary ADR): the version-poll mechanism is referenced in the ADR as the consumption contract interface. The ADR formalizes it as the boundary protocol: CRM is a consumer that self-declares readiness by updating `crm_etl_run.serving_version_consumed`.
- **CRM repoint** (phase-06): once `CRM_OLAP_PATH` is repointed to `sapo_export_latest.duckdb` (phase-06 scope), the version poller and snapshot isolation complete the full decoupling: CRM reads from snapshot, polls version, self-refreshes.
- **Alert escalation**: if lag > threshold (e.g., 3 versions = ~3 pipeline runs behind), consider adding a Lark alert from `morning_digest.py` beyond just surfacing the field. Defer until lag pattern is observed in practice.

---

## Unresolved Questions

1. **CRM Go package layout**: the existing CRM Go codebase structure is not fully mapped (research focused on Python sync layer). Before implementing the poller, read the Go app's main entrypoint to locate where to wire `StartServingVersionPoller`. File path `crm/src/infrastructure/serving_version_poller.go` is a placeholder — adjust to actual package.
2. **Phase-03 `crm_etl_run` schema**: exact column list needs coordination with phase-03 implementer to avoid migration conflicts. The `serving_version_consumed INTEGER DEFAULT 0` addition must be compatible with whatever schema phase-03 finalizes.
3. **`cache.db` path in `morning_digest.py`**: verify the exact mount path available to `data_platform` for reading `crm_data`. Current docker-compose shows `crm_data:/app/var/crm_data:ro` (`docker-compose.yml:41`), making it `/app/var/crm_data/cache.db` — but confirm `cache.db` is at the root of that volume (not in a subdirectory) before coding.
