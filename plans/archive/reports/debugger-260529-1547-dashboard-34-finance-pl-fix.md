# Debug Report: Dashboard 34 — Finance P&L [All] — Widget Errors + Layout Fix

**Dashboard:** `/dashboard/34-finance-p-l-all`
**Reported:** 2026-05-29 ~15:47 ICT
**Investigated + Fixed:** 2026-05-29 15:47–17:10 ICT
**Investigator:** debugger agent

---

## 1. Symptoms

ALL widgets in dashboard 34 showed "There was a problem displaying this chart." across all 3 tabs. Layout was overlapping/messy.

---

## 2. Root Cause Analysis

### RC-1 (PRIMARY): Filters missing `field_id` → template tags created as `type: "date"` (basic variable) instead of `type: "dimension"`

**Evidence chain:**

1. Blueprint filter definitions had no `field_id`:
   ```json
   { "slug": "date_range", "type": "date/all-options", "default": "past30days" }
   ```
2. Deploy script (`buildTemplateTags`) creates `type: "dimension"` ONLY when `field_id` is present. Without it, fallback: `type: "date"` (basic variable).
3. When Metabase renders dashboard with `past30days` filter selected, it passes value `"past30days"` to the card. A `type: "date"` template tag expects a literal date string (e.g. `2026-01-01`). DuckDB fails: `"Text 'past30days' could not be parsed, unparsed text found at index 0"`.
4. All 15 question cards had `type: "date"` — confirmed by inspecting `card.dataset_query.stages[0].template-tags` via API.
5. Dashboard API: `parameters[].field_id = null` for both filters — no field binding.

**Same root cause as RC-1 in dashboard 33 (debugger-260529-1515 report).**

### RC-2 (SECONDARY): Multi-table dashboard — single `field_id` can't bind all cards

After adding `field_id: 141` (fact_orders.order_timestamp) to the filter, cards querying `int_misa_sales_lines` (e.g. COGS MTD, Gross Margin) still failed:
`"Binder Error: Referenced table 'main.fact_orders' not found! Candidate tables: 'main.int_misa_sales_lines'"`

**Root cause:** Metabase dimension template tag embeds the field's parent table in the filter injection. `field_id: 141` (fact_orders.order_timestamp) generates a WHERE clause referencing `fact_orders` — which doesn't exist in a `int_misa_sales_lines`-only query. Three separate field_ids required:

| table | field | field_id | type |
|---|---|---|---|
| fact_orders | order_timestamp | 141 | DateTimeWithTZ |
| int_misa_sales_lines | posting_date | 324 | Date |
| int_shopee_order_fees | payout_released_at | 287 | Date |

The deploy script doesn't support per-card field_id overrides — requires post-deploy manual patch.

### RC-3: Revenue vs COGS Trend — dual-table query incompatible with single dimension filter

Card 1115 queries BOTH `fact_orders` (order_timestamp) and `int_misa_sales_lines` (posting_date) in separate CTEs, both with `[[AND {{date_range}}]]`. No single `field_id` works for both CTEs — whichever table's field is used, the other CTE fails with a binder error.

**Fix:** Remove `{{date_range}}` from the trend SQL; hardcode a 13-month rolling window. Trend charts show full-year context regardless of filter — this is the correct semantic behavior.

### RC-4 (ELIMINATED): Schema drift / DuckDB binder error from view staleness

All 15 cards returned `completed` when queried WITHOUT filter parameters. All referenced tables/columns confirmed present. Not a view rebuild issue.

### RC-5 (ELIMINATED): Visualization settings error

Gauge segments, waterfall config, combo chart series settings all valid for Metabase v0.60.2. No viz config errors detected.

---

## 3. Layout Issues

**P&L Overview tab — 5 overlapping widgets (original):**

| widget | original pos | overlap |
|---|---|---|
| Boi canh text | row 2-3 | overlaps Net Revenue (row 3-6) |
| Net Revenue MTD | row 3-6, col 0-17 | overlaps COGS (row 3-5, col 6-9), Gross Margin Gauge (row 3-7, col 14-17), PL Overview Heading (row 4) |
| PL Overview Heading | row 4 | inside Net Revenue widget |
| Gross Margin Percent | row 3-7 | overlaps Gross Profit MTD (row 7-10) |
| PL Trend Heading | row 8 | inside Gross Profit MTD (row 7-10) |

Shopee Economics tab: Settlement Margin gauge at `size_x: 4, row 3-7` conflicted with Platform Fee Rate at `row 3, col 10, size_x: 4` — they shared columns 10-13.

---

## 4. Fixes Applied

### 4a. Blueprint fixes (`docs/analytics-handbook/blueprints/finance_pl.md`)

1. **Filters: added `field_id`** — set `field_id: 141` (arbitrary; overridden post-deploy). This enables `type: "dimension"` template tags.
2. **SQL template tag syntax** — All `[[AND order_timestamp >= {{date_range}}]]` → `[[AND {{date_range}}]]` (dimension type generates full WHERE clause, not single value).
3. **Revenue vs COGS Trend**: Removed `{{date_range}}` from both CTEs; replaced with hardcoded `>= date_trunc('month', current_date) - INTERVAL '12 months'`.
4. **Layout redesign** — Non-overlapping grid for all 3 tabs:

**P&L Overview (final):**
```
row  0-1:  Chu kỳ báo cáo (18×2)
row  2:    ## Heading: PL Overview (18×1)
row  3-6:  Net Revenue MTD (9×4) | Gross Margin Percent gauge (9×4)
row  7-10: COGS MTD (9×4) | Gross Profit MTD (9×4)
row 11:    ## Heading: PL Trend (18×1)
row 12-17: Revenue vs COGS Trend (12×6) | Revenue Waterfall (6×6)
row 97-98: Seasonal Context footnote (18×2)
row 99:    Source & Freshness (18×1)
```

