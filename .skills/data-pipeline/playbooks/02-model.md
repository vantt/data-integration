# MODEL Playbook — dbt 5-hop Transformation

## Trách nhiệm

MODEL group biến đổi raw Parquet (từ data lake) thành clean analytics tables qua 5 hops:
`src_` → `stg_` → `std_` → `int_` → `dim_/fact_`.

**Đầu vào:** Hive-partitioned Parquet files tại `data_lake/export/raw/`
**Đầu ra:** Rolling Parquet snapshots tại `data_lake/export/marts/rolling/` (để SERVE layer pick up)

Mọi transformation logic đều trong dbt (SQL). Dagster orchestrates dbt via `@dbt_assets`.

---

## Pre-flight Checklist (đọc TRƯỚC khi implement)

- [ ] `sources.yml` có external source với Hive partition glob đúng format
      (Lesson 8 dbt-patterns: `hive_partitioning=True`, `partitions` declared)
- [ ] `src_` model: `INCREMENTAL` materialization, dedup `ORDER BY modified_on DESC` first,
      then `ingest_method` priority (L4, L28) — **không** dùng `event_timestamp` để dedup
- [ ] Incremental filter dùng `_dlt_load_id`, KHÔNG `event_timestamp` (L29) —
      `event_timestamp` không monotonic trong Parquet batches
- [ ] `src_/stg_` split: JSON payload chỉ extract ở `src_` → `stg_` đọc flat cols —
      tránh OOM từ double payload expansion (Lesson 2 dbt-patterns)
- [ ] Mart models có `location="{{ get_rolling_location() }}"` trong config —
      thiếu → dbt ghi overwrite file thay vì rolling snapshot → SERVE view broken (Lesson 5 dbt-patterns)
- [ ] Pre-create rolling dirs trong `@dbt_assets` function TRƯỚC khi `dbt.run_dbt_...` —
      DuckDB external không auto-create dirs (Lesson 3 dagster-patterns)
- [ ] Schema migration self-heal: `on_schema_change='append_new_columns'` + 3-guard pattern
      (L31: `adapter.get_columns_in_relation`, `UNION ALL` guard, cursor CTE) khi thêm column
- [ ] Tests trong `schema.yml`: `unique`, `not_null`, `relationships` cho dim/fact keys
      (Lesson 11 dbt-patterns)
- [ ] Reference seeds nếu cần static lookup tables (Lesson 12 dbt-patterns) —
      seed `id` column là VARCHAR (KHÔNG INTEGER — L memory: DuckDB INTEGER strips underscore)
- [ ] `op_tags={"dagster/concurrency_key": "duckdb_lock"}` cho `@dbt_assets` — DuckDB là
      single-writer; mọi write phải qua slot (L11)
- [ ] `DBT_SEND_ANONYMOUS_USAGE_STATS=false` tại process level — tránh zombie telemetry thread
      (Lesson 4 dagster-patterns)

---

## Mental model & Patterns

### 5-Hop Transformation Flow

```
raw Parquet (Hive partition)
  ↓ sources.yml
src_     [incremental, delete+insert]  ← JSON extract + dedup từ raw. No payload after.
  ↓ ref()
stg_     [view]                        ← Enrichment joins, unnest arrays. Reads flat cols.
  ↓ ref()
std_     [view]                        ← Golden layer: multi-source consolidate, normalize.
  ↓ ref()
int_     [ephemeral/table]             ← Metrics (CLV, RFM). NOT exported to serving.
  ↓ ref()
dim_/fact_ [external + rolling]        ← BI tables. Surrogate keys. location=rolling.
```

Deep-dive: `../references/dbt-patterns.md` — "5-Hop Transformation Flow" section (lines 55-67)

### Two-Phase Dedup (OOM-Safe) — Lesson 1 dbt-patterns

OOM risk khi dedup + JSON extract trong 1 SQL. Pattern: separate CTE for payload extraction
(Phase 1) from dedup window (Phase 2). Reference: `../references/dbt-patterns.md#lesson-1`

### Compare-Before-Overwrite — L30

Idempotent incremental: trước khi overwrite, compare `modified_on` xem record có thực sự mới
không. Tránh spurious updates khi source resends same data.

### Post-Hook Pattern — Lesson 9 dbt-patterns

Dùng `post-hook` để trigger downstream logic (export, cleanup) sau khi model success.
Không trigger nếu model fails → safe for side effects.

### JSON Extraction with Coalesce Fallbacks — Lesson 10 dbt-patterns

`json_extract_string(payload, '$.field') OR json_extract_string(payload, '$.alt_field')`
Handle API schema evolution gracefully. Always coalesce to sensible default, not NULL.

