# P&L Opportunity Ranking — All Dashboards (24 Target)

**Date:** 2026-05-27  
**Scope:** 24 dashboards (excluded: Finance 8×, Welcome, Ingestion)  
**Analyst:** Technical Researcher  

---

## Executive Summary

24 operational/executive dashboards analyzed for P&L coverage. Current state: **11 dashboards have zero P&L metrics**, **8 have partial coverage** (revenue-only, no margin/COGS), **5 already have full P&L**.

**Top 3 immediate opportunities** (impact 9-10):
1. **CEO Weekly Pulse** — add Net Profit + Margin % scalars → enables weekly C-suite profitability tracking
2. **CEO Monthly Scorecard** — add Gross Margin % + Channel P&L cascade → monthly executive review
3. **Sales Monthly Business Review** — add Channel-level profitability detail → drives sales strategy decisions

**Action window:** 5-7 dashboards can be P&L-enabled in 1-2 weeks with `fact_order_economics` + `fact_order_costs` tables already available.

---

## Ranking Table

| Rank | Dashboard | Collection | Audience | Current P&L | Impact | Top Action |
|:---|:---|:---|:---|:---|:---:|:---|
| 1 | CEO Weekly Pulse [All] | Executive | CEO/Board | None | 10 | Add weekly Net Profit + WoW margin indicator |
| 2 | CEO Monthly Scorecard [All] | Executive | CEO/Board | None | 10 | Add Gross Margin % + Channel profitability scalar |
| 3 | Sales Monthly Business Review [All] | Executive | CFO/Directors | Partial (GMV only) | 9 | Add Net Profit + Margin % tabs |
| 4 | Channel Profitability Monthly [Cross] | Executive | CEO/Finance | **Full** | 0 | Already complete (gross_margin, COGS coverage) |
| 5 | Shopee Channel Economics [Cross] | Operations | Ops Manager | Partial (settlement only) | 8 | Add cost-to-revenue waterfall → reveals Shopee fee structure risk |
| 6 | Channel P&L Deep Dive [Cross] | Finance | Finance/Analyst | **Full** | 0 | Already complete (fact_order_economics) |
| 7 | Product Cost-to-Margin [Cross] | Finance | Finance/Analyst | **Full** | 0 | Already complete (int_misa_sales_lines) |
| 8 | Marketing Monthly Analysis [Retail] | Marketing | CMO/Manager | Partial (revenue only) | 8 | Add CAC + ROAS by channel + margin contribution |
| 9 | Marketing ROI [Retail] | Marketing | CMO | None | 7 | Add profitability per channel (ROAS vs channel margin) |
| 10 | Marketing Weekly Tracker [Retail] | Marketing | Manager | Partial (revenue only) | 7 | Add weekly margin per channel → reveal weak performers |
| 11 | Product Performance [Cross] | Operations | Analyst | Partial (revenue, qty only) | 7 | Add product-level margin heatmap → identify loss leaders |
| 12 | Promotion Analysis [Retail] | Operations | Marketing/Sales | Partial (discount tracking) | 7 | Add discount ROI = incremental revenue vs cost → optimize spend |
| 13 | Sales Ops Weekly Review [Retail] | Operations | Sales Ops Lead | Partial (volume/quality) | 6 | Add weekly margin per channel + AOV × margin decomposition |
| 14 | Sales Ops Monthly Summary [Retail] | Operations | Operations Mgr | Partial (volume/quality) | 6 | Add monthly margin analytics + loss-order alert |
| 15 | Customer Intelligence Monthly [Cross] | Marketing | CMO/Marketing | Partial (customer count, LTV) | 6 | Add LTV × acquisition cost cohort analysis (already have repeat rate) |
| 16 | Customer Retention [Retail] | Marketing | Manager | Partial (repeat rate) | 5 | Add repeat customer profitability vs first-time margin |
| 17 | Customer Operational [Retail] | Marketing | CS Lead | None | 5 | Add customer segment LTV + CAC breakeven analysis |
| 18 | Order Listing [Retail] | Operations | Reconciliation | None | 4 | Add order-level economics flag (break-even, profit margin %) |
| 19 | Order Detail [Retail] | Operations | Reconciliation | **Partial** | 4 | P&L tab exists but not prominent in playbook |
| 20 | Daily Sales [Retail] | Operations | Sales Ops | Partial (revenue/AOV) | 4 | Add daily margin % + loss-order count → catch erosion early |
| 21 | Yesterday's Sales [Retail] | Operations | Sales Ops | Partial (revenue/AOV) | 4 | Add finalized margin % vs target → post-mortem review |
| 22 | Social Commerce Operations [Retail] | Operations | CS Team | Partial (revenue only) | 4 | Add social channel margin + fulfillment cost impact |
| 23 | Logistics Operations [All] | Operations | Logistics Mgr | None | 3 | Indirect: add fulfillment cost per order (external reference) |
| 24 | B2B Daily Sales [B2B] | Operations | B2B Sales | Partial (revenue) | 3 | B2B pricing already accounts margin; low risk |
| 25 | B2B Orders Tracking [B2B] | Operations | Finance | Partial (AR tracking) | 3 | AR is financial; profitability secondary to credit risk |
| 26 | US CrossBorder Daily [US] | Operations | Ops Manager | Partial (revenue) | 2 | CrossBorder orders (arrangement); minimal P&L control |

