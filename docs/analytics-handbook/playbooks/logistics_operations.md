# Playbook: Logistics Operations Center

## Overview

- **Audience:** Operations Manager
- **Goal:** Real-time monitoring of order processing pipeline — fulfillment status, processing speed, bottleneck identification.
- **Collection:** `Logistics`
- **Design Spec:** [designs/logistics_operations.md](../designs/logistics_operations.md)

## Data Lineage

- **Core Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) — status, fulfillment_status, ordered_at, first_shipped_at, time_to_complete_hours
- **Dimensions:** [`dim_order_status`](../../../transformation/models/marts/core/dim_order_status.sql), [`dim_staff`](../../../transformation/models/marts/core/dim_staff.sql), [`dim_channels`](../../../transformation/models/marts/core/dim_channels.sql), [`dim_date`](../../../transformation/models/marts/core/dim_date.sql), [`dim_branch_location`](../../../transformation/models/marts/core/dim_branch_location.sql)
- **Planned models (not yet available):** `fact_fulfillments`, `fact_shipments`, `dim_carriers`

### Data Availability

| Capability | Status | Source | Notes |
|---|---|---|---|
| Order status funnel (OPEN/COMPLETED/CANCELLED) | **Available** | `fact_orders.status` | 5 statuses: OPEN, COMPLETED, CANCELLED, ARCHIVED, DRAFT |
| Fulfillment status breakdown | **Available** | `fact_orders.fulfillment_status` | fulfilled/unfulfilled/partial |
| Time to complete (hours) | **Available** | `fact_orders.time_to_complete_hours` | `date_diff('hour', created_at, completed_at)` |
| First shipment timestamp | **Available** | `fact_orders.first_shipped_at` | From `std_fulfillments`, MIN(shipped_at) per order |
| Staff who processed order | **Available** | `fact_orders` JOIN `dim_staff` | Via seller_staff_key |
| Carrier-level performance | **Planned** | No `dim_carriers` / `fact_shipments` | Requires new ingestion + models |
| Delivery timestamps | **Planned** | No delivery tracking data | Cannot compute delivery time |
| Per-fulfillment line items | **Planned** | No `fact_fulfillments` mart | Only aggregated first_shipped_at available |

## Filters

- **Date Range:** Today (Real-time). No interactive filters — Operational Cockpit, zero-interaction.
- **Business Constraints:** Exclude `status = 'DRAFT'` from all cards. Exclude `status = 'CANCELLED'` from speed metrics.

## Reading Flow

1. **CONTEXT** — Pipeline don hang hom nay dang chay the nao? Dashboard tra loi cau hoi xu ly hang ngay.
2. **KEY FINDING** — Nhin Fulfillment Rate (gauge) truoc: xanh (>95%) = on-track, vang (85-94%) = can chu y, do (<85%) = co van de.
3. **EVIDENCE** — Kiem tra Order Status Funnel de biet don dang bi nghen o buoc nao. Xem Hourly Processing Time de phat hien thoi diem cham.
4. **IMPLICATIONS** — Fulfillment Rate thap + nhieu don pending > 24h = pipeline bi tat nghen, anh huong khach hang.
5. **ACTIONS** — Xem Stuck Orders Detail, phan bo lai nhan vien, escalate don cu nhat.

## Visualizations

