---
title: "Customer Discount Tracking — Pipeline + dim_customers + CRM Sync"
description: "Extract line-item discount rate vào pipeline, thống nhất taxonomy 3 buckets, expose 6 customer-level discount metrics qua dim_customers và CRM cache."
status: pending
priority: P2
branch: "main"
tags: ["dbt", "discount", "dim_customers", "crm-sync"]
blockedBy: []
blocks: []
created: "2026-06-29T05:19:56.600Z"
createdBy: "ck:plan"
source: skill
---

# Customer Discount Tracking — Pipeline + dim_customers + CRM Sync

## Problem

Pipeline hiện tại chỉ classify discount từ `discount_items_json` (order-level). Field `order_items.discount_amount` (line-level) bị bỏ sót hoàn toàn:

- **49,323 lines / 31,890 orders** có line-item discount (59.58% lines)
- **8,332 orders** có *chỉ* line-item discount, không có `discount_items` → invisible trong `fact_order_costs`, không ảnh hưởng `max_discount_rate`, không vào customer metrics
- `fact_sales` có `discount_amount` nhưng không có `discount_rate` (chỉ có VND amount)
- `dim_customers` chỉ có `discount_sensitivity` (PROMO_DEPENDENT/MIXED/FULL_PRICE) và `discount_order_rate` (aggregate) — không có rate cụ thể per discount type

## Goal

Mỗi khách trong `dim_customers` có **8 fields** discount, đồng bộ vào CRM `wh_customer_insight`:

| Field | Nguồn | Ý nghĩa |
|---|---|---|
| `last_line_discount_rate` | `order_items.discount_amount` | Rate giảm trực tiếp trên sản phẩm gần nhất |
| `max_line_discount_rate` | `order_items.discount_amount` | Rate giảm sản phẩm cao nhất từ trước |
| `last_voucher_discount_rate` | discount_items (voucher_promotional) | Rate voucher khách chủ động dùng gần nhất |
| `max_voucher_discount_rate` | discount_items | Rate voucher cao nhất từ trước |
| `last_campaign_discount_rate` | discount_items (bundle + campaign + sampling_gift) | Rate KM merchant áp gần nhất |
| `max_campaign_discount_rate` | discount_items | Rate KM cao nhất từ trước |
| `last_negotiated_discount_rate` | discount_items (negotiated_* + wholesale_explicit + employee + overseas) | Rate thỏa thuận B2B gần nhất |
| `max_negotiated_discount_rate` | discount_items | Rate thỏa thuận B2B cao nhất |

## Unified Discount Taxonomy (4 buckets)

```
line_discount  ← order_items.discount_amount / (unit_price × quantity)
                 Giảm ghi trực tiếp trên dòng sản phẩm, không có reason/label

voucher        ← discount_items WHERE discount_type = 'voucher_promotional'
                 Khách CHỦ ĐỘNG dùng mã voucher

campaign       ← discount_items WHERE discount_type IN:
                 bundle, campaign, sampling_gift
                 Merchant CHỦ ĐỘNG áp: bundle deal, CTKM, tặng mẫu

negotiated     ← discount_items WHERE discount_type IN:
                 negotiated_micro, negotiated_standard, negotiated_deep,
                 wholesale_explicit, employee_internal, overseas
                 Thỏa thuận trực tiếp: đại lý, hợp đồng, nhân viên, khách US
```

> Phân biệt voucher vs campaign: voucher = khách chủ động → signal engagement; campaign = merchant áp → signal discount dependency.
> `overseas` ở negotiated vì là segment riêng (US gift-ship), không phải marketing promo.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Pipeline Extraction](./phase-01-pipeline-extraction.md) | Pending |
| 2 | [Customer Discount Metrics](./phase-02-customer-discount-metrics.md) | Pending |
| 3 | [dim_customers + CRM Sync](./phase-03-dim-customers-crm-sync.md) | Pending |

## File Ownership

| Phase | Files Modified |
|---|---|
| 1 | `std_order_items.sql`, `fact_sales.sql`, `fact_order_costs.sql`, `fact_orders.sql` |
| 2 | `int_customer_discount_metrics.sql` (NEW) |
| 3 | `dim_customers.sql`, `duckdb_reader.py`, `sqlite_upsert.py`, `cache_insight.py` |

## Key Constraints

- `dim_customers` is incremental — adding columns requires `--full-refresh` run via dbt CLI (lock-retry pattern per `feedback_dim_customers_incremental_full_refresh.md`)
- After `dim_customers` column change: stop Metabase → run `bootstrap_serving_views.py` → restart (per `feedback_duckdb_view_rebuild.md`)
- After CRM sync schema change: rebuild crm container (per `feedback_new_mart_crm_serving_integration.md`)
- Open DuckDB files with `read_only=True` always (per `feedback_duckdb_always_readonly.md`)

## Acceptance Criteria

- [ ] `fact_sales.discount_rate` computed and non-null where `discount_amount > 0`
- [ ] `fact_order_costs` has `discount_line_item` rows for orders with line-level discounts
- [ ] `fact_orders.max_line_discount_rate` populated (NEW column, not replacing `max_discount_rate`)
- [ ] `int_customer_discount_metrics` exists, computes 8 fields correctly
- [ ] `dim_customers` has 8 new discount fields
- [ ] CRM `wh_customer_insight` includes 8 fields, visible in customer 360 insight panel
- [ ] No double-counting between `line_discount` and `voucher`/`campaign`/`negotiated` buckets

## Dependencies

No cross-plan blockers. Runs independently on `main`.

## Unresolved Questions

1. Double-counting risk: 31,890 orders have BOTH `order_items.discount_amount` AND `discount_items` entries. For `price_reduction` rate, should we use ONLY orders where `distributed_discount_amount = 0` (purely item-level) or all orders with line discount? → **Recommendation:** include all — the two discounts are separate mechanisms and should be tracked independently.

2. `fact_orders.max_discount_rate` hiện tại: có nên update để include line-item rate không? → **Recommendation:** NO — add `max_line_discount_rate` as separate column, avoid breaking existing Metabase charts that use `max_discount_rate`.
