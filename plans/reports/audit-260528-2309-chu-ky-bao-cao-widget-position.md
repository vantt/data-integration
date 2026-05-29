# Audit: "Chu kỳ báo cáo" widget position across multi-tab dashboards

**Date:** 2026-05-28
**Scope:** Tất cả active Metabase dashboards có >= 2 tabs
**Source:** Metabase API (http://127.0.0.1:3001/) — live state, NOT blueprints
**Rule:** Widget "Chu kỳ báo cáo" PHẢI ở row 0 hoặc 1 (widget đầu tiên) trong mọi tab

## Tóm tắt

- Tổng dashboards active: **49**
- Dashboards multi-tabs (>= 2 tabs): **37**
- Tổng tabs đã kiểm tra: **~115**
- Dashboards có ít nhất 1 tab vi phạm (row >= 2): **8**
- Dashboards MISSING widget hoàn toàn: **2** (1 sample + 1 dashboard mới)

## Dashboards vi phạm (row >= 2) — CẦN SỬA

| Dashboard ID | Dashboard Name | Tab vi phạm | Tab ID | Row hiện tại |
|---|---|---|---|---|
| 33 | Channel Profitability Monthly [Cross] | Channel Overview | 108 | 2 |
| 15 | Customer Intelligence Monthly [Cross] | Overview & Health | 84 | 2 |
| 14 | Customer Retention & Lifecycle [Retail] | Suc khoe Retention | 87 | 2 |
| 34 | Finance P&L [All] | P&L Overview | 110 | 2 |
| 40 | Ingestion Health Monitor [Internal] | Tổng quan | 116 | 2 |
| 28 | Logistics Operations Center [All] | Tổng quan | 93 | 2 |
| 26 | Order Listing [Retail] | Today | 62 | 2 |
| 31 | Sales Monthly Business Review [All] | Tong quan | 102 | 2 |

**Pattern:** Vi phạm chỉ xảy ra ở tab ĐẦU TIÊN (position=0) của dashboard. Các tab khác đều OK (row=0).
**Khả năng:** Có text/header card ở row=0/1 chiếm chỗ → widget "Chu kỳ báo cáo" bị đẩy xuống row=2.

## Dashboards MISSING widget

| Dashboard ID | Dashboard Name | Tabs MISSING | Ghi chú |
|---|---|---|---|
| 1 | E-commerce Insights | Portfolio Performance (id=2), Website Analysis (id=3) | Metabase sample dashboard — bỏ qua |
| 94 | Product Inventory Health [All] | All 3 tabs (239, 240, 241) | Dashboard mới, có thể cần bổ sung widget |

## Anomaly / Cleanup

- **Dashboard 32 — Shopee Channel Economics [Cross]**, tab "Settlement Overview" (id=106): có 2 cards:
  - `id=2052` "Chu kỳ báo cáo" row=0 (đúng vị trí)
  - `id=1968` "Chu ky bao cao" row=6, col=6 (DUPLICATE thừa, tên thiếu dấu) → nên xóa

## Dashboards PASS (đã kiểm tra, không vi phạm)

29 dashboards, 95+ tabs. Toàn bộ widget "Chu kỳ báo cáo" ở row=0 (FIRST).
Notable PASS pairs (so sánh "cũ [Cross]/[Retail]" vs "mới"):
- D82 Channel Profitability Monthly (new) ✓ vs D33 [Cross] ✗
- D83 Customer Intelligence Monthly (new) ✓ vs D15 [Cross] ✗
- D84 Customer Retention & Lifecycle (new) ✓ vs D14 [Retail] ✗
- D86 Finance P&L Dashboard (new) ✓ vs D34 [All] ✗
- D87 Ingestion Health Monitor (new) ✓ vs D40 [Internal] ✗
- D88 Logistics Operations Center (new) ✓ vs D28 [All] ✗
- D90 Order Listing (new) ✓ vs D26 [Retail] ✗
- D79 Sales Monthly Business Review (new) ✓ vs D31 [All] ✗

→ **8 dashboards "cũ" vi phạm đều có bản "mới" tương ứng đã sửa.** Có thể dashboards "cũ" này là legacy, sắp deprecate.

## Đề xuất

1. **Quick fix** 8 dashboards vi phạm: di chuyển widget "Chu kỳ báo cáo" lên row=0 ở tab đầu tiên, hoặc xác nhận đây là legacy sắp xóa.
2. **Cleanup D32**: xóa dashcard 1968 (duplicate "Chu ky bao cao" thiếu dấu).
3. **D94 Product Inventory Health**: bổ sung widget "Chu kỳ báo cáo" nếu là requirement chung; hoặc xác nhận đây là dashboard không cần widget này.
4. Bỏ qua D1 (E-commerce Insights) — Metabase sample.

## Unresolved questions

- 8 dashboards "cũ" có bản "mới" tương ứng — đã có kế hoạch deprecate chưa, hay vẫn dùng song song?
- Rule "row 0-1" có phải standard chính thức (documented somewhere) hay convention không viết?
- D94 Product Inventory Health có cần "Chu kỳ báo cáo" widget không?
