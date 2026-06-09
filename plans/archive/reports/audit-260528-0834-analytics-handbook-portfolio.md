# Analytics Handbook Portfolio Audit — Prioritized Optimization Roadmap

> **Created:** 2026-05-28 08:34 ICT
> **Scope:** All 32 playbooks + 35 blueprints in `docs/analytics-handbook/`
> **Output:** Prioritized perspectives, per-report optimization opportunities, data gaps, implementation roadmap
> **Methodology:** Domain reading → playbook inventory (3 parallel agents) → blueprint deep-dive (4 parallel agents) → synthesis

---

## Executive Summary

**Portfolio state.** 32 playbooks + 35 blueprints across 7 domains, ~40K markdown lines. Coverage is broad but **action-density is uneven**: a handful of playbooks (`sales_promotion_analysis`, `marketing_roi`, `logistics_operations`, `ingestion_health`) are world-class with explicit thresholds + owners + actions; the majority — including CEO-facing dashboards — are number walls without prescriptive guidance.

**Three structural problems repeated across the portfolio.**

1. **Redundancy.** ~50% widget overlap between customer_retention ↔ customer_intelligence, ~70% between ceo_monthly_scorecard ↔ sales_monthly_review, 3 near-identical SKU detail tables across product blueprints, channel margin computed differently in 4 dashboards.
2. **Prescriptive layer missing.** Tables list problem channels/SKUs/orders but rarely recommend an action, owner, or SLA. Action triggers exist in playbook `.md` but live invisible to dashboard users.
3. **Wrong "snapshot in time" math.** Customer retention + intelligence MoM scalars filter `first_order_date < lastmonth` returning a *snapshot of the older sub-base today*, not the *state of the base last month*. Affects ~15 widgets. Same family of bug in CEO Monthly target progress (hardcoded 600M VND instead of `fact_targets.target_gmv`).

**Two systemic data gaps.**

- **No `mart_customer_status_snapshot_monthly`** — blocks correct retention/MoM math everywhere.
- **No `mart_sku_economics_monthly`** — forces 4 dashboards to reinvent SKU-level joins of MISA COGS + fact_orders + fact_order_returns. Single root of duplication + drift.

**Recommended actions, ranked by leverage.** See §3 Per-Perspective Evaluation and §6 Roadmap.

---

## 1. Methodology

| Step | Output |
|------|--------|
| Read 7 domain files | Metric/scope foundation |
| Inventory 32 playbooks (3 parallel agents) | Audience, cadence, decisions, action-density, gaps |
| Rank perspectives by action opportunity | §2 ranking |
| Deep-dive 9 highest-priority blueprints (4 parallel agents) | Per-report current strengths, top-5 improvements, redundancy, consolidation proposals |
| Cross-cut data gaps | §4 data-foundation needs |
| Synthesize roadmap | §6 implementation order |

Deep-dive sample (9 of 35 blueprints, ~7000 markdown lines):

- `finance_channel_pl` + `shopee_channel_economics` (channel P&L)
- `sales_promotion_analysis` + `marketing_roi` (promo/marketing ROI)
- `customer_retention_dashboard` + `customer_intelligence_monthly` (customer)
- `ceo_monthly_scorecard` + `ceo_weekly_pulse` (CEO strategic)
- `finance_product_cost_margin` + `product_performance` + `finance_return_impact` (product/return)

Remaining 26 blueprints assessed via playbook inventory + cross-references.

---

## 2. Prioritization of Perspectives (high → low)

Ranked by **(money at stake per action) × (decision velocity) × (current portfolio coverage gap)**.

| Tier | # | Perspective | Money/leverage | Action velocity | Coverage gap | Top blueprints |
|------|---|-------------|----------------|-----------------|--------------|----------------|
| **S** | 1 | **Channel P&L & loss-leader detection** | Very High — Shopee fees alone can wipe channel margin | Monthly + alerts | Medium — finance_channel_pl is strong; needs SKU drill + loss-driver decomposition | finance_channel_pl, shopee_channel_economics |
| **S** | 2 | **Promotion ROI & discount governance** | Very High — VN ecom relies on 11.11/12.12/Tết promos | Weekly + per-campaign | High — no voucher abuse detection, no cannibalization analysis, weak baseline | sales_promotion_analysis, marketing_roi |
| **S** | 3 | **Customer retention & VIP at-risk** | High — VIP save = months of LTV; cheap to act | Daily watchlist + monthly review | Critical — MoM math broken, no outcome loop, no RFM statistical | customer_retention_dashboard, customer_operational_dashboard, customer_intelligence_monthly |
| **A** | 4 | **SKU margin & COGS variance** | High — supplier renegotiation, dead SKU kill | Weekly | Medium — alerts exist, no kill list, no supplier dim | finance_product_cost_margin, product_performance |
| **A** | 5 | **Marketing channel ROI** | High when data complete — but blocked by partial `fact_marketing_spend` coverage | Weekly | High — attribution model broken (last-click + ad-channel ≠ order-channel) | marketing_roi, marketing_weekly_tracker, marketing_monthly_analysis |
| **A** | 6 | **CEO strategic scorecard** | High — board accountability + multi-month bets | Monthly | High — no narrative, no YoY (VN seasonality!), no driver attribution, no customer concentration | ceo_monthly_scorecard, sales_monthly_review |
| **A** | 7 | **Returns & refund liability** | Medium-High — direct refund exposure + supplier quality signal | Daily/Weekly | Critical — no SKU-level return analysis, no return-adjusted margin | finance_return_impact |
| **B** | 8 | **Daily revenue ops cockpit** | Medium per-action, high cumulative | Real-time, intraday | Low — strong coverage but `sales_daily_operation` and `sales_yesterday_operation` are near-duplicates | sales_daily_operation, sales_yesterday_operation, sales_ops_weekly_review, sales_ops_monthly_summary |
| **B** | 9 | **Order fulfillment & logistics** | Medium — NPS + working capital | Real-time | Medium-High — carrier data blocked; logistics_shipping is skeleton | logistics_operations |
| **B** | 10 | **CEO weekly pulse** | Medium — 5-min Monday scan | Weekly | Medium — needs Pace+Alerts focus, drop overlap with sales_ops_weekly | ceo_weekly_pulse |
| **B** | 11 | **B2B daily/tracking** | Medium — high AOV per decision but lower volume | Daily | Unverified — not deep-dived | b2b_sales_daily, b2b_orders_tracking |
| **C** | 12 | **CS social commerce conversion** | Limited without traffic data | Real-time | High blocker — no agent FRT/AHT, no traffic | customer_support_social_commerce |
| **C** | 13 | **Data integrity (recon + ingestion)** | Indirect, huge downside | Daily | Low — strong design; needs auto-recon vs Sapo | ingestion_health, orders_list_reconciliation, finance_accounting_recon, finance_cost_ledger |
| **C** | 14 | **Order detail / lookup** | Low per-event, high cumulative | On-demand | Low — but no usage telemetry | order_detail_view, order_listing |
| **D** | 15 | **Cashflow** | Existential when built | — | **Blocked** — needs payment classification + AP/AR | finance_cashflow (skeleton) |
| **D** | 16 | **Inventory** | High — dead-stock = trapped capital | — | **Blocked** — `fact_inventory` not built | product_inventory (skeleton) |
| **D** | 17 | **Carrier/shipping** | Medium — carrier contract leverage | — | **Blocked** — `fact_shipments` not built | logistics_shipping (skeleton) |
| **D** | 18 | **US cross-border** | Niche but high AOV | — | Unverified | us_crossborder_operations |

