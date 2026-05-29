# Pattern C Investigation — Source Not at Bottom

**Date:** 2026-05-29  
**Dashboards:** 43, 31, 32

---

## Summary

All three blueprints already position source-freshness BELOW the actual max data row. The Pattern C violation exists only in the **live Metabase** (stale deployment), not in the blueprint files. No blueprint edits were applied.

---

## Case 1 — Dashboard 43: CEO Weekly Pulse [All]
### Tab: Khách hàng & Cảnh báo (tab id=129)

**Live API — cards sorted by row desc:**

| row | size | type | content |
|-----|------|------|---------|
| 19 | 6x3 | CARD id=1705 | "Weekly Net Profit" (scalar) |
| 19 | 6x3 | CARD id=1706 | "Gross Margin %" (scalar) |
| 19 | 6x3 | CARD id=1707 | "Loss-Making Channel Count" (scalar) |
| 18 | 18x1 | TEXT | "# Lợi nhuận tuần qua — Net Profit, Gross Margin, Kênh lỗ" |
| **17** | 18x1 | **TEXT (source)** | "Source: fact_orders · Updated weekly (Mon-Sun) · Scope: All sales channels..." |
| 14 | 6x3 ea | CARD id=1261-1263 | Cancelled Orders, Return Count, Discount Rate |
| 7-13 | ... | ... | Customer/14-day bar chart |
| 0 | 18x2 | CARD id=1918 | "Chu kỳ báo cáo" |

**Widget at max_row=19:** Three profitability scalars (Weekly Net Profit, Gross Margin %, Loss-Making Channel Count). These are data widgets added after the source card was placed at row=17.

**Root cause:** Profitability section (heading row=18, cards row=19) was appended after source card was placed at row=17. Source was not moved down.

**Blueprint (`ceo_weekly_pulse.md`, Tab Khach hang & Canh bao):**
- Source-freshness pos: `{ "row": 22 }` — above profit cards at row=19 in doc order, but row=22 > 19 numerically ✓
- Blueprint source row 22 > live max data row 19 → **blueprint already correct**

**Fix applied:** None.

---

## Case 2 — Dashboard 31: Sales Monthly Business Review [All]
### Tab: P&L Hàng Tháng (tab id=250)

**Live API — cards sorted by row desc:**

| row | size | type | content |
|-----|------|------|---------|
| 14 | 18x9 | CARD id=2112 | "Channel Profit Contribution (Top 10)" (table) |
| 13 | 18x1 | TEXT | "## Top/Bottom kênh theo lợi nhuận..." |
| 6 | 18x7 | CARD id=2111 | "Gross Margin % Trend (12M)" (line) |
| **5** | 18x1 | **TEXT (source)** | "**Source:** fact_orders + fact_order_economics · Cadence: monthly..." |
| 1 | 9x4 ea | CARD id=2109-2110 | Monthly Net Profit vs Last Month, Gross Margin % vs Last Month |
| 0 | 18x2 | CARD id=2108 | "Chu kỳ báo cáo" |
| 0 | 18x1 | TEXT (x2) | PnL headings |

**Widget at max_row=14:** `Channel Profit Contribution (Top 10)` table (18x9), visually occupies rows 14–22.

**Root cause:** Source-freshness placed at row=5 (early in tab). The Gross Margin Trend chart (row=6) and Channel Profit table (row=14) were added/positioned below it without moving the source card.

**Blueprint (`sales_monthly_review.md`, Tab P&L Hang Thang):**
- Source-freshness pos: `{ "row": 23 }` ✓
- Channel Profit table: `row=14, size_y=9` → occupies rows 14–22
- Blueprint source row=23 > last occupied row 22 → **blueprint already correct**

**Fix applied:** None.

---

## Case 3 — Dashboard 32: Shopee Channel Economics [Cross]
### Tab: Shopee P&L Cascade (tab id=178)

**Live API — cards sorted by row desc:**

| row | size | type | content |
|-----|------|------|---------|
| 10 | 18x8 | CARD id=1669 | "Orders Below Breakeven (True Margin < 0)" (table) |
| 2 | 12x8 | CARD id=1667 | "Shopee Margin vs COGS Scatter" (scatter) |
| 2 | 6x8 | CARD id=1668 | "Cost Waterfall % of Net Revenue" (row chart) |
| 1 | 18x1 | TEXT | "**Luu y:** Du lieu nay join Shopee fees voi MISA COGS..." |
| **0** | 18x1 | **TEXT (source)** | "**Source:** int_shopee_order_fees · Cadence: payout-period..." |
| 0 | 18x2 | CARD id=1934 | "Chu kỳ báo cáo" |
| 0 | 18x1 | TEXT | "# PnL Cascade Heading" |

**Widget at max_row=10:** `Orders Below Breakeven` table (18x8), occupies rows 10–17.

**Root cause (Pattern A + C combined):** Source at row=0 is both at the top (Pattern A) and not at bottom (Pattern C). Three widgets share row=0: Chu kỳ báo cáo, PnL Cascade Heading, and Source card — this is a col=0 pile-up from incremental additions.

**Blueprint (`shopee_channel_economics.md`, Tab Shopee P&L Cascade):**
- Source-freshness pos: `{ "row": 18 }` ✓
- "Orders Below Breakeven" table: `row=10, size_y=8` → occupies rows 10–17
- Blueprint source row=18 > last occupied row 17 → **blueprint already correct**
- The task note mentioned "Agent đã fix từ row=99 → row=11" — current blueprint shows `row=18`, which clears the full table (rows 10–17) with one row of buffer. This is correct and better than row=11 (which would collide with the table).

**Fix applied:** None — row=18 is already correct.

---

## Verdict

| Dashboard | Tab | Source row (live) | Max data row (live) | Source row (blueprint) | Blueprint OK? |
|-----------|-----|-------------------|---------------------|------------------------|---------------|
| 43 | Khách hàng & Cảnh báo | 17 | 19 | 22 | Yes |
| 31 | P&L Hàng Tháng | 5 | 14 (table ends at row 22) | 23 | Yes |
| 32 | Shopee P&L Cascade | 0 | 10 (table ends at row 17) | 18 | Yes |

**No blueprint changes were needed.** Pattern C violations are live-deployment drift — blueprints already have the correct source positions. A redeploy of the affected tabs is the next required action (excluded from this task per instruction).

---

## Files Modified

None.

## Unresolved Questions

1. **Redeploy required:** These tabs need a targeted redeploy to sync live Metabase with the correct blueprint positions. Excluded from this task per "KHÔNG redeploy Metabase" instruction.
2. **Dashboard 32, Shopee P&L Cascade:** Three widgets at row=0 (Chu kỳ báo cáo, PnL heading, source) is a layout anomaly. Only Chu kỳ báo cáo should be at row=0 — the source at row=0 in live is the regression that needs redeploy to fix.
3. **Dashboard 31, P&L Hàng Tháng:** Two extra TEXT headings at row=0 alongside Chu kỳ báo cáo (row=0) — similar row collision worth reviewing when this tab is redeployed.
