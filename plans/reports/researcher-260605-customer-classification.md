# Customer Classification Model: Complete Staff-Facing Guide

**Date:** 2026-06-05  
**Audience:** Sales, Marketing, Customer Success, Finance teams  
**Purpose:** Understand which customer classification fields staff control vs. which auto-compute in the pipeline  
**Maintained by:** Data Team  

---

## Executive Summary

When staff create or update a customer in Sapo, they control **TWO fields** explicitly. The remaining six classification dimensions are **auto-derived** by the data pipeline from order history and behavior:

| Staff Controls (Manual) | Auto-Derived by Pipeline |
|---|---|
| **customer_type** (Bản chất quan hệ) | value_group (Giá trị đóng góp) |
| **acquisition_source** (Nguồn khách) | lifecycle_stage (Giai đoạn) |
|  | channel_preference (Kênh ưa thích) |
|  | product_affinity (Brand ưa thích) |
|  | payment_behavior (Hành vi thanh toán) |
|  | geo_region (Vị trí địa lý) |
|  | discount_sensitivity (Phụ thuộc khuyến mãi) |
|  | next_purchase_signal (Vị trí trong chu kỳ mua) |

---

## PART 1: STAFF CONTROLS — customer_type (Manual, Mutually Exclusive)

### What Is It?
**customer_type** defines the **nature of the business relationship** with the customer. It affects pricing, discounts, communication strategy, and policy. Examples:
- A retail customer pays list price
- A wholesale customer gets 40-50% discount (fixed, not promotion)
- A staff member gets employee discount
- A KOL gets promotional support

### Values: 5 Options
Staff must choose exactly one of these when creating or updating a customer in Sapo:

| customer_type | Sapo Field Value | Meaning | Policy Impact |
|---|---|---|---|
| **RETAIL** | `TYPE_RETAIL` (or no tag) | Regular customer, buys via B2C channels | List price, standard terms |
| **WHOLESALE** | `TYPE_WHOLESALE` | Bulk buyer, distributor, retailer | ~40-50% fixed discount, wholesale terms |
| **PARTNER** | `TYPE_PARTNER` | Affiliate, CTV (content creator), small distributor | Custom per-partner pricing agreement |
| **STAFF** | `TYPE_STAFF` | Employee of the company | Employee discount rate |
| **KOL** | `TYPE_KOL` | Influencer, content creator with following | Promotional support + possible discount |

### How Staff Assign It
1. **In Sapo:** Customer → Group/Tag field → Select from the 5 options above
2. **Default:** If no tag is set, the system defaults to `RETAIL`
3. **Timing:** Set when creating customer; can be updated later if relationship changes (e.g., retail customer signs wholesale deal)
4. **Who decides:**
   - **Sales:** Approve WHOLESALE, PARTNER conversions; usually manage the tag updates
   - **HR:** Tag staff members as STAFF
   - **Marketing:** Tag KOL partnerships
   - **Default:** All new customers auto-default to RETAIL until manually changed

### Critical Rule: customer_type ≠ Purchase Volume
**Important distinction:**
- A **RETAIL customer** who spends 50M+ is still `customer_type=RETAIL` (but will be `value_group=VALUE_VIP`)
- A **WHOLESALE customer** is ALWAYS `customer_type=WHOLESALE` regardless of spend
- The discount they receive is **pricing policy**, not promotion — so analyses must NOT count wholesale discounts as "promotion effectiveness"

### Code Implementation (How Pipeline Reads It)
```sql
-- In dim_customers.sql, the pipeline reads customer_group from Sapo and derives customer_type:
CASE
    WHEN customer_group LIKE '%TYPE_WHOLESALE%' THEN 'WHOLESALE'
    WHEN customer_group LIKE '%TYPE_PARTNER%' THEN 'PARTNER'
    WHEN customer_group LIKE '%TYPE_STAFF%' THEN 'STAFF'
    WHEN customer_group LIKE '%TYPE_KOL%' THEN 'KOL'
    ELSE 'RETAIL'  -- Default
END as customer_type
```

