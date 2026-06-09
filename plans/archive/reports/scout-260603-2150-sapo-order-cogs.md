# Sapo Order COGS Field Discovery

**Date:** 2026-06-03  
**Parquet path:** `app_data/data_lake/sapo_raw/order/**/*.parquet` (619 files)

---

## 1. Order Payload — Top-Level Keys (67 distinct)

```
account_id, allow_no_refund_order_exchange_amount, assignee_id, billing_address,
business_version, cancelled_on, channel, code, completed_on, contact_id,
create_invoice, created_on, customer_data, customer_id, delivery_fee,
discount_items, discount_reason, einvoice_status, email,
expected_delivery_provider_id, expected_delivery_type, expected_payment_method_id,
finalized_on, finished_on, from_order_return_id, fulfillment_status, fulfillments,
id, interconnection_status, invoices, issued_on, location_id, modified_on, note,
order_coupon_code, order_discount_amount, order_discount_rate, order_discount_value,
order_line_items, order_return_exchange, order_returns, packed_status,
payment_status, phone_number, prepayments, price_list_id, print_status,
process_status_id, promotion_redemptions, reason_cancel_id, received_status,
reference_number, reference_url, return_status, ship_on, ship_on_max, ship_on_min,
shipping_address, source_id, status, tags, tax_treatment, tenant_id, total,
total_discount, total_order_exchange_amount, total_tax
```

**No COGS-signal field** at order top level.

---

## 2. order_line_items Element Keys (42 distinct)

```
barcode, composite_item_domains, created_on, discount_amount, discount_items,
discount_rate, discount_reason, discount_value, distributed_discount_amount,
height_text_term_compo, id, is_composite, is_freeform, is_packsize,
line_amount, line_promotion_type, lots_dates, lots_number_code1-4, modified_on,
note, pack_size_quantity, pack_size_root_id, price, product_id, product_name,
product_type, quantity, serials, sku, tax_amount, tax_included, tax_rate,
tax_rate_override, tax_type_id, unit, variant_id, variant_name, variant_options,
warranty
```

**No COGS-signal field.** Contains `product_id` and `variant_id`.

---

## 3. Nested Array Keys (for completeness)

### fulfillments (46 keys)
Notable: `fulfillment_line_items`, `total`, `total_tax`, `payments`, `shipment`

### fulfillment_line_items (37 keys)
Notable: `base_price`, `product_id`, `variant_id`, `line_amount`, `discount_*`

### order_returns (34 keys) / order_returns.line_items (24 keys)
No COGS fields.

---

## 4. COGS-Candidate Fields — Full Assessment

| Field | Location | % Populated (non-null) | % Non-zero | Sample Values | Verdict |
|---|---|---|---|---|---|
| `base_price` | `fulfillment_line_items` | 100% (1056/1056) | 87.5% (924/1056) | 2425000, 1568000, 1799000, 390000, 4218200 | **SELLING PRICE** — equals `order_line_items.price` for same variant; NOT COGS |
| `price` | `order_line_items` | 100% (500/500) | 83.2% (416/500) | 2425000, 1568000, 1799000 | Selling unit price, NOT COGS |
| `cost_price` | `product.variants` (separate entity) | 0% (0/682) | 0% | — | Schema present, never populated |
| `variant_import_price` | `product.variants` (separate entity) | 99.1% (676/682) | 56.7% (387/682) | 510840, 300785, 586750, 408240, 163296 | **REAL COGS** — import/purchase price; confirmed matches `purchase_order.line_items.price` for same SKUs |
| `price` | `purchase_order.line_items` (separate entity) | ~100% | ~100% | 300785, 811000, 586750, 600000, 172800 | **REAL COGS** — per-unit purchase price; cross-validates `variant_import_price` |

---

## 5. product_id / variant_id on Order Line Items

Both `product_id` and `variant_id` are present on every `order_line_items` element (42-key schema). These are the join keys to look up COGS from the `product` entity.

---

## 6. COGS Join Path

```
order.order_line_items[].variant_id
    → product.variants[].id  (sapo_raw/product)
    → product.variants[].variant_import_price  ← COGS
```

Cross-validated by:
```
purchase_order.line_items[].variant_id / .price  ← purchase unit cost
```

For variant `VTSC20001L001` (variant_id=189170468):
- `variant_import_price` = 300,785
- `purchase_order.line_items.price` = 300,785 ✓

---

## Conclusion

**NO** — the order entity (and its nested `order_line_items`) does **not** carry a COGS field in our ingested data. The only cost-carrying field in the order payload is `fulfillment_line_items.base_price`, which is the **selling price** (mirrors `order_line_items.price`), not cost.

**COGS must come from the `product` entity:**
- `product.variants[].variant_import_price` — 99.1% populated, 56.7% non-zero
- `product.variants[].cost_price` — 0% populated (empty despite schema)
- `purchase_order.line_items[].price` — alternative source, per-PO unit cost

To compute order-level COGS: JOIN `order_line_items.variant_id` → `product.variants.id` → `variant_import_price × quantity`.

---

*No unresolved questions.*