---

## 3. Per-Perspective Evaluation (Tier S + A)

### 3.1 Channel P&L & Loss-Leader Detection (Tier S #1)

**Blueprints:** `finance_channel_pl`, `shopee_channel_economics`, `channel_profitability_monthly` (deprecation candidate)

**Current strengths**
- `finance_channel_pl`: 5-tab logical reading flow, conditional formatting, MoM variance, 12-month heatmap, `has_cogs` correctly applied.
- `shopee_channel_economics`: Hero gauge with 3-zone thresholds, waterfall + fee breakdown pair, True Margin (after MISA COGS), Orders Below Breakeven table.

**Top optimization opportunities**

| # | Issue | Concrete fix | Decision unlocked |
|---|-------|--------------|-------------------|
| 1 | Loss-leader tab has no "WHY" widget | Add **Loss Driver Decomposition** per channel: MoM Δ Gross Rev / Δ Discount % / Δ COGS % / Δ Platform Fee % | Routes ticket to right owner (merch vs sales vs ops) |
| 2 | No SKU drill from loss-leader | Add **Top 20 SKUs by Loss Contribution** filtered by channel | Concrete kill-list + sourcing renegotiation targets |
| 3 | Variance table missing decomposition columns | Add `Δ COGS Ratio pp` / `Δ Fee Ratio pp` / `Δ Discount Ratio pp` columns | Diagnose margin erosion source |
| 4 | No target overlay anywhere | Seed `dim_channel_targets` (channel_key, period_month, target_margin_pct, target_revenue) → overlay on Net Margin Trend | "Vs plan" accountability |
| 5 | Total Loss Exposure scalar = no trend, no concentration | Replace with **Loss Exposure Trend** (6-mo) + **Loss Concentration** ("Shopee gánh 78%") | Prioritize which channel to fix first |
| 6 | Shopee Tab 3 scatter has 5 buckets only — loses distribution signal | True scatter at order grain (LIMIT 5000) OR % orders breakeven per bucket histogram | Pricing floor recommendation per bucket |
| 7 | No Voucher Xtra ROI widget — biggest controllable Shopee lever invisible | Split orders by `voucher_xtra_fee > 0` vs `=0`; compare AOV, conversion proxy, net margin | Opt out of Voucher Xtra if ROI negative |
| 8 | No fee-tier scenario / what-if | Scalar: "If service_fee +1pp → margin impact = X VND/month" | Arms negotiation team |
| 9 | Tab 3 buries Net Profit % | Add final row `'= Net Profit %'` to cost waterfall, color green | True margin visible as hero |

**Widgets to remove/merge:** 5 duplicate "Chu kỳ báo cáo" scalars (collapse to dashboard-level header). Net Margin Trend + Margin Heatmap have overlap — keep heatmap, demote line chart. Shopee Tab 1 fee breakdown row chart + waterfall partially overlap — keep waterfall.

**Redundancy:** `channel_profitability_monthly` overlaps heavily with `finance_channel_pl` AND uses MISA-only margin (ignores Shopee fees → ECOM overstated). **Recommendation: deprecate `channel_profitability_monthly`**, replace with deep-link from `finance_pl`. `finance_pl` Tab Shopee duplicates 6 widgets of `shopee_channel_economics` — reduce to 2 widgets + link.

---

### 3.2 Promotion ROI & Discount Governance (Tier S #2)

**Blueprints:** `sales_promotion_analysis`, `marketing_roi`

**Current strengths**
- `sales_promotion_analysis`: Strict RETAIL scoping with rationale, 4 tabs covering overview/ranking/channel/ROI, high-discount audit list, methodology rigor disclosed (no holdout → directional).
- `marketing_roi`: Profitable ROAS metric (vs vanilla ROAS), Quadrant scatter, MoM Delta, completed-orders-only filter.

**Top optimization opportunities**

