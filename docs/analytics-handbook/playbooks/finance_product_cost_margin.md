# Playbook: Product Cost-to-Margin Heatmap [Cross]

## Overview

- **Audience:** Merchandising Manager, Finance
- **Goal:** Trả lời "SKU nào margin tốt? SKU nào COGS variance cao bất thường?" — phân tích margin theo SKU, phát hiện COGS drift, hỗ trợ quyết định danh mục sản phẩm.
- **Metabase Collection:** `Finance` (id=92)
- **Blueprint:** [finance_product_cost_margin.md](../blueprints/finance_product_cost_margin.md)
- **Scope:** Cross-segment — tất cả kênh bán hàng. Loại trừ promo lines (`NOT is_promo_line`) để phản ánh kinh tế sản phẩm thực.
- **Mart Source:** `int_misa_sales_lines`

## Filters

- **Date Range:** Default = 30 ngày gần nhất (`past30days`). Đổi sang tháng/quý để xem xu hướng dài hơn.
- **Channel:** Optional filter theo `channel_name`. Để trống = hiển thị tất cả kênh (cross-segment).

## Visualizations

### Section 1: KPI Row — Tổng quan SKU & margin

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Total SKUs Sold** | Scalar | [SKU Gross Margin %](../domains/finance.md#m1-sku-gross-margin--biên-lợi-nhuận-gộp-theo-sku) | COUNT DISTINCT product_code. Loại trừ promo lines + zero-revenue lines |
| **Avg Margin %** | Scalar | [SKU Gross Margin %](../domains/finance.md#m1-sku-gross-margin--biên-lợi-nhuận-gộp-theo-sku) | Aggregate margin toàn bộ kỳ. Suffix % |
| **Margin Outlier Count** | Scalar | [Margin Outlier Flag](../domains/finance.md#m5-margin-outlier-flag-cờ-margin-bất-thường) | Số SKU margin < 10%. Alert nếu > 0 |
| **COGS Variance Alert Count** | Scalar | [COGS Variance vs 3-Month Avg](../domains/finance.md#m3-cogs-variance-vs-3-month-average-sai-lệch-giá-vốn-so-với-trung-bình-3-tháng) | Số SKU COGS/unit lệch > 10% vs avg 3M trước. Alert nếu > 0 |

### Section 2: Scatter — Revenue vs Margin

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
| :--- | :--- | :--- | :--- |
| **SKU Margin vs Revenue Scatter** | Scatter (bubble) | [SKU Revenue Share](../domains/finance.md#m4-sku-revenue-share-tỷ-trọng-doanh-thu-sku) | X=Revenue, Y=Margin %, bubble size=So don. Tối đa 200 SKU (by revenue). SKU high-revenue + low-margin = ưu tiên điều tra |

**Cách đọc scatter:**
- Góc trên phải (revenue cao, margin cao) = Star SKU — bảo vệ giá.
- Góc dưới phải (revenue cao, margin thấp) = Cash drain — cần rà soát ngay.
- Góc trên trái (revenue thấp, margin cao) = Niche gem — cân nhắc scale up.
- Góc dưới trái = Long tail — xem xét loại khỏi danh mục.

### Section 3: Top 50 SKU Detail Table

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Top 50 SKU Detail Table** | Table | [COGS Variance vs 3-Month Avg](../domains/finance.md#m3-cogs-variance-vs-3-month-average-sai-lệch-giá-vốn-so-với-trung-bình-3-tháng) | Cột: SKU, Doanh thu, Gia von, Margin %, COGS/don vi, COGS avg 3M, COGS variance %. Red highlight: Margin % < 10%; COGS variance > 10%. Green: Margin % >= 40%; COGS variance < -10% (cost giảm) |

### Section 4: Margin Distribution + COGS Variance Alert

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Margin Distribution Histogram** | Bar chart (bucket) | [SKU Gross Margin %](../domains/finance.md#m1-sku-gross-margin--biên-lợi-nhuận-gộp-theo-sku) | 8 buckets: < 0%, 0–10%, 10–20%, ... > 60%. Nhóm 0–10% highlight đỏ. Giúp thấy "shape" của margin portfolio |
| **COGS Variance Alert Table** | Table | [COGS Variance vs 3-Month Avg](../domains/finance.md#m3-cogs-variance-vs-3-month-average-sai-lệch-giá-vốn-so-với-trung-bình-3-tháng) | Chỉ SKU có \|variance\| > 10%. Sort by |variance| DESC. Red highlight variance > 10%, green < -10% |

### Section 5: SKU by Channel Drill

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
| :--- | :--- | :--- | :--- |
| **SKU Margin by Channel** | Grouped Bar | [SKU Gross Margin %](../domains/finance.md#m1-sku-gross-margin--biên-lợi-nhuận-gộp-theo-sku) | Top 20 SKU theo revenue × Margin % per channel. Phát hiện pricing inconsistency (cùng SKU nhưng margin khác nhau giữa kênh) |

## Business Logic Notes

- **Promo line exclusion:** `WHERE NOT is_promo_line` — loại trừ dòng khuyến mãi (giá 0 hoặc hàng tặng kèm). Nếu không loại, margin của SKU bình thường bị kéo xuống giả tạo.
- **COGS variance window:** Rolling 3 tháng trước tháng hiện tại (không tính tháng hiện tại trong baseline). Tháng hiện tại = `posting_date >= date_trunc('month', current_date)`.
- **COGS per unit grain:** `SUM(cogs_amount) / SUM(quantity)` — đây là weighted average COGS per unit. Cần `quantity > 0` guard.
- **date filter áp dụng trên:** `posting_date` (ngày hạch toán MISA), không phải `invoice_date` hay `voucher_date`. Nhất quán với các dashboard MISA khác.
- **Channel filter scope:** Áp dụng trực tiếp trên `int_misa_sales_lines.channel_name`. KPI row và COGS variance alert **không** áp dụng date_range filter động — hardcode tháng hiện tại để đảm bảo tính nhất quán alert.

## Alert Thresholds

| Metric | Healthy | Watch | Alert |
| :--- | :--- | :--- | :--- |
| SKU Gross Margin % | > 40% | 20–40% | < 10% (outlier flag) |
| COGS Variance % vs 3M | ±5% | ±5–10% | > ±10% (investigate) |
| Margin Outlier Count | 0 | 1–5 SKU | > 5 SKU cùng lúc |

## Recommended Workflow (Merchandising Manager)

1. Kiểm tra **KPI row** mỗi sáng — Margin Outlier Count > 0 hoặc COGS Variance Alert Count > 0 là cần action.
2. Dùng **Scatter** để phân loại SKU portfolio — focus vào Cash drain quadrant (high revenue, low margin).
3. Mở **Top 50 Table** — sort theo "COGS variance %" để thấy SKU nào đang có cost spike.
4. Xem **COGS Variance Alert Table** — contact procurement nếu variance > 20% (có thể là lỗi nhập liệu MISA hoặc thay đổi nhà cung cấp).
5. Dùng **Channel Breakdown** để confirm SKU có margin thấp trên kênh nào cụ thể — có thể do discount policy khác nhau theo kênh.

## Related Dashboards

| Dashboard | Link | Relationship |
| :--- | :--- | :--- |
| Product Profitability | [Playbook](./product_performance.md) | SKU top/bottom ranking — Executive collection |
| Cost Ledger Analyzer | [Playbook](./finance_cost_ledger.md) | COGS aggregate theo order/channel |
| Channel P&L Deep Dive | [Phase 05](../../../plans/260527-1327-metabase-collection-restructure/phase-05-new-finance-dashboards.md) | Margin waterfall per channel |
