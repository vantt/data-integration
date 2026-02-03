# 📊 Reports & Metrics Index

> [!NOTE]
> This document has been refactored. Detailed metrics definitions and SQL implementation playbooks have been moved to the `docs/metabase-workspace/` directory to separate business logic from technical implementation.

## 🗂 Metric Playbooks

| Playbook                                                          | Description                                                     | Key Metrics Covered                                               |
| :---------------------------------------------------------------- | :-------------------------------------------------------------- | :---------------------------------------------------------------- |
| **[Sales Analytics](metabase-workspace/sales-playbook.md)**       | Daily operations, channel performance, and executive reporting. | GMV, AOV, Conversion Rate, Revenue by Channel, Sales by Location. |
| **[Customer Analytics](metabase-workspace/customer-playbook.md)** | Segmentation, retention, and lifetime value analysis.           | CLV, CAC, Churn Rate, Retention Rate, RFM Segments.               |
| **[Product Analytics](metabase-workspace/product-playbook.md)**   | Product performance, inventory health, and merchandising.       | Units Sold, Inventory Turnover, Sell-through Rate, Stock Alerts.  |
| **[Finance Analytics](metabase-workspace/finance-playbook.md)**   | Financial reporting, P&L, and cash flow.                        | Gross Margin, EBITDA, Cash Flow, Revenue Waterfall.               |

## 📚 Quick Reference: Common Metrics

Use this table for quick lookups. For SQL queries and visualization settings, click the **Playbook** link.

### Revenue & Sales

| Metric             | Definition                                   | Playbook                                          |
| :----------------- | :------------------------------------------- | :------------------------------------------------ |
| **GMV**            | `SUM(order_total)` (Gross Merchandise Value) | [Sales](metabase-workspace/sales-playbook.md)     |
| **Net Revenue**    | `GMV - Returns - Discounts`                  | [Sales](metabase-workspace/sales-playbook.md)     |
| **AOV**            | `Total Revenue / Number of Orders`           | [Sales](metabase-workspace/sales-playbook.md)     |
| **Revenue Growth** | `(Current - Previous) / Previous * 100%`     | [Finance](metabase-workspace/finance-playbook.md) |

### Customer & Marketing

| Metric             | Definition                                | Playbook                                            |
| :----------------- | :---------------------------------------- | :-------------------------------------------------- |
| **CAC**            | `Marketing Spend / New Customers`         | [Customer](metabase-workspace/customer-playbook.md) |
| **CLV**            | `AOV * Purchase Freq * Customer Lifespan` | [Customer](metabase-workspace/customer-playbook.md) |
| **Churn Rate**     | `Lost Customers / Total Customers * 100%` | [Customer](metabase-workspace/customer-playbook.md) |
| **Retention Rate** | `((CE-CN)/CS) * 100%`                     | [Customer](metabase-workspace/customer-playbook.md) |

### Product & Inventory

| Metric                 | Definition                              | Playbook                                          |
| :--------------------- | :-------------------------------------- | :------------------------------------------------ |
| **Inventory Turnover** | `COGS / Average Inventory`              | [Product](metabase-workspace/product-playbook.md) |
| **Sell-through Rate**  | `Units Sold / (Start Stock + Received)` | [Product](metabase-workspace/product-playbook.md) |
| **Gross Margin**       | `(Revenue - COGS) / Revenue`            | [Finance](metabase-workspace/finance-playbook.md) |
| **Return Rate**        | `Returns / Total Orders`                | [Sales](metabase-workspace/sales-playbook.md)     |
