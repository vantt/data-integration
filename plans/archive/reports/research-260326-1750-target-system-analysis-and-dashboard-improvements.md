# Research Report: Target System Analysis & Dashboard Improvements

> **Date:** 2026-03-26 | **Scope:** `fact_targets` ingestion pipeline, `stg_targets`, `gsheet_targets.py`, and dashboard improvement opportunities

## Executive Summary

The target system has **3 critical issues** that make it unreliable for daily dashboard integration:

1. **staff_email field mismatch** — actual data has staff codes (`NV001`), not emails. The `fact_targets` JOIN on `dim_staff.email` will always fail.
2. **Only 3 sample rows from Jan-Feb 2024** — looks like test data, never updated since.
3. **Monthly grain only** — `setup_date` = first of month. No mechanism to pro-rate to daily.

Additionally, the currency bug (USD→VND) in both `sales_daily_operation` and `sales_yesterday_operation` blueprints has been **fixed**.

---

## Part 1: Currency Bug Fix (Done)

| File | Change |
|------|--------|
| `blueprints/sales_daily_operation.md` line 196 | `"USD"` → `"VND"` |
| `blueprints/sales_yesterday_operation.md` line 228 | `"USD"` → `"VND"` |

All other blueprint files already used VND correctly.

---

## Part 2: Target System Deep Analysis

### Current Architecture

```
Google Sheet (manual) → gsheet_targets.py → Parquet → stg_targets → fact_targets
```

### Data Schema (Google Sheet → Parquet)

| Column | Type | Purpose | Actual Data |
|--------|------|---------|-------------|
| `setup_date` | date | Target period (1st of month) | `2024-01-01`, `2024-02-01` |
| `branch_code` | string | Store/branch identifier | `ST01`, `ST02` |
| `team_code` | string | Team grouping | Always `NaN` |
| `staff_email` | string | Staff identifier | `NV001`, `NaN`, `None` |
| `sales_channel` | string | Channel filter | Always `NaN` |
| `product_sku` | string | Product filter | Always `NaN` |
| `metric_code` | string | What's being targeted | `gmv`, `profit` |
| `target_value` | decimal | Target amount | `100M`, `20M`, `50M` VND |
| `description` | string | Human label | Vietnamese descriptions |

### Actual Data (All 3 rows)

| setup_date | branch | staff | metric | target_value | description |
|-----------|--------|-------|--------|-------------|-------------|
| 2024-01-01 | ST01 | - | gmv | 100,000,000 | Mục tiêu tháng 1 |
| 2024-01-01 | ST01 | NV001 | gmv | 20,000,000 | Mục tiêu cá nhân NV001 |
| 2024-02-01 | ST02 | - | profit | 50,000,000 | Store 2 Profit |

### Issues Found

#### Issue 1: `staff_email` JOIN is Broken (Critical)

**`stg_targets.sql` line 18:**
```sql
coalesce(nullif(trim(cast(staff_email as string)), ''), 'ALL') as staff_email
```

**`fact_targets.sql` line 41:**
```sql
LEFT JOIN dim_staff st ON s.staff_email = st.email
```

**Problem:** Actual data has `NV001` (a staff code), not an email address. The JOIN to `dim_staff` uses `email` field — this will **never match** `NV001`.

**Fix options:**
- **Option A (Recommended):** Rename column in Google Sheet to `staff_identifier` and JOIN on either `st.email` OR `st.staff_code` (needs to check what `dim_staff` exposes)
- **Option B:** Require actual emails in the Sheet and enforce validation in `gsheet_targets.py`

#### Issue 2: Monthly Grain, No Daily Pro-rating

`setup_date` is always the 1st of the month. `target_code` concatenates `YYYYMM`. There's no mechanism to:
- Set daily targets
- Automatically divide monthly target by business days
- Track cumulative progress within the month

**For daily dashboards**, you'd need either:
- **Option A (Simple):** Pro-rate: `daily_target = monthly_target / days_in_month`
- **Option B (Better):** Pro-rate by business days: `daily_target = monthly_target / business_days_in_month`
- **Option C (Best):** Allow daily rows in Google Sheet (one row per day per metric)

#### Issue 3: Unused Dimensions

`team_code`, `sales_channel`, `product_sku` columns exist in schema but are always `NaN`. The flexibility is there but not used. Not a bug — but the model complexity is wasted.

#### Issue 4: No Automated Ingestion

`gsheet_targets.py` is a standalone script, not integrated into the Dagster orchestration pipeline. Must be run manually. If targets change in Google Sheet, data won't refresh until someone runs the script.

#### Issue 5: No Validation

No checks for:
- Duplicate targets (same month/branch/staff/metric)
- Missing required fields
- Reasonable target values (negative? zero? billions?)
- Valid `metric_code` values (could be anything)

