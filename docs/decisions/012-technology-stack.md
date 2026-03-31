# ADR-012: Lựa chọn technology stack

> **Trạng thái:** Accepted
> **Ngày:** 2026-03-31
> **Tham chiếu:** [`ARCHITECTURE.md` §Technology Decisions](../ARCHITECTURE.md)

## Bối cảnh

Cần chọn technology cho mỗi layer trong data pipeline. Ưu tiên: local-first, low-cost, simple operations, đủ mạnh cho SME scale.

## Quyết định

| Layer | Tool | Alternatives Rejected | Lý do chọn |
|:---|:---|:---|:---|
| **Storage** | Parquet | CSV, JSON, Delta Lake | Columnar, compression 70%, schema evolution, industry standard |
| **Query Engine** | DuckDB | PostgreSQL, BigQuery, Spark | Embedded (no server), vectorized OLAP, native Parquet, zero config |
| **Ingestion** | dlt | Airbyte, Fivetran, custom scripts | Python-native, incremental loading built-in, local-first |
| **Transformation** | dbt | Custom SQL, Spark | Versioned SQL, DAG resolution, testing framework, community |
| **Orchestration** | Dagster | Airflow, Prefect, Cron | Asset-centric, great DX, native dbt integration, concurrency control |
| **BI** | Metabase | Superset, Looker, Redash | OSS, easy setup, good enough for SME, Docker-friendly |
| **Webhook Buffer** | Cloudflare D1 | Redis, SQS, PostgreSQL | Serverless, high availability, at-least-once delivery, no infra to manage |

## Lý do tổng thể

**Local-first architecture:**
- Không phụ thuộc cloud services (trừ webhook buffer)
- Cost gần bằng 0 cho compute/storage
- Full control — không bị vendor lock-in
- Phù hợp SME scale (< 10M rows/entity)

**Modern data stack nhưng lightweight:**
- dlt + dbt + Dagster là "modern data stack" community version
- Mỗi tool best-in-class cho niche của nó
- Tích hợp tốt với nhau (Dagster + dbt native, dlt + Parquet native)

## Hệ quả

- DuckDB single-file → cần dual DB strategy và locking (xem ADR-005, ADR-006)
- Local-first → scale limited bởi single machine resources
- Dlt + Dagster đều Python → team cần Python skills

## Khi nào xem xét lại

- Data vượt 100M rows/entity → cân nhắc ClickHouse hoặc DuckDB server
- Team > 10 data engineers → cân nhắc managed services (Databricks, Snowflake)
- Real-time requirement < 1 second → cân nhắc streaming (Kafka + Flink)
