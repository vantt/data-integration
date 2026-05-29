# Dashboard 33 — Post-Deploy Bug Report

**Date:** 2026-05-29  
**Dashboard:** Channel Profitability Monthly [Cross] (id=33)  
**Blueprint:** `docs/analytics-handbook/blueprints/channel_profitability_monthly.md`

---

## Summary

Both symptoms share a single root cause: `DATE - BIGINT` is not a valid DuckDB operation. `DATE - DATE` returns `BIGINT` in DuckDB (not `INTEGER`), so the chained subtraction `p_start - (p_end - p_start) - 1` fails at the binder layer. This caused 4 cards to fail (1441, 1102, 1103, 1104). The fifth card (1927) is working correctly — its "wrong date range" is expected behavior from the `past3months` default filter.

---

## Symptom 1 — Card 1927 (Trends tab): "Wrong Date Range"

**Status: NOT A BUG — Expected behavior, but UX regression**

### Evidence

- Card 1927 SQL: `filter_bounds` + `[[AND {{date_range}}]]` — no arithmetic on dates, no type error.
- API execution with `past3months` → returns `02/02/2026 – 09/04/2026` (correct: MIN/MAX of data in Feb+Mar+Apr).
- `SELECT MIN(posting_date), MAX(posting_date) ... WHERE posting_date >= date_trunc('month', current_date) - INTERVAL '3 months' AND posting_date < date_trunc('month', current_date)` → returns same range.
- **Old behavior** (before deploy): card displayed a hardcoded string based on `current_date`:  
  `'📅 Tháng này: ' || strftime(date_trunc('month', current_date)::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') || '  ·  MoM: ' || ...`  
  This always showed the current month window regardless of filter selection.
- **New behavior**: shows `MIN/MAX(posting_date)` of filtered rows — so with `past3months` (3 closed months) it shows 02/02–09/04 instead of the MTD current-month window user was accustomed to.

### Root Cause

UX regression from design intent change, not a SQL error. The old card ignored the `date_range` filter and always showed current-month context. The new card obeys the filter. Since the dashboard default is `past3months` (closed months), the displayed range now shows the actual data boundary of the filter period, which ends at the last day with data in April.

### Fix Options

**Option A (keep filter-driven):** Acceptable — user must understand `past3months` = 3 closed months. No code change needed. Add a tooltip or update `card.title` to clarify.

**Option B (restore current-month display):** Revert card 1927 to the old hardcoded logic. But this makes the Trends tab cycle-indicator inconsistent with the filter control.

**Option C (preferred):** Change dashboard default from `past3months` to `past90days` or a date range that includes current partial month. Or update card 1927 to show the filter period label textually.

---

## Symptom 2 — Cards 1441, 1102, 1103, 1104 (Channel Overview): "No Data"

**Status: CONFIRMED BUG — DuckDB type error crashes all four cards**

### Error Message (from `/api/card/1102/query`)

```
Binder Error: No function matches the given name and argument types '-(DATE, BIGINT)'.
  Candidate functions: -(DATE, INTEGER) -> DATE

LINE 23: AND posting_date >= filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start) - 1
```

Same error confirmed on cards 1103, 1441 (tested), and 1104 by identical SQL pattern.

### Root Cause

DuckDB type resolution:
- `DATE - DATE` → returns `BIGINT` (not `INTEGER`)
- `DATE - BIGINT` → **no matching function** → Binder Error
- `DATE - INTEGER` → `DATE` (valid)

The expression `p_start - (p_end - p_start) - 1` fails because `(p_end - p_start)` is `BIGINT`, and then `p_start - BIGINT` has no overload.

Verified by API test:
```sql
WITH fb AS (SELECT '2026-02-01'::DATE AS p_start, '2026-04-30'::DATE AS p_end)
SELECT p_end - p_start AS diff, pg_typeof(p_end - p_start) AS diff_type
-- Result: diff=88, diff_type='bigint'
```

And the fix works:
```sql
SELECT p_start - (p_end - p_start)::INTEGER - 1 AS prev_start
-- Result: '2025-11-04' (correct)
```

### Affected Cards and Expressions

| Card | Name | Failing expression |
|------|------|--------------------|
| 1441 | Chu kỳ báo cáo (Channel Overview) | `(p_start - (p_end - p_start) - 1)::DATE` in SELECT |
| 1102 | Total Revenue | `posting_date >= filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start) - 1` |
| 1103 | Total COGS | same pattern |
| 1104 | Total Gross Profit | same pattern |

---

## Fix — Exact Diffs

### Pattern: cast the `DATE - DATE` result to INTEGER before using it

**Before:**
```sql
p_start - (p_end - p_start) - 1
```

**After:**
```sql
p_start - (p_end - p_start)::INTEGER - 1
```

Apply to all four occurrences in the blueprint and the four live cards.

### Blueprint fix (`channel_profitability_monthly.md`)

Three locations in the blueprint need the cast:

1. **Tab: Channel Overview → Chu kỳ báo cáo** (card 1441):
   ```sql
   -- before
   strftime((p_start - (p_end - p_start) - 1)::DATE, '%d/%m/%Y')
   -- after
   strftime((p_start - (p_end - p_start)::INTEGER - 1)::DATE, '%d/%m/%Y')
   ```

2. **Tab: Channel Overview → Total Revenue** (card 1102) `prev_period` CTE:
   ```sql
   -- before
   AND posting_date >= filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start) - 1
   -- after
   AND posting_date >= filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1
   ```

3. Same fix for **Total COGS** (card 1103) and **Total Gross Profit** (card 1104) — identical pattern in their `prev_period` CTEs.

---

## Parameter Mappings — Not the Issue

All five dashcards have correct `parameter_mappings` wired to `date_range` and `channel`. Dashboard parameters confirmed:
- `date_range`: `date/all-options`, `field_id=324`, default `past3months`
- `channel`: `string/=`, `field_id=349`

This was ruled out as a cause.

---

## Recurrence Prevention

**Design flaw:** DuckDB's `DATE - DATE = BIGINT` is not obvious (PostgreSQL returns `INTEGER`). Any blueprint that computes a prior-period window via `p_start - (p_end - p_start)` will silently fail.

**Recommendation:** Add a note to `.skills/metabase-automation/STRATEGY.md` or blueprint template:
> In DuckDB, `DATE - DATE` returns `BIGINT`, not `INTEGER`. Always cast before subtracting from a DATE: `(end_date - start_date)::INTEGER`.

---

## Unresolved Questions

1. Card 1927 "wrong date range" — is the user expecting MTD display or filter-bounded display? Needs UX decision (Option A/B/C above).
2. Are there other blueprints using `p_start - (p_end - p_start)` pattern that are also broken? (Quick grep across all blueprints recommended before closing.)
