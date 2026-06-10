# Plan: Data Observability in Business Dashboards

> Created: 2026-06-09
> Status: ✅ Complete (2026-06-10)
> Origin: `analytics_improvement_opportunities.md` § Data Observability in Business Reports

## Objective

Prevent users from acting on stale or incomplete data by embedding trust signals inside business dashboards — not only in the data engineering dashboard.

## Current state

**✅ Done:**
- Ingestion Health Monitor playbook: `docs/analytics-handbook/playbooks/ingestion_health.md`
- Ingestion Health blueprint: `docs/analytics-handbook/blueprints/ingestion_health.md`
- Core observability concepts defined (freshness, volume, SLA, recon drift)
- Orders List Reconciliation dashboard has strong freshness coverage
- `Source & Freshness` static text card (`<!-- text-id:source-freshness -->`) already exists at `row: 99` in **all 35 blueprints** — describes source tables, cadence, scope, caveats (hardcoded)

**Not yet done:**
- Business dashboards (CEO, Finance, Marketing, Daily Ops) do not show live data freshness
- No dynamic freshness signal showing actual last-update timestamps
- No "data not reliable" visual state for dashboards with stale dependencies
- No report-specific freshness (only global ingestion freshness available)

## Placement: Bottom of dashboard (row 98)

Trust block is **supplementary info** → place at bottom, same area as existing `Source & Freshness` widget.

| Widget | Row | Type | Content |
|---|---|---|---|
| Trust Block (new) | 98 | Dynamic SQL question | Live timestamps + coverage % |
| Source & Freshness (existing) | 99 | Static text card | Source tables, cadence, scope, caveats |

The two widgets are **complementary**, not duplicates:
- `Source & Freshness` = documentation ("what this dashboard uses by design")
- Trust Block = live signal ("what the actual data state is right now")

## Implementation steps

- [x] Define standard trust block SQL template (scoped per dashboard, not global)
- [x] Add trust block to CEO Weekly Pulse (row 98, each tab) — card ID 2191, deployed 2026-06-10
- [x] Add trust block to Finance P&L dashboard (+ COGS coverage % + Shopee payout lag) — card ID 2192, 4 tabs, deployed 2026-06-10
- [x] Add trust block to Marketing dashboards — card ID 2193, marketing_roi (1 tab) + marketing_weekly_tracker (3 tabs) + marketing_monthly_analysis (5 tabs), deployed 2026-06-10
- [x] Add trust block to Daily Sales Operations dashboards — card IDs 2194/2195, sales_daily_retail (3 tabs) + sales_today_operation (4 tabs) + sales_ops_weekly_review (4 tabs) + sales_ops_monthly_summary (4 tabs), deployed 2026-06-10
- [x] Add "data not reliable" banner pattern — ⚠️ prefix trong trust block SQL khi last_order > 24h, deployed 2026-06-10
- [x] Document `text-id:trust-block` tag standard — added to `docs/analytics-handbook/guides/dashboard_design_patterns.md`, deployed 2026-06-10

## Trust block pattern (SQL sketch)

```sql
-- Scoped to dashboard's relevant sources — not global
SELECT
    MAX(ordered_at)                                       AS last_order_update,
    MAX(CASE WHEN cogs_source = 'misa' THEN updated_at END) AS last_misa_update,
    MAX(CASE WHEN channel = 'shopee' THEN payout_released_at END) AS last_shopee_payout,
    ROUND(100.0 * SUM(has_cogs::INT) / COUNT(*), 1)      AS cogs_coverage_pct
FROM fact_orders
WHERE scope_sales AND is_active_order
```

## Dependency

No new data sources needed — uses existing ingestion_health metadata and fact_orders.
Low effort, high trust impact. Should be done before expanding to new dashboards.
