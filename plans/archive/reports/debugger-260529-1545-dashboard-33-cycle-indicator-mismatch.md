# RCA: Dashboard 33 — cycle-indicator period label mismatch

**Date:** 2026-05-29
**Dashboard:** `/dashboard/33` — Channel Profitability Monthly [Cross]

---

## Root Cause

The two "Chu kỳ báo cáo" scalar questions have **hardcoded date arithmetic** in their SQL that always computes relative to `current_date`, regardless of the Period filter value. The labels (`📅 Tháng trước` / `📅 Tháng này`) are string literals baked into the SQL — they never read from `{{date_range}}`.

**Evidence chain:**

1. **Blueprint SQL — Tab "Channel Overview" (card 1441):**
   ```sql
   SELECT '📅 Tháng trước: ' ||
     strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%d/%m/%Y') ...
   ```
   Hardcoded label `Tháng trước` + dates derived from `current_date` only.

2. **Blueprint SQL — Tab "Trends & Product Detail" (card 1927):**
   ```sql
   SELECT '📅 Tháng này: ' ||
     strftime(date_trunc('month', current_date)::DATE, '%d/%m/%Y') || ' – ' ||
     strftime(current_date, '%d/%m/%Y') ...
   ```
   Hardcoded label `Tháng này` + dates from `current_date` only.

3. **Live Metabase API confirms no `{{date_range}}` template tag in either card's SQL** — verified via `/api/card/1441` and `/api/card/1927`. Neither card has `{{date_range}}` or any parameter template tag.

4. **`parameter_mappings: []`** on both dashcards — confirmed via `/api/dashboard/33`. The Period filter is completely unwired from these two cards.

5. **Period filter is wired to other cards** (those with `[[AND {{date_range}}]]` in their SQL) — so the filter works for data questions but the cycle-indicator sits outside the wiring.

**Why the two tabs show different wrong labels:**
- "Channel Overview" was authored to show last month's range → hardcoded `Tháng trước`.
- "Trends & Product Detail" was authored to show current-month-to-date → hardcoded `Tháng này`.
- Neither was authored to respond to the filter; both are static display cards.

---

## Affected Widgets

| Tab | Card ID | Hardcoded label | Actual filter default |
|-----|---------|-----------------|----------------------|
| Channel Overview | 1441 | `📅 Tháng trước` (last month) | `past3months` |
| Trends & Product Detail | 1927 | `📅 Tháng này` (this month) | `past3months` |

---

## Fix Recommendation

### Option A — Make SQL respond to filter (correct fix, more work)

Replace hardcoded string literals and date arithmetic with a SQL expression that derives display text from the `{{date_range}}` parameter. Problem: DuckDB/Metabase native queries cannot easily compute human-readable period labels from the `date/all-options` filter value (it passes a string like `past3months` or a date range, not a computed date). This approach requires a CASE expression or a helper table.

**Simpler sub-option:** Remove the cycle-indicator question entirely for period-agnostic tabs, or replace it with a plain text card that says the report covers "the selected period" — no SQL needed, no mismatch possible.

### Option B — Fix label to match the actual data window (minimal fix)

Since every data question on both tabs hardcodes `date_trunc('month', current_date) - INTERVAL '3 months'` as the comparison window (see `prev_period` CTEs in Total Revenue, Total COGS, Total Gross Profit), the cycle-indicator should display that 3-month window, not `tháng trước` or `tháng này`.

**Blueprint fix for both tabs:**
```sql
SELECT
  '📅 3 tháng gần nhất: ' ||
  strftime((date_trunc('month', current_date) - INTERVAL '3 months')::DATE, '%d/%m/%Y') || ' – ' ||
  strftime((date_trunc('month', current_date) - INTERVAL '1 day')::DATE, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"
```

This is honest about what the data questions actually filter, and consistent whether the user changes the filter or not. The data questions themselves also use hardcoded windows (not filter-driven) for the comparison period — so this label is at least accurate.

### Option C — Add caveat text card (non-SQL, immediate)

Replace the scalar question with a `📝 Text` card:
```
📅 Kỳ báo cáo: theo bộ lọc "Period" phía trên
```
Zero SQL, always accurate, no deployment complexity.

**Recommended priority:** Option B is the fastest correct fix that requires only a blueprint edit + redeploy. Option C is zero-risk if you want to avoid SQL entirely.

---

## Recurrence Prevention

- **Design gap:** The blueprint template (`blueprint_template.md`) shows cycle-indicator SQL referencing `current_date` with no `{{date_range}}` tag. This pattern will recur in every blueprint that copies the template.
- **Monitoring gap:** The deploy script warns on row=0 conflicts but has no check for cycle-indicator cards lacking filter parameter_mappings.
- **Fix:** Update `blueprint_template.md` to use a label that either (a) wires to filter or (b) explicitly documents that the card is filter-independent and must match the data window.

---

## Unresolved Questions

1. The data questions (Total Revenue, Total COGS, etc.) also use hardcoded `INTERVAL '3 months'` windows for comparison, not `{{date_range}}`. If a user selects a different filter period (e.g. last month), the cycle-indicator label and the data will both be wrong. Is Option B acceptable as a permanent state, or should the data questions also be made filter-responsive?
2. Are there other blueprints/dashboards with the same cycle-indicator pattern that need the same fix?