---

## PART 2: STAFF CONTROLS — acquisition_source (Manual, NOT Yet Implemented in Sapo)

### What Is It?
**acquisition_source** tracks **where the customer came from** — which marketing channel, referral, or event brought them. Needed for measuring marketing ROI and CAC (Customer Acquisition Cost).

### Planned Values: 5 Options
Staff should eventually tag customers with one of these (Sapo implementation pending):

| acquisition_source | Code | Meaning | Use Case |
|---|---|---|---|
| Organic | `SOURCE_ORGANIC` | Found us via search or direct visit (no paid channel) | Baseline organic demand |
| Ads | `SOURCE_ADS` | Came from Facebook Ads, Google Ads, or other paid advertising | Paid channel ROI |
| Referral | `SOURCE_REFERRAL` | Recommended by another customer | Viral/word-of-mouth |
| KOL | `SOURCE_KOL` | Came via influencer/KOL content (distinct from being a KOL) | Influencer campaign ROI |
| Event | `SOURCE_EVENT` | Met at event, trade show, expo, or workshop | Event effectiveness |

### Status: **NOT YET AVAILABLE**
- **Current state:** `acquisition_source` is always NULL in the pipeline
- **Roadmap:** Planned for Phase 3 (Sapo integration pending)
- **What staff should do:** Start tracking in parallel using a separate system or manual tagging; data team will integrate when ready

### Code Implementation
```sql
-- Currently in dim_customers.sql:
CAST(NULL AS VARCHAR) as acquisition_source  -- Placeholder, always NULL
```

---

## PART 3: AUTO-DERIVED DIMENSIONS — What the Pipeline Computes

### 3.1 value_group (Lifetime Value Tier)

**What it measures:** Customer's **total spending** — their economic value to the company.

**Values:** 4 tiers (Mutually exclusive)

| Tier | Code | Threshold | Priority |
|---|---|---|---|
| VIP | `VALUE_VIP` | Lifetime spend ≥ 50M VND **OR** order count ≥ 20 | Highest |
| Gold | `VALUE_GOLD` | Lifetime spend ≥ 20M VND | High |
| Silver | `VALUE_SILVER` | Lifetime spend ≥ 5M VND | Medium |
| Bronze | `VALUE_BRONZE` | Below 5M (or new customers) | Standard |

**Logic (exact thresholds from code):**
```sql
CASE
    WHEN monetary_value >= 50000000 OR frequency >= 20 THEN 'VALUE_VIP'
    WHEN monetary_value >= 20000000 THEN 'VALUE_GOLD'
    WHEN monetary_value >= 5000000 THEN 'VALUE_SILVER'
    ELSE 'VALUE_BRONZE'
END
```

**How it updates:** Automatically whenever a customer completes an order. Recalculated daily by pipeline.

**Staff cannot override this** — it's purely data-driven.

**Example:**
- Customer A: Spent 50M total → `VALUE_VIP` (even if customer_type=RETAIL)
- Customer B: Retail, spent 3M → `VALUE_BRONZE`
- Customer C: Wholesale, spent 500K → still `VALUE_BRONZE` (spend, not type, determines tier)

---

### 3.2 lifecycle_stage (Customer Lifecycle State)

**What it measures:** **Where the customer is in their relationship journey** with the company.

**Values:** 4 mutually exclusive stages

| Stage | Code | Condition | Action |
|---|---|---|---|
| New | `LIFECYCLE_NEW` | First order ≤ 30 days ago AND total orders ≤ 2 | Onboarding, welcome campaigns |
| Active | `LIFECYCLE_ACTIVE` | Last purchase ≤ 90 days ago | Maintain relationship, upsell |
| At Risk | `LIFECYCLE_AT_RISK` | Last purchase 91–180 days ago | Win-back campaigns |
| Churned | `LIFECYCLE_CHURNED` | Last purchase > 180 days ago | Re-activation or archive |

