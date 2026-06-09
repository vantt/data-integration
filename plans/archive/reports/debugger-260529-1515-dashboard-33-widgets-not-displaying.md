# Debug Report: Dashboard 33 — Widgets Not Displaying + Layout Mess

**Dashboard:** `/dashboard/33-channel-profitability-monthly-cross`
**Reported:** 2026-05-29 ~15:15 ICT
**Investigated:** 2026-05-29 15:15–15:40 ICT
**Investigator:** debugger agent

---

## 1. Symptoms Verified

Ran all 12 dashcard queries via API (both raw `/api/card/<id>/query` and dashboard-context `/api/dashboard/33/dashcard/<id>/card/<id>/query`). Results as of 15:25:

| card_id | name | status | rows | error |
|---------|------|--------|------|-------|
| 1101 | Gross Margin % | completed | 1 | none |
| 1102 | Total Revenue | completed | 1 | none |
| 1103 | Total COGS | completed | 1 | none |
| 1104 | Total Gross Profit | completed | 1 | none |
| 1105 | Margin by Channel | completed | 5 | none |
| 1106 | Revenue vs COGS by Channel | completed | 5 | none |
| 1107 | Margin Trend by Channel | completed | 57 | none |
| 1108 | Revenue Mix Trend | completed | 57 | none |
| 1109 | Top Products by Profit | completed | 15 | none |
| 1110 | Low-Margin Products | completed | 103 | none |
| 1441 | Chu kỳ báo cáo (Tab 1) | completed | 1 | none |
| 1927 | Chu kỳ báo cáo (Tab 2) | completed | 1 | none |

**Current state (post 14:58 redeploy): all cards healthy.** The "not displaying" was the pre-fix state.

---

## 2. Root Cause(s)

### RC-1 (PRIMARY): Wrong template tag syntax → filter not bound → widgets showed unfiltered data

**Evidence chain:**

1. **Before the 14:58 redeploy**, the deployed SQL in all 10 question cards used raw text substitution syntax:
   ```sql
   [[AND posting_date >= {{date_range}}]]   -- WRONG
   [[AND channel_name = {{channel}}]]       -- WRONG
   ```
   These are NOT dimension-type template tags — they attempted to use filter variables as bare values inside a comparison expression. For a `date/all-options` filter, Metabase generates a full date-range clause (e.g. `posting_date BETWEEN x AND y`), not a single value. Embedding it as `posting_date >= <range_clause>` produces malformed SQL.

2. **Server log at 11:41 (user_id=1 viewed dashboard):**
   ```
   WARN parameters.params :: Could not find matching Field ID for target: "date_range"
   WARN parameters.params :: Could not find matching Field ID for target: "channel"
   ```
   Metabase could not bind the dashboard filter parameter to any field reference in the card. The cards had `referenced_fields = nil` (no dimension links). Queries executed, but the filter widget had no effect — charts showed all-time unfiltered data regardless of what the user selected.

3. **Server log at 14:56 (manual card query, user_id=2):**
   ```
   POST /api/card/1101/query 500
   ```
   Direct query with a filter value triggered SQL parse error — the old syntax broke.

4. **Server log at 14:58:41 (redeploy):**
   ```
   INFO models.card :: Referenced Fields in Card params have changed. Was: nil Is Now: #{349 324}
   ```
   Emitted for all 10 question cards. The redeploy rewrote SQL to use proper dimension template tags:
   ```sql
   [[AND {{date_range}}]]   -- CORRECT
   [[AND {{channel}}]]      -- CORRECT
   ```
   After this, Metabase bound field 324 (`posting_date`) and 349 (`channel_name`) to the dashboard parameters.

5. **After fix:** All dashcard queries return `202 completed` with no WARNs for field ID lookup. Filter binding confirmed working.

**Classification:** Filter binding failure (wrong template tag syntax in native SQL queries).

---

### RC-2 (SECONDARY): `Total Revenue` scalar card hides MoM%/YoY% comparison columns

Card 1102 returns 5 columns: `[Doanh thu, Ky truoc, Cung ky nam truoc, MoM %, YoY %]`. Display type = `scalar`. Metabase scalar renders **only col[0]** — `MoM %` and `YoY %` are silently hidden. This is by design from commit `71e4020` which reverted these cards from `table` (which showed all 5 cols with green/red formatting) to `scalar` to avoid the Metabase v0.60 SmartScalar "Group only by a time field" error.

