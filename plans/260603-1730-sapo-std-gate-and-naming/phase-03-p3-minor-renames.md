---
title: "Phase 3 — P3 optional minor renames"
description: "Low-priority cosmetic renames: dob→birth_date, sex→gender, loyalty_point→loyalty_points, zip→postal_code, client_details→client_info. Safe to skip."
status: pending
priority: P3
effort: 1h
---

# Phase 3 — P3 minor renames (optional)

## Context links
- Naming rules: `docs/architecture/naming-conventions.md` §1 (no abbreviations)
- Verification toolkit: `plans/260603-1730-sapo-std-gate-and-naming/verification-protocol.md`
- Blocked by: Phase 2 complete (or can run on top of P0 if P1/P2 are deferred)

---

## Overview
- **Priority:** P3 — cosmetic; zero semantic impact; safe to skip indefinitely
- **Status:** pending
- **Lock strategy:** Strategy A for all `dbt build` steps. Parse is lock-free.
- **Decision gate:** Only proceed if schema cleanliness justifies the serving rebuild + detailView image rebuild + blueprint update cost. The same coordinated deploy window as P1/P2 applies.
- **Explicitly excluded:** `order_code → order_number` — rejected per naming-conventions.md §2. `order_code` is alphanumeric (`260316A6VJXGMT`); `_number` implies a numeric sequence. Final decision, not revisitable in this plan.

---

## Rename table

| # | Current | New | Rule | Primary scope |
|---|---------|-----|------|--------------|
| R12 | `dob` | `birth_date` | §1 no abbreviations | `std_customers` → `dim_customers_base`, `dim_customers`, detailView, blueprints |
| R13 | `sex` | `gender` | §1 no abbreviations | same as R12 |
| R14 | `loyalty_point` | `loyalty_points` | English plural (a balance/count) | same as R12 |
| R15 | `shipping_zip` / `billing_zip` | `shipping_postal_code` / `billing_postal_code` | §1 no abbreviations | `std_orders`; `fact_orders` only if columns appear in its SELECT (pre-flight check required) |
| R16 | `client_details` | `client_info` | minor clarity | `std_orders`, `fact_orders` line 152, detailView if referenced |

---

## PRE-FLIGHT CHECKS (read-only, before any edit)

Run these before touching any file:

```bash
# R15: confirm whether fact_orders SELECT outputs shipping_zip / billing_zip
grep -n "shipping_zip\|billing_zip" transformation/models/marts/sales/fact_orders.sql
# If 0 hits → R15 is std-only (no mart cascade for R15)

# R16: confirm whether order_header.sql serving query selects client_details
grep -n "client_details\|client_info" detailView/app/adapters/outbound/duckdb/queries/order_header.sql
# If 0 hits → R16 detailView impact is nil

# R13: identify false-positive risk for 'sex' in templates/comments
grep -rn "\bsex\b" detailView/ docs/analytics-handbook/blueprints/ --include="*.sql" --include="*.py" --include="*.md" | grep -v "gender"
# Review each match manually before bulk replace
```

Document results in `snapshots/pre_p3_preflight.txt`.

---

## PRE-STEP: Capture parquet baseline

Run T3 checksum (verification-protocol.md §T3) for:
`dim_customers, dim_customers_base, fact_orders, mart_customer_action_queue, mart_customer_status_snapshot_monthly`

Save to `snapshots/pre_p3.txt`. Lock-free.

---

## STEP 3.1 — `std_customers`: R12 + R13 + R14 (dob, sex, loyalty_point)

**Change — `transformation/models/staging/standard/std_customers.sql`:**
- `dob,` → `dob AS birth_date,`
- `sex,` → `sex AS gender,`
- `loyalty_point,` → `loyalty_point AS loyalty_points,`

**Change — `transformation/models/staging/standard/schema.yml`:**
- Update `std_customers` column entries: `dob` → `birth_date`; `sex` → `gender`; `loyalty_point` → `loyalty_points`

**Checkpoint (parse + Strategy A build):**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"

docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select std_customers --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

**PASS:** exits 0; downstream marts break on build (expected — fixed in Step 3.2). Parse passes.
**ROLLBACK:** `git checkout -- transformation/models/staging/standard/std_customers.sql transformation/models/staging/standard/schema.yml`
**COMMIT:** `git commit -m "feat(std): R12-R14 dob→birth_date, sex→gender, loyalty_point→loyalty_points in std_customers"`

---

## STEP 3.2 — `std_orders`: R15 + R16 (zip columns, client_details)

**Change — `transformation/models/staging/standard/std_orders.sql`:**
- `shipping_zip,` → `shipping_zip AS shipping_postal_code,`
- `billing_zip,` → `billing_zip AS billing_postal_code,`
- `client_details,` → `client_details AS client_info,`

