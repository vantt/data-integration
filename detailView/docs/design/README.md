# Handoff: detailView — Order & Customer Insight Console

> Read-only internal **ops console** for an e-commerce data warehouse. One screen tells the
> whole story of one entity (an order or a customer). Dense, scannable, truth-first.

---

## Overview

`detailView` is an internal tool for operations / finance / CX staff to look up a single **order**
or **customer** and read its complete story — money waterfall, line items, cost ledger, fulfillment,
shipments, payments, returns, channel/staff, and timelines. It is **read-only** (no mutations) and
**insight-dense**: data-quality caveats are shown inline, never hidden.

This bundle documents the whole app, with extra depth on the two sections most recently designed:
**Shipments** and **Returns** (both inside the order **Operations** tab).

---

## About the design files

The files under `app/` are a **design reference built in HTML + React (inline JSX via Babel)** — a
working, click-through prototype that shows the intended look, layout, copy, and behavior. They are
**not** meant to ship as-is. The task is to **recreate these designs in the target codebase's real
environment**, using its established patterns and libraries.

The team's stated target stack (see `app/data/` and markup hooks) is **server-rendered HTML + HTMX**,
no client framework — the prototype's React is only a convenience for prototyping. The markup,
class names, `data-*` hooks, and token system are all designed to drop into a server-rendered
template + CSS setup without restructuring. If you implement in React/Vue/etc. instead, the same
component boundaries apply.

**To run the prototype:** open `app/index.html` in a browser. Navigate with the search box, or use
hash deep-links (see Routing).

---

## Fidelity

**High-fidelity (hifi).** Final colors, typography, spacing, motion, and interactions. Recreate the
UI pixel-faithfully using the codebase's libraries. All values are tokenized — pull them from
`design_system/colors_and_type.css` and `app/styles/app.css`, do not hand-type hexes.

---

## Design system: "Precision"

The app is built on the **Precision** design system (full reference in `design_system/`).
Character: editorial, sparse chrome, warm-desaturated ink ramp, **one accent** (amber) used only when
something is *true, wrong, or actionable*. Three semantic accents beyond neutral: moss (good),
honey (warning), coral (bad). System loads three Google Fonts: **Fraunces** (display, used sparingly),
**Geist** (body), **Geist Mono** (labels, data, all numbers).

- `design_system/colors_and_type.css` — the authoritative token file (`:root` custom properties). **Copy this in verbatim.**
- `design_system/PRECISION_GUIDE.md` — the full written guide (voice, color, type, spacing, motion, components).
- `app/styles/precision.css` — the same tokens + base primitives, as vendored into this app.
- `app/styles/app.css` — the app shell + every component style built on top (header, tabs, cards, tables, waterfall, timeline, strip, **shipments**, **returns**, states).

### Core tokens (names — read values from the CSS)

| Group | Tokens |
|---|---|
| Ink ramp | `--ink-000`…`--ink-900` (warm grays; page=`--ink-050`, card=`--ink-100`, raised=`--ink-150`) |
| Semantic | `--accent`(amber) `--success`(moss) `--warning`(honey) `--danger`(coral) + `--*-bg` tints |
| Text | `--fg` `--fg-1` `--fg-2` `--fg-muted` `--fg-tertiary` `--fg-disabled` |
| Surface | `--bg-page` `--bg-surface` `--bg-raised`; borders `--border` `--border-strong` `--border-amber` |
| Type | `--font-display` `--font-body` `--font-mono`; sizes `--fs-display`…`--fs-micro`; weights `--fw-*` |
| Spacing | `--sp-0:0 --sp-1:4 --sp-2:8 --sp-3:12 --sp-4:16 --sp-5:24 --sp-6:36 --sp-7:56 --sp-8:80` (px) |
| Radii | `--radii-hairline:2 --radii-control:4 --radii-soft:8 --radii-pill:999` (px) |
| Motion | `--dur-fast:120 --dur-settle:200 --dur-open:260` ms; eases `--ease-fast/-settle/-open` |