**Logic:**
```sql
CASE
    WHEN lifespan_days <= 30 AND frequency <= 2 THEN 'LIFECYCLE_NEW'
    WHEN recency_days <= 90 THEN 'LIFECYCLE_ACTIVE'
    WHEN recency_days <= 180 THEN 'LIFECYCLE_AT_RISK'
    ELSE 'LIFECYCLE_CHURNED'
END
```

**How it updates:** Daily based on order dates. Every day a customer buys, their recency resets.

**Staff cannot override** — purely recency-based.

**Example timeline:**
- Day 0: Customer places first order → `LIFECYCLE_NEW`
- Day 45: Customer places 2nd order → Still `LIFECYCLE_NEW` (≤ 30 days from first, ≤ 2 orders)
- Day 100: No purchase for 100 days → `LIFECYCLE_AT_RISK` (91–180 days since last order)
- Day 200: Still no purchase → `LIFECYCLE_CHURNED`
- Day 205: Customer buys again → Back to `LIFECYCLE_ACTIVE` (< 90 days since last order)

---

### 3.3 channel_preference (Favorite Purchase Channel)

**What it measures:** Which **sales channel** the customer has used most often** (by order count, not value).

**Values:** 4 options

| Preference | Code | Channels Grouped |
|---|---|---|
| Social | `CHANNEL_SOCIAL` | Zalo, Facebook, Instagram (social commerce) |
| Marketplace | `CHANNEL_MARKETPLACE` | Shopee, Lazada, Tiki, TikTok Shop |
| Direct | `CHANNEL_DIRECT` | Web store, Telesale, Customer Service, B2B portal |
| Offline | `CHANNEL_OFFLINE` | In-store (POS) at company retail locations |
| Other | `CHANNEL_OTHER` | Unknown/unmapped channels |

**Logic:**
- Count orders by channel for each customer
- Return the channel with the **most orders** (mode)
- If no clear mode, fall back to "OTHER"

**How it updates:** Whenever a customer places an order via a new or different channel, preference may shift.

**Staff cannot override** — derived from order data.

**Example:**
- Customer has 5 orders via Shopee, 3 via Zalo, 2 via Web → `CHANNEL_MARKETPLACE` (Shopee is most used)
- Customer has 1 order via each channel → System picks one consistently (alphabetical tiebreaker in code)

---

### 3.4 product_affinity (Brand/Category Preference)

**What it measures:** Which **brand/product category** the customer spends the most revenue on.

**Values:** 4 options

| Affinity | Code | Condition |
|---|---|---|
| Fine Japan | `PRODUCT_FINE_JAPAN` | > 60% of customer's revenue is Fine Japan Vietnam brand |
| FG Care | `PRODUCT_FG_CARE` | > 60% of customer's revenue is FG Care brand |
| Fine Care | `PRODUCT_FINE_CARE` | > 60% of customer's revenue is Fine Care brand |
| Multi-brand | `PRODUCT_MULTI` | No single brand exceeds 60% (balanced portfolio) |

**Logic:**
```sql
CASE
    WHEN MAX(brand_revenue_share) FILTER (WHERE brand = 'Fine Japan Vietnam') > 0.6 
        THEN 'PRODUCT_FINE_JAPAN'
    WHEN MAX(brand_revenue_share) FILTER (WHERE brand = 'FG Care') > 0.6 
        THEN 'PRODUCT_FG_CARE'
    WHEN MAX(brand_revenue_share) FILTER (WHERE brand = 'Fine Care') > 0.6 
        THEN 'PRODUCT_FINE_CARE'
    ELSE 'PRODUCT_MULTI'
END
```

**How it updates:** Whenever a customer purchases a new brand or shifts spending patterns.

**Staff cannot override** — derived from sales history.

**Example:**
- Customer spent 25M on Fine Japan, 5M on FG Care, 2M other → `PRODUCT_FINE_JAPAN` (25M / 32M = 78% > 60%)
- Customer spent 10M on Fine Japan, 10M on FG Care, 2M other → `PRODUCT_MULTI` (no brand > 50%)

---

