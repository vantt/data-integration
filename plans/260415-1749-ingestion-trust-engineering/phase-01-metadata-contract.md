# Phase 1 — Metadata Contract Rollout

## Context Links
- Parent plan: [../plan.md](./plan.md)
- Writer: `orchestration/ops/ingestion_health.py` (commit `bb5c965`)
- Pilot pattern: `orchestration/assets/sapo_assets.py::sapo_orders_batch_asset`

## Overview
- **Priority:** P1 — unblocks Phases 2, 3, 4
- **Status:** ✅ DONE (commit `5801b31`)
- **Effort:** ~6h
- **Summary:** Retrofit every ingestion asset to call `_record_health` with standardized metadata. Extract shared DLT-metrics helper. File-drop assets additionally emit `file_sha256`, `file_mtime`, `rows_fetched` from Excel.

## Key Insights
- Pilot (`sapo_orders_batch_asset`) proves the try/finally pattern is safe — health-write failure never breaks asset materialization.
- `_extract_rows_written` currently lives inside `sapo_assets.py` — must factor out before replicating, else DRY violation across 4 asset modules.
- File-drop assets (Shopee, MISA) currently have NO row-count visibility at all — Excel is ground truth; we must hash + count at ingestion boundary.
- Google Sheets assets have no row count surfaced — likely need a follow-up in the `gsheet_*` run modules to return row counts; for Phase 1 just record success/failure + timing.

## Requirements

### Functional
- Every ingestion asset, on every materialize, writes exactly one row to `ingestion_health.ingestion_runs` with PK `(asset_key, run_id)`.
- `status` ∈ {`success`, `skipped` (DLT loaded 0 packages), `failed`}.
- `rows_written` populated from DLT `LoadInfo` where DLT is the writer.
- File-drop assets: `file_sha256`, `file_mtime`, `rows_fetched` (rows parsed from xlsx), `rows_written` (rows into raw table).
- Health-write failure MUST NOT raise from the asset body (try/finally guard).

### Non-functional
- Shared helper in one module; no duplication across 4 asset files.
- Each modified asset file stays < 200 lines (split if needed).
- No change to existing asset return values (would break downstream expectations).

## Architecture

```
┌────────────────────────────────────────────┐
│ orchestration/ops/dlt_metrics.py  (NEW)    │
│   extract_rows_written(info_dict) -> int?  │
│   compute_schema_hash(info_dict) -> str?   │  (optional, stretch)
└─────────────┬──────────────────────────────┘
              │ imported by
              ▼
┌────────────────────────────────────────────┐
│ orchestration/ops/file_metrics.py (NEW)    │
│   hash_and_count_xlsx(path) ->             │
│     (sha256, mtime, row_count)             │
└─────────────┬──────────────────────────────┘
              │ imported by file-drop assets
              ▼
┌────────────────────────────────────────────┐
│ Each ingestion asset                       │
│   try: run dlt / parse file                │
│   finally: _record_health(...)             │
└────────────────────────────────────────────┘
```

## Related Code Files

### Create
- `orchestration/ops/dlt_metrics.py` — move `_extract_rows_written` here; add `extract_loaded_packages`, `derive_status`.
- `orchestration/ops/file_metrics.py` — `hash_and_count_xlsx(path) -> dict` returns `{sha256, mtime_utc, row_count, sheet_count}` using `openpyxl` (already a dep via DLT stack) or `pandas.read_excel(nrows=None)` followed by shape.

### Modify
- `orchestration/assets/sapo_assets.py` — (a) delete local `_extract_rows_written`, import from `ops.dlt_metrics`; (b) apply try/finally + `_record_health` to the 5 non-pilot assets: `sapo_customers_batch_asset`, `sapo_accounts_batch_asset`, `sapo_products_batch_asset`, `sapo_history_log_asset`, `sapo_webhook_consumer_asset`.
- `orchestration/assets/misa_amis_assets.py` — wrap with try/finally, call `hash_and_count_xlsx` on each input file before/after processing, record health.
- `orchestration/assets/shopee_assets.py` — same as MISA.
- `orchestration/assets/sheets_assets.py` — try/finally + `_record_health`; `rows_written=None` (unknown without refactoring gsheet_* modules — accept this for now, TODO note).

### Delete
- None.

## Implementation Steps

1. **Create `orchestration/ops/dlt_metrics.py`**:
   ```python
   def extract_rows_written(info_dict: dict) -> int | None: ...  # moved verbatim
   def extract_loaded_packages(info_dict: dict) -> list[str]:
       return info_dict.get("loads_ids", []) or []
   def derive_status(load_info_or_none) -> str:
       if load_info_or_none is None: return "failed"
       pkgs = extract_loaded_packages(load_info_or_none.asdict() if hasattr(load_info_or_none, 'asdict') else {})
       return "success" if pkgs else "skipped"
   ```
