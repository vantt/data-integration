# Order P&L Schema Research

**Date:** 2026-05-26
**Scope:** Assess current dbt schema for per-order P&L feasibility in `data-integration/transformation`.
**TL;DR:** `fact_order_economics` already exists and delivers per-order P&L for Sapo + MISA + Shopee. **Gap:** non-Shopee marketplaces (Lazada, Tiki, TikTok, Sendo, Grab, Selly...) have no per-order platform-fee feed, marketing spend has no per-order attribution, and Sapo `order_returns` raw is captured but never flows into a mart. No shipping/payment fee for non-platform orders.

---

## 1. Current Schema Map (Orders & Cost Tables)

### Source → Staging → Standard → Mart layers

```
SAPO RAW (JSON payload)
  src_sapo_orders               (incremental, JSON-extracted scalars + 3 nested arrays as text)
  src_sapo_order_returns        (incremental, raw return data — NO downstream)
  ├── stg_sapo_orders           (view, enrichment join refs)
  ├── stg_sapo_order_items      (view, unnest order_line_items_json)
  ├── stg_sapo_payments         (view, unnest payments_json)
  ├── stg_sapo_fulfillments     (view, unnest fulfillments_json)
  └── (no stg for returns)

  std_orders        (view, normalized, status mapping)
  std_order_items   (view)
  std_payments      (view)
  std_fulfillments  (view, contains cod_amount, tracking, carrier)

MISA RAW (file-drop excel)
  src_misa_sales_lines          (view, dedup voucher_no+line_no)
  stg_misa_sales_lines          (view, channel enrichment, derive gross_profit, gross_margin)
  int_misa_sales_lines          (mart-tier intermediate w/ rolling location)

SHOPEE RAW (file-drop excel)
  src_shopee_order_revenue, src_shopee_order_revenue_items, src_shopee_order_service_fees, src_shopee_order_adjustments
  stg_shopee_order_revenue (view, derives total_shipping_net, total_discounts, total_platform_fees, total_taxes)
  stg_shopee_order_revenue_items, stg_shopee_order_service_fees, stg_shopee_order_adjustments
  int_shopee_order_fees         (mart-tier — per-order fee breakdown)
  int_shopee_order_items        (per-order × product)
  int_shopee_order_adjustments  (one row per adjustment)

MARKETING SPEND (Google Sheet)
  src_marketing_spend_raw (sources.yml) → stg_marketing_spend → fact_marketing_spend (date × channel × campaign granularity)

MARTS
  fact_orders            (1 row/order — Sapo revenue, addresses, channel key, team, status)
  fact_sales             (1 row/line item — qty, line_amount, line discount)
  fact_payments          (1 row/payment — amount, method, status)
  fact_marketing_spend   (1 row/spend record — date+channel grain, NO order link)
  fact_order_economics   (1 row/order — Sapo revenue + MISA COGS + Shopee fees) ★ existing P&L
```

### Key Tables for P&L

| Table | Grain | Owner | Status |
|---|---|---|---|
| `fact_orders` | 1 row/order | Sapo | Live. Revenue waterfall (gross/discount/net/tax/total_collected). NO COGS, NO fees, NO shipping. |
| `fact_order_economics` | 1 row/order | Sapo+MISA+Shopee | **Live. Already per-order P&L.** |
| `int_misa_sales_lines` | 1 row/invoice-line | MISA | Live. COGS via `voucher_no` = Sapo `order_code`. ~65% coverage. |
| `int_shopee_order_fees` | 1 row/Shopee order | Shopee | Live. Full fee breakdown for Shopee channel only. |
| `int_shopee_order_adjustments` | 1 row/adjustment | Shopee | Live. Marketing fees, compensations. Aggregated into `int_shopee_order_fees` as `total_adjustment_amount`. |
| `std_fulfillments` | 1 row/shipment | Sapo | Live. Has `cod_amount`, carrier, tracking — NOT in any fact. |
| `src_sapo_order_returns` | 1 row/return | Sapo | **Captured but never flows into mart.** |
| `fact_marketing_spend` | 1 row/spend record | GSheet | Live. Channel-level (source_id × location_id) — NOT joinable per-order. |
| `fact_payments` | 1 row/payment | Sapo | Live. No payment-gateway fee captured. |