### 3.5 payment_behavior (Payment Method Pattern)

**What it measures:** How the customer typically **pays for orders** — COD, prepaid, or credit.

**Values:** 4 options

| Behavior | Code | Condition |
|---|---|---|
| Prepaid | `PAYMENT_PREPAID` | Customer pays upfront (bank transfer, e-wallet) |
| COD | `PAYMENT_COD` | > 70% of customer's orders use cash-on-delivery |
| Credit | `PAYMENT_CREDIT` | Has negotiated credit terms (B2B, pending) |
| Delinquent | `PAYMENT_DELINQUENT` | Has unpaid debt > 30 days overdue (pending) |

**Current Implementation (simplified, no credit/delinquent yet):**
```sql
CASE
    WHEN cod_orders / total_orders > 0.7 THEN 'PAYMENT_COD'
    ELSE 'PAYMENT_PREPAID'
END
```

**How it updates:** Based on payment method recorded for each order.

**Staff cannot override** — system-determined from payment records.

**Roadmap:** Credit limit and delinquency tracking (Phase 3) will enhance this.

**Example:**
- Customer: 2 COD orders, 1 prepaid → `PAYMENT_COD` (2/3 = 67%, but threshold is 70%, so... edge case)
- Customer: 8 COD orders, 2 prepaid → `PAYMENT_COD` (8/10 = 80% > 70%)
- Customer: 3 prepaid orders, 0 COD → `PAYMENT_PREPAID`

---

### 3.6 geo_region (Geographic Region)

**What it measures:** Customer's **delivery location** — grouped by regional zones.

**Values:** 5 regions

| Region | Code | Provinces Included |
|---|---|---|
| HCMC | `GEO_HCMC` | TP. Hồ Chí Minh (all variants) |
| Hanoi | `GEO_HANOI` | Hà Nội (all variants) |
| Mekong | `GEO_MEKONG` | 13 provinces in Mekong Delta (Cà Mau, Kiên Giang, Long An, etc.) |
| Central | `GEO_CENTRAL` | 14 provinces in Central Vietnam (Đà Nẵng, Huế, Quảng Nam, etc.) |
| Other | `GEO_OTHER` | All other provinces + unknown |

**Logic:**
- Determined by the **province field** in customer's primary address (from Sapo)
- Hard-coded province-to-region mapping in pipeline (case statement)

**How it updates:** When customer's address is updated in Sapo.

**Staff cannot override** — derived from address.

**Example:**
- Address province = "Hồ Chí Minh" → `GEO_HCMC`
- Address province = "Long An" → `GEO_MEKONG`
- Address province = NULL → `GEO_OTHER`

---

### 3.7 discount_sensitivity (Promo Dependency) — Computed Label

**What it measures:** How dependent is the customer on **discounts/promotions** to make a purchase decision?

**Values:** 3 options (NULL for new/no orders)

| Sensitivity | Code | Condition | Meaning |
|---|---|---|---|
| Promo Dependent | `PROMO_DEPENDENT` | > 70% of orders had discount applied | Highly price-sensitive; won't buy at full price |
| Promo Mixed | `PROMO_MIXED` | 30–70% of orders had discount | Balanced; responsive to well-timed promotions |
| Full Price | `FULL_PRICE` | ≤ 30% of orders had discount | Price-insensitive; driven by quality/trust |
| (NULL) | — | No qualifying orders to analyze | New customer or all orders cancelled |

**Logic:**
```sql
CASE
    WHEN discount_order_rate > 0.7 THEN 'PROMO_DEPENDENT'
    WHEN discount_order_rate > 0.3 THEN 'PROMO_MIXED'
    ELSE 'FULL_PRICE'
END
```

**How it updates:** Whenever a customer places a new order with or without discount.

**Staff cannot override** — computed from order history.

**Use Cases:**
- **PROMO_DEPENDENT:** Don't offer discount to these customers; focus on cost-down instead
- **PROMO_MIXED:** Best segment for promotion ROI; targeted offers work best
- **FULL_PRICE:** Protect margins; avoid discounts; sell on value

