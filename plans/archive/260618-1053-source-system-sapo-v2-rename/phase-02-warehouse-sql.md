# Phase 2: Warehouse SQL Models

**Priority:** P1  
**Status:** DONE  
**Depends on:** Phase 1 (docs completed)  

## Overview

Đổi `'sapo' AS source_system` → `'sapo_v2' AS source_system` trong tất cả std models và mart.  
Đây là pure SQL change — không có data migration vì source_system được COMPUTE tại query time, không đọc từ parquet.

## Files cần thay đổi

### std models — `transformation/models/staging/standard/`

| File | Thay đổi |
|---|---|
| `std_orders.sql` | `'sapo'` → `'sapo_v2'` |
| `std_order_items.sql` | `'sapo'` → `'sapo_v2'` |
| `std_order_discount_items.sql` | `'sapo'` → `'sapo_v2'`; xoá comment `source_version IN ('v2','v3')` |
| `std_order_returns.sql` | `'sapo'` → `'sapo_v2'`; xoá comment `source_version IN ('v2','v3')` |
| `std_fulfillments.sql` | `'sapo'` → `'sapo_v2'` |
| `std_inventory_movements.sql` | `'sapo'` → `'sapo_v2'`; xoá comment `source_version = 'v2'` |
| `std_products.sql` | `'sapo'` → `'sapo_v2'`; xoá comment `source_version IN ('v2','v3')` |
| `std_variants.sql` | `'sapo'` → `'sapo_v2'`; xoá comment `source_version IN ('v2','v3')` |
| `std_variant_prices.sql` | `'sapo'` → `'sapo_v2'`; xoá comment `source_version IN ('v2','v3')` |
| `std_accounts.sql` | `'sapo'` → `'sapo_v2'` |
| `std_customers.sql` | `'sapo'` → `'sapo_v2'` |
| `std_payments.sql` | `'sapo'` → `'sapo_v2'` |

**Không đổi** (không phải Sapo source):  
- `std_misa_account_ledger.sql`  
- `std_misa_sales_lines.sql`

### mart — `transformation/models/marts/sales/fact_order_costs.sql`

- Dòng 159: `'sapo'` → `'sapo_v2'`
- Dòng 265: `'sapo'` → `'sapo_v2'`

**CONFIRMED:** Dòng 32-36 đổi luôn:
- `'sapo_mac'` → `'sapo_v2_mac'`
- `'sapo_mac+misa'` → `'sapo_v2_mac+misa'`

## schema.yml

Kiểm tra `std-layer/schema.yml` có hardcode test giá trị `'sapo'` không, nếu có phải update.

## Implementation Steps

1. Batch edit tất cả 12 std files (replace_all an toàn — mỗi file chỉ có 1 chỗ)
2. Edit `fact_order_costs.sql` — 4 thay đổi: dòng 32 `sapo_mac` → `sapo_v2_mac`, dòng 33 `sapo_mac+misa` → `sapo_v2_mac+misa` (×2 nếu có), dòng 159 + 265 bare `sapo` → `sapo_v2`
3. Scan lại để verify không còn bất kỳ `sapo[^_v]` nào trong folder này

## Success Criteria

- [x] `grep "'sapo'" transformation/models/staging/standard/` → 0 kết quả
- [x] `grep -E "'sapo[^_]|'sapo'" transformation/models/marts/` → 0 kết quả (không còn bare `sapo` hay `sapo_mac`)
- [ ] dbt compile không lỗi