---

## 2. Cost Inventory — What's Captured Today

### Revenue side (Sapo `fact_orders`)
- `gross_revenue` = `total_amount + total_discount_amount` (computed) — pre-discount, pre-tax (= price × qty)
- `discount_amount` = Sapo `$.total_discount` — coupon/voucher/seller-discount/combo, **mixed (no breakdown by type)**
- `net_revenue` = Sapo `$.total` — post-discount, pre-tax
- `tax_amount` = Sapo `$.total_tax` — VAT
- `total_collected` = `net_revenue + tax_amount` — what customer paid

### Line-level (Sapo `fact_sales`)
- `line_amount`, `unit_price`, `quantity`
- `discount_amount` (line-level) + `distributed_discount_amount` (order-level discount allocated to line)

### COGS (MISA `int_misa_sales_lines`)
- `cogs_amount` — purchase cost (per line, aggregated to order in fact_order_economics)
- `revenue_gross`, `discount_amount`, `revenue_net_of_discount`, `gross_profit`, `gross_margin_pct`
- Channel attribution: `channel_code` (DAILY/ECOM/CS/KHAC) + `voucher_source_hint` (SAPO_DEALER/SHOPEE/AEON/OTHER)

### Shopee platform fees (`int_shopee_order_fees`)
- `service_fee`, `payment_fee`, `fixed_fee`, `affiliate_commission_fee`, `piship_service_fee`, `auto_topup_amount` → aggregated `total_platform_fees`
- `infrastructure_fee`, `voucher_xtra_fee` (from Service Fee Details)
- `vat_tax`, `personal_income_tax` → `total_taxes`
- `total_shipping_net` = sum of 6 shipping components (buyer/actual/subsidy/return/piship/failed)
- `total_discounts` = seller voucher + cofunded voucher + coin cashback + cofunded cashback + product subsidy
- `refund_amount`
- `total_adjustment_amount` (marketing fees, compensations)
- `net_settlement` (= `total_paid_amount`) = invariant from Shopee — what Shopee actually paid out

### Fulfillment (`std_fulfillments`)
- `cod_amount`, `carrier_id`, `shipping_service`, `tracking_code` — NOT in any fact table

### Marketing (`fact_marketing_spend`)
- `spend_amount`, `clicks`, `impressions`, `campaign_id`, `spend_code`
- Categories from `ref_spend_category`: Media (FB/Google/TikTok/Shopee/Lazada), KOLs, PR, Seeding, Production, POSM, Software, Affiliate, Opex
- Linked to channel via `source_id + location_id` → `channel_key`
- **No order-level attribution**

---

## 3. Per-Channel Cost Differences

| Channel | Shipping Fee | Platform/Commission | Payment Fee | Discount Source | COGS | Mkt Spend |
|---|---|---|---|---|---|---|
| **Shopee** | ✅ 6-component breakdown | ✅ Full (service/payment/fixed/affiliate/piship) | ✅ Embedded | ✅ Buyer + cofunded + cashback + subsidy | ✅ via MISA voucher_no | Channel-level only |
| **Lazada / Tiki / TikTok / Sendo / Grab / Selly / Chiaki** | ❌ Not captured | ❌ Not captured | ❌ Not captured | Only in Sapo `total_discount` (mixed) | ✅ via MISA voucher_no if SAPO_DEALER/AEON | Channel-level only |
| **POS (Retail)** | N/A | N/A | N/A | Sapo `total_discount` | ✅ via MISA | Not applicable |
| **Web (WebOrder)** | ❌ Not captured | N/A | ❌ Gateway fees not captured | Sapo `total_discount` | ✅ via MISA | Channel-level only |
| **Social (FB/Zalo/Instagram)** | ❌ Not captured (COD via fulfillment.cod_amount only) | N/A | N/A | Sapo `total_discount` | ✅ via MISA | Channel-level only |
| **B2B (Đại Lý / Chợ sỉ)** | ❌ Not captured | N/A | N/A | Sapo `total_discount` (= wholesale price gap, not promotion) | ✅ via MISA | N/A |
| **Internal (US, Test, Quà tặng)** | N/A | N/A | N/A | 100% discount typical | Usually no COGS | Excluded |

