# Architecture Decision Records (ADR)

Thư mục này ghi nhận các quyết định kiến trúc quan trọng của dự án. Mỗi ADR giải thích **bối cảnh**, **quyết định**, **lý do**, và **khi nào cần xem xét lại**.

## Mục lục

### Data Architecture
- [ADR-001: Pipeline 7-hop và ELT pattern](./001-pipeline-7-hop-elt.md)
- [ADR-002: Immutable append-only data lake với segregated storage](./002-immutable-data-lake.md)
- [ADR-003: 2-level deduplication và src/stg/std 3-layer split](./003-deduplication-3-layer.md)
- [ADR-004: 3-channel ingestion redundancy](./004-three-channel-ingestion.md)
- [ADR-005: Dual DuckDB strategy (warehouse vs. serving)](./005-dual-duckdb.md)

### Orchestration & Concurrency
- [ADR-006: Asset-level locking, priority hierarchy, schedule offset](./006-concurrency-strategy.md)
- [ADR-007: Hybrid job explicit dependencies](./007-hybrid-job-dependencies.md)

### Analytics & BI
- [ADR-008: Analytics-as-Code với Markdown blueprints](./008-analytics-as-code.md)
- [ADR-009: Collection tổ chức theo audience, không theo chủ đề](./009-collection-by-audience.md)
- [ADR-010: Dashboard sở hữu riêng questions, không share](./010-dashboard-owns-questions.md)
- [ADR-011: Dashboard archetypes (Pulse / Cockpit / Exploratory)](./011-dashboard-archetypes.md)

### Technology Stack
- [ADR-012: Lựa chọn technology stack (DuckDB, Parquet, dbt, dlt, Dagster)](./012-technology-stack.md)

### Development Practices
- [ADR-013: Explicit > Implicit, Golden Sample heuristic](./013-development-heuristics.md)

## Quy ước

- **Đánh số:** `NNN-tên-ngắn-gọn.md` (ví dụ: `001-pipeline-7-hop-elt.md`)
- **Trạng thái:** `Proposed` → `Accepted` → `Deprecated` / `Superseded by ADR-XXX`
- **Ngôn ngữ:** Tiếng Việt (nội dung), tiếng Anh (thuật ngữ kỹ thuật)
- **Khi nào tạo ADR mới:** Khi có quyết định thiết kế không hiển nhiên, có trade-off, và có thể bị đặt câu hỏi trong tương lai
