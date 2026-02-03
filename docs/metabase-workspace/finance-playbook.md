# Finance Analytics Playbook

## 🎯 Overview

This playbook covers financial analytics and reporting needs:

- **P&L Dashboard** → [finance-blueprint-pl.md] _(coming soon)_
- **Cash Flow Analysis** → [finance-blueprint-cashflow.md] _(coming soon)_
- **Financial KPIs** → [finance-blueprint-executive.md] _(coming soon)_

## 📊 Business Context

### Target Users

- **CFO/Finance Directors**: Strategic financial overview
- **Finance Managers**: Operational financial metrics
- **Accounting Team**: Transaction-level details
- **Department Heads**: Budget tracking and variance

### Update Frequency

- **Real-time**: Cash position, payment status
- **Daily**: Revenue recognition, expense tracking
- **Monthly**: P&L statements, budget variance
- **Quarterly**: Financial ratios, trend analysis

## 🎯 Key Financial Metrics

### Revenue Metrics

| Metric                   | Formula                                | Business Rule       | Target        |
| ------------------------ | -------------------------------------- | ------------------- | ------------- |
| **Gross Revenue**        | SUM(invoice_amount)                    | All issued invoices | Per budget    |
| **Net Revenue**          | Gross Revenue - Returns - Allowances   | Recognized revenue  | >95% of gross |
| **Revenue Growth**       | (Current - Previous) / Previous × 100% | YoY comparison      | >20%          |
| **Revenue per Employee** | Net Revenue / FTE Count                | Productivity metric | >$200k        |

### Profitability Metrics

| Metric               | Formula                           | Business Rule          | Target   |
| -------------------- | --------------------------------- | ---------------------- | -------- |
| **Gross Margin**     | (Revenue - COGS) / Revenue × 100% | Product profitability  | >40%     |
| **Operating Margin** | EBIT / Revenue × 100%             | Operational efficiency | >15%     |
| **Net Margin**       | Net Income / Revenue × 100%       | Bottom line profit     | >10%     |
| **EBITDA**           | Earnings + Interest + Tax + D&A   | Cash generation        | Positive |

### Liquidity Metrics

| Metric                     | Formula                                            | Business Rule              | Target   |
| -------------------------- | -------------------------------------------------- | -------------------------- | -------- |
| **Current Ratio**          | Current Assets / Current Liabilities               | Short-term health          | >1.5     |
| **Quick Ratio**            | (Current Assets - Inventory) / Current Liabilities | Immediate liquidity        | >1.0     |
| **Cash Conversion Cycle**  | DIO + DSO - DPO                                    | Working capital efficiency | <45 days |
| **Days Sales Outstanding** | (AR / Revenue) × 365                               | Collection efficiency      | <30 days |

## 📈 Dashboard Designs

### 1. P&L Dashboard

**Purpose**: Monthly P&L analysis with drill-down capability

**Layout**:

```
┌─────────────────────────┬─────────────────────────┐
│ Revenue YTD (Scalar)    │ Profit YTD (Scalar)     │
├─────────────────────────┴─────────────────────────┤
│ Monthly P&L Trend (Waterfall Chart)               │
├─────────────────────────┬─────────────────────────┤
│ Revenue by Category     │ Expense Breakdown       │
│ (Stacked Bar)          │ (Treemap)               │
└─────────────────────────┴─────────────────────────┘
```

### 2. Cash Flow Dashboard

**Purpose**: Track cash movements and forecast

**Layout**:

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ Cash Balance│ AR Balance  │ AP Balance  │ Burn Rate   │
├─────────────┴─────────────┴─────────────┴─────────────┤
│ Daily Cash Movement (Line + Bar Combo)                │
├───────────────────────────────────────────────────────┤
│ Cash Flow Forecast     │ Aging Analysis (Heatmap)     │
└────────────────────────┴──────────────────────────────┘
```

## 💾 Data Requirements

### Source Tables

| Table             | Update Frequency | Key Fields                 | Data Quality Checks |
| ----------------- | ---------------- | -------------------------- | ------------------- |
| `fact_gl_entries` | Real-time        | account_id, amount, date   | Debits = Credits    |
| `dim_accounts`    | Daily            | account_id, type, category | Valid hierarchy     |
| `fact_invoices`   | Real-time        | invoice_id, amount, status | No negative amounts |
| `fact_payments`   | Real-time        | payment_id, amount, method | Match to invoices   |

## 🔧 SQL Library

### Monthly P&L Query

```sql
-- P&L by month with comparisons
WITH monthly_pl AS (
    SELECT
        DATE_TRUNC('month', entry_date) as month,
        a.account_type,
        a.account_category,
        SUM(CASE
            WHEN a.account_type = 'Revenue' THEN -g.amount
            ELSE g.amount
        END) as amount
    FROM fact_gl_entries g
    JOIN dim_accounts a ON g.account_id = a.account_id
    WHERE a.is_pl_account = true
    GROUP BY 1, 2, 3
)
SELECT
    month,
    SUM(CASE WHEN account_type = 'Revenue' THEN amount ELSE 0 END) as revenue,
    SUM(CASE WHEN account_category = 'COGS' THEN amount ELSE 0 END) as cogs,
    SUM(CASE WHEN account_category = 'Operating' THEN amount ELSE 0 END) as opex,
    SUM(CASE WHEN account_category = 'Other' THEN amount ELSE 0 END) as other,
    SUM(amount) as net_income
