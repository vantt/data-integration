# Group 1 Blueprint Check — CEO + Sales Dashboards
**Date:** 2026-05-29 | **Run:** #2 (post-fix)

## Summary Table

| ID | Dashboard | Blueprint Tabs | MB Tabs | Blueprint Q | MB Q | Blueprint Text | MB Text | Missing in MB | Extra in MB | Status |
|----|-----------|---------------|---------|-------------|------|----------------|---------|---------------|-------------|--------|
| 43 | CEO Weekly Pulse [All] | 3 | 3 | 22 | 22 | 12 | 12 | — | — | **MATCH** |
| 44 | CEO Monthly Scorecard [All] | 3 | 3 | 28 | 28 | 14 | 14 | — | — | **MATCH** |
| 31 | Sales Monthly Business Review [All] | 5 | 5 | 35 | 35 | 21 | 21 | — | — | **MATCH** |
| 8 | Sales Ops Weekly Review [Retail] | 4 | 4 | 24 | 24 | 16 | 16 | — | — | **MATCH** |
| 9 | Sales Ops Monthly Summary [Retail] | 4 | 4 | 30 | 30 | 18 | 18 | — | — | **MATCH** |
| 41 | Daily Sales [Retail] | 4 | 4 | 30 | 30 | 15 | 15 | — | — | **MATCH** |
| 42 | Yesterday's Sales [Retail] | 4 | 4 | 30 | 30 | 15 | 15 | — | — | **MATCH** |
| 46 | Promotion Analysis [Retail] | 5 | 5 | 30 | 30 | 26 | 26 | — | — | **MATCH** |
| 32 | Shopee Channel Economics [Cross] | 3 | 3 | 14 | 14 | 10 | 10 | — | — | **MATCH** |

## Detail Notes

### ID 43 — CEO Weekly Pulse [All]
- 3 tabs: Doanh thu & Target / Kenh ban hang / Khach hang & Canh bao — all present
- 22 questions (deduped: "Chu ky bao cao" appears 3x in blueprint, counted as 1 shared card in MB — consistent)
- Profitability section (Weekly Net Profit, Gross Margin %, Loss-Making Channel Count) in Tab 3 — all deployed

### ID 44 — CEO Monthly Scorecard [All]
- 3 tabs: Hieu suat thang / Kenh & Khach hang / San pham & Van hanh
- Tab 3 (San pham & Van hanh) has 7 questions in blueprint; MB shows correct count including Chu ky bao cao
- Monthly Gross Margin % + Channel Profitability Breakdown + Cost Structure Breakdown all deployed

### ID 31 — Sales Monthly Business Review [All]
- 5 tabs including P&L Hang Thang (added in recent iteration)
- All 35 questions deployed; 35 in MB matches exactly

### ID 8 — Sales Ops Weekly Review [Retail]
- 4 tabs: Tong quan tuan / Kenh & Chi nhanh / Doi ngu & Thanh toan / Margin
- Margin tab: Weekly Margin by Channel + Loss-Order Alert — both present

### ID 9 — Sales Ops Monthly Summary [Retail]
- 4 tabs matching blueprint exactly
- Top 10 Returned Products added in Tong quan thang — deployed

### ID 41 — Daily Sales [Retail]
- 4 tabs: Tong quan / Kenh ban hang / San pham / Khach hang & Thanh toan
- MB shows garbled tab names (encoding issue in API response) but 4 tabs present and correct

### ID 42 — Yesterday's Sales [Retail]
- Mirrors ID 41 structure — same 4 tabs, 30 questions
- "Channel Performance vs Day Before" (not "Yesterday") correctly differentiates from ID 41

### ID 46 — Promotion Analysis [Retail]
- 5 tabs: Tong quan chiet khau / Hieu suat khuyen mai / Phan tich kenh & chi tiet / Discount ROI / Phat hien lam dung & Bat thuong
- 30 questions, 26 text cards — full match

### ID 32 — Shopee Channel Economics [Cross]
- 3 tabs: Settlement Overview / Trends & Details / Shopee P&L Cascade
- 14 questions — all deployed including Orders Below Breakeven

## Result: All 9 dashboards MATCH their blueprints

All tabs, question counts, and text card counts match between Metabase live data and blueprint specs.
No missing or extra cards detected across Group 1.
