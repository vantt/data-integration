# Finance Domain

> **Owner:** CFO / Finance Team
> **Update Frequency:** Daily / Monthly

## Context: Profit & Loss (P&L) — Sapo Revenue

> **Description:** Revenue-side P&L metrics from Sapo order data. COGS/expense metrics require MISA context below.
> **dbt Source:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)
> **Grain:** Per Order / Monthly

### 1. Gross Revenue (GMV)

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Tổng giá trị hàng hóa theo giá bán, trước chiết khấu.
- **Logic (SQL):**
  ```sql
  SUM(gross_revenue)
  ```
- **Source Mapping:**
  - **Table:** `fact_orders`
  - **Field:** `gross_revenue` (Sum)

### 2. Net Revenue

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Doanh thu thuần — sau chiết khấu, trước thuế.
- **Logic (SQL):**
  ```sql
  SUM(net_revenue)
  ```

### 3. Revenue Breakdown (Waterfall Components)

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Components of revenue flow for waterfall chart.
- **Logic (SQL):**
  ```sql
  SELECT 'Gross Revenue' AS component, SUM(gross_revenue) AS amount FROM fact_orders WHERE status NOT IN ('CANCELLED','Voided')
  UNION ALL SELECT 'Discounts', -SUM(discount_amount) FROM fact_orders WHERE status NOT IN ('CANCELLED','Voided')
  UNION ALL SELECT 'Tax', SUM(tax_amount) FROM fact_orders WHERE status NOT IN ('CANCELLED','Voided')
  UNION ALL SELECT 'Net Revenue', SUM(net_revenue) FROM fact_orders WHERE status NOT IN ('CANCELLED','Voided')
  ```

## Context: COGS & Margin — MISA Sales Ledger

> **Description:** Cost of Goods Sold and gross margin from MISA AMIS accounting system. Per-invoice-line grain with product-level COGS. Covers all channels (DAILY, ECOM, CS, KHAC).
> **dbt Source:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)
> **Grain:** Per Invoice Line
> **Channel Classification:** `channel_code` (DAILY=Bán lẻ tại quầy, ECOM=Thương mại điện tử, CS=Công sở/B2B, KHAC=Khác) + `voucher_source_hint` (SAPO_DEALER, SHOPEE, AEON, OTHER)

### 4. COGS (Giá vốn hàng bán)

> **dbt Model:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)

- **Business Definition:** Giá vốn hàng bán — chi phí mua hàng tương ứng với doanh thu đã ghi nhận. Lấy từ sổ chi tiết bán hàng MISA.
- **Logic (SQL):**
  ```sql
  SUM(cogs_amount)
  ```
- **Source Mapping:**
  - **Table:** `int_misa_sales_lines`
  - **Field:** `cogs_amount` (Sum)

### 5. Gross Profit (Lãi gộp)

> **dbt Model:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)

- **Business Definition:** Doanh thu thuần trừ giá vốn. Cho biết lợi nhuận trước chi phí vận hành.
- **Logic (SQL):**
  ```sql
  SUM(gross_profit)
  -- equivalent: SUM(revenue_net_of_discount) - SUM(cogs_amount)
  ```

### 6. Gross Margin % (Biên lợi nhuận gộp)

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

### 7. Gross Margin by Channel

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

### 8. COGS Ratio (Tỷ lệ giá vốn/doanh thu)

> **dbt Model:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)

- **Business Definition:** Phần trăm doanh thu bị giá vốn chiếm — nghịch đảo của Gross Margin.
- **Logic (SQL):**
  ```sql
  SUM(cogs_amount) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0) AS cogs_ratio
  ```

## Context: Order-Level Profitability

> **Description:** Per-order P&L combining Sapo revenue, MISA COGS, and Shopee platform fees. Enables profitability analysis by channel, customer, staff, geography.
> **dbt Source:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)
> **Grain:** Per Order
> **Join Keys:** `voucher_no` (MISA) = `order_code` (Sapo) = `order_code` (Shopee fees)
> **Coverage:** ~65% of completed orders in MISA date range (cancelled/draft orders excluded from MISA)

### 9. Order Gross Profit (Lãi gộp đơn hàng)

> **dbt Model:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)

- **Business Definition:** Lãi gộp = Doanh thu thuần - Giá vốn. Tính per-order, join MISA COGS vào Sapo revenue.
- **Logic (SQL):**
  ```sql
  SELECT order_code, net_revenue, cogs_amount, gross_profit, gross_margin_pct
  FROM fact_order_economics
  WHERE has_cogs  -- chỉ đơn có dữ liệu COGS từ MISA
  ```

