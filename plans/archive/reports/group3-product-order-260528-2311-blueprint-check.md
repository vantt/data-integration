# Blueprint Consistency Check — Product + Order + Logistics Group
Generated: 2026-05-28 23:11

## Summary
- Checked: 7 dashboards
- MATCH: 4 (Order Profitability, Order Listing, Product Performance, Logistics Operations)
- MINOR_DIFF: 1 (Product Profitability)
- MAJOR_DIFF: 2 (Order Detail, Product Inventory Health)

---

## Dashboard Details

### Order Profitability [All] (id: 35) — MATCH

**Blueprint tabs**: none (single-page)
**Metabase tabs**: none

**Blueprint questions** (10): Chu kỳ báo cáo, Avg Gross Margin %, Total Gross Profit, Total Channel Net Profit, Orders with COGS, Channel Net Margin %, Cost Structure by Channel, Margin Distribution, Profit by Date, Order P&L Table
**Metabase questions** (10): Chu kỳ báo cáo, Avg Gross Margin %, Total Gross Profit, Total Channel Net Profit, Orders with COGS, Channel Net Margin %, Cost Structure by Channel, Margin Distribution, Profit by Date, Order P&L Table

**Missing from Metabase**: none
**Extra in Metabase**: none
**Text cards**: Blueprint 4 / Metabase 6

> Note: Metabase has 2 extra text cards vs blueprint (likely source/freshness footer + extra section heading). Not a functional issue.

---

### Order Detail [Retail] (id: 38) — MAJOR_DIFF

**Blueprint tabs**: none (single-page)
**Metabase tabs**: none

**Blueprint questions** (6): Chu kỳ báo cáo, Order Header, Order Economics, Line Items, Payments
**Metabase questions** (1): Chu kỳ báo cáo

**Missing from Metabase**: Order Header, Order Economics, Line Items, Payments
**Extra in Metabase**: none
**Text cards**: Blueprint 5 / Metabase 5

> Critical: 5 of 6 blueprint questions missing. Only the "Chu kỳ báo cáo" scalar is present. The dashboard appears to have been created with structure (text cards in place) but the 4 core question cards (Order Header, Order Economics, Line Items, Payments) were never deployed or were removed.

---

### Order Listing [Retail] (id: 26) — MATCH

**Blueprint tabs**: Today, Yesterday, By Date
**Metabase tabs**: Today, Yesterday, By Date

**Blueprint questions per tab** (12 per tab = 36 total unique instances across 3 tabs):
- Each tab: Chu kỳ báo cáo, Data Freshness, Total Orders, Net Revenue, Total Collected, Gross Revenue, Total Discount, Cancelled Orders, Returns, Orders by Status, Orders by Payment Status, Orders by Channel, Flagged Orders, Order Detail List
  - (Tab "Today": 14 questions; "Yesterday": 14; "By Date": uses filter + 14 pattern)

**Metabase questions** (42 instances across 3 tabs — includes duplicates as expected for tabbed layout):
- Chu kỳ báo cáo ×3, Data Freshness ×3, Total Orders ×3, Net Revenue ×3, Total Collected ×3, Gross Revenue ×3, Total Discount ×3, Cancelled Orders ×3, Returns ×3, Orders by Status ×3, Orders by Payment Status ×3, Orders by Channel ×3, Flagged Orders ×3, Order Detail List ×3

**Missing from Metabase**: none
**Extra in Metabase**: none
**Text cards**: Blueprint ~18 (6 per tab) / Metabase 21

> Tabs match exactly. Question names match across all 3 tabs. Minor: Metabase has 21 text cards vs ~18 in blueprint (1-2 extra text cards likely source/freshness footers per tab).

---

### Product Performance [Cross] (id: 30) — MATCH

**Blueprint tabs**: Tong quan, Phan tich loai san pham, San pham ban chay & ban cham, Loi nhuan
**Metabase tabs**: Tong quan, Phan tich loai san pham, San pham ban chay & ban cham, Loi nhuan

**Blueprint questions** (22 unique across 4 tabs):
- Tong quan: Chu kỳ báo cáo, Doanh thu san pham, So luong ban, So san pham ban duoc, Doanh thu trung binh/san pham, Doanh thu san pham theo ngay, So luong ban theo ngay, Doanh thu theo loai san pham, Ty trong doanh thu theo loai san pham
- Phan tich loai san pham: Chu kỳ báo cáo, Tang truong doanh thu theo loai SP, Category Mix Trend, Bang hieu suat loai san pham
- San pham ban chay & ban cham: Chu kỳ báo cáo, Top 20 SP theo doanh thu, Top 20 SP theo so luong, Top 10 SP tang truong MoM, Top 10 SP sut giam MoM, Top 20 SP theo daily velocity, Bang chi tiet san pham
- Loi nhuan: Chu kỳ báo cáo, Gross Margin %, Top 20 san pham theo loi nhuan, Margin by Channel, San pham margin thap, Product Category Profitability Heatmap

**Metabase questions** (26 instances): All blueprint questions present including Chu kỳ báo cáo ×4 (one per tab), plus Product Category Profitability Heatmap

**Missing from Metabase**: none
**Extra in Metabase**: none (count inflation is from shared "Chu kỳ báo cáo" per tab as expected)
**Text cards**: Blueprint ~18 / Metabase 18

> Full match. All 4 tabs and all question names align.

---

### Product Profitability [All] (id: 36) — MINOR_DIFF

**Blueprint tabs**: none (single-page)
**Metabase tabs**: none

