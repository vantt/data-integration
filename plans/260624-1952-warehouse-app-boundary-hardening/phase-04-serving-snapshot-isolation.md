---
title: "Serving Snapshot Isolation"
description: "Extend build_standalone_export with main_marts aliases + version sidecar; repoint BI consumers to snapshot to eliminate the Metabase-holds-lock-blocks-bootstrap problem."
status: pending
priority: P1
effort: 3h
branch: main
tags: [serving, duckdb, metabase, snapshot, isolation]
created: 2026-06-24
---

## Context Links

- Research report: `plans/reports/from-research-to-planner-boundary-hardening-findings-260624-1952-report.md`
- Parent plan: `plans/260624-1952-warehouse-app-boundary-hardening/plan.md`
- Source: `scripts/provisioning/build_standalone_export.py`
- Source: `scripts/provisioning/bootstrap_serving_views.py` (lock note :8-23, alias logic :146)
- Source: `orchestration/assets/serving.py` (build_standalone_export asset :140-171)
- Source: `orchestration/definitions.py` (nightly job :179-204, realtime/incremental :80-98)
- Source: `docker-compose.yml` (metabase :51-71, rill :73-95, evidence :97-119, detail_view :142-165, crm :167-212)
- Source: `Dockerfile.evidence` (CMD copies olap.duckdb at container start :33)
- Source: `evidence/sources/datalake/connection.yaml` (filename: olap-serving.duckdb)
- Consumer config: `rill/connectors/duckdb.yaml`, `rill/models/src_*.yaml` (parquet-direct, no repoint needed)
- Consumed by phase-05: `serving_version.json` sidecar written here, polled there

---

## Overview

**Priority:** P1 — unblocks bootstrap_serving_views.py from requiring Metabase stop; also enables phase-05 durable trigger.

**Current status:** Pending. Gap identified: `build_standalone_export.py` materializes only `main.*` base tables from olap.duckdb views, but does NOT recreate `main_marts.*` alias views (`bootstrap_serving_views.py:146`). Metabase SQL cards use `FROM main_marts.<table>` — switching Metabase to the snapshot without this fix breaks all such cards. Additionally, no version marker exists on the snapshot, blocking phase-05.

**What this phase does:**
1. Extend `build_standalone_export.py` to also create `main_marts.*` alias views inside the snapshot.
2. Write `serving_version.json` atomically alongside `sapo_export_latest.duckdb`.
3. Decide and justify snapshot cadence (nightly-only vs. after-every-serving-build).
4. Repoint Metabase, Evidence, DetailView to read `sapo_export_latest.duckdb` instead of live `olap.duckdb`.
5. Rill does NOT read olap.duckdb — reads parquet directly via `RILL_EXPORT_ROOT` — no repoint needed.
6. CRM repoint (from `olap.duckdb` to `sapo_export_latest`) is designed here architecturally but implemented in phase-06.

**Outcome:** `bootstrap_serving_views.py` no longer requires stopping Metabase, because Metabase reads the snapshot (a separate file) while bootstrap writes `olap.duckdb`.

---

## Key Insights

