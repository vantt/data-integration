# Board C — Customer Intelligence Build Report
**Date:** 2026-06-12 · **Plan ref:** boardC-customer-intelligence-build-260612-0932

---

## Blueprint

- **File:** `docs/analytics-handbook/blueprints/customer_intelligence.md` (NEW — created 2026-06-12)
- **Source:** `blueprints/customer_intelligence_monthly.md` (dashboard #15, collection 93)

---

## Dashboard

| Field | Value |
|---|---|
| **Name** | Monthly · Customer Intelligence [Cross] |
| **Dashboard ID** | 106 |
| **URL** | https://bi.lan.fwg.vn/dashboard/106 |
| **Collection ID** | 99 (👥 Customer, under Marketing & Customers ID 52) ✅ |
| **Total cards** | 51 |

---

## Tabs & Cards

### Tab 1 — Overview & Health (10 cards)
- Chu kỳ báo cáo (scalar)
- Text: Bối cảnh mùa vụ + YoY Caveat
- Text: Monitor customer base health
- Total Customers (scalar, snapshot MoM)
- Active Customers 30d (scalar, snapshot MoM)
- New Customers Last Month (scalar, MoM + YoY)
- One-Time Buyer Rate (scalar, snapshot MoM)
- Text: Assess customer status distribution
- Customer Status Distribution (pie)
- Customer Segment Distribution (pie)
- Revenue from Top 20% Customers (scalar, Pareto)
- Text: Track growth dynamics
- Monthly Acquisition vs Churn 6M (combo)
- Text: Review segment health scorecard
- Customer Health Scorecard (table, conditional formatting)
- Text + Source & Freshness

### Tab 2 — Value & Segmentation (17 cards)
- Chu kỳ báo cáo (scalar)
- Text: Analyze customer value
- Total Customer LTV (scalar, snapshot MoM)
- Avg LTV per Customer (scalar, snapshot MoM)
- Avg Orders per Customer (scalar, snapshot MoM)
- Repeat Purchase Rate (scalar, snapshot MoM)
- Text: Examine LTV distribution
- Customer Value Distribution (bar histogram)
- Segment Revenue Share (pie)
- Text: Track segment performance trends
- AOV by Segment Trend 6M (line, multi-segment)
- Revenue by Segment Trend 6M (stacked area)
- Text: Review segment detail
- Segment Revenue & Metrics Detail (table)
- Source & Freshness

### Tab 3 — Behavior & Insights (24 cards)
- Chu kỳ báo cáo (scalar)
- Text: Analyze purchase behavior
- Text: Channel effectiveness
- Channel Revenue by Segment (stacked bar, 3M)
- Text: Product affinity
- Top 10 Products — VIP Customers (horizontal bar)
- Top 10 Products — First-Time Buyers (horizontal bar)
- Text: New customer quality
- New Customer Quality Trend 6M (combo: bar + 2 lines)
- Text: Demographics & loyalty
- Loyalty Point Distribution by Segment (stacked bar)
- Gender Distribution by Segment (stacked bar)
- Text: Behavioral metrics
- Discount Sensitivity Distribution (pie)
- Discount Sensitivity by Segment (normalized stacked bar)
- Avg Days Between Orders by Segment (table)
- Text: Geographic view
- Top 15 Provinces by Customers (horizontal bar) ← from #48
- Top 15 Provinces by LTV (horizontal bar) ← from #48
- Source & Freshness

---

## Dedup Notes

- All value/segment/behavior/LTV/product-affinity content kept (unique strategic core).
- Discount Sensitivity Distribution + by Segment kept (behavioral angle; margin angle stays in board D).
- **Added from #48:** Top 15 Provinces by Customers + Top 15 Provinces by LTV → appended to Behavior & Insights tab as "Geographic view" section. SQL is clean (`dim_customers.province`). No operational call-lists or watchlists added.
- Boards #15 and #48 untouched.

---

## Deploy Log (tail)

```
✅ Created Dashboard 'Monthly · Customer Intelligence [Cross]' (ID: 106)
📑 Dashboard has 3 tab(s): Overview & Health, Value & Segmentation, Behavior & Insights
✅ Synced cards. Dashboard now has 51 cards.
🚀 Deployment Complete.
```

---

## Verification

| Card | Status | Sample |
|---|---|---|
| Total Customer LTV (2286) | completed, 1 row | [1,695,553,845 / prev 1,626,902,346] |
| Customer Health Scorecard (2285) | completed, 4 rows | VALUE_VIP: 34 customers, 26.5% active |
| Monthly Acquisition vs Churn 6M (2284) | completed, 6 rows | Dec-25: +54 acq / -14 churn / +40 net |

Collection_id=99 confirmed. 3 tabs present. No card errors observed.

---

**Status:** DONE
**Summary:** New dashboard #106 "Monthly · Customer Intelligence [Cross]" deployed to collection 99 (👥 Customer). Blueprint created from #15 source with light additions (2 geo cards from #48). 51 cards across 3 tabs. All verification queries return data.
**Concerns:** None.
