# Playbook: Inventory Health

> **Status:** ACTIVE
> **Audience:** Inventory Manager, Ops Manager
> **Cadence:** Daily (5-min morning check)
> **Collection:** Operations > Logistics
> **Dashboard:** Product Inventory Health

## Purpose

Daily inventory check to prevent stockouts, surface slow-mover capital exposure, and track stock value by location. Answer three questions each morning:
1. Any SKUs went OOS overnight?
2. Which location has the most capital tied up in slow-movers?
3. Any new low-stock alerts requiring reorder?

## Reading Flow (5-min check)

| Step | Tab | Signal | Action |
|------|-----|--------|--------|
| 1 | Current Stock | OOS count scalar | If > 0 → drill into SKU list, coordinate reorder |
| 2 | Current Stock | Low-stock table | Check min_value breached → trigger purchase order |
| 3 | Slow-Mover & Dead Stock | Value at risk by SKU | Review > 10M VND exposure → escalate to manager |
| 4 | Inventory Trend | Stock value 30d trend | Down > 20%? Check if depletion or fulfillment issue |

## Action Triggers

| Signal | Threshold | Action | Owner |
|--------|-----------|--------|-------|
| OOS SKU | on_hand ≤ 0 | Immediate reorder / check incoming | Inventory Manager |
| Low stock | on_hand ≤ min_value | Create purchase order | Inventory Manager |
| Slow mover value | stock_value_at_mac > 10M AND days_of_supply > 90 | Escalate to Ops Manager for discount/clearance decision | Ops Manager |
| Dead stock value | stock_value_at_mac > 5M AND no sale 90d | Flag for write-off review | Finance / Ops Manager |
| Negative on_hand (MM Market) | on_hand < 0 | Expected for consignment — confirm shipment received by partner | Logistics |

## Data Lineage

| Model | Role |
|-------|------|
| [`fact_inventory_snapshot`](../../../transformation/models/marts/sales/fact_inventory_snapshot.sql) | Daily snapshot grain: (variant_id, location_id, snapshot_date). Incremental parquet, never deleted |
| [`mart_inventory_health`](../../../transformation/models/marts/sales/mart_inventory_health.sql) | Derived health flags + days_of_supply + capital-at-risk |
| [`mart_sku_economics_monthly`](../../../transformation/models/marts/sales/mart_sku_economics_monthly.sql) | Velocity source (daily_velocity, days_since_last_sale) for days_of_supply calc |
| [`dim_branch_location`](../../../transformation/models/marts/core/dim_branch_location.sql) | Location name/code (denormalized into snapshot) |

## Locations in Scope

| location_id | Name | Code | Notes |
|-------------|------|------|-------|
| 452566 | 16 Trương Định | VVT | Main warehouse — 118K units, 114 active SKUs |
| 494912 | Hậu Giang | HG | Secondary — 100K units, only 7 active SKUs |
| 624127 | MM Market An Phú | MMA | Consignment — negative on_hand is normal |

TheHealthyUs (639290) and ShowroomVVT (657377) are logical entities — no inventory payload from Sapo API.

## Key Metrics

| Metric | Definition | Source column |
|--------|-----------|---------------|
| OOS Rate | COUNT(is_oos=true) / total SKUs | `mart_inventory_health.is_oos` |
| Inventory Value | SUM(stock_value_at_mac) | `fact_inventory_snapshot.stock_value_at_mac` |
| Days of Supply | on_hand / daily_velocity | `mart_inventory_health.days_of_supply` |
| Slow-Mover Value at Risk | SUM(slow_mover_value_at_risk) | `mart_inventory_health.slow_mover_value_at_risk` |
| Dead Stock Value | SUM(dead_stock_value_at_risk) | `mart_inventory_health.dead_stock_value_at_risk` |

## Caveats

- **Snapshot freshness**: data reflects the 3am ICT nightly batch. Intra-day transactions are not visible.
- **days_of_supply uses SKU-level velocity** (all locations combined) — not per-location. A SKU sold only from Trương Định will show overstated supply for Hậu Giang.
- **mac (Moving Average Cost)** from Sapo may lag recent GRN pricing. Stock value figures are estimates, not accounting-grade.
- **MM Market on_hand can be negative**: consignment stock fully shipped to partner; committed > on_hand is expected.
- **Velocity NULL = never sold in 24 months**: these SKUs appear as dead stock regardless of actual movement (e.g. new launches or gift items).

## Filters Available

- **Location**: filter to individual warehouse (Trương Định / Hậu Giang / MM Market)
- **Date**: select snapshot_date for historical view
- **Category / Brand**: drill into specific product family