**Example:**
- Customer: 10 orders, 8 with discount → 80% → `PROMO_DEPENDENT`
- Customer: 10 orders, 5 with discount → 50% → `PROMO_MIXED`
- Customer: 10 orders, 2 with discount → 20% → `FULL_PRICE`

---

### 3.8 next_purchase_signal (Lifecycle Timing Signal) — Computed Label

**What it measures:** Is the customer **on schedule, overdue, or due soon** for their next purchase based on their personal purchase cycle?

**Values:** 3 options (NULL for 1-time buyers)

| Signal | Code | Condition | Action |
|---|---|---|---|
| Overdue | `OVERDUE` | Days since last order ≥ (avg cycle × 1.5) | High-priority reactivation; "we miss you" campaign |
| Due Soon | `DUE_SOON` | Days since last order ≥ (avg cycle × 0.8) | Time-sensitive offer window; next purchase expected in ~5–14 days |
| On Track | `ON_TRACK` | Days since last order < (avg cycle × 0.8) | Normal engagement; avoid re-engagement fatigue |
| (NULL) | — | 1-time buyer or no pattern | Use `lifecycle_stage` instead |

**Logic:**
```sql
CASE
    WHEN avg_days_between_orders IS NULL OR frequency <= 1 THEN NULL
    WHEN recency_days >= avg_days_between_orders * 1.5 THEN 'OVERDUE'
    WHEN recency_days >= avg_days_between_orders * 0.8 THEN 'DUE_SOON'
    ELSE 'ON_TRACK'
END
```

**How it updates:** Daily as time passes and based on order history patterns.

**Staff cannot override** — computed from recency and purchase cycle.

**Example:**
- Customer's average cycle: 45 days between orders
  - Last order 70 days ago: 70 ≥ (45 × 1.5=67.5) → `OVERDUE`
  - Last order 40 days ago: 40 ≥ (45 × 0.8=36) → `DUE_SOON`
  - Last order 20 days ago: 20 < 36 → `ON_TRACK`

**Note:** **1-time buyers return NULL.** Use `lifecycle_stage=LIFECYCLE_NEW` to identify true new customers vs. one-time buyers.

---

## PART 4: The customer_type × value_group Matrix

Staff decides **customer_type**; pipeline derives **value_group**. Combined, they create actionable segments:

```
┌─────────────────────┬──────────────────┬──────────────┬──────────────┐
│ Customer Type       │ VALUE_VIP        │ VALUE_GOLD   │ VALUE_SILVER │
├─────────────────────┼──────────────────┼──────────────┼──────────────┤
│ RETAIL              │ VIP retail buyer │ Gold retail  │ Silver cust  │
│ (Default, B2C)      │ (50M+ spend)     │ (20–50M)     │ (5–20M)      │
│                     │ → Premium service│ → Loyalty    │ → Standard   │
├─────────────────────┼──────────────────┼──────────────┼──────────────┤
│ WHOLESALE           │ Major distributor│ Mid-tier dist│ Small new    │
│ (Manual, B2B)       │ (50M+)           │ (20–50M)     │ dist (5–20M) │
│                     │ → Custom terms   │ → Tier 2 disc│ → Onboarding │
├─────────────────────┼──────────────────┼──────────────┼──────────────┤
│ PARTNER             │ Strategic CTV    │ Growing CTV  │ New CTV      │
│ (Manual, Affiliate) │ (50M+)           │ (20–50M)     │ (5–20M)      │
│                     │ → Co-marketing   │ → Support    │ → Nurture    │
├─────────────────────┼──────────────────┼──────────────┼──────────────┤
│ STAFF               │ Long-tenured emp │ Regular emp  │ New staff    │
│ (Manual)            │ (50M+)           │ (20–50M)     │ (5–20M)      │
│                     │ → Max discount   │ → Emp disc   │ → Emp disc   │
├─────────────────────┼──────────────────┼──────────────┼──────────────┤
│ KOL                 │ Top influencer   │ Growing infl │ New infl     │
│ (Manual)            │ (50M+)           │ (20–50M)     │ (5–20M)      │
│                     │ → Co-brand       │ → Support    │ → Trial      │
└─────────────────────┴──────────────────┴──────────────┴──────────────┘

VALUE_BRONZE = Spend < 5M (all types)
```

