---
phase: 3
title: "Dual-Stream Supply Tracking"
status: done
priority: P1
dependencies: [1]
---

# Phase 3: Dual-Stream Supply Tracking

## Overview

Refactor `int_customer_sku_supply_tracking` để tách 2 luồng theo quyết định đã chốt với user:

- **`supply_stream = 'purchased'`**: khách đã TỪNG mua SKU đó thật (bất kỳ đơn nào, không cần cùng đơn với line tặng) → MỌI quantity (mua + tặng) cộng dồn vào `effective_supply_days` như logic hiện tại (không đổi hành vi cho nhóm này).
- **`supply_stream = 'gift_only'`**: khách CHƯA TỪNG mua SKU đó, chỉ toàn được tặng → track supply_days riêng, độc lập, KHÔNG trộn vào nhịp tái mua của luồng mua. Feed scenario `GIFT_TO_PURCHASE` ở Phase 4.

Đây là phase rủi ro cao nhất (đổi recursive CTE đang chạy production) — cần regression guard chặt: khách không có gift line nào phải cho kết quả **giống hệt** trước khi đổi.

> **Làm rõ phạm vi fix (post red-team, 3/3 reviewer flag)**: chỉ khách `gift_only` (chưa từng mua SKU đó) được tách khỏi nhịp tái mua. Khách `purchased` (đã từng mua, kể cả nếu SKU đó SAU ĐÓ được tặng thêm) **vẫn cộng dồn gift qty vào `effective_supply_days` y hệt hôm nay** — đây là hành vi giữ nguyên có chủ đích (user case a), KHÔNG phải phần bug chưa fix xong. Đừng báo cáo phase này là "đã fix bug gift-inflate-supply" nói chung — chỉ đúng cho nhánh `gift_only`.

