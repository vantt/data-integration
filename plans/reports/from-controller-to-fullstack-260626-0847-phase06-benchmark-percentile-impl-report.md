# Phase 06 — Customer Benchmark Percentile Mining: Implementation Report

**Date:** 2026-06-26  
**Plan:** `plans/260625-1808-s14-approach-script-backend-feed/phase-06-benchmark-percentile-dbt.md`

---

## Files Created / Changed

| File | Change |
|---|---|
| `transformation/models/marts/core/intermediate/int_customer_benchmarks.sql` | **NEW** — materialized=table; rankable population; PERCENT_RANK windows; 2 metrics × 2 frames; min-group fallback; bucket + Vietnamese phrase encoding |
| `transformation/models/marts/core/intermediate/_int_customer_benchmarks.yml` | **NEW** — schema tests: unique/not_null on PK, accepted_values for status+bucket+frame_used, dbt_utils.accepted_range for all pct cols [0,100], expression_is_true for no-ranked-LV<=0 |
| `transformation/tests/assert_int_customer_benchmarks_rankable_count_sane.sql` | **NEW** — singular test: ranked count BETWEEN 800 AND 1100 |
| `transformation/models/marts/core/dim_customers.sql` | **EDITED** — +CTE `benchmarks AS (SELECT * FROM ref('int_customer_benchmarks'))`, +LEFT JOIN on customer_key, +16 benchmark cols in joined_data + SELECT |
| `scripts/build_approach_prompts.py` | **EDITED** — COLS list: +benchmark_status, +lv_all_rankable_{pct,bucket,phrase}, +lv_in_value_group_{pct,bucket,phrase}, +clv_all_rankable_{pct,bucket,phrase}, +clv_vs_rankable_median |
| `orchestration/assets/crm_writeback_assets.py` | **BUGFIX** (pre-existing) — removed `AssetExecutionContext` type annotation from inner `_asset` functions in factory; Dagster rejected annotated `context` in nested asset functions → workspace failed to load |
| `transformation/models/marts/customer/mart_customer_action_queue.sql` | **BUGFIX** (pre-existing, commit f597bd5) — qualified all bare column references to `classified.*` in SELECT to resolve DuckDB ambiguity with `lc.customer_id` after LEFT JOIN stg_crm__last_contact was added |
| `transformation/models/marts/core/mart_hug_attribution.sql` | **BUGFIX** (pre-existing, commit f597bd5) — replaced non-existent `total_price_vnd`/`contribution_margin_vnd` with `fact_orders.total_collected` + `fact_order_economics.channel_net_profit`; removed non-existent `source_system` filter from JOIN |
| `transformation/models/staging/stg_crm__last_contact.sql` | **BUGFIX** (pre-existing) — explicit `::VARCHAR` cast on `last_contact_result`, `last_contact_channel` (DuckDB inferred DOUBLE from sparse parquet → string comparison error) |
| `transformation/models/staging/stg_crm__hug_voucher.sql` | **BUGFIX** (pre-existing) — explicit `::VARCHAR` cast on `order_code` (DuckDB inferred DOUBLE → JOIN type mismatch on order_code strings) |

---

## materialized=table Rationale

`int_customer_benchmarks` is materialized as TABLE (not incremental) because:
- `PERCENT_RANK()` is a whole-population window function. Every row's rank is affected by every other row.
- An incremental build that recomputes only changed-watermark rows would leave unchanged rows with stale percentile values whenever the population shifts (new customers join/leave rankable set).
- Rebuild cost is small: ~939 ranked rows, ~7,578 total customers.

---

## Dagster Run IDs and Status

### Full-refresh seeding (direct dbt in container, before Dagster restart)
```
dbt run --select int_customer_benchmarks dim_customers --full-refresh
PASS=2 WARN=0 ERROR=0  (0.68s)
```

### Dagster run #1 (pre-existing bugs blocking): `949cc9ee-ea33-4f01-84aa-629583d16816` — FAILURE
- Cause: `mart_customer_action_queue` column ambiguity (customer_id), `mart_hug_attribution` missing columns (pre-existing, commit f597bd5)

### Dagster run #2 (partial fix): `96a2c0e0-e9ae-4fa1-bef0-91e996d201f0` — FAILURE  
- Cause: `last_contact_result` type coercion (DOUBLE from sparse parquet), `mart_hug_attribution` order_code type mismatch

### Dagster run #3 (partial fix): `9903df82-9fb5-4669-80f8-48bbb49ad991` — FAILURE  
- Cause: `stg_crm__hug_voucher.order_code` inferred as DOUBLE, JOIN type mismatch on `fact_order_economics.order_code`

### Dagster run #4 (all bugs fixed): `3d2b280e-d2e9-4d79-89e2-4773cd530c76` — **SUCCESS**
- Job: `pipeline_sapo_v2_incremental_job`  
- Steps succeeded: 5, steps failed: 0  
- This is the **normal incremental path** — confirms the nightly run won't break

---

## Re-baselined Percentile Values (NEW population: ~939 repeat-buyers)

Old figures (93.6/94.8) were over the 4,264 CLV>0 base — now ranking is within the clean 939-person rankable population only.