- **Lock root cause** (`bootstrap_serving_views.py:8-23`): Metabase's open read connection holds a DuckDB shared lock that blocks the exclusive write lock required by bootstrap. Even with `read_only=true` in its JDBC URL, the lock is taken. Verified empirically 2026-06-10.
- **build_standalone_export opens olap.duckdb READ_ONLY** (`build_standalone_export.py:141`): `ATTACH ... (READ_ONLY)`. This is already lock-safe — it does NOT block bootstrap. The problem is exclusively that Metabase holds the live olap.duckdb open.
- **Snapshot already exists and is atomic** (`build_standalone_export.py:183-191`): `os.replace(out_tmp, out_final)` then `shutil.copy2 + os.replace` to `sapo_export_latest.duckdb.tmp` → `sapo_export_latest.duckdb`. Atomicity already correct.
- **main_marts alias gap** (`build_standalone_export.py:148-178`): enumerates `table_type = 'VIEW'` from `main` schema, materializes as `CREATE TABLE x AS SELECT * FROM src.x`. No `CREATE SCHEMA main_marts` and no alias views. Metabase SQL cards referencing `FROM main_marts.fact_orders` will fail with CatalogException.
- **Evidence copies olap.duckdb at container start** (`Dockerfile.evidence:33`): `cp /app/var/data_lake/serving/olap.duckdb /app/sources/datalake/olap-serving.duckdb`. This is a one-time copy at startup; the running Evidence instance uses its own local copy and is already decoupled from live olap.duckdb. Repoint = change the `cp` source to `sapo_export_latest.duckdb`.
- **DetailView reads `OLAP_DB_PATH`** (`docker-compose.yml:155`): `OLAP_DB_PATH=/app/var/data_lake/serving/olap.duckdb`. Repoint = env var change. DetailView opens with `read_only=True` (memory note); :ro volume mount is defense-in-depth.
- **Rill reads parquet directly** (`rill/models/src_fact_orders.yaml:6`): `read_parquet('{{ .env.RILL_EXPORT_ROOT }}/fact_orders.parquet')`. No DuckDB file reference. No repoint needed.
- **Cadence decision** (open question #3): `build_standalone_export` is currently nightly-only (`definitions.py:195`). It opens olap.duckdb READ_ONLY so it is lock-safe and CAN run after every `build_serving_db`. Running it after every serving build (realtime/incremental/filedrop) means Metabase staleness follows pipeline cadence (~every webhook flush, 4-10 min), not 24h. Cost: ~5-30s extra per pipeline run (DuckDB copy of ~20 marts). Recommendation: **add `build_standalone_export` to all pipeline jobs** (realtime, incremental, filedrop jobs) — the existing `duckdb_lock` concurrency key already serializes it with `build_serving_db`. The nightly job already includes it (`definitions.py:195`). Staleness tolerance: Metabase is used for monitoring/decisions by operators; 24h is not acceptable for realtime ops context. After-every-build is the correct choice.
- **TZ note**: snapshot is materialized from already-computed view rows (data values fixed at parquet-write time). `SET TimeZone` in `build_standalone_export.py:137` covers timestamp display in DuckDB sessions against the snapshot, consistent with main pipeline. No additional action needed.

---

## Requirements

### Functional

1. `build_standalone_export.py` creates `main_marts` schema in the output snapshot and populates alias views `main_marts.<table> → main.<table>` for every materialized table.
2. `build_standalone_export.py` writes `serving_version.json` atomically to `OUT_DIR` alongside `sapo_export_latest.duckdb`. Contents: `version` (monotonic int), `built_at` (ICT ISO-8601 string), `table_list_hash` (SHA-256 of sorted table name list, hex).
3. Metabase is repointed to read `sapo_export_latest.duckdb` via its database connection config (API update or UI). Existing `FROM main_marts.*` SQL cards must work without changes.
4. Evidence Dockerfile CMD is changed to copy `sapo_export_latest.duckdb` instead of `olap.duckdb` at container start.
5. DetailView `OLAP_DB_PATH` env var is changed to point to `sapo_export_latest.duckdb` path.
6. All pipeline jobs that include `build_serving_db` also include `build_standalone_export` (except jobs where the asset was already absent by design).
7. `bootstrap_serving_views.py` can run without stopping Metabase, because Metabase no longer holds `olap.duckdb` open.

### Non-functional

- Atomic write: `serving_version.json` must be written via tmp-then-replace to avoid a reader seeing a partial file.
- Backward compat: existing `main.*` table layout in the snapshot is unchanged; only additions (new schema + alias views).
- No new infra, no new Docker images beyond config changes.
- Windows/Linux dual-runtime: use `os.path.join`, forward-slash in DuckDB SQL strings.

---

## Architecture

### Data Flow

```
build_serving_db asset
  └─ refresh_rolling.py → updates parquet + olap.duckdb views (olap.duckdb open RW)
        │
        ▼
build_standalone_export asset  [serialized by duckdb_lock]
  └─ build_standalone_export.py
        ├─ ATTACH olap.duckdb (READ_ONLY)          ← lock-safe, never blocks bootstrap
        ├─ CREATE TABLE main.<t> AS SELECT * FROM src.<t>  [existing behavior]
        ├─ CREATE SCHEMA main_marts                         [NEW]
        ├─ CREATE VIEW main_marts.<t> AS SELECT * FROM main.<t>  [NEW, per table]
        ├─ atomic write: sapo_export_<ts>.duckdb.tmp → sapo_export_<ts>.duckdb
        ├─ atomic copy: → sapo_export_latest.duckdb          [existing]
        └─ atomic write: serving_version.json.tmp → serving_version.json  [NEW]

serving/standalone/
  ├─ sapo_export_latest.duckdb   ← Metabase, Evidence, DetailView, CRM (phase-06) read here
  │    ├─ schema: main
  │    │    └─ tables: fact_orders, dim_customers, ...  (materialized, no parquet paths)
  │    └─ schema: main_marts
  │         └─ views: fact_orders → main.fact_orders, ... (alias views)
  └─ serving_version.json        ← phase-05 CRM version poll reads here

olap.duckdb  (unchanged)
  └─ consumed by: bootstrap_serving_views.py (RW), build_standalone_export (RO attach)
  └─ NO LONGER consumed by: Metabase, Evidence, DetailView (after this phase)
```

### Component Interactions

| Consumer | Before | After | Change vector |
|---|---|---|---|
| Metabase | reads live `olap.duckdb` via JDBC | reads `sapo_export_latest.duckdb` | DB connection update (API/UI) |
| Evidence | copies `olap.duckdb` at container start | copies `sapo_export_latest.duckdb` | `Dockerfile.evidence` CMD |
| DetailView | `OLAP_DB_PATH=.../serving/olap.duckdb` | `OLAP_DB_PATH=.../serving/standalone/sapo_export_latest.duckdb` | `docker-compose.yml` env |
| Rill | reads parquet directly | unchanged | no change |
| CRM | reads `CRM_OLAP_PATH=.../serving/olap.duckdb` | reads `sapo_export_latest.duckdb` | phase-06 (not this phase) |
| bootstrap_serving_views.py | requires Metabase stopped | runs freely (Metabase reads snapshot) | no code change to bootstrap |

### Version Sidecar Schema

```json
{
  "version": 142,
  "built_at": "2026-06-24T21:30:00+07:00",
  "table_list_hash": "a3f9b2..."
}
```

- `version`: incremented by reading prior `serving_version.json` if present, else starts at 1. This is an append-and-replace pattern — no external counter needed.
- `table_list_hash`: SHA-256 of `",".join(sorted(view_names))` hex digest. Lets CRM detect schema additions without diffing individual names.
- `built_at`: ICT timezone, matching pipeline TZ convention (`ZoneInfo("Asia/Ho_Chi_Minh")` already used in `build_standalone_export.py:125`).

---

## Related Code Files

### Modify
- `scripts/provisioning/build_standalone_export.py` — add main_marts alias views + version sidecar logic
- `Dockerfile.evidence` — change `cp` source from `olap.duckdb` to `sapo_export_latest.duckdb`
- `docker-compose.yml` — change DetailView `OLAP_DB_PATH` env; add `build_standalone_export` to pipeline jobs (via `orchestration/definitions.py`)
- `orchestration/definitions.py` — add `build_standalone_export` asset to realtime, incremental, filedrop jobs

### No code change
- `scripts/provisioning/bootstrap_serving_views.py` — unchanged; benefit is environmental (Metabase no longer holds live DB)
- `rill/` — unchanged; reads parquet

### Metabase DB config (runtime, not file-tracked)
- Metabase database connection path: updated via Metabase Admin UI or PUT `/api/database/:id` to point to new file path.
- Existing SQL cards: no change needed (main_marts schema present in snapshot after this fix).

---

## Implementation Steps

1. **Extend `build_standalone_export.py`: main_marts aliases**

   After all `CREATE TABLE` materializations succeed (after the `for view_name in view_names` loop at line 168-177), add:
   ```python
   # Create main_marts alias schema so SQL referencing main_marts.<table> resolves.
   # Mirrors bootstrap_serving_views.py:112 which does the same in olap.duckdb.
   con.sql("CREATE SCHEMA IF NOT EXISTS main_marts")
   for view_name in view_names:
       if view_name in row_counts:  # only alias successfully materialized tables
           con.sql(
               f"CREATE VIEW main_marts.{view_name} AS SELECT * FROM main.{view_name}"
           )
   ```
   Add `aliases_created = len([v for v in view_names if v in row_counts])` to the summary print.

2. **Extend `build_standalone_export.py`: version sidecar**

   Add a `_write_version_sidecar(out_dir, view_names)` function:
   - Reads `serving_version.json` from `out_dir` if it exists to get prior `version` int (defaults to 0).
   - Computes new `version = prior + 1`.
   - Computes `table_list_hash = hashlib.sha256(",".join(sorted(view_names)).encode()).hexdigest()`.
   - Builds `built_at` as `datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat()`.
   - Writes JSON to `serving_version.json.tmp` then atomically renames to `serving_version.json` via `os.replace`.
   - Add `import hashlib, json` imports.
   
   Call `_write_version_sidecar(OUT_DIR, view_names)` after the `_gc_old_exports` call (line 195), before the summary print. This ensures version is only incremented on a successful build.

3. **Update `orchestration/definitions.py`: add `build_standalone_export` to non-nightly jobs**

   Add `AssetSelection.assets(serving.build_standalone_export)` to:
   - `pipeline_sapo_v2_realtime_job` (`definitions.py:82`)
   - `pipeline_sapo_v2_incremental_job` (`definitions.py:96`)
   - `ingest_sheets_sync_job` (`definitions.py:116-126`)
   - `ingest_filedrop_shopee_job` (`definitions.py:137-147`)
   - `ingest_filedrop_misa_job` (`definitions.py:151-161`)
   - `ingest_filedrop_misa_account_ledger_job` (`definitions.py:167-176`)
   
   The nightly job (`_nightly_batch_selection`, line 195) already includes it.

4. **Update `Dockerfile.evidence`: repoint source file**

   Change CMD line (`:33`):
   ```
   # Before:
   cp /app/var/data_lake/serving/olap.duckdb /app/sources/datalake/olap-serving.duckdb
   # After:
   cp /app/var/data_lake/serving/standalone/sapo_export_latest.duckdb /app/sources/datalake/olap-serving.duckdb
   ```
   `evidence/sources/datalake/connection.yaml` (`filename: olap-serving.duckdb`) is unchanged — the local filename inside the container stays the same.

5. **Update `docker-compose.yml`: repoint DetailView**

   Change DetailView env (`docker-compose.yml:155`):
   ```yaml
   # Before:
   - OLAP_DB_PATH=/app/var/data_lake/serving/olap.duckdb
   # After:
   - OLAP_DB_PATH=/app/var/data_lake/serving/standalone/sapo_export_latest.duckdb
   ```
   The existing volume mount `./app_data/data_lake:/app/var/data_lake:ro` (`docker-compose.yml:162`) already covers `serving/standalone/` — no new volume line needed.

6. **Repoint Metabase DB connection**

   Metabase database connection path is stored in Metabase's own application DB (H2 or configured external). Update via:
   - Metabase Admin UI → Databases → edit the Sapo DuckDB connection → update the "Database file" path to `/app/var/data_lake/serving/standalone/sapo_export_latest.duckdb`.
   - OR: `PUT /api/database/:id` with `{"details": {"db": "/app/var/data_lake/serving/standalone/sapo_export_latest.duckdb"}}`.
   
   The existing volume `./app_data/data_lake:/app/var/data_lake:ro` (`docker-compose.yml:67`) already covers the new path.
   
   After update: run a test query `SELECT count(*) FROM main_marts.fact_orders` in Metabase SQL editor to verify alias schema resolved.

7. **Deploy sequence**

   ```
   # 1. Build/restart data_platform (picks up definitions.py change)
   docker compose up -d --build data_platform
   
   # 2. Manually trigger build_standalone_export once to populate snapshot with main_marts aliases
   docker compose exec data_platform python scripts/provisioning/build_standalone_export.py
   
   # 3. Verify serving_version.json written
   # (check app_data/data_lake/serving/standalone/serving_version.json)
   
   # 4. Update Metabase DB connection (UI or API)
   
   # 5. Rebuild Evidence (picks up Dockerfile.evidence change)
   docker compose up -d --build evidence
   
   # 6. Restart DetailView (picks up docker-compose.yml env change)
   docker compose up -d detail_view
   
   # 7. Verify: run bootstrap_serving_views.py WITHOUT stopping Metabase
   docker compose exec data_platform python scripts/provisioning/bootstrap_serving_views.py
   # → must succeed with no lock error
   ```

---

## Todo List

- [ ] Add `main_marts` schema + alias view creation to `build_standalone_export.py` (step 1)
- [ ] Add `_write_version_sidecar()` function to `build_standalone_export.py` (step 2)
- [ ] Add `build_standalone_export` asset to 6 non-nightly jobs in `definitions.py` (step 3)
- [ ] Update `Dockerfile.evidence` CMD source path (step 4)
- [ ] Update `docker-compose.yml` DetailView `OLAP_DB_PATH` (step 5)
- [ ] Repoint Metabase DB connection to snapshot path (step 6)
- [ ] Run deploy sequence and verify (step 7)
- [ ] Validate: bootstrap_serving_views.py succeeds without stopping Metabase

---

## Success Criteria

1. **main_marts aliases present in snapshot**: `duckdb -c "SHOW ALL TABLES" app_data/data_lake/serving/standalone/sapo_export_latest.duckdb` shows tables in both `main` and `main_marts` schemas.
2. **Version sidecar written**: `app_data/data_lake/serving/standalone/serving_version.json` exists with valid JSON after every `build_standalone_export` run; `version` increments on each run.
3. **Metabase queries resolve**: `SELECT count(*) FROM main_marts.fact_orders` in Metabase SQL editor returns non-zero row count without error.
4. **Bootstrap without Metabase stop**: `bootstrap_serving_views.py` completes successfully while Metabase is running. No "Conflicting lock" error in output.
5. **Evidence builds from snapshot**: `docker compose up -d --build evidence` succeeds; Evidence site loads and serves data.
6. **DetailView reads snapshot**: DetailView serves customer/order data after env var change; no `FileNotFoundError` or DuckDB error in logs.
7. **Cadence working**: After a realtime pipeline run, `serving_version.json` version increments (confirming `build_standalone_export` ran in the job chain).

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `sapo_export_latest.duckdb` not yet present when Evidence/DetailView start on fresh deploy | Medium | High (container crash loop) | `build_standalone_export.py` is run in `data_platform` startup command OR add safety check in Dockerfile.evidence CMD: `if [ ! -f ... ]; then cp olap.duckdb ...; fi` fallback |
| Metabase SQL card uses unqualified `FROM fact_orders` (no schema prefix) | Low | Low | These already work against `main` schema tables — no regression; only `main_marts.*` refs need the alias views |
| `serving_version.json` read race (CRM reads partial write) | Low | Low | Atomic write via tmp-rename pattern; JSON is small (<200 bytes); OS guarantees rename atomicity on same filesystem |
| Windows PermissionError on `serving_version.json.tmp` rename if prior run left stale tmp | Low | Low | Add same stale-tmp sweep pattern used in `_sweep_stale_tmp()` (`:100-112`) |
| Metabase DuckDB driver version incompatibility with `sapo_export_latest.duckdb` format | Very low | High | Snapshot is created by the same DuckDB version used in `data_platform`; file format identical to `olap.duckdb` |
| DetailView opens snapshot for RW by mistake (writes would corrupt) | Very low | High | Volume mount is already `:ro` (`docker-compose.yml:162`); DetailView code uses `read_only=True` per memory note |

---

## Security Considerations

- `serving_version.json` contains only metadata (version int, timestamp, hash of table names). No PII, no credentials.
- Snapshot file is served via `data_fileserver` (Caddy, `docker-compose.yml:121-141`, basic_auth protected). No change to existing auth posture.
- DetailView and Evidence read the snapshot via `:ro` volume mount — no write path exposed.
- Metabase connection path change: Metabase API endpoint (`PUT /api/database/:id`) requires Metabase admin credentials. Document in ops runbook.

---

## Next Steps

- **Phase-05** consumes `serving_version.json` written here to implement durable CRM trigger polling.
- **Phase-06** (CRM service-boundary ADR): documents CRM repoint from `olap.duckdb` to `sapo_export_latest.duckdb` as part of the consumption contract spec. The `CRM_OLAP_PATH` env (`docker-compose.yml:179`, `crm/src/config.py:37`) needs updating, but is deferred to phase-06 design.
- **bootstrap_serving_views.py**: after this phase ships, update the warning comment at `:8-23` to reflect that Metabase no longer needs to be stopped (only relevant if both olap.duckdb writers run concurrently, which they don't).

---

## Unresolved Questions

1. **Metabase connection update method**: does the team prefer UI-based update (manual, one-time) or a scripted `PUT /api/database/:id` call in the deploy runbook? The scripted approach is repeatable on fresh deploys. Currently leaning toward a deploy-script call to avoid manual error.
2. **Fresh-deploy ordering**: `sapo_export_latest.duckdb` won't exist on a fresh environment until the first pipeline run. Evidence and DetailView would crash-loop waiting for it. Need a startup guard or a `docker compose up` ordering constraint. Consider adding a readiness check script or a fallback `cp olap.duckdb .../sapo_export_latest.duckdb` in `data_platform` startup.
