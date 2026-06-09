# Plan: Inventory & Stock Health

> Created: 2026-06-09
> Status: ✅ Done
> Origin: `analytics_improvement_opportunities.md` § Inventory and Stock Health

## Objective

Daily inventory snapshots for OOS alerts, slow-mover detection, reorder decisions, and stock value tracking.

## Status

**✅ Complete** — verified 2026-06-09:
- `fact_inventory_snapshot`: 2037 rows, live
- `mart_inventory_health`: 2037 rows, with computed fields `is_oos`, `is_low_stock`, `is_overstock`, `daily_velocity`, `days_of_supply`, `is_slow_mover`, `is_dead_stock`, `slow_mover_value_at_risk`, `dead_stock_value_at_risk`
- Dashboard: **Product Inventory Health [All]** (Metabase id=94) — ACTIVE
- Blueprint: `docs/analytics-handbook/blueprints/product_inventory.md`
- Playbook: `docs/analytics-handbook/playbooks/product_inventory.md`

## Unlocked metrics

- [x] OOS rate
- [x] Days of supply
- [x] Inventory turnover
- [x] Dead stock / slow-mover
- [x] Clearance candidates
- [x] Stock value at MAC
- [ ] Stockout impact on revenue (needs join to fact_orders — not yet built)
- [ ] Purchase order / inbound shipment data (source not available)

## Next step

Join `mart_inventory_health.is_oos` with `fact_orders` to estimate revenue lost to stockouts.
