# Phase 01 — Standalone Export Script + Dagster Asset

## Context Links

- Plan: [plan.md](plan.md)
- Research: [research-260508-2305-serving-layer-design-applicability.md](../reports/research-260508-2305-serving-layer-design-applicability.md)
- Source pattern: `D:/Vantt/app/nu-data-pipeline/docs/serving-layer-design.md` §6
- Existing related: `scripts/provisioning/bootstrap_serving_views.py`, `orchestration/assets/serving.py`

## Overview

- **Priority:** P1 (core deliverable)
- **Status:** Pending
- **Description:** Tạo script materialize toàn bộ views trong `olap.duckdb` thành file `sapo_export_<timestamp>.duckdb` standalone. Wire vào Dagster nightly chain.

## Key Insights

- `olap.duckdb` chỉ chứa view definitions — query được khi parquet path tồn tại. File standalone phải là BASE TABLE (self-contained).
- Mọi input là read-only (parquet không lock, `olap.duckdb` ATTACH READ_ONLY) → không lock conflict.
- Output là file mới `.tmp` + `os.replace` → atomic, không đụng file đang được đọc.
- Pattern Popen + stream + timeout (theo L17, `serving.py:54-77`) bắt buộc cho subprocess Dagster.
- Scope: tất cả views trong schema `main` của `olap.duckdb` (không hardcode allowlist — tự động pickup khi schema thay đổi).

## Requirements

### Functional
- Build self-contained DuckDB từ olap.duckdb views.
- Timezone `Asia/Ho_Chi_Minh` set trong file output (per existing convention).
- Output 2 file: timestamped + `_latest` alias.
- GC keep last 3 standalone files.

### Non-functional
- Idempotent (chạy lại cho ra file mới timestamped, không corrupt file cũ).
- Lock-safe: parallel với Metabase + dbt được.
- Timeout 1800s (theo SERVING_TIMEOUT_SEC convention).

## Architecture

```
┌──────────────────────────────────────────────┐
│ Inputs (read-only)                            │
│  - serving/olap.duckdb (ATTACH READ_ONLY)     │
│  - export/marts/rolling/*/*.parquet (mmap)    │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
        build_standalone_export.py
        (single-process, single-writer
         on tmp file)
                   │
                   ▼
┌──────────────────────────────────────────────┐
│ Output dir: serving/standalone/               │
│  - sapo_export_<YYYYMMDDHHMMSS>.duckdb        │
│  - sapo_export_latest.duckdb (atomic copy)    │
│  - GC keeps last 3                            │
└──────────────────────────────────────────────┘
```

## Related Code Files

**CREATE:**
- `scripts/provisioning/build_standalone_export.py`

**MODIFY:**
- `orchestration/assets/serving.py` — append asset `sapo_standalone_export` after `sapo_serving_db`
- `orchestration/definitions.py` — include in nightly job selection (verify selection picks up new asset automatically; may need explicit add)

**READ for context:**
- `scripts/provisioning/bootstrap_serving_views.py` — view enumeration pattern
- `orchestration/assets/serving.py` — Popen+stream+timeout pattern to clone

## Implementation Steps

1. **Create `build_standalone_export.py`:**
   - Resolve paths: `DATA_LAKE_ROOT`, `SERVING_DIR`, `OLAP_DB`, `OUT_DIR=serving/standalone`.
   - `os.makedirs(OUT_DIR, exist_ok=True)`.
   - Compute `ts = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y%m%d%H%M%S")`.
   - Open `OUT_TMP = f"{OUT_DIR}/sapo_export_{ts}.duckdb.tmp"` via `duckdb.connect(OUT_TMP)`.
   - `SET TimeZone='Asia/Ho_Chi_Minh'`.
   - `ATTACH '{OLAP_DB}' AS src (READ_ONLY)`.
   - Enumerate views: `SELECT table_name FROM src.information_schema.tables WHERE table_schema='main' AND table_type='VIEW' ORDER BY table_name`.
   - For each view: `CREATE TABLE {view} AS SELECT * FROM src.{view}` — print row count.
   - `DETACH src`; `con.close()`.
   - `os.replace(OUT_TMP, OUT_FINAL)` (atomic).
   - Atomic refresh `_latest` alias: copy → `.tmp` → `os.replace`.
   - GC: list `sapo_export_*.duckdb` (exclude `_latest`), sort, keep last 3, delete rest with PermissionError/OSError retry (mirror `refresh_rolling.py` pattern).
   - Print summary line.

2. **Wire Dagster asset in `orchestration/assets/serving.py`:**
   - Add constant `STANDALONE_SCRIPT = scripts/provisioning/build_standalone_export.py`.
   - Define `@asset deps=[sapo_serving_db], group_name="serving_layer"`.
   - Reuse Popen+stream+timeout pattern from existing `sapo_serving_db` (extract helper if duplication > 30 lines).
   - Detect `[!] WARNING|ERROR|Failed` markers same as existing.

3. **Verify nightly job picks up new asset:**
   - Read `orchestration/definitions.py` selection definitions.
   - If `sapo_serving_db.downstream()` is selected → auto-includes.
   - Else add explicit asset key.

4. **Compile check:** `python -c "import scripts.provisioning.build_standalone_export"` (syntax only).

5. **Manual run:** `docker compose exec data_platform python scripts/provisioning/build_standalone_export.py`. Verify file created.

6. **DuckDB CLI verification:**
   ```bash
   docker cp data_platform:/app/var/data_lake/serving/standalone/sapo_export_latest.duckdb /tmp/
   duckdb /tmp/sapo_export_latest.duckdb -c "SHOW TABLES; SELECT count(*) FROM fact_orders;"
   ```

## Todo List

- [ ] Create `build_standalone_export.py`
- [ ] Add `sapo_standalone_export` asset in `serving.py`
- [ ] Verify Dagster asset graph (selection includes new asset)
- [ ] Compile check
- [ ] Manual run inside container
- [ ] Verify file query works standalone
- [ ] Confirm Metabase still functional during build

## Success Criteria

- File `serving/standalone/sapo_export_latest.duckdb` exists, size ~ tổng marts.
- All views materialized as base tables (verify via `SELECT table_type FROM information_schema.tables`).
- Row counts khớp với olap.duckdb views.
- Standalone file query được khi mang ra ngoài container (no parquet path needed).
- GC giữ đúng 3 file timestamped + 1 file `_latest` sau ≥ 4 runs.
- Dagster nightly run xanh, asset complete trong < 10 phút.

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Build time tăng nightly window | Asset song song được với non-DB workloads; hard timeout 1800s; có thể mark schedule `nightly_low_priority` |
| Storage growth (3 snapshots × full marts) | GC keep last 3; total ~ 3-9 GB ước tính; monitor `app_data/data_lake/serving/standalone` size |
| dbt build crash → olap.duckdb stale views | Asset `deps=[sapo_serving_db]` ensures upstream success; views không thay đổi giữa runs |
| `_latest.duckdb` overwrite vs reader hold | `os.replace` atomic, reader thấy file cũ until replace done. POSIX/NTFS đều OK |

## Security Considerations

- File chứa **toàn bộ business data** — phải gate qua basic_auth (Phase 2).
- Không log sensitive content; chỉ row counts, table names.
- File path không được expose ngoài Docker network unless via fileserver service.

## Next Steps

- Phase 2: Fileserver service mount `serving/standalone` để expose qua HTTP.
- Phase 4: Update `data-flow.md` để document new branch.