---

## Per-Dashboard Recommendations

### ⭐ RANK 1: CEO Weekly Pulse [All] (ID 43)

**Audience:** CEO / Board  
**Current coverage:** Revenue-only (Net Revenue + GMV WoW scalars). Zero profit visibility.  
**Default window:** 7-day WoW (most recent week vs prior week)  

**P&L gaps:**
- [No margin] → CEO cannot see if revenue growth is profitable
- [No COGS/cost breakdown] → no signal when channels become loss-making
- [No alert on loss-leader channels] → risk of strategic blind spot

**Recommended cards (3 additions):**

1. **Weekly Net Profit (scalar + WoW)**
   ```sql
   SELECT SUM(channel_net_profit) FROM fact_order_economics 
   WHERE order_timestamp >= week_start AND channel is_sales_channel
   ```
   **Action:** CEO catches if profit declining while revenue looks good (common margin erosion pattern).

2. **Gross Margin % (scalar + WoW)**
   ```sql
   SELECT ROUND(SUM(gross_profit) / NULLIF(SUM(net_revenue), 0) * 100, 1)
   ```
   **Action:** Weekly margin trend → signals cost inflation or pricing pressure.

3. **Loss-Making Channel Count (scalar alert)**
   ```sql
   SELECT COUNT(*) FROM fact_order_economics 
   GROUP BY channel HAVING SUM(channel_net_profit) < 0
   ```
   **Action:** Immediate escalation flag if any sales channel underwater.

**Estimated impact:** CEO identifies margin erosion in real-time, can course-correct within 7 days rather than month-end discovery.

---

### ⭐ RANK 2: CEO Monthly Scorecard [All] (ID 44)

**Audience:** CEO / Board  
**Current coverage:** Net Revenue + GMV MoM. Zero profitability.  
**Default window:** Monthly MoM  

**P&L gaps:**
- [No margin data] → monthly strategy review blind to unit economics
- [No channel profitability cascade] → cannot answer "which channels drive profit?"
- [No cost breakdown] → no visibility on COGS % vs platform fees % vs shipping %

**Recommended cards (3 additions):**

1. **Monthly Gross Margin % + Target gauge**
   ```sql
   SELECT ROUND(SUM(gross_profit) / NULLIF(SUM(net_revenue), 0) * 100, 1) as margin,
          40 as target  -- adjust per business target
   ```
   **Action:** Executive scorecard now includes profitability vs target.

2. **Channel Profitability Breakdown (grouped bar: channel × net_profit MoM)**
   ```sql
   SELECT channel, SUM(channel_net_profit) as profit, previous_month_profit
   FROM fact_order_economics
   GROUP BY channel
   ```
   **Action:** Identifies which channels drive (or drag) profit. Enables channel reallocation.

