# ADR-003: 2-level deduplication và src/stg/std 3-layer split

> **Trạng thái:** Accepted
> **Ngày:** 2026-03-31
> **Tham chiếu:** [`AGENTS.md` §Deduplication](../../AGENTS.md), [`transformation/AGENTS.md`](../../transformation/AGENTS.md)

## Bối cảnh

Append-only storage + 3 kênh ingestion = nhiều bản ghi trùng lặp. Cần dedup hiệu quả mà không gây OOM (DuckDB chạy trên single machine, memory giới hạn).

## Quyết định

### 2-level deduplication (trong src_ models)

| Level | Mục đích | Key | Phương pháp |
|:---|:---|:---|:---|
| **Tech dedup** | Loại bản ghi raw trùng | `entity_id` | Last-Write-Wins trên raw payload |
| **Biz dedup** | 1 row/business entity | Business key (e.g. `order_id`) | Last-Write-Wins trên flat data, priority: webhook > history_log > batch |

### 3-layer split

| Layer | Materialization | Vai trò | Memory impact |
|:---|:---|:---|:---|
| `src_` | INCREMENTAL table | JSON extraction + dedup | Nặng nhất — payload lớn, nhưng chỉ chạy 1 lần |
| `stg_` | VIEW | Enrichment joins, unnest | Nhẹ — không có payload |
| `std_` | VIEW | Business normalization, status mapping | Nhẹ — chỉ transform flat columns |

## Lý do

**Tại sao tách 3 layer thay vì 1 model lớn?**

Mỗi model = 1 SQL query = 1 memory budget riêng. Peak memory = `max(src_, stg_, std_)` thay vì `sum()`.

Cụ thể:
- `src_` xử lý JSON payload nặng → kết quả là flat table (payload bị loại bỏ)
- `stg_` và `std_` chỉ làm việc với flat columns → memory negligible
- Nếu gộp chung: JSON extraction + JOIN + normalization trong 1 query → OOM

**Tại sao dedup ở src_ (transformation) thay vì ở storage?**

- Storage append-only = đơn giản, không locking
- Dedup logic phức tạp (priority hierarchy, business key) → SQL dễ express và test hơn
- Thay đổi dedup logic = sửa dbt model, không cần re-ingest

## Hệ quả

- `src_` models là INCREMENTAL → cần `dbt run --full-refresh` khi thay đổi dedup logic
- 7-day lookback window xử lý late-arriving data
- Mỗi entity mới cần cả 3 model files (src_, stg_, std_)

## Khi nào xem xét lại

- Nếu upgrade lên DuckDB cluster hoặc chuyển sang engine có memory cao hơn → có thể merge layers
- Nếu dedup logic đơn giản hóa (chỉ còn 1 channel) → có thể merge src_ và stg_
