# Finance Domain

> **Domain Document định nghĩa cách một nhóm nghiệp vụ được hiểu và đo lường trong hệ thống analytics.**
> Tài liệu này xác định phạm vi domain, các câu hỏi phân tích nền tảng, các metric liên quan, cùng định nghĩa nghiệp vụ và logic tính toán chuẩn cho từng metric.
> Đây là nguồn tham chiếu chính thức cho business logic; dashboard, playbook, design spec và blueprint phải tham chiếu lại tài liệu này thay vì tự định nghĩa lại metric.

> **Owner:** CFO / Finance Team
> **Update Frequency:** Daily / Monthly

## Context: Channel Budget Targets — dim_channel_targets

> **Description:** Channel-level budget/plan targets. Manually maintained CSV seed until a formal budget process exists. One row per (channel_name, period_month, metric_type, target_source).
> **dbt Seed:** [`dim_channel_targets`](../../../transformation/seeds/dim_channel_targets.csv)
> **dbt Model:** [`dim_channel_targets`](../../../transformation/models/marts/core/dim_channel_targets.sql)
> **Grain:** (channel_key, period_month, metric_type, target_source)
> **Refresh:** `dbt seed --select dim_channel_targets && dbt build --select dim_channel_targets`

| metric_type | Unit | Description |
|-------------|------|-------------|
| `NET_REVENUE` | VND | Monthly net revenue target per channel |
| `NET_MARGIN_PCT` | % | Net margin % target per channel (used in CPL5 scorecard + CPL trend overlay) |
| `ORDER_COUNT` | count | Order volume target per channel |

**Blueprints using this dim:** `finance_channel_pl` (CPL5 Scorecard → Target % + Variance pp; Variance Analysis → Budget overlay on trend line)

---

## Context: Profit & Loss (P&L) — Sapo Revenue

> **Description:** Revenue-side P&L metrics from Sapo order data. COGS/expense metrics require MISA context below.
> **dbt Source:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)
> **Grain:** Per Order / Monthly

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Profit & Loss (P&L) — Sapo Revenue | How do revenue, COGS, and profit combine into P&L performance? | 1. Gross Revenue (GMV), 2. Net Revenue, 3. Revenue Breakdown (Waterfall Components) | [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) | None documented |

### Analytical Questions

#### Q1. Profit & Loss (P&L) — Sapo Revenue Readiness

- **Question:** How do revenue, COGS, and profit combine into P&L performance?
- **Definition:** This question defines whether `Profit & Loss (P&L) — Sapo Revenue` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** finance, lagging/value.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 1. Gross Revenue (GMV), 2. Net Revenue, 3. Revenue Breakdown (Waterfall Components)

### Metrics

#### 1. Gross Revenue (GMV)

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Tổng giá trị hàng hóa theo giá bán, trước chiết khấu. **Sapo giá bán đã gồm VAT** — gross_revenue = total_amount + discount_amount (VAT vẫn nhúng bên trong). Xem [Revenue Terminology](../guides/revenue_terminology.md).
- **Logic (SQL):**
  ```sql
  SUM(gross_revenue)
  ```
- **Source Mapping:**
  - **Table:** `fact_orders`
  - **Field:** `gross_revenue` (Sum)

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 2. Net Revenue

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Doanh thu thuần — sau chiết khấu, **đã trừ VAT** (= total_amount − total_tax_amount). VAT nhúng trong giá bán Sapo, không phải cộng thêm bên ngoài. Xem [Revenue Terminology](../guides/revenue_terminology.md).
- **Logic (SQL):**
  ```sql
  SUM(net_revenue)
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 3. Revenue Breakdown (Waterfall Components)

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Components of revenue flow for waterfall chart.
- **Logic (SQL):**
  ```sql
  SELECT 'Gross Revenue' AS component, SUM(gross_revenue) AS amount FROM fact_orders WHERE status NOT IN ('CANCELLED','Voided')
  UNION ALL SELECT 'Discounts', -SUM(discount_amount) FROM fact_orders WHERE status NOT IN ('CANCELLED','Voided')
  UNION ALL SELECT 'Tax', SUM(tax_amount) FROM fact_orders WHERE status NOT IN ('CANCELLED','Voided')
  UNION ALL SELECT 'Net Revenue', SUM(net_revenue) FROM fact_orders WHERE status NOT IN ('CANCELLED','Voided')
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: COGS & Margin — MISA Sales Ledger

> **Description:** Cost of Goods Sold and gross margin from MISA AMIS accounting system. Per-invoice-line grain with product-level COGS. Covers all channels (DAILY, ECOM, CS, KHAC).
> **dbt Source:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)
> **Grain:** Per Invoice Line
> **Channel Classification:** `channel_code` (DAILY=Bán lẻ tại quầy, ECOM=Thương mại điện tử, CS=Công sở/B2B, KHAC=Khác) + `voucher_source_hint` (SAPO_DEALER, SHOPEE, AEON, OTHER)

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| COGS & Margin — MISA Sales Ledger | How are COGS and margin changing by product or channel? | 4. COGS (Giá vốn hàng bán), 5. Gross Profit (Lãi gộp), 6. Gross Margin % (Biên lợi nhuận gộp), 7. Gross Margin by Channel, 8. COGS Ratio (Tỷ lệ giá vốn/doanh thu) | [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql) | None documented |

### Analytical Questions

#### Q1. COGS & Margin — MISA Sales Ledger Readiness

- **Question:** How are COGS and margin changing by product or channel?
- **Definition:** This question defines whether `COGS & Margin — MISA Sales Ledger` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** finance, margin quality.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 4. COGS (Giá vốn hàng bán), 5. Gross Profit (Lãi gộp), 6. Gross Margin % (Biên lợi nhuận gộp), 7. Gross Margin by Channel, 8. COGS Ratio (Tỷ lệ giá vốn/doanh thu)

### Metrics

#### 4. COGS (Giá vốn hàng bán)

> **dbt Model:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)

- **Business Definition:** Giá vốn hàng bán — chi phí mua hàng tương ứng với doanh thu đã ghi nhận. Lấy từ sổ chi tiết bán hàng MISA.
- **Logic (SQL):**
  ```sql
  SUM(cogs_amount)
  ```
- **Source Mapping:**
  - **Table:** `int_misa_sales_lines`
  - **Field:** `cogs_amount` (Sum)

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 5. Gross Profit (Lãi gộp)

> **dbt Model:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)

- **Business Definition:** Doanh thu thuần trừ giá vốn. Cho biết lợi nhuận trước chi phí vận hành.
- **Logic (SQL):**
  ```sql
  SUM(gross_profit)
  -- equivalent: SUM(revenue_net_of_discount) - SUM(cogs_amount)
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 6. Gross Margin % (Biên lợi nhuận gộp)

> **dbt Model:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)

- **Business Definition:** Phần trăm doanh thu còn lại sau giá vốn. Đo lường hiệu quả chiến lược giá.
- **Logic (SQL):**
  ```sql
  SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0) AS gross_margin_pct
  ```
- **Threshold:**
  - Healthy: > 40%
  - Watch: 25-40%
  - Alert: < 25%

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 7. Gross Margin by Channel

> **dbt Model:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)

- **Business Definition:** Biên lợi nhuận gộp theo kênh bán hàng — so sánh hiệu quả giữa các kênh.
- **Logic (SQL):**
  ```sql
  SELECT
      channel_name,
      SUM(revenue_net_of_discount) AS revenue,
      SUM(cogs_amount) AS cogs,
      SUM(gross_profit) AS gross_profit,
      SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0) AS gross_margin_pct
  FROM int_misa_sales_lines
  WHERE NOT is_promo_line
  GROUP BY channel_name
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 8. COGS Ratio (Tỷ lệ giá vốn/doanh thu)

> **dbt Model:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)

- **Business Definition:** Phần trăm doanh thu bị giá vốn chiếm — nghịch đảo của Gross Margin.
- **Logic (SQL):**
  ```sql
  SUM(cogs_amount) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0) AS cogs_ratio
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Order-Level Profitability

> **Description:** Per-order P&L combining Sapo revenue, MISA COGS, and Shopee platform fees. Enables profitability analysis by channel, customer, staff, geography.
> **dbt Source:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)
> **Grain:** Per Order
> **Join Keys:** `voucher_no` (MISA) = `order_code` (Sapo) = `order_code` (Shopee fees)
> **Coverage:** ~65% of completed orders in MISA date range (cancelled/draft orders excluded from MISA)

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Order-Level Profitability | How much profit remains per order or channel after direct costs? | 9. Order Gross Profit (Lãi gộp đơn hàng), 10. Channel Net Profit (Lãi ròng kênh), 11. Operating Margin %, 12. Net Margin %, 13. EBITDA | [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql) | None documented |

### Analytical Questions

#### Q1. Order-Level Profitability Readiness

- **Question:** How much profit remains per order or channel after direct costs?
- **Definition:** This question defines whether `Order-Level Profitability` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** profitability, unit economics.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 9. Order Gross Profit (Lãi gộp đơn hàng), 10. Channel Net Profit (Lãi ròng kênh), 11. Operating Margin %, 12. Net Margin %, 13. EBITDA

### Metrics

#### 9. Order Gross Profit (Lãi gộp đơn hàng)

> **dbt Model:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)

- **Business Definition:** Lãi gộp = Doanh thu thuần - Giá vốn. Tính per-order, join MISA COGS vào Sapo revenue.
- **Logic (SQL):**
  ```sql
  SELECT order_code, net_revenue, cogs_amount, gross_profit, gross_margin_pct
  FROM fact_order_economics
  WHERE has_cogs  -- chỉ đơn có dữ liệu COGS từ MISA
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 10. Channel Net Profit (Lãi ròng kênh)