| # | Issue | Concrete fix | Decision unlocked |
|---|-------|--------------|-------------------|
| 1 | **Voucher abuse / stacking detection absent** | Table: top 20 customers by `SUM(discount_amount)` 30d + distinct promo codes used; top 10 promo codes with `unique_customers/total_uses < 0.3` (shared); staff_id column | Kill leaky codes, ban abusing customers, investigate staff |
| 2 | **Discount cannibalization not measured** | Compare `units_sold_promo_period vs prior` for promo + non-promo category same window; non-promo drop = cannibalization | Avoid discounting best-sellers that sell themselves |
| 3 | **No action triggers in dashboard** | Text card per tab: "Discount Rate >15% → Finance review | ROI <-50% on >5 codes → Marketing pause | Discount Frequency +20% MoM → CEO escalation" | One-glance health |
| 4 | **ROI baseline = channel-AOV → selection bias** (promo targets lower-AOV new customers) | Add **ROI by Customer Type** (new/repeat/reactivated) with same-segment baseline | Honest ROI per customer type |
| 5 | **AOV Uplift scalar misleading** (min-spend threshold drives AOV, not lift) | Replace with **AOV by discount band** (0/1-10/10-20/20-30%); non-monotonic = threshold effect not lift | True lift signal |
| 6 | **Marketing ROI attribution model broken** when ad_channel ≠ order_channel | Add **Spend Coverage** scalar + "spend without matching channel revenue" + "revenue from zero-spend channels" — if >30% mismatch → big banner | Stop trusting ROAS per channel until proper attribution |
| 7 | **Spend data completeness invisible** | Scalar "Coverage X/Y channels have spend data" + freshness per channel; <80% coverage → block dashboard with warning | Trigger backfill before budget decision |
| 8 | **CAC + Payback period missing** (despite "pending") | Per channel: CAC = spend / new_customers; 90-day LTV; Payback months = CAC / monthly gross profit | Scale payback <3mo, pause >12mo regardless of first-touch ROAS |
| 9 | **No budget pacing vs plan** | If monthly budget Sheet exists: Spend Pacing = actual / (budget × pct_month_elapsed); <80% under, >120% over | Daily Marketing check |
| 10 | **No prescriptive "Top 3 actions this week"** | Auto-compute table from threshold rules; surface 3 kill + 3 scale recommendations | Dashboard → decision tool |

**Widgets to remove/merge:** Sales-promo Tab 1 has 4 scalars → merge Discounted Orders count into Frequency %. Marketing-ROI "ROAS by Channel" row chart duplicates Table — drop row chart. Hero scalar trio → merge into single scalar.comparisons table.

