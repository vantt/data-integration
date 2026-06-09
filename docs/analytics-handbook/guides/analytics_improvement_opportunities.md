# Analytics Improvement Opportunities

> Last reviewed: 2026-06-09
> Scope: `docs/analytics-handbook/playbooks/`, `docs/analytics-handbook/blueprints/`, and related domain definitions.

This document reviews the current analytics handbook from a business-action perspective. It is not a new dashboard specification. It is a map of where the current reporting system creates the most business leverage, where reports are already strong, where they still stop too early, and what additional data would unlock the next level of insight.

The short version: the handbook already covers the right operating areas, but many reports still answer "what happened?" better than "what should we do next, who owns it, and how much value is at stake?". The highest-value improvement is to connect revenue, cost, margin, customer, campaign, and operations into decision queues.

## 1. Important Perspectives

### 1. Profitability and Unit Economics

This is the most important perspective because it controls whether growth is actually valuable. Revenue dashboards show size and momentum, but profitability views show which channels, products, orders, and promotions are creating or destroying value.

Important reports:

- [Finance P&L Dashboard](../playbooks/finance_pl.md)
- [Channel Profitability Monthly](../playbooks/channel_profitability_monthly.md)
- [Shopee Channel Economics](../playbooks/shopee_channel_economics.md)
- [Order Profitability](../blueprints/order_profitability.md)
- [Product Profitability](../blueprints/product_profitability.md)
- [Product Performance](../playbooks/product_performance.md)

Important questions:

- How much profit remains after COGS and Shopee/platform fees?
- Which channel has high revenue but low margin?
- Which products generate the most absolute profit, not just revenue?
- Which products or orders have low or negative margin?
- Is Shopee still worth pushing after settlement fees, vouchers, taxes, and operational cost?
- How much margin can be recovered by changing price, product mix, or promotion policy?

Important metrics:

- Net Revenue
- COGS
- Gross Profit
- Gross Margin %
- Channel Net Profit
- Channel Net Margin %
- Shopee Settlement Margin %
- Platform Fee Rate %
- Low-Margin Products
- Orders with COGS / COGS Coverage %
- Product Gross Profit
- Product Margin %

Current strength: the handbook already has a strong margin foundation using `int_misa_sales_lines`, `int_shopee_order_fees`, and `fact_order_economics`.

Main improvement opportunity: move from margin reporting to margin recovery. The reports should rank the biggest recoverable leaks in VND, not only show rates. A 5-point margin drop on a large channel matters more than a 30-point margin issue on a tiny product.

Recommended additions:

- Add a "Margin Leakage Queue" across channel, product, and order:
  - Dimension: channel, product, order, promotion.
  - Issue: low margin, high fee, high discount, missing COGS, negative profit.
  - Estimated value at stake: revenue multiplied by margin gap to target.
  - Owner: Finance, Sales Director, Marketing, Merchandising.
  - Action: reprice, reduce discount, change channel push, review supplier cost, audit order.
- Add COGS coverage to all profitability reports. Margin cards should not be trusted if only part of orders have COGS.
- Add drill path: Finance P&L -> Channel Profitability -> Order Profitability -> Order Detail.
- Add a clear distinction between gross margin, channel net margin, and full company net margin. The current system does not yet support full net margin because GL expense data is missing.

### 2. Executive Target and Revenue Steering

This perspective is the main steering wheel for leadership. It decides whether the company needs to accelerate demand, protect margin, reduce discounting, or fix operational problems.

Important reports:

- [CEO Weekly Pulse](../playbooks/ceo_weekly_pulse.md)
- [CEO Monthly Scorecard](../playbooks/ceo_monthly_scorecard.md)
- [Sales Monthly Business Review](../playbooks/sales_monthly_review.md)
- [Rill Orders Executive](../playbooks/rill/orders_executive.md)

Important questions:

- Are we on track against monthly target?
- Is revenue growth driven by orders, AOV, channel mix, or discounting?
- Which channel is driving the change?
- Are customer health and operational flags supporting or weakening growth?
- What needs to change next week or next month?

Important metrics:

- Net Revenue
- Gross Revenue
- Total Orders
- AOV
- Target Achievement Rate
- Variance to Target
- Pace Index
- Channel Mix
- New Customers
- Returning Revenue %
- Discount Rate
- Return Count
- Cancelled Orders

Current strength: CEO weekly and monthly reports have the right scanning pattern: hero KPI, target progress, channel/customer context, and red flags.

Main improvement opportunity: add a real variance bridge. "Behind target" is useful, but the next question is why. The executive reports should decompose the gap into volume, AOV, channel mix, discount, return/cancel, and customer mix.

Recommended additions:

- Add "Target Gap Bridge":
  - Target Revenue
  - Actual Revenue
  - Order Volume Impact
  - AOV Impact
  - Discount Impact
  - Return/Cancel Impact
  - Channel Mix Impact
- Add "Top 5 Decisions This Week" as a table, not a chart:
  - Signal
  - Why it matters
  - Owner
  - Suggested action
  - Related dashboard link
- Add an executive drill-through path into the deeper reports instead of duplicating every metric in the CEO dashboard.

### 3. Marketing ROI and Promotion Efficiency

This perspective is high leverage because it controls customer acquisition, channel spend, promotion policy, and discount discipline.

Important reports:

- [Marketing Weekly Tracker](../playbooks/marketing_weekly_tracker.md)
- [Marketing Monthly Analysis](../playbooks/marketing_monthly_analysis.md)
- [Marketing ROI](../blueprints/marketing_roi.md)
- [Sales Promotion & Discount Analysis](../playbooks/sales_promotion_analysis.md)

Important questions:

- Which channels acquire new customers efficiently?
- Are promotions increasing valuable demand, or just subsidizing orders that would have happened anyway?
- Is discount rate eating margin?
- Which promotion is overused, low-AOV, or margin destructive?
- Which brand/product/channel combination deserves more marketing push?

Important metrics:

- Marketing Spend
- Revenue from Spend Channels
- Blended ROAS
- ROAS by Channel
- New Customers
- New Customer Revenue
- New Customer Share %
- Discount Rate %
- Discounted Orders %
- Average Discount Depth
- Promo Revenue
- Promo Usage Count
- Promo vs Non-Promo AOV
- Cohort Retention

Current strength: weekly and monthly marketing views already cover channel, customers, promotions, products, and geography. The ROI blueprint introduces spend, ROAS, CPC, and CPM.

Main improvement opportunity: ROAS based only on revenue can be misleading. The next step is contribution view: revenue after discount, COGS, platform fees, and spend.

Recommended additions:

- Add "Contribution ROAS" where possible:
  - Revenue
  - Discount
  - COGS
  - Platform fees
  - Marketing spend
  - Contribution profit
- Add "Promo Quality Matrix":
  - High revenue, high margin: scale.
  - High revenue, low margin: reprice/restrict.
  - Low revenue, high usage: stop or retarget.
  - Low usage, high discount: audit.
- Add cohort quality by acquisition channel:
  - First order AOV
  - 30-day repeat rate
  - 60-day repeat rate
  - LTV after first purchase
- Add clear action thresholds for marketing budget reallocation.

### 4. Customer Retention and Value Concentration

This perspective is important because revenue quality depends on repeat customers and high-value segments. It also creates concrete actions: outreach, reactivation, VIP offers, and churn prevention.

Important reports:

- [Customer Operational Dashboard](../playbooks/customer_operational_dashboard.md)
- [Customer Retention & Lifecycle](../playbooks/customer_retention.md)
- [Customer Intelligence Monthly](../playbooks/customer_intelligence_monthly.md)
- [Customer Retention Dashboard](../blueprints/customer_retention_dashboard.md)

Important questions:

- Is the customer base getting healthier or weaker?
- Which high-value customers are at risk?
- Which cohorts are retaining worse than expected?
- Are new customers becoming repeat customers?
- Which products and channels attract valuable customers?

Important metrics:

- MAU
- Active Customers
- New Customers
- Repeat Purchase Rate
- Churn Rate
- At-Risk Customers
- One-Time Buyer Rate
- Customer LTV
- Avg LTV per Customer
- Revenue from Top 20% Customers
- Segment Revenue Share
- Cohort Retention
- Avg Days Between Purchases
- Reactivated Customers

