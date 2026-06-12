# Board D — Monthly · Customer Profitability [Retail] — Build Report

**Date:** 2026-06-12
**Blueprint:** `docs/analytics-handbook/blueprints/customer_profitability.md`
**Dashboard ID:** 104
**Dashboard URL:** https://bi.lan.fwg.vn/dashboard/104
**Collection ID:** 99 (👥 Customer, sub of Marketing & Customers, ID 52) ✅

---

## Tab / Card List

### Tab 1: Channel × Retention × Margin (4 questions + 3 text cards = 7)
| Card ID | Type | Title |
|---------|------|-------|
| 2244 | scalar | Chu kỳ báo cáo |
| 2245 | row chart | Channel Net Margin % by Channel |
| 2246 | row chart | Repeat Rate by Channel |
| 2247 | table | Channel × Repeat Rate × Contribution Margin |
| — | text | Channel net margin % heading |
| — | text | Channel comparison table heading |
| — | text | Source & Freshness |

### Tab 2: Discount-Dependency × Margin (6 questions + 4 text cards = 10 + 1 shared scalar)
| Card ID | Type | Title |
|---------|------|-------|
| 2244 | scalar | Chu kỳ báo cáo (reused) |
| 2248 | pie | Discount Sensitivity Distribution |
| 2249 | row chart | Avg Contribution Margin by Discount Sensitivity |
| 2250 | scalar | PROMO_DEPENDENT — Discount % of Gross Revenue |
| 2251 | scalar | Margin-Negative Retail Customers |
| 2252 | scalar | PROMO_DEPENDENT Retail Customers |
| 2253 | table | Discount Sensitivity × Value Tier × Margin Detail |
| — | text | Discount dependency heading |
| — | text | Key KPIs heading |
| — | text | Segment detail heading |
| — | text | Source & Freshness |

**Total dashcards:** 18 (confirmed by API)

---

## Dropped Content

- Tab "Activation Now" (queue/contactable/reactivation) — lives in board A "Daily · Customer Action Queue" (#103+). Not duplicated.
- Dashboard filters (action_type, value_group, is_contactable) — not needed for monthly strategic view.

---

## Deploy Log (tail)

```
✅ Created Dashboard 'Monthly · Customer Profitability [Retail]' (ID: 104)
✅ Created Question 'Channel Net Margin % by Channel' (ID: 2245)
✅ Created Question 'Repeat Rate by Channel' (ID: 2246)
✅ Created Question 'Channel × Repeat Rate × Contribution Margin' (ID: 2247)
✅ Created Question 'Discount Sensitivity Distribution' (ID: 2248)
✅ Created Question 'Avg Contribution Margin by Discount Sensitivity' (ID: 2249)
✅ Created Question 'PROMO_DEPENDENT — Discount % of Gross Revenue' (ID: 2250)
✅ Created Question 'Margin-Negative Retail Customers' (ID: 2251)
✅ Created Question 'PROMO_DEPENDENT Retail Customers' (ID: 2252)
✅ Created Question 'Discount Sensitivity × Value Tier × Margin Detail' (ID: 2253)
✅ Synced cards. Dashboard now has 18 cards.
🚀 Deployment Complete.
```

---

## Verification Numbers

**Card 2245 — Channel Net Margin % by Channel** (rows=6, no error)
- Shopee - JPC SHOP: −8.4% (lowest, confirms story)
- Shopee - thehealthyus: −8.3%
- Shopee - Fine Japan Vietnam: +23.1% (profitable)
- Đại Lý: +23.3%

**Card 2248 — Discount Sensitivity Distribution** (rows=4, no error)
- PROMO_DEPENDENT: 1,239 customers (18.5% of classified base)
- Chưa đủ dữ liệu: 5,455 (81.3%) — expected: single-purchase customers without enough order history

**Card 2253 — Discount Sensitivity × Value Tier × Margin Detail** (rows=7, no error)
- PROMO_DEPENDENT / VALUE_BRONZE: 75.4% margin-negative, Avg Contrib −4,912K VND
- PROMO_DEPENDENT / VALUE_VIP: 33.3% margin-negative

No Binder errors on ORDER BY — `CASE COALESCE(discount_sensitivity,'Chưa đủ dữ liệu') WHEN ...` fix applied throughout.

---

## Errors Fixed

- DuckDB Binder fix: ORDER BY clauses use `CASE COALESCE(discount_sensitivity, 'Chưa đủ dữ liệu') WHEN ...` matching GROUP BY expression exactly. Original #102 used `CASE discount_sensitivity WHEN ...` vs GROUP BY `COALESCE(...)` — would cause Binder error under DuckDB.
- Pre-deploy warning: "SQL uses raw customer_type='RETAIL' — use WHERE scope_retail" — non-blocking (dim_customers has no scope_retail column; customer_type='RETAIL' is the correct filter for dim_customers queries). Acceptable per SQL migration period note.

---

**Status:** DONE
**Summary:** New dashboard #104 "Monthly · Customer Profitability [Retail]" deployed to collection 99 (👥 Customer). 2 margin tabs from #102 (Channel × Retention × Margin, Discount-Dependency × Margin), Activation Now tab dropped. All 10 questions deployed, 18 dashcards synced. 3 verification queries return rows with no card errors. DuckDB Binder fix applied. Board #102 untouched.
**Concerns:** None.