**Theming:** `<html data-theme="dark|light">` flips the ink ramp meaning (dark default; light = warm
paper). `data-density="comfortable|compact"`, `data-numfont="mono|sans"`, `data-accent="amber|moss|honey"`,
`data-lang="en|vi"` are all live switches (exposed in the prototype's Tweaks panel). **All component
CSS uses only `var(--*)` tokens**, so dark/light and accent swaps require no per-component work.

---

## Architecture & file map (`app/`)

```
index.html            shell: font links, stylesheets, script load order, React/Babel pins
styles/
  precision.css       design-system tokens + primitives (vendored)
  app.css             app shell + all component styles  ← most CSS lives here
data/
  mock.js             window.DV_DATA — customers{}, orders{}, search index, mock generators
components/           inline-JSX (Babel) — each exports to window at file end
  ui.jsx              primitives: tr(), Money, Pct, Badge, Caveat, Kpi, StatusPill, Eyebrow, Sparkline
  header.jsx          floating header: brand, segmented Order/Customer search, results, context crumb
  financial.jsx       REDESIGNED Financial tab: verdict addons, composition bar, PL waterfall, cost ledger, COGS recon
  orderTabs.jsx       all order tab panels (Financial delegates to financial.jsx, Items, Operations*, Context)
  order.jsx           order shell: tab bar + sidebar ("Order at a glance")
  customerTabs.jsx    customer tab panels (Value & Behavior, Status Timeline, Order History)
  customer.jsx        customer shell: tab bar + sidebar ("Customer profile")
  app.jsx             router (hash), shared states (NotFound, 503), Tweaks panel
tweaks-panel.jsx      prototype-only control panel (NOT part of the product)
assets/icons/         hand-drawn SVGs (copy, check-tiny, cog, arrow-right) — 1.3–1.6 stroke, round caps
```

Each `components/*.jsx` is a separate Babel script; shared symbols are published via
`Object.assign(window, {...})` at the bottom of each file. In a real build these become normal modules.

### Routing (hash deep-links)

`app.jsx → parseHash()` maps the URL hash to a route, and a `hashchange` listener keeps it live
(shareable deep-links, per spec):

- `#/order/<order_code>` or `#/order/<order_code>/<tab>` — tab ∈ `financial | items | operations | context`
- `#/customer/<customer_id>` or `#/customer/<id>/<tab>` — tab ∈ `value | timeline | orders`
- empty hash → Home

In the prototype, an order's tab is only applied from the hash on first mount of that order; tab
switches thereafter are internal state. In the real (HTMX) app, tabs are `hx-get` lazy-loads with
`hx-push-url` writing the hash — implement that contract.

---

## Screens

Screenshots in `screens/` (dark theme, ~1305px wide desktop). Two-column grid everywhere:
**main 2fr : sidebar 1fr**, sidebar sticky, collapses to single column < 860px (sidebar moves to top).

| # | File | Screen |
|---|---|---|
| 01 | `01-home.png` | **Home** — centered search only (segmented Order/Customer toggle, mono input, hint line). No data grid. |
| 02 | `02-order-financial.png` | **Order ▸ Financial** (default tab) — REDESIGNED. Verdict + COGS badge + fully-loaded footnote → composition bar → 4-col waterfall (op \| label \| % \| amount) → decision tier → overhead footer → cost ledger (+ OVERHEAD/PROMO_GOODS) → COGS reconciliation. |
| 02b | `02b-order-financial-waterfall.png` | Financial waterfall detail — % column aligned, decision tier (Channel net profit) emphasized in moss. |
| 02c | `02c-order-financial-costs-recon.png` | Cost breakdown with ledger groups + OVERHEAD NEW tag. |
| 02d | `02d-order-financial-bottom.png` | OVERHEAD group expanded + COGS reconciliation collapsed panel. |
| 02e | `02e-order-financial-recon.png` | COGS reconciliation showing Sapo-MAC vs MISA-632 variance. |
| 11 | `11-order-financial-loss.png` | **Loss order (HD00251)** — coral verdict, composition bar showing loss segment, fully-loaded deepens loss. |
| 12 | `12-order-financial-unverified.png` | **Unverified order (HD00076)** — graceful degradation: no composition bar, no overhead, no recon. |
| 13 | `13-order-financial-promo.png` | **Promo goods order (HD00098)** — shows Promo goods cost row between Gross profit and Channel net. |
| 03 | `03-order-items.png` | **Order ▸ Items** — line-item table (SKU, product/variant, brand, qty, unit, line, discount, weight), Σ reconciliation vs net revenue, "no per-line COGS" note. |
| 04 | `04-order-operations-top.png` | **Order ▸ Operations** (top) — Recipient & delivery, then Fulfillment. |
| 05 | `05-order-operations-shipments.png` | **Order ▸ Operations ▸ Shipments** — leg-level shipment cards (detailed below). |
| 06 | `06-order-operations-returns.png` | **Order ▸ Operations ▸ Payments + Returns** — payments table; multi-return cards (detailed below). |
| 07 | `07-order-context.png` | **Order ▸ Context** — channel & staff facts + vertical event timeline. |
| 08 | `08-customer-value.png` | **Customer ▸ Value & Behavior** (default) — KPI grid (LTV/orders/AOV/recency), RFM, segmentation chips. |
| 09 | `09-customer-timeline.png` | **Customer ▸ Status Timeline** — 24-month ACTIVE/AT_RISK/CHURNED strip (RETAIL only; disabled otherwise). |
| 10 | `10-customer-orders.png` | **Customer ▸ Order History** — newest-first table, each row links to its order. |

**Order Operations tab — section order (top→bottom):**
`Recipient & delivery → Fulfillment → Shipments → Payments → Returns`.

### Shared sidebars
- **Order "at a glance":** identity (`order_code` big mono, `order_id` muted), status badge row, money headline (net revenue hero, gross profit + margin, channel net), recipient/buyer card (links to customer), quick facts, data-quality flags.
- **Customer profile:** identity (name in Fraunces, id muted), badge row, headline KPIs, contact & geo facts, dates.

### Shared states (in `app.jsx`)
- **Not found** — Fraunces-italic "No match" + the queried code + back-home.
- **503 DB busy** — "Data refreshing" + retry (toggle via Tweaks ▸ Demo states).
- **Tab loading** — shimmer skeleton rows (`aria-busy`), simulating HTMX lazy swap.

---

## ▸ Section spec: SHIPMENTS  (`OrderShipments` in `orderTabs.jsx`; CSS `.ship-*` in `app.css`)

Leg-level fulfillment. An order has **0..N** shipment legs (avg 1–3). Designed for N, optimized for the
common 1–2 case. See `screens/05`.

### Data per shipment (priority high→low)
| Field | Notes |
|---|---|
| `status` | hero badge — one of `DELIVERED · SHIPPING · PACKED · PENDING · CANCELLED · FAILED` |
| `tracking_code` | monospace, prominent, **copy-on-click** (e.g. `GHN05582104567`). Not auto-linked (no carrier-URL map yet — leave room). |
| `carrier` + `shipping_service` | e.g. `GHN · Standard` (top-right, mono caption) |
| `fulfillment_code` | secondary human id, e.g. `FUN18213` |
| `shipped_at` | datetime ICT; may be **NULL → "not shipped yet"** |
| `cod_amount` | VND; **show emphasized only when > 0** (cash the carrier collects); else `COD —` muted |
| `created_at` | datetime ICT, muted |

> **Never display `fulfillment_id`** (internal numeric, can be negative).

### Status → badge tone
`DELIVERED`=good(moss) · `SHIPPING`/`PENDING`=warn(amber) · `PACKED`=neutral · `CANCELLED`/`FAILED`=bad(coral).
Badges **always carry the status text** (never color-only).

### Layout
- **Section header:** title "Shipments" + count chip (only when N>1) + a one-line status **summary** on the right (e.g. "1 delivered · 1 shipping") with small tone dots.
- **Vertical list of compact cards**, sorted **newest-first by `shipped_at`, NULLs last**.
- **Card:**
  - Top row: status badge + a tiny **stage stepper** `PACKED → SHIPPING → DELIVERED` (left); `carrier · service` (right). `CANCELLED`/`FAILED` render the stepper as a coral ✕ error marker.
  - **Tracking line** (the card's hero): `TRACKING` eyebrow, the code in mono ~18px, and a copy affordance flush right — framed by top+bottom hairlines (echoes the Precision "password slab"). Long codes wrap (`overflow-wrap:anywhere`), never overflow.
  - Meta row (muted): `fulfillment_code · shipped <datetime> (ICT · rel) · COD <amount|—>`.
- One-line caveat: "Tracking codes are copy-only — no carrier link map in the serving layer yet."

### Behavior
- **Copy:** clicking the tracking line copies `tracking_code` to clipboard, flashes a soft amber wash across the line + accent card border for ~1.5s, and swaps the affordance to a check glyph + "copied" (Precision `motion/settle`). Graceful fallback if `navigator.clipboard` is unavailable.
- **Cancelled/failed legs:** the tracking code is struck through (voided) and de-emphasized.

### Empty state
No card shell — a calm muted line "No shipments yet" plus the order's `fulfillment_status` badge for context.

### Demo orders
`HD00123` = DELIVERED + SHIPPING (COD on delivered leg) · `HD00210` = SHIPPING + PACKED (null `shipped_at`, intl) · `HD00098` = single DELIVERED · `HD00076` = DELIVERED + CANCELLED.

---

## ▸ Section spec: RETURNS  (`OrderReturns`/`ReturnCard` in `orderTabs.jsx`; CSS `.ret-*` in `app.css`)

Last section of the Operations tab. **Low-volume**: most orders have 0 returns; those that do usually
have exactly 1 (rarely more). Optimize the empty + single case; still handle N. **Muted by default —
only the refund money and refund status carry signal.** See `screens/06`.

### Data per return (priority high→low)
| Field | Notes |
|---|---|
| `refund_amount` | **hero** VND money refunded (range seen ~900K–21.6M ₫); large, mono, tabular |
| `refund_status` | badge: raw lowercase `paid`=good / `unpaid`=warn → **Title-cased** to "Paid"/"Unpaid" |
| `return_status` | badge: raw lowercase `returned`=neutral / `cancelled`=bad → **Title-cased** |
| `return_date` | date ICT |
| `return_quantity` | units — **often NULL → "—"** |
| `return_reason` | free-text Vietnamese — **often blank → muted "No reason recorded"** |

### Layout
- **Header:** title "Returns". Single return → no count chrome (just the section title). Multiple → count chip + **"total refunded"** sum on the right.
- **Card(s)**, newest-first by `return_date`:
  - Top: `refund_amount` (hero, left, tabular) · two status badges (right): `Refund: <Paid|Unpaid>` then `<Returned|Cancelled>`.
  - Meta (muted): `return_date · ICT · qty <n|—>`.
  - Reason: `Reason <free text>` or muted "No reason recorded".
- Caveat (when N>0): "Reference only — returns are not deducted from this order's P&L."

> **"total refunded"** in the prototype sums only `paid` refunds (money that actually left). Confirm
> the desired semantic with the data team — gross sum of all `refund_amount` is the alternative.

### Empty state (common, healthy — NOT an error)
A single calm muted line "No returns" in a small bordered box. **No empty table shell, no large state block.**

### Demo orders
`HD00098` = single (paid/returned, with reason & qty) · `HD00076` = two returns (unpaid/cancelled + paid/returned, exercises NULL qty and blank reason) · `HD00123`/`HD00210` = empty state.

---

## Component inventory (reusable)

- **Badge** (`ui.jsx`) — `tone` ∈ neutral/good/warn/bad/accent, optional leading `dot`. Always text. CSS `.bdg`.
- **Caveat** (`ui.jsx`) — inline info/warn note, optional amber rule-strip. CSS `.caveat`.
- **Money / Pct** (`ui.jsx`) — VND formatter (`vi-VN`, ₫ suffix, null→"—"); percent with good/bad tone. Numbers use `--num-font` (mono) + `tabular-nums`.
- **Kpi, StatusPill, Eyebrow, Sparkline** (`ui.jsx`).
- **PanelHead / Fact** (`orderTabs.jsx`) — section title + data-source sub; key/value fact rows.
- **Tab bar** — `role=tablist/tab`, `aria-selected`, amber underline on active; `.tab`.
- **Data table** — `.tbl` (mono uppercase headers, right-aligned tabular numbers, hairline rows).
- **Waterfall** `.wf-*`, **vertical timeline** `.timeline/.tl-*`, **month strip** `.strip-*`, **grouped ledger** `.group`.
- **Shipments** `.ship-*`, **Returns** `.ret-*` (specs above).

---

## Interactions & behavior

- **Search** (header): segmented Order/Customer mode switches the placeholder; submit resolves → 1 hit redirects to detail, N customers render a results dropdown, 0 shows an inline "No match". (Prototype resolves against `DV_DATA`; real app does `hx-get /search`, `HX-Redirect` on single hit.)
- **Tabs:** lazy — only the default tab loads first paint; others on click (prototype simulates a 220ms skeleton; real app = `hx-get` into `#tab-panel` with `hx-indicator` + `hx-push-url`).
- **Row → detail:** customer Order-History rows and order recipient cards navigate to the linked entity.
- **Motion:** ≤260ms, no bounce/spring (Precision). Page entrance translates only (never gates visibility on opacity). Respects `prefers-reduced-motion`.
- **Copy confirmation:** see Shipments.

## State management

- Route: `{ page, id, tab }` from the hash. Order/customer tab is local component state (lazy-load trigger).
- Tweaks (prototype only): `lang/theme/density/numfont/accent` persisted to `localStorage`, applied as `data-*` on `<html>`. In production these are app/user settings, not an overlay panel.
- Data fetching: each tab is an independent fetch in the real app (serving layer / warehouse views). Always render money & timestamps via the shared renderers; missing → "—". Surface data-quality caveats inline.

## Accessibility & responsive

- Semantic landmarks (`header/main/aside/nav`), real `<table>` for tabular data, tabs with ARIA, keyboard-navigable, `:focus-visible` = 1px amber outline at 2px offset.
- **Color is never the only signal** — every badge carries text; status also uses a dot.
- Breakpoints: ≥1100 two-col; 860–1100 narrower; <860 single column (sidebar to top). Cards stack full-width <700; tracking codes stay fully visible/copyable; money stays right-aligned tabular.

## Assets

- `app/assets/icons/` — hand-drawn SVGs (`copy`, `check-tiny`, `cog`, `arrow-right`). Style: 16px box, 1.3–1.6 stroke, round caps, `currentColor`. The Shipments copy/check glyphs are drawn inline in `orderTabs.jsx` in the same style.
- `app/assets/wordmark.svg` — the "detailView" mark (header uses a text wordmark + amber dot).
- **No photography, no illustration, no emoji, no icon library** — identity is type + three accent colors (Precision rule).

## Files to reference

- **Financial tab (redesigned):** `app/components/financial.jsx` — all 5 zones (verdict addons, composition bar, PL waterfall, cost ledger, COGS recon)
- Shipments + Returns + other order panels: `app/components/orderTabs.jsx`
- Mock data shapes (orders incl. new financial fields, `shipments[]` / `returns[]`, customers): `app/data/mock.js`
- All component CSS (search `.comp-`, `.wf-row--pl`, `.wf-footer-`, `.recon-`, `.ship-`, `.ret-`): `app/styles/app.css`
- Tokens: `design_system/colors_and_type.css` · Guide: `design_system/PRECISION_GUIDE.md`

---

## ▸ Section spec: FINANCIAL TAB (redesigned)  (`financial.jsx`; CSS `.comp-*`, `.wf-*--pl`, `.wf-footer-*`, `.recon-*` in `app.css`)

Reorganized so a non-finance user can answer at a glance: **"Did this order make money, how much, where did it go, and can I trust the numbers?"** Five progressive-disclosure zones.

### Zone 1 — Verdict bar + addons

Keeps the existing `ProfitVerdict` component (bar/rule/gauge treatments via `data-verdict-style`).

**COGS source badge** — shown below the verdict bar. Maps `cogs_source` field:
| Value | Badge | Tone | Tooltip |
|---|---|---|---|
| `sapo_mac` | `Sapo-MAC` | good | Giá vốn từ tồn kho Sapo |
| `misa` | `MISA` | neutral | Giá vốn kế toán TK632 |
| `both` | `Sapo + MISA` | good | Có cả hai (đối chiếu được) |
| `none` | `No COGS` | warn | Chưa có giá vốn → margin chưa xác định |

**Fully-loaded footnote** — muted line below verdict, conditional on `allocated_overhead != null`:
> ⓘ After operating cost allocation (est.): Fully-loaded net profit +272.000 đ · 21.8%

Never competes with the verdict hero number; it's a quiet report figure.

### Zone 2 — Composition bar

Horizontal 100%-stacked bar of **Net Revenue** broken into cost segments + profit. CSS `.comp-bar`.

| Segment | Color token | Condition |
|---|---|---|
| COGS | `amber-lo` mixed with `ink-300` | `cogs_amount > 0` |
| Promo | `coral-500` at 65% | `promo_goods_cost > 0` |
| Platform fees | `honey-500` at 75% | `platform_fees > 0` |
| Overhead | `ink-500` | `allocated_overhead > 0` |
| Profit / Loss | `moss-500` / `coral-500` | always (remainder) |

Legend below the bar shows each segment's VN label + percentage. Zero segments are skipped. If `cogs_amount` is null (unverified), the entire bar is hidden.

### Zone 3 — P&L Waterfall

**4-column grid**: `op (20px) | label (1fr) | % (72px) | amount (140px)`. Header row with `P&L LINE | % | AMOUNT`. All numbers use `font-variant-numeric: tabular-nums` for column alignment.

| # | Op | Label | % basis | Amount field |
|---|---|---|---|---|
| 1 | | Gross revenue `[incl VAT]` | — | `gross_revenue` |
| 2 | − | Discount `BUNDLE` | — | `discount_amount` |
| 3 | = | Net revenue `[excl VAT]` | — | `net_revenue` (total row) |
| 4 | + | Tax amount `[embedded in price]` | — | `tax_amount` |
| 5 | = | Total collected `[incl VAT]` | — | `total_collected` (total row) |
| 6 | − | COGS + source badge | cogs/net | `cogs_amount` (neg) |
| 7 | = | Gross profit | `gross_margin_pct` | `gross_profit` (result) |
| 8 | − | Promo goods cost `promo` | promo/net | `promo_goods_cost` (neg, **only if > 0**) |
| 9 | − | Platform fees `Shopee ▸ detail` | fees/net | `platform_fees` (neg) |
| 10 | = | ★ **Channel net profit** | `channel_net_margin_pct` | `channel_net_profit` (**decision tier**) |

**Decision tier** (row 10): CSS `.wf-row--decision` — moss-tinted background, bold label + amount in `moss-500`, star glyph. When negative, amount flips to `coral-500`.

**EN labels + VN tooltips**: every label has a `title` attribute with Vietnamese name + short definition (see `TOOLTIP_MAP` in `financial.jsx`). Cursor shows `help` on hover.

**Tags**: `[incl VAT]`, `[excl VAT]`, `[embedded in price]` rendered in mono caption style (`.wf-tag`).

### Fully-loaded footer (below waterfall, conditional)

Rendered only when `allocated_overhead > 0`. Dashed-border box (`.wf-footer-muted`), two rows:
- `+ Allocated overhead [est.] ESTIMATED badge  −48.000 đ`
- `= Fully-loaded net profit [for reporting]  +272.000 đ  21.8%`

Muted styling — never visually competes with the decision tier above.

### Zone 4 — Cost breakdown

Same grouped collapsible ledger as before, extended with two new `cost_category` values:
- **`PROMO_GOODS`** — tone `accent`, green `NEW` tag
- **`OVERHEAD`** — tone `accent`, green `NEW` tag, `(allocated)` suffix

Each row remains traceable: `cost_type · source · record · fee_source (actual/estimated) · amount`.

### Zone 5 — COGS reconciliation (collapsed)

Rendered only when `cogs_source === "both"` (both Sapo-MAC and MISA data exist). CSS `.recon-*`.

**Collapsed** (default): dashed border, one-line preview:
> ▸ COGS RECONCILIATION  audit · collapsed by default
> Sapo-MAC **870.000 đ** vs MISA-632 **850.000 đ** · variance **+20.000 đ (+2.4%)**

**Expanded** (click): 3-column grid showing Sapo-MAC value, MISA TK632 value, and variance. Variance > 5% highlights in `honey-500`.

### New data fields (mock data, `order.financial`)

| Field | Type | When null |
|---|---|---|
| `cogs_source` | `"sapo_mac"` \| `"misa"` \| `"both"` \| `"none"` | Falls back to inferring from `has_cogs` |
| `promo_goods_cost` | number | Row hidden |
| `allocated_overhead` | number | Footer + composition segment hidden |
| `is_overhead_estimated` | boolean | Controls badge |
| `fully_loaded_net_profit` | number | Footnote hidden |
| `fully_loaded_margin_pct` | number | Pct hidden |
| `sapo_mac_cogs` | number | Recon hidden |
| `misa_cogs_632` | number | Recon hidden |
| `cogs_variance` | number | Recon hidden |
| `cogs_variance_pct` | number | Recon hidden |

### Graceful degradation

When all new fields are null (backend phases pending), the page renders **exactly as before**: verdict + waterfall (ending at channel net) + cost ledger. No composition bar, no overhead footer, no reconciliation. Tested on HD00076.

### Demo orders

| Order | State | New features shown |
|---|---|---|
| HD00123 | Profitable, Shopee | All 5 zones: both-source badge, overhead, fully-loaded, composition, recon |
| HD00251 | Loss, Shopee | Coral verdict, loss composition segment, overhead deepens loss |
| HD00098 | Profitable, Facebook, gift | Promo goods cost row, MISA-only badge, PROMO_GOODS in ledger |
| HD00076 | Unverified, Lazada | Graceful degradation — `No COGS` badge, no new zones |
| HD00210 | US CrossBorder | Separate US variant (unchanged), MISA badge added |