**Checkpoint (parse + Strategy A build):**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"

docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select std_orders --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

**PASS:** exits 0. `fact_orders` breaks on build if it references these columns (fix in Step 3.3).
**ROLLBACK:** `git checkout -- transformation/models/staging/standard/std_orders.sql`
**COMMIT:** `git commit -m "feat(std): R15-R16 zip→postal_code, client_details→client_info in std_orders"`

---

## STEP 3.3 — Published mart cascade: `dim_customers_base`, `dim_customers`, `fact_orders`

**Pre-step: determine actual changes needed from pre-flight results.**

`dim_customers_base.sql` (R12–R14 — verify):
```bash
grep -n "\bdob\b\|\bsex\b\|loyalty_point\b" transformation/models/marts/core/dim_customers_base.sql
```
Update only lines that match (alias or select).

`dim_customers.sql` (R12–R14):
- `dob,` → `birth_date,` (line 158 or equivalent)
- `sex,` → `gender,` (line 159)
- `loyalty_point,` → `loyalty_points,` (line 162)

Also check for consumer mart references:
```bash
grep -rn "\bdob\b\|\bsex\b\|loyalty_point\b" transformation/models/marts/customer/
```
Update `mart_customer_action_queue.sql` and `mart_customer_status_snapshot_monthly.sql` if they reference these columns.

`fact_orders.sql` (R15 and R16 — if pre-flight found matches):
- If `shipping_zip` / `billing_zip` in SELECT → rename to `shipping_postal_code` / `billing_postal_code`
- If `client_details` in SELECT → rename to `client_info`

**Checkpoint (full-refresh on dim_customers because incremental; normal build for others):**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"

docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select dim_customers_base --full-refresh --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
docker exec data_platform sh -c "cd /app && dbt build --select dim_customers --full-refresh --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
docker exec data_platform sh -c "cd /app && dbt build --select fact_orders mart_customer_action_queue mart_customer_status_snapshot_monthly --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -15"
# T3 — dim_customers, fact_orders row counts must match pre_p3.txt
python -c "import duckdb,glob,os; [print(m, duckdb.query(f'SELECT COUNT(*) FROM read_parquet(\"{sorted(glob.glob(f\"app_data/data_lake/export/marts/rolling/{m}/*.parquet\"))[-1]}\")').df()) for m in ['dim_customers','fact_orders']]"
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

**PASS:** all models build; row counts match baseline; `birth_date`, `gender`, `loyalty_points` columns present in dim_customers parquet.
**ROLLBACK:** `git checkout --` all changed mart files; Strategy A full-refresh rebuild.
**COMMIT:** `git commit -m "feat(marts): R12-R16 cascade — dim_customers, dim_customers_base, fact_orders, customer marts"`

---

## STEP 3.4 — Serving rebuild (T8)

```bash
docker compose stop metabase
python scripts/provisioning/bootstrap_serving_views.py
docker compose start metabase
```

**Spot-check olap.duckdb:**
```bash
docker exec data_platform sh -c "duckdb /app/var/olap.duckdb -c 'SELECT birth_date, gender, loyalty_points FROM dim_customers LIMIT 1' 2>&1"
```

**PASS:** query returns a row without error.
**ROLLBACK:** revert all mart SQL edits (Steps 3.1–3.3); re-run serving rebuild; restart Metabase.

---

## STEP 3.5 — detailView updates + image rebuild (T9)

**Changes (only what pre-flight confirmed is referenced):**

`queries/customer_profile.sql`:
```bash
grep -n "\bdob\b\|\bsex\b\|loyalty_point\b" detailView/app/adapters/outbound/duckdb/queries/customer_profile.sql
```
Update any matches → `birth_date`, `gender`, `loyalty_points`.

`customer_mappers.py`:
```bash
grep -n "\bdob\b\|\bsex\b\|loyalty_point\b" detailView/app/adapters/outbound/duckdb/customer_mappers.py
```
Update `row.get("dob")` → `row.get("birth_date")` etc.

Customer domain class (locate file):
```bash
grep -rn "\bdob\b\|\bsex\b\|loyalty_point\b" detailView/app/domain/
```
Update field names.

Templates:
```bash
grep -rn "\bdob\b\|\bsex\b\|loyalty_point\b" detailView/app/web/templates/
```
Update display labels (HTML text, not just Python references).

R15/R16 in detailView (only if pre-flight found matches):
```bash
grep -n "shipping_zip\|billing_zip\|client_details" detailView/app/adapters/outbound/duckdb/queries/order_header.sql
```

**Rebuild + smoke test:**
```bash
docker compose up -d --build detail_view
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/orders/<valid_order_code>/tab/financial
```