**Blueprint questions** (8): Chu kỳ báo cáo, Total Products, Avg Margin %, Highest Margin Product, Lowest Margin Product, Top Products by Profit, Bottom Margin Products, Product Detail Table
**Metabase questions** (8): Chu kỳ báo cáo, Total Products, Avg Margin %, Highest Margin Product, Lowest Margin Product, Top Products by Profit, Bottom Margin Products, Product Detail Table

**Missing from Metabase**: none
**Extra in Metabase**: none
**Text cards**: Blueprint 3 / Metabase 4

> All 8 questions present. Metabase has 1 extra text card vs blueprint (likely source/freshness footer). MINOR_DIFF due to text card count.

---

### Product Inventory Health [All] (id: 94) — MAJOR_DIFF

**Blueprint tabs**: Current Stock, Slow-Mover & Dead Stock, Inventory Trend
**Metabase tabs**: Current Stock, Slow-Mover & Dead Stock, Inventory Trend

**Blueprint questions** (19): OOS SKUs, Low Stock SKUs, Tổng Giá Trị Tồn Kho, Tổng SKU Có Hàng, Giá Trị Tồn Kho Theo Location, Top 20 SKU Theo Giá Trị Tồn Kho, Danh Sách SKU OOS, Slow-Mover Value At Risk, Dead Stock Value At Risk, Slow-Mover SKU Count, Dead Stock SKU Count, Danh Sách Slow-Mover Chi Tiết, Slow-Mover Value Theo Category, Committed Value At Risk, Stock Value Trend 90 Ngày, OOS Rate Trend 90 Ngày, Stock Value Trend Theo Location 30 Ngày, Slow-Mover Value Trend 90 Ngày, Monthly Stock Value Summary
**Metabase questions** (19): all matching

**Missing from Metabase**: none
**Extra in Metabase**: none
**Text cards**: Blueprint 3 / Metabase 3

> All questions and tabs match. However: MAJOR_DIFF classification because the blueprint uses `size_x: 24` (24-column grid) while Metabase standard is 18-column. This is a structural grid mismatch that will cause layout problems if deployed via standard deploy script. The blueprint may have been designed for a different grid width.

> Correction: On re-review, all questions and tabs match 1:1. Downgrade to MATCH pending layout verification. Flagging for layout grid review only.

**Re-classified: MATCH** (questions/tabs align perfectly; 24-col grid difference is a layout concern, not a card/question inconsistency)

---

### Logistics Operations Center [All] (id: 28) — MATCH

**Blueprint tabs**: Tổng quan, Tốc độ xử lý, Chi tiết & Nhân viên
**Metabase tabs**: Tổng quan, Tốc độ xử lý, Chi tiết & Nhân viên

**Blueprint questions** (18 unique across 3 tabs):
- Tổng quan: Chu kỳ báo cáo, Fulfillment Rate, Tổng đơn hôm nay, Đơn đã xuất kho, Thời gian hoàn thành TB, Phễu trạng thái đơn, Fulfillment Status Breakdown, Đơn hàng theo giờ (DoD), Đơn hàng lũy kế (DoD)
- Tốc độ xử lý: Chu kỳ báo cáo, TB giờ đến xuất kho, Tỷ lệ xuất cùng ngày, Đơn chờ > 24h, Đơn hoàn thành hôm nay, TB giờ xử lý theo giờ (DoD), Heatmap xuất kho, Chi tiết đơn kẹt
- Chi tiết & Nhân viên: Chu kỳ báo cáo, NV — Số đơn xử lý, NV — TB giờ xử lý, Bảng chi tiết đơn hàng

**Metabase questions** (21 instances — 18 unique + Chu kỳ báo cáo ×3): all match blueprint
**Missing from Metabase**: none
**Extra in Metabase**: none
**Text cards**: Blueprint 12 / Metabase 12

> Full match. All 3 tabs and all question names present.

---

## Revised Summary

| Dashboard | ID | Status | Questions (BP/MB) | Text Cards (BP/MB) | Notes |
|---|---|---|---|---|---|
| Order Profitability [All] | 35 | MATCH | 10/10 | 4/6 | 2 extra text cards |
| Order Detail [Retail] | 38 | MAJOR_DIFF | 6/1 | 5/5 | 5 questions missing |
| Order Listing [Retail] | 26 | MATCH | 42/42 | ~18/21 | 3 tabs, all aligned |
| Product Performance [Cross] | 30 | MATCH | 26/26 | ~18/18 | 4 tabs, all aligned |
| Product Profitability [All] | 36 | MINOR_DIFF | 8/8 | 3/4 | 1 extra text card |
| Product Inventory Health [All] | 94 | MATCH | 19/19 | 3/3 | 3 tabs, all aligned; grid width 24 vs 18 — layout review needed |
| Logistics Operations Center [All] | 28 | MATCH | 18/21 | 12/12 | 3 tabs, Chu kỳ ×3 expected |

- **MATCH**: 5
- **MINOR_DIFF**: 1 (Product Profitability — 1 extra text card only)
- **MAJOR_DIFF**: 1 (Order Detail — 5 of 6 questions missing)

## Action Items

1. **Order Detail [Retail] (id: 38)** — Deploy missing 4 questions: Order Header, Order Economics, Line Items, Payments. Blueprint: `docs/analytics-handbook/blueprints/order_detail.md`.
2. **Product Inventory Health [All] (id: 94)** — Review layout: blueprint uses 24-column grid (`size_x: 24`) while standard Metabase layout is 18-column. May display incorrectly. Verify in browser.
3. **Order Profitability [All] (id: 35)** — Optional: reconcile 2 extra text cards in Metabase vs blueprint.
4. **Product Profitability [All] (id: 36)** — Optional: reconcile 1 extra text card in Metabase vs blueprint.
