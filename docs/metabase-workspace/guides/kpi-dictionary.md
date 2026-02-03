# Metabase KPI Dictionary

## 📖 Introduction

This dictionary serves as the single source of truth for all metric definitions across the organization. All SQL queries and dashboard calculations must align with these formulas.

## 💰 Revenue Metrics

| Metric                            | Formula                                  | Description                                                                           | Data Source                   |
| --------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------- | ----------------------------- |
| **GMV (Gross Merchandise Value)** | `SUM(order_total)`                       | Total value of merchandise sold over a given period of time. Includes taxes/shipping. | `fact_orders`                 |
| **Net Revenue**                   | `GMV - Returns - Discounts`              | The actual revenue generated after all deductions.                                    | `fact_orders`, `fact_returns` |
| **Average Order Value (AOV)**     | `Total Revenue / Number of Orders`       | The average amount spent each time a customer places an order.                        | `fact_orders`                 |
| **Revenue per Customer**          | `Total Revenue / Unique Customers`       | The average revenue generated per unique customer.                                    | `fact_orders`                 |
| **Revenue Growth Rate**           | `(Current - Previous) / Previous × 100%` | The percentage increase or decrease in revenue over time.                             | Calculated                    |

## 👥 Customer Metrics

| Metric                              | Formula                                   | Description                                                                | Data Source                 |
| ----------------------------------- | ----------------------------------------- | -------------------------------------------------------------------------- | --------------------------- |
| **Customer Lifetime Value (CLV)**   | `AOV × Purchase Frequency × Lifespan`     | The total expected revenue from a customer over their entire relationship. | `dim_customers`             |
| **Customer Acquisition Cost (CAC)** | `Marketing Spend / New Customers`         | The cost associated with acquiring a new customer.                         | Marketing + `dim_customers` |
| **Churn Rate**                      | `Lost Customers / Total Customers × 100%` | The percentage of customers who stop doing business during a period.       | `dim_customers`             |
| **Retention Rate**                  | `((CE-CN)/CS) × 100%`                     | The percentage of customers a company retains over a given period.         | `dim_customers`             |
| **Net Promoter Score (NPS)**        | `% Promoters - % Detractors`              | Customer loyalty and satisfaction measurement.                             | Survey Data                 |

## 🚀 Operational Metrics

| Metric                     | Formula                                  | Description                                                               | Data Source         |
| -------------------------- | ---------------------------------------- | ------------------------------------------------------------------------- | ------------------- |
| **Order Fulfillment Rate** | `Fulfilled Orders / Total Orders × 100%` | The percentage of orders that are successfully filled.                    | `fact_fulfillments` |
| **Average Delivery Time**  | `AVG(Delivered Date - Order Date)`       | The average time it takes for an order to be delivered.                   | `fact_shipments`    |
| **Return Rate**            | `Returns / Total Orders × 100%`          | The percentage of orders that result in a return.                         | `fact_returns`      |
| **Inventory Turnover**     | `COGS / Average Inventory`               | How many times a company has sold and replaced inventory during a period. | `fact_inventory`    |
| **Out of Stock Rate**      | `OOS Products / Total Products × 100%`   | The percentage of products that are currently out of stock.               | `dim_products`      |

## 🛒 Conversion & Traffic Metrics

| Metric                    | Formula                           | Description                                                             | Data Source            |
| ------------------------- | --------------------------------- | ----------------------------------------------------------------------- | ---------------------- |
| **Conversion Rate**       | `Orders / Visitors × 100%`        | The percentage of visitors who complete a desired action (purchase).    | GA4 / `fact_orders`    |
| **Cart Abandonment Rate** | `Abandoned / Created × 100%`      | The percentage of shopping carts where the user left before purchasing. | `fact_orders` (drafts) |
| **Order Frequency**       | `Orders / Customers`              | How often customers purchase on average.                                | `fact_orders`          |
| **Repeat Purchase Rate**  | `Repeat Cust / Total Cust × 100%` | The percentage of customers who have made more than one purchase.       | `fact_orders`          |
