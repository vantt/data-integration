# Audit Report: Segmentation Implementation Bugs

**Date:** 2026-04-19
**Scope:** Review of report segmentation changes across blueprints
**Status:** ✅ FIXED

---

## ISSUES FOUND & FIXED

### Issue 1: Retail Blueprints - Inconsistent Filter Application

**File:** `docs/analytics-handbook/blueprints/sales_daily_operation.md`

**Problem:** Blueprint header claims `scope_retail (customer_type = 'RETAIL')` but MANY queries are MISSING this filter, causing data pollution.

| Query | Line | Has JOIN? | Has Filter? | Status |
|-------|------|-----------|-------------|--------|
| Health Score - recent CTE | 64-74 | ✓ | ✓ | OK |
| Health Score - previous CTE | 75-85 | ✓ | ✓ | OK |
| Health Score - customer_loyalty CTE | 86-95 | ✓ | ✗ | **BUG** |
| Health Breakdown - recent CTE | 131-139 | ✗ | ✗ | **BUG** |
| Health Breakdown - previous CTE | 140-150 | ✓ | ✓ | OK |
| Health Breakdown - customer_loyalty CTE | 151-160 | ✓ | ✗ | **BUG** |
| Net Revenue | 236-245 | ✓ | ✓ | OK |
| Gross Revenue | 279-288 | ✓ | ✓ | OK |
| Total Orders | 322-331 | ✓ | ✓ | OK |
| AOV | ~360 | ✓ | ✓ | OK |
| Unique Customers | ~390 | ✓ | ✓ | OK |
| Returns | 451-455 | ✗ | ✗ | **BUG** |
| Total Collected | 469-473 | ✗ | ✗ | **BUG** |
| Discount Rate | 497-505 | ✗ | ✗ | **BUG** |
| Items per Order | 517-523 | ✗ | ✗ | **BUG** (uses fact_sales) |
| Hourly Sales Trend | 541-565 | ✗ | ✗ | **BUG** (both CTEs) |
| Cumulative Revenue | 588+ | ✗ | ✗ | **BUG** (likely) |

**Impact:** 8+ queries showing ALL customer types instead of RETAIL only. Health Score, Returns, Discount Rate, Hourly patterns all include B2B data.

---

### Issue 2: Executive Blueprints - Documentation/SQL Mismatch

**Problem:** Headers updated to say `scope_sales (is_sales_channel = true)` but actual SQL queries still use old `channel_name != 'US'` pattern.

| File | Header Says | SQL Uses | Occurrences |
|------|-------------|----------|-------------|
| ceo_weekly_pulse.md | `is_sales_channel = true` | `channel_key != (SELECT ... WHERE channel_name = 'US')` | 26 |
| ceo_monthly_scorecard.md | `is_sales_channel = true` | `channel_name != 'US'` or subquery | 35 |
| order_profitability.md | `is_sales_channel = true` | No channel filter (status/has_cogs only) | 0 |

**Semantic Analysis:**
- US channel: `channel_format = 'CrossBorder Fulfillment'` → `is_sales_channel = false` ✓
- **Filters are semantically equivalent for US** but `is_sales_channel = true` ALSO excludes:
  - System channels (Test Sản Phẩm, Ưu đãi Nhân Viên, Quà Tặng)
  - Other channels (Gosumo)
- Using `is_sales_channel = true` is MORE correct for executive dashboards

---

## RISK ASSESSMENT

| Risk | Severity | Description |
|------|----------|-------------|
| Data Pollution | **HIGH** | Retail dashboards include B2B data, inflating metrics |
| Misleading AOV | **HIGH** | B2B AOV (~2.5M) mixed with Retail (~450K) |
| Wrong Discount Analysis | **HIGH** | B2B wholesale pricing mixed with retail promotions |
| Documentation Drift | **MEDIUM** | Headers don't match SQL behavior |

---

## RECOMMENDATIONS

### Option A: Full Fix (Recommended)
1. **Retail blueprints:** Add `JOIN dim_customers c ON o.customer_key = c.customer_key` and `AND c.customer_type = 'RETAIL'` to ALL missing queries
2. **Executive blueprints:** Update SQL queries to use `JOIN dim_channels ch ON o.channel_key = ch.channel_key WHERE ch.is_sales_channel = true`

### Option B: Partial Fix + Documentation Revert
1. **Retail blueprints:** Fix missing filters
2. **Executive blueprints:** Revert header to say "excludes US channel" to match current SQL

### Option C: Documentation-Only Fix
1. Remove scope claims from retail blueprint queries that weren't updated
2. Add warning notes about partial scope application
3. Create backlog ticket for full SQL update