> **Tác động phụ đã xác nhận với user (Critical finding #2, red-team)**: khách `gift_only` HIỆN TẠI đang có action sống (`REORDER_*`/`USAGE_FOLLOWUP`, vì mart hiện tại không phân biệt gift) — sau khi đổi grain, các dòng này chuyển sang nhánh `gift_only` → `GIFT_TO_PURCHASE` (Phase 4), nhưng `GIFT_TO_PURCHASE` ship `enabled=false` ban đầu → action của nhóm khách này BIẾN MẤT khỏi CRM worklist tạm thời cho đến khi `GIFT_TO_PURCHASE` được review + enable. **Quyết định đã chốt**: chấp nhận khoảng trống tạm thời này, báo CS team TRƯỚC khi deploy (xem `plan.md` § Deploy Sequencing) — không tự động giữ REORDER_* cho nhóm này.

## Requirements

- Functional: output grain đổi từ `(customer_key, sku)` thành `(customer_key, sku, supply_stream)`.
- Non-functional: `supply_stream='purchased'` rows không được lệch so với baseline hiện tại (regression-free cho phần lớn dữ liệu, vì đa số customer×sku không có gift line).

## Architecture

```
raw_purchases (existing, both branches: direct + pack/alias)
         │
         │  + JOIN ever_purchased CTE (customer_key, sku đã từng có is_gift_line=FALSE)
         ▼
raw_purchases_classified
         │  supply_stream = CASE WHEN ever_purchased THEN 'purchased' ELSE 'gift_only' END
         │
         │  Note: nếu ever_purchased=TRUE, TẤT CẢ dòng (kể cả is_gift_line=TRUE) đi vào
         │  stream 'purchased' — giữ hành vi cộng dồn hiện tại. Nếu ever_purchased=FALSE,
         │  theo định nghĩa CHỈ có gift lines tồn tại cho (customer,sku) đó (không có gì
         │  khác để lẫn vào) — nên stream 'gift_only' chỉ chứa gift lines, tự nhiên.
         ▼
purchases_numbered / supply_stack (recursive CTE — GIỮ NGUYÊN logic,
         chỉ thêm supply_stream vào PARTITION BY / GROUP BY mọi nơi)
         ▼
last_order_ctx (giữ nguyên logic, thêm supply_stream vào GROUP BY/JOIN key)
         ▼
Final SELECT: grain (customer_key, sku, supply_stream)
```

## Related Code Files

- Modify: `transformation/models/marts/core/intermediate/int_customer_sku_supply_tracking.sql`
- Modify: `transformation/models/marts/core/intermediate/int_customer_sku_supply_tracking.yml` (grain doc, new column, tests)

## Implementation Steps

1. Add an `ever_purchased` CTE before `raw_purchases`:
   ```sql
   ever_purchased AS (
       SELECT DISTINCT fs.customer_key, cfg.sku
       FROM {{ ref('fact_sales') }}   fs
       JOIN {{ ref('dim_products') }} dp  ON fs.product_key = dp.product_key
       JOIN config                   cfg ON dp.sku          = cfg.sku
       JOIN {{ ref('fact_orders') }}  fo  ON fs.order_id    = fo.order_id
       WHERE fo.is_active_order = TRUE
         AND fs.is_gift_line = FALSE
       -- NOTE: direct-SKU branch only. Pack/alias purchases (Branch 2) also count as
       -- "ever purchased" for the base SKU — add a second UNION here mirroring the
       -- alias JOIN pattern from raw_purchases Branch 2 if pack purchases should count
       -- (recommended: yes, a pack purchase is still a real purchase of the base SKU).
   )
   ```
   Include the pack/alias branch (mirroring `raw_purchases` Branch 2's `dim_sku_alias` join) so a customer who bought the *packed* SKU counts as having purchased the *base* config SKU.

2. In `raw_purchases`, join `ever_purchased` and classify:
   ```sql
   raw_purchases AS (
       SELECT
           customer_key, sku, product_group, display_name,
           supply_days_per_unit, dose_reduction_buffer, remind_lead_days, journey_enabled,
           purchase_date,
           CASE WHEN ep.customer_key IS NOT NULL THEN 'purchased' ELSE 'gift_only' END AS supply_stream,
           SUM(qty) AS total_qty
       FROM ( /* existing Branch 1 + Branch 2 UNION ALL, unchanged */ ) raw
       LEFT JOIN ever_purchased ep
           ON raw.customer_key = ep.customer_key AND raw.sku = ep.sku
       GROUP BY
           customer_key, sku, product_group, display_name,
           supply_days_per_unit, dose_reduction_buffer, remind_lead_days, journey_enabled,
           purchase_date, supply_stream
   )
   ```
   Important: `supply_stream` must be a per-`(customer_key, sku)` constant (not per-row) — the `LEFT JOIN ever_purchased` correctly makes it constant since `ever_purchased` is a static per-customer-sku fact, not time-windowed (confirmed with user: no need for purchase-then-gift chronological ordering nuance).

3. Thread `supply_stream` through `purchases_numbered` (add to `PARTITION BY` for `ROW_NUMBER()`) and `supply_stack` (add to the recursive CTE's column list, `PARTITION BY`/join keys) — mechanical, both already key on `(customer_key, sku)`.

   **`last_order_ctx` needs explicit changes, not just "add to partition"** (post red-team, Assumption Destroyer Finding 7) — it is a SELF-CONTAINED CTE with its OWN independent Branch-1/Branch-2 UNION (mirroring `raw_purchases`, but not sharing its `supply_stream` classification) and its own `ROW_NUMBER() OVER (PARTITION BY customer_key, sku ORDER BY ordered_at DESC)`. It has no access to `ever_purchased` today. Required change: join `ever_purchased` INSIDE both of `last_order_ctx`'s UNION branches (same pattern as step 2), add `supply_stream` to its SELECT list, and change its `ROW_NUMBER() PARTITION BY` to `(customer_key, sku, supply_stream)` so `rn=1` is picked independently per stream:
   ```sql
   last_order_ctx AS (
       SELECT
           customer_key, sku, supply_stream, last_order_code,
           last_sku_discount_rate, last_net_unit_price,
           ROW_NUMBER() OVER (PARTITION BY customer_key, sku, supply_stream ORDER BY ordered_at DESC) AS rn
       FROM (
           -- Branch 1 (existing), + join ever_purchased ep, + supply_stream classification:
           SELECT
               fs.customer_key, cfg.sku,
               CASE WHEN ep.customer_key IS NOT NULL THEN 'purchased' ELSE 'gift_only' END AS supply_stream,
               fo.order_code AS last_order_code,
               /* existing last_sku_discount_rate / last_net_unit_price CASE expressions, unchanged */
               fs.ordered_at
           FROM {{ ref('fact_sales') }}   fs
           JOIN {{ ref('dim_products') }} dp  ON fs.product_key = dp.product_key
           JOIN config                   cfg ON dp.sku          = cfg.sku
           JOIN {{ ref('fact_orders') }}  fo  ON fs.order_id    = fo.order_id
           LEFT JOIN ever_purchased ep ON fs.customer_key = ep.customer_key AND cfg.sku = ep.sku
           WHERE fo.is_active_order = TRUE

           UNION ALL

           -- Branch 2 (existing pack/alias), same ever_purchased join pattern
           SELECT
               fs.customer_key, cfg.sku,
               CASE WHEN ep.customer_key IS NOT NULL THEN 'purchased' ELSE 'gift_only' END AS supply_stream,
               fo.order_code AS last_order_code,
               /* existing last_sku_discount_rate / last_net_unit_price CASE expressions, unchanged */
               fs.ordered_at
           FROM {{ ref('fact_sales') }}    fs
           JOIN {{ ref('dim_products') }}  dp  ON fs.product_key  = dp.product_key
           JOIN {{ ref('dim_sku_alias') }} da  ON dp.sku          = da.sapo_pack_sku
           JOIN config                    cfg ON da.sapo_base_sku = cfg.sku
           JOIN {{ ref('fact_orders') }}   fo  ON fs.order_id     = fo.order_id
           LEFT JOIN ever_purchased ep ON fs.customer_key = ep.customer_key AND cfg.sku = ep.sku
           WHERE fo.is_active_order = TRUE
             AND dp.sku NOT IN (SELECT sku FROM config)
             AND da.sapo_pack_sku != da.sapo_base_sku
       )
   )
   ```
   Then join `last_order_ctx` into the final SELECT on `(customer_key, sku, supply_stream)` instead of `(customer_key, sku)`.

4. Final SELECT: add `s.supply_stream` to the output column list and to the `LEFT JOIN last_order_ctx` condition and `QUALIFY` clause (`PARTITION BY s.customer_key, s.sku, s.supply_stream`).

5. Update `.yml` doc: grain becomes `(customer_key, sku, supply_stream)`, document `supply_stream` values and the "ever purchased = static per-customer-sku fact, not chronological" decision explicitly (avoid future confusion).

6. **Regression test — broadened after red-team** (Failure Mode Analyst Finding 6: the original version below only checked `estimated_depletion_date` for customers with NO gift-line history — a population that structurally CANNOT change under the new logic, so the test would pass even if the refactor were broken). Take a snapshot of current `int_customer_sku_supply_tracking` output BEFORE this change (export to parquet/CSV), then run ALL of the following:

   ```sql
   -- (a) Narrow check (kept, but insufficient alone): zero-gift-history customers unchanged
   SELECT old.customer_key, old.sku, old.estimated_depletion_date, new.estimated_depletion_date
   FROM old_snapshot old
   JOIN new_output new
     ON old.customer_key = new.customer_key AND old.sku = new.sku AND new.supply_stream = 'purchased'
   WHERE old.estimated_depletion_date != new.estimated_depletion_date
   -- Expect 0 rows

   -- (b) REQUIRED: total row-count parity check — every (customer_key, sku) pair that
   -- existed before must still exist after (as exactly one of purchased/gift_only), no
   -- silent drops from a join bug (e.g. an incomplete ever_purchased pack/alias branch):
   SELECT COUNT(*) FROM old_snapshot old
   LEFT JOIN new_output new ON old.customer_key = new.customer_key AND old.sku = new.sku
   WHERE new.customer_key IS NULL
   -- Expect 0 rows

   -- (c) REQUIRED: for customers WITH gift-line history who ARE also ever_purchased,
   -- estimated_depletion_date must be UNCHANGED too (per the "purchased stream keeps
   -- accumulating gift qty" decision — this is the population the narrow check (a) skips
   -- entirely; it must be verified, not assumed):
   SELECT old.customer_key, old.sku, old.estimated_depletion_date, new.estimated_depletion_date
   FROM old_snapshot old
   JOIN new_output new
     ON old.customer_key = new.customer_key AND old.sku = new.sku AND new.supply_stream = 'purchased'
   JOIN (SELECT DISTINCT customer_key, sku FROM fact_sales_with_gift_flag WHERE is_gift_line) g
     ON old.customer_key = g.customer_key AND old.sku = g.sku
   WHERE old.estimated_depletion_date != new.estimated_depletion_date
   -- Expect 0 rows

   -- (d) REQUIRED — HARD GATE (confirmed in validation session 2026-07-08): quantify the
   -- gift_only population and its overlap with OPEN, CLAIMED CRM tasks BEFORE deploy.
   -- If this count is > 0, DO NOT PROCEED with deploy — a rep is actively working one of
   -- these accounts and would be orphaned mid-workflow. Resolve those specific tasks first
   -- (let the rep finish / reassign) before re-running this check. The broader "gift-only
   -- customers lose their live action temporarily" gap (no open task) is NOT gated — that
   -- population is reported to CS per plan.md § Deploy Sequencing but does not block deploy.
   -- Run against CRM cache.db:
   SELECT COUNT(*)
   FROM wh_sku_action_queue q
   JOIN crm_task t ON t.source_ref = q.action_id AND t.status IN ('open', 'doing')
   WHERE (q.customer_key, q.sku) IN (
       -- (customer_key, sku) pairs whose supply_stream will become 'gift_only' post-deploy
       SELECT customer_key, sku FROM new_output WHERE supply_stream = 'gift_only'
   )
   -- Expect / gate: 0 rows. If > 0, STOP — do not proceed to reverse-ETL resume (Phase 5 step 9).
   ```

## Success Criteria

- [x] Output grain is `(customer_key, sku, supply_stream)`, `supply_stream ∈ {'purchased', 'gift_only'}`
- [x] Regression check (a): zero `estimated_depletion_date` changes for customer×SKU pairs with no gift-line history — 0 rows
- [x] Regression check (b): zero silently-dropped `(customer_key, sku)` pairs vs. pre-change snapshot — 0 rows
- [x] Regression check (c): zero `estimated_depletion_date` changes for `purchased`-stream customers WHO DO have gift-line history (the population the narrow check alone would miss) — 0 rows (699-pair population)
- [x] Regression check (d) — HARD GATE: gift_only population size + open-CRM-task overlap quantified before deploy; count of `gift_only`-reclassified rows with an OPEN/CLAIMED `crm_task` is exactly 0 (deploy blocks otherwise); broader gift_only population (no open task) is reported to CS per plan.md § Deploy Sequencing but does not block — **result: 0** (2317 gift_only pairs, 1087 overlapping wh_sku_action_queue rows, 0 overlapping an open/doing crm_task) — see `reports/phase-03-implementation-report.md`
- [x] New `gift_only` rows exist only where `ever_purchased` is false for that customer×SKU — true by construction (single `ever_purchased` CTE feeds the classification everywhere)
- [x] `last_order_ctx`'s two UNION branches both join `ever_purchased` and emit `supply_stream`; final join uses `(customer_key, sku, supply_stream)`
- [x] Recursive CTE still terminates correctly (no infinite recursion, same `rn`-based traversal logic per stream)
- [x] `dbt run --select int_customer_sku_supply_tracking` succeeds

## Risk Assessment

- **High risk**: this is a production recursive CTE feeding a live CRM action queue. A logic error could silently corrupt reorder timing for real customers.
- **Mitigation**: mandatory before/after snapshot diff (step 6, all 4 checks a-d) before this ships to Phase 4/5. Do not proceed to Phase 4 until ALL FOUR regression checks are clean — not just check (a), which is structurally incapable of catching most real defects (see step 6 note).
- **Mitigation**: keep the recursive CTE structure itself untouched — only add `supply_stream` to grouping/partition keys, don't alter the `GREATEST(purchase_date, depletion_date) + effective_supply` stacking formula.
- **Deploy ordering (post red-team — see `plan.md` § Deploy Sequencing for the full runbook)**: Phase 3 alone breaks `mart_customer_sku_action_queue` (Phase 4's consumer) — Phase 3+4 dbt changes land in the same commit/deploy, but the CRM reverse-ETL cron MUST be paused until the regression diff (step 6) is verified clean, because reverse-ETL mutates CRM action-state (`action_id`, `pending_since`, dismissals, open tasks) in a way that a warehouse-side rollback cannot undo. Do not resume reverse-ETL on a dirty diff.
- **Accepted behavior (user decision, not a defect)**: when a `gift_only` customer places their first real purchase of that SKU, `supply_stream` flips to `purchased`, which changes `action_type` and therefore `action_id` (`md5(customer_key|sku|action_type|pending_since)`) — any prior `GIFT_TO_PURCHASE` dismissal/snooze for that customer×SKU does NOT carry over to the new `REORDER_*` action. This is intentional: a gift→purchase transition is itself a meaningful event that warrants a fresh card, not a continuation of the old context.