Additionally, `prev_period` in the Total Revenue SQL uses a **hardcoded 3-month lookback** that overlaps with the `past3months` default filter → `MoM % = 2475.3%` (nonsensical). This is noted in the SQL comment but not surfaced to the user.

**Classification:** Visualization setting + SQL design issue (comparison columns invisible; period comparison logic conflicts with filter default).

---

### RC-3 (ELIMINATED): Schema drift / DuckDB lock / column rename

- `int_misa_sales_lines` exists in DB 2 (Sapo), table_id=60, 36 columns confirmed.
- All referenced columns (`posting_date`, `channel_name`, `gross_profit`, `revenue_net_of_discount`, `cogs_amount`, `product_name`, `is_promo_line`) present.
- Field IDs 324 (posting_date) and 349 (channel_name) confirmed correct.
- DuckDB connections: `0/5 (0 threads blocked)` — no lock contention.
- **Eliminated.**

---

### RC-4 (ELIMINATED): Dashboard or cards archived / permissions issue

- Dashboard 33: `archived: false`, `collection_id: 46` (Executive).
- All 12 question cards: `archived: false`.
- Metabase health: `status: ok`, version `v0.60.2`.
- **Eliminated.**

---

## 3. Layout Assessment

### Tab 1: Channel Overview — current grid

```
row  0-1:  [══════ Chu kỳ báo cáo ══════] (18×2)
row  2-3:  [══════ Bối cảnh mùa vụ + Caveat (dense text) ══════] (18×2)  ← disrupts flow
row  4:    [══════ ## Heading: Biên lợi nhuận gộp ══════] (18×1)
row  5-8:  [Gauge 6×4][Revenue 6×4][COGS 3×4][GP 3×4]   ← 3×4 too narrow
row  9:    [══════ ## Heading: So sánh kênh ══════] (18×1)
row 10-15: [Margin bar 9×6][Rev vs COGS bar 9×6]
row 99:    [══════ Source ══════] (18×1)
```

**Issues:**
1. `row 2-3` caveat/seasonal-context block sits between the period banner and KPIs — 4 rows of text before user sees any data.
2. `COGS` and `Gross Profit` at `size_x=3` are cramped — compact currency + VND may truncate.
3. `Total Revenue` shows only `Doanh thu` (scalar col[0]); `MoM %` (2475%) and `YoY %` invisible — misleading.

### Tab 2: Trends & Product Detail — current grid

```
row  0-1:  [══════ Chu kỳ báo cáo ══════] (18×2)
row  2:    [══════ ## Heading: Xu hướng ══════] (18×1)  ← immediate after period banner
row  3-8:  [Margin Trend 9×6][Revenue Mix 9×6]
row  9:    [══════ ## Heading: Sản phẩm ══════] (18×1)
row 10-18: [Top Products 9×9][Low-Margin table 9×9]  ← 9 rows tall = excessive scroll
row 99:    [══════ Source ══════] (18×1)
```

**Issues:**
1. Product charts at `size_y=9` (rows 10-18) make the page extremely tall; table scrolls separately within 9 rows.
2. No visual breathing room between period banner (row 0-1) and section heading (row 2).

---

## 4. Proposed Fix

### 4a. RC-1 — ALREADY FIXED

Commit chain `ad2b8a3` → `71e4020` → deployed at 14:58:43 today. All 10 question cards now use correct dimension template tags. No further SQL action needed.

### 4b. RC-2 — Recommended fix for Total Revenue card

Option A (simple): Change `display` from `scalar` back to `table` with `table.pivot: false` — shows all 5 columns with MoM%/YoY% visible. Requires accepting Metabase v0.60 SmartScalar won't be used (plain table is fine for a comparison row).

Option B (structural): Split into 2 cards — one scalar for `Doanh thu`, one standalone `row` chart for `MoM % / YoY %`. Cleaner but requires 2 new cards + layout space.

**Recommendation: Option A** — change display back to `table`, add `table.pivot: false`, restore color formatting for MoM%/YoY%. The commit `71e4020` confirmed `plain scalar` preserves currency settings, but `table` with a single-row result also renders fine and shows all columns.

### 4c. Layout Redesign

Proposed `metabase-pos` for all cards on both tabs (unified table):

#### Tab 1: Channel Overview

