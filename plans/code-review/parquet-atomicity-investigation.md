# Backlog: dbt Parquet Export Atomicity Investigation

**Origin:** [code-reviewer-260227-1721-orchestration-edge-cases.md](./archive/code-reviewer-260227-1721-orchestration-edge-cases.md) — Unresolved Question #1
**Priority:** Low
**Status:** Open
**Created:** 2026-04-03

---

## Question

Does `dbt build` export parquet files atomically per model, or can a partial write exist if the process is interrupted mid-export?

## Why It Matters

- dbt marts export to `data_lake/export/marts/rolling/{model_name}/` as timestamped `.parquet` files
- `generate_serving_db.py` GC keeps only the latest file (lexically max filename)
- If dbt writes a parquet file non-atomically (e.g., streaming write), an interrupted export could leave a zero-byte or truncated file as the "latest"
- The Smart View in DuckDB would then read from the corrupted file

## Current Mitigation

- DuckDB's `read_parquet()` errors on truncated/invalid parquet files — this would surface the issue at query time rather than silently return bad data
- GC only runs after dbt completes (serving asset depends on dbt asset), so mid-write interruption would mean dbt itself failed and serving wouldn't run

## Risk Assessment

**Low** — the failure mode requires:
1. dbt process killed mid-parquet-write (not a normal exit)
2. The partial file happens to be lexically latest
3. No subsequent successful dbt run overwrites it

## Investigation Steps (when prioritized)

1. Check DuckDB's `COPY TO` behavior — does it write to temp file then rename (atomic) or stream directly?
2. Check dbt-duckdb adapter source for export materialization strategy
3. If non-atomic: consider adding file size validation in `get_latest_file()` (skip zero-byte files)

## Related Files

- `scripts/provisioning/generate_serving_db.py` — GC + view creation
- `orchestration/assets/dbt.py` — dbt asset execution
- `transformation/dbt_project.yml` — materialization config
