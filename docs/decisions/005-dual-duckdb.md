# ADR-005: Dual DuckDB strategy (warehouse vs. serving)

> **Trạng thái:** Accepted
> **Ngày:** 2026-03-31
> **Tham chiếu:** [`AGENTS.md` §Dual DuckDB](../../AGENTS.md), [`ARCHITECTURE.md`](../architecture/overview.md)

## Bối cảnh

DuckDB là single-file database, không hỗ trợ concurrent writes. dbt cần write models, Metabase cần read queries. Nếu dùng chung 1 file → lock conflict.

## Quyết định

Tách thành **2 DuckDB files**:

| File | Vai trò | Ai truy cập |
|:---|:---|:---|
| `sapo_warehouse.duckdb` | Write DB — dbt writes models | Dagster/dbt (write) |
| `serving/olap.duckdb` | Read DB — Metabase queries | Metabase (read-only) |

Quy trình: dbt → export marts sang timestamped Parquet → serving DB tạo views trỏ đến latest snapshot.

## Lý do

1. **Không lock conflict** — dbt write không block Metabase read
2. **Zero-downtime** — users tiếp tục query trong khi warehouse đang transform
3. **Rolling snapshots** — `dim_customers_20260128_1001.parquet` → view auto-select latest
4. **Easy rollback** — giữ snapshot cũ, revert view nếu cần

## Hệ quả

- Cần `generate_serving_db.py` script để sync warehouse → serving
- Mart models phải có `location="{{ get_rolling_location() }}"` (CRITICAL config)
- Slight delay giữa transform complete và data available trên Metabase

## Khi nào xem xét lại

- Nếu chuyển sang DuckDB server mode (khi có) → có thể dùng 1 instance
- Nếu chuyển sang PostgreSQL/ClickHouse → concurrent access native