### Key observations
- **Shopee is the only channel with full per-order economics**. Schema baked specifically for Shopee invariant (`net_settlement = total_paid_amount`).
- Other marketplaces (Lazada, Tiki, TikTok Shop, Grab) have **zero per-order fee feed** — no ingestion pipeline equivalent to Shopee.
- Sapo's `discount_amount` is a **single mixed value** — cannot decompose into coupon vs. combo vs. employee discount vs. wholesale-price-gap (B2B). Domain doc explicitly warns this pollutes Discount Rate metric → enforced via `scope_retail`.
- Shipping fee NEVER captured for non-Shopee orders. `std_fulfillments.cod_amount` is COD value collected, NOT shipping cost.
- Payment gateway fees (VNPAY/OnePay for Web) are NEVER captured.

---

## 4. Gap Analysis

### Captured today (sufficient for current P&L)
- ✅ Revenue waterfall per order (Sapo)
- ✅ COGS per order (MISA, ~65% coverage)
- ✅ Shopee per-order fees (full breakdown)
- ✅ Gross profit, gross margin %, channel net profit (Shopee-aware)

### Missing — blocks complete per-order P&L
| Cost Type | Captured? | Notes |
|---|---|---|
| Lazada/Tiki/TikTok/Sendo platform fees | ❌ | No ingestion pipeline. Manual entry needed or build per-marketplace ingestors. |
| Shipping fee (carrier cost — non-Shopee) | ❌ | Not in Sapo payload, not in any external source. Need carrier invoice feed (GHTK, J&T, Viettel Post, GHN). |
| Payment gateway fee (Web orders) | ❌ | VNPAY/OnePay statements not ingested. |
| Marketing spend → order attribution | ❌ | Spend is channel × date level only. No campaign_id on Sapo orders, no UTM tracking. |
| Order returns / refunds | ⚠ Partial | `src_sapo_order_returns` exists but no stg/std/fact. `total_amount`, `refund_status` in raw — currently dropped. |
| Discount type breakdown | ❌ | Sapo gives single mixed `total_discount`. `discount_codes` array has codes but no per-code amount allocation. |
| Operating expenses (OpEx) | ❌ | `fact_gl_entries` listed as **Planned** in `domains/finance.md`. |
| Per-order COGS for missing MISA orders | ⚠ ~35% gap | MISA delayed/missing for some channels. Need fallback (avg COGS per SKU from `dim_products`?). |
| Commission per-staff/team | ❌ | No commission table. `team_bonus` is OpEx-level, not per-order. |

### Can we compute per-order P&L today?
- **Shopee orders**: YES — full picture via `fact_order_economics.channel_net_profit`.
- **MISA-covered non-Shopee orders (POS/Web/Social/B2B/other-marketplace)**: PARTIAL — `gross_profit` only (revenue − COGS), missing platform fees + shipping + payment fee → overstates margin.
- **Non-MISA orders (35%)**: NO COGS, only revenue.
- **Internal/US orders**: Excluded by design (`is_sales_channel = false`).

---

## 5. Standardization Recommendations

### Option A: Extend `fact_order_economics` denormalized (Minimal change, KISS)
Add new nullable columns for additional channel platforms when ingestion exists. Keep current Shopee-specific columns; add similar `lazada_*`, `tiktok_*`, `gateway_fee`, `shipping_cost_carrier`, etc. as nullable.

**Pros:** Backward-compatible. Existing dashboards (Dashboard 35, finance_pl, channel_profitability_monthly) keep working unchanged.
**Cons:** Wide table grows with each new marketplace. Hard to query "all fees" uniformly.

### Option B: Normalized `fact_order_costs` table (Long-term, scalable)
Create new fact table:

```sql
-- fact_order_costs: long-format cost ledger, 1 row per (order, cost_type)
order_id        VARCHAR
order_code      VARCHAR
cost_type       VARCHAR  -- 'cogs', 'platform_service', 'platform_payment', 'platform_fixed',
                         -- 'platform_infra', 'platform_voucher_xtra', 'shipping_cost',
                         -- 'payment_gateway', 'commission', 'tax_vat', 'tax_pit',
                         -- 'discount_seller_voucher', 'discount_subsidy', 'adjustment_marketing',
                         -- 'adjustment_compensation', 'refund'
cost_category   VARCHAR  -- 'COGS', 'PLATFORM_FEE', 'SHIPPING', 'PAYMENT', 'TAX', 'DISCOUNT', 'OTHER'
amount          DECIMAL  -- always positive; sign convention in cost_category
source_system   VARCHAR  -- 'sapo', 'misa', 'shopee', 'lazada', 'carrier_gtk', 'gsheet'
source_record   VARCHAR  -- traceability
recorded_at     TIMESTAMPTZ
```

Then `fact_order_economics` becomes a **derived rollup view** that pivots `fact_order_costs` × `fact_orders`.

**Pros:** Adding new cost types = new rows, not new columns. Uniform query across channels. Audit-friendly.
**Cons:** All dashboards must pivot/join. Migration cost is real (5+ blueprints reference `fact_order_economics` columns).

### Option C (Recommended): Hybrid
1. **Keep `fact_order_economics` as the wide P&L table** (consumed by dashboards) — drives existing usage.
2. **Add `fact_order_costs` (long format) as the source of truth** for granular costs (esp. NEW cost types — Lazada fees, shipping invoices, gateway fees). `fact_order_economics` pivots from it.
3. **Backfill** Sapo discount/tax + Shopee fees into `fact_order_costs` so old data is uniform.
4. Standardize sign convention: store `ABS(amount)` always, sign derived from `cost_category`.

### Immediate next steps (Concrete deliverables)
1. **Materialize `std_order_returns` + `fact_order_returns`** — Sapo returns data exists in `src_sapo_order_returns`, just needs staging→std→fact path. This unlocks return rate and refund tracking that currently are missing.
2. **Promote `fulfillment.cod_amount` and carrier into a column on `fact_order_economics`** (single LEFT JOIN). Enables COD reconciliation.
3. **Build per-marketplace fee ingestion** parallel to Shopee. Priority order: Lazada (highest volume after Shopee), TikTok Shop, Tiki.
4. **Create `dim_marketplace_fee_schedules`** seed for marketplaces where we don't get per-order statements — fallback formula (e.g., Lazada = 5% service + 2.85% payment) for estimation.
5. **Decide on marketing-spend attribution model**: top-down (channel × date pro-rated to orders by net_revenue share) vs. campaign-tracked (requires UTM ingestion).

---

## 6. Unresolved Questions

1. **Scope:** Does "per-order P&L" need carrier shipping cost (vendor invoice) or only platform-charged shipping (what Shopee/Lazada deduct)? Carrier invoice = additional ingestion source (likely Excel from GHTK/J&T/Viettel Post/GHN).
2. **Marketing attribution model preference:** top-down channel-pro-rate vs. UTM-tracked campaign_id ingested into Sapo `client_details`?
3. **Lazada/Tiki/TikTok fees priority:** Do we have access to their seller-center exports? If yes, build pipelines analogous to Shopee. If no, fall back to fee-schedule estimation?
4. **Returns data:** What's the desired return-handling logic? Net out from revenue at original order date (restate) vs. recognize at return date (separate fact)?
5. **B2B "discount":** Should wholesale price gap (B2B discount that's structural, not promotional) be excluded from `discount_amount` entirely, or kept and flagged? Current scope_b2b workaround filters at dashboard, not at source.
6. **COGS gap (35% missing):** Acceptable to leave as `has_cogs = false`, or build SKU-level avg-COGS fallback from `dim_products`?
7. **Payment gateway fees:** VNPAY/OnePay statement format — accessible for ingestion?
8. **MISA timing:** MISA lags Sapo by days/weeks. Acceptable that `fact_order_economics` is partial for recent orders, or build a "preliminary P&L" using estimated COGS?

---

**Status:** DONE
**Summary:** Per-order P&L already exists as `fact_order_economics` (Sapo + MISA + Shopee). Gaps: non-Shopee marketplace fees, shipping cost, payment gateway fees, returns flow-through, per-order marketing attribution. Recommend hybrid wide+long schema with `fact_order_costs` as granular ledger feeding rolled-up `fact_order_economics`.
**Concerns/Blockers:** None — research complete. Decisions in Section 6 need user input before any schema change.