Current strength: the handbook has a good distinction between daily customer operations and monthly customer intelligence.

Main improvement opportunity: convert customer insight into prioritized action lists. The current reports describe customer health, but the highest business value comes from ranked outreach opportunities.

Recommended additions:

- Add "Revenue at Risk":
  - At-risk customers multiplied by trailing customer value.
  - Split by VIP/GOLD/SILVER/BRONZE.
- Add "Next Best Action" lists:
  - VIP at risk: direct call.
  - High-LTV churned: win-back offer.
  - One-time high-AOV buyers: second-purchase campaign.
  - New customers with product affinity: targeted bundle.
- Add "Campaign Timing Signal":
  - Use days-between-purchases distribution to recommend when to nudge.
- Add "Retention ROI":
  - Reactivated revenue minus campaign cost, when campaign cost data is available.

### 5. Daily Sales Operations and Reconciliation

This perspective is operationally important because it detects anomalies while they can still be fixed. It protects revenue, payment reconciliation, and data trust.

Important reports:

- [Daily Sales Operations](../playbooks/sales_daily_operation.md)
- [Daily Sales Operations](../playbooks/sales_daily_retail.md)
- [Orders List Reconciliation](../playbooks/orders_list_reconciliation.md)
- [Order Listing](../blueprints/order_listing.md)
- [Order Detail](../blueprints/order_detail.md)
- [Sales Ops Weekly Review](../playbooks/sales_ops_weekly_review.md)
- [Sales Ops Monthly Summary](../playbooks/sales_ops_monthly_summary.md)

Important questions:

- Is today's revenue, order volume, and AOV normal?
- Are there abnormal cancellations, returns, discounts, or unpaid completed orders?
- Does BI match Sapo?
- Which channels or branches need attention?
- Which orders need immediate investigation?

Important metrics:

- Health Score
- Net Revenue
- Total Orders
- AOV
- Total Collected
- Returns
- Discount Rate
- Items per Order
- Hourly Sales Trend
- Cumulative Revenue
- Orders by Status
- Payment Status
- Flagged Orders
- Data Freshness

Current strength: order reconciliation has a strong workflow and explicitly prioritizes freshness, count match, revenue match, status distribution, and flagged orders.

Main improvement opportunity: consolidate the daily workflow. Daily Sales, Yesterday's Sales, Order Listing, and Order Detail should feel like one operating loop: detect, diagnose, assign, resolve.

Recommended additions:

- Add a single "Action Queue" to daily operations:
  - Completed but unpaid.
  - Negative revenue.
  - Discount greater than gross.
  - 100% discount.
  - OPEN order older than threshold.
  - Channel missing relative to normal pattern.
- Add severity scoring:
  - Financial impact.
  - Age.
  - Customer value.
  - Repeat occurrence.
- Add links from flagged order rows to Order Detail.
- Add freshness and source coverage mini-cards on every operational dashboard.

### 6. B2B Credit and Partner Operations

This perspective is high-value because B2B orders often have larger AOV, longer cycles, and payment risk. It is not just sales reporting; it is credit and relationship management.

Important reports:

- [Rill Orders B2B Operations](../playbooks/rill/orders_b2b_ops.md)
- [B2B Daily Sales](../blueprints/b2b_sales_daily.md)
- [B2B Orders Tracking](../blueprints/b2b_orders_tracking.md)

Important questions:

- Which B2B customers are driving revenue?
- Which customers have unpaid or partial-payment orders?
- How old is the outstanding balance?
- Which B2B orders are waiting for fulfillment?
- Which partner needs follow-up today?

Important metrics:

- B2B Revenue
- B2B Orders
- B2B AOV
- Unique B2B Customers
- Outstanding Amount
- Unpaid Orders Count
- Partial Payment Orders
- Avg Days Outstanding
- Aging Bucket
- Pending Fulfillment
- Pending B2B Orders

Current strength: B2B blueprints are concrete and action-oriented, especially the aging and outstanding customer lists.

Main improvement opportunity: make this a credit-risk dashboard, not only an unpaid-orders dashboard.

