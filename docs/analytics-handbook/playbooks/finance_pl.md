# Playbook: Finance P&L Dashboard

## Overview

- **Audience:** CFO, Finance Managers
- **Goal:** Monthly Profit & Loss analysis with drill-down capability.
- **Metabase Collection:** `Finance Analytics`

## Filters

- **Date Range:** Month-to-Date (MTD), Year-to-Date (YTD).
- **Cost Center / Department:** Optional filter.

## Visualizations

### Section 1: Top Line

| Chart Title     | Visualization Type | Metric Reference (Link to Domain)                   | Notes/Config                             |
| :-------------- | :----------------- | :-------------------------------------------------- | :--------------------------------------- |
| **Revenue YTD** | Scalar             | [Net Revenue](../domains/finance.md#2-net-revenue)  | Filter: YTD                              |
| **Profit YTD**  | Scalar             | [Net Margin %](../domains/finance.md#5-net-margin-) | Display absolute Net Income or Margin %. |

### Section 2: Trends & Breakdowns

| Chart Title             | Visualization Type | Metric Reference (Link to Domain)                               | Notes/Config                                                |
| :---------------------- | :----------------- | :-------------------------------------------------------------- | :---------------------------------------------------------- |
| **Monthly P&L Trend**   | Waterfall Chart    | [Net Revenue](../domains/finance.md#2-net-revenue)              | Breakdown by Revenue, COGS, Opex, Other to show Net Income. |
| **Revenue by Category** | Stacked Bar        | [Gross Revenue](../domains/finance.md#1-gross-revenue)          | Group by Category (Product/Service).                        |
| **Expense Breakdown**   | Treemap            | [Operating Margin %](../domains/finance.md#4-operating-margin-) | Breakdown Operating Expenses by Account Category.           |

## Implementation Notes

### Best Practices

1. **Accrual Basis**: Ensure all metrics follow accrual accounting.
2. **Period Consistency**: Use consistent period boundaries for P&L.
3. **Currency Handling**: Convert to reporting currency using valid FX rates.
4. **Audit Trail**: Maintain source transaction references.

### Common Pitfalls

- Mixing cash and accrual basis metrics.
- Not handling refunds/returns properly in Net Revenue.
- Ignoring inter-company eliminations.
