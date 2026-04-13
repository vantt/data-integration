# Logistics & Inventory Entities

`fulfillment`, `purchase_order`, `order_return`, `stock_adjustment` — tracked exclusively via history log (no batch pipeline).

## fulfillment (sapo_raw.fulfillment)

**Business Purpose:** Packing slips (kho đóng gói) representing goods prepared for shipment. One order may spawn multiple fulfillments.

**Ingest Methods:** `history_log` only

**Current State:** ~3 rows (recently started)

**API Endpoint:** `/admin/fulfillments/{id}.json`

### Envelope

```
entity_id: fulfillment ID (e.g., "87654321")
entity_type: "fulfillment"
ingest_method: "history_log"
event_timestamp: Fulfillment creation or update time (TIMESTAMPTZ)
event_type: "create" | "update"
```

### Payload Structure

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Fulfillment ID |
| `tenant_id` | INT | Account ID |
| `code` | VARCHAR | Fulfillment code |
| `order_id` | INT | Parent order ID |
| `order` | JSON | Denormalized order snapshot |
| `stock_location_id` | INT | Warehouse location |
| `account_id` | INT | Created by account |
| `assignee_id` | INT | Assigned to account |
| `partner_id` | INT | Partner/3PL ID |
| `customer` | JSON | Denormalized customer data |
| `billing_address` | JSON | Address object |
| `shipping_address` | JSON | Address object |
| `delivery_type` | VARCHAR | `courier`, `self_shipping`, `pick_at_store` |
| `tax_treatment` | VARCHAR | `included`, `excluded` |
| `status` | VARCHAR | `fulfilled`, `packed`, `shipped`, `cancelled` |
| `print_status` | VARCHAR | Print status for label |
| `composite_fulfillment_status` | VARCHAR | Composite status |
| `payment_status` | VARCHAR | Payment on fulfillment |
| `created_on` | TIMESTAMPTZ | Creation date |
| `modified_on` | TIMESTAMPTZ | Last update |
| `packed_on` | TIMESTAMPTZ | Packing completion |
| `shipped_on` | TIMESTAMPTZ | Shipment date |
| `received_on` | TIMESTAMPTZ | Customer received date |
| `cancel_date` | TIMESTAMPTZ | Cancellation date |
| `cancel_account_id` | INT | Cancelled by account |
| `total` | DECIMAL(15,2) | Fulfillment total |
| `total_discount` | DECIMAL(15,2) | Total discount |
| `total_tax` | DECIMAL(15,2) | Total tax |
| `discount_rate` | DECIMAL(5,2) | Discount % |
| `discount_value` | DECIMAL(15,2) | Discount amount |
| `discount_amount` | DECIMAL(15,2) | Calculated discount |
| `total_quantity` | INT | Total units |
| `notes` | VARCHAR | Fulfillment notes |
| `fulfillment_line_items` | JSON[] | Line items in fulfillment (see below) |
| `shipment` | JSON | Nested shipment object (see below) |
| `payments` | JSON[] | Fulfillment-level payments |
| `stock_out_account_id` | INT | Who marked as stock-out |
| `receive_account_id` | INT | Who received |
| `receive_cancellation_account_id` | INT | Who cancelled receipt |
| `receive_cancellation_on` | TIMESTAMPTZ | When receipt cancelled |
| `pushing_status` | VARCHAR | Push to carrier status |
| `bill_of_lading_on` | TIMESTAMPTZ | B/L date |
| `late_pickup_date` | TIMESTAMPTZ | Late pickup date |
| `late_delivery_date` | TIMESTAMPTZ | Late delivery date |
| `reason_cancel_id` | INT | Cancellation reason ID |

