# ADR-001: Pipeline 7-hop và ELT pattern

> **Trạng thái:** Accepted
> **Ngày:** 2026-03-31
> **Tham chiếu:** [`ARCHITECTURE.md`](../ARCHITECTURE.md), [`DATA_FLOW.md`](../DATA_FLOW.md)

## Bối cảnh

Cần thiết kế data pipeline từ Sapo (nguồn) đến Metabase (hiển thị). Hai cách tiếp cận phổ biến:
- **ETL:** Transform trong lúc extract → mất dữ liệu gốc, khó debug
- **ELT:** Load raw trước, transform sau → giữ nguyên dữ liệu gốc

## Quyết định

Áp dụng **ELT pattern** với **7 hop** rõ ràng:

```
Sources → Collection → Raw Storage → Query Layer → Staging → Transformation → Serving
(Sapo)   (dlt/webhook)  (Parquet)    (DuckDB)     (src_)    (stg_/std_/fct_)  (olap.duckdb)
```

Mỗi hop là một ranh giới rõ ràng, có thể debug và optimize độc lập.

## Lý do

1. **Raw data được bảo toàn** — mọi transform đều có thể tái tạo từ raw Parquet
2. **Transform versioned** — dbt models trong git, có thể rollback
3. **Reprocess dễ dàng** — không cần re-extract từ Sapo API
4. **Debug theo hop** — khi có lỗi, xác định ngay hop nào có vấn đề

## Hệ quả

- Cần storage cho raw data (Parquet files tích lũy theo thời gian)
- Latency cao hơn ETL thuần (data đi qua nhiều hop hơn)
- Bù lại bằng webhook channel cho near-real-time use cases

## Khi nào xem xét lại

- Nếu latency trở thành yêu cầu nghiêm ngặt (< 1 phút end-to-end) → cân nhắc streaming architecture
- Nếu storage cost tăng đáng kể → cân nhắc retention policy cho raw data
