# Sapo Product COGS Field Scout Report

**Date:** 2026-06-03  
**Scope:** Raw parquet — `sapo_raw/product`, `sapo_raw/purchase_order`, `sapo_raw/price_list`

---

## 1. Product Payload Keys

### Top-level
```
id, tenant_id, created_on, modified_on, status, brand_id, brand, description, image_path,
image_name, name, opt1, opt2, opt3, category_id, category, category_code, tags, medicine,
vat_pit_category_code, product_type, variants, options, images, product_medicines
```
No COGS field at product level — cost lives inside `variants[]`.

### Variant element keys (inside `$.variants[0]`)
```
id, tenant_id, location_id, created_on, modified_on, category_id, brand_id, product_id,
composite, init_price, init_stock, variant_retail_price, variant_whole_price,
variant_import_price, cost_price, image_id, description, name, opt1, opt2, opt3,
product_name, product_status, status, sellable, sku, barcode, taxable, weight_value,
weight_unit, unit, packsize, packsize_quantity, packsize_root_id, packsize_root_sku,
packsize_root_name, tax_included, input_vat_id, output_vat_id, input_vat_rate,
output_vat_rate, product_type, variant_prices, inventories, images, composite_items,
warranty, warranty_term_id, expiration_alert_time
```

COGS candidates spotted: `variant_import_price`, `cost_price`, `init_price`, and nested `inventories[].mac`.

#### Variant `inventories[]` element keys
```
location_id, variant_id, mac, amount, on_hand, available, committed, incoming,
onway, min_value, max_value, bin_location, wait_to_pack, modified_on
```
`mac` = moving average cost (MAV), updated on each PO receipt.

#### Variant `variant_prices[]` element keys
```
id, value, included_tax_price, name, price_list_id, price_list
```
Links variant to each price list, including the cost price list `GIANHAP` (`is_cost=true`).

---

## 2. Purchase Order Payload Keys

### Top-level (15 POs, 25 line items ingested)
```
id, tenant_id, location_id, account_id, assignee_id, code, reference, supplier_id,
supplier_data, order_supplier_id, order_supplier_code, billing_address, supplier_address,
email, phone_number, line_items, applied_discount, landed_cost_lines, note, tags,
price_list_id, taxes_included, tax_lines, transactions, receipts, refunds,
total_discounts, total_line_items_price, subtotal_price, total_tax, total_landed_costs,
total_price, total_refunds, status, financial_status, receive_status, payment_status,
refund_payment_status, receive_inventory_status, refund_status, due_on, billing_date,
activated_account_id, cancelled_on, cancel_reason, cancelled_account_id, activated_on,
completed_on, closed_on, closed_account_id, created_on, modified_on, interconnection_status
```

### PO `line_items[]` element keys
```
id, product_id, variant_id, title, sku, quantity, price, applied_discount,
discount_allocation, tax_lines, accepted_quantity, remaining_quantity, note,
product_type, serials, lots_dates, tax_included, excluded_tax_price,
excluded_tax_begin_amount, excluded_discount_allocation, order_supplier_line_item_id,
packsize, pack_size_quantity, pack_size_root_id
```
`price` = per-unit purchase/import price on that PO.  
`excluded_tax_price` = same value ex-VAT (confirmed identical in all 25 rows, taxes_included=false).

---

## 3. COGS-Candidate Field Analysis

| Field | Entity | Location | % Populated (>0) | Sample Values (VND) | Verdict |
|---|---|---|---|---|---|
| `variant_import_price` | product | `$.variants[].variant_import_price` | **56.7%** (387/682) | 586,750 / 300,785 / 811,000 / 237,600 / 55,300 | **PRIMARY COGS field** — is_cost price list mirror |
| `cost_price` | product | `$.variants[].cost_price` | **0%** (0/682) | all `null` | Not used — ignore |
| `init_price` | product | `$.variants[].init_price` | **0%** (0/682) | all 0.0 | Not used — ignore |
| `inventories[].mac` | product | `$.variants[].inventories[].mac` | **2.6%** (54/2046 inv rows) | 586,750 / 55,300 / 527,250 / 329,000 | Moving-average cost; diverges from import_price when batches differ; sparse |
| `variant_prices[].value` where `price_list.is_cost=true` | product | `$.variants[].variant_prices[]` (price_list_id=1359099) | **57.2%** (387/676 rows with that list) | identical to variant_import_price | Duplicate — same data, different access path |
| `line_items[].price` | purchase_order | `$.line_items[].price` | **100%** (25/25) | 586,750 / 811,000 / 300,785 / 503,280 / 600,000 | Historical import price per PO — useful for cost-over-time but small dataset (15 POs) |

### Price list context
The tenant has a cost price list: `GIANHAP` (`id=1359099`, `code="GIANHAP"`, `name="Giá nhập"`, `is_cost=true`, `status=default`).  
`variant_import_price` is confirmed to be an exact mirror of this price list's `value` — 100% match on all rows where both are non-zero.

### mac vs variant_import_price divergence
When a variant has received stock at different prices across POs, `mac` diverges from `variant_import_price`. Example:
- variant 72558047 (VCST21003L001): `variant_import_price=286,200` vs `mac=265,000`
- variant 192564024 (VTSC22006L001): `variant_import_price=475,200` vs `mac=329,000`

`mac` reflects weighted average of actual receipts; `variant_import_price` is the currently configured cost price in the product master.

---

## 4. Primary COGS Field

**`$.variants[].variant_import_price`** in the `product` entity is THE per-variant cost price (giá vốn).

- Proof: 387 variants have value > 0; exact match to `GIANHAP` price list (`is_cost=true`)
- Sapo displays this as "Giá vốn" in the product UI
- 43.3% of variants have 0 — these are likely gift/promo SKUs or newly created variants without cost set

Secondary field for moving-average cost: `$.variants[].inventories[].mac` — more accurate for COGS after multiple PO receipts, but only 2.6% populated in current snapshot (mostly zero).

---

## 5. Join Path: Order → Variant Cost

```
order payload
  └─ $.order_line_items[]
       ├─ .product_id   ──→  product.id  ($.id)
       ├─ .variant_id   ──→  product.variants[].id
       └─ .sku          ──→  product.variants[].sku  (alternate join)

product.variants[] where id = order_line_item.variant_id
  └─ .variant_import_price  = per-unit COGS at time of product master snapshot
  └─ .inventories[].mac     = moving-average cost (more precise, rarely populated in snapshot)
```

Validated cross-join: order line item variant_id `72558047` (SKU `VCST21003L001`) → `variant_import_price = 286,200 VND` confirmed present in product parquet.

For PO-based cost tracking:
```
purchase_order.line_items[].variant_id  →  same variant_id
purchase_order.line_items[].price       =  purchase cost on that specific PO
```

---

## 6. Conclusion

**THE COGS field is `variant_import_price` inside `product.payload.variants[]`**, mirroring the `GIANHAP` cost price list (`is_cost=true`). Join from order line items via `variant_id`.

- 56.7% of variants have cost > 0 (remainder are 0 or no-cost SKUs)
- `cost_price` and `init_price` are empty — ignore
- `inventories[].mac` exists but sparse; use when available for weighted-average accuracy
- PO `line_items[].price` provides historical import cost per receipt (15 POs in dataset — small)

**Recommended COGS derivation for `fact_order_economics`:**  
`COALESCE(inventories.mac, variant_import_price)` — prefer mac (actual weighted cost) when populated, fall back to the product master import price.