FROM monthly_pl
GROUP BY month
ORDER BY month DESC;
```

### Year-over-Year Growth

```sql
SELECT
    EXTRACT(MONTH FROM created_on) as month,
    EXTRACT(YEAR FROM created_on) as year,
    SUM(total) as revenue,
    LAG(SUM(total)) OVER (PARTITION BY EXTRACT(MONTH FROM created_on)
                          ORDER BY EXTRACT(YEAR FROM created_on)) as prev_year_revenue,
    (SUM(total) - LAG(SUM(total)) OVER (PARTITION BY EXTRACT(MONTH FROM created_on)
                                        ORDER BY EXTRACT(YEAR FROM created_on))) * 100.0 /
    NULLIF(LAG(SUM(total)) OVER (PARTITION BY EXTRACT(MONTH FROM created_on)
                                  ORDER BY EXTRACT(YEAR FROM created_on)), 0) as yoy_growth
FROM fact_orders
GROUP BY month, year
ORDER BY year, month;
```

### Cash Flow Analysis

```sql
-- Daily cash movements
WITH cash_movements AS (
    SELECT
        DATE(payment_date) as date,
        SUM(CASE WHEN type = 'inflow' THEN amount ELSE 0 END) as cash_in,
        SUM(CASE WHEN type = 'outflow' THEN amount ELSE 0 END) as cash_out
    FROM fact_payments
    WHERE payment_date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY DATE(payment_date)
)
SELECT
    date,
    cash_in,
    cash_out,
    cash_in - cash_out as net_movement,
    SUM(cash_in - cash_out) OVER (
        ORDER BY date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) as running_balance
FROM cash_movements
ORDER BY date;
```

### Working Capital Metrics

```sql
-- Key working capital ratios
WITH current_balances AS (
    SELECT
        SUM(CASE WHEN account_type = 'Current Asset' THEN balance ELSE 0 END) as current_assets,
        SUM(CASE WHEN account_type = 'Inventory' THEN balance ELSE 0 END) as inventory,
        SUM(CASE WHEN account_type = 'Current Liability' THEN balance ELSE 0 END) as current_liabilities,
        SUM(CASE WHEN account_code = 'AR' THEN balance ELSE 0 END) as accounts_receivable,
        SUM(CASE WHEN account_code = 'AP' THEN balance ELSE 0 END) as accounts_payable
    FROM fact_account_balances
    WHERE balance_date = CURRENT_DATE
),
revenue_metrics AS (
    SELECT
        SUM(amount) / 365 as daily_revenue,
        SUM(cogs) / 365 as daily_cogs
    FROM fact_revenue
    WHERE date >= CURRENT_DATE - INTERVAL '365 days'
)
SELECT
    ROUND(current_assets / NULLIF(current_liabilities, 0), 2) as current_ratio,
    ROUND((current_assets - inventory) / NULLIF(current_liabilities, 0), 2) as quick_ratio,
    ROUND(accounts_receivable / NULLIF(daily_revenue, 0), 0) as days_sales_outstanding,
    ROUND(accounts_payable / NULLIF(daily_cogs, 0), 0) as days_payables_outstanding,
    ROUND(inventory / NULLIF(daily_cogs, 0), 0) as days_inventory_outstanding
FROM current_balances, revenue_metrics;
```

## 🚀 Implementation Notes

### Best Practices

1. **Accrual Basis**: Ensure all metrics follow accrual accounting
2. **Period Consistency**: Use consistent period boundaries
3. **Currency Handling**: Convert to reporting currency
4. **Audit Trail**: Maintain source transaction references

### Common Pitfalls

- Mixing cash and accrual basis metrics
- Not handling refunds/returns properly
- Ignoring inter-company eliminations
- Using wrong FX rates for conversion

### Performance Tips

- Pre-aggregate GL entries by period
- Index on account_id, entry_date
- Materialize monthly P&L views
- Partition large transaction tables

## 📚 Related Resources

- [Sales Analytics Playbook](sales-playbook.md)
- [Accounting Best Practices](guides/accounting-standards.md)
- [Financial Ratios Guide](guides/financial-ratios.md)

## 🔄 Change Log

- 2024-02: Initial version
- 2024-03: Added cash flow forecasting