> **dbt Model:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)

- **Business Definition:** Lãi ròng kênh = Gross Profit - Phí sàn (Shopee). Cho kênh non-Shopee thì = Gross Profit.
- **Logic (SQL):**
  ```sql
  SELECT
      c.channel_name,
      COUNT(*) AS orders,
      SUM(e.net_revenue) AS revenue,
      SUM(e.cogs_amount) AS cogs,
      SUM(e.gross_profit) AS gross_profit,
      SUM(e.channel_net_profit) AS channel_net_profit,
      ROUND(SUM(e.channel_net_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1) AS channel_net_margin_pct
  FROM fact_order_economics e
  JOIN dim_channels c USING (channel_key)
  WHERE e.has_cogs AND e.status = 'COMPLETED'
  GROUP BY 1
  ```
- **Note:** `channel_net_profit` includes Shopee fees (service, payment, fixed, infra, voucher Xtra, taxes) for Shopee orders. Non-Shopee orders: channel_net_profit = gross_profit.

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### P&L Metrics — Planned (requires `fact_gl_entries`)

> **Status: Planned** — Metrics below require General Ledger integration. Operating expenses, depreciation, interest are not yet available.

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** Planned / defined by the source model when implemented.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 11. Operating Margin %

- **Business Definition:** Operating Income (EBIT) as a percentage of Revenue. Requires GL OpEx data.
- **Status:** Planned — `fact_gl_entries` not yet built.

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** Planned / defined by the source model when implemented.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 12. Net Margin %

- **Business Definition:** Net Income as a percentage of Revenue. Requires full GL.
- **Status:** Planned — `fact_gl_entries` not yet built.

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** Planned / defined by the source model when implemented.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 13. EBITDA

- **Business Definition:** Earnings Before Interest, Taxes, Depreciation, and Amortization. Requires full GL.
- **Status:** Planned — `fact_gl_entries` not yet built.

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** Planned / defined by the source model when implemented.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Shopee Platform Economics

> **Description:** Shopee channel fee structure, net settlement, and platform margin. Dùng để phân tích chi phí bán hàng trên Shopee và tối ưu lợi nhuận kênh.
> **dbt Source:** [`int_shopee_order_fees`](../../../transformation/models/intermediate/shopee/int_shopee_order_fees.sql)
> **Grain:** Per Shopee Order
> **Note:** Only covers orders with released payouts (payout_released_at IS NOT NULL).

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Shopee Platform Economics | How do Shopee fees and settlements affect channel margin? | 12. Shopee Net Settlement (Tổng phát hành), 13. Shopee Platform Fee Rate (Tỷ lệ phí sàn), 14. Shopee Fee Breakdown, 15. Shopee Settlement Margin (Biên lợi nhuận sàn) | [`int_shopee_order_fees`](../../../transformation/models/intermediate/shopee/int_shopee_order_fees.sql) | None documented |

### Analytical Questions

#### Q1. Shopee Platform Economics Readiness

- **Question:** How do Shopee fees and settlements affect channel margin?
- **Definition:** This question defines whether `Shopee Platform Economics` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** marketplace economics, reconciliation/value.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 12. Shopee Net Settlement (Tổng phát hành), 13. Shopee Platform Fee Rate (Tỷ lệ phí sàn), 14. Shopee Fee Breakdown, 15. Shopee Settlement Margin (Biên lợi nhuận sàn)

### Metrics

#### 12. Shopee Net Settlement (Tổng phát hành)

> **dbt Model:** [`int_shopee_order_fees`](../../../transformation/models/intermediate/shopee/int_shopee_order_fees.sql)

- **Business Definition:** Số tiền Shopee thực chuyển về seller sau khi trừ toàn bộ phí, thuế, hoàn hàng. Khớp với cột "Tổng phát hành" trên Shopee Seller Center.
- **Logic (SQL):**
  ```sql
  SUM(net_settlement)
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 13. Shopee Platform Fee Rate (Tỷ lệ phí sàn)

> **dbt Model:** [`int_shopee_order_fees`](../../../transformation/models/intermediate/shopee/int_shopee_order_fees.sql)

- **Business Definition:** Tổng phí sàn Shopee trên doanh thu — bao gồm service fee, payment fee, fixed fee, infrastructure fee, voucher Xtra.
- **Logic (SQL):**
  ```sql
  (SUM(ABS(service_fee)) + SUM(ABS(payment_fee)) + SUM(ABS(fixed_fee))
   + SUM(infrastructure_fee) + SUM(voucher_xtra_fee))
  * 100.0 / NULLIF(SUM(gross_revenue), 0) AS platform_fee_rate_pct
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 14. Shopee Fee Breakdown

> **dbt Model:** [`int_shopee_order_fees`](../../../transformation/models/intermediate/shopee/int_shopee_order_fees.sql)

- **Business Definition:** Chi tiết từng loại phí Shopee để xác định khoản nào chiếm tỷ trọng lớn nhất.
- **Components:**
  - `service_fee` — Phí dịch vụ (% doanh thu)
  - `payment_fee` — Phí thanh toán
  - `fixed_fee` — Phí cố định
  - `infrastructure_fee` — Phí hạ tầng (từ Service Fee Details)
  - `voucher_xtra_fee` — Phí voucher Xtra (từ Service Fee Details)
  - `vat_tax` — Thuế VAT trên phí
  - `personal_income_tax` — Thuế TNCN
