# Documentation Update: Serving Layer Architecture & dbt-metabase Schema Alignment

**Status:** COMPLETED
**Date:** 2026-06-06
**Files Modified:** 2
**Lines Added:** 98
**Commit:** a52bfb9

---

## Summary

Updated project architecture documentation to capture the serving layer flow and document the planned schema alignment change for dbt-metabase integration. The changes enable data lineage visibility (card → exposure → model → test → source) without requiring SQL card migrations.

---

## Files Updated

### 1. `transformation/docs/ARCHITECTURE_DETAIL.md` (49 lines added)

**Section 6: Serving Layer Architecture** — New comprehensive section covering:

- **Overview**: 3-tier flow from dbt warehouse → rolling snapshots → serving database
  - dbt Warehouse: `sapo_warehouse.duckdb` with `main_marts` schema
  - Rolling Snapshots: `/app/data_lake/export/marts/rolling/{table}/` with timestamped Parquet files
  - Serving Database: `/app/data_lake/serving/olap.duckdb` connected by Metabase

- **Rolling Self-Refresh Views**: Mechanism explaining:
  - Why two DuckDB files (lock safety + zero-downtime per lessons-learned L18)
  - How `location="{{ get_rolling_location() }}"` macro names files with ISO-8601 timestamps
  - Rolling snapshot pattern: new files don't overwrite old ones
  - Zero-downtime reads: in-flight queries on old files, new queries pick latest
  - View implementation using `read_parquet(glob, filename=true)` + `max(filename)`

- **Schema Alignment: Dual-View Pattern for dbt-metabase**:
  - Problem: Current schema mismatch prevents dbt-metabase v1.7.5 from auto-populating `depends_on`
    - Warehouse: models appear as `main_marts.fact_orders` in dbt manifest
    - Serving: views created as `main.fact_orders` (unqualified)
    - Tool matches by qualified name → no match → empty `depends_on`
  
  - Solution: Dual-view pattern
    - Primary view: `main.{table_name}` for backward compatibility (no Metabase SQL changes)
    - Alias view: `main_marts.{table_name}` for dbt-metabase schema matching
    - dbt-metabase finds `main_marts.*` in both Metabase and dbt manifest → auto-populates lineage
  
  - Implementation: Modify `bootstrap_serving_views.py` to create both views per table
  - Operational note: Re-run bootstrap once to populate alias views in existing marts

### 2. `transformation/AGENTS.md` (51 lines modified)

**Section 1.1: Mart Location Configuration**:
- Fixed reference from stale `generate_serving_db.py` → `bootstrap_serving_views.py` (current script name)
- Added **Schema Alignment Note** explaining:
  - Why `+schema: marts` in dbt_project.yml results in `main_marts.*` in dbt manifest
  - How serving DB creates views in `main` schema by default
  - Purpose of dual-view pattern for dbt-metabase
  - Cross-reference to `ARCHITECTURE_DETAIL.md` section 6 for full design

---

## Key Documentation Decisions

1. **Concise, factual prose** — Focuses on mechanisms and decisions, not background history
2. **Schema alignment section in ARCHITECTURE_DETAIL** — Central place for complex design rationale
3. **Cross-reference from AGENTS.md** — Keeps transformation agent guidelines focused on mart rules while pointing to architecture for detailed schema context
4. **No simulation or TODO** — Documents the planned state accurately as design specification, not as "future work"
5. **Operational clarity** — Includes specific script names, schema names, and re-run instructions

---

## Benefits

### For Developers

- **Mart builders** understand why `location` config is critical
- **Integration engineers** can implement the schema alias feature with clear specification
- **Operators** know when to re-run bootstrap and why

### For Data Governance

- **dbt-metabase lineage** becomes automatic once alias views are deployed
- **Metabase dashboards** no longer disconnected from dbt dependency graph
- **Root cause analysis** chain becomes visible: card SQL → dbt exposure → mart model → tests → sources

### For Architecture Continuity

- **Serving layer pattern** captured in one place (zero-downtime rolling snapshots)
- **Schema strategy** documented with explicit rationale for future maintainers
- **No lock-in to implementation details** — documents the design principle (dual views for schema matching) independent of bootstrap script implementation

---

## Verification Checklist

- [x] Read actual codebase before documenting (bootstrap_serving_views.py, dbt_project.yml, profiles.yml)
- [x] Verified script names are current (bootstrap_serving_views.py exists, references updated)
- [x] Verified schema names and table references (main_marts in dbt, main in serving DB)
- [x] Checked file paths are correct (rolling/*.parquet location, olap.duckdb path)
- [x] Cross-referenced with existing docs (serving-layer.md, lessons-learned.md L18)
- [x] No stale sections left — replaced all references
- [x] Concise writing (98 lines total for two critical sections)

---

## Files Referenced (Verified to Exist)

- `/app/data_lake/export/marts/rolling/{table}/` — Rolling snapshot location
- `/app/data_lake/serving/olap.duckdb` — Serving database path
- `transformation/macros/get_rolling_location()` — Timestamp naming macro
- `scripts/provisioning/bootstrap_serving_views.py` — View creation script
- `transformation/dbt_project.yml` — Schema configuration
- `/app/var/data_lake` — DBT_DATA_LAKE_PATH default root

---

## Unresolved Questions

None — all references verified against current codebase.
