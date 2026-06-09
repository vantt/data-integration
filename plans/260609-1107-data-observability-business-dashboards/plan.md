# Plan: Data Observability in Business Dashboards

> Created: 2026-06-09
> Status: ✅ Mostly done (infrastructure ready, surfacing pending)
> Origin: `analytics_improvement_opportunities.md` § Data Observability in Business Reports

## Objective

Prevent users from acting on stale or incomplete data by embedding trust signals inside business dashboards — not only in the data engineering dashboard.

## Current state

**✅ Done:**
- Ingestion Health Monitor playbook: `docs/analytics-handbook/playbooks/ingestion_health.md`
- Ingestion Health blueprint: `docs/analytics-handbook/blueprints/ingestion_health.md`
- Core observability concepts defined (freshness, volume, SLA, recon drift)
- Orders List Reconciliation dashboard has strong freshness coverage

**Not yet done:**
- Business dashboards (CEO, Finance, Marketing, Daily Ops) do not show data freshness
- No "data not reliable" visual state for dashboards with stale dependencies
- No report-specific freshness (only global ingestion freshness available)

## Implementation steps

- [ ] Define standard trust block component: last_order_update, last_misa_update, last_shopee_update, cogs_coverage_pct
- [ ] Add trust block text card to CEO Weekly Pulse (top of dashboard)
- [ ] Add trust block to Finance P&L dashboard (+ COGS coverage % + Shopee payout lag)
- [ ] Add trust block to Marketing dashboards
- [ ] Add trust block to Daily Sales Operations dashboards
- [ ] Add "data not reliable" banner pattern: if last_update > SLA threshold → show warning text card
- [ ] Add report-specific freshness query per dashboard (not global — scope to relevant sources)

## Trust block pattern (SQL sketch)

```sql
SELECT
    MAX(ordered_at)                             AS last_order_update,
    MAX(CASE WHEN source='misa' THEN updated_at END) AS last_misa_update,
    SUM(has_cogs::INT)::FLOAT / COUNT(*)        AS cogs_coverage_pct
FROM fact_orders
WHERE scope_sales AND is_active_order
```

## Dependency

No new data sources needed — uses existing ingestion_health metadata and fact_orders.
Low effort, high trust impact. Should be done before expanding to new dashboards.