- **Logic (SQL):**
  ```sql
  SELECT
      'Service Fee' AS fee_type, SUM(ABS(service_fee)) AS amount FROM int_shopee_order_fees
  UNION ALL SELECT 'Payment Fee', SUM(ABS(payment_fee)) FROM int_shopee_order_fees
  UNION ALL SELECT 'Fixed Fee', SUM(ABS(fixed_fee)) FROM int_shopee_order_fees
  UNION ALL SELECT 'Infrastructure Fee', SUM(infrastructure_fee) FROM int_shopee_order_fees
  UNION ALL SELECT 'Voucher Xtra Fee', SUM(voucher_xtra_fee) FROM int_shopee_order_fees
  UNION ALL SELECT 'VAT Tax', SUM(ABS(vat_tax)) FROM int_shopee_order_fees
  UNION ALL SELECT 'Personal Income Tax', SUM(ABS(personal_income_tax)) FROM int_shopee_order_fees
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 15. Shopee Settlement Margin (Biên lợi nhuận sàn)

> **dbt Model:** [`int_shopee_order_fees`](../../../transformation/models/intermediate/shopee/int_shopee_order_fees.sql)

- **Business Definition:** Tỷ lệ tiền thực nhận so với doanh thu gộp — đo lường "mất mát" khi bán trên Shopee.
- **Logic (SQL):**
  ```sql
  SUM(net_settlement) * 100.0 / NULLIF(SUM(gross_revenue), 0) AS settlement_margin_pct
  ```
- **Threshold:**
  - Healthy: > 75% (giữ lại ≥75% doanh thu)
  - Watch: 60-75%
  - Alert: < 60%

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Balance Sheet & Liquidity — Planned

> **Status: Planned** — Requires `fact_account_balances` (not yet built).
> **Description:** Health of the business and cash position.
> **dbt Source:** `fact_account_balances`

> **Grain:** See metric-level grain notes

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Balance Sheet & Liquidity — Planned | Is liquidity and collection risk within an acceptable range? | 16. Current Ratio, 17. Quick Ratio, 18. Days Sales Outstanding (DSO) | `fact_account_balances` | Source/model implementation required for planned metrics |

### Analytical Questions

#### Q1. Balance Sheet & Liquidity — Planned Readiness

- **Question:** Is liquidity and collection risk within an acceptable range?
- **Definition:** This question defines whether `Balance Sheet & Liquidity — Planned` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** liquidity, strategic risk.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 16. Current Ratio, 17. Quick Ratio, 18. Days Sales Outstanding (DSO)

### Metrics

#### 16. Current Ratio

- **Business Definition:** Ability to pay short-term obligations (Assets / Liabilities).
- **Status:** Planned — `fact_account_balances` not yet built.

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** Planned / defined by the source model when implemented.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 17. Quick Ratio

- **Business Definition:** Measure of immediate liquidity.
- **Status:** Planned — `fact_account_balances` not yet built.

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** Planned / defined by the source model when implemented.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 18. Days Sales Outstanding (DSO)

- **Business Definition:** Average number of days to collect payment after a sale.
- **Logic (SQL):**
  ```sql
  (Accounts_Receivable / Annual_Revenue) * 365
  ```
- **Status:** Planned — `fact_account_balances` not yet built.

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** hours/days
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Cash Flow

> **Description:** Cash movement tracking.
> **dbt Source:** [`fact_payments`](../../../transformation/models/marts/sales/fact_payments.sql)

> **Grain:** See metric-level grain notes

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Cash Flow | Is actual cash movement positive or negative by period? | 19. Net Cash Flow | [`fact_payments`](../../../transformation/models/marts/sales/fact_payments.sql) | None documented |

### Analytical Questions

#### Q1. Cash Flow Readiness

- **Question:** Is actual cash movement positive or negative by period?
- **Definition:** This question defines whether `Cash Flow` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** cash flow, lagging/value.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 19. Net Cash Flow

### Metrics

#### 19. Net Cash Flow

- **Business Definition:** Difference between Cash Inflow and Cash Outflow.
- **Logic (SQL):**
  ```sql
  SELECT
      DATE(payment_date),
      SUM(CASE WHEN type = 'inflow' THEN amount ELSE 0 END) AS cash_in,
      SUM(CASE WHEN type = 'outflow' THEN amount ELSE 0 END) AS cash_out,
      (SUM(CASE WHEN type = 'inflow' THEN amount ELSE 0 END) -
       SUM(CASE WHEN type = 'outflow' THEN amount ELSE 0 END)) AS net_movement
  FROM fact_payments
  GROUP BY 1
  ```

<!-- ============================================================ -->
<!-- COST_LEDGER_SECTION_START — owned by Phase 05 Cost Ledger agent -->

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Cost Ledger — Per-Order Costs

> **Description:** Long-format cost ledger — 1 row per (order_id, cost_type). Covers COGS (from MISA), Shopee platform fees, taxes, shipping, and seller discounts (from Sapo). Amounts are always positive (ABS); sign/direction is derived from cost_category. Enables breakdown of "where does money go?" by channel and cost type.
> **dbt Source:** [`fact_order_costs`](../../../transformation/models/marts/sales/fact_order_costs.sql)
> **Grain:** Per (order_id, cost_type)
> **cost_category values:** `COGS`, `PLATFORM_FEE`, `TAX`, `SHIPPING`, `DISCOUNT`
> **cost_type values (subset):** `cogs`, `platform_service`, `platform_payment`, `platform_fixed`, `platform_affiliate`, `platform_piship`, `platform_infra`, `platform_voucher_xtra`, `tax_vat`, `tax_pit`, `shipping_platform`, `discount_seller_voucher`, `discount_bundle`, `discount_seller`, `discount_manual`
> **Channel Join:** `dim_channels` via `channel_key`
> **Coverage:** COGS only for orders matched in MISA; Shopee fees only for Shopee orders; discounts for all Sapo orders with discount_items.

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Cost Ledger — Per-Order Costs | Which cost groups dominate by order, channel, or month? | 1. Total Costs (Tổng chi phí), 2. COGS Ratio — Cost Ledger (Tỷ lệ giá vốn / tổng chi phí), 3. Platform Fees Ratio (Tỷ lệ phí sàn / tổng chi phí), 4. Voucher / Discount Ratio (Tỷ lệ chiết khấu / tổng chi phí), 5. Cost Composition by Month (Cơ cấu chi phí theo tháng), 6. Top Channels by Total Cost (Kênh tốn nhiều chi phí nhất) | [`fact_order_costs`](../../../transformation/models/marts/sales/fact_order_costs.sql) | None documented |

### Analytical Questions

#### Q1. Cost Ledger — Per-Order Costs Readiness

- **Question:** Which cost groups dominate by order, channel, or month?
- **Definition:** This question defines whether `Cost Ledger — Per-Order Costs` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** cost analysis, value/quality.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 1. Total Costs (Tổng chi phí), 2. COGS Ratio — Cost Ledger (Tỷ lệ giá vốn / tổng chi phí), 3. Platform Fees Ratio (Tỷ lệ phí sàn / tổng chi phí), 4. Voucher / Discount Ratio (Tỷ lệ chiết khấu / tổng chi phí), 5. Cost Composition by Month (Cơ cấu chi phí theo tháng), 6. Top Channels by Total Cost (Kênh tốn nhiều chi phí nhất)

### Metrics

#### 1. Total Costs (Tổng chi phí)

> **dbt Model:** [`fact_order_costs`](../../../transformation/models/marts/sales/fact_order_costs.sql)

- **Business Definition:** Tổng tất cả các loại chi phí phát sinh cho một đơn hàng hoặc một kỳ — bao gồm giá vốn, phí sàn, thuế, vận chuyển và chiết khấu. Đây là "tổng tiền đi ra" của doanh nghiệp.
- **Logic (SQL):**
  ```sql
  SELECT COALESCE(SUM(amount), 0) AS total_costs
  FROM fact_order_costs
  ```
- **Source Mapping:**
  - **Table:** `fact_order_costs`
  - **Field:** `amount` (Sum)

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 2. COGS Ratio — Cost Ledger (Tỷ lệ giá vốn / tổng chi phí)

> **dbt Model:** [`fact_order_costs`](../../../transformation/models/marts/sales/fact_order_costs.sql)

- **Business Definition:** Phần trăm giá vốn hàng bán trong tổng chi phí. Cho biết chi phí sản xuất/mua hàng chiếm bao nhiêu % tổng "tiền ra".
- **Logic (SQL):**
  ```sql
  SELECT
      ROUND(
          SUM(CASE WHEN cost_category = 'COGS' THEN amount ELSE 0 END) * 100.0
          / NULLIF(SUM(amount), 0),
          1
      ) AS cogs_ratio_pct
  FROM fact_order_costs
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 3. Platform Fees Ratio (Tỷ lệ phí sàn / tổng chi phí)

> **dbt Model:** [`fact_order_costs`](../../../transformation/models/marts/sales/fact_order_costs.sql)

- **Business Definition:** Phần trăm phí nền tảng (Shopee: service, payment, fixed, affiliate, piship, infra, voucher xtra) trong tổng chi phí. Tăng cao cho thấy chi phí bán trên sàn đang bào mòn lợi nhuận.
- **Logic (SQL):**
  ```sql
  SELECT
      ROUND(
          SUM(CASE WHEN cost_category = 'PLATFORM_FEE' THEN amount ELSE 0 END) * 100.0
          / NULLIF(SUM(amount), 0),
          1
      ) AS platform_fee_ratio_pct
  FROM fact_order_costs
  ```
- **Threshold:**
  - Healthy: < 8% of total costs
  - Watch: 8–12%
  - Alert: > 12%

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 4. Voucher / Discount Ratio (Tỷ lệ chiết khấu / tổng chi phí)

> **dbt Model:** [`fact_order_costs`](../../../transformation/models/marts/sales/fact_order_costs.sql)

- **Business Definition:** Phần trăm chi phí chiết khấu (voucher seller, bundle deal, manual discount) trong tổng chi phí. Phản ánh mức độ phụ thuộc vào khuyến mãi để tăng doanh số.
- **Logic (SQL):**
  ```sql
  SELECT
      ROUND(
          SUM(CASE WHEN cost_category = 'DISCOUNT' THEN amount ELSE 0 END) * 100.0
          / NULLIF(SUM(amount), 0),
          1
      ) AS discount_ratio_pct
  FROM fact_order_costs
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 5. Cost Composition by Month (Cơ cấu chi phí theo tháng)

> **dbt Model:** [`fact_order_costs`](../../../transformation/models/marts/sales/fact_order_costs.sql)

- **Business Definition:** Breakdown chi phí theo từng cost_category (COGS, PLATFORM_FEE, TAX, SHIPPING, DISCOUNT) qua từng tháng. Dùng để vẽ stacked bar chart — thấy ngay chi phí nào đang tăng bất thường.
- **Logic (SQL):**
  ```sql
  SELECT
      date_trunc('month', CAST(date_key AS DATE)) AS month,
      cost_category,
      COALESCE(SUM(amount), 0)                    AS total_amount
  FROM fact_order_costs
  GROUP BY 1, 2
  ORDER BY 1, 2
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 6. Top Channels by Total Cost (Kênh tốn nhiều chi phí nhất)

> **dbt Model:** [`fact_order_costs`](../../../transformation/models/marts/sales/fact_order_costs.sql)