### View 1: Pipeline Overview

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
|:---|:---|:---|:---|
| **Fulfillment Rate** | Gauge | [Fulfillment Rate](../domains/logistics.md#1-fulfillment-rate) | Zones: 95-100 (green), 85-94 (yellow), 0-84 (red). Hero card. |
| **Total Orders Today** | Scalar + trend | Count(orders) WHERE status != 'DRAFT' | DoD comparison. |
| **Shipped Orders** | Scalar + trend | Count WHERE first_shipped_at IS NOT NULL AND today | DoD comparison. |
| **Avg Time to Complete** | Scalar + trend | AVG(time_to_complete_hours) | DoD comparison. Lower = better (inverted). |
| **Order Status Funnel** | Funnel | [Order Status Funnel](../domains/logistics.md#8-order-status-funnel) | OPEN -> COMPLETED. Excludes DRAFT. |
| **Fulfillment Status Breakdown** | Donut | fulfillment_status distribution | fulfilled/unfulfilled/partial. |
| **Hourly Order Intake** | Line (Today vs Yesterday) | Count orders by hour | DoD overlay. |
| **Cumulative Orders** | Line (Today vs Yesterday) | Running sum orders by hour | DoD overlay. |

### View 2: Processing Speed

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
|:---|:---|:---|:---|
| **Avg Hours to First Ship** | Scalar + trend | [Order Cycle Time](../domains/logistics.md#2-order-cycle-time) | `AVG(date_diff('hour', ordered_at, first_shipped_at))`. Hero card. DoD. |
| **Same-Day Ship Rate** | Scalar + trend | [Same-Day Ship Rate](../domains/logistics.md#3-same-day-ship-rate) | `COUNT(same day shipped) / total eligible`. DoD. |
| **Orders Pending > 24h** | Scalar | Count WHERE status = 'OPEN' AND age > 24h | Red when > 0. Escalation signal. |
| **Completed Today** | Scalar + trend | Count WHERE status = 'COMPLETED' AND today | DoD comparison. |
| **Hourly Avg Processing Time** | Line (Today vs Yesterday) | AVG hours to first ship by hour | DoD overlay. |
| **Throughput Heatmap** | Heatmap | Count shipped per Day-of-Week x Hour | Intensity matrix. |
| **Stuck Orders Detail** | Table (formatted) | Orders WHERE OPEN > 24h | Conditional: >24h red, >12h yellow. Sorted by age desc. |

### View 3: Details & Staff

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
|:---|:---|:---|:---|
| **Staff — Orders Processed** | Horizontal Bar | [Staff Performance](../domains/logistics.md#7-staff-performance) | Ranking by count. |
| **Staff — Avg Processing Time** | Horizontal Bar | AVG(time_to_complete_hours) by staff | Ranking by speed. |
| **Order Detail Table** | Table (formatted) | Full order detail | Status conditional formatting. |

## Action Triggers

| Metric | Threshold | Owner | Action |
|--------|-----------|-------|--------|
| Fulfillment Rate | < 85% | Operations Manager | Review stuck orders, check inventory/system issues |
| Fulfillment Rate | 85-94% | Operations Manager | Monitor closely, identify which status stage has backlog |
| Avg Hours to First Ship | DoD > +30% | Operations Manager | Check staffing, review pending orders by age |
| Orders Pending > 24h | > 0 | Operations Manager | Immediate review of stuck orders, escalate oldest |
| Orders Pending > 24h | > 5 | Operations Manager | Escalate to management, check for systemic issue |
| Same-Day Ship Rate | DoD < -10% | Operations Manager | Investigate hourly trend for slowdown pattern |
| Staff workload imbalance | Top > 3x Bottom | Operations Manager | Rebalance assignments |

## Implementation Notes

### Best Practices

1. **Status mapping**: `fact_orders.status` values: OPEN, COMPLETED, CANCELLED, ARCHIVED, DRAFT. Exclude DRAFT from pipeline counts.
2. **Fulfillment Rate formula**: `COUNT(CASE WHEN fulfillment_status = 'fulfilled') / COUNT(*) WHERE status NOT IN ('DRAFT', 'CANCELLED')`.
3. **Time to first ship**: `date_diff('hour', ordered_at, first_shipped_at)` — only for orders with `first_shipped_at IS NOT NULL`.
4. **Timezones**: All timestamps are TIMESTAMPTZ. Display in Asia/Ho_Chi_Minh at serving layer.
5. **Stuck orders**: `WHERE status = 'OPEN' AND date_diff('hour', ordered_at, NOW()) > 24`.

### Common Pitfalls

- Counting DRAFT orders in pipeline metrics — always exclude.
- Including CANCELLED orders in speed calculations — skews averages.
- Using `time_to_complete_hours` for "time to ship" — this measures created-to-completed, not created-to-shipped. Use `first_shipped_at` for shipping speed.
- Assuming carrier data exists — no `dim_carriers` or `fact_shipments`. Focus on order processing, not shipping/delivery.

### Planned Enhancements (require new data sources)

1. **Carrier performance breakdown** — requires `dim_carriers` + `fact_shipments`
2. **Delivery time tracking** — requires delivery timestamps
3. **Per-fulfillment line item view** — requires `fact_fulfillments` mart
4. **SLA compliance tracking** — requires defined SLA targets per order type
