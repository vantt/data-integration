---
phase: 2
title: "Blast-Radius Validation"
status: completed
priority: P1
dependencies: [1]
---

# Phase 2: Blast-Radius Validation

## Overview

Trước khi coi Phase 1 xong, đo lường quy mô thay đổi (bao nhiêu khách reclassify RETAIL→CROSSBORDER) và tác động lên các mart downstream đã xác định qua grep (retention/cohort/benchmark) — tránh dashboard/báo cáo bất ngờ khi số liệu đổi.

## Requirements

- Functional: quantify số khách bị reclassify, cross-check với `us-customers-260606.csv`.
- Functional: xác nhận các mart downstream re-run thành công với customer_type mới, không lỗi.
- Non-functional: không cần match 100% với CSV (CSV có thể cũ/không đầy đủ) — chỉ cần plausibility check, không phải acceptance gate cứng.

## Architecture

```
dim_customers (before snapshot, full-refresh Phase 1)
         │
         ▼  diff customer_type old vs new
Reclassified population (RETAIL → CROSSBORDER)
         │
         ├──► Cross-check vs us-customers-260606.csv (818 rows) — overlap %, not exact match
         │
         └──► Re-run + inspect downstream marts:
                mart_customer_action_queue, mart_customer_sku_action_queue,
                int_customer_benchmarks, int_customer_entry_attributes,
                mart_retention_waterfall_monthly, mart_cohort_retention,
                mart_customer_status_snapshot_monthly
```

## Related Code Files

- Read only: all 7 downstream consumer files listed above (verify each still runs, spot-check row-count deltas)
- Modify: `docs/context/order-customer-classification-staff-guide.md` mục 12 ("Chất lượng dữ liệu") — điền con số thật đã đo (Phase 1 mới cập nhật logic, chưa có số liệu vì lúc đó chưa full-refresh)
- No other code changes in this phase — validation only

## Implementation Steps

1. Before Phase 1's full-refresh, snapshot current `dim_customers.customer_type` distribution (export `customer_key, customer_type` to parquet/CSV).

2. After Phase 1's full-refresh, diff:
   ```sql
   SELECT old.customer_type AS old_type, new.customer_type AS new_type, COUNT(*)
   FROM old_snapshot old
   JOIN dim_customers new ON old.customer_key = new.customer_key
   WHERE old.customer_type != new.customer_type
   GROUP BY 1, 2
   ```
   Expect the overwhelming majority of changes to be `RETAIL → CROSSBORDER`. Any OTHER transition (e.g. `WHOLESALE → CROSSBORDER`) would indicate a CASE-branch-order bug — investigate before proceeding (per Phase 1's Unresolved Question #1, WHOLESALE should never be overridden by the channel signal).

3. Cross-check against `plans/reports/us-customers-260606.csv`:
   ```sql
   SELECT COUNT(*) AS csv_rows,
          COUNT(*) FILTER (WHERE new.customer_type = 'CROSSBORDER') AS now_crossborder,
          COUNT(*) FILTER (WHERE new.customer_type != 'CROSSBORDER') AS still_not_crossborder
   FROM read_csv('plans/reports/us-customers-260606.csv') csv
   LEFT JOIN dim_customers new ON csv.customer_id = TRY_CAST(new.customer_id AS INTEGER)
   ```
   Report `still_not_crossborder` rows for manual review (CSV customer with US order history but still not classified CROSSBORDER post-fix) — investigate a sample: likely means those customers' US orders are CANCELLED (excluded by design) or the CSV itself has stale/incorrect entries (per user's earlier stated intent to edit this CSV — do not treat CSV as ground truth, treat it as a sanity cross-check).

4. Re-run downstream marts and spot-check row-count deltas are sane (not zero, not wildly different from a normal daily run):
   ```bash
   dbt run --select mart_customer_action_queue mart_customer_sku_action_queue \
     int_customer_benchmarks int_customer_entry_attributes \
     mart_retention_waterfall_monthly mart_cohort_retention \
     mart_customer_status_snapshot_monthly
   ```

5. For `mart_customer_action_queue`/`mart_customer_sku_action_queue` specifically: confirm reclassified customers who move from RETAIL to CROSSBORDER now correctly DISAPPEAR from action-queue output (both marts filter `customer_type = 'RETAIL'`) — this is the actual fix payoff for the sibling plan (`260708-1501-gift-purchase-sku-action-scenario`).

6. Once the hard gate passes (Success Criteria below), cập nhật `docs/context/order-customer-classification-staff-guide.md` mục 12 — theo đúng pattern các dòng "ĐÃ XÁC NHẬN {ngày}" đã có (dòng ~309, ~313): thêm 1 dòng mới ghi ngày xác nhận (hôm chạy full-refresh), số khách reclassify RETAIL→CROSSBORDER thật đo được, và kết quả cross-check với `us-customers-260606.csv`. Đây là bước hoàn tất phần "số liệu" mà Phase 1 chưa điền được (Phase 1 chỉ cập nhật logic/SQL, chưa có số vì chưa full-refresh).

## Success Criteria

- [x] Before/after diff shows only `RETAIL → CROSSBORDER` transitions (no unexpected branch-order violations) — 773 rows, zero other transition types
- [x] **HARD GATE (confirmed in validation session 2026-07-08)**: reclassified count is a plausible order of magnitude vs. `us-customers-260606.csv`'s 818 rows (actual: 817) — specifically NOT >10x the CSV count and NOT near-zero. **PASSED**: 773 vs 817 — same order of magnitude. (An earlier run before a bug fix produced 6675 reclassifications — that WAS caught by this exact gate check and triggered the investigation/fix; see Phase 1 implementation note.)
- [x] All 7 downstream marts re-run without error
- [x] Reclassified customers confirmed absent from `mart_customer_action_queue`/`mart_customer_sku_action_queue` output post-refresh — verified 0/773 present in either mart
- [x] `docs/context/order-customer-classification-staff-guide.md` mục 12 điền số liệu thật đã đo (ngày + count reclassify + kết quả cross-check CSV) — 773 reclassified, 813/817 CSV match, 4 remaining WHOLESALE-by-design

## Risk Assessment

- **Low risk**: read-only validation phase, no code changes.
- **Risk**: if reclassified count is much larger than expected (e.g. thousands, not tens/hundreds), it could indicate the `channel_name = 'US'` join is too broad (e.g. matching unrelated orders) — this is now a HARD GATE (see Success Criteria), not just an informational flag: do not proceed to Phase 3 on an implausible count.
- Findings from this phase should be reported back to the user before Phase 3 proceeds, especially the `still_not_crossborder` CSV cross-check sample and the gate outcome.