- **Business Definition:** Ranking kênh bán hàng theo tổng chi phí, kèm % breakdown từng loại chi phí. Giúp CFO xác định kênh nào "ăn" ngân sách nhiều nhất và theo loại chi phí nào.
- **Logic (SQL):**
  ```sql
  SELECT
      c.channel_name,
      COALESCE(SUM(fc.amount), 0)                                                   AS total_costs,
      ROUND(SUM(CASE WHEN fc.cost_category = 'COGS'         THEN fc.amount ELSE 0 END) * 100.0 / NULLIF(SUM(fc.amount), 0), 1) AS cogs_pct,
      ROUND(SUM(CASE WHEN fc.cost_category = 'PLATFORM_FEE' THEN fc.amount ELSE 0 END) * 100.0 / NULLIF(SUM(fc.amount), 0), 1) AS platform_fee_pct,
      ROUND(SUM(CASE WHEN fc.cost_category = 'DISCOUNT'     THEN fc.amount ELSE 0 END) * 100.0 / NULLIF(SUM(fc.amount), 0), 1) AS discount_pct,
      ROUND(SUM(CASE WHEN fc.cost_category = 'TAX'          THEN fc.amount ELSE 0 END) * 100.0 / NULLIF(SUM(fc.amount), 0), 1) AS tax_pct,
      ROUND(SUM(CASE WHEN fc.cost_category = 'SHIPPING'     THEN fc.amount ELSE 0 END) * 100.0 / NULLIF(SUM(fc.amount), 0), 1) AS shipping_pct
  FROM fact_order_costs fc
  LEFT JOIN dim_channels c ON fc.channel_key = c.channel_key
  GROUP BY c.channel_name
  ORDER BY total_costs DESC
  LIMIT 20
  ```

<!-- COST_LEDGER_SECTION_END -->
<!-- ============================================================ -->

<!-- ============================================================ -->
<!-- RETURN_IMPACT_SECTION_START — owned by Phase 05 Return Impact agent -->

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Returns & Refund Liability

> **Description:** Per-return event tracking refund exposure, return rate, and reason analysis. Returns are recognized at return date — original order P&L is not restated. Dashboard: Return Impact Analysis [All].
> **dbt Source:** [`fact_order_returns`](../../../transformation/models/marts/sales/fact_order_returns.sql)
> **Grain:** Per Return Event (one row per Sapo return)
> **Key Fields:** `return_id`, `order_code`, `return_date`, `return_timestamp`, `refund_amount`, `return_quantity`, `return_status`, `refund_status`, `return_reason`, `channel_key`, `date_key`
> **Join:** `fact_order_returns.order_code` → `fact_orders.order_code` for order-date cohort; `channel_key` → `dim_channels` for channel name

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Returns & Refund Liability | How much revenue risk and refund liability is created by returns? | R1. Return Rate MTD (Ty le hoan hang), R2. Refund Liability (Gia tri hoan tien), R3. Average Days-to-Return (So ngay trung binh den hoan), R4. Return Reason Top (Ly do hoan pho bien), R5. Return Rate by Channel (Ty le hoan theo kenh), R6. Return Revenue Impact (Doanh thu bi hoan) | [`fact_order_returns`](../../../transformation/models/marts/sales/fact_order_returns.sql) | None documented |

### Analytical Questions

#### Q1. Returns & Refund Liability Readiness

- **Question:** How much revenue risk and refund liability is created by returns?
- **Definition:** This question defines whether `Returns & Refund Liability` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** returns risk, finance operations.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** R1. Return Rate MTD (Ty le hoan hang), R2. Refund Liability (Gia tri hoan tien), R3. Average Days-to-Return (So ngay trung binh den hoan), R4. Return Reason Top (Ly do hoan pho bien), R5. Return Rate by Channel (Ty le hoan theo kenh), R6. Return Revenue Impact (Doanh thu bi hoan)

### Metrics

#### R1. Return Rate MTD (Ty le hoan hang)

> **dbt Model:** [`fact_order_returns`](../../../transformation/models/marts/sales/fact_order_returns.sql)

- **Business Definition:** Phan tram don hang bi hoan trong ky. So sanh so return event voi tong don hang hop le cung ky.
- **Logic (SQL):**
  ```sql
  WITH returns_mtd AS (
      SELECT COUNT(DISTINCT order_code) AS returned_orders
      FROM fact_order_returns
      WHERE return_date >= date_trunc('month', current_date)
        AND return_date < current_date
  ),
  orders_mtd AS (
      SELECT COUNT(DISTINCT order_code) AS total_orders
      FROM fact_orders
      WHERE status NOT IN ('CANCELLED', 'Voided')
        AND order_timestamp >= date_trunc('month', current_date)
        AND order_timestamp < current_date
  )
  SELECT ROUND(r.returned_orders * 100.0 / NULLIF(o.total_orders, 0), 2) AS return_rate_pct
  FROM returns_mtd r, orders_mtd o
  ```
- **Threshold:** Healthy < 2% | Watch 2-5% | Alert > 5%

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### R2. Refund Liability (Gia tri hoan tien)

> **dbt Model:** [`fact_order_returns`](../../../transformation/models/marts/sales/fact_order_returns.sql)

- **Business Definition:** Tong gia tri hoan tien phat sinh trong ky — do muc do anh huong tai chinh truc tiep tu hang hoan.
- **Logic (SQL):**
  ```sql
  SELECT COALESCE(SUM(refund_amount), 0) AS refund_liability
  FROM fact_order_returns
  WHERE return_date >= date_trunc('month', current_date)
    AND return_date < current_date
  ```
- **Unit:** VND

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the business formula follows the metric definition and source grain above.
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### R3. Average Days-to-Return (So ngay trung binh den hoan)