Recommended additions:

- Add credit terms per customer:
  - Payment due date.
  - Credit limit.
  - Approved outstanding limit.
  - Overdue amount.
- Add "Collections Priority Queue":
  - Customer.
  - Outstanding amount.
  - Days overdue.
  - Last order date.
  - Recent payment behavior.
  - Suggested follow-up action.
- Add fulfillment SLA specific to B2B, because B2B cycle expectations differ from retail.

### 7. Product, Assortment, and Inventory

This perspective is medium-high today and would become very high after inventory data is added. Product revenue and margin are available, but inventory decisions need stock data.

Important reports:

- [Product Performance](../playbooks/product_performance.md)
- [Product Profitability](../blueprints/product_profitability.md)
- [Sales Items Product Rill Explore](../blueprints/rill/sales_items_product.yaml)
- [Inventory Health](../playbooks/product_inventory.md)

Important questions:

- Which products drive revenue and profit?
- Which products have high sales velocity but low margin?
- Which products are declining and need intervention?
- Which products should be pushed, repriced, bundled, or cleared?
- Which products are out of stock or at risk of stockout?

Important metrics:

- Product Revenue
- Units Sold
- Daily Velocity
- Gross Profit
- Product Margin %
- Top Products by Profit
- Low-Margin Products
- Category Mix Trend
- Category Growth MoM
- Inventory Turnover
- Days of Supply
- OOS Rate
- Slow-Moving Stock

Current strength: product sales and margin analysis are available through `fact_sales` and `int_misa_sales_lines`.

Main improvement opportunity: product action requires inventory. Without stock, the system cannot distinguish demand decline from stockout, or slow demand from overstock.

Recommended additions:

- Add product action classification:
  - High velocity, high margin, low stock: reorder/protect.
  - High velocity, low margin: reprice or supplier review.
  - Low velocity, high stock: clearance/bundle.
  - High traffic/new customers, low repeat: review product quality.
- Add inventory snapshots before building stock metrics.
- Add product lifecycle state: new launch, active, seasonal, clearance, discontinued.

### 8. Logistics and Fulfillment

This perspective matters because slow fulfillment hurts customer experience, creates cancellations/returns, and reduces repeat purchase. Current reports can monitor order processing, but not full delivery performance.

Important reports:

- [Logistics Operations Center](../playbooks/logistics_operations.md)
- [Logistics Domain](../domains/logistics.md)
- [Shipping & Returns](../playbooks/logistics_shipping.md)

Important questions:

- Are orders stuck in processing?
- Are same-day ship and first-ship speed healthy?
- Which staff or branch has bottlenecks?
- Which orders need escalation now?
- Which carrier or delivery route is causing delays?

Important metrics:

- Fulfillment Rate
- Total Orders Today
- Shipped Orders
- Avg Time to Complete
- Avg Hours to First Ship
- Same-Day Ship Rate
- Orders Pending > 24h
- Stuck Orders Detail
- Staff Orders Processed
- Staff Avg Processing Time

Current strength: the available logistics view is practical for order processing and stuck-order escalation.

Main improvement opportunity: split internal processing from external delivery. The current system can measure created-to-shipped reasonably, but it cannot fully measure carrier performance or customer receipt.

Recommended additions:

- Add SLA by channel/order type.
- Add oldest-stuck queue with owner and age.
- Add customer impact estimate for stuck orders:
  - Customer value group.
  - Order amount.
  - Days delayed.
  - Repeat customer flag.
- Add carrier and delivery data when available.

### 9. Social Commerce and CS Productivity

This perspective has large potential but is currently under-instrumented. Sales by staff is useful, but it does not yet measure the chat-to-order funnel.

Important reports:

- [Social Commerce Operations](../playbooks/customer_support_social_commerce.md)
- [Customer Support Domain](../domains/customer_support.md)
- Social sections in [Sales Ops Weekly Review](../playbooks/sales_ops_weekly_review.md) and [Sales Ops Monthly Summary](../playbooks/sales_ops_monthly_summary.md)

Important questions:

- Are Facebook and Zalo converting today?
- Which agent drives orders and revenue?
- Is low sales caused by low traffic or low conversion?
- Are response times hurting conversion?
- Which agent needs coaching?

Important metrics:

- Social Revenue
- Social Orders
- Social AOV
- Revenue by Channel
- Top Sales Agents
- Orders by Agent
- First Response Time
- Average Handling Time
- Chat-to-Order Conversion Rate

Current strength: social revenue and order contribution by channel/staff are available.

Main improvement opportunity: add traffic and conversation data. Without inbound message volume and response behavior, the team cannot tell whether a bad day is a demand problem, a staffing problem, or a conversion problem.

Recommended additions:

- Add chat funnel:
  - Inbound conversations.
  - First reply within SLA.
  - Qualified conversations.
  - Orders created.
  - Revenue.
  - Conversion rate.
- Add agent performance with fairness controls:
  - Assigned conversations.
  - Response time.
  - Conversion rate.
  - Revenue per conversation.
  - AOV.
- Add missed opportunity queue:
  - High-intent chats without order.
  - Slow first response.
  - Repeated abandoned inquiries.

### 10. Data Trust and Observability

This perspective does not directly increase revenue, but every business report depends on it. If data is stale or incomplete, the organization may make wrong decisions faster.

Important reports:

- [Ingestion Health Monitor](../playbooks/ingestion_health.md)
- [Ingestion Health Blueprint](../blueprints/ingestion_health.md)
- [Orders List Reconciliation](../playbooks/orders_list_reconciliation.md)

Important questions:

- Did every source move data today?
- Is data fresh enough for the report being read?
- Is source volume sane?
- Is there drift between source and destination?
- Which asset failed or skipped?

Important metrics:

- Ingestion Freshness
- Ingestion Volume
- SLA Conformance
- Recon Drift
- Run Success Rate
- Failed/Skipped Runs
- Source Count vs Destination Count

Current strength: the ingestion health playbook is clear about trust engineering and daily operator use.

Main improvement opportunity: surface trust signals inside business dashboards, not only in the data engineering dashboard.

Recommended additions:

- Add a small "Data Freshness / Coverage" block to executive, finance, daily ops, and marketing dashboards.
- Add report-specific freshness, not only global freshness.
- Add "data not reliable" visual state for dashboards with stale dependencies.

## 2. Current Issues and Recommended Fixes

### Issue 1: Reports often stop at diagnosis instead of action

Current state: many playbooks define good metrics and thresholds, but the final action is often described in prose. That makes the user interpret the dashboard manually.

Better state: every high-value dashboard should include an action table. The table should be sorted by value at stake or urgency.

Recommended pattern:

| Field | Purpose |
|---|---|
| Signal | What happened |
| Severity | How urgent it is |
| Value at Stake | Estimated VND impact |
| Suspected Cause | First likely explanation |
| Owner | Team responsible |
| Suggested Action | What to do next |
| Drill Link | Where to investigate |

Best candidates:

- Finance P&L
- Channel Profitability
- Shopee Channel Economics
- Sales Promotion Analysis
- Customer Retention
- Orders List Reconciliation
- B2B Orders Tracking
- Logistics Operations

### Issue 2: Profitability is fragmented across several reports

Current state: Finance P&L, Channel Profitability, Shopee Economics, Order Profitability, and Product Profitability are separate. Each is useful, but the user must connect the story manually.

Better state: define one margin investigation path:

1. Company margin changed.
2. Which channel caused it?
3. Was it COGS, discount, Shopee/platform fees, or product mix?
4. Which products/orders explain the change?
5. What action recovers the most VND?

Recommended changes:

- Add cross-links between profitability dashboards.
- Add COGS coverage to the top of every margin report.
- Add a common margin taxonomy:
  - Gross Revenue
  - Net Revenue
  - COGS
  - Gross Profit
  - Platform Fees
  - Channel Net Profit
  - Operating Expenses
  - Net Profit
- Keep full net profit marked as unavailable until `fact_gl_entries` exists.

### Issue 3: Collection governance and naming are inconsistent

