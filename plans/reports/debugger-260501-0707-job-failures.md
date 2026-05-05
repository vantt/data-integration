# Incident Report: Dagster Job Failures 2026-05-01

**Incident window:** 2026-05-01 03:01 ICT → ongoing (as of 07:10 ICT)
**Affected jobs:** `ingest_sapo_realtime_job`, `ingest_sapo_incremental_job`, `transform_batch_nightly_job`
**Total failures confirmed:** 102 runs

---

## Executive Summary

All Dagster jobs fail at the `sapo_dbt_assets` step. The root cause is **duplicate partition data in two config tables** (`teams_raw`, `team_members_raw`), triggered when the nightly batch job ran `sheets_team_config_asset` at 03:01 ICT on May 1st, creating new `month=5` partitions that duplicate the existing `month=4` data. This causes:

1. `unique_dim_teams_team_code` / `unique_dim_teams_team_key` fail: 1 duplicate (team CS appears in both month=4 and month=5)
2. `unique_fact_orders_order_id` fails: 1419 duplicates (every order from seller `finejapanvnn@fineworldgroupp.com` fans out 2× due to two identical SCD2 rows in `team_members`)

---

## Evidence Chain

### 1. Failure timeline
- **03:01:27 ICT** — `transform_batch_nightly_job` ran, included `sheets_team_config_asset`, wrote `year=2026/month=5` partition for both `teams_raw` and `team_members_raw`
- **03:01 ICT onward** — every subsequent `dbt build` fails on same 3 tests
- Files created: `D:\...\teams_raw\ingest_method=google_sheet\year=2026\month=5\teams.parquet` and `\team_members_raw\...\month=5\team_members.parquet`

### 2. Duplicate data confirmed
Both month=4 and month=5 partitions contain **identical data** (identical content, only year/month partition columns differ):

| Table | month=4 rows | month=5 rows | Content identical |
|-------|-------------|-------------|-------------------|
| `teams_raw` | 1 (CS) | 1 (CS) | Yes |
| `team_members_raw` | 1 (finejapanvnn@...) | 1 (finejapanvnn@...) | Yes |

### 3. Failure cascade
- `stg_teams` queries `SELECT * FROM teams_raw` → reads both partitions → 2 rows for team CS
- `dim_teams` built from `stg_teams` (+ UNK row) → duplicate `team_code=CS`, `team_key=<same hash>`
- dbt tests `unique_dim_teams_team_code` and `unique_dim_teams_team_key` → FAIL 1 each

- `stg_team_members` queries `SELECT * FROM team_members_raw` → reads both partitions → 2 identical rows for `finejapanvnn@fineworldgroupp.com` in CS team, both with `effective_to=NULL`
- `fact_orders` SCD2 join: `LEFT JOIN team_members tm ON lower(dseller.email) = tm.staff_email AND ... effective_to IS NULL` matches **both** rows → each order for that seller duplicated
- dbt test `unique_fact_orders_order_id` → FAIL 1419

### 4. Root cause in code

`ingestion/src/gsheet_team_config.py` line 312–313:
```python
valid_teams["year"] = datetime.now().year
valid_teams["month"] = datetime.now().month
```

These "config" tables (teams, team_members) are **current-state snapshots**, not time-series. The script correctly partitions by current date, but `stg_teams.sql` and `stg_team_members.sql` query `SELECT * FROM source` which reads **all historical partitions** without deduplication. When the month rolls over, a new partition is created, and the old one is not deleted.

---

## Competing Hypotheses (Tested)

| Hypothesis | Status | Evidence |
|---|---|---|
| **H1: New month partition duplicates config tables** | **CONFIRMED (root cause)** | Files created at 03:01 ICT May 1; identical data in month=4 and month=5 |
| H2: Sapo API returned duplicate orders (upstream data quality) | Eliminated | src_sapo_orders has dedup logic (ROW_NUMBER); duplicates are in team_members join fan-out, not raw orders |
| H3: dbt incremental model corruption / stale materialization | Eliminated | Tests fail on freshly built table; issue is data, not model state |

---

## Immediate Fix (stops bleeding now)

**Delete the month=5 partition files:**

```bash
rm "D:/Vantt/app/data-integration/app_data/data_lake/sapo_raw/teams_raw/ingest_method=google_sheet/year=2026/month=5/teams.parquet"
rmdir "D:/Vantt/app/data-integration/app_data/data_lake/sapo_raw/teams_raw/ingest_method=google_sheet/year=2026/month=5"

rm "D:/Vantt/app/data-integration/app_data/data_lake/sapo_raw/team_members_raw/ingest_method=google_sheet/year=2026/month=5/team_members.parquet"
rmdir "D:/Vantt/app/data-integration/app_data/data_lake/sapo_raw/team_members_raw/ingest_method=google_sheet/year=2026/month=5"
```

After deletion, dbt build will succeed on next job run.

---

## Permanent Fix (prevents recurrence at month rollover)

**Option A — Overwrite strategy (recommended):** Change `gsheet_team_config.py` to write to a fixed "latest" partition, not year/month-based. These are config tables with no historical value across partitions.

In `ingestion/src/gsheet_team_config.py`, replace the `_save_to_parquet` calls with a fixed output directory using `ingest_method=google_sheet/year=current/month=current` where `current` is a fixed sentinel (e.g., `"latest"`), or simply write directly to `ingest_method=google_sheet/` with a single file.

Simplest fix — use a fixed path:
```python
# In _save_to_parquet, for config tables always write to same partition:
def _save_to_parquet(df, table_name, partition_col="year"):
    # For config/snapshot tables: always write to fixed partition to prevent accumulation
    output_dir = os.path.join(DATA_LAKE_PATH, "sapo_raw", table_name, "ingest_method=google_sheet")
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{table_name.replace('_raw', '')}.parquet")
    df.to_parquet(file_path, index=False)
```

Then delete the `year=/month=` subdirectories and update the dbt source to point at the flat path.

**Option B — Dedup in staging model (defensive, compatible with current partitioning):**

In `stg_teams.sql`, add `QUALIFY ROW_NUMBER() OVER (PARTITION BY team_code ORDER BY year DESC, month DESC) = 1` to always take the latest partition's row per team_code.

In `stg_team_members.sql`, similar dedup: `QUALIFY ROW_NUMBER() OVER (PARTITION BY staff_email, team_code, effective_from ORDER BY year DESC, month DESC) = 1`.

Option B is a less invasive stop-gap; Option A is the correct long-term design.

**Option C — Combine A+B:** Fix the ingestion to overwrite AND add defensive dedup in staging.

---

## Affected Files

| File | Issue |
|---|---|
| `ingestion/src/gsheet_team_config.py` | Uses `year/month` partitioning for config snapshot tables |
| `transformation/models/staging/stg_teams.sql` | No dedup against partition accumulation |
| `transformation/models/staging/stg_team_members.sql` | No dedup against partition accumulation |
| `transformation/models/marts/sales/fact_orders.sql` | SCD2 join fans out on team_members duplicates |

---

## Monitoring Gap

No alert exists for "partition count > 1 in config tables." Consider adding a dbt source freshness test or an asset check that verifies `teams_raw` has exactly 1 active partition. Alternatively, the `unique` tests on `dim_teams` already serve as the canary — but they fire too late (after dbt build, downstream). A pre-build check on raw partition counts would catch this earlier.

---

## Unresolved Questions

None — root cause fully confirmed with data evidence.