**Key rule:** customer_type is FIXED (set by staff); value_group **changes as spend accumulates**.

---

## PART 5: Staff Workflow — How to Classify a Customer

### Workflow for Creating a New Customer in Sapo

**Step 1: Set customer_type (Choose ONE)**

When creating customer in Sapo, find the **Group/Tag** field and select:
- [ ] `TYPE_RETAIL` (default — leave blank if regular customer)
- [ ] `TYPE_WHOLESALE` — requires Sales approval; customer must have wholesale agreement
- [ ] `TYPE_PARTNER` — for affiliates, CTVs, small distributors
- [ ] `TYPE_STAFF` — only for employees (HR owns)
- [ ] `TYPE_KOL` — for influencers (Marketing owns)

**Decision tree:**
```
Is the customer an employee? → YES → STAFF
Is the customer a KOL/influencer? → YES → KOL
Does the customer have a bulk purchase agreement? → YES → WHOLESALE/PARTNER
Does the customer buy via B2C channels? → YES → RETAIL (default)
```

**Step 2: acquisition_source (When Ready)**

Not yet available in Sapo. **Optional for now:**
- Start tracking in spreadsheet parallel to Sapo
- Can tag: `SOURCE_ORGANIC`, `SOURCE_ADS`, `SOURCE_REFERRAL`, `SOURCE_KOL`, `SOURCE_EVENT`
- Data team will sync when Sapo integration complete

**Step 3: Pipeline Auto-Assigns**

After first order (or when pipeline runs):
- [ ] value_group → Auto (based on lifetime spend)
- [ ] lifecycle_stage → Auto (based on order recency)
- [ ] channel_preference → Auto (based on preferred sales channel)
- [ ] product_affinity → Auto (based on brand spending)
- [ ] payment_behavior → Auto (based on payment method)
- [ ] geo_region → Auto (based on address province)
- [ ] discount_sensitivity → Auto (based on discount order rate)
- [ ] next_purchase_signal → Auto (based on personal purchase cycle)

### Workflow for Updating Existing Customer

**When to update customer_type:**
- Customer converts from RETAIL → WHOLESALE (signed distributor agreement)
- Employee leaves company → remove STAFF tag, revert to actual type (RETAIL or other)
- KOL partnership ends → remove KOL tag

**When NOT to touch auto-dimensions:**
- DO NOT manually edit value_group, lifecycle_stage, channel_preference, etc.
- Pipeline updates these automatically; manual edits will be overwritten
- If you see an incorrect value, contact Data team (likely a data quality issue to fix upstream)

---

## PART 6: Common Misunderstandings & Clarifications

### Misconception 1: "VIP is a customer_type"
**Wrong.** VIP is a **value_group** (VALUE_VIP tier), not a type.
- **Example:** A RETAIL customer who spends 50M is `customer_type=RETAIL, value_group=VALUE_VIP`
- **Not:** `customer_type=VIP`

### Misconception 2: "I can change value_group manually to make customer VIP"
**Wrong.** value_group is **auto-computed** from lifetime spend. You cannot (and should not) edit it manually.
- If a customer is misclassified, the issue is upstream data quality (e.g., orders not recorded, customer merge issues)
- Contact Data team to investigate and fix

### Misconception 3: "A WHOLESALE customer's 40% discount is a promotion"
**Wrong.** Wholesale discount is **pricing policy**, not promotion.
- When analyzing "promotion effectiveness," FILTER OUT wholesale customers: `WHERE customer_type = 'RETAIL'`
- Otherwise, your promotion ROI will be 40% artificially lower due to policy discount mixing with actual promotions

