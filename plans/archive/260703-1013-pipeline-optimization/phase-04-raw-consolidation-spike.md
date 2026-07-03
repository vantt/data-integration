# Phase 4: Raw Data Consolidation — Deferred
**Status:** 🔵 Monitor, implement khi file count vượt ~2000 history_log files  
**Spike findings:** `spike-raw-consolidation-findings.md`

## Tại Sao Defer

### ROI thấp hơn dự kiến

Normal incremental run dùng `_dlt_load_id > cursor` — chỉ đọc files MỚI, không scan 978 history_log files cũ. 978 small files chỉ gây overhead khi `dbt run --full-refresh` (rare, vài lần/năm khi thêm column hoặc sửa schema). Compact job phức tạp hơn benefit từ full-refresh speedup.

### Delta Lake complication

Webhook data (`ingest_method=webhook`) dùng `table_format="delta"` trong dlt pipeline. Delta Lake lưu transaction log trong `_delta_log/`. Compact parquet files của Delta table thủ công (plain merge) sẽ **corrupt** Delta log vì log references specific file paths.

→ Compact webhook data phải dùng Delta's `OPTIMIZE` + `VACUUM` commands, không phải plain merge.

→ Cần verify riêng: history_log và batch_sync có dùng Delta format không (likely plain parquet, nhưng chưa confirm).

### Batch_sync không phải target

78 files, 184.9 MB — cursor-based bulk pulls, already "consolidated" per pull. Không có lý do compact.

---

## Điều Kiện Để Trigger Implementation

Implement Phase 4 khi **một trong các điều kiện** sau xảy ra:

1. **history_log file count > 2000** (tốc độ hiện tại ~978 files/7 tháng → dự kiến hit ngưỡng Q1 2027)
2. **`dbt run --full-refresh` trên src_sapo_v2_orders mất > 5 phút** (benchmark hiện tại cần đo)
3. **Disk usage của sapo_raw/order/ vượt 1 GB**

Theo dõi qua: Dagster asset metadata hoặc Metabase alert.

---

## Pre-conditions Khi Implement (từ Spike)

1. ✅ Unique test trên `stg_sapo_v2_orders.order_id` (đã add trong Phase 1)
2. ⬜ Verify `ingest_method=history_log` dùng plain parquet (không phải Delta)
3. ⬜ Backup dlt state trước khi compact: `_dlt_pipeline_state/sapo_v2_*.jsonl`
4. ⬜ Test trên `sapo_raw_staging` (dev dataset) trước production
5. ⬜ Playbook dlt state restore nếu compact gây cursor corruption

---

## Thiết Kế Dự Kiến (Khi Cần)

### Target

- **history_log** files cũ hơn 90 ngày: merge theo tháng thành 1 super-parquet
- **Webhook Delta**: dùng `OPTIMIZE` + `VACUUM RETAIN 0 HOURS` qua Delta Lake API
- **Batch_sync**: không compact
- **MISA**: không compact (file-drop pattern, đã tự-consolidated)

### Compact Strategy (history_log plain parquet)

```python
# Dagster asset: compact_history_log_raw
# Điều kiện: chạy monthly, chỉ compact data > 90 ngày
# Input: sapo_raw/order/ingest_method=history_log/year={Y}/month={M}/
# Output: sapo_raw/order/consolidated/year={Y}/month={M}/data.parquet
# Bảo toàn: _dlt_load_id column (required for cursor compatibility)
# Giữ original: 30 ngày sau compact trước khi delete
```

### DuckDB Read Pattern Sau Compact

```sql
-- Cần update source definition để đọc cả hai locations
SELECT * FROM read_parquet([
    'sapo_raw/order/ingest_method=history_log/**/*.parquet',
    'sapo_raw/order/consolidated/**/*.parquet'
], hive_partitioning=true, union_by_name=true)
```

---

## Unresolved Questions

1. history_log và batch_sync có dùng Delta format không? (check `_delta_log/` trong từng ingest_method dir)
2. dlt source definition (`{{ source('sapo_v2_raw', 'order') }}`) đọc từ path nào? Có pick up `consolidated/` subdir không?
3. Nếu dlt re-run history_log sau compact, nó có ghi files mới vào `consolidated/` dir không? (conflict risk)