2. **Create `orchestration/ops/file_metrics.py`**:
   ```python
   def hash_and_count_xlsx(path: str) -> dict:
       # sha256 streamed in 64kb chunks; mtime as UTC datetime; row count = sum(ws.max_row-1 for ws in wb.worksheets)
       return {"sha256": ..., "mtime_utc": ..., "row_count": ..., "sheet_count": ...}
   ```
3. **Refactor `sapo_assets.py`** — remove local `_extract_rows_written`, import from `ops.dlt_metrics`. Verify pilot still works.
4. **Retrofit remaining 5 Sapo assets** — copy the pilot try/finally block. `asset_key_str` = `"sapo/<asset_function_name>"`.
5. **Retrofit MISA asset** — before `_get_run_module().run()`, enumerate xlsx files in `misa-amis/` input dir (excluding `_archive/`), compute sha256+mtime+rowcount for the set, aggregate into `metadata.file_manifest`, also set top-level `file_sha256` = hash-of-hashes, `file_mtime` = max mtime. Then run DLT. After run, `rows_written` = best-effort via `dlt_metrics` if DLT surface available, else None.
6. **Retrofit Shopee asset** — same shape as MISA.
7. **Retrofit Sheets assets** — minimal try/finally + `_record_health(status, metadata={"gsheet_row_count": None})`. Add TODO comment to surface row count from `gsheet_targets.run()` / `gsheet_marketing_spend.run()` in a follow-up.
8. **Smoke test**: trigger each modified asset once from Dagster UI; verify one row per run in `ingestion_health.ingestion_runs` via:
   ```sql
   SELECT asset_key, run_id, status, rows_written, rows_fetched, file_sha256
   FROM ingestion_runs ORDER BY run_started_at DESC LIMIT 20;
   ```
9. **Docstring** each modified asset with a 1-line note: `# Writes to ingestion_health via orchestration.ops.ingestion_health`.

## Todo List

- [ ] Create `orchestration/ops/dlt_metrics.py`
- [ ] Create `orchestration/ops/file_metrics.py`
- [ ] Refactor `sapo_assets.py` to import from `dlt_metrics`; remove local helper
- [ ] Retrofit `sapo_customers_batch_asset`
- [ ] Retrofit `sapo_accounts_batch_asset`
- [ ] Retrofit `sapo_products_batch_asset`
- [ ] Retrofit `sapo_history_log_asset`
- [ ] Retrofit `sapo_webhook_consumer_asset`
- [ ] Retrofit `misa_sales_file_drop_asset` with file-hash+count
- [ ] Retrofit `shopee_income_file_drop_asset` with file-hash+count
- [ ] Retrofit `sheets_targets_asset`
- [ ] Retrofit `sheets_marketing_spend_asset`
- [ ] Smoke test: one manual materialize per asset, verify row in `ingestion_runs`
- [ ] Compile check: `python -c "import orchestration.definitions"` must exit 0

## Success Criteria

- Running `SELECT count(DISTINCT asset_key) FROM ingestion_runs` after a full nightly cycle returns **≥ 9** (6 Sapo + 1 MISA + 1 Shopee + 2 Sheets — Sapo count is 6 assets; 10 total).
- Failure-mode test: break a Sapo credential deliberately → asset raises → `status='failed'` row still present.
- No regression in existing jobs: `sapo_realtime_sync_job`, `sapo_nightly_reconciliation_job` still succeed.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Health-DB lock during concurrent writes | Low | Med | DuckDB connection per call, short critical section; pk `INSERT OR REPLACE` is atomic |
| `hash_and_count_xlsx` slow on very large Shopee files | Med | Low | Stream hash in 64kb chunks; row count via `openpyxl` read-only mode |
| DLT `LoadInfo.asdict()` shape differs between dlt versions | Med | Med | `extract_rows_written` already defensive; add unit test with fixture dicts |
| Sheets `gsheet_*.run()` returns None — can't derive `rows_written` | High | Low | Accept `rows_written=None`; follow-up ticket to surface it |
| File-drop sensor triggers mid-archive → file disappears before hash | Low | Med | Hash BEFORE run module moves file to `_archive/`; wrap in try/except FileNotFoundError |

## Next Steps

- Phase 2 can start as soon as at least 3 assets are rolled out (orders, webhook, one file-drop) — asset_check patterns don't need all 10.
- Phase 3 waits for Phase 1 + research gate.
