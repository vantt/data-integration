# UI/UX Specs — `detailView` (handoff for `claude design`)

**Date:** 2026-05-29 | **Audience:** `claude design` (visual design) + frontend dev (skeleton)
**Status:** Skeleton built unstyled now; visual design applied later from this spec.

> This document describes STRUCTURE, CONTENT, and BEHAVIOR. Visual design (colors, type, spacing,
> shadows, motion) is intentionally deferred — `claude design` owns that. The skeleton must expose
> clean semantic HTML + stable hooks (`data-*`, class names, slots) so a design system drops in
> without restructuring markup.

---

## 0. Design principles
- **Insight-dense, scannable.** One screen = the whole story of one entity. Minimize clicks.
- **Truth-first.** Always show data-quality caveats inline (never hide that COGS is missing or revenue is US-sourced). Honesty > prettiness.
- **Glance → drill.** Sidebar = at-a-glance identity + headline KPIs (always visible). Main column = deep tabs.
- **Money is the hero** for orders; **segmentation/RFM is the hero** for customers.
- **Calm skeleton.** Until design lands: neutral, semantic, accessible HTML.

## 1. Global shell
### 1.1 Layout grid (every detail page)
- **Two columns, ratio 2 : 1** (main : sidebar). CSS grid `grid-template-columns: 2fr 1fr` with a gap.
- **Sidebar is sticky** (stays in view while main scrolls). On < 900px → stack to single column, sidebar first.
- Max content width ~1280px, centered. Generous vertical rhythm (design TBD).
- Region hooks: `<header class="app-header">`, `<main class="detail-grid">` → `<section class="detail-main">` + `<aside class="detail-sidebar">`.

### 1.2 Floating header (sticky top, on all pages)
Contents, left→right:
- **Brand**: small logo/text "detailView" (links to `/`).
- **Search cluster** (centered, dominant):
  - Segmented control `[ Order | Customer ]` (`data-search-mode`), default Order.
  - Text input: placeholder switches by mode — Order: "Order code e.g. HD00123"; Customer: "Customer ID, phone or email".
  - Submit button (magnifier). Enter submits.
  - Behavior: **HTMX** `hx-get` to `/search?mode=&q=` → server resolves:
    - exactly 1 match → `HX-Redirect` to detail page.
    - multiple customers → render dropdown result list (`#search-results` partial) under the box; each row links to `/customers/{id}` (shows name, phone, value tier).
    - 0 matches → inline "No match" hint in `#search-results`.
- **Context slot** (right): current entity breadcrumb when on a detail page (e.g. "Order HD00123" / "Customer · Nguyễn A"). Optional.
- Header is `position: sticky; top:0; z-index` high; shadow on scroll (design TBD).

### 1.3 Home `/`
Minimal: centered large search (same component), short helper text explaining the two lookups. No data grid.

### 1.4 Shared partials/states
- **Loading** (HTMX tab swap): skeleton rows / spinner in target (`aria-busy`).
- **Empty / not found**: friendly message + "try another code" + back-to-home.
- **Error (503 DB busy)**: "Data refreshing, retry in a moment" + auto-retry button.
- **Badge** component: `kind` (status/payment/fulfillment/value/lifecycle/quality), `tone` (neutral/good/warn/bad), text. Used everywhere.
- **Caveat note** component: small inline callout (info/warn) e.g. "Margin unverified — no MISA COGS match", "Revenue is US CrossBorder", "Timeline available for RETAIL only".
- **KPI stat** component: label, big value, optional sub/delta, optional flag.
- **Money** rendering: VND, thousands separator, ₫ suffix; null → "—".
- **Timestamp** rendering: ICT, `YYYY-MM-DD HH:mm` (+ relative e.g. "3d ago" where useful).

---

## 2. Order Detail — `/orders/{order_code}`