> **dbt Model:** [`fact_order_returns`](../../../transformation/models/marts/sales/fact_order_returns.sql) JOIN [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** So ngay trung binh giua ngay dat hang va ngay hoan hang. Phat hien van de chat luong (hoan som) hoac gian lan (hoan muon).
- **Logic (SQL):**
  ```sql
  SELECT ROUND(AVG(
      date_diff('day', DATE(o.order_timestamp), r.return_date)
  ), 1) AS avg_days_to_return
  FROM fact_order_returns r
  JOIN fact_orders o ON r.order_code = o.order_code
  WHERE r.return_date >= date_trunc('month', current_date)
    AND o.status NOT IN ('CANCELLED', 'Voided')
  ```
- **Unit:** Days

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the business formula follows the metric definition and source grain above.
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### R4. Return Reason Top (Ly do hoan pho bien)

> **dbt Model:** [`fact_order_returns`](../../../transformation/models/marts/sales/fact_order_returns.sql)

- **Business Definition:** Ly do hoan hang xuat hien nhieu nhat — giup xac dinh nguyen nhan goc re de cai thien chat luong/van hanh.
- **Logic (SQL):**
  ```sql
  SELECT COALESCE(return_reason, 'Khong ro') AS return_reason, COUNT(*) AS cnt
  FROM fact_order_returns
  WHERE return_date >= date_trunc('month', current_date)
  GROUP BY 1 ORDER BY 2 DESC LIMIT 1
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### R5. Return Rate by Channel (Ty le hoan theo kenh)

> **dbt Models:** [`fact_order_returns`](../../../transformation/models/marts/sales/fact_order_returns.sql), [`dim_channels`](../../../transformation/models/marts/core/dim_channels.sql)

- **Business Definition:** Ty le hoan phan ra theo kenh ban hang. Kenh nao > 5% can dieu tra ngay.
- **Logic (SQL):**
  ```sql
  WITH ret AS (
      SELECT channel_key, COUNT(DISTINCT order_code) AS returned_orders
      FROM fact_order_returns GROUP BY 1
  ),
  ord AS (
      SELECT channel_key, COUNT(DISTINCT order_code) AS total_orders
      FROM fact_orders WHERE status NOT IN ('CANCELLED', 'Voided') GROUP BY 1
  )
  SELECT c.channel_name,
         ROUND(ret.returned_orders * 100.0 / NULLIF(ord.total_orders, 0), 2) AS return_rate_pct
  FROM ret JOIN ord USING (channel_key)
  JOIN dim_channels c USING (channel_key)
  WHERE c.is_sales_channel
  ORDER BY return_rate_pct DESC
  ```
- **Alert Threshold:** > 5% triggers investigation.

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### R6. Return Revenue Impact (Doanh thu bi hoan)

> **dbt Model:** [`fact_order_returns`](../../../transformation/models/marts/sales/fact_order_returns.sql)

- **Business Definition:** Tong refund_amount theo ly do hoan — giup luong hoa muc do anh huong doanh thu theo tung nguyen nhan.
- **Logic (SQL):**
  ```sql
  SELECT COALESCE(return_reason, 'Khong ro') AS return_reason,
         COUNT(*) AS return_count,
         COALESCE(SUM(refund_amount), 0) AS revenue_impact
  FROM fact_order_returns
  GROUP BY 1 ORDER BY 3 DESC LIMIT 10
  ```

<!-- RETURN_IMPACT_SECTION_END -->
<!-- ============================================================ -->

<!-- ============================================================ -->
<!-- CHANNEL_PL_SECTION_START — owned by Phase 05 Channel P&L agent -->

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Channel P&L Waterfall & Loss-Leader Detection

> **Description:** Per-channel P&L combining Sapo revenue, MISA COGS, and Shopee platform fees at order level. Enables waterfall decomposition (Gross Revenue → Discounts → Net Revenue → COGS → Platform Fees → Net Profit) and loss-leader detection. Dashboard: Channel P&L Deep Dive [Cross].
> **dbt Source:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)
> **Grain:** Per Order (aggregated to channel × period for reporting)
> **Filters:** `is_sales_channel = true AND status NOT IN ('CANCELLED','Voided') AND has_cogs = true`
> **Join Keys:** `channel_key` → `dim_channels`; Shopee fees are pre-joined in mart via `order_code`

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Channel P&L Waterfall & Loss-Leader Detection | Which channels generate net profit and which behave as loss leaders? | CPL1. Channel Net Margin % (Biên lợi nhuận ròng kênh), CPL2. Loss Leader Flag (Cờ kênh lỗ), CPL3. Channel Variance vs Prior Period (Biến động so với kỳ trước), CPL4. Waterfall Components (Thành phần thác nước P&L), CPL5. Channel Scorecard (Bảng điểm kênh), CPL6. Net Margin % Heatmap — Channel × Month | [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql) | None documented |

### Analytical Questions

#### Q1. Channel P&L Waterfall & Loss-Leader Detection Readiness

- **Question:** Which channels generate net profit and which behave as loss leaders?
- **Definition:** This question defines whether `Channel P&L Waterfall & Loss-Leader Detection` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** channel profitability, comparative.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** CPL1. Channel Net Margin % (Biên lợi nhuận ròng kênh), CPL2. Loss Leader Flag (Cờ kênh lỗ), CPL3. Channel Variance vs Prior Period (Biến động so với kỳ trước), CPL4. Waterfall Components (Thành phần thác nước P&L), CPL5. Channel Scorecard (Bảng điểm kênh), CPL6. Net Margin % Heatmap — Channel × Month

### Metrics

#### CPL1. Channel Net Margin % (Biên lợi nhuận ròng kênh)

> **dbt Model:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)

- **Business Definition:** Tỷ lệ lợi nhuận ròng sau khi trừ COGS và toàn bộ phí platform (Shopee). Đây là chỉ số cuối cùng để phân biệt kênh lãi và kênh lỗ sau chi phí thực tế.
- **Logic (SQL):**
  ```sql
  SELECT
      c.channel_name,
      ROUND(
          SUM(e.channel_net_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0),
          1
      ) AS channel_net_margin_pct
  FROM fact_order_economics e
  JOIN dim_channels c USING (channel_key)
  WHERE e.has_cogs
    AND e.status NOT IN ('CANCELLED', 'Voided')
    AND c.is_sales_channel
  GROUP BY c.channel_name
  ```
- **Threshold:**
  - Healthy: > 20%
  - Watch: 0–20%
  - Alert (Loss Leader): < 0%

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### CPL2. Loss Leader Flag (Cờ kênh lỗ)

> **dbt Model:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)

- **Business Definition:** Kênh có `channel_net_profit < 0` sau khi trừ COGS và phí platform — cần điều tra ngay về chiến lược giá và chi phí sàn.
- **Logic (SQL):**
  ```sql
  SELECT
      c.channel_name,
      ROUND(SUM(e.channel_net_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1) AS channel_net_margin_pct,
      CASE WHEN SUM(e.channel_net_profit) < 0 THEN 'LỖ' ELSE 'LÃI' END AS profit_flag
  FROM fact_order_economics e
  JOIN dim_channels c USING (channel_key)
  WHERE e.has_cogs AND e.status NOT IN ('CANCELLED', 'Voided') AND c.is_sales_channel
  GROUP BY c.channel_name
  HAVING SUM(e.channel_net_profit) < 0
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### CPL3. Channel Variance vs Prior Period (Biến động so với kỳ trước)

> **dbt Model:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)

- **Business Definition:** So sánh Net Revenue và Net Margin % của kênh giữa kỳ hiện tại và kỳ trước (WoW, MoM, YoY). Phát hiện kênh nào đang suy giảm nhanh.
- **Logic (SQL):**
  ```sql
  WITH cur AS (
      SELECT channel_key,
          SUM(net_revenue)   AS rev_cur,
          ROUND(SUM(channel_net_profit) * 100.0 / NULLIF(SUM(net_revenue), 0), 1) AS margin_cur
      FROM fact_order_economics
      WHERE has_cogs AND status NOT IN ('CANCELLED', 'Voided')
        AND CAST(CAST(date_key AS VARCHAR) AS DATE) >= date_trunc('month', current_date)
      GROUP BY channel_key
  ),
  prior AS (
      SELECT channel_key,
          SUM(net_revenue)   AS rev_prior,
          ROUND(SUM(channel_net_profit) * 100.0 / NULLIF(SUM(net_revenue), 0), 1) AS margin_prior
      FROM fact_order_economics
      WHERE has_cogs AND status NOT IN ('CANCELLED', 'Voided')
        AND CAST(CAST(date_key AS VARCHAR) AS DATE) >= date_trunc('month', current_date) - INTERVAL '1 month'
        AND CAST(CAST(date_key AS VARCHAR) AS DATE) <  date_trunc('month', current_date)
      GROUP BY channel_key
  )
  SELECT
      c.channel_name,
      cur.rev_cur, prior.rev_prior,
      ROUND((cur.rev_cur - COALESCE(prior.rev_prior, 0)) * 100.0 / NULLIF(prior.rev_prior, 0), 1) AS rev_delta_pct,
      cur.margin_cur, prior.margin_prior,
      ROUND(cur.margin_cur - COALESCE(prior.margin_prior, 0), 1) AS margin_delta_pp
  FROM cur
  LEFT JOIN prior USING (channel_key)
  JOIN dim_channels c USING (channel_key)
  WHERE c.is_sales_channel
  ORDER BY margin_delta_pp ASC
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### CPL4. Waterfall Components (Thành phần thác nước P&L)

> **dbt Model:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)

- **Business Definition:** Phân tách dòng tiền từ Gross Revenue → Discounts → Net Revenue → COGS → Platform Fees → Net Profit. Mỗi bước là một khoản trừ giúp thấy rõ tiền bị mất ở đâu.
- **Components:**
  - `Doanh thu gop` = `SUM(gross_revenue)`
  - `Chiet khau` = `-SUM(ABS(discount_amount))` (negative deduction)
  - `Doanh thu thuan` = `SUM(net_revenue)` (running subtotal bar)
  - `Gia von COGS` = `-SUM(COALESCE(cogs_amount, 0))`
  - `Phi platform` = Shopee fees (already negative in mart — sum as-is)
  - `Loi nhuan rong` = `SUM(channel_net_profit)` (final total bar)
- **Logic (SQL):**
  ```sql
  SELECT "Khoan muc", COALESCE("Gia tri", 0) AS "Gia tri"
  FROM (
      VALUES
          ('Doanh thu gop',   (SELECT SUM(gross_revenue)        FROM fact_order_economics WHERE has_cogs AND status NOT IN ('CANCELLED','Voided'))),
          ('Chiet khau',      (SELECT -SUM(ABS(discount_amount)) FROM fact_order_economics WHERE has_cogs AND status NOT IN ('CANCELLED','Voided'))),
          ('Doanh thu thuan', (SELECT SUM(net_revenue)           FROM fact_order_economics WHERE has_cogs AND status NOT IN ('CANCELLED','Voided'))),
          ('Gia von COGS',    (SELECT -SUM(COALESCE(cogs_amount,0)) FROM fact_order_economics WHERE has_cogs AND status NOT IN ('CANCELLED','Voided'))),
          ('Phi platform',    (SELECT SUM(COALESCE(shopee_platform_fees,0) + COALESCE(shopee_infra_fee,0) + COALESCE(shopee_voucher_xtra_fee,0) + COALESCE(shopee_taxes,0)) FROM fact_order_economics WHERE has_cogs AND status NOT IN ('CANCELLED','Voided'))),
          ('Loi nhuan rong',  (SELECT SUM(channel_net_profit)   FROM fact_order_economics WHERE has_cogs AND status NOT IN ('CANCELLED','Voided')))
  ) AS t("Khoan muc", "Gia tri")
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### CPL5. Channel Scorecard (Bảng điểm kênh)

> **dbt Model:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)

