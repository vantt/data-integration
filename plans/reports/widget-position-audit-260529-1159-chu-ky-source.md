# Audit: Vị trí widget `cycle-indicator` & `source-freshness`

**Ngày audit:** 2026-05-29  
**Phạm vi:** 36 dashboards × tất cả tab  
**Logic detect:**
- `cycle-indicator`: `dashcard.card.name === "Chu kỳ báo cáo"` AND `card.display === "scalar"` — vi phạm nếu `row > 1`
- `source-freshness`: text card bắt đầu `Source:` hoặc `**Source:**` — vi phạm nếu `row < max_row` của tab

---

## Kết quả tổng quan

| Widget | Tab vi phạm | Dashboards bị ảnh hưởng |
|---|---|---|
| `cycle-indicator` | **0** | 0 |
| `source-freshness` | **23** | **17** |

`cycle-indicator` = clean: tất cả 36 dashboards đặt đúng row 0.

---

## source-freshness vi phạm

### Pattern A — Source ở đầu tab (row=0) [Nghiêm trọng]

Source widget xuất hiện ở top tab thay vì bottom. Có 2 source cards trong cùng tab (1 ở row=0, 1 ở row max).

| Dashboard | Tab | Source row | Max row |
|---|---|---|---|
| 44 · CEO Monthly Scorecard [All] | Sản phẩm & Vận hành | 0 | 23 |
| 46 · Promotion Analysis [Retail] | Discount ROI | 0 | 27 |
| 32 · Shopee Channel Economics [Cross] | Shopee P&L Cascade | 0 | 10 |
| 26 · Order Listing [Retail] | By Date | **0 + 36** | 99 |

> Dashboard 26 "By Date" có 3 source cards trong 1 tab: row=0, row=36, row=99.

### Pattern B — Hai source cards (old-format giữa tab + new-format row=99) [Cần dọn]

Old-format `Source: fact_... · Updated X...` chưa bị xóa khi deploy new-format `**Source:** ... · **Cadence:** ...`.

| Dashboard | Tab | Old source row | Max row |
|---|---|---|---|
| 15 · Customer Intelligence Monthly [Cross] | Behavior & Insights | 29 | 99 |
| 48 · Customer Operational [Retail] | Watchlist & Hành động | 33 | 99 |
| 14 · Customer Retention & Lifecycle [Retail] | Hành vi & Reactivation | 27 | 99 |
| 40 · Ingestion Health Monitor [Internal] | Failures & Detail | 20 | 99 |
| 28 · Logistics Operations Center [All] | Chi tiết & Nhân viên | 17 | 99 |
| 13 · Marketing Monthly Analysis [Retail] | Campaigns & Products | 33 | 99 |
| 13 · Marketing Monthly Analysis [Retail] | ROI & Margin | 17 | 99 |
| 47 · Marketing Weekly Tracker [Retail] | Promotion & Social | 24 | 99 |
| 26 · Order Listing [Retail] | Today | 37 | 99 |
| 26 · Order Listing [Retail] | Yesterday | 36 | 99 |
| 30 · Product Performance [Cross] | Sản phẩm bán chạy & bán chậm | 34 | 99 |
| 46 · Promotion Analysis [Retail] | Phân tích kênh & chi tiết | 24 | 99 |
| 31 · Sales Monthly Business Review [All] | Sức khỏe vận hành | 21 | 99 |
| 9 · Sales Ops Monthly Summary [Retail] | Đội ngũ & Thanh toán | 30 | 99 |
| 9 · Sales Ops Monthly Summary [Retail] | Margin | 13 | 99 |
| 8 · Sales Ops Weekly Review [Retail] | Đội ngũ & Thanh toán | 19 | 99 |
| 27 · Social Commerce Operations [Retail] | (main) | 34 | 99 |

### Pattern C — Single source không ở bottom [Cần fix]

Chỉ có 1 source card nhưng không phải widget cuối cùng — có widget khác bên dưới.

| Dashboard | Tab | Source row | Max row | Widget ở max row là gì? |
|---|---|---|---|---|
| 43 · CEO Weekly Pulse [All] | Khách hàng & Cảnh báo | 17 | 19 | cần kiểm tra |
| 31 · Sales Monthly Business Review [All] | P&L Hàng Tháng | 5 | 14 | cần kiểm tra |
| 32 · Shopee Channel Economics [Cross] | Shopee P&L Cascade | 0 | 10 | cần kiểm tra |

---

## Tóm tắt theo dashboard

| Dashboard | Pattern | Số tab |
|---|---|---|
| 26 · Order Listing [Retail] | A + B | 4 tab |
| 13 · Marketing Monthly Analysis [Retail] | B | 2 tab |
| 46 · Promotion Analysis [Retail] | A + B | 2 tab |
| 31 · Sales Monthly Business Review [All] | B + C | 2 tab |
| 9 · Sales Ops Monthly Summary [Retail] | B | 2 tab |
| 44 · CEO Monthly Scorecard [All] | A | 1 tab |
| 43 · CEO Weekly Pulse [All] | C | 1 tab |
| 15 · Customer Intelligence Monthly [Cross] | B | 1 tab |
| 48 · Customer Operational [Retail] | B | 1 tab |
| 14 · Customer Retention & Lifecycle [Retail] | B | 1 tab |
| 40 · Ingestion Health Monitor [Internal] | B | 1 tab |
| 28 · Logistics Operations Center [All] | B | 1 tab |
| 47 · Marketing Weekly Tracker [Retail] | B | 1 tab |
| 30 · Product Performance [Cross] | B | 1 tab |
| 75 · Return Impact Analysis [All] | B | 1 tab |
| 8 · Sales Ops Weekly Review [Retail] | B | 1 tab |
| 32 · Shopee Channel Economics [Cross] | A + C | 1 tab |
| 27 · Social Commerce Operations [Retail] | B | 1 tab |

---

## Câu hỏi chưa giải quyết

1. Pattern C: widget nào đang ở max_row của CEO Weekly Pulse "Khách hàng", Sales Monthly "P&L Hàng Tháng", Shopee "P&L Cascade"? Cần xem có phải widget data hay lỗi layout.
2. Pattern A (row=0): source bị đặt nhầm lên top do deploy lỗi hay do tab thiếu `cycle-indicator`?
3. Pattern B: có kế hoạch xóa hàng loạt old-format source hay fix từng dashboard?