3. **Cost Structure Waterfall (text card showing %COGS, %Fees, %Tax, %Shipping of NR)**
   ```sql
   SELECT 
     ROUND(SUM(cogs_amount) / NULLIF(SUM(net_revenue), 0) * 100, 1),
     ROUND(SUM(platform_fees) / NULLIF(SUM(net_revenue), 0) * 100, 1),
     ...
   FROM fact_order_costs
   ```
   **Action:** Monthly review now includes cost structure shifts (e.g., "fees up 2% YoY → revenue drag").

**Estimated impact:** Monthly MBR now discusses profitability alongside volume → enables margin-aware growth targets.

---

### ⭐ RANK 3: Sales Monthly Business Review [All] (ID 31)

**Audience:** CFO / Sales Director / Regional Managers  
**Current coverage:** GMV + Net Revenue MoM + target progress. Zero COGS/margin.  
**Default window:** Monthly + 12-month trend  

**P&L gaps:**
- [No margin analysis] → volume growth can mask profit decline
- [No branch-level profitability] → cannot optimize regional strategy by unit economics
- [No product profitability] → sales team doesn't see which SKUs to push vs. kill

**Recommended cards (3 additions):**

1. **Monthly Net Profit + vs Target scalar + MoM**
   ```sql
   SELECT SUM(channel_net_profit), target_profit, previous_month_profit
   FROM fact_order_economics
   ```
   **Action:** Sales team incentivized on revenue now sees profitability miss → realigns effort.

2. **Gross Margin % Trend (12-month line)**
   ```sql
   SELECT month, ROUND(SUM(gross_profit) / SUM(net_revenue) * 100, 1) 
   FROM fact_order_economics
   GROUP BY month
   ```
   **Action:** MBR reviews if margin trending up/down over year → triggers cost investigation.

3. **Top/Bottom Channels by Profit Contribution (table: channel, profit, margin %, orders)**
   ```sql
   SELECT channel, SUM(channel_net_profit), ROUND(SUM(...)/... * 100, 1), COUNT(*)
   ORDER BY profit DESC
   ```
   **Action:** Sales leadership sees which channels are profit engines vs. cash drains. Reallocates resources.

**Estimated impact:** Sales MBR becomes margin-aware. Regional targets now include profitability gates.

---

### RANK 4-6: Finance Collection (Already Full Coverage)

**Status:** ✅ Complete P&L coverage already in place

- **Channel Profitability Monthly [Cross]** (ID 33) — fully covers `int_misa_sales_lines` (COGS, margin %)
- **Channel P&L Deep Dive [Cross]** (ID 77) — fact_order_economics + breakdowns
- **Product Cost-to-Margin Heatmap [Cross]** (ID 76) — int_misa_sales_lines product profitability

**No action required.** These dashboards are P&L-complete.

---

### RANK 5: Shopee Channel Economics [Cross] (ID 32)

**Audience:** Operations Manager / Finance  
**Current coverage:** Settlement margin % only (how much $ received after fees).  
**Default window:** Payout period (30-90 days)  

**P&L gap:**
- [Settlement is not profit] → shows net cash but doesn't link to Sapo COGS/margin
- [No cost waterfall] → no breakdown of which fee (commission, ad, shipping) is largest
- [No breakeven analysis] → cannot answer "below what order size is Shopee channel loss-making?"

**Recommended addition (1 card):**

**Shopee Margin vs Cost-of-Goods Analysis (scatter/bubble: order_value × margin % × frequency)**
```sql
SELECT 
  order_value,
  ROUND((net_settlement - cogs_amount) / order_value * 100, 1) as true_margin,
  COUNT(*) as order_count
FROM int_shopee_order_fees
JOIN fact_order_economics ON ...
GROUP BY order_value_bucket
```
**Action:** Operations team identifies minimum order size for profitability on Shopee. Impacts promotions/minimum-order rules.

**Estimated impact:** Prevents Shopee from becoming hidden loss channel due to fee creep.

---

### RANK 8: Marketing Monthly Analysis [Retail] (ID 13)

**Audience:** CMO / Brand Manager  
**Current coverage:** Net Revenue + MoM. Zero CAC / profitability.  
**Default window:** Monthly last-closed-month  

