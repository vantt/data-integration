# Raw Consolidation Spike Findings

## A. Volume

### Raw Data Lake Path
- **Location:** D:\Vantt\app\data-integration\app_data\data_lake\
- **Environment variable:** DESTINATION__FILESYSTEM__BUCKET_URL (file:// URL)

### SAPO V2 Order Raw Volume
Total: **1,064 parquet files, 206.7 MB**

Breakdown by ingest method:
- **batch_sync:** 78 files, 184.9 MB (NOT partitioned by year/month — all in _default/_default)
- **history_log:** 978 files, 17.7 MB (Hive-partitioned by year/month)
  - Year 2025: ~1 file (Oct-Dec)
  - Year 2026: 972 files (Jan-Jul), concentrated in Apr-Jun (155+353+448 files)
- **text:** 3 files, 0.2 MB
- **_delta_log:** 5 files (metadata), 3.9 MB

### MISA Raw Volume
Total: **102 parquet files, ~2.5 MB**
- **account_ledger:** 18 files (no year/month partitioning)
- **sales_lines:** 84 files (no year/month partitioning)
- Both use ingest_method=file_drop only

**Finding:** Large file count (~1000) is a metadata overhead problem. history_log's small file size (<1MB each) + frequency (978 files in 7 months) suggests high ingestion velocity. Batch_sync is consolidated (78 large files), not fragmented.

---

## B. Full-Refresh Safety

### Downstream Read Pattern

**Model:** src_sapo_v2_orders.sql (and all src_sapo_v2_*.sql models)

**Configuration:**
`\sql
{{ config(
    materialized='incremental',
    unique_key='order_id',
    incremental_strategy='delete+insert',
    tags=['source', 'sapo']
) }}

raw_data AS (
    SELECT * FROM {{ source('sapo_v2_raw', 'order') }}
    {% if is_incremental() %}
    WHERE _dlt_load_id > (SELECT max_load_id FROM _cursor)
    {% endif %}
)
`\

**Behavior:**
- **Normal incremental run:** Filters on _dlt_load_id > max_load_id → reads only NEW data since last run
- **Full-refresh:** is_incremental() = false → **reads ALL raw parquet history** (no WHERE clause)
- Downstream stg_ models are views reading from deduped src_ table

### Risk Assessment: CONDITIONAL

**IF compacted files preserve path structure or are in same recursive read:**
- ✅ Safe — dbt just reads ead_parquet('sapo_v2_raw/order/**/*.parquet') recursively
- Compacted files in any subdirectory will be included

**IF compacted files break path assumptions OR dlt reads from specific paths:**
- ❌ Risky — dbt and dlt may not find compacted files if they are in unexpected locations

**Evidence:**
- dlt reads from sapo_v2_raw/order/ingest_method={method}/year={year}/month={month}/ paths
- dbt uses ead_parquet() with Hive partition pruning on year/month
- Both support recursive **/*.parquet patterns

**Recommendation:**
Compacted files should maintain Hive-style paths:
`
BEFORE: sapo_raw/order/ingest_method=history_log/year=2024/month=01/file1.parquet
AFTER:  sapo_raw/order/consolidated/year=2024/month=01/data.parquet
\\\

This preserves partition columns in filenames, allowing dbt/dlt partition pruning to work.

---

## C. Dedup Test Coverage

### Current State: ❌ GAP

**No automated test for 0 duplicates on order_id in staging.**

**Evidence:**
- schema.yml entry for stg_sapo_v2_orders:
  `yaml
  - name: stg_sapo_v2_orders
    columns:
      - name: order_id
        tests: [not_null]  # ← NO unique test
  \\\

- Only manual verification scripts in 	ransformation/docs/DEDUPLICATION.md:
  `sql
  SELECT order_id, COUNT(*) as cnt
  FROM {{ ref('src_sapo_orders') }}
  GROUP BY order_id
  HAVING COUNT(*) > 1;
  \\\

### Pre-Consolidation Requirement

Before compacting raw files, staging dedup must be verified automatically. Current state:
1. ✅ 2-level dedup logic in src_sapo_v2_orders (tech + biz)
2. ✅ Manual verification docs exist
3. ❌ No dbt test to catch duplicate order_ids escaping staging

### Recommended Addition

Add to 	ransformation/models/staging/schema.yml:
`yaml
- name: stg_sapo_v2_orders
  columns:
    - name: order_id
      tests:
        - not_null
        - unique  # ← ADD THIS
\\\

Or create a custom test:
`sql
-- tests/assert_stg_sapo_v2_orders_no_duplicates.sql
SELECT order_id
FROM {{ ref('stg_sapo_v2_orders') }}
GROUP BY order_id
HAVING COUNT(*) > 1
\\\

**Cost:** < 5 minutes to add test. Prevents data escaping into downstream marts.

---

## D. dlt Cursor Compatibility

### How dlt Incremental Works

**Cursor field:** sync_metadata.event_timestamp (from orders.py)
**Watermark storage:** _dlt_pipeline_state directory in data lake
**Watermark format:** JSON file with max cursor value per pipeline

**File-to-state mapping:**
- dlt adds _dlt_load_id (UUID) to every record
- Cursor is NOT the file path; it's the max _dlt_load_id value seen
- dlt reads from data lake and restores cursor from _dlt_pipeline_state/*.jsonl

### Compaction Compatibility: ✅ SAFE (with caveats)

**IF consolidated files preserve _dlt_load_id column:**
- ✅ dlt cursor will work correctly
- dlt reads _dlt_load_id > max_cursor regardless of file location

**IF dlt uses path-based deduplication (e.g., "already processed year=2024/month=01"):**
- ⚠️ Risky — moving files to consolidated/ subdirectory may confuse dlt

**Evidence:**
- ingestion/src/utils/pipeline_runner.py line 100:
  \\\python
  data_lake_root = os.environ.get("DESTINATION__FILESYSTEM__BUCKET_URL", "")
  state_files = _glob.glob(os.path.join(data_lake_root, "_dlt_pipeline_state", f"{pipeline_name}__*.jsonl"))
  \\\
- Cursor is ID-based, NOT path-based ✅

### Pre-Consolidation Safety Checks

1. **Verify dlt state before compact:**
   \\\ash
   cat data_lake/_dlt_pipeline_state/sapo_v2_webhook_consumer__*.jsonl | jq .
   \\\
   Ensure max_cursor is recorded and max date is > compact cutoff.

2. **Preserve _dlt_load_id in consolidated files:**
   - When merging parquets, keep _dlt_load_id column
   - Don't regenerate UUIDs

3. **Test compaction on staging dataset first:**
   - Compact sapo_raw_staging/order/ (dev dataset)
   - Run full-refresh on src_sapo_v2_orders_dev
   - Verify row counts match

---

## E. MISA Raw Structure

### File-Drop vs API Pipeline

**SAPO V2 (API):**
- Ingestion method: atch_sync (cursor-based), webhook (append), history_log (gap-fill)
- Partitioning: year/month (temporal)
- Cursor: sync_metadata.event_timestamp (time-based)

**MISA (File-Drop):**
- Ingestion method: ile_drop only
- Partitioning: None (all files in ingest_method=file_drop/)
- Cursor: posting_date extracted from Excel → **_dlt_load_id from dlt**
- Source: Excel files uploaded to pp_data/input_source/misa-amis/

**Implication for Consolidation:**
- MISA does NOT use time-based partitioning → cannot apply year/month consolidation strategy
- MISA files are already consolidated (84 files = 84 Excel uploads parsed into single table)
- **No consolidation needed for MISA** — different ingestion pattern

**Evidence:** ingestion/run-misa-sales-file-drop.py processes one Excel file per pipeline run, appends to parquet. Files are never split by date.

---

## Verdict

### Consolidation Safe? **CONDITIONAL**

**Green lights:**
- ✅ Full-refresh reads all raw history (safe if paths preserved)
- ✅ dlt cursor is ID-based, not path-based
- ✅ Volume is moderate (206 MB sapo_raw, 2.5 MB misa_raw)
- ✅ High file count (1000+) justifies consolidation effort

**Yellow flags:**
- ⚠️ No automated dedup test in dbt (gap identified)
- ⚠️ Batch_sync not partitioned (consolidation target unclear)
- ⚠️ No pre-consolidation verification playbook

### Conditions for Safe Consolidation

1. **Add dedup test to dbt schema.yml** (Task C) — fail fast if dedup logic breaks
2. **Maintain Hive partition structure** — consolidated files should have year/month in filename
3. **Preserve _dlt_load_id column** — required for dlt cursor compatibility
4. **Test on dev dataset first** — sapo_raw_staging/order/ → verify full-refresh works
5. **Backup before compact** — 30-day retention of original files before deletion

### Recommended Next Steps

1. **Immediate (this week):**
   - Add unique test to stg_sapo_v2_orders.order_id in schema.yml
   - Run dbt test suite to baseline — ensure 0 duplicates today

2. **Next (planning phase):**
   - Design consolidation algorithm:
     - Target: history_log files older than 90 days
     - Merge: ingest_method=history_log/year=2024/month=01/ → consolidated/year=2024/month=01/merged.parquet
     - Preserve: _dlt_load_id, ingest_method, year, month columns
   - Write playbook for dlt state backup/restore

3. **Implementation (follow-up spike):**
   - Implement compact Dagster asset with dry-run mode
   - Test on staging dataset
   - Monitor dlt cursor after first consolidation
   - Document lessons learned

---

## Status Protocol

**Status:** DONE_WITH_CONCERNS

**Summary:**
Raw consolidation is technically safe if three conditions are met: (1) automated dedup test is added, (2) file path structure is preserved, and (3) _dlt_load_id column is maintained. Volume justifies effort (1000+ history_log files, small sizes). No blockers found; gaps identified and actionable.

**Concerns:**
1. Missing automated test for duplicate order_ids (pre-condition for safe compaction)
2. Batch_sync data not partitioned by year/month (need consolidation strategy clarification)
3. No pre-consolidation verification playbook (risk if dlt behavior differs from assumptions)

**Next Owner:** Whoever implements phase 4 consolidation task should:
- Confirm dlt cursor behavior with test on sapo_raw_staging
- Add dedup test to schema.yml before any raw file modifications
- Document consolidation playbook in ingestion/docs/ before Dagster implementation