- **Business Definition:** Một dòng/kênh với đầy đủ: Net Revenue, Gross Margin %, Net Margin %, Order Volume, Platform Fees. Cho phép Finance Director so sánh tất cả kênh trong một màn hình.
- **Logic (SQL):**
  ```sql
  SELECT
      c.channel_name                                                                        AS "Kenh",
      COUNT(*)                                                                              AS "So don",
      COALESCE(SUM(e.net_revenue), 0)                                                       AS "Net Revenue",
      ROUND(SUM(e.gross_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1)                AS "Gross Margin %",
      ROUND(SUM(e.channel_net_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1)          AS "Net Margin %",
      COALESCE(SUM(ABS(COALESCE(e.shopee_platform_fees,0)) + ABS(COALESCE(e.shopee_infra_fee,0)) + ABS(COALESCE(e.shopee_voucher_xtra_fee,0))), 0) AS "Platform Fees"
  FROM fact_order_economics e
  JOIN dim_channels c USING (channel_key)
  WHERE e.has_cogs AND e.status NOT IN ('CANCELLED', 'Voided') AND c.is_sales_channel
  GROUP BY c.channel_name
  ORDER BY "Net Margin %" ASC
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### CPL6. Net Margin % Heatmap — Channel × Month

> **dbt Model:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)

- **Business Definition:** Ma trận kênh × tháng, màu sắc = Net Margin %. Phát hiện kênh nào đang suy giảm margin theo thời gian, hoặc tháng nào bất thường.
- **Logic (SQL):**
  ```sql
  SELECT
      c.channel_name                                                                AS "Kenh",
      date_trunc('month', CAST(CAST(e.date_key AS VARCHAR) AS DATE))               AS "Thang",
      ROUND(SUM(e.channel_net_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1) AS "Net Margin %"
  FROM fact_order_economics e
  JOIN dim_channels c USING (channel_key)
  WHERE e.has_cogs AND e.status NOT IN ('CANCELLED', 'Voided') AND c.is_sales_channel
  GROUP BY c.channel_name, date_trunc('month', CAST(CAST(e.date_key AS VARCHAR) AS DATE))
  ORDER BY "Thang", "Kenh"
  ```

<!-- CHANNEL_PL_SECTION_END -->
<!-- ============================================================ -->

<!-- ============================================================ -->
<!-- SKU_MARGIN_SECTION_START — owned by Phase 05 SKU Margin agent -->

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: SKU Cost & Margin Variance

> **Description:** Per-SKU gross margin and COGS tracking from MISA sales ledger. Enables merchandising analysis of which SKUs drive profit vs. which have abnormal COGS drift. Promo lines excluded (`NOT is_promo_line`) to reflect true product economics.
> **dbt Source:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)
> **Grain:** Per SKU (aggregated from invoice lines)
> **Audience:** Merchandising Manager, Finance

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| SKU Cost & Margin Variance | Which SKUs have abnormal margin or COGS variance? | M1. SKU Gross Margin % (Biên lợi nhuận gộp theo SKU), M2. COGS Per Unit (Giá vốn trung bình mỗi đơn vị), M3. COGS Variance vs 3-Month Average (Sai lệch giá vốn so với trung bình 3 tháng), M4. SKU Revenue Share (Tỷ trọng doanh thu SKU), M5. Margin Outlier Flag (Cờ margin bất thường) | [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql) | None documented |

### Analytical Questions

#### Q1. SKU Cost & Margin Variance Readiness

- **Question:** Which SKUs have abnormal margin or COGS variance?
- **Definition:** This question defines whether `SKU Cost & Margin Variance` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** sku margin, anomaly detection.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** M1. SKU Gross Margin % (Biên lợi nhuận gộp theo SKU), M2. COGS Per Unit (Giá vốn trung bình mỗi đơn vị), M3. COGS Variance vs 3-Month Average (Sai lệch giá vốn so với trung bình 3 tháng), M4. SKU Revenue Share (Tỷ trọng doanh thu SKU), M5. Margin Outlier Flag (Cờ margin bất thường)

### Metrics

#### M1. SKU Gross Margin % (Biên lợi nhuận gộp theo SKU)

> **dbt Model:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)

- **Business Definition:** Phần trăm doanh thu thuần còn lại sau giá vốn, tính theo từng SKU. Đo lường hiệu quả định giá và chiến lược sản phẩm ở cấp độ SKU.
- **Logic (SQL):**
  ```sql
  SELECT
      product_code,
      product_name,
      ROUND(
          SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
          1
      ) AS sku_gross_margin_pct
  FROM int_misa_sales_lines
  WHERE NOT is_promo_line
    AND revenue_net_of_discount > 0
  GROUP BY product_code, product_name
  ```
- **Threshold:**
  - Healthy: > 40%
  - Watch: 20–40%
  - Alert (Outlier): < 10% → flag as low-margin

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### M2. COGS Per Unit (Giá vốn trung bình mỗi đơn vị)

> **dbt Model:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)

- **Business Definition:** Giá vốn trung bình trên mỗi đơn vị bán ra của một SKU. Phản ánh chi phí nhập hàng thực tế và hữu ích để phát hiện thay đổi giá nhập đột biến.
- **Logic (SQL):**
  ```sql
  SELECT
      product_code,
      product_name,
      ROUND(
          SUM(cogs_amount) / NULLIF(SUM(quantity), 0),
          0
      ) AS cogs_per_unit
  FROM int_misa_sales_lines
  WHERE NOT is_promo_line
    AND quantity > 0
  GROUP BY product_code, product_name
  ```
- **Unit:** VND per unit

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the business formula follows the metric definition and source grain above.
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### M3. COGS Variance vs 3-Month Average (Sai lệch giá vốn so với trung bình 3 tháng)

> **dbt Model:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)

- **Business Definition:** So sánh giá vốn mỗi đơn vị của tháng hiện tại với trung bình 3 tháng gần nhất. Phát hiện bất thường chi phí nhập hàng (thay đổi nhà cung cấp, lỗi hạch toán, cost spike).
- **Logic (SQL):**
  ```sql
  WITH current_cogs AS (
      SELECT
          product_code,
          product_name,
          SUM(cogs_amount) / NULLIF(SUM(quantity), 0) AS cogs_per_unit_current
      FROM int_misa_sales_lines
      WHERE NOT is_promo_line
        AND quantity > 0
        AND posting_date >= date_trunc('month', current_date)
      GROUP BY product_code, product_name
  ),
  avg_3m AS (
      SELECT
          product_code,
          SUM(cogs_amount) / NULLIF(SUM(quantity), 0) AS cogs_per_unit_3m_avg
      FROM int_misa_sales_lines
      WHERE NOT is_promo_line
        AND quantity > 0
        AND posting_date >= date_trunc('month', current_date) - INTERVAL '3 months'
        AND posting_date <  date_trunc('month', current_date)
      GROUP BY product_code
  )
  SELECT
      c.product_code,
      c.product_name,
      c.cogs_per_unit_current,
      a.cogs_per_unit_3m_avg,
      ROUND(
          (c.cogs_per_unit_current - a.cogs_per_unit_3m_avg)
          * 100.0 / NULLIF(a.cogs_per_unit_3m_avg, 0),
          1
      ) AS cogs_variance_pct
  FROM current_cogs c
  LEFT JOIN avg_3m a USING (product_code)
  ```
- **Threshold:** |variance| > 10% → flag for investigation

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### M4. SKU Revenue Share (Tỷ trọng doanh thu SKU)

> **dbt Model:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)

- **Business Definition:** Phần trăm doanh thu của một SKU trong tổng doanh thu kỳ. Kết hợp với Margin % để phân loại SKU: high-revenue+high-margin (star), high-revenue+low-margin (cash drain), low-revenue+high-margin (niche gem).
- **Logic (SQL):**
  ```sql
  SELECT
      product_code,
      product_name,
      SUM(revenue_net_of_discount) AS sku_revenue,
      ROUND(
          SUM(revenue_net_of_discount) * 100.0
          / NULLIF(SUM(SUM(revenue_net_of_discount)) OVER (), 0),
          2
      ) AS revenue_share_pct
  FROM int_misa_sales_lines
  WHERE NOT is_promo_line
    AND revenue_net_of_discount > 0
  GROUP BY product_code, product_name
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### M5. Margin Outlier Flag (Cờ margin bất thường)

> **dbt Model:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)

- **Business Definition:** SKU được đánh dấu là "outlier" khi gross margin < 10%. Đây là ngưỡng cảnh báo cần hành động: rà soát giá bán, COGS, hoặc loại SKU khỏi danh mục.
- **Logic (SQL):**
  ```sql
  SELECT
      product_code,
      product_name,
      ROUND(
          SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
          1
      ) AS gross_margin_pct,
      CASE
          WHEN SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0) < 10
          THEN true ELSE false
      END AS is_margin_outlier
  FROM int_misa_sales_lines
  WHERE NOT is_promo_line
    AND revenue_net_of_discount > 0
  GROUP BY product_code, product_name
  ```
- **Alert:** `is_margin_outlier = true` → highlight red in dashboard

<!-- SKU_MARGIN_SECTION_END -->
<!-- ============================================================ -->

<!-- ============================================================ -->
<!-- RECON_SECTION_START — owned by Phase 05 Recon agent -->

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Daily Reconciliation (Sapo ↔ MISA ↔ Shopee)

> **Status: Proxy mode** — `recon_sapo_orders_daily` and `recon_misa_daily` tables are **not yet built**.
> Metrics below derive from `fact_order_economics` flags as proxy:
> - **Sapo↔MISA match proxy:** `has_cogs = TRUE` (order has MISA invoice line joined via `voucher_no = order_code`)
> - **Sapo↔Shopee match proxy:** `has_platform_fees = TRUE` (order has Shopee payout record)
> - **Triple match (fully reconciled):** `has_cogs AND has_platform_fees` (Shopee orders only)
> **dbt Source:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)
> **Grain:** Per Order
> **Known Limitation:** `has_cogs` coverage ≈ 65% of completed orders in MISA date range — unmatched orders include cancelled/draft + orders before MISA ingestion window.
> **Caveat:** This is a derived proxy, not a true reconciliation ledger. Build `recon_sapo_orders_daily` + `recon_misa_daily` dbt models for a proper recon pipeline.

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Daily Reconciliation (Sapo ↔ MISA ↔ Shopee) | Do Sapo, MISA, and Shopee reconcile well enough to trust finance reporting? | RC1. MISA Coverage % (Tỷ lệ khớp MISA), RC2. Unmatched Rate — No MISA (Tỷ lệ thiếu MISA invoice), RC3. Shopee Fee Coverage % (Tỷ lệ có dữ liệu phí Shopee), RC4. Recon Status Distribution (Phân loại trạng thái đối soát), RC5. Daily Unmatched Trend (Xu hướng đơn chưa đối soát theo ngày), RC6. Sapo↔Shopee Fee Gap (Đơn Shopee thiếu dữ liệu phí) | [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql) | None documented |