### Line Item Structure (fulfillment_line_items[])

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Line item ID |
| `order_line_item_id` | INT | FK to parent order line item |
| `product_id` | INT | Product ID |
| `product_name` | VARCHAR | Denormalized product name |
| `variant_id` | INT | Variant ID |
| `variant_name` | VARCHAR | Denormalized variant name |
| `sku` | VARCHAR | SKU |
| `barcode` | VARCHAR | Barcode |
| `unit` | VARCHAR | Unit of measure |
| `quantity` | INT | Units in fulfillment |
| `base_price` | DECIMAL(15,2) | Base price |
| `line_amount` | DECIMAL(15,2) | quantity × base_price |
| `line_discount_amount` | DECIMAL(15,2) | Line discount |
| `line_tax_amount` | DECIMAL(15,2) | Line tax |
| `discount_rate` | DECIMAL(5,2) | Discount % |
| `discount_value` | DECIMAL(15,2) | Discount amount |
| `tax_rate` | DECIMAL(5,2) | Tax rate |
| `tax_type_id` | INT | Tax type |
| `tax_rate_override` | DECIMAL(5,2) | Custom rate |
| `is_freeform` | BOOLEAN | Custom line |
| `is_composite` | BOOLEAN | Bundled product |
| `is_packsize` | BOOLEAN | Pack item |
| `product_type` | VARCHAR | Product type |
| `variant_options` | JSON | Variant attributes |
| `serials` | JSON | Serial numbers |
| `lots_dates` | JSON | Lot/expiry dates |
| `lots_number_code1-4` | VARCHAR | Legacy lot codes |
| `distributed_discount_value` | DECIMAL(15,2) | Allocated discount |
| `distributed_discount_amount` | DECIMAL(15,2) | Calculated allocation |
| `sub_variants` | JSON | Sub-variant details |
| `created_on` | TIMESTAMPTZ | Creation date |
| `modified_on` | TIMESTAMPTZ | Last update |
| `order_line_item_note` | VARCHAR | Original line note |

### Shipment Structure (shipment{})

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Shipment ID |
| `delivery_service_provider_id` | INT | Carrier ID |
| `service_name` | VARCHAR | Service name (e.g., "GHN Standard") |
| `delivery_service_provider` | VARCHAR | Carrier name (e.g., "GHN", "GrabExpress") |
| `tracking_code` | VARCHAR | Tracking number |
| `tracking_url` | VARCHAR | Carrier tracking URL |
| `partner_order_id` | VARCHAR | Carrier's order ID |
| `cod_amount` | DECIMAL(15,2) | Cash on delivery amount |
| `freight_amount` | DECIMAL(15,2) | Freight cost |
| `freight_amount_detail` | JSON | Detailed freight breakdown |
| `delivery_fee` | DECIMAL(15,2) | Delivery fee charged |
| `created_on` | TIMESTAMPTZ | Shipment creation |
| `modified_on` | TIMESTAMPTZ | Last update |
| `sender_address` | JSON | Sender address |
| `shipping_address` | JSON | Shipping address |
| `shipper_deposits` | JSON | Deposit details |
| `detail` | JSON | Detailed tracking events |
| `note` | VARCHAR | Shipment note |
| `pushing_status` | VARCHAR | Push status |
| `reference_status` | VARCHAR | Carrier reference status |
| `reference_status_explanation` | VARCHAR | Status explanation |
| `pushing_note` | VARCHAR | Push notes |
| `collation_status` | VARCHAR | Collation status |
| `freight_payer` | VARCHAR | Who pays freight |
| `estimated_delivery_time` | TIMESTAMPTZ | Estimated delivery |
| `route_code_se` | VARCHAR | Route code |
| `sorting_code` | VARCHAR | Sorting code |
| `is_multiple_drop_off` | BOOLEAN | Multiple drop-offs |
| `weight` | DECIMAL | Total weight (kg) |
| `length`, `width`, `height` | DECIMAL | Dimensions (cm) |
| `shipping_account_id` | INT | Shipping account |
| `partial_tracking_code` | VARCHAR | Partial tracking |
| `partial_tracking_url` | VARCHAR | Partial tracking URL |

### Status Transitions

- **Status:** `fulfilled`, `packed`, `shipped`, `cancelled`
- **Delivery Types:** `courier` (third-party carrier), `self_shipping` (in-house), `pick_at_store` (customer pickup)

---

## purchase_order (sapo_raw.purchase_order)

**Business Purpose:** Supplier purchase orders (nhập hàng) — track goods received from suppliers.

**Ingest Methods:** `history_log` only

**Current State:** 0 rows (awaiting PO events in Sapo)

**API Endpoint:** `/admin/purchase_orders/{id}.json`

### Envelope

