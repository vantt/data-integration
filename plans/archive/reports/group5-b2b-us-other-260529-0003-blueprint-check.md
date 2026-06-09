# Blueprint Consistency Check — B2B + US + Other Group
Generated: 2026-05-29T00:03 (Run 2 — post-fix verification)

## Summary Table

| ID | Dashboard | BP Q | MB Q | Missing | Extra | Text BP/MB | Status |
|----|-----------|------|------|---------|-------|------------|--------|
| 49 | B2B Daily Sales [B2B] | 10 | 10 | none | none | 6/6 | MATCH |
| 50 | B2B Orders Tracking [B2B] | 13 | 13 | none | none | 7/7 | MATCH |
| 51 | US CrossBorder Daily [US] | 29 | 29 | none | none | 15/15 | MATCH |
| 40 | Ingestion Health Monitor [Internal] | 24 | 24 | none | none | 11/11 | MATCH |
| 1 | E-commerce Insights | — | 20 | — | — | —/15 | NO_BLUEPRINT |
| 73 | Welcome to ChPulse BI | — | 0 | — | — | —/1 | NO_BLUEPRINT |

**Result: 4 MATCH, 0 MINOR_DIFF, 0 MAJOR_DIFF, 2 NO_BLUEPRINT**

---

## Detail

### 49 — B2B Daily Sales [B2B] — MATCH

Tabs: `Tong quan`, `Chi tiet don hang` ✓

| Blueprint Q | In MB |
|---|---|
| Chu kỳ báo cáo (x2 tabs) | ✓ |
| Net Revenue (B2B) | ✓ |
| Total Orders (B2B) | ✓ |
| AOV (B2B) | ✓ |
| Unique Customers (B2B) | ✓ |
| Revenue by Customer Type | ✓ |
| Revenue by Channel (B2B) | ✓ |
| Top B2B Customers Today | ✓ |
| B2B Orders List | ✓ |

Text cards: 6/6. No drift.

---

### 50 — B2B Orders Tracking [B2B] — MATCH

Tabs: `Cong no`, `Giao hang` ✓

| Blueprint Q | In MB |
|---|---|
| Chu kỳ báo cáo (x2 tabs) | ✓ |
| Outstanding Amount (B2B) | ✓ |
| Unpaid Orders Count (B2B) | ✓ |
| Partial Payment Orders (B2B) | ✓ |
| Avg Days Outstanding (B2B) | ✓ |
| Aging Analysis (B2B) | ✓ |
| Outstanding by Customer Type | ✓ |
| Top Customers by Outstanding | ✓ |
| Pending Fulfillment (B2B) | ✓ |
| In Transit (B2B) | ✓ |
| Delivered Today (B2B) | ✓ |
| Pending B2B Orders List | ✓ |

Text cards: 7/7. No drift.

---

### 51 — US CrossBorder Daily [US] — MATCH

Tabs: `Tong quan`, `Tuan nay`, `Thang nay` ✓

All 29 questions present (9 in Tong quan + 10 in Tuan nay + 10 in Thang nay). Text cards: 15/15. No drift.

---

### 40 — Ingestion Health Monitor [Internal] — MATCH

Tabs: `Tổng quan`, `Volume & Trend`, `Failures & Detail` ✓

All 24 questions present (16 in Tổng quan + 5 in Volume & Trend + 3 in Failures & Detail). Text cards: 11/11. No drift.

---

### 1 — E-commerce Insights — NO_BLUEPRINT

Sample/demo Metabase dashboard. 3 tabs, 20 questions, 15 text cards. No blueprint expected.

### 73 — Welcome to ChPulse BI — NO_BLUEPRINT

Onboarding/welcome page. 0 tabs, 0 questions, 1 text card. No blueprint expected.

---

## Notes
- All 4 blueprinted dashboards remain in perfect sync after post-fix verification.
- Compared to Run 1 (2026-05-28T23:11): no regression, no new drift introduced.
- `Chu kỳ báo cáo` deduplication applied: counted once per unique name across tabs (RAW counts: 49→10, 50→13, 51→29, 40→24 match blueprint raw totals).