**PASS:** HTTP 200; no 500 errors in container logs.
**ROLLBACK:** `git checkout -- detailView/`; `docker compose up -d --build detail_view`.
**COMMIT:** `git commit -m "feat(detailView): R12-R16 customer field renames"`

---

## STEP 3.6 — Blueprint updates + redeploy

**Identify affected blueprints:**
```bash
grep -rl "\bdob\b\|\bsex\b\|loyalty_point\b\|shipping_zip\|billing_zip\|client_details" docs/analytics-handbook/blueprints/
```

**For each file returned:**

R12: `\.dob\b` → `.birth_date` (scoped to SQL column refs, not comments — review manually)
R13: `\.sex\b` → `.gender` (MUST use word-boundary; review every match for false positives before applying)
R14: `loyalty_point` → `loyalty_points`
R15: `shipping_zip` → `shipping_postal_code`; `billing_zip` → `billing_postal_code`
R16: `client_details` → `client_info`

**Post-replace verification (must all return zero):**
```bash
grep -r "\bdob\b" docs/analytics-handbook/blueprints/ --include="*.md"
grep -r "loyalty_point\b" docs/analytics-handbook/blueprints/ --include="*.md"
grep -r "shipping_zip\|billing_zip" docs/analytics-handbook/blueprints/ --include="*.md"
grep -r "client_details" docs/analytics-handbook/blueprints/ --include="*.md"
# R13 sex: manual review only (word-boundary grep too noisy)
```

**Redeploy affected blueprints:**
```bash
node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/<file>.md
```

**PASS:** all dashboard cards load; zero old-name hits in post-replace grep.
**ROLLBACK:** `git checkout -- docs/analytics-handbook/blueprints/`; redeploy previous versions.
**COMMIT:** `git commit -m "feat(blueprints): R12-R16 customer + order field renames in affected blueprints"`

---

## STEP 3.7 — Full harness validation

**T3 — parquet checksums:**
Run T3. Save to `snapshots/post_p3.txt`. Compare to `pre_p3.txt`:
- Row counts: identical for all marts
- Key-column value checksums on `total_spend` (from P1), `order_count` (from P2): unchanged

**T4 — Dagster health:**
```bash
docker exec data_platform sh -c "dagster run list --limit 3"
docker logs data_platform --since 10m 2>&1 | grep -iE "RUN_SUCCESS|RUN_FAILURE|tests:|ERROR"
```

**T7 — App smoke:**
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/orders/<valid_code>/tab/financial
```

**PASS:** all checksums match; RUN_SUCCESS; HTTP 200.

---

## Success criteria

- `dbt build` clean; all renamed columns present in parquet
- Harness: byte-identical row counts + key-column checksums for affected marts
- Metabase customer dashboards show `gender`, `birth_date`, `loyalty_points` without errors
- detailView customer profile renders renamed fields correctly
- `dim_customers` incremental runs cleanly after full-refresh rebuild

---

## Risk assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `\bsex\b` grep matches unrelated text in templates/comments | Medium | Low | Manual review of every match before bulk replace; skip template-text hits |
| R15 `zip` columns absent from `fact_orders` output → std-only rename causes no mart cascade | Low | Low | Pre-flight check confirms scope before any edit |
| `dim_customers` incremental produces duplicate rows after full-refresh (P2 `last_modified_at` filter) | Low | Medium | Full-refresh in Step 3.3 forces clean rebuild; verify row count matches baseline |
| Blueprint `dob`/`sex` referenced in text-card labels (non-SQL) — rename breaks display text | Low | Low | grep blueprints for non-SQL occurrences and update text labels too |

---

## Rollback plan

1. Revert std model edits (`git checkout -- std_customers.sql std_orders.sql`)
2. Revert mart edits
3. Strategy A rebuild for affected DAG
4. Stop Metabase → `bootstrap_serving_views.py` → start Metabase
5. Rebuild detailView image
6. Redeploy previous blueprint versions

Estimated rollback: ~30 min (narrower blast radius than P1/P2).

---

## Decision note — `order_code` explicitly NOT renamed

The analysis report listed `order_code → order_number` as a P3 candidate. **Rejected** per naming-conventions.md §2: "`_code` = human/business identifier that is ALPHANUMERIC". `order_code` is alphanumeric (`260316A6VJXGMT`); `order_number` misleads. This decision is final for this plan.

---

## Next steps

After P3 (or after P0 if P1–P3 are deferred):
- The std layer is the clean v3 contract. When Q1–Q5 business answers arrive, implement the UNION in each std model: `stg_sapo_v2_<entity>` (freeze) UNION ALL `stg_sapo_v3_<entity>` (new), with `source_version` driving overlap policy.
- Phase 4 (v2 file rename) is independent of P1–P3 and can run after P0 at any time.