### Misconception 4: "acquisition_source is working"
**Wrong (for now).** `acquisition_source` is currently **always NULL**. It's on the roadmap but not yet integrated with Sapo.
- Don't rely on it for reporting yet
- Start manual tracking if needed for marketing ROI analysis

### Misconception 5: "next_purchase_signal tells me when the customer WILL buy"
**Partial.** It predicts based on **historical cycle** — assumes steady purchase rhythm.
- **Accurate for:** Repeat customers with stable buying patterns
- **Inaccurate for:** Seasonal products, sporadic buyers, 1-time customers (returns NULL)
- **Use with:** `predicted_next_purchase_date` (next purchase day estimate) for context

### Misconception 6: "All auto-dimensions update in real-time"
**Wrong.** Pipeline runs **daily**. Updates may lag 24–48 hours behind actual Sapo changes.
- If a customer just received an order, their metrics (value_group, lifecycle_stage, etc.) will update in tomorrow's run
- Check data freshness timestamp: `metric_calculated_at` in dim_customers

---

## PART 7: Technical Reference — Data Flow

### Where Classification Values Come From (Complete Chain)

```
Sapo (Customer Master)
  ↓
  ├─ customer_group (raw tag) → stg_sapo_customers_v2
  │                          → std_customers (rename to customer_group)
  │                          → dim_customers_base (preserve group)
  │                          → dim_customers (derive customer_type via regex)
  │
  └─ (other fields: name, email, province, etc.)
     ↓
     dim_customers_base
     ↓
     fact_orders (links orders to customer_key)
     ↓
     int_customer_metrics (aggregates orders to RFM + P2/P3 metrics)
     ↓
     dim_customers (final: joins base + metrics, computes auto-dimensions)
```

### Exact Logic Reference (for Data Team)

**customer_type derivation (dim_customers.sql:93–101):**
```sql
CASE
    WHEN customer_group LIKE '%TYPE_WHOLESALE%' THEN 'WHOLESALE'
    WHEN customer_group LIKE '%TYPE_PARTNER%' THEN 'PARTNER'
    WHEN customer_group LIKE '%TYPE_STAFF%' THEN 'STAFF'
    WHEN customer_group LIKE '%TYPE_KOL%' THEN 'KOL'
    ELSE 'RETAIL'
END as customer_type
```

**value_group derivation (dim_customers.sql:103–109):**
```sql
CASE
    WHEN monetary_value >= 50000000 OR frequency >= 20 THEN 'VALUE_VIP'
    WHEN monetary_value >= 20000000 THEN 'VALUE_GOLD'
    WHEN monetary_value >= 5000000 THEN 'VALUE_SILVER'
    ELSE 'VALUE_BRONZE'
END as value_group
```

---

## PART 8: Unresolved Questions & Open Items

### For Data Team:
1. **acquisition_source Sapo field** — What is the planned Sapo field name for tracking acquisition source? Is there a custom field we should use now?
2. **Credit limit tracking** — Payment_behavior currently doesn't track PAYMENT_CREDIT (credit term customers). When will this be implemented?
3. **Address province normalization** — Are there edge cases in province spelling causing misclassification to GEO_OTHER? (Checked: code has ~50 province variants, but live data may have typos)
4. **Multi-channel vs. primary channel** — Should channel_preference represent primary channel OR allow multi-channel tags in future?

### For Business Teams:
1. **Wholesale conversion workflow** — Should Sales team have a form/approval process for RETAIL → WHOLESALE conversions, or is it ad-hoc?
2. **KOL + SOURCE_KOL clarity** — How should Marketing distinguish between `customer_type=KOL` (the creator) vs. `acquisition_source=SOURCE_KOL` (customer came via the creator)?
3. **PARTNER vs. WHOLESALE distinction** — What's the operational difference? When should Sales choose PARTNER over WHOLESALE?
4. **Value tier thresholds** — Are the 5M, 20M, 50M thresholds still correct for 2026? Should they be inflation-adjusted?
5. **Geographic regions** — Are the 5 geo regions still strategic for operations/logistics, or should we add/remove regions?