### Analytical Questions

#### Q1. Daily Reconciliation (Sapo ↔ MISA ↔ Shopee) Readiness

- **Question:** Do Sapo, MISA, and Shopee reconcile well enough to trust finance reporting?
- **Definition:** This question defines whether `Daily Reconciliation (Sapo ↔ MISA ↔ Shopee)` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** accounting reconciliation, operational quality.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** RC1. MISA Coverage % (Tỷ lệ khớp MISA), RC2. Unmatched Rate — No MISA (Tỷ lệ thiếu MISA invoice), RC3. Shopee Fee Coverage % (Tỷ lệ có dữ liệu phí Shopee), RC4. Recon Status Distribution (Phân loại trạng thái đối soát), RC5. Daily Unmatched Trend (Xu hướng đơn chưa đối soát theo ngày), RC6. Sapo↔Shopee Fee Gap (Đơn Shopee thiếu dữ liệu phí)

### Metrics

#### RC1. MISA Coverage % (Tỷ lệ khớp MISA)

> **dbt Model:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)

- **Business Definition:** Phần trăm đơn hàng hoàn tất có MISA invoice khớp. Đây là proxy cho "Sapo↔MISA reconciled". Thấp hơn benchmark (≈65%) → cần kiểm tra MISA ingestion.
- **Logic (SQL):**
  ```sql
  SELECT
      ROUND(
          SUM(CASE WHEN has_cogs THEN 1 ELSE 0 END) * 100.0
          / NULLIF(COUNT(*), 0),
          1
      ) AS misa_coverage_pct
  FROM fact_order_economics
  WHERE status = 'COMPLETED'
  ```
- **Threshold:**
  - Healthy: > 70%
  - Watch: 50-70%
  - Alert: < 50%

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### RC2. Unmatched Rate — No MISA (Tỷ lệ thiếu MISA invoice)

> **dbt Model:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)

- **Business Definition:** Phần trăm đơn hàng hoàn tất KHÔNG có MISA invoice. Đây là "unmatched orders" từ góc độ kế toán.
- **Logic (SQL):**
  ```sql
  SELECT
      ROUND(
          SUM(CASE WHEN NOT has_cogs THEN 1 ELSE 0 END) * 100.0
          / NULLIF(COUNT(*), 0),
          1
      ) AS unmatched_rate_pct
  FROM fact_order_economics
  WHERE status = 'COMPLETED'
  ```
- **Threshold:**
  - Healthy: < 30%
  - Watch: 30-50%
  - Alert: > 50%

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### RC3. Shopee Fee Coverage % (Tỷ lệ có dữ liệu phí Shopee)

> **dbt Model:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)

- **Business Definition:** Phần trăm đơn hàng Shopee có dữ liệu payout/phí từ Shopee Seller Center. Thấp → thiếu settlement data → không tính được channel_net_profit chính xác.
- **Logic (SQL):**
  ```sql
  SELECT
      ROUND(
          SUM(CASE WHEN e.has_platform_fees THEN 1 ELSE 0 END) * 100.0
          / NULLIF(COUNT(*), 0),
          1
      ) AS shopee_fee_coverage_pct
  FROM fact_order_economics e
  JOIN dim_channels c ON e.channel_key = c.channel_key
  WHERE c.channel_name ILIKE '%shopee%'
    AND e.status = 'COMPLETED'
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### RC4. Recon Status Distribution (Phân loại trạng thái đối soát)

> **dbt Model:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)

- **Business Definition:** Phân nhóm đơn hàng theo trạng thái recon: FULLY_RECONCILED / MISSING_MISA / MISSING_SHOPEE_FEES / UNRECONCILED. Proxy từ `has_cogs` và `has_platform_fees`.
- **Logic (SQL):**
  ```sql
  SELECT
      CASE
          WHEN has_cogs AND has_platform_fees THEN 'FULLY_RECONCILED'
          WHEN has_cogs AND NOT has_platform_fees THEN 'MISSING_SHOPEE_FEES'
          WHEN NOT has_cogs AND has_platform_fees THEN 'MISSING_MISA'
          ELSE 'UNRECONCILED'
      END AS recon_status,
      COUNT(*) AS order_count,
      COALESCE(SUM(net_revenue), 0) AS revenue_at_risk
  FROM fact_order_economics
  WHERE status = 'COMPLETED'
  GROUP BY 1
  ORDER BY 2 DESC
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### RC5. Daily Unmatched Trend (Xu hướng đơn chưa đối soát theo ngày)

> **dbt Model:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)

