---
title: "PLAN-004 P1 - Mart Match (engine core)"
status: deployed
priority: P2
parent: "PLAN-004"
stage: 5
created: 2026-06-20
---

# PLAN-004 P1 — Mart Match (engine core)

**Parent:** [PLAN-004](./PLAN-004-deadstock-customer-targeting-engine.md) · **Depends:** P0 (noise dọn xong).

> Cây cầu product→customer. 1 mart mới ghép **SKU ế/slow bán-được × khách từng mua đúng SKU**, gate tier eligible, enrich replenishment + discount-sensitivity, rank + reason fragments.

> **Scope sản phẩm — CHỐT (owner 2026-06-20, đóng open Q #3):** product spine = **own-brand Fine Japan Vietnam**, filter chính **`brand_code='FJV'`** (≈ `brand_name='Fine Japan Vietnam'`). Data justify: own-brand FJV slow/dead = **20 SKU / 81.1M capital**, gồm 2 SKU vốn lớn `VTST23023L001` (QUESTION 41.5M) + `VCST21003L001` (DOG 35.2M); giữ ~97% vốn + ~342/426 past-buyer của universe rộng → scope hẹp không hi sinh prize. **Data-quality caveat:** vài SKU own-brand có `brand_name=NULL` (vd prefix VCMC/VCSC/VCST) → dùng `brand_code='FJV'` (đầy đủ hơn brand_name); nhóm NULL-brand-FJV-prefix gần 0 vốn → ưu tiên thấp.

---

## Overview
- **Priority:** cao (lõi engine). **Owner:** Data. **Effort:** 2-3 ngày.
- **Status:** ✅ DEPLOYED (2026-06-21).
- Output: `mart_deadstock_target_queue` — grain **1 dòng / (product_key × customer_key)**, chỉ khách eligible từng mua SKU ế/slow.

> **Deploy 2026-06-21:** mart live = **498 rows / 4 FJV SKU / 414 khách**; grain (product_key,customer_key) UNIQUE; **17 dbt test PASS**; Dagster run `8f8c0f1a` SUCCESS (materialize 2 mart).
> **Đính chính số liệu vs spec (số live ĐÚNG):** thực tế **4 SKU / 83.1M capital** (KHÔNG phải ~20 SKU). ~16 SKU slow/dead còn lại bị loại đúng vì tồn kho/vốn = 0 (không có gì để thanh lý) + điều kiện past-buyer. 4 SKU GỒM 2 SKU vốn lớn `VTST23023L001` (41.5M) + `VCST21003L001` (35.2M).
> **Follow-up mở:** 4 SKU NULL-`brand_code` bị `brand_code='FJV'` bỏ sót (**6.85M**, chủ yếu `VCMC21010H001` Medicine 5.46M) — chờ owner fix brand_code source HOẶC fallback `brand_name='Fine Japan Vietnam'` + redeploy. Holdout live 23.5% (mục tiêu ~20%) — tune `% 20 < 4` nếu cần.
> **Bonus fix:** `schema.yml` sửa deprecation dbt 1.11 (`combination_of_columns`→nest `arguments:`).

## Key insights (ground từ probe live 2026-06-20)
- Match key = `fact_sales.product_key` × `customer_key` (line-grain, FK xác nhận tại `marts/schema.yml:468-522`). Filter COMPLETED qua `status_key='8f7afecbc8fbc4cd0f50a57d1172482e'` (dim_order_status).
- Universe slow/dead bán-được (scope FJV): `mart_product_health` WHERE `(is_dead_stock OR health_class IN ('DOG','QUESTION')) AND category NOT IN ('Vận Hành','Uncategorized') AND brand_code='FJV'`.
- Probe: 538 rows / 426 khách / 12 SKU; 333/426 replenishment-due; 419/426 voucher-gate-able (chỉ 7 FULL_PRICE).
- Enrich từ `dim_customers`: `next_purchase_signal`, `predicted_next_purchase_date`, `discount_sensitivity` (logic tại `dim_customers.sql:162-177`).
- Gate tier từ `mart_customer_tier` (tier logic tại `mart_customer_tier.sql:34-57`).

## Requirements

**Functional**
- 1 dòng per (SKU ế × khách eligible từng mua SKU đó).
- Loại SKU có 0 past-buyer (failed-launch → merchandising, không vào mart).
- Loại GRAVEYARD + NONBUYER (chỉ giữ 5 tier eligible).
- Rank trong mỗi SKU: replenishment-due > value; expose reason fragments.
- Cột routing channel: contactable→Hug, MASKED_REPEAT→Shopee.
- Cột `is_holdout` deterministic (cho P3 measurement).

**Non-functional**
- Thin, deterministic (đọc mart đã tính sẵn — KHÔNG re-join raw, theo pattern `mart_product_action_queue`).
- Parquet rolling location (`get_rolling_location()`), tag mart.
- Fail-fast nếu source column đổi (dbt ref guard).

## Architecture / data flow

```
mart_product_health (slow/dead universe, P0-cleaned categories)
        │  product_key, sku, category, health_class, is_dead_stock,
        │  dead_stock_value_at_risk, stock_value_at_mac, days_since_last_sale
        ▼
   [CTE slow_universe]  ── filter dead/DOG/QUESTION, exclude noise cat, brand_code='FJV', capital>0
        │
fact_sales (COMPLETED) ──► [CTE past_buyers] DISTINCT product_key × customer_key
        │                       (+ buyer-level qty/recency của đúng SKU cho rank)
        ▼ JOIN on product_key
   [CTE matched]
        │
mart_customer_tier ──► gate strategic_tier IN (5 eligible)  [JOIN customer_key]
        │
dim_customers ──► enrich next_purchase_signal, predicted_next_purchase_date,
        │          discount_sensitivity, value_group, full RFM  [JOIN customer_key]
        ▼
   [SELECT] rank, reason fragments, channel route, is_holdout
        ▼
   mart_deadstock_target_queue (grain SKU×customer)
```

## Output schema (đề xuất)

| Cột | Nguồn | Ghi chú |
|---|---|---|
| `product_key`, `sku`, `product_name`, `category`, `brand_code` | mart_product_health | SKU ế own-brand FJV (brand_code='FJV') |
| `health_class`, `is_dead_stock` | mart_product_health | DOG/QUESTION/dead |
| `dead_stock_value_at_risk`, `stock_value_at_mac` | mart_product_health | vốn kẹt SKU (cho threshold P3) |
| `days_since_last_sale` (product) | mart_product_health | độ ế SKU |
| `customer_key`, `full_name` | tier/dim | PII — không export git |
| `strategic_tier` | mart_customer_tier | 1 trong 5 eligible |
| `source_contact_quality` | mart_customer_tier | real/masked → routing |
| `next_purchase_signal`, `predicted_next_purchase_date` | dim_customers | replenishment-due |
| `discount_sensitivity` | dim_customers | gate voucher |
| `value_group`, `lifetime_value`, `recency_days`, `order_count` | dim/tier | rank + value |
| `buyer_sku_qty`, `buyer_sku_last_date` | fact_sales agg | từng mua bao nhiêu / lần cuối SKU này |
| `target_rank` | computed | rank trong SKU: due-status, value, recency |
| `route_channel` | computed | `HUG` nếu source_contact_quality='real'; `SHOPEE_NATIVE` nếu MASKED_REPEAT/masked |
| `voucher_eligible` | computed | discount_sensitivity IN ('PROMO_DEPENDENT','PROMO_MIXED') → true; FULL_PRICE → false (tránh ăn lãi) |
| `reason_fragment` | computed | vd "Từng mua VCST21003L001 ×2, đến nhịp tái mua (OVERDUE) — đẩy thanh lý" |
| `is_holdout` | computed | deterministic `abs(hash(customer_key||sku)) % 10 < 2` ≈ 20% holdout |
| `queue_generated_at` | current_timestamp | |

## Related code files
- **Create:** `transformation/models/marts/core/mart_deadstock_target_queue.sql`
- **Modify:** `transformation/models/marts/schema.yml` — entry mart mới (grain test `combination_of_columns: [product_key, customer_key]`, relationships product_key→dim_products, customer_key→dim_customers).
- **Read (ground, không sửa):** `mart_product_health.sql`, `fact_sales.sql`, `mart_customer_tier.sql`, `dim_customers.sql`.

## Implementation steps
1. CTE `slow_universe`: SELECT từ `mart_product_health` WHERE dead/DOG/QUESTION + noise-cat excluded + **`brand_code='FJV'`** (own-brand Fine Japan Vietnam, filter chính — đầy đủ hơn brand_name vì có SKU brand_name NULL) + (dead_stock_value_at_risk + stock_value_at_mac) > 0.
2. CTE `past_buyers`: từ `fact_sales` WHERE status_key=COMPLETED, GROUP BY product_key, customer_key → `buyer_sku_qty=SUM(quantity)`, `buyer_sku_last_date=MAX(date_key)`. (DISTINCT bridge.)
3. JOIN slow_universe × past_buyers ON product_key → loại SKU 0-buyer tự nhiên (INNER JOIN).
4. JOIN `mart_customer_tier` ON customer_key, WHERE strategic_tier IN (5 eligible) — gate.
5. JOIN `dim_customers` ON customer_key cho enrich columns.
6. Computed cols: `route_channel`, `voucher_eligible`, `is_holdout`, `reason_fragment`, `target_rank` (ROW_NUMBER OVER PARTITION BY product_key ORDER BY due-priority, value DESC, recency).
7. Config: tag mart, `location=get_rolling_location()`. Comment nghiệp vụ (không phase/finding ref).
8. **Coverage-check step (open Q #3 chốt: giới hạn FJV own-brand):** rà SKU own-brand bị `brand_code` NULL nhưng có vốn lớn (vd prefix VCMC/VCSC/VCST với brand_name NULL) — đảm bảo filter `brand_code='FJV'` không bỏ sót SKU FJV vốn đáng kể; nếu lộ SKU FJV vốn lớn ngoài filter → báo owner, tách item bổ sung. (Universe rộng ngoài FJV accept bỏ qua: FJV giữ ~97% vốn.)
9. **New node → reload manifest:** thêm model mới → restart container data_platform (manifest pre-parsed lúc startup) trước khi `dbt run`, else KeyError.
10. `dbt run --select mart_deadstock_target_queue` + `dbt test`.

## Todo
- [x] CTE slow_universe (noise-excluded, **brand_code='FJV'**, capital>0).
- [x] CTE past_buyers (COMPLETED, qty + last_date per SKU×cust).
- [x] INNER JOIN bridge + tier gate (5 eligible) + dim enrich.
- [x] Computed: route_channel, voucher_eligible, is_holdout, reason_fragment, target_rank. (holdout live 23.5% — follow-up tune `% 20 < 4` về ~20% nếu P3 cần.)
- [x] schema.yml entry + grain/relationships tests. (17 dbt test PASS; bonus fix deprecation dbt 1.11.)
- [x] Coverage-check: phát hiện 4 SKU FJV NULL-`brand_code` bị bỏ sót (6.85M, chủ yếu `VCMC21010H001` 5.46M) → **follow-up mở, chờ owner**.
- [x] Restart data_platform (new node) → `dbt run` + `dbt test`. (Dagster run `8f8c0f1a` SUCCESS.)
- [x] Verify counts live: **498 rows / 4 FJV SKU / 414 khách** (số live đúng; đính chính spec ~20 SKU → 4 SKU, lý do tồn kho/vốn=0 bị loại).

## Success criteria
- Mart tồn tại, grain (product_key, customer_key) unique (test pass).
- Counts khớp probe FJV-scoped trong dung sai (~20 SKU own-brand FJV; ~342 past-buyer; P0 dọn + FJV filter có thể đổi nhẹ universe).
- 0 SKU failed-launch (0-buyer) trong mart; 0 GRAVEYARD/NONBUYER.
- `voucher_eligible=false` cho FULL_PRICE; `route_channel` đúng theo contact quality.
- `is_holdout` ≈ 18-22% deterministic, ổn định qua các run.

## Risk assessment
| Risk | L×I | Mitigation |
|---|---|---|
| product_key surrogate mismatch giữa health/fact_sales | thấp×cao | cùng `generate_surrogate_key(product_id-variant_id)`; verify join cardinality probe (đã match 538 rows) |
| `brand_code='FJV'` filter bỏ sót SKU FJV own-brand brand_code NULL có vốn lớn | TB×TB | coverage-check step rà brand_code NULL + vốn lớn; brand_code đầy đủ hơn brand_name; nhóm NULL-FJV-prefix gần 0 vốn |
| fact_sales bao gồm dòng quà 0đ / line âm | TB×TB | net_revenue/quantity filter dương nếu cần; nhưng "từng mua" = đã sở hữu SKU → 0đ vẫn là tín hiệu affinity hợp lệ (giữ, KISS) |
| Multi-row blow-up nếu past_buyers không DISTINCT đúng grain | thấp×cao | GROUP BY product_key,customer_key đảm bảo 1 dòng/cặp |
| dim_customers incremental → enrich cột mới chưa backfill | thấp×TB | mart này đọc cột đã tồn tại (next_purchase_signal/discount_sensitivity đã live); không thêm cột dim |

## Security / PII
- Mart chứa PII (full_name, customer_key resolves to phone qua cache). **KHÔNG export ra git.** Tiêu thụ qua serving view/cache/dashboard.
- Rolling parquet nằm trong `app_data` (không tracked git) — ok.

## Next steps
→ P2 sync mart này → cache.db + route 2 kênh. P3 đọc vốn/holdout từ mart cho threshold + measurement.
