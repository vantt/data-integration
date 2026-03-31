# Architecture Guide: dbt vs Metabase

This guide resolves the ambiguity between where to implement data logic vs. visualization logic, and how to ensure your Metabase configuration is backed up and reproducible.

## 1. The Core Philosophy: "Logic in dbt, Visualization in Metabase"

To avoid "logic drift" and ensure consistency, we follow this rule: **If a metric definition changes, you should only have to update it in dbt, not in 50 different Metabase charts.**

| Layer             | Tool         | Responsibilities                                                         | Example                                                             |
| :---------------- | :----------- | :----------------------------------------------------------------------- | :------------------------------------------------------------------ |
| **Data modeling** | **dbt**      | Cleaning, Joining, **Business Logic**, Complex Metrics, Privacy Masking. | Calculating `Net Revenue`, `Customer Lifespan`, `Session Duration`. |
| **Visualization** | **Metabase** | Aggregation (Sum/Avg), Grouping, Filtering, Formatting, Alerting.        | `SUM(net_revenue) GROUP BY month`, Red color if `< target`.         |

### ❌ Anti-Pattern (Logic in Metabase)

Writing this query in Metabase:

```sql
SELECT SUM(total - discount_amount - tax) as net_revenue FROM ...
```

_Why it's bad:_ If Finance decides "Net Revenue" shouldn't subtract tax, you have to find and fix this SQL in every single dashboard.

### ✅ Best Practice (Logic in dbt)

1.  **dbt (`fact_orders.sql`)**: Create the column once.
    ```sql
    ...
    (total_amount - total_discount - total_tax) as net_revenue,
    ...
    ```
2.  **Metabase**: Use the column.
    ```sql
    SELECT SUM(net_revenue) ...
    ```

## 2. Solving "Configuration Anxiety" (Infrastructure as Code)

You mentioned: _"I feel insecure doing this in Metabase because config might be lost."_

**Solution: The Playbook Architecture**

We use the **Metabase Automation Skill** to treat your `docs/metabase-workspace/*.md` files as the **Source of Truth**.

1.  **You write logic in Markdown**: You define Dashboards, Questions, and Charts in the `*.md` playbooks (as we have been doing).
2.  **Agent Deploys**: The Agent reads these files and calls the Metabase API to create them.
3.  **Safety**: If you wipe your Metabase container tomorrow, we simply re-run the Agent. **Your configuration is safe in Git**, not locked in Metabase's database.

## 3. Decision Matrix: Where does it go?

| Use Case                                           | Implementation Location      | Why?                                                 |
| :------------------------------------------------- | :--------------------------- | :--------------------------------------------------- |
| **Cleaning strings** (e.g. " Hanoi" -> "Hanoi")    | **dbt**                      | Do it once, everyone benefits.                       |
| **Joining Tables** (Orders + Customers)            | **dbt**                      | Star schema (Fact/Dim) is faster and cleaner for BI. |
| **Specific Business Formula** (e.g. "Net Revenue") | **dbt**                      | Ensure consistency across the company.               |
| **Date Filtering** (e.g. "Last 30 days")           | **Metabase**                 | User preference, changes frequently.                 |
| **Dashboard Layout**                               | **Metabase (via Playbooks)** | It's a UI concern.                                   |
| **Ad-hoc Analysis**                                | **Metabase**                 | Quick exploration doesn't need a formal model yet.   |

## 4. Next Steps for Us

To align with this architecture, we should:

1.  **Refactor dbt**: Move calculations like `net_revenue` from the SQL queries in `docs/analytics-handbook/` (now Playbooks) into `fact_orders.sql`.
2.  **Simplify Playbooks**: Update the Playbooks to use the new simple columns (e.g. `SUM(net_revenue)` instead of formula).
3.  **Automate**: Use the Metabase Automation Agent to deploy these Playbooks.
