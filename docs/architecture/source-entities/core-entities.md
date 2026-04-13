# Core Business Entities

`order`, `customer`, `product`, `account` — primary entities with batch + history log coverage.

## order (sapo_raw.order)

**Business Purpose:** Customer purchases with line items, fulfillments, payments, returns.

**Ingest Methods:** `history_log`, `text` (batch), `webhook`

**Current State:** ~10,000 rows (primary fact table)

### Envelope

```
entity_id: order ID (e.g., "12345678")
entity_type: "order"
ingest_method: "history_log" | "text" | "webhook"
event_timestamp: Order creation or update time (TIMESTAMPTZ)
event_type: "create" | "update"
payload_hash: MD5 of order snapshot
```

### Payload Structure

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Sapo order ID |
| `tenant_id` | INT | Account/tenant ID |
| `code` | VARCHAR | Human-readable order code (e.g., "SON000001") |
| `status` | VARCHAR | `draft`, `finalized`, `completed`, `cancelled` |
| `fulfillment_status` | VARCHAR | `unshipped`, `partial`, `fulfilled` |
| `payment_status` | VARCHAR | `pending`, `partial`, `paid`, `refunded` |
| `packed_status` | VARCHAR | Packing status |
| `return_status` | VARCHAR | Return status |
| `received_status` | VARCHAR | Received status |
| `process_status_id` | INT | Process status ID |
| `process_status` | VARCHAR | Process status name |
| `channel` | VARCHAR | Sales channel (e.g., "web", "retail", "shopee") |
| `created_on` | TIMESTAMPTZ | Order creation timestamp |
| `modified_on` | TIMESTAMPTZ | Last modification timestamp |
| `issued_on` | TIMESTAMPTZ | Invoice issued date |
| `finalized_on` | TIMESTAMPTZ | Order finalized date |
| `finished_on` | TIMESTAMPTZ | Order finished date |
| `completed_on` | TIMESTAMPTZ | Order completion date |
| `cancelled_on` | TIMESTAMPTZ | Cancellation date (null if not cancelled) |
| `customer_id` | INT | FK to customer entity |
| `customer_data` | JSON | **Snapshot** of customer at order time |
| `contact_id` | INT | Contact person ID |
| `account_id` | INT | Sales staff account ID |
| `assignee_id` | INT | Assigned staff account ID |
| `location_id` | INT | Store/warehouse location |
| `source_id` | INT | Sales channel source ID |
| `source_url` | VARCHAR | Source URL (e.g., "shopee.vn") |
| `currency_id` | INT | Currency ID |
| `price_list_id` | INT | FK to price_list |
| `tax_treatment` | VARCHAR | `included`, `excluded` |
| `tax_label` | VARCHAR | Tax label (e.g., "VAT") |
| `total` | DECIMAL(15,2) | Order total (gross) |
| `total_discount` | DECIMAL(15,2) | Total discount |
| `total_tax` | DECIMAL(15,2) | Total tax |
| `order_discount_rate` | DECIMAL(5,2) | Discount rate % |
| `order_discount_value` | DECIMAL(15,2) | Discount amount |
| `order_discount_amount` | DECIMAL(15,2) | Calculated discount |
| `total_discount` | DECIMAL(15,2) | Final discount |
| `discount_reason` | VARCHAR | Reason for discount |
| `discount_items` | JSON | Discount detail lines |
| `delivery_fee` | DECIMAL(15,2) | Shipping/delivery fee |
| `expected_payment_method_id` | INT | Expected payment method ID |
| `expected_delivery_type` | VARCHAR | `courier`, `self_shipping`, `pick_at_store` |
| `expected_delivery_provider_id` | INT | Delivery service provider ID |
| `reason_cancel_id` | INT | Cancellation reason ID (null if not cancelled) |
| `reference_number` | VARCHAR | External reference number |
| `note` | VARCHAR | Order notes |
| `tags` | JSON[] | Order tags (e.g., ["urgent", "vip"]) |
| `billing_address` | JSON | Address object |
| `shipping_address` | JSON | Address object |
| `email` | VARCHAR | Customer email |
| `phone_number` | VARCHAR | Customer phone |
| `order_line_items` | JSON[] | Array of line items (see below) |
| `fulfillments` | JSON[] | Array of fulfillment objects |
| `payments` | JSON[] | Array of payment transactions |
| `prepayments` | JSON[] | Array of advance payments |
| `order_returns` | JSON[] | Array of return transactions |
| `promotion_redemptions` | JSON[] | Array of applied promotions |
| `from_order_return_id` | INT | If created from a return, the return ID |

