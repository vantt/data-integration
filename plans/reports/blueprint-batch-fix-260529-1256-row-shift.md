# Blueprint Batch Fix — cycle-indicator row=0 conflict
**Date:** 2026-05-29
**Script:** `plans/fix-blueprint-row-shift.js`

## Root Cause
Blueprint files had CRLF line endings (`\r\n`). First script draft used `\n`-only regex for `metabase-pos` block matching — zero blocks found, no conflict detected. Fixed by making regex CRLF-aware (`\r?\n`).

## Algorithm Used

For each tab with `Chu kỳ báo cáo`:
1. Locate cycle-indicator `metabase-pos` block (first pos block after `#### ❓ Question: Chu kỳ báo cáo`, before next `####`)
2. Check if any OTHER pos block in the tab has `"row": 0`
3. If conflict → shift ALL non-cycle pos blocks:
   - `row == 0` → `2`
   - `1 ≤ row ≤ 89` → `row + 2`
   - `row ≥ 90` → unchanged (source-freshness pins at 99)
4. Cycle-indicator block left untouched

Blocks processed in reverse index order to preserve string offsets during in-place replacement.

## D44 Before/After Sample (ceo_monthly_scorecard.md — "Kenh & Khach hang")

**Before:**
```
cycle-indicator:  { "row": 0, "col": 0, "size_x": 18, "size_y": 2 }  ← UNTOUCHED
heading text:     { "row": 0, "col": 0, "size_x": 18, "size_y": 1 }  ← CONFLICT
heading text 2:   { "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
heading text 3:   { "row": 14, "col": 0, "size_x": 18, "size_y": 1 }
```

**After:**
```
cycle-indicator:  { "row": 0, "col": 0, "size_x": 18, "size_y": 2 }  ← UNTOUCHED
heading text:     { "row": 2, "col": 0, "size_x": 18, "size_y": 1 }  ← fixed (0→2)
heading text 2:   { "row": 9, "col": 0, "size_x": 18, "size_y": 1 }  ← shifted (7→9)
heading text 3:   { "row": 16, "col": 0, "size_x": 18, "size_y": 1 } ← shifted (14→16)
```

## Per-File Results

### Fixed (17 files)

| File | Tabs Fixed | Tabs |
|------|-----------|------|
| marketing_monthly_analysis.md | 4 | Channel & Brand, Customer Intelligence, Campaigns & Products, ROI & Margin |
| customer_retention_dashboard.md | 2 | Phan tich Cohort, Hanh vi & Reactivation |
| customer_intelligence_monthly.md | 2 | Value & Segmentation, Behavior & Insights |
| logistics_operations.md | 2 | Tốc độ xử lý, Chi tiết & Nhân viên |
| product_performance.md | 4 | Tong quan, Phan tich loai san pham, San pham ban chay & ban cham, Loi nhuan |
| sales_monthly_review.md | 4 | Hieu suat tai chinh, Dong luc tang truong, Suc khoe van hanh, P&L Hang Thang |
| shopee_channel_economics.md | 2 | Trends & Details, Shopee P&L Cascade |
| channel_profitability_monthly.md | 1 | Trends & Product Detail |
| finance_pl.md | 2 | Channel Profitability, Shopee Economics |
| ingestion_health.md | 2 | Volume & Trend, Failures & Detail |
| sales_daily_operation.md | 3 | Kênh bán hàng, Sản phẩm, Khách hàng & Thanh toán |
| sales_yesterday_operation.md | 4 | Tổng quan, Kênh bán hàng, Sản phẩm, Khách hàng & Thanh toán |
| ceo_monthly_scorecard.md | 2 | Kenh & Khach hang, San pham & Van hanh |
| sales_promotion_analysis.md | 2 | Hieu suat khuyen mai, Phan tich kenh & chi tiet |
| marketing_weekly_tracker.md | 3 | Hieu suat Kenh, Khach hang & Acquisition, Promotion & Social |
| customer_operational_dashboard.md | 2 | Kenh & Dia ly, Watchlist & Hanh dong |
| b2b_sales_daily.md | 2 | Tong quan, Chi tiet don hang |
| b2b_orders_tracking.md | 2 | Cong no, Giao hang |

### No Fix Needed / No Tabs (5 files)

| File | Reason |
|------|--------|
| sales_ops_weekly_review.md | No tab sections found |
| sales_ops_monthly_summary.md | No tab sections found |
| order_listing.md | No tab sections found |
| order_profitability_all.md | No tab sections found |
| ceo_monthly_scorecard.md | Already fixed in test pass (processed twice) |

## Verification

- Cycle-indicator `metabase-pos` blocks: all remain at `"row": 0` (verified spot-check on 5 files)
- Source-freshness pins `"row": 99`: untouched — no `"row": 101` found in any file
- CRLF line endings preserved in written files
