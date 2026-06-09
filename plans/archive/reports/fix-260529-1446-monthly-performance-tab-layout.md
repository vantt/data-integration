# Fix: Monthly Performance Tab Layout

**Date:** 2026-05-29  
**Dashboard:** `/dashboard/31-sales-monthly-business-review-all`

---

## Tab Name

- **Live (before):** Tab did not exist — no "Hiệu xuất tháng" tab in live dashboard
- **Blueprint (before):** Tab did not exist in blueprint
- **Live (after):** `Hiệu xuất tháng` (tab id: 253)
- **Blueprint (after):** `### 📑 Tab: Hiệu xuất tháng` added between Tong quan and Hieu suat tai chinh

---

## Widget Mapping (new → existing query source)

| New Widget Name       | Query Source (Tong quan tab)  | Blueprint Question Name    |
|-----------------------|-------------------------------|---------------------------|
| Monthly Net Revenue   | Net Revenue (id: 1052)        | Question: Net Revenue     |
| Monthly GMV           | GMV vs Target (id: 1051)      | Question: GMV vs Target   |
| Target Variance       | Variance to Target (id: 1062) | Question: Variance to Target |
| Monthly Total Orders  | Total Orders (id: 1054)       | Question: Total Orders    |

New questions created: IDs 2139, 2140, 2141, 2142 (fresh questions on new tab, same SQL as source).

---

## Layout

Grid width: **18** (confirmed from all full-width dividers using `size_x: 18`)

### Old (non-existent)
Tab did not exist.

### New
| Widget               | row | col | size_x | size_y |
|----------------------|-----|-----|--------|--------|
| Monthly Net Revenue  | 0   | 0   | 18     | 4      |
| Monthly GMV          | 4   | 0   | 6      | 4      |
| Target Variance      | 4   | 6   | 6      | 4      |
| Monthly Total Orders | 4   | 12  | 6      | 4      |

- Monthly Net Revenue: full width (18/18)
- 3 widgets: same row (row=4), equal width (6 each = 18/3), same height (size_y=4)

---

## Deploy Result

```
✅ Created Question 'Monthly Net Revenue' (ID: 2139)
✅ Created Question 'Monthly GMV' (ID: 2140)
✅ Created Question 'Target Variance' (ID: 2141)
✅ Created Question 'Monthly Total Orders' (ID: 2142)
✅ Synced cards. Dashboard now has 64 cards.
🚀 Deployment Complete.
```

**Verified via API:** Tab id=253 `Hiệu xuất tháng` with correct positions confirmed.

---

## File Modified

`D:\Vantt\app\data-integration\docs\analytics-handbook\blueprints\sales_monthly_review.md`  
— New tab `Hiệu xuất tháng` inserted between `Tong quan` and `Hieu suat tai chinh`, containing 4 questions + Source & Freshness footer.

---

**Status:** DONE  
**Summary:** New tab "Hiệu xuất tháng" created in blueprint and deployed. 4 widgets laid out: Monthly Net Revenue full-width (size_x=18), Monthly GMV + Target Variance + Monthly Total Orders on same row equal-width (size_x=6 each). All positions verified via API.