Current state: `collection_registry.yml` defines three top-level collections: `Executive`, `Marketing & Customers`, and `Operations`. Several reports use paths outside this registry, including `Product Analytics`, `Logistics`, `Customer Support`, `Sales Analytics`, `Operations > B2B Operations`, `Operations > CrossBorder Operations`, `Operations > Retail Operations`, and `Operations > Order Management`.

Better state: either update the registry intentionally or move dashboards into the existing three-collection structure.

Recommended changes:

- Decide whether B2B and CrossBorder deserve new registered sub-collections.
- Move `Product Analytics` style reports under `Executive` or `Operations > Periodic Reviews`, depending on audience.
- Move `Customer Support` under `Operations` unless a separate top-level collection is intentionally added.
- Keep collection paths identical between playbook and blueprint.

### Issue 4: Playbook and blueprint filenames do not always align

Current state: some playbooks do not have same-name blueprints, and some blueprints do not have same-name playbooks. This breaks the handbook rule and makes ownership harder.

Observed playbooks without same-name blueprint:

- `customer_retention`
- `finance_cashflow`
- `logistics_shipping`
- `order_detail_view`
- `orders_list_reconciliation`
- `product_inventory`

Observed blueprints without same-name playbook:

- `b2b_orders_tracking`
- `b2b_sales_daily`
- `customer_retention_dashboard`
- `marketing_roi`
- `order_detail`
- `order_listing`
- `order_profitability`
- `order_profitability_all`
- `product_profitability`
- `rill/sales_items_product`
- `us_crossborder_operations`

Recommended changes:

- For each deployed blueprint, create or rename the corresponding playbook.
- For each planned playbook, mark it explicitly as planned if no blueprint exists.
- Use the same filename unless there is a documented exception.

### Issue 5: Scope separation needs to be more visible

Current state: the handbook has a good 3-layer scope architecture, but users can still misread dashboards if `[All]`, `[Retail]`, `[B2B]`, and `[US]` are not prominent.

Better state: every dashboard title, first text block, and key metric should make scope obvious.

Recommended changes:

- Add scope badges in dashboard headings:
  - `[All]` for executive sales.
  - `[Retail]` for promotion/discount/customer acquisition.
  - `[B2B]` for wholesale/partner operations.
  - `[US]` for CrossBorder operations.
- Never mix retail discount/promotion metrics with B2B pricing.
- Keep B2B credit and retail promotion reports separate.

### Issue 6: Some reports need trust indicators

Current state: Orders List Reconciliation and Ingestion Health are strong on freshness. Other business dashboards may not show whether source data is fresh or complete.

Better state: business users should see whether the report is safe to act on.

Recommended changes:

- Add a compact trust block to key reports:
  - Last order update.
  - Last MISA update.
  - Last Shopee payout update.
  - COGS coverage.
  - Source completeness warning.
- For profitability, always show COGS coverage and Shopee payout lag.
- For daily operations, always show order freshness.

### Issue 7: Thresholds are present but not always calibrated

Current state: many thresholds exist, for example discount > 15%, margin < 25%, pending payment > 5%, fulfillment < 85%. These are useful but may be generic.

Better state: combine business thresholds with historical baseline thresholds.

Recommended changes:

- Keep fixed thresholds for policy limits.
- Add historical anomaly detection for operational metrics:
  - Above/below 4-week same-day average.
  - Above/below rolling median.
  - Channel-specific baselines.
- Use different thresholds for Retail, B2B, and US where behavior differs.

## 3. Missing Data, Opportunities, and Readiness

### Full GL / Accounting Entries

Opportunity: build full company profitability instead of gross/channel profitability.

What this unlocks:

- Full P&L statement.
- Operating Margin %.
- Net Margin %.
- EBITDA.
- OpEx by category.
- Department/cost-center profitability.
- Accounting reconciliation between operational revenue and the general ledger.

Data needed:

- `fact_gl_entries` from accounting system.
- Chart of accounts.
- Debit/credit amount.
- Posting date.
- Voucher/document number.
- Account category mapping: revenue, COGS, OpEx, tax, interest, depreciation.
- Optional cost center, department, channel, branch.

System readiness: ❌ **Not ready** (2026-06-09). `fact_gl_entries` does not exist. Finance domain marks GL-based metrics as planned.