---

## Part 3: Dashboard Improvement Recommendations (Updated)

Based on previous research report + target system findings:

### Priority Matrix

| # | Improvement | Dashboard | Effort | Impact | Depends On |
|---|------------|-----------|--------|--------|------------|
| 1 | Add Net Revenue, Returns, Discount Impact to Daily | Daily | Low | High | Nothing |
| 2 | Add Revenue by Customer Segment (VIP/Loyal/Regular) | Both | Low | High | Nothing |
| 3 | Replace "New vs Returning" with 4-way split | Both | Low | High | Nothing |
| 4 | Add Order Status Health (cancelled/fulfilled breakdown) | Both | Low | High | Nothing |
| 5 | Add Staff Performance table | Both | Low | Medium | Nothing |
| 6 | Add Store/Location comparison | Both | Low | Medium | Nothing |
| 7 | Add MTD Target Achievement gauge | Both | Medium | High | Fix Issue 1+2 first |
| 8 | Add Geographic breakdown (Top provinces) | Both | Low | Medium | Nothing |
| 9 | Add Time-to-Fulfill metric | Yesterday | Low | Medium | Nothing |

Items 1-6 and 8-9 can proceed immediately — no target system fixes needed.
Item 7 is blocked until target system issues are resolved.

### Target System Fix Plan (for Item 7)

**Step 1:** Fix `staff_email` JOIN
- Check `dim_staff` for available identifiers
- Update `fact_targets` JOIN logic or Sheet column

**Step 2:** Add pro-rating logic
```sql
-- In a new Metabase model or dbt mart
WITH monthly_targets AS (
    SELECT
        date_trunc('month', target_date) as month_start,
        branch_key,
        SUM(target_val) as monthly_target
    FROM fact_targets
    WHERE metric_code = 'gmv'
    GROUP BY 1, 2
),
days_in_month AS (
    SELECT
        month_start,
        branch_key,
        monthly_target,
        -- Count actual days in that month
        EXTRACT(DAY FROM (month_start + INTERVAL '1 month' - INTERVAL '1 day')) as total_days,
        monthly_target / EXTRACT(DAY FROM (month_start + INTERVAL '1 month' - INTERVAL '1 day')) as daily_target
    FROM monthly_targets
)
SELECT * FROM days_in_month
```

**Step 3:** Integrate `gsheet_targets.py` into Dagster pipeline (or add a cron job)

**Step 4:** Add fresh target data to Google Sheet (current data is from 2024)

---

## Opinions on Target Ingestion Approach

### What works well
- **Flexible schema** — supports branch, team, staff, channel, product granularity. Good for growth.
- **Google Sheets as source** — low-friction for business users to update targets.
- **Semantic key generation** (`TGT-YYYYMM-Branch-Team-Staff-Metric`) — readable and debuggable.

### What needs attention

1. **Google Sheet is fragile** — no schema validation, anyone can break the format. Consider:
   - Adding column validation in `gsheet_targets.py` before writing Parquet
   - Or using Google Sheets data validation rules on the Sheet itself

2. **Monthly grain is limiting** — for daily dashboards, you need daily visibility. Three approaches:

   | Approach | Pros | Cons |
   |----------|------|------|
   | **Pro-rate in SQL** | No Sheet changes, simple | Assumes uniform distribution |
   | **Daily rows in Sheet** | Accurate, flexible | Tedious to maintain 30+ rows/month |
   | **Monthly + weekday weights** | Accounts for weekend dips | Needs weight config somewhere |

   **Recommendation:** Start with pro-rate in SQL (simplest). If business needs finer control, graduate to weighted approach later. YAGNI.

3. **`metric_code` needs a controlled vocabulary** — currently freetext. At minimum document valid values: `gmv`, `profit`, `orders`, `new_customers`. Consider adding a `ref_metric_codes` seed table in dbt.

4. **Staff identification** — decide once: is it email or staff_code? Mixing both breaks JOINs. Recommend using `staff_email` (actual email) since `dim_staff` keys on email, or add a `staff_code` field to `dim_staff`.

---

## Unresolved Questions

1. **What staff identifier does the business actually use?** Email or staff code (NV001)? This determines how to fix the JOIN.
2. **Is `profit` metric meaningful?** Profit requires COGS data — does the pipeline have cost data? If not, `profit` targets can't be validated.
3. **Who maintains the Google Sheet?** Need to confirm ownership for data freshness.
4. **Are the 2024 targets just test data, or real historical data?** If real, they're 2+ years old and not useful for current dashboards.
5. **Does the business want daily or monthly target tracking in the daily dashboard?** Pro-rated daily vs. cumulative MTD progress — different UX.