### 2.1 Sidebar (1fr, sticky) — "Order at a glance"
Stacked cards:
1. **Identity**: `order_code` (big), `order_id` (muted). Status badges row: `status`, `payment_status`, `fulfillment_status`.
2. **Money headline**:
   - Effective revenue (domestic: `total_collected`/`net_revenue`; US: `fact_us_shipment_economics.total_us_revenue_incl_vat`) — label adapts + US badge.
   - Gross profit + `gross_margin_pct` (badge "unverified" if `has_cogs=false`).
   - Channel net profit + `channel_net_margin_pct`.
3. **Customer mini-card**: `full_name`, `customer_type` + `value_group` badges, `lifetime_value`. Whole card links → `/customers/{customer_id}`.
4. **Quick facts**: channel name, seller name, branch, created date, first_shipped_at, carrier, COD amount (if any).
5. **Data-quality flags** (chips): `is_us`, `has_cogs`, `has_platform_fees`, `has_returns`.

### 2.2 Main (2fr) — tabbed (HTMX `hx-get=/orders/{code}/tab/{name}` into `#tab-panel`)
Tab order + content:

| Tab | Source | Key content |
|---|---|---|
> Consolidated 8 → **4 tabs** (by user task + usage frequency; sparse single-purpose tabs merged so the wide 2fr column isn't empty). Merged panels reuse the original section partials via `{% include %}`.

| Tab | Source | Key content |
|---|---|---|
| **Financial** (default) | `fact_orders` + `fact_order_economics` (+ `fact_us_shipment_economics` if US) + `fact_order_costs` | Revenue/profit waterfall: gross → −discount → net → +VAT → collected → −COGS → gross profit (margin%) → −Shopee fees → channel net profit (margin%). US: swap to US revenue (excl/incl VAT, line count, unpriced warning). Returns = reference-only note (NOT subtracted). Inline caveats. **+ Cost breakdown section** = `fact_order_costs` grouped by `cost_category` (COGS/PLATFORM_FEE/TAX/SHIPPING/DISCOUNT) w/ cost_type, amount, source_system, source_record, fee_source. |
| **Items** | `fact_sales` × `dim_products` | Table: sku, product/variant, brand, category, qty, unit_price (revenue/qty), line revenue, per-line + distributed discount, weight. Σ vs net_revenue note. US price cols if available. No per-line COGS (note). |
| **Operations** | `fact_orders`/economics + `fact_payments`×`dim_payment_methods` + `fact_order_returns` | Stacked sections — **Fulfillment** (status/payment/fulfillment badges, first_shipped_at, carrier, COD, shipping address, time_to_complete) · **Payments** (method, amount, status, paid_on; COD vs prepaid mix) · **Returns** (per event: date/refund/qty/status/reason; empty-state aware). |
| **Context** | dims + `dim_date`/`dim_time` | Stacked — **Channel & Source** (name/code/category/format/platform/brand/market; promo code(s), max_discount_rate, primary_discount_type) · **Staff/Team** (seller primary, creator, team, branch) · **Timeline** (created/shipped/completed, time_to_complete, paid_on(s), return event(s)). |

### 2.3 Order behaviors
- Tabs lazy-load (only Financial loads on first paint; others on click). Active tab reflected in URL hash for shareability.
- All money/timestamps via shared renderers. Missing → "—".
- US order: Financial + Items adapt automatically based on `is_us` flag.

---

## 3. Customer Detail — `/customers/{customer_id}`

### 3.1 Sidebar (1fr, sticky) — "Customer profile"
1. **Identity**: `full_name` (big), `customer_id` (muted). Badges: `customer_type`, `value_group`, `lifecycle_stage`.
2. **Headline KPIs** (stat grid): `lifetime_value` (hero), `order_count`, AOV (=ltv/orders), `recency_days`.
3. **Contact & geo**: phone, email, address (address1/ward/district/province/country), `geo_region`, `loyalty_points`, birth_date/gender.
4. **Dates**: first_order_date, last_order_date, tenure (`lifespan_days`), account created_at.
5. **Caveats**: acquisition_source unknown; profile sync nightly (not real-time).

### 3.2 Main (2fr) — tabbed (HTMX into `#tab-panel`)

| Tab | Source | Key content |
|---|---|---|
> Consolidated 4 → **3 tabs**: Value Metrics + Behaviour merged into **Overview** (sparse single-metric panels combined).

| Tab | Source | Key content |
|---|---|---|
| **Overview** (default) | `dim_customers` + aggregates over `fact_orders`/`fact_order_economics` | Stacked — **Value metrics** (LTV, total orders, AOV, value_group; total gross profit, total COGS, avg margin % w/ COGS-coverage caveat; total returns) · **Behaviour/RFM** (Recency/Frequency/Monetary; segmentation chips: lifecycle_stage, channel_preference, product_affinity, payment_behavior, geo_region, customer_type; cohort month = trunc(first_order_date)). |
| **Status Timeline** | `mart_customer_status_snapshot_monthly` | 24-month horizontal strip of monthly status (ACTIVE/AT_RISK/CHURNED), is_new marker on acquisition month, days_since_last_order tooltip, value_group trend (approx note). **RETAIL only** — non-RETAIL → "RETAIL only" notice, no data. |
| **Order History** | `fact_orders` × economics × dims | Table (newest first): order_code (→ links to order page), date, status, channel, seller, total_collected, gross_profit + margin%, discount info, payment method, return flag, carrier. Pagination/scroll if long. |

### 3.3 Customer behaviors
- Order History rows: entire row clickable → `/orders/{order_code}` (HTMX boost or full nav).
- Status Timeline tab hidden/disabled w/ tooltip when `customer_type != 'RETAIL'`.
- AOV, cohort computed in domain, not SQL-dependent display.

---

## 4. Component inventory (for design system)
- Floating header + search cluster (segmented control, input, results dropdown).
- Two-column responsive grid (2fr/1fr → stack).
- Tab bar + lazy panel (HTMX target, loading/empty states).
- Sidebar card (variants: identity, KPI grid, contact, mini-card-link).
- KPI stat, Badge (6 kinds × tones), Caveat note (info/warn), Money/Timestamp inline.
- Data table (sortable later), grouped table (cost ledger), vertical waterfall list, vertical timeline, horizontal month strip.
- Empty/Not-found, Error/503 states.

## 5. Accessibility & responsive (skeleton must satisfy)
- Semantic landmarks (`header/main/aside/nav`), `<table>` for tabular data, tabs with `role=tablist/tab/tabpanel` + `aria-selected`, keyboard-navigable, focus-visible.
- Color is never the only signal (badges have text). Respect prefers-reduced-motion.
- Breakpoints: ≥1100px two-col; 700–1100 narrower main; <700 single column (sidebar collapses to top summary).

## 6. HTMX interaction contract (skeleton)
- Search: `hx-get /search`, target `#search-results`, `HX-Redirect` on single hit.
- Tabs: `hx-get /orders/{code}/tab/{name}` & `/customers/{id}/tab/{name}`, target `#tab-panel`, `hx-push-url` (hash) for deep link, `hx-indicator` for loading.
- Disambiguation list + order-history row navigation via `hx-boost`/links.
- No client framework; htmx.min.js from local `static/` (vendored, not CDN, for offline/LAN).

## 7. Design handoff notes (`claude design`)
- Deliver tokens (color/type/space/radius/shadow), then style: header, cards, badges, tables, tabs, timeline strip, waterfall. Keep markup; add classes/tokens only.
- Two moods to explore: (a) "ops console" dense/utilitarian; (b) "insight report" airy/editorial. Pick per stakeholder.
- Charts optional later (e.g. mini sparkline for status timeline / margin) — not required for skeleton.

---

## 8. ASCII Layout Mockups (section-by-section)

> Wireframe intent only — boxes = regions/components, not final styling. Annotations in `« »`
> map a region to its data source. `[badge]` = Badge component, `{ }` = dynamic value.

### 8.1 Global floating header (every page)
```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│  detailView      ┌─────────────────────────────────────────────────┐         Order HD00123 │
│  «brand /»        │ (•Order ) ( Customer )  [ HD00123________ ] (🔍) │          «context slot»│
│                  └─────────────────────────────────────────────────┘                        │
│                   ▲ segmented mode toggle   ▲ text input (placeholder per mode)  ▲ submit     │
└───────────────────────────────────────────────────────────────────────────────────────────┘
        │ on submit → HTMX GET /search?mode=&q=  →  HX-Redirect (1 hit) | dropdown (N) | hint (0)
        ▼
   ┌──────────────────────────────┐   ← #search-results (only for multi-customer match)
   │ Nguyễn A · 09xx · [VALUE_VIP] │      each row → /customers/{id}
   │ Trần B   · 09yy · [GOLD]      │
   └──────────────────────────────┘
```

### 8.2 Home `/`
```
┌───────────────────────────────────── header (8.1) ─────────────────────────────────────────┐
└─────────────────────────────────────────────────────────────────────────────────────────────┘
                          ┌───────────────────────────────────────────┐
                          │   Look up the full story of one entity     │
                          │   ( •Order ) ( Customer )                  │
                          │   [ enter order code / customer id … ] (🔍)│
                          │   Order: HD00123   ·   Customer: id/phone  │
                          └───────────────────────────────────────────┘
```

### 8.3 Order Detail `/orders/{order_code}` — full page (grid 2fr : 1fr)
```
┌──────────────────────────────────────── header (8.1) ──────────────────────────────────────────┐
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
┌───────────────────── MAIN  (2fr) ─────────────────────┐ ┌──────── SIDEBAR (1fr, sticky) ────────┐
│ ┌ tab bar ─────────────────────────────────────────┐ │ │ ┌─ Identity ───────────────────────┐ │
│ │ [•Financial] Line Items  Cost  Payments  Fulfil… │ │ │ │  HD00123          «order_code»    │ │
│ │  Returns  Channel&Staff  Timeline                │ │ │ │  id 4821          «order_id»      │ │
│ └──────────────────────────────────────────────────┘ │ │ │  [COMPLETED][PAID][SHIPPED_COD]   │ │
│ ┌ #tab-panel  (HTMX target) ───────────────────────┐ │ │ └──────────────────────────────────┘ │
│ │  see 8.4 per-tab detail                          │ │ │ ┌─ Money headline ─────────────────┐ │
│ │                                                  │ │ │ │  Net revenue     1.250.000 ₫     │ │
│ │                                                  │ │ │ │  Gross profit      380.000 ₫ 30% │ │
│ │                                                  │ │ │ │   ⤷ [margin unverified] if !cogs │ │
│ │                                                  │ │ │ │  Channel net       past fees …   │ │
│ │                                                  │ │ │ └──────────────────────────────────┘ │
│ │                                                  │ │ │ ┌─ Customer mini-card → link ──────┐ │
│ │                                                  │ │ │ │  Nguyễn A  [RETAIL][VALUE_VIP]   │ │
│ │                                                  │ │ │ │  LTV 52.000.000 ₫   →/customers/ │ │
│ │                                                  │ │ │ └──────────────────────────────────┘ │
│ │                                                  │ │ │ ┌─ Quick facts ────────────────────┐ │
│ │                                                  │ │ │ │ channel · seller · branch        │ │
│ │                                                  │ │ │ │ created · shipped · carrier · COD │ │
│ │                                                  │ │ │ └──────────────────────────────────┘ │
│ │                                                  │ │ │ ┌─ Data-quality flags ─────────────┐ │
│ │                                                  │ │ │ │ [is_US?][has_cogs][fees][returns]│ │
│ └──────────────────────────────────────────────────┘ │ │ └──────────────────────────────────┘ │
└───────────────────────────────────────────────────────┘ └────────────────────────────────────────┘
```

### 8.4 Order tabs — panel detail (rendered inside #tab-panel)
```
FINANCIAL (default)  «fact_orders + fact_order_economics (+ fact_us_shipment_economics if US)»
┌──────────────────────────────────────────────────────────────────────────────┐
│  Revenue waterfall                                                             │
│    Gross revenue                                       1.400.000 ₫             │
│  − Discount                                             −150.000 ₫  [bundle]   │
│  = Net revenue                                          1.250.000 ₫            │
│  + VAT (8%)                                             +100.000 ₫             │
│  = Total collected                                      1.350.000 ₫            │
│  − COGS «MISA»                                          −870.000 ₫  [has_cogs] │
│  = Gross profit                       380.000 ₫  · margin 30.4%                │
│  − Shopee fees (service/payment/infra/voucher_xtra/tax) −60.000 ₫              │
│  = Channel net profit                 320.000 ₫  · margin 25.6%                │
│  ----------------------------------------------------------------------------  │
│  ⓘ Returns: 0 ₫ (reference only — not subtracted from this order's P&L)        │
│  ⚠ if US order → swap revenue block: US revenue excl/incl VAT, line count,     │
│     [US CrossBorder] badge, ⚠ unpriced SKU warning if has_unpriced_sku         │
└──────────────────────────────────────────────────────────────────────────────┘

LINE ITEMS  «fact_sales × dim_products»                COST LEDGER  «fact_order_costs»
┌───────────────────────────────────────────────┐     ┌──────────────────────────────────────┐
│ SKU    Product/Variant   Brand  Qty  Unit  Line│     │ ▾ COGS                    870.000 ₫    │
│ A-01   Cream 50ml        FINE    2  300k  600k │     │    cogs   misa  voucher_no=HD..  actual│
│ B-12   Serum / Large     FG      1  650k  650k │     │ ▾ PLATFORM_FEE             60.000 ₫    │
│ …                                              │     │    platform_service shopee … estimated │
│ ───────────────────────────────────────────── │     │ ▾ TAX / SHIPPING / DISCOUNT  …         │
│ Σ line revenue 1.250k  ✓ matches net_revenue   │     │   (each row: type·amount·source·trace) │
│ ⓘ no per-line COGS (order-level only)          │     │   category subtotals                   │
└───────────────────────────────────────────────┘     └──────────────────────────────────────┘

PAYMENTS «fact_payments×dim_payment_methods»   FULFILLMENT «fact_orders+economics»   RETURNS «fact_order_returns»
┌────────────────────────────────────────┐   ┌────────────────────────────────┐   ┌──────────────────────────┐
│ Method   Amount   Status  Paid_on       │   │ [status][payment][fulfillment] │   │ Date  Refund  Qty  Reason│
│ COD     1.350k    paid    2026-05-20    │   │ first_shipped_at · carrier     │   │ —— empty state if none ——│
│ Σ paid 1.350k · COD vs prepaid mix      │   │ COD · ship addr · TTC hours    │   │ totals: count · amount   │
└────────────────────────────────────────┘   └────────────────────────────────┘   └──────────────────────────┘

CHANNEL & STAFF «dims»                                   TIMELINE «fact_orders + dim_date/dim_time»
┌──────────────────────────────────────────────┐        ┌────────────────────────────────────────┐
│ Channel  name/code/category/format/platform   │        │ ● created  2026-05-18 14:20 (ICT)        │
│          brand · market(Domestic/Export)      │        │ │  day_period=afternoon · business_hour  │
│ Promo    code(s) · max_rate · primary_nature  │        │ ● first shipped  2026-05-19              │
│ Seller   {name}  (primary)                    │        │ ● completed  2026-05-21 · TTC 70h        │
│ Creator  {name}   Team {team}   Branch {br}   │        │ ● payment paid_on / ● return events …    │
└──────────────────────────────────────────────┘        └────────────────────────────────────────┘
```

### 8.5 Customer Detail `/customers/{customer_id}` — full page (grid 2fr : 1fr)
```
┌──────────────────────────────────────── header (8.1) ──────────────────────────────────────────┐
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
┌───────────────────── MAIN  (2fr) ─────────────────────┐ ┌──────── SIDEBAR (1fr, sticky) ────────┐
│ ┌ tab bar ─────────────────────────────────────────┐ │ │ ┌─ Identity ───────────────────────┐ │
│ │ [•Value Metrics] Behavior  Status Timeline  Orders│ │ │ │  Nguyễn A         «full_name»     │ │
│ └──────────────────────────────────────────────────┘ │ │ │  id 7781                          │ │
│ ┌ #tab-panel (HTMX) ───────────────────────────────┐ │ │ │  [RETAIL][VALUE_VIP][ACTIVE]      │ │
│ │ VALUE METRICS (default):                         │ │ │ └──────────────────────────────────┘ │
│ │  ┌ LTV ──────┐ ┌ Orders ┐ ┌ AOV ───┐ ┌ Recency ┐│ │ │ ┌─ Headline KPIs ──────────────────┐ │
│ │  │52.000.000₫│ │   24   │ │2.16M ₫ │ │  12 d   ││ │ │ │  LTV 52.000.000 ₫  (hero)        │ │
│ │  └───────────┘ └────────┘ └────────┘ └─────────┘│ │ │ │  orders 24 · AOV 2.16M · rec 12d │ │
│ │  Gross profit contributed · total COGS ·         │ │ │ └──────────────────────────────────┘ │
│ │  avg margin% [⚠ ~65% COGS coverage] · returns    │ │ │ ┌─ Contact & geo ──────────────────┐ │
│ │                                                  │ │ │ │ 09xx · email · address1/ward/…   │ │
│ │  (other tabs: see 8.6)                           │ │ │ │ geo_region · loyalty · birth_date/gender   │ │
│ └──────────────────────────────────────────────────┘ │ │ └──────────────────────────────────┘ │
│                                                       │ │ ┌─ Dates ──────────────────────────┐ │
│                                                       │ │ │ first 2024-02 · last 2026-05     │ │
│                                                       │ │ │ tenure 820d · created 2024-01    │ │
│                                                       │ │ └──────────────────────────────────┘ │
│                                                       │ │ ⓘ acquisition unknown · sync nightly  │
└───────────────────────────────────────────────────────┘ └────────────────────────────────────────┘
```

### 8.6 Customer tabs — panel detail
```
BEHAVIOR (RFM + segmentation) «dim_customers»          STATUS TIMELINE «mart_customer_status_snapshot_monthly»
┌────────────────────────────────────────────┐        ┌────────────────────────────────────────────────────┐
│  R  recency 12d   F  24 orders   M  52.0M ₫ │        │ 2024-06 … ……………………………… 2026-05  (24 months)         │
│  ┌ Recency ┐ ┌ Frequency┐ ┌ Monetary ┐      │        │  A A A A R A A A … A A A R R C  ← ACTIVE/AT_RISK/CHURN│
│  Segments:                                   │        │  ▲is_new (acquisition month)                         │
│  [LIFECYCLE_ACTIVE][CHANNEL_SOCIAL]          │        │  hover → days_since_last_order · value_group(approx) │
│  [PRODUCT_FINE_JAPAN][PAYMENT_COD]           │        │  ⚠ RETAIL only → if not RETAIL: notice, no strip     │
│  [GEO_HCMC][RETAIL]  · cohort 2024-02        │        └────────────────────────────────────────────────────┘
└────────────────────────────────────────────┘
ORDER HISTORY «fact_orders × economics × dims»  (rows → /orders/{code})
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Code     Date        Status     Channel    Seller   Total      GP     Margin Pay  Ret    │
│ HD00123  2026-05-18  COMPLETED  Shopee     Linh    1.350.000  380k   30%   COD   —      │ → click row
│ HD00098  2026-04-02  COMPLETED  Facebook   Linh      820.000  210k   26%   PRE   ↩1     │
│ …  (newest first, scroll/paginate if long)                                               │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 8.7 Responsive stack (< 700px) & shared states
```
< 700px: single column          NOT FOUND                503 DB BUSY            TAB LOADING
┌───────────────┐               ┌──────────────────┐     ┌──────────────────┐   ┌──────────────┐
│ header        │               │  🔍 No match for │     │ Data refreshing… │   │ ░░░ skeleton │
│ sidebar (top) │               │  "HD99999"       │     │ retry in a moment│   │ ░░░ rows     │
│ tab bar       │               │  ( back home )   │     │ ( retry )        │   │ aria-busy    │
│ tab panel     │               └──────────────────┘     └──────────────────┘   └──────────────┘
└───────────────┘
```

---

## 9. Shipments section — design brief (for `claude design`)

**What:** an order can ship in one or more legs (avg ~1–3). This section shows every shipment of the
order. **Placement:** FIRST section of the **Operations** tab (above Fulfillment · Payments · Returns).
**Source:** `fact_fulfillments` → domain `Shipment` (one card/row per leg).

### Data per shipment (what to surface, by priority)
| Field | Display | Priority |
|---|---|---|
| `status` | **Hero** — status badge w/ tone: DELIVERED=good · SHIPPING/PENDING=warn · PACKED=neutral · CANCELLED/FAILED=bad | ★★★ |
| `tracking_code` | monospace, **copy-on-click**; the thing CS reads to the customer / pastes into a carrier site | ★★★ |
| `carrier_id` + `shipping_service` | carrier name + service tier (e.g. "SPX · Standard") | ★★ |
| `fulfillment_code` | the shipment's human code (e.g. `FUN18213`) — secondary identifier | ★★ |
| `shipped_at` | date-time ICT (relative ok, e.g. "2d ago"); NULL = "not shipped yet" | ★★ |
| `cod_amount` | VND money, only if > 0 → emphasize (COD shipments matter operationally) | ★★ |
| `created_at` | date-time ICT, muted | ★ |
| `fulfillment_id` | **de-emphasize / omit** — internal numeric id, can be negative; not user-facing | ☆ |

### Layout & behaviour
- **Multiple legs → vertical list of compact cards** (not a wide sparse table). Each card: status badge top-left,
  carrier+service top-right, tracking_code as a prominent copyable line, then a small meta row (code · shipped_at · COD).
- **Order legs newest-first** (`shipped_at` desc, NULLs last — i.e. not-yet-shipped legs at the end or flagged).
- **Section header**: "Shipments" + count chip (e.g. "Shipments · 2"); optional one-line summary of the mix
  (e.g. "1 delivered · 1 shipping").
- **Status as the visual anchor** — a viewer should grok delivery state in <1s. Consider a tiny stage indicator
  PACKED → SHIPPING → DELIVERED (with CANCELLED/FAILED as a distinct error treatment) — optional, nice-to-have.
- **tracking_code**: monospace + a copy affordance; do NOT auto-link (we have no per-carrier tracking-URL map yet —
  leave a hook/comment for a future `carrier → tracking-URL` template).
- **COD**: when present, give it a small money emphasis (it's cash the carrier collects).

### States
- **No shipments** (order not yet fulfilled): calm empty-state — "No shipments yet" + the order's
  `fulfillment_status` for context. Don't show an empty table shell.
- **Single shipment**: same card, no count chip needed.
- **Long tracking codes**: must not overflow on mobile — wrap or truncate-with-copy.

### A11y / responsive / mood
- Semantic: a list (`<ul>`/cards) or a `<table>` with real headers; status badge carries **text** (not color-only).
- < 700px: cards stack full-width; tracking_code stays fully visible/copyable.
- Mood: same "ops console" system as the rest — dense, scannable, tabular-nums for money/dates. Shipment status
  is the one place a little color/iconography earns its keep.

### ASCII intent
```
Shipments · 2          1 delivered · 1 shipping
┌───────────────────────────────────────────────────────────┐
│ [DELIVERED]                               SPX · Standard    │
│ Tracking  SPXVN063279123185                          ⧉ copy │
│ Code FUN18213 · shipped 2026-05-28 14:20 (ICT) · COD 350.000₫│
└───────────────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────────────┐
│ [SHIPPING]                                GHTK · Express    │
│ Tracking  GHTK20260529X8821                          ⧉ copy │
│ Code FUN18250 · not shipped yet · COD —                     │
└───────────────────────────────────────────────────────────┘

empty:  ┌────────────────────────────────────────────┐
        │  No shipments yet · fulfillment: IN_PROGRESS │
        └────────────────────────────────────────────┘
```

### Caveats for the designer
- One order ↔ many shipments (design for N, not 1). Some legs have NULL `shipped_at` / NULL `cod_amount`.
- `fulfillment_id` is internal (may be negative) — never feature it; `fulfillment_code` + `tracking_code` are the human keys.
- This section is **searchable**: users can find the order by typing the shipment code / id / tracking code in the
  header search — so those values shown here should be exact + copyable.

---

## 10. Returns section — design brief (for `claude design`)

**What:** per-return events for the order (refunds / goods returned). **Placement:** LAST section of the
**Operations** tab (after Shipments · Fulfillment · Payments). **Source:** `fact_order_returns` → domain
`ReturnEvent`. **Reality check (live data):** returns are LOW-VOLUME — most orders have **0**, those that
do usually have **1** (rarely more). Optimize for the empty + single case; still handle N.

### Data per return (priority high→low)
| Field | Display | Priority |
|---|---|---|
| `refund_amount` | **Hero** — VND money returned to customer | ★★★ |
| `refund_status` | badge — `paid`=good (refund done) · `unpaid`=warn (pending). Raw lowercase → Title-case it. | ★★★ |
| `return_status` | badge — `returned`=neutral/info · `cancelled`=muted/bad. Raw lowercase → Title-case. | ★★ |
| `return_date` | date (ICT), relative ok | ★★ |
| `return_quantity` | qty of units returned; **often NULL → "—"** | ★ |
| `return_reason` | free text (Vietnamese), **often blank → "No reason recorded"** (muted) | ★ |

### Layout & behaviour
- Low volume → **compact card(s)** (or a tight table). Single return = one card; no count chrome needed.
- Each card: `refund_amount` as the anchor number; two status badges (refund + return); a muted meta row
  (date · qty · reason).
- If multiple: list newest-first by `return_date`; section header "Returns · N" + **total refunded** sum.
- **Reconciliation note (important):** returns are recognized at return date and are **NOT subtracted from this
  order's P&L** — show a one-line caveat ("Reference only — not deducted from order profit") consistent with the
  Financial tab's returns note. This context matters so users don't double-count.

### States
- **No returns** (the common case): calm empty state — "No returns" (single muted line). This is normal/healthy,
  NOT an error tone. Don't render an empty table shell.
- **Blank reason / NULL quantity:** graceful placeholders ("No reason recorded" / "—"), never empty gaps.
- **Large refund** (seen up to ~21.6M₫): money must stay readable/aligned (tabular-nums).

### A11y / responsive / mood
- Status badges carry TEXT (Title-cased), not color-only. List or table with real headers.
- < 700px: cards stack full-width; money right-aligned/tabular.
- Mood: same "ops console". Returns is muted by default (low signal); the refund money + refund_status are the
  only things that should pop.

### ASCII intent
```
Returns · 1                                 total refunded 2.472.945₫
┌───────────────────────────────────────────────────────────┐
│ 2.472.945 ₫                       [Refund: Paid] [Returned] │
│ 2026-01-12 (ICT) · qty —                                    │
│ Reason: KHÁCH TRẢ HÀNG                                      │
└───────────────────────────────────────────────────────────┘
ⓘ Reference only — returns are not deducted from this order's P&L.

empty:  ┌──────────────────────────┐
        │  No returns               │
        └──────────────────────────┘
```

### Caveats for the designer
- `return_status` / `refund_status` are RAW lowercase Sapo values (`returned`/`cancelled`, `paid`/`unpaid`) —
  Title-case in the UI; map to tones above.
- `return_reason` is unstructured Vietnamese and frequently empty; `return_quantity` frequently NULL — design
  must look intentional when these are absent.
- Order-level totals (`return_amount`, `return_count`) already appear as a reference note on the Financial tab;
  this section is the per-event detail. Keep them consistent, not contradictory.
