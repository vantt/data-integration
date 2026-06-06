# Freshness & SLA

Reference document for per-mart data SLA, ingestion asset thresholds, dependency chains, and stale detection procedures.

> **Canonical source:** this file
> **Live monitoring:** Dagster Ingestion Health dashboard → [`blueprints/ingestion_health.md`](../blueprints/ingestion_health.md)
> **Freshness metric:** [`ingestion_freshness`](metrics.md#ingestion_freshness)

---

## Mart SLA

Each row is self-contained: Depends On shows the upstream asset gate, SLA Breach Impact shows what breaks downstream.

| Mart | Frequency | Available By | Grain | Source | Depends On | SLA Breach Impact |
|---|---|---|---|---|---|---|
| `fact_orders` | Daily + near-realtime | 07:00 ICT | Per order | Sapo API | `sapo_webhook_consumer` (SLA 12h) | All [All] and [Retail] dashboards, CEO Weekly Pulse |
| `fact_order_items` / `fact_sales` | Daily | 07:00 ICT | Per order line | Sapo API | `sapo_batch_asset` (SLA 28h) | Product performance, basket size metrics |
| [`fact_order_economics`](entities.md#order-economics) | Daily | 08:00 ICT | Per order | MISA + Sapo | `fact_orders` + `misa_sales_file_drop_asset` (SLA 192h) | Order Profitability, Channel P&L, gross profit analysis |
| `fact_order_costs` | Daily | 08:00 ICT | Per (order, cost_type) | MISA + Sapo + Shopee | `fact_order_economics` + `int_shopee_order_fees` | Finance Cost Ledger dashboard |
| `fact_order_returns` | Daily | 07:00 ICT | Per return event | Sapo API | `sapo_batch_asset` (SLA 28h) | Return Impact Analysis, `return_rate` metric |
| `dim_customers` | Daily | 07:00 ICT | Per customer | Sapo API | `sapo_batch_asset` (SLA 28h) | Customer dashboards, RFM segments, scope flags |
| `dim_channels` | Daily | 07:00 ICT | Per channel | Sapo API | `sapo_batch_asset` (SLA 28h) | Channel dimensions on all dashboards |
| `dim_products` | Daily | 07:00 ICT | Per SKU | Sapo API | `sapo_batch_asset` (SLA 28h) | Product dimensions on all dashboards |
| `fact_fulfillments` | Real-time | ~5 min lag | Per fulfillment | Sapo webhook | `sapo_webhook_consumer` (SLA 12h) | Logistics Operations dashboard, `fulfillment_rate` metric |
| `fact_marketing_spend` | Daily | 09:00 ICT | Per campaign/day | Manual import (Sheets) | `sheets_marketing_spend_asset` (SLA 48h) | Marketing ROI, CTR, CPM dashboards |
| `mart_sku_economics_monthly` | Daily | 08:30 ICT | Per (SKU, month) | MISA + Sapo | `fact_order_economics` + `fact_sales` | Product Profitability, SKU margin analysis |
| `fact_inventory_snapshot` | Daily | 07:00 ICT | Per (SKU, location, date) | Sapo nightly batch (3am ICT) | `sapo_batch_asset` (SLA 28h) | Inventory Health dashboard, OOS rate |
| `mart_inventory_health` | Daily | 07:30 ICT | Per (SKU, location, date) | Derived | `fact_inventory_snapshot` + `mart_sku_economics_monthly` | Days of supply, dead stock alerts |
| `fact_targets` | On-demand | Manual trigger | Per target rule | Sheets CSV seed | `sheets_targets_asset` (SLA 48h) | Target Achievement Rate, Variance to Target |
| `dim_channel_targets` | On-demand | Manual trigger | Per (channel, month, metric) | CSV seed | Manual `dbt seed` | Channel budget overlay in Finance P&L |
| `fact_payments` | Daily | 07:00 ICT | Per payment | Sapo API | `sapo_batch_asset` (SLA 28h) | Cash flow analysis |
| `ingestion_health.duckdb` | Real-time | ~5 min lag | Per asset run | Internal pipeline | Dagster scheduler | Ingestion Health Monitor dashboard itself |
| `int_shopee_order_fees` | Daily | 08:00 ICT | Per Shopee order | Shopee income file | `shopee_income_file_drop_asset` (SLA 48h) | Shopee Channel Economics, platform fee metrics |

---

## Ingestion Asset SLA Reference

Asset-level SLAs from the operations domain. Status thresholds apply to `ingestion_health.duckdb`.

| Asset Key | SLA | Status Token Thresholds |
|---|---|---|
| `sapo/sapo_webhook_consumer_asset` | 12h | healthy < 12h / warning ≥ 9h / stale ≥ 12h |
| `sapo/sapo_history_log_asset` | 12h | healthy < 12h / warning ≥ 9h / stale ≥ 12h |
| `sapo/sapo_*_batch_asset` (4 assets) | 28h | healthy < 28h / warning ≥ 21h / stale ≥ 28h |
| `shopee/shopee_income_file_drop_asset` | 48h | healthy < 48h / warning ≥ 36h / stale ≥ 48h |
| `sheets/sheets_*_asset` (2 assets) | 48h | healthy < 48h / warning ≥ 36h / stale ≥ 48h |
| `misa_amis/misa_sales_file_drop_asset` | 192h (8 days) | healthy < 192h / warning ≥ 144h / stale ≥ 192h |
| `recon/*` assets | 28h | same thresholds as batch assets |

> **Rule:** Dashboards showing "yesterday" data require availability by 07:00 ICT.
> **Rule:** Real-time dashboards use `fact_orders` + `fact_fulfillments` via webhook (lag ~5 min). Not suitable for financial reporting.
> **Rule:** Do not use P&L dashboards before 08:00 ICT — `fact_order_economics` requires MISA COGS data (1h lag after `fact_orders`).

---

## Mart Dependency Chain

```
Sapo webhook ──► fact_orders (07:00) ──────────────────► [All daily dashboards]
                       │
                       ▼
             fact_order_economics (08:00) ◄── MISA file drop (SLA 192h — BOTTLENECK)
                       │
                       ▼
             fact_order_costs (08:00) ◄── int_shopee_order_fees
                       │
                       ▼
             mart_sku_economics_monthly (08:30)
                       │
                       ▼ (velocity input)
Sapo batch ──► fact_inventory_snapshot (07:00)
                       │
                       ▼
             mart_inventory_health (07:30)

Manual import ──► fact_marketing_spend (09:00)    [SLA 48h — manual gap risk]
Manual dbt seed ► fact_targets / dim_channel_targets   [not in pipeline monitoring]
```

**Critical path:** `misa_amis/misa_sales_file_drop_asset` (SLA 192h) is the single longest dependency in the chain. When MISA is stale, `fact_order_economics`, `fact_order_costs`, and `mart_sku_economics_monthly` all delay or serve stale data.

---

## Stale Data Detection Procedure

Run these checks in order. Do not investigate metric definitions until data freshness is confirmed.

```sql
-- Step 1: Check whether the upstream ingestion asset ran successfully
SELECT asset_key, status, run_ended_at,
       EXTRACT(EPOCH FROM (NOW() - run_ended_at)) / 3600 AS hours_ago
FROM ingestion_runs
WHERE asset_key = 'sapo/sapo_webhook_consumer_asset'  -- replace with relevant asset
ORDER BY run_ended_at DESC
LIMIT 5;

-- Step 2: Check mart freshness directly
SELECT MAX(ordered_at) AS latest_order       FROM fact_orders;          -- should be < 2h ago
SELECT MAX(date_key)   AS latest_econ_date   FROM fact_order_economics;  -- should be yesterday

-- Step 3: MISA specifically (most common bottleneck for economics marts)
SELECT asset_key, status, run_ended_at,
       EXTRACT(EPOCH FROM (NOW() - run_ended_at)) / 3600 AS hours_ago
FROM ingestion_runs
WHERE asset_key = 'misa_amis/misa_sales_file_drop_asset'
  AND status IN ('success', 'partial')
ORDER BY run_ended_at DESC
LIMIT 3;
-- SLA is 192h; if stale, fact_order_economics and all downstream marts are affected.

-- Step 4: Verify recon drift to detect silent data quality issues
SELECT asset_key,
       metadata_json->>'drift_pct' AS drift_pct
FROM ingestion_runs
WHERE asset_key LIKE 'recon/%'
ORDER BY run_started_at DESC
LIMIT 4;

-- Step 5: Only after confirming data is fresh → investigate metric definitions
```

**Decision tree:**

```
Dashboard shows unexpected numbers
    │
    ├─ ingestion_health shows stale?  ──► Wait for pipeline / trigger manual run
    │
    ├─ mart freshness query is old?   ──► Check Dagster run log for failed job
    │
    ├─ MISA stale (> 144h)?           ──► Alert finance team to drop MISA file
    │
    └─ All fresh, numbers still wrong ──► Investigate metric definition or filter logic
```

---

## Historical Data Warning — Sapo Truncation

**Sapo truncates `history_log` data over time.** The text partition holds irreplaceable 2021–2025 historical data.

- **Action: NEVER delete the text partition.**
- Some status history and fulfillment timeline data is only available from the ingestion start date, not as a full historical backfill.
- When querying pre-2025 order status or fulfillment timelines, acknowledge this coverage gap.

---

## Seed-based Tables

`fact_targets` and `dim_channel_targets` are **not pipeline assets** — they do not appear in `ingestion_health` monitoring and have no automated refresh.

Manual update process:

```bash
# 1. Edit the seed CSV first (transformation/seeds/dim_channel_targets.csv or fact_targets.csv)

# 2. Load seed and rebuild dependent models
dbt seed --select dim_channel_targets
dbt build --select dim_channel_targets

# 3. Verify after seed
dbt run-operation run_query --args '{"query": "SELECT COUNT(*), MAX(period_month) FROM dim_channel_targets"}'
```

> These tables will not trigger alerts in Ingestion Health Monitor when stale. Staleness must be detected via dashboard review or manual audit.
