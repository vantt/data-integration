# ADR-002: Immutable append-only data lake với segregated storage

> **Trạng thái:** Accepted
> **Ngày:** 2026-03-31
> **Tham chiếu:** [`ARCHITECTURE.md` §Immutable Data Lake](../architecture/overview.md), [`AGENTS.md` §Data Flow](../../AGENTS.md)

## Bối cảnh

Raw data từ Sapo đến qua 3 kênh (batch, webhook, history log). Cần quyết định:
- Ghi đè (upsert) hay append-only?
- Gộp chung hay tách theo kênh ingestion?

## Quyết định

1. **Append-only:** Parquet files không bao giờ bị sửa hoặc xóa trong vận hành bình thường.
2. **Segregated storage:** Tách theo `ingest_method=batch_sync/`, `ingest_method=webhook/`, `ingest_method=history_log/`.

## Lý do

### Append-only
- **Audit trail** đầy đủ — có thể time-travel query
- **Concurrent access** an toàn — không cần locking
- **Rollback đơn giản** — xóa partition của source cụ thể để re-sync

### Segregated storage
- **Selective re-sync** — re-sync webhook mà không ảnh hưởng batch data
- **Data lineage** rõ ràng — biết record đến từ kênh nào
- **Source-aware dedup** — ưu tiên kênh real-time (webhook > history_log > batch)

## Hệ quả

- Raw storage tăng theo thời gian (append-only = không xóa)
- Deduplication xảy ra ở tầng transformation (src_ models), không ở storage
- Cần monitoring storage size và retention policy khi cần

## Khi nào xem xét lại

- Storage vượt ngưỡng chấp nhận → thêm retention/compaction policy
- Nếu chuyển sang Delta Lake/Iceberg → có thể dùng MERGE thay append