| dashcard | card | name | row | col | size_x | size_y | change |
|----------|------|------|-----|-----|--------|--------|--------|
| 2055 | 1441 | Chu kỳ báo cáo | 0 | 0 | 18 | 2 | same |
| 1552 | — | ## Biên lợi nhuận heading | 2 | 0 | 18 | 1 | moved up from row=4 |
| 1542 | 1101 | Gross Margin % | 3 | 0 | 6 | 4 | moved up from row=5 |
| 1543 | 1102 | Total Revenue | 3 | 6 | 6 | 4 | moved up from row=5 |
| 1544 | 1103 | Total COGS | 3 | 12 | 3 | 4 | moved up from row=5 |
| 1545 | 1104 | Total Gross Profit | 3 | 15 | 3 | 4 | moved up from row=5 |
| 1553 | — | ## So sánh kênh heading | 7 | 0 | 18 | 1 | moved up from row=9 |
| 1546 | 1105 | Margin by Channel | 8 | 0 | 9 | 6 | moved up from row=10 |
| 1547 | 1106 | Revenue vs COGS by Channel | 8 | 9 | 9 | 6 | moved up from row=10 |
| 3234 | — | Bối cảnh mùa vụ text | 97 | 0 | 18 | 2 | moved from row=2 to footnote |
| 2868 | — | Source & Freshness | 99 | 0 | 18 | 1 | same |

**Net effect:** Removes the 2-row text wall from between the period banner and KPIs. KPIs now at row=3 (directly after heading at row=2). Charts at row=8. Total visible height = 14 rows (down from 16).

#### Tab 2: Trends & Product Detail

| dashcard | card | name | row | col | size_x | size_y | change |
|----------|------|------|-----|-----|--------|--------|--------|
| 2869 | 1927 | Chu kỳ báo cáo | 0 | 0 | 18 | 2 | same |
| 1554 | — | ## Xu hướng heading | 2 | 0 | 18 | 1 | same |
| 1548 | 1107 | Margin Trend by Channel | 3 | 0 | 9 | 6 | same |
| 1549 | 1108 | Revenue Mix Trend | 3 | 9 | 9 | 6 | same |
| 1555 | — | ## Sản phẩm heading | 9 | 0 | 18 | 1 | same |
| 1550 | 1109 | Top Products by Profit | 10 | 0 | 9 | 7 | size_y 9→7 |
| 1551 | 1110 | Low-Margin Products | 10 | 9 | 9 | 7 | size_y 9→7 |
| 2870 | — | Source & Freshness | 99 | 0 | 18 | 1 | same |

**Net effect:** Product section height reduced from 9 to 7 rows — less scroll, table still shows ~10 rows comfortably at compact cell height.

---

## 5. Open Questions

1. **RC-2 Total Revenue display=table**: Before reverting, confirm the v0.60 SmartScalar "Group only by a time field" error does NOT trigger for single-row table display (it shouldn't, but should be verified before deploy).
2. **Bối cảnh mùa vụ text**: Moving to row=97 makes it a footnote — is this intended? If it should remain visible on load (without scrolling), keep at row=2 but reduce to `size_y=1` (collapsible text format).
3. **COGS / Gross Profit at size_x=3**: Compact currency (e.g. "16.6T VND") may still be readable but should be visually verified in browser — if values truncate, increase to `size_x=4` and reduce Revenue to `size_x=5`.
4. **Blueprint uncommitted changes** (`git diff HEAD` shows modified blueprint): the working tree has the correct fixed SQL but has NOT been committed. The deployed state IS the fixed state (from 14:58 redeploy). Blueprint file should be committed to align git state with Metabase.

---

**Status:** DONE_WITH_CONCERNS
**Summary:** Root cause confirmed — wrong template tag syntax (`posting_date >= {{date_range}}` instead of `[[AND {{date_range}}]]`) broke filter binding for all 10 question cards; this was fixed by the 14:58 redeploy today. Current backend is healthy. RC-2 concern: `Total Revenue` scalar card silently hides MoM%/YoY% columns — recommend reverting display to `table`. Layout redesign: move Bối cảnh text to footnote, shift KPIs up 2 rows, reduce product chart height from 9→7.
**Concerns:** (1) Blueprint working tree changes uncommitted. (2) Total Revenue comparison values invisible in scalar mode — user may still perceive this as "not displaying properly".