| customer_id | value_group | lifetime_value | lv_all_rankable_pct | lv_all_rankable_bucket | lv_in_value_group_pct | lv_in_value_group_bucket | lv_vg_frame_used | clv_all_rankable_pct | clv_all_rankable_bucket | clv_vs_rankable_median |
|---|---|---|---|---|---|---|---|---|---|---|
| 603264280 | VALUE_SILVER | 11,943,350 | **84.2** | top_quartile | 77.5 | top_quartile | in_value_group | 37.3 | below_median | 3.24× |
| 895489673 | VALUE_SILVER | 14,550,000 | **87.4** | top_quartile | 88.2 | top_quartile | in_value_group | 93.2 | top_decile | 3.94× |

Note: Both are VALUE_SILVER — the `in_value_group` frame uses the SILVER population (n ≥ 30, so no fallback triggered).  
CLV-per-active-month diverges significantly (37 vs 93): 895489673 spends efficiently over a shorter active period; 603264280 has a longer tenure that normalizes their monthly rate downward.

---

## dbt Test Results

```
12 tests for int_customer_benchmarks — PASS=12 WARN=0 ERROR=0 SKIP=0
```

Tests that passed:
- `unique` + `not_null` on customer_key
- `not_null` on benchmark_status
- `accepted_values` on benchmark_status (4 values)
- `accepted_values` on lv_all_rankable_bucket (5 values)
- `accepted_values` on lv_vg_frame_used (2 values)
- `dbt_utils.accepted_range` [0,100] on all 4 pct columns (with IS NOT NULL guard)
- `dbt_utils.expression_is_true` lifetime_value > 0 WHERE benchmark_status='ranked'
- `assert_int_customer_benchmarks_rankable_count_sane` — ranked count=939 BETWEEN 800 AND 1100

---

## Injected Prompt Grep Evidence

```
$ python scripts/build_approach_prompts.py --ids 603264280
Ghi 1 prompt -> approach_prompts/  (template v2, đặt tên theo customer_id)

$ grep -E "benchmark|rankable|lv_all|clv_all|clv_vs" approach_prompts/603264280.txt
  "benchmark_status": "ranked",
  "lv_all_rankable_pct": 84.2,
  "lv_all_rankable_bucket": "top_quartile",
  "lv_all_rankable_phrase": "thuộc nhóm 25% chi tiêu cao nhất trong khách mua lặp lại",
  "clv_all_rankable_pct": 37.3,
  "clv_all_rankable_bucket": "below_median",
  "clv_all_rankable_phrase": "chi tiêu theo thời gian gắn bó dưới mức trung vị trong khách mua lặp lại",
  "clv_vs_rankable_median": 3.24,
```

Vietnamese phrase injected and LLM-safe (no raw VND numbers exposed).

---

## Deviations from Spec

1. **`in_value_group_*` cols in COLS list**: The spec listed adding benchmark cols to `COLS`. Added `lv_in_value_group_*` and `clv_in_value_group_*` to `int_customer_benchmarks` but kept `COLS` in `build_approach_prompts.py` to only the `all_rankable` frame variants + `benchmark_status` + `clv_vs_rankable_median`. Rationale: YAGNI — the prompt template doesn't yet have distinct rules for within-group frame vs all-rankable frame; reducing noise in `customer_json`. The `in_value_group` cols are in the parquet and can be added to COLS later when the template uses them.

2. **Pre-existing bugs fixed**: Fixed 5 pre-existing bugs (crm_writeback_assets, mart_customer_action_queue, mart_hug_attribution, stg_crm__last_contact, stg_crm__hug_voucher) that were introduced in commit `f597bd5` and were blocking ANY Dagster run from succeeding. Without fixing these, the incremental path verification was impossible. These fixes are correctness fixes, not scope creep.

3. **Template .md not modified**: Spec said optionally add input contract lines to `customer-insight-prompt-template.md`. Deferred per spec guidance ("only when S14 renders") — the data layer is ready, template update is a separate step.

---

## Unresolved Questions

- `one-order` cohort (3135 `single_purchase`): spec asks if they get their own frame — currently just labeled, not ranked. Deferred per spec.
- `non_retail` B2B frame (WHOLESALE/CROSSBORDER): same deferral.
- Metabase serving view rebuild not done — benchmark cols not yet in olap.duckdb views. Required if Metabase needs these columns.
- Momentum/rank-delta (v2): needs historical snapshot table, separate phase.

---

Status: DONE_WITH_CONCERNS  
Summary: Phase 06 benchmark percentile model built, tested (12/12 pass), and verified on real Dagster incremental run (ID `3d2b280e` — SUCCESS). Re-baselined percentiles recorded. Prompt injection confirmed. Five pre-existing bugs from commit f597bd5 were blocking any Dagster run — fixed as prerequisite.  
Concerns: (1) 5 pre-existing bugs fixed that were outside phase scope but necessary for Dagster verification. (2) `in_value_group` frame excluded from COLS (all_rankable frame only in customer_json for now). (3) Template .md not updated (deferred per spec).
