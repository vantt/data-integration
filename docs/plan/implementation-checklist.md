# Metabase Implementation Checklist

## 📊 Must-Have Charts (Top 20)

_Status: [ ] Pending [/] In Progress [x] Complete_

### Sales & Revenue

- [ ] **Daily Revenue Trend** (Line Chart): Monitor daily sales performance.
- [ ] **Revenue by Channel** (Pie/Donut): Identify top sales sources.
- [ ] **Year-over-Year Comparison** (Line Chart): Seasonality and growth analysis.
- [ ] **Revenue Waterfall** (Waterfall Chart): Net revenue calculation breakdown.
- [ ] **Sales by Location** (Map Chart): Geographic performance.
- [ ] **Hourly Sales Pattern** (Heatmap): Identify peak trading hours.

### Customer Analysis

- [ ] **Customer Acquisition Trend** (Stacked Bar): New vs. Returning split.
- [ ] **RFM Segmentation** (Scatter Plot): High-value customer clusters.
- [ ] **Cohort Retention** (Heatmap): Long-term retention tracking.
- [ ] **Customer Lifetime Value** (Histogram): Distribution of customer value.

### Operations & Product

- [ ] **Order Status Funnel** (Funnel Chart): Pipeline efficiency.
- [ ] **Top Products by Revenue** (Bar Chart): Bestsellers.
- [ ] **Product Category Performance** (Treemap): Revenue mix.
- [ ] **Inventory Status** (Gauge Chart): Stock health overview.
- [ ] **Return Rate Trend** (Line Chart): Quality control monitor.
- [ ] **Fulfillment Performance** (Line Chart): Speed and efficiency.
- [ ] **Delivery Time Distribution** (Histogram): Logistics performance.

### Financials

- [ ] **Payment Methods Distribution** (Pie Chart): Cash/Card/Wallet split.
- [ ] **Discount Impact** (Combo Chart): Profitability impact.
- [ ] **Profit Margin by Category** (Bar Chart): Margin analysis.

---

## 📋 Must-Have Tables (Top 15)

- [ ] **Daily Sales Summary**: Key metrics for end-of-day reporting.
- [ ] **Top Performing Products**: Granular sku-level details.
- [ ] **Slow-Moving Inventory**: Actionable dead stock report.
- [ ] **Customer Segments Analysis**: Detailed segment breakdowns.
- [ ] **Channel Performance Comparison**: CPA and ROI by channel.
- [ ] **Top Customers by Revenue**: VIP list.
- [ ] **Staff Performance**: Sales leaderboard.
- [ ] **Carrier Performance**: Shipping partner analysis.
- [ ] **Return Reasons Analysis**: QA feedback loop.
- [ ] **Promotion Performance**: Campaign results.
- [ ] **Order Fulfillment Queue**: Operational priority list.
- [ ] **Category Performance**: Buying/Merchandising review.
- [ ] **Revenue Components Breakdown**: P&L inputs.
- [ ] **Customer Cohort Analysis**: Raw retention data.
- [ ] **Product Velocity Report**: Sales speed per SKU.

## 📝 Implementation Notes

- All SQL queries should use the specific schema defined in the [Data Dictionary](../DATA_DICTIONARY.md).
- Use Metabase "Smart Numbers" where applicable for automatic trend indicators.
- Set up alerts for "Inventory Status" and "Fulfillment Queue" cards.