### Partition Pruning — Lesson 13 dbt-patterns

Hive partition predicates PHẢI xuất hiện trong WHERE clause — DuckDB không auto-pushdown
virtual column filter. `WHERE year = extract(year from current_date)` prunes files.

### Generated Time Dimension — Lesson 14 dbt-patterns

SQL-only approach (không cần CSV seed): generate dim_time với DuckDB range function.
`SELECT * FROM range(date '2021-01-01', current_date + 30, interval '1 day')`.

### Nightly Incremental vs Full-Refresh — Separate Jobs (L32, Lesson 9 dagster)

Nightly job: `dbt run --select src_*` (incremental mode, cursor advances).
Full-refresh job: separate Dagster job, triggered manually or via sensor.
**KHÔNG** combine — shared cursor state causes inconsistency.

### dlt 2-Layer Filter — Full-Refresh Reset (L33)

dlt incremental has 2 filter layers: (1) cursor in pipeline state, (2) `_dlt_load_id` in dbt.
`--full-refresh` must reset BOTH: delete `_dlt_load_id` filter state AND wipe `.dlt/pipelines/{name}/` dir.

---

## Templates

All templates in `../templates/model/` (post-Phase 4 path):

| Template | Khi nào dùng |
|----------|-------------|
| `src-model-template.sql` | Mọi new source entity — INCREMENTAL dedup + JSON extract + `_dlt_load_id` filter |
| `dim-model-template.sql` | Dimension tables — surrogate keys + `location=get_rolling_location()` |
| `fact-model-template.sql` | Fact tables — FK to dims + rolling + aggregation |
| `sources-yml-template.yml` | dbt sources entry với Hive partitioning glob pattern |
| `schema-yml-template.yml` | Schema tests (unique, not_null, relationships) cho model layer |

---

## Reference Sections (từ references/dbt-patterns.md)

### Project Configuration (dbt-patterns.md lines 3-54)

Critical settings đã được validate production:
- `profiles.yml`: `memory_limit=5GB` (< container limit → spill-to-disk), `threads=1`
  (sequential → tránh buffer overflow), `TimeZone='Asia/Ho_Chi_Minh'`
- `dbt_project.yml`: `marts` layer → `materialized: external`, `format: parquet`
- `on_schema_change: sync_all_columns` default cho marts (tránh full-refresh khi add column)

### 5-Hop Flow (dbt-patterns.md lines 55-67)

Bảng prefix/materialization/purpose cho 6 layer types (src/stg/std/int/dim/fact).

### Quick Reference: Materialization Decision Tree (dbt-patterns.md line 465+)

```
Source entity (raw dedup)?  → src_  → INCREMENTAL (delete+insert)
Enrichment/joins?           → stg_  → VIEW
Normalize/consolidate?      → std_  → VIEW
Aggregations (internal)?    → int_  → ephemeral hoặc table
BI dimension table?         → dim_  → external + rolling location
BI fact table?              → fact_ → external + rolling location
```

---

## Supporting Scripts

Scripts relevant to MODEL group — từ `../references/supporting-scripts.md`:

| Script | Khi nào dùng |
|--------|-------------|
| `scripts/ensure_dbt_directories.py` | Pre-create rolling/ dirs trước dbt run |
| `transformation/scripts/run_dbt.py` | dbt build wrapper (handles env, logs, target) |
| `transformation/check_view.py` | Inspect dbt model state post-run |
| `scripts/maintenance/sync_seeds.py` | Refresh seed CSVs khi lookup data thay đổi |

**Decision logic — "Thêm mart model mới" chain:**
Xem `../references/supporting-scripts.md` section "Khi Nào Gọi Script Nào".
Chuỗi: `ensure_dbt_directories.py` → `run_dbt.py --select {model}` → `generate_serving_db.py`.

---

## Cross-ref tới SERVE

Khi thêm hoặc sửa mart model, **PHẢI** check `../references/serving-layer.md`
section "Checklist khi thêm mart model mới" (6 items):

1. `location="{{ get_rolling_location() }}"` in config
2. `ensure_dbt_directories.py` → tạo rolling dir
3. `dbt run --select {model}` → verify parquet written to rolling/
4. `generate_serving_db.py` → verify view created
5. Test view via DuckDB CLI
6. Re-run dbt → verify GC, view still returns fresh data

**Cả 02-model.md pre-flight checklist VÀ serving-layer.md checklist phải đồng thời satisfied.**

---

## Debug Recipes

Từ `../references/troubleshooting.md` — MODEL-relevant sections:

