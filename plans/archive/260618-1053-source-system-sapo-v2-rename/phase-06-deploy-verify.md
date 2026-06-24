# Phase 6: Deploy + Dagster Full Run + Verify

**Priority:** P1  
**Status:** DONE_PARTIAL (Phase 4 webhook deploy pending user action)  
**Depends on:** Phase 2 + Phase 3 + Phase 4 + Phase 5 hoàn thành  

## Overview

Full pipeline run để sinh ra mart outputs mới với `source_system='sapo_v2'`.  
Verify row counts không đổi, Metabase dashboards không vỡ, parquet exports được cleanup.

## Pre-flight Checklist

Trước khi chạy Dagster:

- [ ] Phase 2: tất cả `std_*.sql` đã commit, dbt compile không lỗi
- [ ] Phase 3: CRM SQLite migration đã apply (`crm.db` không còn `source_system='sapo'`)
- [ ] Phase 4: ingestion code + consumer đã deploy
- [ ] Phase 5: Supabase migration đã chạy
- [ ] Không có Dagster run nào đang chạy (kiểm tra UI hoặc `dagster job list`)
- [ ] **Scan Metabase blueprints** cho hardcoded `source_system = 'sapo'` filter (xem bên dưới)

## Metabase Pre-check

```bash
grep -r "source_system.*sapo[^_v]" docs/analytics-handbook/blueprints/ --include="*.md"
grep -r "source_system.*'sapo'" docs/analytics-handbook/blueprints/ --include="*.md"
```

Nếu tìm thấy → update blueprint + redeploy card đó TRƯỚC khi chạy pipeline.

## Dagster Run

```bash
# Chạy full sapo pipeline assets
dagster asset materialize --select "sapo_warehouse/*"

# Hoặc nếu muốn chạy toàn bộ
dagster job execute -j sapo_dbt_assets
```

Monitor trên Dagster UI. Expected: tất cả assets GREEN.

## Post-run Verification

### 1. Row counts không đổi

```sql
-- Trong DuckDB / olap.duckdb
SELECT source_system, COUNT(*) FROM main_marts.fact_orders GROUP BY 1;
SELECT source_system, COUNT(*) FROM main_marts.fact_order_costs GROUP BY 1;
-- Expect: 'sapo_v2' với same row count như trước (không phải 'sapo')
```

### 2. Không còn bare 'sapo' trong marts

```sql
SELECT DISTINCT source_system FROM main_marts.fact_orders;
SELECT DISTINCT source_system FROM main_marts.fact_order_items;
SELECT DISTINCT source_system FROM main_marts.fact_order_costs;
-- None of these should return 'sapo'
```

### 3. Parquet export cleanup

Sau khi Dagster run sinh ra parquet mới trong `data_lake/export/marts/rolling/fact_order_costs/`:

```python
import pyarrow.parquet as pq, glob

files = glob.glob('app_data/data_lake/export/marts/rolling/fact_order_costs/*.parquet')
for f in files:
    vals = pq.read_table(f, columns=['source_system']).column('source_system').unique().to_pylist()
    print(f, vals)
```

- Files mới: chỉ có `'sapo_v2'`
- Files cũ (timestamp cũ): vẫn có `'sapo'` → **xoá các file cũ** sau khi confirm file mới đúng
- DuckDB read strategy: nếu đọc tất cả `*.parquet` trong folder → double count nếu giữ cả cũ và mới

### 4. Metabase spot check

Mở 3-5 dashboard quan trọng, verify:
- Numbers không thay đổi so với trước run
- Không có error card nào
- Filter dropdowns cho `source_system` nếu có → `sapo_v2` xuất hiện thay `sapo`

### 5. CRM verify

```bash
# Check crm.db
sqlite3 app_data/crm/crm.db "SELECT source_system, COUNT(*) FROM crm_party_identity GROUP BY 1;"
# Expect: sapo_v2 | N (không còn sapo)
```

## Rollback Plan

Nếu có vấn đề sau run:

1. **Warehouse SQL**: git revert Phase 2 commits → re-run dbt → xuất ra `'sapo'` lại
2. **CRM**: rollback SQLite migration bằng Down migration (thêm `.down.sql` với UPDATE ngược lại)
3. **Supabase**: chạy SQL reverse (UPDATE `sapo_v2` → `sapo`, restore old constraint)
4. **Parquet**: files cũ (với `'sapo'`) vẫn còn → chỉ cần xoá files mới

## Success Criteria

- [ ] Dagster run hoàn thành 100% GREEN, không asset nào failed
- [ ] `SELECT DISTINCT source_system` trên tất cả major marts → không còn bare `'sapo'`
- [ ] Parquet exports mới chỉ có `'sapo_v2'`; files cũ đã xoá
- [ ] Metabase dashboards hiển thị đúng số liệu
- [ ] CRM `crm_party_identity` không còn `source_system='sapo'`
- [ ] `grep -r "'sapo'" transformation/models/` → 0 kết quả (trừ compound nếu giữ nguyên)