- **Business Definition:** Tỷ lệ đơn không có MISA invoice theo ngày — 30 ngày gần nhất. Spike đột ngột → lỗi ingestion MISA hoặc Sapo data lag.
- **Logic (SQL):**
  ```sql
  SELECT
      CAST(CAST(date_key AS VARCHAR) AS DATE) AS order_date,
      COUNT(*) AS total_orders,
      SUM(CASE WHEN NOT has_cogs THEN 1 ELSE 0 END) AS unmatched_orders,
      ROUND(
          SUM(CASE WHEN NOT has_cogs THEN 1 ELSE 0 END) * 100.0
          / NULLIF(COUNT(*), 0),
          1
      ) AS unmatched_pct
  FROM fact_order_economics
  WHERE status = 'COMPLETED'
    AND date_key >= CAST(current_date - INTERVAL '30 days' AS INTEGER)
  GROUP BY 1
  ORDER BY 1
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### RC6. Sapo↔Shopee Fee Gap (Đơn Shopee thiếu dữ liệu phí)

> **dbt Model:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)

- **Business Definition:** Đơn Shopee có doanh thu nhưng thiếu `shopee_platform_fees` → channel_net_profit bị overstate. Số này là "fee gap" cho kế toán reconcile.
- **Logic (SQL):**
  ```sql
  SELECT
      COUNT(*) AS shopee_orders_missing_fees,
      COALESCE(SUM(e.net_revenue), 0) AS revenue_without_fee_data
  FROM fact_order_economics e
  JOIN dim_channels c ON e.channel_key = c.channel_key
  WHERE c.channel_name ILIKE '%shopee%'
    AND e.status = 'COMPLETED'
    AND NOT e.has_platform_fees
  ```

<!-- RECON_SECTION_END -->
<!-- ============================================================ -->

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Services Revenue

> **Description:** Doanh thu dịch vụ (non-product) tracked separately for CFO P&L review. Covers US HR staffing services (DVCCNS/DVCCNS1), legacy office utilities (DVRENTAL/DVDIEN/etc. — discontinued 2022), and CPBH adjustment entries. Services have zero COGS in MISA — contribution margin = 100%.
> **dbt Source:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql) WHERE `is_service_line = true`
> **Grain:** Per Invoice Line
> **Flag:** `is_service_line = (product_code LIKE 'DV%' OR product_code LIKE 'CPBH%')` — added in P0

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Services Revenue | Doanh thu dịch vụ đang tăng hay giảm? DVCCNS contract còn active không? CPBH adjustments có bất thường không? | S1. Services Revenue, S2. Services as % of Total Revenue, S3. Service Type Breakdown, S4. CPBH Adjustments | `int_misa_sales_lines` + `is_service_line` flag (P0) | `is_service_line` flag must be deployed before queries return data |

### Analytical Questions

#### Q1. Services Revenue Tracking

- **Question:** Doanh thu dịch vụ hàng tháng có ổn định không? DVCCNS US HR contract còn đang được xuất hóa đơn?
- **Definition:** Theo dõi revenue từ DV* codes (dịch vụ) tách biệt khỏi hàng hóa — phát hiện sụt giảm contract hay phát sinh mã mới.
- **Nature:** Revenue tracking, lagging/value.
- **Why It Matters:** 2.4B VND/năm (10%+ tổng revenue MISA) hiện invisible vì lẫn với hàng hóa. CFO cần thấy riêng để đánh giá cơ cấu doanh thu.
- **Tradeoffs / Caveats:** Services có COGS = 0 — không dùng gross margin % để so sánh với hàng hóa. Posting date có thể delay 1-3 ngày so với transaction date thực.
- **Insight / Action Enabled:** Nếu DVCCNS drop MoM > 20% → kiểm tra contract status. Nếu CPBH spike âm > 100M → reconcile với chứng từ gốc.
- **Related Metrics:** S1. Services Revenue, S2. Services as % of Total Revenue

#### Q2. Service Code Audit

- **Question:** Có mã dịch vụ discontinued nào tái xuất hiện không? Có mã mới nào chưa được phân loại?
- **Definition:** Audit tất cả DV* + CPBH codes trong sổ MISA — phân loại ACTIVE / Low Activity / DISCONTINUED dựa trên last invoice date.
- **Nature:** Compliance, data quality.
- **Why It Matters:** Kế toán nhầm mã (vd dùng DVRENTAL cho hợp đồng mới) sẽ khiến P&L bị phân loại sai.
- **Tradeoffs / Caveats:** "DISCONTINUED" chỉ là trạng thái quan sát từ data — không có flag chính thức trong MISA.
- **Insight / Action Enabled:** Nếu mã discontinued tái xuất hiện → xác nhận với kế toán trước khi báo cáo.
- **Related Metrics:** S3. Service Type Breakdown

### Metrics

#### S1. Services Revenue

> **dbt Model:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)

- **Business Definition:** Tổng doanh thu từ các dòng dịch vụ (DV* + CPBH) trong kỳ. Bao gồm cả CPBH điều chỉnh âm — tổng có thể thấp hơn DV* alone nếu CPBH spike. Không bao gồm COGS vì services không có giá vốn.
- **Logic (SQL):**
  ```sql
  SELECT COALESCE(SUM(revenue_net_of_discount), 0) AS services_revenue
  FROM int_misa_sales_lines
  WHERE is_service_line = true
  ```
- **Formula:** SUM(revenue_net_of_discount) WHERE is_service_line = true
- **Unit:** VND
- **Common Misunderstandings:** Đừng dùng gross_profit = services_revenue để so sánh gross margin % với hàng hóa — hàng hóa có COGS ~54%, services = 100% contribution (zero COGS). Các số này không comparable.
- **Pitfalls / Edge Cases:** CPBH entries có giá trị âm — tổng services_revenue thấp hơn tổng DV* codes alone. Check cả hai.

#### S2. Services as % of Total Revenue

> **dbt Model:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)

- **Business Definition:** Tỷ lệ doanh thu dịch vụ trong tổng doanh thu MISA (DV* + hàng hóa). Đo mức độ đóng góp của mảng dịch vụ vào top-line. Baseline: ~9-10% (2.4B / ~26B total).
- **Logic (SQL):**
  ```sql
  SELECT
      ROUND(
          SUM(CASE WHEN is_service_line THEN revenue_net_of_discount ELSE 0 END) * 100.0
          / NULLIF(SUM(revenue_net_of_discount), 0),
          1
      ) AS services_pct_of_total
  FROM int_misa_sales_lines
  ```
- **Formula:** SUM(services revenue) / SUM(total revenue) × 100
- **Unit:** %
- **Common Misunderstandings:** % tăng không nhất thiết là services tăng — có thể do hàng hóa giảm. Luôn xem cả numerator lẫn denominator.
- **Pitfalls / Edge Cases:** Dùng tháng đóng (tháng trước) để tính % — MTD có thể distort nếu services xuất HĐ cuối tháng.

#### S3. Service Type Breakdown

> **dbt Model:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)

- **Business Definition:** Phân bổ doanh thu theo từng service code trong kỳ. Phân loại ACTIVE (HĐ cuối < 3 tháng), Low Activity (3-12 tháng), DISCONTINUED (> 12 tháng).
- **Logic (SQL):**
  ```sql
  SELECT
      product_code,
      product_name,
      MAX(posting_date) AS last_invoice_date,
      COALESCE(SUM(revenue_net_of_discount), 0) AS revenue_12m,
      CASE
          WHEN MAX(posting_date) >= current_date - INTERVAL '3 months'  THEN 'ACTIVE'
          WHEN MAX(posting_date) >= current_date - INTERVAL '12 months' THEN 'Low Activity'
          ELSE 'DISCONTINUED'
      END AS status
  FROM int_misa_sales_lines
  WHERE is_service_line = true
  GROUP BY 1, 2
  ORDER BY revenue_12m DESC
  ```
- **Formula:** GROUP BY product_code, flag status by last_invoice_date recency
- **Unit:** VND per code
- **Common Misunderstandings:** DVCCNS và DVCCNS1 là 2 codes khác nhau nhưng cùng bản chất (US HR staffing). Không cộng dồn trừ khi muốn xem tổng US HR.
- **Pitfalls / Edge Cases:** Mã mới chưa có trong danh sách sẽ tự động xuất hiện khi `is_service_line` flag pick up theo regex DV* / CPBH*. Review hàng quý.

#### S4. CPBH Adjustments

> **dbt Model:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)

- **Business Definition:** Các dòng điều chỉnh Chi phí bán hàng khác (CPBH) — thường là giá trị âm, là reversals hoặc credit notes. Không phải "doanh thu thực" mà là kế toán adjustments. Alert nếu tháng bất kỳ > -100M VND.
- **Logic (SQL):**
  ```sql
  SELECT
      date_trunc('month', posting_date) AS month,
      COUNT(*) AS line_count,
      COALESCE(SUM(revenue_net_of_discount), 0) AS cpbh_adjustment
  FROM int_misa_sales_lines
  WHERE product_code LIKE 'CPBH%'
  GROUP BY 1
  ORDER BY 1 DESC
  ```
- **Formula:** SUM(revenue_net_of_discount) WHERE product_code LIKE 'CPBH%'
- **Unit:** VND (typically negative)
- **Threshold:** Alert if cpbh_adjustment < -100,000,000 VND in any month
- **Common Misunderstandings:** CPBH không phải COGS và không phải operating expense — là accounting adjustment. Không dùng trong margin calculation.
- **Pitfalls / Edge Cases:** Một số tháng có CPBH = 0 (bình thường). Spike âm lớn thường do credit note lớn từ 1 khách hàng.

### Known Service Codes (as of 2026-05)

| Code | Name | Status | Revenue (12M) | Notes |
|------|------|--------|---------------|-------|
| `DVCCNS1` | Phí dịch vụ cung cấp nhân sự cho US (FGO) | **ACTIVE** | 1.30B VND | Primary US HR code từ 2024+ |
| `DVCCNS` | Phí dịch vụ cung cấp nhân sự cho US | **ACTIVE** | 1.12B VND | Original US HR code |
| `DVVC` | Dịch vụ vận chuyển | Low Activity | 0.6M VND | Last seen 2025-10 |
| `CPBH` | Chi phí bán hàng khác (adjustments) | Low Activity | -58.5M VND | Negative adjustments |
| `DVRENTAL` | Thuê văn phòng | DISCONTINUED | 0 (12M) | Last 2022-12 |
| `DVDIEN` | Tiền điện văn phòng | DISCONTINUED | 0 (12M) | Last 2022-12 |
| `DVGX` | Giặt xấy văn phòng | DISCONTINUED | 0 (12M) | Last 2022-12 |
| `DVQL` | Phí quản lý văn phòng | DISCONTINUED | 0 (12M) | Last 2022-12 |
| `DVNUOC` | Tiền nước văn phòng | DISCONTINUED | 0 (12M) | Last 2022-12 |
| `DVVS` | Vệ sinh văn phòng | DISCONTINUED | 0 (12M) | Last 2022-12 |
| `DVDT1` | Thiết bị phóng cao áp (one-off) | DISCONTINUED | 0 (12M) | Last 2022-06, 1.29B one-off |

## Related Dashboards

| Dashboard | Audience | Purpose | Link |
|:---|:---|:---|:---|
| **Finance Services Revenue** | CFO, Finance Manager | Monthly services revenue tracking (DV* + CPBH) | [Playbook](../playbooks/finance_services_revenue.md) |
| **Finance P&L Dashboard** | CFO, Finance | Monthly P&L: revenue vs COGS vs margin | [Playbook](../playbooks/finance_pl.md) |
| **Channel Profitability Monthly** | CEO, Finance, Sales Director | Cross-channel margin comparison | [Playbook](../playbooks/channel_profitability_monthly.md) |
| **Shopee Channel Economics** | Sales Ops, CS Lead | Shopee fee structure & settlement analysis | [Playbook](../playbooks/shopee_channel_economics.md) |
| **Product Performance** | Merchandising | Product margin using MISA COGS | [Playbook](../playbooks/product_performance.md) |
| **Order Profitability** | CEO, Finance, Sales Ops | Per-order P&L: revenue - COGS - platform fees | [Playbook](../playbooks/order_profitability.md) |
| **Cost Ledger Analyzer** | CFO, Accounting | Cost breakdown by type (COGS / fees / vouchers) | *Phase 05 — see [phase-05](../../../plans/260527-1327-metabase-collection-restructure/phase-05-new-finance-dashboards.md)* |
| **Return Impact Analysis** | CEO, CFO, Sales Ops | Refund liability + return rate trends | *Phase 05* |
| **Channel P&L Deep Dive** | Finance Director | Loss-leader detection via channel margin waterfall | *Phase 05* |
| **Product Cost-to-Margin Heatmap** | Merchandising, Finance | SKU margin with COGS variance | *Phase 05* |
| **Accounting Reconciliation Cockpit** | Accounting, CFO | Daily Sapo↔MISA↔Shopee recon | [Playbook](../playbooks/finance_accounting_recon.md) |