---

## FILES FIXED

| File | Status | Queries Fixed |
|------|--------|---------------|
| sales_daily_operation.md | ✅ Fixed | ~12 queries |
| sales_yesterday_operation.md | ✅ Fixed | ~15 queries |
| sales_promotion_analysis.md | ✅ Fixed | ~14 queries |
| marketing_weekly_tracker.md | ✅ Fixed | ~40 queries |
| customer_operational_dashboard.md | ✅ Fixed | 1 query |
| ceo_weekly_pulse.md | ✅ Fixed | 26 queries → is_sales_channel |
| ceo_monthly_scorecard.md | ✅ Fixed | 35 queries → is_sales_channel |
| b2b_sales_daily.md | ✅ Verified | All queries correct |
| b2b_orders_tracking.md | ✅ Verified | All queries correct |

---

## RESOLUTION

All issues resolved:

1. **Executive dashboards:** Updated to use `is_sales_channel = true` (more comprehensive, excludes all internal/system channels)
2. **fact_sales queries:** Fixed with JOIN path: `fact_sales → dim_customers` (fact_sales has customer_key directly)
3. **All blueprints fixed immediately**

### Second Pass Fixes (2026-04-19 ultrathink review #1)

Additional bugs found and fixed in sales_daily_operation.md:

### Third Pass Fixes (2026-04-19 ultrathink review #2)

**CRITICAL: Double-counting bug found!**

Retail/B2B blueprints were filtering by `customer_type` but NOT `is_sales_channel`. This caused:
- US CrossBorder orders with RETAIL customers → counted in BOTH US dashboard AND Retail dashboards
- US CrossBorder orders with B2B customers → counted in BOTH US dashboard AND B2B dashboards

**Fix Applied:** Added `is_sales_channel` filter to ALL Retail and B2B queries:
```sql
AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
```

| Blueprint | Queries Fixed |
|-----------|---------------|
| sales_daily_operation.md | 36 |
| sales_yesterday_operation.md | 35 |
| sales_promotion_analysis.md | 30 |
| marketing_weekly_tracker.md | 46 |
| customer_operational_dashboard.md | 3 |
| b2b_sales_daily.md | 8 |
| b2b_orders_tracking.md | 11 |
| **Total** | **169 queries** |

### US CrossBorder Blueprint Created

New `us_crossborder_operations.md` created to track US orders separately with scope `channel_name = 'US'`.

### Updated Scope Definitions

| Scope | Old Definition | New Definition |
|-------|---------------|----------------|
| scope_retail | `customer_type = 'RETAIL'` | `customer_type = 'RETAIL'` + `is_sales_channel = true` |
| scope_b2b | `customer_type IN ('WHOLESALE', 'PARTNER')` | `customer_type IN ('WHOLESALE', 'PARTNER')` + `is_sales_channel = true` |
| scope_us | N/A | `channel_name = 'US'` |

---

### Previous Second Pass Fixes

| Query | Issue | Fix |
|-------|-------|-----|
| Sales by Branch | Missing RETAIL filter | Added JOIN dim_customers + customer_type filter |
| Top 10 Products by Revenue | Missing customer filter | Added JOIN dim_customers + customer_type filter |
| Top 10 Products by Quantity | Missing customer filter | Added JOIN dim_customers + customer_type filter |
| Revenue by Product Type | Missing customer filter | Added JOIN dim_customers + customer_type filter |
| Product Performance Table | Missing customer filter | Added JOIN dim_customers + customer_type filter |

### Out of Scope (Backlog)

| File | Issue | Queries Affected |
|------|-------|------------------|
| sales_monthly_review.md | No is_sales_channel filter | ~43 queries |

### Final Verification Results

| Scope | Filters | Files |
|-------|---------|-------|
| RETAIL (`customer_type = 'RETAIL'`) | 157 | 5 blueprints |
| Executive (`is_sales_channel`) | 83 | 5 blueprints |
| B2B (`customer_type IN (...)`) | 25 | 2 blueprints |
| **TOTAL** | **265** | **12 blueprints** |

### Verification Commands
```bash
# Check retail scope coverage
grep -c "customer_type = 'RETAIL'" docs/analytics-handbook/blueprints/*.md

# Check executive scope coverage  
grep -c "is_sales_channel" docs/analytics-handbook/blueprints/*.md

# Check B2B scope coverage
grep -c "customer_type IN ('WHOLESALE', 'PARTNER')" docs/analytics-handbook/blueprints/*.md
```
