# Blueprint Consistency Check — B2B + US + Other Group
Generated: 2026-05-28T23:11

## Summary
- Checked: 6 dashboards
- MATCH: 4
- MINOR_DIFF: 0
- MAJOR_DIFF: 0
- NO_BLUEPRINT: 2

---

## Dashboard Details

### B2B Daily Sales [B2B] (id: 49) — MATCH

**Blueprint tabs**: Tong quan, Chi tiet don hang
**Metabase tabs**: Tong quan, Chi tiet don hang

**Blueprint questions** (10): Net Revenue (B2B), Total Orders (B2B), AOV (B2B), Unique Customers (B2B), Chu kỳ báo cáo, Revenue by Customer Type, Revenue by Channel (B2B), Top B2B Customers Today, Chu kỳ báo cáo, B2B Orders List
**Metabase questions** (10): Net Revenue (B2B), Total Orders (B2B), AOV (B2B), Unique Customers (B2B), Revenue by Customer Type, Revenue by Channel (B2B), Top B2B Customers Today, B2B Orders List, Chu kỳ báo cáo, Chu kỳ báo cáo

**Missing from Metabase**: none
**Extra in Metabase**: none
**Text cards**: Blueprint 6 / Metabase 6

---

### B2B Orders Tracking [B2B] (id: 50) — MATCH

**Blueprint tabs**: Cong no, Giao hang
**Metabase tabs**: Cong no, Giao hang

**Blueprint questions** (13): Outstanding Amount (B2B), Unpaid Orders Count (B2B), Partial Payment Orders (B2B), Avg Days Outstanding (B2B), Chu kỳ báo cáo, Aging Analysis (B2B), Outstanding by Customer Type, Top Customers by Outstanding, Chu kỳ báo cáo, Pending Fulfillment (B2B), In Transit (B2B), Delivered Today (B2B), Pending B2B Orders List
**Metabase questions** (13): Outstanding Amount (B2B), Unpaid Orders Count (B2B), Partial Payment Orders (B2B), Avg Days Outstanding (B2B), Aging Analysis (B2B), Outstanding by Customer Type, Top Customers by Outstanding, Pending Fulfillment (B2B), In Transit (B2B), Delivered Today (B2B), Pending B2B Orders List, Chu kỳ báo cáo, Chu kỳ báo cáo

**Missing from Metabase**: none
**Extra in Metabase**: none
**Text cards**: Blueprint 7 / Metabase 7

---

### US CrossBorder Daily [US] (id: 51) — MATCH

**Blueprint tabs**: Tong quan, Tuan nay, Thang nay
**Metabase tabs**: Tong quan, Tuan nay, Thang nay

**Blueprint questions** (29):
- Tong quan (9): Chu kỳ báo cáo, Net Revenue (US), Total Orders (US), AOV (US), Unique Customers (US), Orders by Status (US), Fulfillment Status (US), US Revenue Trend (7 Days), US Orders List
- Tuan nay (10): Chu kỳ báo cáo, Chu kỳ báo cáo (Weekly), Net Revenue (Weekly), Total Orders (Weekly), AOV (Weekly), Unique Customers (Weekly), Orders by Status (Weekly), Fulfillment Status (Weekly), Daily Trend This Week (US), US Orders List (Weekly)
- Thang nay (10): Chu kỳ báo cáo, Chu kỳ báo cáo (Monthly), Net Revenue (Monthly), Total Orders (Monthly), AOV (Monthly), Unique Customers (Monthly), Orders by Status (Monthly), Fulfillment Status (Monthly), Weekly Trend This Month (US), US Orders List (Monthly)

**Metabase questions** (29): all 29 questions present, names exact match

**Missing from Metabase**: none
**Extra in Metabase**: none
**Text cards**: Blueprint 15 / Metabase 15

---

### Ingestion Health Monitor [Internal] (id: 40) — MATCH

**Blueprint tabs**: Tổng quan, Volume & Trend, Failures & Detail
**Metabase tabs**: Tổng quan, Volume & Trend, Failures & Detail

**Blueprint questions** (24):
- Tổng quan (16): Chu kỳ báo cáo, Sapo Orders — Trạng thái, Sapo Customers — Trạng thái, Sapo Products — Trạng thái, Sapo Accounts — Trạng thái, Sapo Webhook — Trạng thái, Sapo History Log — Trạng thái, Google Sheets Targets — Trạng thái, Google Sheets Marketing Spend — Trạng thái, MISA File Drop — Trạng thái, Shopee File Drop — Trạng thái, Drift — Sapo Orders, Drift — Sapo Customers, Drift — MISA, Drift — Shopee, Run Count per Day (30d)
- Volume & Trend (5): Chu kỳ báo cáo, Sapo Batch — Volume 30d, Sapo Realtime & Incremental — Volume 30d, External Sources — Volume 30d, Success Rate per Asset (7d)
- Failures & Detail (3): Chu kỳ báo cáo, Runs Failed or Skipped (7d), Full Run Log (200 runs)

**Metabase questions** (24): all 24 questions present, names exact match

**Missing from Metabase**: none
**Extra in Metabase**: none
**Text cards**: Blueprint 11 / Metabase 11

---

### E-commerce Insights (id: 1) — NO_BLUEPRINT

No blueprint file — this is a sample/demo dashboard.

**Metabase tabs**: Overview, Portfolio Performance, Website Analysis
**Metabase questions** (20): Best selling products, Orders by product category, Average product rating, Revenue by state, Product category orders per age, Revenue and orders over time, Revenue per quarter, Revenue goal for this quarter, Revenue by product category, Orders according to sources per quarter, Total orders by product category, Product breakdown, Total order amount vs. discount given, Customer satisfaction per category, Customer survey responses, Checkout funnel, Number of subscriptions, Most recent subscription, User flow diagram, Subscription seats over time
**Text cards**: 15

---

### Welcome to ChPulse BI (id: 73) — NO_BLUEPRINT

No blueprint file — this is an onboarding/welcome page.

**Metabase tabs**: none (untabbed)
**Metabase questions** (0): no question cards
**Text cards**: 1

---

## Notes
- All 4 dashboards with blueprints are perfectly in sync — no drift detected
- Dashboard name for id 73 shows `"Welcome to Ch?Pulse BI"` in API (character encoding issue in API response for the `❓` emoji), display in Metabase UI shows correctly
- E-commerce Insights (id 1) is a Metabase sample dashboard — no blueprint expected
