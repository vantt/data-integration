# Audit: Cycle-Indicator & Source-Freshness — All Dashboards
**Ngày:** 2026-05-29 | **Phạm vi:** Toàn bộ dashboard

---

## Tổng Quan

| Loại vấn đề | Số tab bị ảnh hưởng |
|---|---|
| MISSING `Source & Freshness` | 6 |
| MISSING `Chu kỳ báo cáo` | 2 |
| **Tổng** | **8** |

---

## MISSING — Source & Freshness

Tab thiếu text card "Source & Freshness" (widget_row = -1 → không tồn tại).

| Dashboard | Dashboard ID | Tab | widget_row | max_row |
|---|---|---|---|---|
| Finance Services Revenue [All] | 95 | Tổng Quan | -1 | 99 |
| Finance Services Revenue [All] | 95 | US HR Services | -1 | 99 |
| Finance Services Revenue [All] | 95 | Kiểm Tra Dịch Vụ Khác | -1 | 99 |
| Product Inventory Health [All] | 94 | Current Stock | -1 | 12 |
| Product Inventory Health [All] | 94 | Slow-Mover & Dead Stock | -1 | 14 |
| Product Inventory Health [All] | 94 | Inventory Trend | -1 | 15 |

---

## MISSING — Chu kỳ báo cáo

Tab thiếu SQL scalar "Chu kỳ báo cáo" (widget_row = -1 → không tồn tại).

| Dashboard | Dashboard ID | Tab | widget_row | max_row |
|---|---|---|---|---|
| US CrossBorder Daily [US] | 51 | Tuan nay | -1 | 99 |
| US CrossBorder Daily [US] | 51 | Thang nay | -1 | 99 |

---

## Hành Động Cần Thực Hiện

- **Finance Services Revenue [All] (ID 95):** Thêm text card "Source & Freshness" vào 3 tab.
- **Product Inventory Health [All] (ID 94):** Thêm text card "Source & Freshness" vào 3 tab.
- **US CrossBorder Daily [US] (ID 51):** Thêm SQL scalar "Chu kỳ báo cáo" vào 2 tab.
