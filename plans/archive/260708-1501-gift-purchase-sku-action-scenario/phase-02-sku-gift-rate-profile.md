---
phase: 2
title: "SKU Gift-Rate Profile"
status: pending
priority: P2
dependencies: [1]
---

# Phase 2: SKU Gift-Rate Profile

## Overview

Tính `gift_rate` per SKU (tỷ lệ line hàng tặng / tổng line) để phân biệt SKU chủ lực (anchor/premium, khách chủ động mua) vs SKU mồi/dễ bị tặng kèm (entry/gift-prone) — trả lời câu hỏi user đặt ra "làm sao phân biệt được". Đây là metric liên tục (derivable, không cần seed thủ công); nhãn phân loại categorical là optional convenience trên top.

## Requirements

- Functional: mỗi SKU trong `seed_sku_regimen_config` (8 core SKU) có `gift_rate` tính từ dữ liệu thật.
- Non-functional: dùng lại `is_gift_line` từ Phase 1, không tính lại logic gift riêng.

## Architecture

```
fact_sales (is_gift_line, sku via dim_products)
         │
         ▼
   [new] int_sku_gift_profile        -- hoặc thêm cột vào mart_product_health nếu phù hợp hơn
     sku, total_lines, gift_lines, gift_rate,
     sku_role (derived label, threshold-based)
```

Quyết định đặt ở đâu: **tạo intermediate model mới** `int_sku_gift_profile` thay vì nhét vào `mart_product_health` — giữ tách biệt vì `mart_product_health` phục vụ inventory/merchandising (ABC/health class), còn `gift_rate` phục vụ customer-outreach scenario (Phase 4 sẽ join vào action-queue). Tránh lẫn 2 concern khác nhau vào 1 mart (đúng tinh thần "existing module boundaries").

## Related Code Files

- Create: `transformation/models/marts/core/intermediate/int_sku_gift_profile.sql`
- Modify: `transformation/models/marts/schema.yml` (doc + tests for new model)

## Implementation Steps

1. Write `int_sku_gift_profile.sql`:
   ```sql
   WITH lines AS (
       SELECT
           dp.sku,
           fs.is_gift_line,
           -- Multi-SKU basket flag: per finejapan report, gift-rate differs sharply
           -- solo vs multi-SKU orders. Expose both for transparency.
           COUNT(*) OVER (PARTITION BY fs.order_id) > 1 AS is_multi_sku_basket
       FROM {{ ref('fact_sales') }} fs
       JOIN {{ ref('dim_products') }} dp ON fs.product_key = dp.product_key
       JOIN {{ ref('fact_orders') }} fo ON fs.order_id = fo.order_id
       WHERE fo.is_active_order = TRUE
   )
   SELECT
       sku,
       COUNT(*)                                              AS total_lines,
       COUNT(*) FILTER (WHERE is_gift_line)                  AS gift_lines,
       ROUND(COUNT(*) FILTER (WHERE is_gift_line)::DOUBLE / NULLIF(COUNT(*), 0), 4) AS gift_rate,
       COUNT(*) FILTER (WHERE is_multi_sku_basket)                                   AS multi_sku_lines,
       COUNT(*) FILTER (WHERE is_multi_sku_basket AND is_gift_line)                  AS multi_sku_gift_lines,
       ROUND(
           COUNT(*) FILTER (WHERE is_multi_sku_basket AND is_gift_line)::DOUBLE
           / NULLIF(COUNT(*) FILTER (WHERE is_multi_sku_basket), 0), 4
       )                                                      AS multi_sku_gift_rate
   FROM lines
   GROUP BY sku
   ```
   Grain: 1 row per SKU (not limited to the 8 core SKUs — compute for all, filter downstream where needed).

2. Add a derived `sku_role` label as a thin view or in the consuming mart (Phase 4), NOT baked into this table as a hardcoded threshold — expose `gift_rate`/`multi_sku_gift_rate` as the source of truth, let consumers apply their own threshold. (Rationale: avoid freezing a business threshold into a table column before it's been validated against all 8 core SKUs — open question #2 in plan.md.)

3. Validate against `finejapan-gift-entry-sku-zero-rev-260622-1720-report.md` known values as a sanity check:
   - Metabo: multi-SKU gift-rate ≈ 75-78% expected
   - Coix: multi-SKU gift-rate ≈ 67% expected
   - Shark/Natto/Cordyceps/Fucoidan: expected low (report doesn't give exact solo/multi split for these, but they're described as "not gifted" — expect near-0%)

4. Restart `data_platform` → `dbt run --select int_sku_gift_profile`.

## Success Criteria

- [ ] `int_sku_gift_profile` exists, 1 row per SKU, `gift_rate` + `multi_sku_gift_rate` populated
- [ ] Validation query matches finejapan report's known Metabo/Coix multi-SKU gift-rate values (within reasonable tolerance — data has moved since 2026-06-22 report date)
- [ ] Schema.yml documents `gift_rate` semantics and the deliberate absence of a hardcoded `sku_role` threshold
- [ ] No new column added to `mart_product_health` (kept out of inventory/merchandising concern)

## Risk Assessment

- **Low risk**: new read-only aggregation model, no impact on existing marts.
- **Risk**: `is_multi_sku_basket` window function over full `fact_sales` history — check query performance on full rolling window; if slow, consider limiting to a trailing period (e.g. last 12 months) matching how other marts window their calculations.
- Depends on Phase 1's `is_gift_line` being correct — do not start until Phase 1 verification query passes.
