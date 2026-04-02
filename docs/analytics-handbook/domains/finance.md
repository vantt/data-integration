# Finance Domain

> **Owner:** CFO / Finance Team
> **Update Frequency:** Daily / Monthly

## Context: Profit & Loss (P&L)

> **Description:** Profitability and Income Statement metrics.
> **dbt Source:** `fact_gl_entries`
> **Grain:** Monthly / Daily

### 1. Gross Revenue

> **dbt Model:** `fact_invoices` (Planned)

- **Business Definition:** Total invoice amount issued.
- **Logic (SQL):**
  ```sql
  SUM(invoice_amount)
  ```
- **Source Mapping:**
  - **Table:** `fact_invoices`
  - **Field:** `Amount` (Sum)

### 2. Net Revenue

> **dbt Model:** `fact_gl_entries` (Planned)

- **Business Definition:** Gross Revenue minus Returns and Allowances. Recognized revenue.
- **Logic (SQL):**
  ```sql
  -- P&L Logic
  SUM(CASE
  WHEN account_type = 'Revenue' THEN -amount -- Credit balances are negative in some systems, adjust as needed
  ELSE amount
  END)
  ```

### 3. Revenue Breakdown (Waterfall Components)

> **dbt Model:** [fact_orders](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Components of revenue flow for waterfall chart.
- **Logic (SQL):**
  ```sql
  SELECT 'Gross Revenue', SUM(total) FROM orders
  UNION ALL SELECT 'Discounts', -SUM(total_discount) FROM orders
  UNION ALL SELECT 'Returns', -SUM(refund_amount) FROM order_returns
  UNION ALL SELECT 'Tax', SUM(total_tax) FROM orders
  UNION ALL SELECT 'Shipping', SUM(delivery_fee) FROM fulfillments
  ```

### 4. Gross Margin %

> **dbt Model:** `fact_gl_entries` (Planned)

- **Business Definition:** Percentage of Revenue retained after COGS.
- **Logic (SQL):**
  ```sql
  (SUM(Revenue) - SUM(COGS)) / SUM(Revenue) * 100
  ```

### 5. Operating Margin %

> **dbt Model:** `fact_gl_entries` (Planned)

- **Business Definition:** Operating Income (EBIT) as a percentage of Revenue.
- **Logic (SQL):**
  ```sql
  -- EBIT / Revenue
  (SUM(Revenue) - SUM(COGS) - SUM(Opex)) / SUM(Revenue) * 100
  ```

### 6. Net Margin %

> **dbt Model:** `fact_gl_entries` (Planned)

- **Business Definition:** Net Income as a percentage of Revenue.
- **Logic (SQL):**
  ```sql
  SUM(Net_Income) / SUM(Revenue) * 100
  ```

### 7. EBITDA

> **dbt Model:** `fact_gl_entries` (Planned)

- **Business Definition:** Earnings Before Interest, Taxes, Depreciation, and Amortization.
- **Logic (SQL):**
  ```sql
  Net_Income + Interest + Taxes + Depreciation + Amortization
  ```

## Context: Balance Sheet & Liquidity

> **Description:** Health of the business and cash position.
> **dbt Source:** `fact_account_balances`

### 7. Current Ratio

- **Business Definition:** Ability to pay short-term obligations (Assets / Liabilities).
- **Logic (SQL):**
  SELECT
  SUM(CASE WHEN account_type = 'Current Asset' THEN balance ELSE 0 END) /
  NULLIF(SUM(CASE WHEN account_type = 'Current Liability' THEN balance ELSE 0 END), 0)
  FROM fact_account_balances

  ```

  ```

### 8. Quick Ratio

- **Business Definition:** Measure of immediate liquidity.
- **Logic (SQL):**
  ```sql
  (Current_Assets - Inventory) / Current_Liabilities
  ```

### 9. Days Sales Outstanding (DSO)

- **Business Definition:** Average number of days to collect payment after a sale.
- **Logic (SQL):**
  ```sql
  (Accounts_Receivable / Annual_Revenue) * 365
  ```

## Context: Cash Flow

> **Description:** Cash movement tracking.
> **dbt Source:** `fact_payments`

### 10. Net Cash Flow

- **Business Definition:** Difference between Cash Inflow and Cash Outflow.
- **Logic (SQL):**
  SELECT
  DATE(payment_date),
  SUM(CASE WHEN type = 'inflow' THEN amount ELSE 0 END) as cash_in,
  SUM(CASE WHEN type = 'outflow' THEN amount ELSE 0 END) as cash_out,
  (SUM(CASE WHEN type = 'inflow' THEN amount ELSE 0 END) -
  SUM(CASE WHEN type = 'outflow' THEN amount ELSE 0 END)) as net_movement
  FROM fact_payments
  GROUP BY 1

  ```

  ```