**Channel Profitability (final):**
```
row  0-1:  Chu kỳ báo cáo (18×2)
row  2:    ## Heading (18×1)
row  3-8:  Margin by Channel (9×6) | Revenue vs COGS by Channel (9×6)
row  9:    ## Heading: Trend (18×1)
row 10-15: COGS Ratio Trend (18×6)
row 99:    Source & Freshness (18×1)
```

**Shopee Economics (final):**
```
row  0-1:  Chu kỳ báo cáo (18×2)
row  2:    ## Heading (18×1)
row  3-6:  Settlement MTD (6×4) | Margin Gauge (6×4) | Platform Fee Rate (6×4)
row  7-10: Shopee Gross Revenue (9×4) [empty 9 cols]
row 11:    ## Heading: Fee Structure (18×1)
row 12-17: Shopee Fee Breakdown (9×6) | Revenue→Settlement Waterfall (9×6)
row 99:    Source & Freshness (18×1)
```

5. **Heading text**: Added `## ` prefix to all section headings to render as markdown h2 (bold visual hierarchy).
6. **Seasonal Context text**: Moved from row 2 (blocked KPIs) → row 97 (footnote area).

### 4b. Post-deploy patch: per-card `field_id` assignment

After each deploy (deploy script overwrites template tags), manually patched each card's dimension field_id via PUT `/api/card/<id>`:

```
Cards 1111, 1115, 1116 (fact_orders)     → field_id: 141 (order_timestamp, DateTimeWithTZ)
Cards 1112, 1113, 1114, 1117-1119 (misa) → field_id: 324 (posting_date, Date)
Cards 1120-1125 (shopee)                 → field_id: 287 (payout_released_at, Date)
```

---

## 5. Deploy Result

```
Deploy 1 (with field_id:141):  ✅ Synced 28 cards. Deployment Complete.
Post-patch 1:                   ✅ 14 cards patched.
Deploy 2 (trend SQL updated):  ✅ Synced 28 cards. Deployment Complete.
Post-patch 2:                   ✅ 14 cards patched.
```

---

## 6. Verification

### Dashboard-context query test (all 18 dashcards, `past30days` filter):

| dashcard | card | name | status | rows |
|---|---|---|---|---|
| 2057 | 1443 | Chu kỳ báo cáo (Tab 1) | completed | 1 |
| 1556 | 1111 | Net Revenue MTD | completed | 1 |
| 1557 | 1112 | COGS MTD | completed | 1 |
| 1558 | 1113 | Gross Profit MTD | completed | 1 |
| 1559 | 1114 | Gross Margin Percent | completed | 1 |
| 1560 | 1115 | Revenue vs COGS Trend | completed | 13 |
| 1561 | 1116 | Revenue Waterfall | completed | 4 |
| 2861 | 1924 | Chu kỳ báo cáo (Tab 2) | completed | 1 |
| 1562 | 1117 | Margin by Channel | completed | 3 |
| 1563 | 1118 | Revenue vs COGS by Channel | completed | 3 |
| 1564 | 1119 | COGS Ratio Trend | completed | 3 |
| 2863 | 1925 | Chu kỳ báo cáo (Tab 3) | completed | 1 |
| 1565 | 1120 | Shopee Settlement MTD | completed | 1 |
| 1566 | 1121 | Settlement Margin Percent | completed | 1 |
| 1567 | 1122 | Platform Fee Rate | completed | 1 |
| 1568 | 1123 | Shopee Gross Revenue | completed | 1 |
| 1569 | 1124 | Shopee Fee Breakdown | completed | 0 |
| 1570 | 1125 | Revenue to Settlement Waterfall | completed | 7 |

**All 18 dashcards: `completed`.**

Card 1124 (Shopee Fee Breakdown) returns 0 rows: `int_shopee_order_fees` last payout was 2026-04-08 (51 days ago). `past30days` filter yields no data → all fee SUMs are 0 → `WHERE "Gia tri phi" > 0` filters all rows out. This is a data staleness issue, not a code bug — the card renders as "No results" which is correct behavior.

---

## 7. Known Issue: Post-Deploy Patch Required

Every time the blueprint is redeployed, the deploy script resets template tags to `field_id: 141` for all cards. The per-card patch must be re-applied after each redeploy.

**Recommendation:** Modify `.skills/metabase-automation/scripts/deploy_from_markdown.js` `buildTemplateTags()` to support a `field_id_map` object in the blueprint filter definition, e.g.:

```json
{
  "slug": "date_range",
  "type": "date/all-options",
  "field_id": 141,
  "field_id_map": {
    "int_misa_sales_lines": 324,
    "int_shopee_order_fees": 287
  }
}
```

Then `buildTemplateTags` detects the table reference in each card's SQL and applies the correct field_id. This is a deploy script enhancement, not urgent.

---

## 8. Unresolved Questions

1. **Shopee data staleness**: `int_shopee_order_fees.payout_released_at` max = 2026-04-08. Is the Shopee settlement ingestion pipeline failing? Card 1124 will render "No results" until new data arrives.
2. **Revenue vs COGS Trend filter**: Trend now shows hardcoded 13-month window — the date filter has no effect on it. This is intentional (correct for trend context) but the user may expect the filter to also control trend range. Consider adding a note in the heading text.
3. **Channel filter on Shopee tab**: The `channel` filter is available in dashboard header but has no effect on Shopee Economics cards (Shopee data has no channel_name dimension). This is expected but may confuse users.
