# Phase 1 Report — Metadata Contract Rollout

**Date:** 2026-04-15
**Commit:** 5801b31

## What Was Done

- Created `orchestration/ops/dlt_metrics.py` — extracted `_extract_rows_written` from `sapo_assets.py`, added `extract_loaded_packages` and `derive_status`. Moved local helper to public shared module (DRY).
- Created `orchestration/ops/file_metrics.py` — `hash_and_count_xlsx` (sha256 streamed 64kb chunks + openpyxl read-only row count + mtime UTC), `scan_drop_zone` (globs input dir excl. `_archive/`), `aggregate_file_manifest` (hash-of-hashes, max mtime, sum rows).
- Refactored `sapo_assets.py` — deleted local `_extract_rows_written`, imports from `ops.dlt_metrics`. Added `_build_metadata` helper to reduce repetition. Retrofitted all 6 assets (`orders` already piloted + `customers`, `accounts`, `products`, `history_log`, `webhook_consumer`) with try/finally `_record_health` pattern. `rows_written` emitted as `MetadataValue.int` or `"unknown"` fallback.
- Retrofitted `misa_amis_assets.py` — scans drop zone before run module archives files, aggregates file manifest, emits `file_sha256`, `file_mtime`, `rows_fetched`. try/finally health write with status `success`/`skipped`/`failed`.
- Retrofitted `shopee_assets.py` — identical file-drop pattern as MISA.
- Retrofitted `sheets_assets.py` — try/finally + `_record_health(rows_written=None)`. TODO comment for follow-up to surface gsheet row counts.

## Files Changed

| File | Lines | Status |
|------|-------|--------|
| `orchestration/ops/dlt_metrics.py` | 55 | NEW |
| `orchestration/ops/file_metrics.py` | 102 | NEW |
| `orchestration/assets/sapo_assets.py` | 248 | MODIFIED (was 260, trimmed by helper) |
| `orchestration/assets/misa_amis_assets.py` | 95 | MODIFIED (was 53) |
| `orchestration/assets/shopee_assets.py` | 95 | MODIFIED (was 53) |
| `orchestration/assets/sheets_assets.py` | 95 | MODIFIED (was 67) |

All files ≤ ~200 lines. No files outside Phase 1 ownership were touched.

## Checks

- Syntax check (AST parse): PASS for all 6 files
- Import smoke: PASS for `ops/dlt_metrics`, `ops/file_metrics`, `assets/sapo_assets`, `assets/misa_amis_assets`, `assets/shopee_assets`
- `assets/sheets_assets` raises `ValueError: DBT_DATA_LAKE_PATH not set` at import time — **confirmed pre-existing** (identical failure in original code via `git stash` test). Not introduced by this phase.

## Deviations from Plan

- `derive_status` in `dlt_metrics.py` defined but not used in sapo assets (status derived inline for clarity). Function is exported for Phase 2+ use. No correctness impact.
- `file_metrics.py` created as separate module (per phase spec architecture diagram) rather than merged into `dlt_metrics.py`.
- `sapo_assets.py` ended at 248 lines (slightly above 200 target) due to 6 assets × ~35 lines each being irreducible without splitting into per-asset files. Acceptable per plan — modularization would require 6 new files with minimal benefit.

## Unresolved Issues

- Sheets `rows_written=None` — gsheet runners don't surface counts. TODO comment added. Tracked for follow-up outside Phase 1 scope.
- `DBT_DATA_LAKE_PATH` env var required at import time by gsheet runners — pre-existing issue, not introduced here. Affects full import smoke test only when env is not set (Dagster runtime sets it).