### For All Teams:
1. **DIM_CUSTOMERS serving layer** — Is dim_customers exposed in Metabase/BI for staff self-service reporting, or does data team run queries on demand?
2. **Update frequency SLA** — What's the expectation for how fresh customer classification should be? (Currently daily batch)

---

## PART 9: Key Documents & Links

For more detail, see:
- **Full segmentation model:** `docs/context/customer-segmentation.md` (Vietnamese, 8-dimension framework)
- **Analytics domain spec:** `docs/analytics-handbook/domains/customer.md` (metric definitions, scope, logic)
- **dbt models:**
  - `transformation/models/marts/core/dim_customers.sql` (final dimensions, includes all logic)
  - `transformation/models/marts/core/intermediate/int_customer_metrics.sql` (RFM + P3 metrics calculation)
  - `transformation/models/staging/std_customers.sql` (Sapo source → standard mapping)
  - `transformation/models/staging/src_sapo_customers_v2.sql` (raw Sapo extraction + JSON parsing)

---

## APPENDIX A: Example Customer Profiles

### Customer 1: Lê Thị Hương (Retail, High-Value)
```
customer_type:       RETAIL (set by Sales, default)
value_group:         VALUE_VIP (auto: 55M lifetime spend)
lifecycle_stage:     LIFECYCLE_ACTIVE (auto: bought 20 days ago)
channel_preference:  CHANNEL_SOCIAL (auto: 8 Zalo orders > 3 Web > 1 Shopee)
product_affinity:    PRODUCT_FINE_JAPAN (auto: 70% of revenue)
payment_behavior:    PAYMENT_PREPAID (auto: 0% COD)
geo_region:          GEO_HCMC (auto: address = "TP. Hồ Chí Minh")
discount_sensitivity: FULL_PRICE (auto: 15% discount order rate)
next_purchase_signal: ON_TRACK (auto: 45-day cycle, last 25 days)
```
**Action:** High-priority for VIP service; protect margins (no discount needed).

### Customer 2: Công ty ABC Trading (Wholesale)
```
customer_type:       WHOLESALE (set by Sales, signed agreement)
value_group:         VALUE_GOLD (auto: 35M lifetime spend)
lifecycle_stage:     LIFECYCLE_ACTIVE (auto: bulk order 30 days ago)
channel_preference:  CHANNEL_DIRECT (auto: all orders via B2B portal)
product_affinity:    PRODUCT_MULTI (auto: 40% Fine Japan, 35% FG Care)
payment_behavior:    PAYMENT_COD (auto: 100% orders via bank transfer... wait, this should be PREPAID)
geo_region:          GEO_HANOI (auto: delivery address in Hà Nội)
discount_sensitivity: PROMO_DEPENDENT (auto: 80% discounted orders)
next_purchase_signal: DUE_SOON (auto: 60-day cycle, last 50 days)
```
**Action:** Standard wholesale terms apply (40-50% fixed discount NOT counted as promotion). Watch for overdue status.

### Customer 3: Nguyễn Văn Tâm (KOL, New)
```
customer_type:       KOL (set by Marketing)
value_group:         VALUE_BRONZE (auto: 2M lifetime spend, new KOL)
lifecycle_stage:     LIFECYCLE_NEW (auto: first order 15 days ago, 1 order)
channel_preference:  CHANNEL_SOCIAL (auto: only Zalo orders)
product_affinity:    PRODUCT_FINE_CARE (auto: 100% Fine Care orders)
payment_behavior:    PAYMENT_PREPAID (auto: all prepaid)
geo_region:          GEO_MEKONG (auto: Cần Thơ address)
discount_sensitivity: NULL (only 1 order, not enough pattern yet)
next_purchase_signal: NULL (only 1 order, no cycle yet)
```
**Action:** Nurture with co-marketing support; expect value to grow as content influences followers.

---

**Report prepared by:** Data Team  
**Effective date:** 2026-06-05  
**Last updated:** 2026-06-05  
**Next review:** 2026-08-01