### 10. Channel Net Profit (Lãi ròng kênh)

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

### P&L Metrics — Planned (requires `fact_gl_entries`)

> **Status: Planned** — Metrics below require General Ledger integration. Operating expenses, depreciation, interest are not yet available.

### 11. Operating Margin %

- **Business Definition:** Operating Income (EBIT) as a percentage of Revenue. Requires GL OpEx data.
- **Status:** Planned — `fact_gl_entries` not yet built.

### 12. Net Margin %

- **Business Definition:** Net Income as a percentage of Revenue. Requires full GL.
- **Status:** Planned — `fact_gl_entries` not yet built.

### 13. EBITDA

- **Business Definition:** Earnings Before Interest, Taxes, Depreciation, and Amortization. Requires full GL.
- **Status:** Planned — `fact_gl_entries` not yet built.

## Context: Shopee Platform Economics

> **Description:** Shopee channel fee structure, net settlement, and platform margin. Dùng để phân tích chi phí bán hàng trên Shopee và tối ưu lợi nhuận kênh.
> **dbt Source:** [`int_shopee_order_fees`](../../../transformation/models/intermediate/shopee/int_shopee_order_fees.sql)
> **Grain:** Per Shopee Order
> **Note:** Only covers orders with released payouts (payout_released_at IS NOT NULL).

### 12. Shopee Net Settlement (Tổng phát hành)

> **dbt Model:** [`int_shopee_order_fees`](../../../transformation/models/intermediate/shopee/int_shopee_order_fees.sql)

- **Business Definition:** Số tiền Shopee thực chuyển về seller sau khi trừ toàn bộ phí, thuế, hoàn hàng. Khớp với cột "Tổng phát hành" trên Shopee Seller Center.
- **Logic (SQL):**
  ```sql
  SUM(net_settlement)
  ```

### 13. Shopee Platform Fee Rate (Tỷ lệ phí sàn)

> **dbt Model:** [`int_shopee_order_fees`](../../../transformation/models/intermediate/shopee/int_shopee_order_fees.sql)

- **Business Definition:** Tổng phí sàn Shopee trên doanh thu — bao gồm service fee, payment fee, fixed fee, infrastructure fee, voucher Xtra.
- **Logic (SQL):**
  ```sql
  (SUM(ABS(service_fee)) + SUM(ABS(payment_fee)) + SUM(ABS(fixed_fee))
   + SUM(infrastructure_fee) + SUM(voucher_xtra_fee))
  * 100.0 / NULLIF(SUM(gross_revenue), 0) AS platform_fee_rate_pct
  ```

### 14. Shopee Fee Breakdown

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

### 15. Shopee Settlement Margin (Biên lợi nhuận sàn)

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

## Context: Balance Sheet & Liquidity — Planned

> **Status: Planned** — Requires `fact_account_balances` (not yet built).
> **Description:** Health of the business and cash position.
> **dbt Source:** `fact_account_balances`

### 16. Current Ratio

- **Business Definition:** Ability to pay short-term obligations (Assets / Liabilities).
- **Status:** Planned — `fact_account_balances` not yet built.

### 17. Quick Ratio

- **Business Definition:** Measure of immediate liquidity.
- **Status:** Planned — `fact_account_balances` not yet built.

### 18. Days Sales Outstanding (DSO)

- **Business Definition:** Average number of days to collect payment after a sale.
- **Logic (SQL):**
  ```sql
  (Accounts_Receivable / Annual_Revenue) * 365
  ```
- **Status:** Planned — `fact_account_balances` not yet built.

## Context: Cash Flow

> **Description:** Cash movement tracking.
> **dbt Source:** [`fact_payments`](../../../transformation/models/marts/sales/fact_payments.sql)

### 19. Net Cash Flow

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

## Related Dashboards

| Dashboard | Audience | Purpose | Link |
|:---|:---|:---|:---|
| **Finance P&L Dashboard** | CFO, Finance | Monthly P&L: revenue vs COGS vs margin | [Playbook](../playbooks/finance_pl.md) |
| **Channel Profitability Monthly** | CEO, Finance, Sales Director | Cross-channel margin comparison | [Playbook](../playbooks/channel_profitability_monthly.md) |
| **Shopee Channel Economics** | Sales Ops, CS Lead | Shopee fee structure & settlement analysis | [Playbook](../playbooks/shopee_channel_economics.md) |
| **Product Performance** | Merchandising | Product margin using MISA COGS | [Playbook](../playbooks/product_performance.md) |
| **Order Profitability** | CEO, Finance, Sales Ops | Per-order P&L: revenue - COGS - platform fees | *Planned* |
