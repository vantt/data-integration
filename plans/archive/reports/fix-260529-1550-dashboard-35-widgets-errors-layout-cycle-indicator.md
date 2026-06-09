# Fix: Dashboard 35 — Widget Errors + Layout + Cycle-Indicator Mismatch

**Dashboard:** `/dashboard/35-order-profitability-all`
**Date:** 2026-05-29
**Status:** DONE

---

## Root Causes

### RC-1: Widget errors — missing `field_id` on filters
Filters `date_range` and `channel` had no `field_id` in blueprint → deploy script couldn't wire template tags as dimension filters → `parameter_mappings: []` on all question cards → SQL executed but filter had no effect (all-time unfiltered data), and direct query with a filter value caused SQL parse errors.

**Fix:** Added `"field_id": 77` (date/all-options) and `"field_id": 179` (string/=) to filter definitions in blueprint.

### RC-2: Cycle-indicator shows "this month" — hardcoded SQL
`Chu kỳ báo cáo` scalar used `current_date - INTERVAL '30 days'` which showed ~30 days ending today. Filter default is `past3months` (3 months). The label text said "Period filter ở đầu — mặc định" but the dates shown were wrong.

**Fix:** Changed SQL to show accurate 3-month window:
```sql
SELECT '📅 3 tháng gần nhất: ' ||
  strftime((date_trunc('month', current_date) - INTERVAL '3 months')::DATE, '%d/%m/%Y') ||
  ' – ' ||
  strftime((current_date - INTERVAL '1 day')::DATE, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"
```

### RC-3: Layout — uneven KPI section heights
P&L Overview had asymmetric "Bento box" — Gauge (6×4), Gross Profit (6×2), Net Profit (6×2), Orders COGS wide bottom (12×2 at row=5). The 3 different heights and misaligned rows created visual clutter.

**Fix:** Unified all 4 KPI cards to same height (4 rows), 6+4+4+4=18 grid:
| Card | row | col | size_x | size_y |
|------|-----|-----|--------|--------|
| Avg Gross Margin % (gauge) | 3 | 0 | 6 | 4 |
| Total Gross Profit | 3 | 6 | 4 | 4 |
| Total Channel Net Profit | 3 | 10 | 4 | 4 |
| Orders with COGS | 3 | 14 | 4 | 4 |

Also fixed Source & Freshness text: `is_sales_channel` → `all channels`.

---

## Final Layout

```
row  0-1:  [════════ Chu kỳ báo cáo (18×2) ════════]
row  2:    [════════ ## Tổng quan P&L (18×1) ════════]
row  3-6:  [Gauge 6×4][Gross Profit 4×4][Net Profit 4×4][Orders COGS 4×4]
row  7:    [════════ ## Lợi nhuận theo kênh (18×1) ════════]
row  8-13: [Channel Net Margin 9×6][Cost Structure 9×6]
row  14:   [════════ ## Chi tiết P&L (18×1) ════════]
row 15-20: [Margin Distribution 9×6][Profit by Date 9×6]
row  21:   [════════ ## Danh sách đơn hàng (18×1) ════════]
row 22-31: [════════ Order P&L Table (18×10) ════════]
row  99:   [════════ Source & Freshness (18×1) ════════]
```

---

## Verification

Post-deploy API checks:
- All 10 question cards: `parameter_mappings = 2` (date_range + channel)
- All 10 query results: `status = completed`, rows > 0
- Card positions confirmed via `/api/dashboard/35`

---

## Files Modified

- `docs/analytics-handbook/blueprints/order_profitability_all.md`
  - Added `field_id: 77` and `field_id: 179` to filters
  - Fixed cycle-indicator SQL (30 days → 3-month accurate window)
  - Unified KPI layout (4 rows each, 6+4+4+4=18)
  - Fixed Source scope text
