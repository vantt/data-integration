# Re-audit: "Chu kỳ báo cáo" widget position (post-fixes)

**Date:** 2026-05-29 10:20 ICT
**Scope:** All active multi-tab Metabase dashboards
**Source:** Metabase API (http://127.0.0.1:3001/) — live state
**Rule:** Widget "Chu kỳ báo cáo" PHẢI ở row 0 hoặc 1

## So sánh với audit lần trước (2026-05-28 23:09)

| Metric | 2026-05-28 23:09 | 2026-05-29 10:20 | Delta |
|---|---|---|---|
| Total active dashboards | 49 | 37 | -12 (xóa no-suffix) |
| Multi-tab dashboards | 37 | 29 | -8 |
| Tabs checked | ~115 | 90 | -25 |
| **Violations (row >= 2)** | **8** | **0** | **-8 ✓** |
| Missing widget tabs | 5 (D1×2, D94×3) | 2 (D1 only) | -3 ✓ |
| Cleanup artifacts | 1 (D32) | 1 (D51) | new finding |

## Kết quả 5 batches

| Batch | Dashboards | Tabs | Violations | Missing | Notes |
|---|---|---|---|---|---|
| A | 6 (D78, D49, D50, D44, D43, D77) | 19 | 0 | 0 | Clean |
| B | 6 (D33, D15, D48, D14, D41, D1) | 17 | 0 | 2 (D1 Tab 2,3) | D1 = Metabase sample |
| C | 6 (D34, D95, D40, D28, D13, D47) | 17 | 0 | 0 | Clean |
| D | 6 (D26, D94, D30, D46, D75, D31) | 22 | 0 | 0 | D31 thêm tab P&L Hang Thang, D94 widget mới đã có |
| E | 5 (D9, D8, D32, D51, D42) | 15 | 0 | 0 | D32 dup đã sạch; D51 phát hiện minor dup mới |
| **Total** | **29** | **90** | **0** | **2 (exempt)** | — |

## Trạng thái: ✅ PASS

- **Tất cả 29 multi-tab dashboards canonical compliance Rule "Chu kỳ báo cáo row 0-1"**
- D1 E-commerce Insights — Metabase sample, exempt (không có blueprint)
- 8 violations gốc đã fix hoàn toàn

## Verify từng dashboard từng có vi phạm

| Dashboard | Trước (23:09) | Sau (10:20) |
|---|---|---|
| D14 Customer Retention & Lifecycle [Retail] / Tab Suc khoe Retention | row=2 ❌ | row=0 ✓ |
| D15 Customer Intelligence Monthly [Cross] / Tab Overview & Health | row=2 ❌ | row=0 ✓ |
| D26 Order Listing [Retail] / Tab Today | row=2 ❌ | row=0 ✓ |
| D28 Logistics Operations Center [All] / Tab Tổng quan | row=2 ❌ | row=0 ✓ |
| D31 Sales Monthly Business Review [All] / Tab Tong quan | row=2 ❌ | row=0 ✓ |
| D33 Channel Profitability Monthly [Cross] / Tab Channel Overview | row=2 ❌ | row=0 ✓ |
| D34 Finance P&L [All] / Tab P&L Overview | row=2 ❌ | row=0 ✓ |
| D40 Ingestion Health Monitor [Internal] / Tab Tổng quan | row=2 ❌ | row=0 ✓ |

## Phát hiện mới — D51 US CrossBorder Daily [US]

Tab "Tuan nay" (id=182) và Tab "Thang nay" (id=183) mỗi tab có **2 cards "Chu kỳ báo cáo"** trùng tên:
- 1 card có suffix (Weekly/Monthly): `Chu kỳ báo cáo (Weekly)` hoặc `Chu kỳ báo cáo (Monthly)`
- 1 card không suffix: `Chu kỳ báo cáo`
- Cả 2 đều row=0 → không vi phạm Rule
- Nhưng là **duplicate artifact**, nên cleanup

## Đề xuất

1. **D51 cleanup**: kiểm tra blueprint `us_crossborder_operations.md` xem có declare cả 2 cards không (có thể intentional) hoặc legacy artifact cần xóa
2. **D1 E-commerce Insights**: bỏ qua (Metabase sample)

## Unresolved questions

- D51 — 2 "Chu kỳ báo cáo" trên Tab 2/3 là intentional design hay legacy duplicate?