**Redundancy:** Discount Rate appears in 3 blueprints (sales_promotion + marketing_weekly + marketing_monthly). ROAS appears in 3 blueprints (marketing_roi + marketing_monthly + channel_profitability). **Recommendation:**
- `sales_promotion_analysis` = SoT for promo deep-dive
- `marketing_roi` = SoT for paid spend ROAS + attribution + CAC
- Weekly/monthly versions = headline scalars + drill-link only (don't recompute)

---

### 3.3 Customer Retention & VIP At-Risk (Tier S #3)

**Blueprints:** `customer_retention_dashboard`, `customer_intelligence_monthly`, `customer_operational_dashboard`

**Critical bug found.** Both retention + intelligence MoM scalars are mathematically broken. CTEs filter on `first_order_date < lastmonth` which returns **a snapshot of the older sub-population today**, not a true month-end snapshot. Affects ~15 hero scalars (Repeat Rate, Churn Rate, Active Rate, One-Time, Avg Lifespan, Total LTV, Avg LTV, Avg Orders, etc.). Stakeholders may be making decisions on misleading deltas.

**Current strengths**
- Lifecycle taxonomy (Active/At Risk/Churned at 30/90d) consistent across all customer blueprints.
- Cohort retention heatmap (12-month rolling) is genuinely strong.
- Revenue Layer Cake (cohort area chart) answers "are we cohort-dependent on legacy customers".
- At-Risk Watchlist has correct columns for CRM export (phone, LTV, recency).
- `customer_intelligence_monthly`: Top 10 products VIP vs First-Time Buyer is the cleanest acquisition→retention bridge widget in the handbook.

**Top optimization opportunities**

| # | Issue | Concrete fix | Decision unlocked |
|---|-------|--------------|-------------------|
| 1 | **MoM math broken (15 widgets, 2 blueprints)** | Build `mart_customer_status_snapshot_monthly` (one row per customer-month, status derived from `last_order_date` as-of month-end). Drive all hero MoM scalars off it. | Trustworthy "is retention improving?" answer |
| 2 | **At-Risk Watchlist not actionable in CRM workflow** | Add columns: `Days to Churn`, `Last Channel`, `Last Category`, `Suggested Action` (CASE on segment+recency), `Assigned CS Owner` | CS team gets a work queue, not a report |
| 3 | **No outcome loop / win-back attribution** | Build CS action log table (call/SMS/email + timestamp + customer_key). Widget: **"At-Risk → Reactivated Conversion"** — prior-month At-Risk cohort, % placed order in following 30/60d, by segment | CS leader sees outreach ROI; tunes cadence |
| 4 | **Cohort heatmap not wired to Segment filter** despite filter existing | Wire `{{segment}}` parameter; add second heatmap by acquisition channel | "Which channel's customers stick?" → CAC payback input |
| 5 | **Churn Rate Trend SQL conceptually broken** (pivots on `last_order_date + 90 DAY` truncated) | Replace with snapshot-driven monthly churn from #1 | Stable trend line |
| 6 | **No RFM statistical segmentation** (only rule-based value_group) | Build RFM via NTILE(5) on recency/frequency/monetary → 11 named cells (Champions/Loyal/At-Risk-High-Value/Hibernating/Lost). Add `rfm_segment_label` to `dim_customers` | Marketing campaign targeting becomes evidence-based |
| 7 | **No prescriptive segment action layer** | Seed `dim_customer_action_playbook(segment, lifecycle_status, recency_band) → (action, owner, sla_days, channel)`; surface as table widget | Operating rhythm becomes tasking session |
| 8 | **No CLV projection** (all backward-looking) | Add Projected CLV by Segment: `AOV × annual freq × 2-year survival × gross margin %`. Stub CAC column for when `fact_marketing_spend` lands | Sets up LTV/CAC discussion |
| 9 | **No first→second order product affinity / cross-sell** | Widget: **"First→Second Order Path"** (top 10 pairs where 2nd order within 60d) + **VIP Basket Co-occurrence** | Concrete bundle/upsell campaigns |
| 10 | **No customer concentration risk** | Scalar: **Top-10 customer revenue share %** trended 6M; if >25% flag | Spot dependency risk |

**Widgets to remove/merge:**
- Repeat Purchase Rate appears in 3 places across 2 blueprints — keep once
- 3 widgets answering "where are customers concentrated?" (lifecycle pie + revenue bar + segment×status matrix) → merge into one stacked bar
- New vs Returning Revenue + Customers → merge into combo (bars + line)
- At-Risk count scalar duplicates donut slice — remove
- Total LTV scalar = vanity; keep Avg LTV
- Loyalty Point + Gender distributions = demographic afterthoughts — replace with Province × Segment heatmap (geo-actionable) and Repeat Channel for VIP
- Best Cohort scalar = vanity → Worst Recent Cohort

**Consolidation proposal: merge `customer_retention_dashboard` + `customer_intelligence_monthly` → `customer_health_cockpit` (4 tabs, ~22 widgets, down from 47).**

| Tab | Owner | Core questions | Widgets |
|-----|-------|----------------|---------|
| 1. Health & Growth | MM/CEO | Base size, net growth, Pareto, segment×status | 4 hero + acquisition vs churn combo + segment×status stacked + Pareto + scorecard |
| 2. Cohort & Quality | CMO | Cohort retention rigor, new-customer quality, returning-rev dependency | Cohort heatmap (toggleable) + Layer cake + New customer quality combo |
| 3. Behavior & Cross-Sell | MM/Merch | Channel-segment fit, basket affinity, drives of next purchase | Channel×Segment + Top VIP vs First-time products + First→Second path + Basket co-occurrence + Days-between distribution |
| 4. Action Queue | CS lead | Who to call today, RFM action grid, outreach ROI | RFM grid + At-risk watchlist (actionable) + Reactivation funnel + Reactivation trend |

Move duplicate cohort heatmap *out* of `marketing_monthly_analysis.md` → link to cockpit Tab 2.

---

### 3.4 SKU Margin & COGS Variance (Tier A #4) + Returns (Tier A #7)

**Blueprints:** `finance_product_cost_margin`, `product_performance`, `product_profitability`, `finance_return_impact`

**Top optimization opportunities**

| # | Issue | Concrete fix | Decision unlocked |
|---|-------|--------------|-------------------|
| 1 | **Scatter at 200 SKUs unreadable** | Limit to SKUs with revenue > P50 OR margin <10% OR >40%; 4-quadrant overlay (high-rev/low-margin = "renegotiate", low-rev/high-margin = "promote") | Pick 5 SKUs/week, not scan 200 |
| 2 | **COGS variance has no direction-of-blame** | Add `qty_current / qty_3m_avg` column; qty stable + COGS spike = supplier issue; qty change >50% = mix shift | Routes ticket to procurement vs ops |
| 3 | **No SKU kill list** | "SKUs to discontinue" widget: margin <10% AND revenue rank in bottom-80% AND no MoM growth 60d; action column KILL/REPRICE/RENEGOTIATE | Concrete weekly cull list |
| 4 | **No supplier roll-up** (no dim_suppliers) | Proxy via 4–6 char SKU prefix; top 10 prefix groups by COGS spend = de-facto supplier list | Renegotiate top-3 by spend |
| 5 | **No SKU-level return analysis (BIGGEST GAP)** | New tab "Return-prone SKUs": top 20 by refund_amount AND return rate; flag if SKU return_rate > 3× channel avg | Concrete delist / supplier-quality conversations |
| 6 | **No return-adjusted margin** (current margin ignores returns) | View on int_misa_sales_lines + fact_order_returns: `(revenue - COGS - refund + recovered_COGS) / revenue` | Single biggest insight unlock for merchandising |
| 7 | **Days-to-Return averaged across all reasons = meaningless** | Histogram bucketed 0–3 / 4–7 / 8–14 / 15–30 / >30 days stacked by top-3 reasons | QC (early) vs CS (mid) vs fraud (late) routing |
| 8 | **No return prevention prescriptive layer** | Per top reason: top 5 SKUs, top 5 channels, recommended action ("Tighten sizing", "Pre-ship QC", "Block fraud cohort") | Reason → SKU/channel → owner → action |
| 9 | **Velocity widget divorced from margin** | Add gross_margin_pct column; sort by `velocity × margin_pct` | Identify true winners vs loss-leader treadmill |
| 10 | **No slow-mover proxy** (no inventory data) | "Going cold" widget: SKUs with last sale > 14 days, was top-200 in 30–60d window | Proactive cull without fact_inventory |
| 11 | **MoM growth lists have no significance filter** | `HAVING p.val > 1M AND t.val > 1M` + absolute delta column | Filter noise from tail |
| 12 | **Top 10 decline as bar masks severity** | Replace with table: SKU \| Prev DT \| Now DT \| Δ VND \| Δ % \| Days since peak; highlight Δ VND > 10M | Routes urgency to top declining by absolute |

**Widgets to remove/merge:** 3 near-identical SKU detail tables across product_performance + finance_product_cost_margin + product_profitability — keep ONE canonical. Tab "Loi nhuan" in product_performance = 100% duplicate of finance_product_cost_margin — delete entire tab, replace with link card. `Doanh thu trung binh/san pham` distorted by long-tail SKUs — drop. Category-by-revenue bar + donut both rank categories — keep donut only.

**Consolidation proposal: 3 product blueprints → 2.**

| New blueprint | Replaces |
|--------------|----------|
| **`merch_sku_economics`** (4 tabs: Action Queue / Margin & COGS / Velocity & Growth / SKU Drill) | finance_product_cost_margin + product_performance Tab Loi nhuan + product_profitability |
| **`merch_return_impact`** (5 tabs: KPI / Channel / Reasons+Actions / Return-prone SKUs / Cohort matrix) | current finance_return_impact + NEW SKU layer |

**Expected:** ~70 widgets across 3 dashboards → ~35 widgets across 2 dashboards. Return data feeds into SKU view. Prescriptive layer added.

---

### 3.5 CEO Strategic Scorecard (Tier A #6)

**Blueprints:** `ceo_monthly_scorecard`, `ceo_weekly_pulse`

**Critical bug found.** `ceo_monthly_scorecard` Target Achievement card runs a `monthly_target` CTE but never references `t.target_gmv` in the SELECT. Metabase progress widget is anchored to **hardcoded 600,000,000 VND**. Variance display correct but visual progress bar lies whenever target ≠ 600M.

**Top optimization opportunities**

| # | Issue | Concrete fix | Decision unlocked |
|---|-------|--------------|-------------------|
| 1 | **CEO Monthly target = fake** (hardcoded 600M) | Display target as `scalar.comparisons` column (drop progress widget) OR auto-regenerate when target changes | Trustworthy "are we on plan?" |
| 2 | **Zero action triggers — wall of 28 numbers** | "Tín hiệu & Hành động" text card per tab summarizing top 3 triggers (pull from sales_monthly_review playbook) | Translates interesting → do X by Friday |
| 3 | **No YoY anywhere** — VN seasonality (Tết, 9/9, 11/11) invisible | YoY column on all heroes + 13-month trend overlay + Seasonal context text card | Distinguish real growth from calendar artifacts |
| 4 | **Strategic narrative absent** — "why did the month change?" | **MoM Revenue Bridge**: prev → Δ(new customers) → Δ(returning freq) → Δ(AOV) → Δ(channel mix) → this month | Pinpoints which lever moved the number |
| 5 | **No customer concentration / cohort risk** | Top-10 customer revenue concentration % trended 6M (>25% flag); cohort retention heatmap M0..M5 last 6 cohorts on Tab 2 | Governance risk + acquisition quality signal |
| 6 | **CEO Weekly Loss-Making Channel scalar = dead-end** (no drill) | Table directly below: "Channels with negative net profit this week" (channel, revenue, COGS, fees, net loss) | Investigate Shopee vs TikTok specifically |
| 7 | **CEO Weekly no MTD picture — week-tunnel-vision** | Scalar trio: MTD Revenue / Target / Days Remaining; Required daily run-rate to hit target | Triggers in-month pivots not month-end post-mortems |
| 8 | **CEO Weekly "Cảnh báo" tab is just 3 scalars** | Single rule-based table: `Metric \| Current \| Last Week \| Threshold \| Status \| Owner` | "Here are 2 things to ask team about today" |
| 9 | **No "story" — narrative tabs missing** | Auto-generated "Tóm tắt tuần" text card via CASE: `WHEN pace<0.8 AND wow<0 AND loss>0 THEN '🔴 Tuần khó: pace X, WoW Y%, Z kênh lỗ. Ưu tiên: review chi phí sàn.'` | 30-second read-and-act |
| 10 | **Returning Revenue % gauge thresholds arbitrary** (hardcoded 40/60) | Replace with YoY/6M trend line + horizontal "12-week median" band | Honest signal vs arbitrary judgement |

**Widgets to remove/merge:** Revenue Waterfall (Tab 1) + Revenue Breakdown Table (Tab 3) = same data — keep waterfall. Customer Segment pie + Revenue by Segment row bar = same — keep one. Top 10 Products on CEO Monthly = too tactical — move to product blueprint. Weekly Pulse: Gross Revenue scalar (redundant with Net + Discount Rate). Top Channels row bar duplicates Channel Performance Table — drop row bar.

**Consolidation proposal: keep 2 dashboards, restructure roles.**

**CEO Weekly Pulse → "Pace + Alerts"** (2 tabs, 5-6 widgets):
- Tab 1 Pace: MTD progress, Pace Index, required run-rate, narrative summary
- Tab 2 Alerts: rule-based table + loss-channel drill

**CEO Monthly Scorecard → "Strategy & Bets"** (3 tabs, ~14 widgets):
- Tab 1 Performance & Plan: heroes with MoM AND YoY, Pace vs Plan annualized, MoM Revenue Bridge, 13-month trend
- Tab 2 Customer Health & Risk: cohort heatmap, top-10 concentration, segment LTV trend, acquisition quality
- Tab 3 Channel Bets & Margin: channel net profit MoM, mix shift 6M area, margin by channel, loss-channel deep-dive

**Drop entirely from CEO dashboards:** Top 10 Products table (tactical → product blueprint), Cost Structure Breakdown (→ finance_pl), Customer Segment pies (→ customer_intelligence). Eliminates ~80% duplication with Sales Director / Finance / Channel / Customer dashboards.

---

### 3.6 Daily Revenue Ops Cockpit (Tier B #8)

**Issue:** `sales_daily_operation` and `sales_yesterday_operation` are near-byte-identical — same 4 tabs, same chart catalog, only date predicate flips. **2× maintenance cost for 1.x value.**

**Recommendation:** Combine into ONE dashboard with Today/Yesterday tab pair (or date filter parameter). Cuts maintenance ~50%, reduces cognitive split for store managers.

**Other improvements:**
- "Health Score 0-100" composite is opaque (4 sub-components shown anyway in Health Breakdown table — composite is redundant). Either explode into component scalars OR define explicit action ladder per band.
- No prescriptive "do X if Y" triggers documented.

---

## 4. Data Gaps & Untapped Exploitation Opportunities

### 4.1 Data foundation gaps (data not in warehouse — block analyses)

| Gap | Blocks | Priority | Effort |
|-----|--------|----------|--------|
| `mart_customer_status_snapshot_monthly` | All retention/customer MoM math (~15 wrong widgets) | **CRITICAL** | Small (1 dbt model) |
| `mart_sku_economics_monthly` | Eliminates 4 dashboards reinventing MISA/orders/returns joins | **HIGH** | Small-Med (1 dbt model) |
| `dim_channel_targets` seed | Target overlays everywhere; data-driven gauges | **HIGH** | Small (CSV seed) |
| `dim_customer_action_playbook` seed | Prescriptive layer in retention | **HIGH** | Small (CSV seed) |
| `merch_actions` log table | Closed-loop SKU flag→action tracking | MEDIUM | Small (manual log) |
| `cs_outreach_log` table | Closed-loop CS call→reactivation attribution | MEDIUM | Small-Med (needs CS process change) |
| `rfm_segment_label` in `dim_customers` | Statistical RFM (Champions/At-Risk-High-Value/etc.) | HIGH | Small (dbt column) |
| `fact_marketing_spend` completeness | CAC, Payback, attribution rigor | HIGH | Med (needs spend source completion) |
| `recon_sapo_orders_daily` + `recon_misa_daily` + `recon_shopee_daily` | True reconciliation (currently proxy mode); auto-recon vs Sapo | HIGH | Med (dbt models) |
| `fact_inventory` | All inventory metrics, dead-stock $, OOS rate, days of supply, slow-movers | HIGH | Large (new pipeline) |
| `fact_shipments` + `dim_carriers` | Carrier performance, on-time delivery, delivery cycle | MEDIUM | Large (new pipeline) |
| `fact_gl_entries` | True EBITDA, Operating Margin, Net Margin (P&L below gross profit) | HIGH | Large (MISA GL ingestion) |
| `fact_account_balances` | Cashflow, DSO, Current Ratio, liquidity | MEDIUM-HIGH | Large |
| `fact_conversations` (CS chat data) | FRT, AHT, agent productivity, social-to-order conversion | MEDIUM | Large (FB/Zalo API integration) |
| Traffic data (Web/Social) | Funnel conversion, CAC by source, content ROI | MEDIUM | Large (GA4/UTM) |
| `dim_suppliers` (or SKU-prefix proxy) | Supplier consolidation, COGS concentration | MEDIUM | Med (data discovery — may proxy via SKU prefix) |

### 4.2 Insight gaps (data exists but no widget built)

| Gap | Where | Decision unlocked |
|-----|-------|-------------------|
| **Voucher abuse / sharing detection** | sales_promotion_analysis | Kill leaky promo codes, ban abuse, investigate staff |
| **Discount cannibalization** (promo SKUs vs non-promo SKUs same period) | sales_promotion_analysis | Avoid discounting best-sellers |
| **Attribution model integrity check** (spend channel vs order channel mismatch) | marketing_roi | Stop trusting ROAS until UTM/promo attribution |
| **CAC + Payback period** (needs fact_marketing_spend complete) | marketing_roi | Scale payback <3mo channels |
| **Cohort retention by channel/segment** (filter exists but not wired) | customer_retention | "Which channel's customers stick?" |
| **RFM statistical segmentation** (NTILE on R/F/M) | customer_intelligence | Evidence-based campaign targeting |
| **First→Second order product affinity** | customer_intelligence | Cross-sell campaigns + bundles |
| **VIP basket co-occurrence** | customer_intelligence | Merchandising layout |
| **Customer concentration risk** (top 10 customer share) | ceo_monthly_scorecard | Governance dependency signal |
| **Cohort heatmap on CEO Monthly** | ceo_monthly_scorecard | Acquisition quality degradation alert |
| **MoM Revenue Bridge** (driver attribution: new customers / freq / AOV / mix) | ceo_monthly_scorecard | "Why did revenue change?" |
| **YoY columns** (VN Tết / 9.9 / 11.11 / 12.12 seasonality) | All CEO + Sales monthly | Distinguish real perf from calendar |
| **Loss driver decomposition** (Δ Discount/COGS/Fee per channel MoM) | finance_channel_pl | Route ticket to right owner |
| **SKU-level loss contribution** drill on loss channels | finance_channel_pl | Concrete kill-list |
| **Voucher Xtra ROI** (split orders by voucher_xtra_fee > 0) | shopee_channel_economics | Opt out if ROI negative |
| **Fee tier what-if scenario** | shopee_channel_economics | Negotiation arsenal |
| **True net margin scalar on Shopee Tab 1** (currently buried) | shopee_channel_economics | Hero metric correct |
| **SKU-level return analysis** + return-prone SKU detection | finance_return_impact | Delist / supplier-quality conversation |
| **Return-adjusted margin view** | NEW (cross 3 product blueprints) | Single biggest merchandising unlock |
| **Days-to-return histogram by reason** | finance_return_impact | Route QC/CS/fraud separately |
| **Return prevention prescriptive layer** | finance_return_impact | Reason → SKU/channel → owner |
| **Velocity × Margin combined ranking** | product_performance | True winners vs loss-leader treadmill |
| **Slow-mover proxy** ("going cold" 14d) | product_performance | Proactive cull without fact_inventory |
| **Auto-recon vs Sapo count** | orders_list_reconciliation | Replace manual cross-check |
| **Outreach → Reactivation funnel** (At-risk cohort → re-purchase rate) | customer_retention | CS leader sees outreach ROI |
| **Outcome attribution: VIP called → re-purchased** | customer_retention | Tune call cadence |
| **Health Score component drill** (or replace composite with explicit action ladder) | sales_daily/yesterday | Action-oriented |
| **"Top 3 actions this week" auto-widget** per major dashboard | Multiple | Dashboard → decision tool |
| **Geographic / Province × Segment heatmap** | customer_intelligence | Geo-actionable acquisition |
| **Repeat Channel for VIP** (which platform VIPs return on) | customer_intelligence | Loyalty channel investment |
| **Concentration index trend** (e.g. Herfindahl on channel mix, customer share) | ceo_monthly_scorecard | Risk monitoring |

### 4.3 Entirely missing perspectives

| Perspective | Why it matters | What's needed |
|-------------|---------------|---------------|
| **Demand forecasting / replenishment** | Stock-out + over-stock both bleed money | fact_inventory + simple time-series mart |
| **A/B test / experimentation framework** | All marketing decisions are observational, no causal claim | Test setup + holdout schema + reporting widget |
| **Anomaly detection / proactive alerting** | All current dashboards are pull-based; failure modes silent until someone checks | Alerting subsystem (Slack/Lark hook + threshold engine) |
| **Customer satisfaction (NPS/CSAT)** | Repeat customers churn for reasons we can't see today | Survey integration |
| **Web/social conversion funnel** | Marketing spend opaque without funnel | GA4/UTM data |
| **Price elasticity** | No analysis of price changes vs volume | Historical price-change events + control SKUs |
| **Product lifecycle / launch curves** | New SKU sell-through velocity unknown | Time-since-launch dim + sell-through metric |
| **Staff productivity & SPIFF** | Partial via fact_orders.seller_staff but no dedicated playbook | Staff playbook + targets per staff |
| **Returns prevention scoring** | Predict return likelihood at order time | ML model on order features |
| **Tax/regulatory reporting** | Currently MISA does this manually | Tax-export view |

---

## 5. Portfolio-Level Recommendations (apply to all dashboards)

### 5.1 Standards to establish

1. **Action triggers schema** — every alert widget exposes `(metric, current, threshold, status, owner, action_eta)`. One reusable Metabase question type. Stop the wall-of-scalars problem.
2. **Narrative summary card** — templated CASE-based SQL text card at top of each major tab. Auto-generates "🔴 Tuần khó: ..." sentence from metric state. Already proven feasible.
3. **YoY column standard** — all monthly hero KPIs include YoY (Δ% vs cùng kỳ năm trước). VN seasonality demands it.
4. **Data Health strip** — every dashboard top: last update timestamp, row count vs 30-day avg, % null on key dimensions. Reuse from `ingestion_health`.
5. **Source-of-truth per metric** — document in handbook README: "Metric X owned by Blueprint Y; weekly/monthly views must link not recompute". Currently Discount Rate exists in 3 blueprints, ROAS in 3, Repeat Rate in 3, etc.
6. **Header chrome reduction** — single dashboard-level metadata header replaces per-tab period+freshness duplicates. Estimated ~30% widget reduction across portfolio.
7. **Filter consistency** — Segment / Channel / Date filters present on every dashboard where applicable. Currently inconsistent (Retention has Segment filter, Intelligence doesn't, etc.).
8. **Attribution methodology page** — document Level 1/2/3 attribution rigor; each dashboard label its level. Stops over-trust of weak signals.

### 5.2 Known platform constraints to surface

- **Metabase v0.58.11 `scalar.comparisons` broken** (per memory) — currently used in `product_performance` (4 heroes) and likely others. Migrate to manual 2-column scalar pattern.
- **DuckDB filter type limitations** — `date/all-options` and `string/=` filter types not supported in native SQL templates. Affects `marketing_monthly_analysis` (acknowledged) and any monthly dashboard with parameter. Document as portfolio-level constraint, not per-blueprint footnote.
- **`fact_targets` underused** — currently only `gmv` cycle=monthly consumed. Schema supports daily/weekly/monthly × any metric. Adding `gross_margin_pct`, `discount_rate_pct`, `return_rate_pct`, `net_profit`, `new_customers` makes every threshold gauge data-driven.

### 5.3 Skeletons / blocked dashboards

| Dashboard | Status | Recommendation |
|-----------|--------|----------------|
| `finance_cashflow` | Skeleton — no fact_payments classification | Mark "DEFERRED — Q3" in catalog. Hide from collection. |
| `product_inventory` | Skeleton — no fact_inventory | Mark "DEFERRED — pending pipeline" |
| `logistics_shipping` | Blocked — no fact_shipments + dim_carriers | Mark "DEFERRED — pending pipeline" |

These dilute portfolio coverage signal; users see them in catalog and assume coverage exists.

---

## 6. Implementation Roadmap

### Phase 1 (1-2 weeks) — Stop the bleeding (critical bugs)

1. **Fix CEO Monthly target widget** (hardcoded 600M → real `fact_targets.target_gmv`). [1 day]
2. **Build `mart_customer_status_snapshot_monthly`** + rewire ~15 wrong MoM scalars in customer_retention + customer_intelligence. [3-5 days]
3. **Audit `scalar.comparisons` usage** across product_performance + others; migrate to 2-column scalar pattern. [2 days]
4. **Mark skeleton dashboards as DEFERRED** in collection_registry; remove from active deployment. [0.5 day]

### Phase 2 (2-4 weeks) — Foundation marts + seeds

5. **Build `mart_sku_economics_monthly`** (one row per SKU-month with all economic columns including return-adjusted margin). [1 week]
6. **Add `rfm_segment_label` to `dim_customers`** via NTILE on R/F/M. [2 days]
7. **Seed `dim_channel_targets`** + extend `fact_targets` schema to non-GMV metrics. [3 days, depends on business input]
8. **Seed `dim_customer_action_playbook`** (segment×status → action/owner/SLA). [2 days, depends on CS input]
9. **Create `cs_outreach_log` table** + agree CS workflow change for logging. [1 week incl. process change]

### Phase 3 (4-8 weeks) — Consolidate dashboards

10. **Customer cluster:** merge `customer_retention` + `customer_intelligence_monthly` → `customer_health_cockpit` (4 tabs, ~22 widgets). Decommission originals via redirect. [1 week]
11. **Product cluster:** merge `finance_product_cost_margin` + `product_performance` + `product_profitability` → `merch_sku_economics` + `merch_return_impact` (2 dashboards from 3+). [1 week]
12. **CEO cluster restructure:** Weekly Pulse → Pace+Alerts (5-6 widgets); Monthly Scorecard → Strategy+Bets (~14 widgets). [1 week]
13. **Deprecate `channel_profitability_monthly`** (overstates ECOM margin, redundant with `finance_channel_pl`). [0.5 day]
14. **Combine `sales_daily_operation` + `sales_yesterday_operation`** with date filter. [3 days]
15. **Reduce `finance_pl` Shopee + Channel tabs** to headline scalar + drill-link to deep-dive dashboards. [3 days]

### Phase 4 (8-12 weeks) — Insight unlocks

16. **Sales Promotion Analysis:** voucher abuse detection, cannibalization analysis, ROI by customer type. [1 week]
17. **Marketing ROI:** attribution integrity widget, spend coverage health, CAC + Payback. [1 week]
18. **Channel P&L:** loss driver decomposition, SKU drill on loss channels, target overlay. [3-5 days]
19. **Shopee Channel:** Voucher Xtra ROI split, fee tier what-if, true Net Margin hero, real scatter at order grain. [3-5 days]
20. **Return Impact:** SKU-level return tab, days-to-return histogram, prescriptive action mapping, return-adjusted margin. [1 week]
21. **CEO Monthly:** MoM Revenue Bridge, YoY columns, customer concentration risk, cohort heatmap. [1 week]
22. **CEO Weekly:** Loss-channel drill table, MTD trio, rule-based alerts table, narrative card. [3-5 days]
23. **Standard action-triggers widget** rolled out to top 8 dashboards. [1 week]
24. **Narrative summary cards** added to weekly/monthly major dashboards. [3 days]

### Phase 5 (3-6 months) — New data foundation

25. Build `recon_sapo_orders_daily` + `recon_misa_daily` + `recon_shopee_daily` true recon marts.
26. Complete `fact_marketing_spend` ingestion (unblock CAC, payback, attribution).
27. Plan `fact_inventory` pipeline (unblock dead-stock, slow-mover, OOS rate).
28. Plan `fact_gl_entries` ingestion (unblock true EBITDA, operating margin).

### Phase 6 (6-12 months) — Advanced perspectives

29. Anomaly detection / alerting subsystem (Lark/Slack hooks).
30. A/B test framework + reporting widgets.
31. Forward CLV model + LTV/CAC by channel.
32. Returns prevention scoring (ML on order features).
33. Demand forecasting / replenishment recommendation.
34. Price elasticity analysis.

---

## 7. Quick Wins (this week)

1. **Mark skeleton dashboards DEFERRED** — `finance_cashflow`, `product_inventory`, `logistics_shipping`. [0.5 day]
2. **Add target text card to CEO Monthly** — workaround for hardcoded 600M until proper fix. [1 hour]
3. **Pull action-trigger tables from playbooks → text cards on dashboards** — make invisible triggers visible. [2 days]
4. **Auto-recon scalar** on `orders_list_reconciliation`: Sapo count − BI count = X. [1 day]
5. **Loss-channel drill table** on CEO Weekly: replace scalar with name+VND table. [0.5 day]
6. **Header chrome cleanup** — consolidate per-tab period+freshness duplicates to dashboard-level. [3 days across portfolio]

---

## 8. Top 10 "Highest Leverage Per Hour Invested"

| Rank | Action | Hours | Value |
|------|--------|-------|-------|
| 1 | Build `mart_customer_status_snapshot_monthly` (fixes 15 wrong widgets) | 24 | Trust restored to customer dashboards |
| 2 | Fix CEO Monthly target widget hardcoded 600M | 4 | Trust to top-of-house "are we on plan" |
| 3 | Build `mart_sku_economics_monthly` + return-adjusted margin view | 40 | Single source of SKU truth; unlocks return-prone analysis |
| 4 | Merge customer_retention + customer_intelligence → cockpit | 40 | -25 widgets, +outcome loop, +RFM, +action queue |
| 5 | Add SKU-level return analysis | 8 | Biggest gap in return blueprint |
| 6 | Voucher abuse detection on sales_promotion | 8 | Direct margin recovery |
| 7 | Action-triggers visible on top 8 dashboards | 40 | Translates portfolio from descriptive → prescriptive |
| 8 | YoY columns on all monthly heroes | 8 | Fixes seasonality blindness |
| 9 | Auto-recon scalar on orders_list_reconciliation | 6 | Replaces manual eyeball cross-check |
| 10 | Deprecate `channel_profitability_monthly` (or restrict) | 4 | Removes ECOM margin overstatement misinformation |

---

## 9. Unresolved Questions

1. Is `fact_targets` populated for non-GMV metrics, or does adding require Google Sheets schema change?
2. Does `int_misa_sales_lines` carry vendor / first-PO reference? (Determines SKU-prefix proxy viability for supplier rollup.)
3. Does `fact_order_returns` carry `product_code` directly or only `order_code`? (Determines join path for SKU-level return analysis.)
4. What status values exist for returns (resaleable/damaged)? (Needed for net-return-impact calculation.)
5. Are MISA's 35% non-covered orders systematically biased toward specific channels (e.g. Shopee)? (Affects fairness of cross-channel margin comparisons.)
6. Is there an existing CS action log table anywhere? (Needed for outcome-loop widget.)
7. Is `dim_customers.recency_days` recomputed daily or only at month-end? (Affects daily-refresh of customer health heroes.)
8. Is `loyalty_point` actively maintained or stale? (If stale, Loyalty Distribution widget is fiction.)
9. Should B2B customers get their own retention dashboard, or is RETAIL-only scope permanent?
10. Is `fact_marketing_spend.channel_key` mapped to ad-channel or sales-channel? (Determines if attribution model is recoverable.)
11. Does business support running holdout / A-B tests on promotions, or is attribution permanently capped at Level 2 (directional)?
12. Are usage telemetry / view counts available per dashboard/question? (Would prioritize prune list by actual usage, not assumed.)
13. Is `sales_monthly_review` backed by a live dashboard or pure process doc (status TBD)?
14. Confirm v0.58.11 broken-feature list beyond `scalar.comparisons`?
15. Are the 26 non-deep-dived blueprints likely to surface additional bugs (b2b_*, us_crossborder, marketing_monthly_analysis, sales_monthly_review specifically)?

---

## Appendix A. Playbook Inventory Summary (32 playbooks)

Full per-playbook inventory available in research notes. Highlights:

- **Strongest action-trigger discipline:** `sales_promotion_analysis`, `marketing_roi`, `logistics_operations`, `ingestion_health`, `sales_monthly_review`, `sales_ops_weekly_review`, `sales_ops_monthly_summary`.
- **Weakest action-trigger discipline (decision-critical):** `ceo_monthly_scorecard`, `ceo_weekly_pulse`, `customer_operational_dashboard`, `customer_retention`, `customer_intelligence_monthly`, `order_detail_view`, `rill/orders_executive`.
- **Heavy redundancy clusters:** finance (`finance_pl` ↔ `finance_channel_pl` ↔ `channel_profitability_monthly` ↔ `finance_cost_ledger`); customer (`customer_retention` ↔ `customer_intelligence_monthly`); marketing (`marketing_weekly_tracker` ↔ `marketing_monthly_analysis` ↔ `marketing_roi` ↔ `sales_promotion_analysis`); daily ops (`sales_daily_operation` ↔ `sales_yesterday_operation`).
- **Heaviest card budgets** (consolidation candidates): `sales_ops_monthly_summary` (43 cards), `sales_ops_weekly_review` (35), `marketing_monthly_analysis` (~40 across 5 tabs), `ceo_monthly_scorecard` (~28).
- **Skeletons / blocked:** `finance_cashflow`, `product_inventory`, `logistics_shipping`.

---

**End of audit report.**
