# Customer Support Domain

> **Owner:** Customer Support Lead / Sales Ops
> **Update Frequency:** Real-time / Daily

## Context: Social Commerce Performance

> **Description:** Tracking the effectiveness of the CS team in converting social media inquiries (Facebook, Zalo) into orders.
> **dbt Source:** `fact_orders`

### 1. Social Sales Volume

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** GMV generated specifically from Social Media channels (Facebook, Zalo).
- **Logic (SQL):**
  ```sql
  SELECT
      channel_format,
      channel_name,
      SUM(gmv)
  FROM fact_orders
  LEFT JOIN dim_channels USING (channel_key)
  WHERE channel_format = 'Social'
  GROUP BY 1, 2
  ```

### 2. Social Order Count

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Number of successful orders originating from social channels.
- **Logic (SQL):**
  ```sql
  SELECT COUNT(DISTINCT order_id)
  FROM fact_orders
  LEFT JOIN dim_channels USING (channel_key)
  WHERE channel_format = 'Social'
  ```

## Context: Support Efficiency (Planned)

> **Description:** Metrics related to response speed and ticket handling.
> **Status:** 🚧 Requirements Definition Only. Data not yet available in Warehouse.

### 3. First Response Time (FRT)

> **Status:** 🔴 Missing Data

- **Requirement:** Time difference between _Customer First Message_ and _Agent First Reply_.
- **Target Grain:** Per Conversation.
- **Goal:** < 5 Minutes.

### 4. Average Handling Time (AHT)

> **Status:** 🔴 Missing Data

- **Requirement:** Average duration of a support conversation from open to close.
- **Target Grain:** Per Ticket/Conversation.

## Related Playbooks

| Playbook                                                                           | Description                                                      |
| :--------------------------------------------------------------------------------- | :--------------------------------------------------------------- |
| **[Social Commerce Operations](../playbooks/customer_support_social_commerce.md)** | Daily guide for CS Leads to monitor "Chat-to-Order" performance. |