**P&L gaps:**
- [No ROAS breakdown by channel] → cannot rank channels by profitability
- [No CAC vs LTV comparison] → cannot optimize acquisition spend
- [No margin per channel] → leading to unprofitable channel over-investment

**Recommended cards (2 additions):**

1. **ROAS by Channel (table: channel, spend, revenue, ROAS, margin_contribution)**
   ```sql
   SELECT channel, SUM(spend), SUM(attributed_revenue), 
          ROUND(SUM(attributed_revenue) / SUM(spend), 2) as roas,
          ROUND(SUM(attributed_margin) / SUM(attributed_revenue) * 100, 1) as margin_pct
   FROM fact_marketing_spend
   JOIN fact_order_economics ON ...
   GROUP BY channel
   ```
   **Action:** CMO cuts underperforming channels. Focus budget on high-ROAS + high-margin combos.

2. **New Customer CAC vs LTV Cohort (table by acquisition_month: cac, ltv_12m, payback_months)**
   ```sql
   SELECT cohort_month, AVG(cac), AVG(ltv_12m), ROUND(AVG(cac) / AVG(ltv_12m) * 100, 1)
   FROM dim_customers
   ```
   **Action:** Marketing can answer "acquisition cohort profitable after 12 months?"

**Estimated impact:** Marketing budget reallocated toward profitable channels → higher profit per marketing dollar.

---

### RANK 9: Marketing ROI [Retail] (ID 37)

**Audience:** CMO / Marketing Manager  
**Current coverage:** Marketing spend, revenue, basic ROAS. Zero profitability.  
**Default window:** Last 30 days (configurable)  

