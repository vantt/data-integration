# Plan: Metabase Collection Restructure + Doc Sync + P&L Domain

> **Created:** 2026-05-27 13:27
> **Owner:** Data Team
> **Branch:** main
> **Trigger:** Audit `audit-260527-1202-metabase-collection-tree.md` phát hiện 7 cặp duplicate, drift spec↔live, 3 sub-1-board, audience mismatch + 3 mart P&L mới chưa có dashboard.
> **Mục tiêu:** UX tối đa cho end-user — mỗi audience 1 folder, mỗi dashboard 1 scope rõ ràng.

---

## Phases

| # | Phase | Status | File |
|:---|:---|:---|:---|
| 01 | Data Scan & Discovery (P&L domain) | DONE | [phase-01-data-scan-discovery.md](./phase-01-data-scan-discovery.md) |
| 02 | Archive 7 Dashboard Duplicates | DONE | [phase-02-archive-duplicates.md](./phase-02-archive-duplicates.md) |
| 03 | Collection Tree Restructure | DONE | [phase-03-collection-restructure.md](./phase-03-collection-restructure.md) |
| 04 | Dashboard Relocation (10 moves) | DONE | [phase-04-dashboard-relocation.md](./phase-04-dashboard-relocation.md) |
| 05 | New Finance Dashboards Roadmap | DONE | [phase-05-new-finance-dashboards.md](./phase-05-new-finance-dashboards.md) |
| 06 | Documentation Sync (5 files) | DONE | [phase-06-docs-sync.md](./phase-06-docs-sync.md) |
| 07 | Validation & Rollout | DONE | [phase-07-validation-rollout.md](./phase-07-validation-rollout.md) |

---

## Cấu trúc mục tiêu (6 top-level)

```text
📁 📍 Start Here              ← onboarding (NEW)
📁 Executive                  ← CEO/Founders, 3 boards (trimmed)
📁 Finance                    ← CFO/FP&A/Accounting (NEW — driven by P&L mart explosion)
📁 Marketing & Customers      ← Marketing + CS
📁 Operations                 ← Store Manager + Sales Ops + B2B + Logistics + Data team
📁 Analytics                  ← Analyst (Layer 3 cross-segment)
```

## Vấn đề phát sinh đã phát hiện

| # | Issue | Phase giải quyết |
|:---|:---|:---|
| 1 | 7 cặp duplicate (3 loại: true clone / refactor / semantic) | Phase 02 |
| 2 | Drift spec↔live: 6 collection paths trong blueprints không đăng ký | Phase 06 |
| 3 | 3 sub-collection chỉ 1 board (Retail Ops, CrossBorder Ops, Order Management) | Phase 03 |
| 4 | Audience mismatch: Ingestion Health + Logistics ở Daily Monitoring | Phase 04 |
| 5 | 2 Promotion dashboards trùng logic ở 2 collection | Phase 04 |
| 6 | 3 mart P&L mới (fact_order_costs, fact_order_returns, fact_order_economics) — 2 chưa có dashboard | Phase 05 |
| 7 | Doc bất nhất: 3 nói có Analytics, 2 không | Phase 06 |
| 8 | Không có validation chống drift tương lai | Phase 07 |
| 9 | Không có archive policy → migration đẻ duplicate | Phase 06 + 07 |

## Key Dependencies

- Phase 02 → 03 → 04: thứ tự bắt buộc (archive trước khi move, move trước khi xoá folder)
- Phase 06 chạy SAU 03+04 để doc khớp với live state
- Phase 05 độc lập, có thể chạy bất cứ lúc nào
- Phase 07 chạy cuối — validation + Lark notification

## Success Criteria toàn plan

- [ ] 0 dashboard duplicate trong live Metabase
- [ ] 0 sub-collection có ≤1 dashboard (trừ growing folder có roadmap)
- [ ] 5 doc gốc nhất quán + nhất quán với `collection_registry.yml`
- [ ] Validation script chạy được trong CI, fail nếu drift
- [ ] Mọi dashboard có suffix scope `[All]/[Retail]/[B2B]/[Cross]/[US]`
- [ ] Mọi dashboard có description ≥1 dòng audience + scope + câu hỏi chính

## Quyết định cần user xác nhận trước khi chạy Phase 02

1. **Finance top-level**: tạo hay gộp vào Executive? (Plan này đề xuất TẠO — rationale ở phase-01.)
2. **Loại C archive**: chắc chắn archive 4 bản mixed scope (Daily Sales, Yesterday's Sales, Marketing Weekly, Customer Op)? View count cũ rất cao (286 cho Yesterday).
3. **Channel Profitability Monthly**: ở Executive hay Analytics? (Plan đề xuất Analytics vì là cross-segment comparison.)