Recommended next step: define the GL extract contract and account mapping before building dashboards.

### Cash Flow and Liquidity

Opportunity: move from sales/payment reporting to treasury visibility.

What this unlocks:

- Cash balance.
- Daily cash movement.
- Cash inflow/outflow.
- DSO.
- Short-term liquidity monitoring.
- Cash forecast.

Data needed:

- Payment inflow/outflow classification.
- Bank/account balance snapshots.
- Accounts receivable and payable.
- Payment due dates.
- Bank transaction data or accounting cash ledger.

System readiness: ✅ **Partially done** (2026-06-09). `fact_payments` confirmed in production. Inflow/outflow classification and account balance snapshots still missing.

Recommended next step: enrich `fact_payments` with transaction type and account mapping, then add account balance snapshots.

### Inventory and Stock Health

Opportunity: turn product reports into merchandising and replenishment decisions.

What this unlocks:

- OOS rate.
- Days of supply.
- Inventory turnover.
- Sell-through rate.
- Dead stock.
- Reorder priority.
- Clearance candidates.
- Stockout impact on revenue.

Data needed:

- `fact_inventory` daily snapshot.
- SKU/variant stock quantity.
- Warehouse/branch location.
- Cost price.
- Received quantity.
- Stock adjustment.
- Optional purchase order and inbound shipment data.

System readiness: ✅ **Done** (2026-06-09). `fact_inventory_snapshot` and `mart_inventory_health` confirmed in production. OOS, days of supply, dead stock, and clearance candidate dashboards are now unblocked.

Recommended next step: start with daily inventory snapshot by SKU and branch. That is enough to unlock OOS, days of supply, and dead stock.

### Carrier, Shipment, and Delivery Data

Opportunity: measure end-to-end fulfillment, not just order processing.

What this unlocks:

- Carrier performance.
- Average delivery time.
- On-time delivery rate.
- Delivery failure rate.
- Delivery delay alerts.
- Delivery SLA by carrier/channel/region.

Data needed:

- `fact_shipments`.
- `dim_carriers`.
- Shipped timestamp.
- Delivered timestamp.
- Promised delivery date.
- Tracking number.
- Carrier status events.
- Return-to-sender events.

System readiness: ❌ **Not ready** (2026-06-09). `fact_shipments` does not exist. Internal `first_shipped_at` available on `fact_orders` but no carrier or delivery timestamp data.

Recommended next step: ingest shipment tracking events and normalize carrier names.

### Return Reasons and Product Quality

Opportunity: identify whether returns are caused by product quality, wrong description, shipping damage, or customer preference.

What this unlocks:

- Return reason ranking.
- Product quality issue detection.
- Content/product-page correction queue.
- Supplier escalation.
- Return-cost analysis.

Data needed:

- Return event table.
- Return reason.
- Returned quantity by line item.
- Refund amount.
- Return timestamp.
- Optional CS notes.

System readiness: ✅ **Partially done** (2026-06-09). `fact_order_returns` confirmed in production with `return_reason`, `return_status`, `refund_status`, `returned_at`, `channel_key` (10 rows, Jan–May 2026). Return reason ranking and product quality dashboards are now unblocked.

Recommended next step: define a returns model separate from orders if the source supports it.

### Social Commerce Conversation Data

Opportunity: move from social sales reporting to chat-to-order funnel optimization.

What this unlocks:

- Inbound message volume.
- First response time.
- Average handling time.
- Agent conversion rate.
- Missed opportunity detection.
- Staffing and coaching recommendations.

Data needed:

- Conversation ID.
- Channel: Facebook, Zalo.
- Customer ID or matched phone.
- Assigned agent.
- First customer message timestamp.
- First agent reply timestamp.
- Conversation status.
- Linked order ID.
- Message volume.

System readiness: ❌ **Not ready** (2026-06-09). No conversation data source connected. FRT and AHT data are missing.

Recommended next step: ingest conversation metadata first. Full message content is not required for the first useful version.

### Marketing Attribution and Campaign Detail

Opportunity: connect spend to customer quality, not just revenue.

What this unlocks:

- CAC by channel/campaign.
- Contribution ROAS.
- Payback period.
- First-order quality.
- Cohort retention by acquisition source.
- Budget reallocation recommendations.

Data needed:

- Campaign/adset/ad spend.
- Clicks, impressions.
- Channel mapping to order source.
- UTM or voucher attribution.
- First-order source on customer.
- Marketing spend by date/channel/campaign.

System readiness: ✅ **Partially done** (2026-06-09). `fact_marketing_spend` confirmed in production. Attribution quality and campaign-level joins still need validation before CAC and payback metrics are reliable.

Recommended next step: validate channel mapping and introduce campaign-level keys before building CAC and payback metrics.

### B2B Credit Terms

Opportunity: turn unpaid-order tracking into credit-risk management.

What this unlocks:

- Overdue amount.
- Credit exposure.
- DSO by customer.
- Collection priority.
- Hold/release recommendation for new B2B orders.

Data needed:

- Customer credit limit.
- Payment terms.
- Due date per invoice/order.
- Payment schedule.
- Partial payment allocation.
- Customer owner/sales rep.

System readiness: partially ready. Payment status and outstanding amount exist, but formal credit terms are missing.

Recommended next step: add payment terms and due dates to B2B customer/order models.

### Targets and Forecasting Inputs

Opportunity: make pace and target dashboards prescriptive.

What this unlocks:

- Forecasted month-end revenue.
- Required daily run-rate.
- Gap-to-target by channel/branch.
- Recommended acceleration amount.
- Target miss early warning.

Data needed:

- `fact_targets` by date, channel, branch, product category, or team.
- Calendar working days.
- Historical seasonality.
- Promotion calendar.
- Optional campaign calendar.

System readiness: partially ready. `fact_targets` exists in several playbooks, but target granularity should be validated.

Recommended next step: standardize target grain and add expected pace curves.

### Data Observability in Business Reports

Opportunity: prevent users from acting on stale or incomplete data.

What this unlocks:

- Confidence state per report.
- Report-specific freshness.
- Source coverage warnings.
- Faster root cause when dashboards look wrong.

Data needed:

- Ingestion run metadata.
- Source row counts.
- Destination row counts.
- Last successful load per source/model.
- SLA configuration.
- Reconciliation drift records.

System readiness: mostly ready. Ingestion Health already defines the core observability concepts.

Recommended next step: expose a lightweight trust summary inside business dashboards.

## 4. Recommended Roadmap

### Phase 1: Improve actionability without new data

This phase should be done first because it mostly reorganizes existing analytics.

- Add action queues to profitability, promotion, customer, B2B, logistics, and reconciliation reports.
- Add COGS coverage and data freshness blocks to key dashboards.
- Align playbook/blueprint filenames or mark planned artifacts explicitly.
- Fix collection paths against `collection_registry.yml`.
- Add scope badges to `[All]`, `[Retail]`, `[B2B]`, and `[US]` reports.
- Add drill-through links between summary dashboards and detail dashboards.

### Phase 2: Use existing data more deeply

This phase creates better insight from existing models.

- Build target gap bridge for CEO and Sales MBR.
- Build margin leakage queue using `fact_order_economics`.
- Build promo quality matrix using discount and revenue data.
- Build retention action list using `dim_customers` and `fact_orders`.
- Build B2B collections priority list from payment status and order age.
- Build product action classification using velocity and margin.

### Phase 3: Add new data sources

This phase unlocks currently impossible analysis.

- Add `fact_gl_entries` for full P&L and OpEx.
- Add inventory snapshots for OOS, days of supply, and dead stock.
- Add shipment/carrier events for delivery SLA and carrier performance.
- Add social conversation metadata for response-time and conversion funnel.
- Add campaign-level attribution for CAC, payback, and contribution ROAS.
- Add B2B credit terms for overdue and credit exposure.

## 5. Filename Recommendation

Recommended filename:

```text
docs/analytics-handbook/guides/analytics_improvement_opportunities.md
```

Reason: this is a cross-dashboard improvement guide. It is not owned by a single domain, not a playbook, and not a deployable blueprint. The name is broad enough to cover the current review and future iterations.