### Line Item Structure (order_line_items[])

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Line item ID |
| `created_on` | TIMESTAMPTZ | Creation timestamp |
| `modified_on` | TIMESTAMPTZ | Modification timestamp |
| `product_id` | INT | Product ID |
| `variant_id` | INT | Variant ID |
| `product_name` | VARCHAR | Denormalized product name |
| `variant_name` | VARCHAR | Denormalized variant name |
| `sku` | VARCHAR | Product SKU |
| `barcode` | VARCHAR | Product barcode |
| `unit` | VARCHAR | Unit of measure |
| `quantity` | INT | Units ordered |
| `price` | DECIMAL(15,2) | Unit price |
| `line_amount` | DECIMAL(15,2) | quantity × price |
| `discount_rate` | DECIMAL(5,2) | Line discount % |
| `discount_value` | DECIMAL(15,2) | Line discount amount |
| `discount_amount` | DECIMAL(15,2) | Calculated discount |
| `discount_reason` | VARCHAR | Reason |
| `discount_items` | JSON | Breakdown |
| `tax_type_id` | INT | Tax type ID |
| `tax_included` | BOOLEAN | Tax included in price |
| `tax_rate_override` | DECIMAL(5,2) | Custom tax rate |
| `tax_rate` | DECIMAL(5,2) | Applied tax rate |
| `tax_amount` | DECIMAL(15,2) | Calculated tax |
| `note` | VARCHAR | Line notes |
| `is_freeform` | BOOLEAN | Custom line item |
| `is_composite` | BOOLEAN | Bundled product |
| `is_packsize` | BOOLEAN | Pack item |
| `product_type` | VARCHAR | Product type |
| `variant_options` | JSON | Variant attributes (size, color, etc.) |
| `serials` | JSON | Serial numbers |
| `lots_dates` | JSON | Lot/expiry dates |
| `sub_variants` | JSON | Sub-variant details |

### Status Transitions

- **Status:** `draft` → `finalized` → `completed` OR `cancelled`
- **Fulfillment:** `unshipped` → `partial` → `fulfilled`
- **Payment:** `pending` → `partial` → `paid` → (optionally) `refunded`
- **Cancellation:** Sets `status=cancelled` and `cancelled_on` timestamp

---

## customer (sapo_raw.customer)

**Business Purpose:** Customer master data. Addresses are nested within the entity.

**Ingest Methods:** `history_log`, `text` (batch)

**Current State:** ~1,000 rows

### Envelope

```
entity_id: customer ID (e.g., "9876543")
entity_type: "customer"
ingest_method: "history_log" | "text"
event_timestamp: Customer creation or update time (TIMESTAMPTZ)
event_type: "create" | "update"
```

### Payload Structure

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Customer ID |
| `code` | VARCHAR | Customer code/reference |
| `name` | VARCHAR | Full name |
| `email` | VARCHAR | Email address |
| `phone` | VARCHAR | Phone number |
| `gender` | VARCHAR | `male`, `female`, `other` |
| `birthday` | DATE | Birth date |
| `customer_group_name` | VARCHAR | Customer segment (from group or price list) |
| `tags` | JSON[] | Tags (e.g., ["loyal", "wholesale"]) |
| `total_spent` | DECIMAL(15,2) | Lifetime value (VND) |
| `orders_count` | INT | Total orders placed |
| `created_on` | TIMESTAMPTZ | Registration date |
| `modified_on` | TIMESTAMPTZ | Last update |
| `addresses` | JSON[] | Array of addresses (see below) |

### Address Structure (addresses[])

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Address ID |
| `address1` | VARCHAR | Street address |
| `address2` | VARCHAR | Additional address |
| `ward_name` | VARCHAR | Ward/commune |
| `district_name` | VARCHAR | District |
| `city` | VARCHAR | City/province |
| `country` | VARCHAR | Country |
| `phone` | VARCHAR | Address-specific phone |
| `is_default` | BOOLEAN | Default shipping address |
| `note` | VARCHAR | Address notes |