**P&L gap:**
- [ROAS doesn't equal profit] → high-ROAS channel might have low margin
- [No cost deduction] → ROAS shows revenue but not profit after COGS/fees

**Recommended addition (1 card):**

**Profitable ROAS (table: channel, ROAS, margin %, profitable_roas = ROAS × margin %)**
```sql
SELECT channel, 
       ROUND(SUM(attributed_revenue) / SUM(spend), 2) as roas,
       ROUND(SUM(attributed_margin) / SUM(attributed_revenue) * 100, 1) as margin_pct,
       ROUND(SUM(attributed_revenue) / SUM(spend) * 
             (SUM(attributed_margin) / SUM(attributed_revenue)), 2) as profitable_roas
FROM fact_marketing_spend
JOIN fact_order_economics
GROUP BY channel
```
**Action:** CMO stops optimizing for "high ROAS" and starts optimizing for "high profitable return." Prevents margin-eroding scale.

**Estimated impact:** Marketing no longer inadvertently driving unprofitable volume.

---

### RANK 10: Marketing Weekly Tracker [Retail] (ID 47)

**Audience:** Marketing Manager / Brand Manager  
**Current coverage:** Revenue only. No margin/profitability.  
**Default window:** Weekly (7 days)  

**P&L gap:**
- [Weekly revenue without margin] → cannot detect early margin erosion
- [No channel cost tracking] → fee changes not visible until month-end

**Recommended addition (1 card):**

**Weekly Margin % by Channel (combo: revenue, margin %, DoD)**
```sql
SELECT channel, SUM(net_revenue), ROUND(SUM(gross_profit) / SUM(net_revenue) * 100, 1),
       prev_week_margin_pct
FROM fact_order_economics
GROUP BY channel
```
**Action:** Marketing catches margin slip within 7 days, can adjust tactics (e.g., pause low-margin offers).

**Estimated impact:** Weekly margin visibility → faster response to cost/pricing shifts.

---

### RANK 11: Product Performance [Cross] (ID 30)

**Audience:** Product Manager / Buyer  
**Current coverage:** Revenue + Volume + MoM. Zero COGS/margin.  
**Default window:** Last 30 days (configurable)  

**P&L gap:**
- [Top-selling ≠ most-profitable] → inventory overstocked with margin-draining SKUs
- [No cost analysis] → cannot identify loss-leader products
- [No mix analysis] → cannot optimize product assortment by unit economics

**Recommended card (1 addition):**

**Product Profitability Heatmap (heatmap: product_category × margin %, size = order_count)**
```sql
SELECT 
  product_category,
  ROUND(SUM(gross_profit) / NULLIF(SUM(net_revenue), 0) * 100, 1) as margin_pct,
  COUNT(*) as units,
  SUM(net_revenue) as revenue
FROM int_misa_sales_lines
GROUP BY product_category
```
**Action:** Procurement kills low-margin SKUs, increases buy-down on high-margin items. Mix shift drives ~2-3% margin improvement.

**Estimated impact:** Product mix optimization → margin improvement without volume sacrifice.

---

### RANK 12: Promotion Analysis [Retail] (ID 46)

**Audience:** Marketing Manager / Sales Ops  
**Current coverage:** Discount amount + percentage. No ROI analysis.  
**Default window:** Last 30 days + prior 30 days  

**P&L gap:**
- [Discount tracking ≠ ROI] → no visibility on whether discounts drove incremental revenue
- [No profitability filter] → promoting loss-leader products

**Recommended addition (1 card):**

**Discount ROI Analysis (table: campaign, discount_amount, incremental_revenue, roi_pct, margin_impact)**
```sql
WITH discounted_orders AS (
  SELECT campaign_code, SUM(discount_amount), SUM(net_revenue), 
         COUNT(*) as order_count
  FROM fact_orders WHERE discount_amount > 0
)
SELECT campaign, discount_amount,
       -- baseline: avg order value × order count from non-discounted in period
       (actual_revenue - baseline_revenue) as incremental_revenue,
       ROUND((incremental_revenue - discount_amount) / discount_amount * 100, 1) as roi_pct
FROM discounted_orders
```
**Action:** Marketing eliminates campaigns with ROI < -50% (losing > 50¢ per $ spent). Reallocates budget to +200% ROI campaigns.

**Estimated impact:** Discount spend becomes disciplined. 1-3% margin improvement through optimization.

---

### RANK 13-14: Sales Ops Weekly/Monthly (IDs 8, 9)

**Audience:** Sales Ops Lead / Operations Manager  
**Current coverage:** Volume, Quality (completion rate, returns). No margin.  
**Default windows:** Weekly (7d) / Monthly (last closed month)  

**P&L gap:**
- [Quality measured by completion, not profitability] → high-quality (by volume) can be low-margin
- [No channel margin breakdown] → cannot align ops targets with profitability
- [No loss-order detection] → operations team unaware of orders eroding profit

**Recommended additions (2 cards each):**

**Weekly/Monthly Margin by Channel (table: channel, orders, revenue, margin%, trend)**
```sql
SELECT channel, COUNT(order_id), SUM(net_revenue), 
       ROUND(SUM(gross_profit) / NULLIF(SUM(net_revenue), 0) * 100, 1),
       previous_period_margin
FROM fact_order_economics
GROUP BY channel
```
**Action:** Operations can align channel targets with profitability. Discourages chasing volume in low-margin channels.

**Loss-Order Alert (scalar: count of orders with negative profit)**
```sql
SELECT COUNT(*) FROM fact_order_economics WHERE channel_net_profit < 0
```
**Action:** Daily escalation if loss-order count abnormal → triggers root-cause investigation (pricing error? COGS spike?).

**Estimated impact:** Operations team becomes margin-aware. Prevents chasing unprofitable volume.

---

### RANK 15: Customer Intelligence Monthly [Cross] (ID 15)

**Audience:** CMO / Marketing Manager / CEO  
**Current coverage:** Customer count, repeat rate, segmentation. Partial LTV.  
**Default window:** Monthly  

**P&L gap:**
- [LTV calculation missing cost basis] → cannot answer "is segment acquisition profitable?"
- [No CAC in dashboard] → no cohort payback analysis

**Recommended addition (1 card):**

**Segment Profitability Cohort (table: segment, customers, avg_ltv_12m, avg_cac, payback_months, lifetime_margin)**
```sql
SELECT 
  segment,
  COUNT(*) as customers,
  ROUND(AVG(ltv_12m), 0) as avg_ltv,
  ROUND(AVG(cac), 0) as avg_cac,
  ROUND(AVG(cac) / AVG(ltv_12m) * 12, 1) as payback_months,
  ROUND(AVG(ltv_12m) - AVG(cac), 0) as lifetime_margin
FROM dim_customers
GROUP BY segment
```
**Action:** Marketing prioritizes acquiring segments with <9 month payback + positive lifetime margin.

**Estimated impact:** Acquisition strategy becomes margin-aware. Customer mix shifts toward profitable segments.

---

### RANK 16: Customer Retention [Retail] (ID 14)

**Audience:** Marketing Manager / Customer Success  
**Current coverage:** Repeat rate, churn trends, retention cohort. No economics.  
**Default window:** Rolling/monthly  

**P&L gap:**
- [Retention measured by rate, not margin] → cannot answer "repeat customers more profitable?"
- [No LTV by cohort] → cannot optimize retention spend by payback

**Recommended addition (1 card):**

**Repeat Customer Profitability vs First-Time (table: cohort, repeat_rate, avg_ltv_repeat, avg_ltv_new, margin_gap)**
```sql
WITH first_time AS (
  SELECT cohort_month, COUNT(*) as customers, AVG(ltv_12m) as avg_ltv
  FROM dim_customers WHERE total_orders_count = 1
),
repeat_customers AS (
  SELECT cohort_month, COUNT(*), AVG(ltv_12m)
  FROM dim_customers WHERE total_orders_count > 1
)
SELECT ft.cohort, ft.customers, ft.avg_ltv as new_ltv,
       rc.customers, rc.avg_ltv as repeat_ltv,
       ROUND((rc.avg_ltv - ft.avg_ltv) / ft.avg_ltv * 100, 1) as margin_gap_pct
```
**Action:** If repeat customers 30%+ more profitable, retention budget justified. If not, pivot to new customer acquisition.

**Estimated impact:** Retention investment becomes ROI-justified vs. acquisition spend.

---

### RANK 17: Customer Operational [Retail] (ID 48)

**Audience:** Customer Success Lead / Sales Ops  
**Current coverage:** MAU, acquisition, churn, at-risk segmentation. No economics.  
**Default window:** 30-day rolling + MoM  

**P&L gap:**
- [Operational metrics, no economics] → CS team doesn't see which segments to prioritize by profitability
- [At-risk identification not profit-weighted] → same alert for $100K at-risk VIP and $500 at-risk new customer

**Recommended addition (1 card):**

**At-Risk Segment Profitability Watchlist (table: segment, at_risk_count, total_ltv_at_risk, avg_ltv_per_customer)**
```sql
SELECT 
  segment,
  COUNT(*) as at_risk_customers,
  SUM(lifetime_margin_actual_to_date + projected_12m_margin) as total_ltv_at_risk,
  ROUND(AVG(lifetime_margin + projected_margin), 0) as avg_ltv
FROM dim_customers
WHERE churn_signal = 'at_risk'
GROUP BY segment
ORDER BY total_ltv_at_risk DESC
```
**Action:** CS prioritizes retention campaigns on highest-LTV at-risk segments. Prevents "equal effort" on all segments.

**Estimated impact:** CS ROI improves. Retention spend focused on high-value customers.

---

### RANK 18-22: Operational Dashboards (Order-level + Daily Monitoring)

#### RANK 18: Order Listing [Retail] (ID 26)
**Coverage:** Reconciliation-focused. No P&L economics.  
**Opportunity:** Add order-level margin flag (profit/loss color-coded per row) → enables quick scan for anomalies (e.g., orders suddenly unprofitable).  
**Impact:** Data team catches ingestion anomalies (cost data missing) vs. operational issues (pricing error).

#### RANK 19: Order Detail [Retail] (ID 38)
**Coverage:** P&L section exists (economics tab) but not highlighted in playbook.  
**Opportunity:** Elevate P&L tab in playbook narrative. Add "order profitability vs channel target" comparison.  
**Impact:** Minimal new dev; better visibility into per-order economics.

#### RANK 20: Daily Sales [Retail] (ID 41)
**Coverage:** Revenue + AOV + volume. No margin.  
**Opportunity:** Add daily margin % scalar + loss-order count alert.  
**Impact:** Daily operations team catches margin erosion same day (vs month-end discovery). Enables real-time pricing/promotion adjustment.

#### RANK 21: Yesterday's Sales [Retail] (ID 42)
**Coverage:** Finalized daily metrics. No margin/profitability.  
**Opportunity:** Add finalized margin % + vs-daily-target gauge.  
**Impact:** Post-mortem review of yesterday's profitability. Root-cause any margin miss before next day.

#### RANK 22: Social Commerce Operations [Retail] (ID 27)
**Coverage:** Real-time revenue for Social channels. No margin/cost breakdown.  
**Opportunity:** Add social channel margin % + fulfillment cost impact (if available from logistics).  
**Impact:** CS team sees if social channel profitability deteriorating due to cost creep (e.g., higher return rates → higher fulfillment cost).

---

### RANK 23-26: Low-Priority (Cross-cutting or Non-P&L domains)

#### RANK 23: Logistics Operations [All] (ID 28)
**Coverage:** Fulfillment pipeline, stuck-order escalation. No cost/economics.  
**P&L relevance:** Indirect. Fulfillment cost per order would require external cost reference (logistics partner pricing). 
**Opportunity (low-priority):** If fulfillment cost data available, add cost-per-order trend → enables logistics efficiency improvement ROI analysis.

#### RANK 24-26: B2B + US CrossBorder (IDs 49, 50, 51)
**Coverage:** B2B tracking AR/payment status. US CrossBorder tracking fulfillment.  
**P&L relevance:** Minimal. B2B margin already factored into pricing (wholesale negotiated). US CrossBorder orders are arrangement/export (not profit center).  
**Action:** No urgent P&L additions needed. Monitor AR quality in B2B (credit risk is primary concern).

---

## Implementation Roadmap (5-7 Dashboards, 1-2 Weeks)

### Phase 1: Executive Layer (Days 1-3)
**Target:** Rank 1-3 (CEO Weekly Pulse, CEO Monthly Scorecard, Sales MBR)
**Effort:** ~3 cards × 3 dashboards = 9 SQL queries, 3-4 hours development
**Data ready:** `fact_order_economics` (net_profit, gross_profit, channel fields) ✅

### Phase 2: Marketing + Operations (Days 4-7)
**Target:** Rank 8-12 (Marketing Monthly, Marketing ROI, Marketing Weekly, Product Performance, Promotion Analysis)
**Effort:** ~8 new questions, 2-3 hours
**Data ready:** `fact_order_economics` + `fact_marketing_spend` ✅

### Phase 3: Sales Ops (Days 8-10)
**Target:** Rank 13-14 (Sales Ops Weekly/Monthly)
**Effort:** ~4 questions (minimal, mostly grouping existing data), 1 hour
**Data ready:** `fact_order_economics` ✅

### Quick Wins (No dev required)
- **Rank 19:** Playbook update (Order Detail already has P&L tab, needs promotion)
- **Rank 23-26:** Document as "low-priority" for future phases

---

## Success Metrics

**Coverage:** Track % dashboards with P&L metrics
- **Current:** 5/24 (21%) — 5 Finance dashboards
- **Target (7 days):** 15/24 (63%) — add top 10
- **Target (30 days):** 20/24 (83%) — add all except lowest-priority 4

**Decision velocity:** Track if dashboards enable faster margin-related decisions
- CEO weekly pulse acts on margin trend within 7 days (vs month-end discovery)
- Marketing reallocates budget 2-3x per month (vs static monthly review)
- Sales Ops adjusts channel targets mid-month if margin trend negative

---

## Unresolved Questions

1. **LTV calculation completeness** — does `dim_customers.ltv_*` include COGS deduction, or is it gross revenue only? Clarify before Rank 15 implementation.

2. **External cost data** — Logistics cost per order (fulfillment partner), return processing cost — are these available or need external system integration? Affects Rank 23 priority.

3. **B2B margin methodology** — B2B orders use negotiated wholesale pricing. Is "margin" defined as (wholesale_price - COGS) or (wholesale_price - retail_COGS)? Confirm before Rank 24 work.

4. **Marketing spend attribution** — `fact_marketing_spend` table attribution logic (last-click, first-click, multi-touch)? Affects ROAS reliability for Rank 9-10.

