---
title: "Verification Protocol — Sapo std gate + naming migration"
description: "Toolkit of exact physical check commands, cadence rules, lock-handling guidance, and per-step rollback actions."
---

# Verification Protocol

## The Cadence Rule (NON-NEGOTIABLE)

**Every atomic step ends with its checkpoint. The pipeline must be GREEN before the next step begins. Every step is a single git commit so it is independently revertible.**

GREEN = ALL of the following:
1. `dbt parse` exits 0 (no syntax/ref errors)
2. Selective `dbt build` for the changed model(s) + direct consumers exits 0 with zero test failures
3. Affected-mart parquet checksum = pre-step baseline (or matches expected delta if a rename step)
4. **MANDATORY FINAL GATE — one FRESH `ingest_sapo_realtime_job` run that STARTED AFTER your change** completes `RUN_SUCCESS` with `tests: N passed, 0 failed` and no `STEP_FAILURE`. A pre-change run does NOT count. This is the primary end-to-end proof: a single orchestrated run exercises ingestion → dbt build → 341 tests → serving publish → rill. If it is green and bug-free, the step is safe.

**NEVER proceed to the next step on a red check.**

### Why the fresh Dagster run is the decisive check
A selective `dbt build` (#2) only builds the models you named — it can miss breakage in a model outside your selection, in the ingestion step, in serving publish, or in rill. The realtime job rebuilds the FULL mart graph + runs ALL tests + republishes every run, so one fresh green run is the truest "pipeline still runs, no bug" signal. Make it the closing action of every step.

### How to get a FRESH run (and know it's fresh)
- **Pause→change→resume→observe** (cleanest): pause schedules (avoids an auto-run firing mid-edit on half-applied refs → false failure), apply + manually verify the change, resume schedules, then watch the FIRST run after resume — that run is your fresh gate.
- **Trigger manually** instead of waiting ≤3 min: `docker exec data_platform sh -c "dagster job launch -j ingest_sapo_realtime_job -f /app/orchestration/definitions.py"`.
- **Confirm freshness:** note the run id / start time from `dagster run list --limit 1` and verify it is later than your edit; never accept a run that started before the change.

---

## Lock-Handling Guidance

> **⚠️ REALITY CHECK (2026-06-03): CLI `dagster schedule stop/start -f <file>` is INEFFECTIVE on this daemon.** It spins up an ephemeral code-location whose origin ID differs from the running daemon's, so the instigator-state override never reaches the daemon — the schedule keeps firing every 3 min (confirmed via `SchedulerDaemon` "Completed scheduled launch" logs). `dagster schedule list -f` likewise shows a misleading `[STOPPED]`. **Do NOT rely on Strategy A pausing via CLI.** To truly pause, use the Dagster UI toggle. Otherwise: accept that an auto-run may fire mid-edit and transiently FAIL (self-heals on the next tick), and rely on the real gate = a FRESH green run AFTER edits + checksum match. **Minimize the failure window:** create the new `std_` model FIRST (a tick here is safe — consumers still ref `stg_`), THEN repoint consumers.

### The conflict

`ingest_sapo_realtime_job` runs every 3 min and holds the DuckDB write-lock during its build phase. A concurrent manual `dbt build` on the host will conflict.

### Two strategies — choose per step

#### Strategy A: Pause schedules, run manual build, resume (PREFERRED for structural changes)

```bash
# 1. Pause the two hot schedules (inside container)
docker exec data_platform sh -c "
  dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py &&
  dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py
"

# 2. Wait for any in-flight run to finish (check status)
docker exec data_platform sh -c "dagster run list --limit 3"
# Wait until no run shows status=STARTED for ingest_sapo_realtime_job

# 3. Run your manual dbt build
python transformation\scripts\run_dbt.py --select <model>+

# 4. Resume schedules
docker exec data_platform sh -c "
  dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py &&
  dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py
"
```

#### Strategy B: Ride the next auto-run (PREFERRED for verifying parse-only or config changes)

1. Apply the code change (dbt SQL/YAML only).
2. Run `dbt parse` (lock-free — never touches the DB).
3. Wait for the next scheduled `ingest_sapo_realtime_job` to complete (≤3 min).
4. Read logs: `docker logs data_platform --since 5m | grep -iE "RUN_SUCCESS|RUN_FAILURE|tests:|ERROR"`.
5. Check parquet checksum.

**Use Strategy A** when the change touches incremental model logic (full-refresh required) or when you need immediate verification. **Use Strategy B** when the change is to views/tests only and you can tolerate ≤3 min wait.

---

## Toolkit — Exact Commands

### T1 — dbt parse (lock-free, instant, catches all ref/syntax errors)

```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"
```

PASS: exits 0, output shows `Parsing` → no `ERROR` lines.

---

### T2 — Selective build + test

```bash
# Option A: via host wrapper (auto-finds dbt in dlt venv or PATH)
python transformation\scripts\run_dbt.py --select <model>+

# Option B: directly inside container (when schedules are paused)
docker exec data_platform sh -c "cd /app && dbt build --select <model>+ --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -20"

# Full-refresh (required after renaming incremental models in Phase 4)
docker exec data_platform sh -c "cd /app && dbt build --select <model>+ --full-refresh --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -20"
```

PASS: exits 0, "Completed successfully", zero `WARN`/`ERROR`/`FAIL` lines.

---

### T3 — Parquet checksum (lock-free, PREFERRED per-step)

Run this Python snippet on the host — reads the newest parquet under each mart's rolling folder. Compute once before the step (baseline) and once after (post). Values must match.

```python
import duckdb, glob, os

EXPORT_BASE = r"app_data\data_lake\export\marts\rolling"

MARTS = {
    "dim_products":                 ["product_id", "sku"],
    "dim_sku_alias":                ["sku_alias_key"],
    "dim_price_lists":              ["price_list_id"],
    "fact_variant_prices_snapshot": ["variant_id", "price_list_id", "price_value"],
    "fact_order_returns":           ["return_id", "refund_amount", "return_quantity"],
    "fact_order_costs":             ["order_id", "amount"],
    "fact_orders":                  ["order_id", "gross_revenue", "net_revenue", "discount_amount"],
    "fact_sales":                   ["order_id", "gross_revenue", "net_revenue"],
    "mart_inventory_health":        ["variant_id", "location_id", "on_hand"],
    "mart_data_quality":            ["dq_key", "total_orders", "cogs_rate_pct"],
}

con = duckdb.connect(read_only=False)
results = {}
for mart, key_cols in MARTS.items():
    folder = os.path.join(EXPORT_BASE, mart)
    files = sorted(glob.glob(os.path.join(folder, "*.parquet")))
    if not files:
        results[mart] = {"error": "no parquet found"}
        continue
    newest = files[-1]
    col_list = ", ".join(key_cols)
    try:
        row = con.execute(
            f"SELECT COUNT(*) AS n, SUM(hash({col_list})) AS chk FROM read_parquet('{newest}')"
        ).fetchone()
        results[mart] = {"rows": row[0], "checksum": row[1], "file": os.path.basename(newest)}
    except Exception as e:
        results[mart] = {"error": str(e)}

for m, r in results.items():
    print(f"{m}: {r}")
```

Save output to `plans/260603-1730-sapo-std-gate-and-naming/snapshots/pre_<phase>_<step>.txt` before each step and `post_<phase>_<step>.txt` after. Diff must show zero delta on unaffected marts; renamed-column marts must show same row count + recalculated checksum that verifies values unchanged (re-run checksum using NEW column names to confirm equality).

---

### T4 — Dagster run health

```bash
# Recent run status (last 3)
docker exec data_platform sh -c "dagster run list --limit 3"

# Logs from last 5 minutes — look for RUN_SUCCESS / RUN_FAILURE / ERROR
docker logs data_platform --since 5m 2>&1 | grep -iE "RUN_SUCCESS|RUN_FAILURE|tests:|ERROR"

# A green realtime run with "tests: X passed, 0 failed" proves end-to-end pipeline health.
```

PASS: most recent `ingest_sapo_realtime_job` shows no FAILURE; test line shows 0 failed.

---

### T5 — HOP row counts (read-only, lock-safe)

```bash
# Only run when Dagster is NOT mid-build (check T4 first)
python scripts/testing/verify_hops_readonly.py
```

PASS: all hop counts within expected bounds (no unexpected zeros).

---

### T6 — DQ mart parquet spot-check

```python
import duckdb, glob, os
folder = r"app_data\data_lake\export\marts\rolling\mart_data_quality"
newest = sorted(glob.glob(os.path.join(folder, "*.parquet")))[-1]
print(duckdb.query(f"SELECT * FROM read_parquet('{newest}')").df())
```

PASS: `total_orders` > 0; `cogs_rate_pct`, `fulfillment_coverage_pct` are non-null and plausible.

---

### T7 — App smoke tests

```bash
# detailView order detail (financial tab)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/orders/<any_valid_order_code>/tab/financial
# PASS: 200

# Metabase olap serving check (query mart via olap.duckdb — read-only, host has duckdb python)
python -c "import duckdb; print(duckdb.connect(r'app_data\data_lake\serving\olap.duckdb', read_only=True).execute('SELECT COUNT(*) FROM fact_orders').fetchone())"
# PASS: returns a row count > 0  (olap path in container = /app/var/data_lake/serving/olap.duckdb)
```

---

### T8 — Metabase / serving rebuild sequence (for column-rename steps)

Use ONLY when a published column is renamed (Phases 1, 2, 3):

```bash
# 1. Stop Metabase
docker compose stop metabase

# 2. Rebuild serving views (binder requires fresh view definitions)
python scripts/provisioning/bootstrap_serving_views.py

# 3. Start Metabase
docker compose start metabase

# 4. Verify no binder error in output of step 2 — look for "Error" or "binder"
# 5. Open Metabase, run a dashboard query touching renamed column, confirm no "unknown column"
```

> **⚠️ GLOB-UNION STALE-SCHEMA CAVEAT (learned P1 2a, 2026-06-04):** serving views read `read_parquet('.../rolling/<mart>/*.parquet')` — a GLOB over MULTIPLE files with `union_by_name`. Right after a column rename, an OLD pre-rename parquet still co-exists with the new one until GC removes it → the union exposes the OLD column name, so `bootstrap_serving_views.py` rebuilds the view with the STALE name. **Fix:** wait for the rolling GC to drop old-schema files (or remove them), THEN re-run bootstrap. > **⚠️ INCREMENTAL-WATERMARK RENAME CAVEAT (learned P2, 2026-06-04):** if you rename a column that an **incremental** model uses as its cursor/watermark (e.g. `dim_customers` incremental `WHERE … > (SELECT MAX(last_modified_at) FROM {{ this }})`, or `src_*` `_dlt_load_id`), the EXISTING physical table still has the OLD column name → the next incremental run throws a DuckDB **Binder Error** (and Dagster RUN_FAILURE) until the table is recreated. **Fix:** run `dbt run --select <model> --full-refresh` immediately after the edit (before the next scheduled run fires), then verify. Check whether the renamed column appears in an incremental `WHERE`/`QUALIFY`/`MAX()` over `{{ this }}` BEFORE the cutover to pre-empt the transient failures.

**Verify (mandatory for rename steps):** (a) query `olap.duckdb` INSIDE a container (`docker exec detail_view sh -c "python3 -c \"import duckdb;c=duckdb.connect('/app/var/data_lake/serving/olap.duckdb',read_only=True);print([x[0] for x in c.execute('DESCRIBE SELECT * FROM <mart>').fetchall()])\""`) and confirm ONLY the NEW column name appears; (b) confirm no remaining rolling parquet has the OLD column (`DESCRIBE` each file). Both must pass before commit.

---

### T9 — detailView image rebuild (for detailView code changes)

```bash
docker compose up -d --build detail_view
# Wait for container to be healthy, then:
curl -s http://localhost:8000/orders/<valid_order_code>/tab/financial | grep -i "vat\|discount\|revenue"
```

PASS: page returns 200 with expected financial data visible in HTML.

---

## Per-Step Rollback Action

| Situation | Rollback |
|-----------|---------|
| dbt parse fails after edit | `git checkout -- <file>` on the changed SQL/YAML; re-parse |
| dbt build fails (view-only step) | `git checkout -- <file>`; re-parse; no serving rebuild needed |
| dbt build fails (incremental rename, Phase 4) | `git checkout -- <file>`; `git mv` files back; drop new `*_v2` tables in DuckDB; re-build old model |
| Parquet checksum delta on unaffected mart | Stop — investigate which upstream changed unexpectedly; `git revert HEAD` |
| Metabase binder error after column rename | Re-run `bootstrap_serving_views.py`; if error persists, revert SQL in that mart + re-run script |
| detailView returns 500 after rebuild | Revert detailView code changes (`git checkout -- detailView/`); `docker compose up -d --build detail_view` |
| Dagster run fails after schema change | Pause schedules; investigate logs; revert offending dbt model; re-parse; resume |

**Key rule:** Each atomic step = one git commit. Any failed check = `git revert HEAD` for that step, then investigate before proceeding.

---

## Schedule Names (for reference)

| Schedule | Cron | When to pause |
|----------|------|---------------|
| `ingest_sapo_realtime_schedule` | `*/3 * * * *` | Always pause during manual builds |
| `ingest_sapo_incremental_schedule` | `*/10 0-2,4-23 * * *` | Pause during extended manual sessions |
| `transform_batch_nightly_schedule` | `0 3 * * *` | Only if running full overnight rebuild |

Commands:
```bash
# Stop
docker exec data_platform sh -c "dagster schedule stop <SCHEDULE_NAME> -f /app/orchestration/definitions.py"
# Start
docker exec data_platform sh -c "dagster schedule start <SCHEDULE_NAME> -f /app/orchestration/definitions.py"
```