- **dbt — OOM / Memory** section: incremental model memory explosion debug steps
- **dbt — Incremental / Late Events** section: cursor stall, wrong filter field symptoms
- **dbt — Source / Reference** section: missing source, schema mismatch
- **dbt — Mart / Export** section: rolling dir missing, external materialization fails
- Check dbt incremental state: `dbt run --select src_{entity} --vars '{"target_schema": "staging"}'`
- Check rolling snapshot latest: `ls -lt data_lake/export/marts/rolling/{model}/ | head -3`
- Verify DuckDB file lock: see `../playbooks/cross-cutting.md#duckdb-locking`

---

## Lessons Cross-Reference

### From lessons-learned.md

| ID | Title | File |
|----|-------|------|
| L4 | Ingest method priority dedup | `../references/lessons-learned.md#L4` |
| L5 | 7-day incremental buffer trong dbt | `../references/lessons-learned.md#L5` |
| L28 | Dedup dùng `modified_on`, KHÔNG `event_timestamp` | `../references/lessons-learned.md#L28` |
| L29 | Incremental filter: `_dlt_load_id`, KHÔNG `event_timestamp` | `../references/lessons-learned.md#L29` |
| L30 | Compare-before-overwrite cho incremental dedup | `../references/lessons-learned.md#L30` |
| L31 | DuckDB incremental schema migration — 3 bẫy khi thêm column | `../references/lessons-learned.md#L31` |
| L32 | Nightly incremental vs full-refresh — separate jobs | `../references/lessons-learned.md#L32` |
| L33 | dlt incremental 2-layer filter — reset cả hai khi full-refresh | `../references/lessons-learned.md#L33` |

### From dbt-patterns.md

| ID | Title | File |
|----|-------|------|
| dbt-Lesson-1 | Two-Phase Dedup (OOM-Safe) | `../references/dbt-patterns.md` |
| dbt-Lesson-2 | src_/stg_ Split (Primary OOM Fix) | `../references/dbt-patterns.md` |
| dbt-Lesson-3 | Incremental Filter bằng `_dlt_load_id` | `../references/dbt-patterns.md` |
| dbt-Lesson-4 | Ingest Method Priority khi Dedup | `../references/dbt-patterns.md` |
| dbt-Lesson-5 | Rolling Location cho Marts (CRITICAL) | `../references/dbt-patterns.md` |
| dbt-Lesson-6 | Circular Dependency Breaking | `../references/dbt-patterns.md` |
| dbt-Lesson-7 | Unknown Key Handling | `../references/dbt-patterns.md` |
| dbt-Lesson-8 | sources.yml với Hive Partitioning | `../references/dbt-patterns.md` |
| dbt-Lesson-9 | Post-Hook Pattern (Alternative Export) | `../references/dbt-patterns.md` |
| dbt-Lesson-10 | JSON Extraction — Coalesce Fallbacks | `../references/dbt-patterns.md` |
| dbt-Lesson-11 | Testing Strategy theo Layer | `../references/dbt-patterns.md` |
| dbt-Lesson-12 | Reference Seeds Pattern | `../references/dbt-patterns.md` |
| dbt-Lesson-13 | Partition Pruning với Hive Partitioning | `../references/dbt-patterns.md` |
| dbt-Lesson-14 | Generated Time Dimension Pattern (SQL) | `../references/dbt-patterns.md` |

### From dagster-patterns.md (MODEL-relevant)

| ID | Title | File |
|----|-------|------|
| dagster-Lesson-3 | Pre-Create Mart Directories IN Asset | `../references/dagster-patterns.md` |
| dagster-Lesson-9 | Separate Jobs for Nightly Incremental vs Full-Refresh | `../references/dagster-patterns.md` |

---

## When This Group Interacts with Others

| Upstream/Downstream | Interaction |
|---------------------|-------------|
| INGEST → MODEL | raw Parquet (Hive partition) từ INGEST là nguồn `src_` |
| MODEL → SERVE | Rolling Parquet snapshots từ `dim_/fact_` là input cho SERVE views |
| MODEL ↔ TRUST | dbt-Lesson-11 Testing Strategy: tests in schema.yml are TRUST checks |
| MODEL + OPS | `@dbt_assets` wiring: concurrency tags, telemetry, separate job topology |

---

## Related Cross-cutting Concerns

| Concern | Canonical file |
|---------|---------------|
| DuckDB single-writer lock | `../playbooks/cross-cutting.md#duckdb-locking` (dbt là writer chính) |
| Docker mount paths → rolling output | `../playbooks/cross-cutting.md#docker-mount-paths` |
| dbt target cache sau mount change | `../playbooks/cross-cutting.md#dbt-target-cache-after-mount-change` |