```
entity_id: PO ID
entity_type: "purchase_order"
ingest_method: "history_log"
event_timestamp: PO creation or update time (TIMESTAMPTZ)
event_type: "create" | "update"
```

### Expected Payload Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | PO ID |
| `code` | VARCHAR | PO code |
| `supplier_id` | INT | FK to supplier (if available) |
| `location_id` | INT | Receiving warehouse |
| `status` | VARCHAR | `draft`, `confirmed`, `received`, `cancelled` |
| `po_date` | DATE | PO date |
| `received_date` | DATE | Goods received date |
| `total` | DECIMAL(15,2) | PO total |
| `po_line_items` | JSON[] | Array of line items with product_id, quantity, unit_cost, received_qty |
| `created_on` | TIMESTAMPTZ | Creation date |
| `modified_on` | TIMESTAMPTZ | Last update |

**Note:** Exact structure **not verified** against live API — populated when PO events occur.

---

## order_return (sapo_raw.order_return)

**Business Purpose:** Return/refund transactions (hoàn/trả hàng) — track customer returns and refunds.

**Ingest Methods:** `history_log` only

**Current State:** 0 rows (awaiting return events in Sapo)

**API Endpoint:** `/admin/order_returns/{id}.json`

### Envelope

```
entity_id: Return ID
entity_type: "order_return"
ingest_method: "history_log"
event_timestamp: Return creation or update time (TIMESTAMPTZ)
event_type: "create" | "update"
```

### Expected Payload Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Return ID |
| `code` | VARCHAR | Return code |
| `order_id` | INT | FK to original order |
| `status` | VARCHAR | `pending`, `approved`, `received`, `rejected`, `refunded` |
| `reason_id` | INT | Return reason ID |
| `reason` | VARCHAR | Return reason (e.g., "defective", "wrong_item", "changed_mind") |
| `total_amount` | DECIMAL(15,2) | Return amount |
| `refund_amount` | DECIMAL(15,2) | Refunded amount |
| `return_date` | DATE | Return date |
| `received_date` | DATE | Items received back date |
| `return_line_items` | JSON[] | Line items being returned (product_id, quantity, reason) |
| `created_on` | TIMESTAMPTZ | Creation date |
| `modified_on` | TIMESTAMPTZ | Last update |

**Note:** Exact structure **not verified** against live API — populated when return events occur.

---

## stock_adjustment (sapo_raw.stock_adjustment)

**Business Purpose:** Inventory adjustments (kiểm kho, điều chỉnh tồn kho) — track manual stock corrections, physical counts, write-offs.

**Ingest Methods:** `history_log` only

**Current State:** 0 rows (awaiting adjustment events in Sapo)

**API Endpoint:** `/admin/stock_adjustments/{id}.json`

### Envelope

```
entity_id: Adjustment ID
entity_type: "stock_adjustment"
ingest_method: "history_log"
event_timestamp: Adjustment creation or update time (TIMESTAMPTZ)
event_type: "create" | "update"
```

### Expected Payload Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Adjustment ID |
| `code` | VARCHAR | Adjustment code |
| `location_id` | INT | Warehouse location |
| `adjustment_type` | VARCHAR | `inventory_count` (kiểm kho), `write_off` (xóa tồn), `damage`, `theft`, `correction` |
| `reason_id` | INT | Reason ID |
| `reason` | VARCHAR | Reason description |
| `status` | VARCHAR | `draft`, `confirmed`, `received` |
| `adjustment_date` | DATE | Adjustment date |
| `total_cost` | DECIMAL(15,2) | Total value of adjustment |
| `adjustment_line_items` | JSON[] | Line items with product_id, quantity_before, quantity_after, reason |
| `note` | VARCHAR | Notes |
| `created_on` | TIMESTAMPTZ | Creation date |
| `modified_on` | TIMESTAMPTZ | Last update |

**Note:** Exact structure **not verified** against live API — populated when adjustment events occur.

---

## Related Documentation

- **[Envelope Schema](./envelope-schema.md)** — Shared outer structure
- **[Core Business Entities](./core-entities.md)** — `order`, `customer`, `product`, `account`
- **[Reference Data](./reference-data.md)** — `customer_group`, `price_list`
- **[Raw Data Sources Reference](../raw-data-sources.md)** — Complete technical specification
