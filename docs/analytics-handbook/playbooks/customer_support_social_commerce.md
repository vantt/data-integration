# Playbook: Social Commerce Operations

## Overview

- **Audience:** Customer Support Team Leader
- **Goal:** Monitor and improve the "Chat-to-Order" conversion rate from Facebook & Zalo.
- **Collection:** `Customer Support`

## Key Questions

1. **Are we hitting our daily sales targets from Social?**
2. **Which channel (FB vs Zalo) is driving more value today?**
3. **Are there "missed opportunities" (high traffic but low orders)?** _(Requires future traffic data)_

## Visualizations

### Section 1: Real-time Social Performance

| Chart Title              | Visualization Type | Metric Reference                                                            | Notes                         |
| :----------------------- | :----------------- | :-------------------------------------------------------------------------- | :---------------------------- |
| **Social Revenue Today** | Scalar / Number    | [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume) | Filter: Today, Source: Social |
| **Social Orders Today**  | Scalar / Number    | [Social Order Count](../domains/customer_support.md#2-social-order-count)   | Filter: Today, Source: Social |
| **Revenue by Channel**   | Pie Chart          | [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume) | Breakdown by Facebook / Zalo  |

### Section 2: Team Performance (Sales Contribution)

> **Note:** Currently tracking _Sales_ attached to Staff ID. Future updates will include _Response Time_.

| Chart Title          | Visualization Type     | Metric Reference | Notes                                |
| :------------------- | :--------------------- | :--------------- | :----------------------------------- |
| **Top Sales Agents** | Bar Chart (Horizontal) | GMV by Staff     | Filter: Source = Social              |
| **Orders by Agent**  | Table                  | Count of Orders  | Columns: Agent Name, Orders, Revenue |

## Action Triggers

| Metric | Threshold | Owner | Action |
| :----- | :-------- | :---- | :----- |
| Social Revenue Today | DoD < -20% | CS Team Leader | Check unread messages on FB Page/Zalo OA. Verify Flash Sale posts published. |
| Social Revenue Today | DoD > +30% | CS Team Leader | Verify no duplicate orders. Identify which channel/agent is driving spike. |
| Social Orders Today | DoD < -15% | CS Team Leader | Check inbound message volume — is traffic down or conversion down? |
| Revenue by Channel | 1 channel < 20% of total | CS Team Leader | Push underperforming channel — post content, respond faster. |
| Agent Revenue | Agent has 0 orders after 2h | CS Team Leader | Check if agent is online/replying. Redistribute incoming messages. |
| Agent Revenue DoD | Change < -30% | CS Team Leader | Talk to agent directly, review chat logs for missed closings. |

## Reading Flow

1. **Start at Hero** — Social Revenue Today: "Are we on track vs yesterday?"
2. **Check supporting KPIs** — Orders + AOV: "Volume problem or value problem?"
3. **Channel breakdown** — Donut + Trend: "Which channel is driving or dragging?"
4. **Agent performance** — Bar charts + Table: "Who needs help? Who is overperforming?"
5. **Recent orders** — Detail table: "Verify latest orders are flowing in correctly."

## Operational Actions

- **Low Social Revenue:**
  - Check if there are unread messages on Facebook Page/Zalo OA.
  - Verify if "Flash Sale" posts have been published.
- **High Traffic / Low Orders:**
  - Audit a random sample of chat logs to check for "missed closing" opportunities.
  - Retrain agents on the current promotion script.

## Design Spec

- **Design:** [Social Commerce Operations](../designs/customer_support_social_commerce.md)