### Address Changes in History Log

Customer address updates trigger `customer_address` events in history log, which are resolved by fetching the **parent customer entity**. The `customer` table captures all address changes via customer updates.

---

## product (sapo_raw.product)

**Business Purpose:** Product master including variants, pricing, categories, inventory.

**Ingest Methods:** `history_log`, `text` (batch)

**Current State:** ~1,000 rows

### Envelope

```
entity_id: product ID (e.g., "111111")
entity_type: "product"
ingest_method: "history_log" | "text"
event_timestamp: Product creation or update time (TIMESTAMPTZ)
event_type: "create" | "update"
```

### Payload Structure

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Product ID |
| `tenant_id` | INT | Account ID |
| `code` | VARCHAR | Product code/SKU |
| `name` | VARCHAR | Product name |
| `status` | VARCHAR | `active`, `inactive` |
| `brand` | VARCHAR | Brand name |
| `category_id` | INT | Category ID |
| `category` | VARCHAR | Category name |
| `category_code` | VARCHAR | Category code |
| `product_type` | VARCHAR | Product type (flat classification, e.g., "Shirt") |
| `unit` | VARCHAR | Unit of measure (e.g., "piece", "box") |
| `medicine` | BOOLEAN | Is medicine product |
| `opt1`, `opt2`, `opt3` | VARCHAR | Variant option names (e.g., "Size", "Color") |
| `tags` | JSON[] | Product tags |
| `created_on` | TIMESTAMPTZ | Creation date |
| `modified_on` | TIMESTAMPTZ | Last update |
| `variants` | JSON[] | Array of variants (see below) |
| `options` | JSON[] | Option definitions |
| `images` | JSON[] | Product images |
| `product_medicines` | JSON[] | Medicine/regulatory info |

### Variant Structure (variants[])

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Variant ID |
| `code` | VARCHAR | Variant code |
| `name` | VARCHAR | Variant name (e.g., "Red - Size M") |
| `status` | VARCHAR | `active`, `inactive` |
| `option1`, `option2`, `option3` | VARCHAR | Variant option values |
| `sku` | VARCHAR | Variant SKU |
| `barcode` | VARCHAR | Variant barcode |
| `weight` | DECIMAL | Weight |
| `cost` | DECIMAL(15,2) | Cost price |
| `price` | DECIMAL(15,2) | Selling price |
| `variant_prices` | JSON[] | Prices at different price lists |
| `inventories` | JSON[] | Stock levels per location |

---

## account (sapo_raw.account)

**Business Purpose:** Staff/employee accounts for sales attribution and order assignment.

**Ingest Methods:** `history_log`, `text` (batch)

**Current State:** ~50 rows

### Envelope

```
entity_id: account ID (e.g., "1001")
entity_type: "account"
ingest_method: "history_log" | "text"
event_timestamp: Account creation or update time (TIMESTAMPTZ)
event_type: "create" | "update"
```

### Payload Structure

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Account ID |
| `email` | VARCHAR | Email (unique per tenant) |
| `first_name` | VARCHAR | First name |
| `last_name` | VARCHAR | Last name |
| `full_name` | VARCHAR | Full name |
| `role` | VARCHAR | Job role (`admin`, `sales`, `warehouse`, `customer_service`, etc.) |
| `status` | VARCHAR | `active`, `inactive`, `suspended` |
| `locations` | INT[] | Array of location IDs where account can operate |

### Role Values

- `admin` — Full administrative access
- `sales` — Sales staff (can create/modify orders, manage customers)
- `warehouse` — Warehouse staff (can manage fulfillments, inventory)
- `customer_service` — Customer service team
- Other domain-specific roles as defined in Sapo

### Status Values

- `active` — Currently employed, account active
- `inactive` — No longer employed or account deactivated
- `suspended` — Temporarily suspended

---

## Related Documentation

- **[Envelope Schema](./envelope-schema.md)** — Shared outer structure
- **[Logistics & Inventory](./logistics-inventory.md)** — `fulfillment`, `purchase_order`, `order_return`, `stock_adjustment`
- **[Reference Data](./reference-data.md)** — `customer_group`, `price_list`
- **[Raw Data Sources Reference](../raw-data-sources.md)** — Complete technical specification
