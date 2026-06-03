# Raw Data Sources Reference

> Complete documentation of all raw entities ingested into `sapo_raw` Delta Lake tables with their schemas, ingest methods, and business context.

## Table of Contents

1. [Envelope Schema (All Entities)](#envelope-schema-all-entities)
2. [Ingest Methods](#ingest-methods)
3. [Core Business Entities](#core-business-entities)
4. [Logistics & Inventory (History Log Only)](#logistics--inventory-history-log-only)
5. [Reference & Configuration (History Log Only)](#reference--configuration-history-log-only)
6. [Resolved via Parent Entity](#resolved-via-parent-entity)
7. [Content/CMS (Planned)](#contentcms-planned)
8. [Other Raw Sources](#other-raw-sources)
9. [Entity Registry Summary](#entity-registry-summary)
10. [Known Issues & Caveats](#known-issues--caveats)

---

## Envelope Schema (All Entities)

All raw entities in `sapo_raw` use a unified **envelope schema** — the same outer structure wrapping entity-specific JSON payloads.

### Envelope Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `entity_id` | VARCHAR | NO | **Primary Key** — Unique identifier for the entity instance (e.g., order ID, customer ID). Combined with `entity_type` for uniqueness. |
| `entity_type` | VARCHAR | NO | Type of entity (e.g., `order`, `customer`, `fulfillment`). Maps to source API endpoint. |
| `payload` | JSON | NO | **Full entity snapshot** — Complete data from Sapo JSON API or upstream system. See entity-specific sections for payload structure. |
| `sync_metadata` | JSON | YES | Source system context and audit trail. Fields: `source` (e.g., "sapo_api"), `sync_timestamp`, `actor` (who triggered the sync), `raw_api_url` (endpoint used). |
| `ingest_method` | VARCHAR | NO | **Partition column** — How entity was ingested: `history_log`, `text` (batch), `webhook`, `google_sheet`. Critical for change tracking. |
| `event_type` | VARCHAR | NO | Action type: `create` or `update`. Indicates whether entity is new or modified. |
| `event_timestamp` | TIMESTAMPTZ | NO | **When the event occurred** (entity creation/modification time in Sapo, not ingest time). **CRITICAL:** Timezone-aware; use for date_key calculations at serving layer. |
| `payload_hash` | VARCHAR | NO | MD5 hash of payload JSON (excluding envelope). Used for efficient deduplication and change detection. |
| `year` | VARCHAR | NO | **Partition column** — Extracted from `event_timestamp` (YYYY format). Enables partitioned queries. |
| `month` | VARCHAR | NO | **Partition column** — Extracted from `event_timestamp` (MM format). Combined with year for monthly partitioning. |
| `_dlt_load_id` | VARCHAR | NO | **dlt framework** — Load batch identifier. Tracks which ingestion run created this record. |
| `_dlt_id` | VARCHAR | NO | **dlt framework** — Unique row identifier assigned by dlt pipeline. |

### Important Notes on Envelope

- **Timezone Awareness**: `event_timestamp` is stored as TIMESTAMPTZ (UTC-aware). Always preserve this when reading — don't cast to naive TIMESTAMP.
- **Partitioning**: Queries should filter on `year` and `month` for performance; `ingest_method` partition separates batch, webhook, and history log flows.
- **Deduplication**: Use `(entity_id, entity_type, event_timestamp)` as logical key; keep the most recent event per entity per timestamp using `payload_hash` for tie-breaking.
- **Change Detection**: Compare `payload_hash` across `event_timestamp` to identify actual field changes vs. no-op updates.

---

## Ingest Methods

| Method | Data Freshness | Completeness | Use Case | Current Entities |
|--------|-----------------|--------------|----------|-------------------|
| **history_log** | Real-time change feed (checked every 30s) | Every change since Sapo API added entity | Source of truth for incremental changes; enables event-driven data lake | `order`, `customer`, `product`, `account`, `fulfillment`, `purchase_order`, `order_return`, `stock_adjustment`, `customer_group`, `price_list`, `customer_address` (via parent) |
| **text (batch)** | Daily full sync at night | Complete snapshot of all entities | Backup for validation; covers entities without history log support | `order`, `customer`, `product`, `account` |
| **webhook** | Event-driven (milliseconds) | Only entities with webhook triggers configured | Live order updates; fast P0 dashboard refresh | `order` (mainly), `unknown` (misrouted orders) |
| **google_sheet** | Manual (user uploads or automation) | Configured by user | Marketing spend, sales targets, external reference data | `marketing_spend_raw`, `targets_raw` |

### Method Selection Strategy

1. **History Log is Primary** — Most entities use history log for incremental ingestion (change tracking, audit trail).
2. **Batch as Fallback** — Periodic full snapshots catch missed events and validate history log.
3. **Webhooks for Speed** — Order webhooks supplement history log for sub-30s latency on P0 dashboards.
4. **Google Sheets for Manual Data** — External data (ad spend, targets) ingested on schedule.

---

## Core Business Entities

### `order` (sapo_raw.order)

**Business Purpose:** Core transactional entity representing customer purchases, including line items, fulfillments, payments, and returns.

**Ingest Methods:** `history_log`, `text` (batch), `webhook`

**Current State:** ~10,000s of rows (approx); primary entity for most analytics

#### Payload Structure

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | INT | Sapo order ID | `12345678` |
| `tenant_id` | INT | Account identifier | `5006` |
| `code` | VARCHAR | Human-readable order code | `"SON000001"` |
| `status` | VARCHAR | Order status: `draft`, `finalized`, `completed`, `cancelled` | `"finalized"` |
| `fulfillment_status` | VARCHAR | Shipping status: `unshipped`, `partial`, `fulfilled` | `"unshipped"` |
| `payment_status` | VARCHAR | Payment status: `pending`, `partial`, `paid`, `refunded` | `"paid"` |
| `packed_status` | VARCHAR | Packing status | `"packed"` |
| `return_status` | VARCHAR | Return status | `"none"` |
| `received_status` | VARCHAR | Received status | `"pending"` |
| `process_status_id` | INT | Process status ID | `1` |
| `process_status` | VARCHAR | Process status name | `"processing"` |
| `channel` | VARCHAR | Sales channel | `"web"` |
| `created_on` | TIMESTAMPTZ | Order creation timestamp | `"2026-01-28T10:00:00Z"` |
| `modified_on` | TIMESTAMPTZ | Last modification timestamp | `"2026-01-28T10:30:00Z"` |
| `issued_on` | TIMESTAMPTZ | Invoice issued date | `"2026-01-28T10:05:00Z"` |
| `finalized_on` | TIMESTAMPTZ | Order finalized date | `"2026-01-28T10:10:00Z"` |
| `finished_on` | TIMESTAMPTZ | Order finished date | `"2026-01-28T10:20:00Z"` |
| `completed_on` | TIMESTAMPTZ | Order completion date | `"2026-01-28T10:25:00Z"` |
| `cancelled_on` | TIMESTAMPTZ | Cancellation date | `null` |
| `customer_id` | INT | FK to customer | `9876543` |
| `customer_data` | JSON | Denormalized customer snapshot at order time | `{...}` |
| `contact_id` | INT | Contact person ID | `null` |
| `account_id` | INT | Sales staff account ID | `1001` |
| `assignee_id` | INT | Assigned staff account ID | `1002` |
| `location_id` | INT | Store/warehouse location | `12345` |
| `source_id` | INT | Sales channel source ID | `1` |
| `source_url` | VARCHAR | Source URL for online orders | `"shopee.vn"` |
| `currency_id` | INT | Currency | `1` |
| `price_list_id` | INT | FK to price_list | `123` |
| `tax_treatment` | VARCHAR | Tax treatment type | `"included"` |
| `tax_label` | VARCHAR | Tax label | `"VAT"` |
| `total` | DECIMAL(15,2) | Order total after discount — **VAT-inclusive** (cash collected from customer; VAT is embedded, not added on top) | `500000` |
| `total_discount` | DECIMAL(15,2) | Total discount | `50000` |
| `total_tax` | DECIMAL(15,2) | VAT **embedded inside** `total`. Sapo computes per-order: 8/108 for 8%-VAT items, 10/110 for 10%-VAT items, 0 for exports/non-VAT. Net revenue = `total − total_tax`. | `0` |
| `order_discount_rate` | DECIMAL(5,2) | Discount rate % | `10` |
| `order_discount_value` | DECIMAL(15,2) | Discount amount | `50000` |
| `order_discount_amount` | DECIMAL(15,2) | Calculated discount | `50000` |
| `total_discount` | DECIMAL(15,2) | Total after all discounts | `50000` |
| `discount_reason` | VARCHAR | Reason for discount | `"promotion"` |
| `discount_items` | JSON | Discount detail lines | `[...]` |
| `delivery_fee` | DECIMAL(15,2) | Delivery/shipping fee | `25000` |
| `expected_payment_method_id` | INT | Expected payment method | `1` |
| `expected_delivery_type` | VARCHAR | Expected delivery type | `"courier"` |
| `expected_delivery_provider_id` | INT | Delivery service provider | `123` |
| `reason_cancel_id` | INT | Cancellation reason ID | `null` |
| `reference_number` | VARCHAR | External reference | `"REF123"` |
| `note` | VARCHAR | Order notes | `"Handle with care"` |
| `tags` | JSON | Order tags | `["urgent", "vip"]` |
| `billing_address` | JSON | Billing address object | `{...}` |
| `shipping_address` | JSON | Shipping address object | `{...}` |
| `email` | VARCHAR | Customer email | `"customer@example.com"` |
| `phone_number` | VARCHAR | Customer phone | `"0901234567"` |
| `order_line_items` | JSON[] | Array of line items | `[{id, product_id, variant_id, quantity, ...}]` |
| `fulfillments` | JSON[] | Array of fulfillment objects | `[{...}]` |
| `payments` | JSON[] | Payment transaction details | `[{...}]` |
| `prepayments` | JSON[] | Advance payment records | `[{...}]` |
| `order_returns` | JSON[] | Return transaction details | `[{...}]` |
| `promotion_redemptions` | JSON[] | Applied promotion codes | `[{...}]` |
| `from_order_return_id` | INT | If created from return, return ID | `null` |

#### Line Item Structure (in `order_line_items[]`)

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Line item ID |
| `created_on` | TIMESTAMPTZ | Creation timestamp |
| `modified_on` | TIMESTAMPTZ | Modification timestamp |
| `product_id` | INT | FK to product |
| `variant_id` | INT | Product variant ID |
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
| `discount_reason` | VARCHAR | Reason for line discount |
| `discount_items` | JSON | Detailed discount breakdown |
| `tax_type_id` | INT | Tax type |
| `tax_included` | BOOLEAN | Tax included in price |
| `tax_rate_override` | DECIMAL(5,2) | Custom tax rate |
| `tax_rate` | DECIMAL(5,2) | Applied tax rate |
| `tax_amount` | DECIMAL(15,2) | Calculated tax |
| `note` | VARCHAR | Line item notes |
| `is_freeform` | BOOLEAN | Custom line item (no product ID) |
| `is_composite` | BOOLEAN | Bundled product |
| `is_packsize` | BOOLEAN | Pack/case item |
| `product_type` | VARCHAR | Product type classification |
| `variant_options` | JSON | Variant attributes (size, color, etc.) |
| `serials` | JSON | Serial numbers |
| `lots_dates` | JSON | Lot/expiry dates |
| `sub_variants` | JSON | Sub-variant details |

#### Business Rules & Status Transitions

- **Status flow**: `draft` → `finalized` → `completed` OR `cancelled`
- **Fulfillment flow**: `unshipped` → `partial` → `fulfilled`
- **Payment flow**: `pending` → `partial` → `paid` → (optionally) `refunded`
- **Cancellation**: Sets `status=cancelled` and `cancelled_on` timestamp; other statuses remain for audit.

---

### `customer` (sapo_raw.customer)

**Business Purpose:** Customer master data (nhân khách hàng). Denormalized in orders for historical accuracy.

**Ingest Methods:** `history_log`, `text` (batch)

**Current State:** ~1,000s of rows

#### Payload Structure

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Customer ID |
| `code` | VARCHAR | Customer code / reference | `"KH000001"` |
| `name` | VARCHAR | Full name |
| `email` | VARCHAR | Email address |
| `phone` | VARCHAR | Phone number |
| `gender` | VARCHAR | Gender: `male`, `female`, `other` |
| `birthday` | DATE | Birth date |
| `customer_group_name` | VARCHAR | Customer segment (from price list/group) | `"VIP"` |
| `tags` | JSON | Customer tags | `["loyal", "wholesale"]` |
| `total_spent` | DECIMAL(15,2) | Lifetime value in VND |
| `orders_count` | INT | Total orders placed |
| `created_on` | TIMESTAMPTZ | Registration date |
| `modified_on` | TIMESTAMPTZ | Last update |
| `addresses` | JSON[] | Array of customer addresses |

#### Address Structure (in `addresses[]`)

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

---

### `product` (sapo_raw.product)

**Business Purpose:** Product master data including variants, pricing, and inventory.

**Ingest Methods:** `history_log`, `text` (batch)

**Current State:** ~100s–1,000s of rows

#### Payload Structure

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Product ID |
| `tenant_id` | INT | Account ID |
| `code` | VARCHAR | Product code / SKU |
| `name` | VARCHAR | Product name |
| `status` | VARCHAR | Status: `active`, `inactive` |
| `brand` | VARCHAR | Brand name |
| `category_id` | INT | Category ID |
| `category` | VARCHAR | Category name |
| `category_code` | VARCHAR | Category code |
| `product_type` | VARCHAR | Product type (flat classification) |
| `opt1`, `opt2`, `opt3` | VARCHAR | Variant option names (e.g., "Size", "Color") |
| `unit` | VARCHAR | Unit of measure (e.g., "piece", "box") |
| `medicine` | BOOLEAN | Is medicine product |
| `tags` | JSON | Product tags | `["new", "seasonal"]` |
| `created_on` | TIMESTAMPTZ | Creation date |
| `modified_on` | TIMESTAMPTZ | Last update |
| `variants` | JSON[] | Array of product variants |
| `options` | JSON[] | Option definitions |
| `images` | JSON[] | Product images |
| `product_medicines` | JSON[] | Medicine/regulatory info |

#### Variant Structure (in `variants[]`)

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Variant ID |
| `code` | VARCHAR | Variant code |
| `name` | VARCHAR | Variant name (e.g., "Red - Size M") |
| `status` | VARCHAR | Status: `active`, `inactive` |
| `option1`, `option2`, `option3` | VARCHAR | Variant option values |
| `sku` | VARCHAR | Variant SKU |
| `barcode` | VARCHAR | Variant barcode |
| `weight` | DECIMAL | Weight |
| `cost` | DECIMAL(15,2) | Cost price |
| `price` | DECIMAL(15,2) | Selling price |
| `variant_prices` | JSON[] | Price at different price lists |
| `inventories` | JSON[] | Stock levels per location |

---

### `account` (sapo_raw.account)

**Business Purpose:** Staff/employee accounts for sales attribution and order assignment.

**Ingest Methods:** `history_log`, `text` (batch)

**Current State:** ~10–100 rows

#### Payload Structure

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Account ID |
| `email` | VARCHAR | Email (unique per tenant) |
| `first_name` | VARCHAR | First name |
| `last_name` | VARCHAR | Last name |
| `full_name` | VARCHAR | Full name |
| `role` | VARCHAR | Job role: `admin`, `sales`, `warehouse`, `customer_service`, etc. |
| `status` | VARCHAR | Account status: `active`, `inactive`, `suspended` |
| `locations` | INT[] | Array of location IDs where account can operate |

---

## Logistics & Inventory (History Log Only)

Entities tracked exclusively via history log (no batch pipeline). These capture changes in real-time as fulfillments are packed, returned, or inventory is adjusted.

### `fulfillment` (sapo_raw.fulfillment)

**Business Purpose:** Packing slip (kho đóng gói) — tracking goods for a single shipment. Distinct from order; one order may have multiple fulfillments.

**Ingest Methods:** `history_log` only

**Current State:** ~3 rows (recently started ingesting)

**API Endpoint:** `/admin/fulfillments/{id}.json`

#### Payload Structure

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Fulfillment ID |
| `tenant_id` | INT | Account ID |
| `code` | VARCHAR | Fulfillment code | `"KH000001"` |
| `order_id` | INT | Parent order ID |
| `order` | JSON | Denormalized order snapshot |
| `stock_location_id` | INT | Warehouse location |
| `account_id` | INT | Created by account |
| `assignee_id` | INT | Assigned to account |
| `partner_id` | INT | Partner/vendor ID (if 3PL) |
| `customer` | JSON | Denormalized customer data |
| `billing_address` | JSON | Billing address |
| `shipping_address` | JSON | Shipping address |
| `delivery_type` | VARCHAR | `courier`, `self_shipping`, `pick_at_store` |
| `tax_treatment` | VARCHAR | Tax treatment |
| `status` | VARCHAR | `fulfilled`, `packed`, `shipped`, `cancelled` |
| `print_status` | VARCHAR | Print status for label |
| `composite_fulfillment_status` | VARCHAR | Composite status |
| `payment_status` | VARCHAR | Payment on fulfillment |
| `packed_on` | TIMESTAMPTZ | Packing completion |
| `shipped_on` | TIMESTAMPTZ | Shipment date |
| `received_on` | TIMESTAMPTZ | Customer received date |
| `cancel_date` | TIMESTAMPTZ | Cancellation date |
| `cancel_account_id` | INT | Cancelled by account |
| `created_on` | TIMESTAMPTZ | Creation date |
| `modified_on` | TIMESTAMPTZ | Last update |
| `total` | DECIMAL(15,2) | Fulfillment total |
| `total_discount` | DECIMAL(15,2) | Total discount |
| `total_tax` | DECIMAL(15,2) | Total tax |
| `discount_rate` | DECIMAL(5,2) | Discount % |
| `discount_value` | DECIMAL(15,2) | Discount amount |
| `discount_amount` | DECIMAL(15,2) | Calculated discount |
| `total_quantity` | INT | Total units |
| `notes` | VARCHAR | Fulfillment notes |
| `fulfillment_line_items` | JSON[] | Line items in fulfillment |
| `shipment` | JSON | Nested shipment object with tracking |
| `payments` | JSON[] | Fulfillment-level payments |
| `stock_out_account_id` | INT | Who marked as stock-out |
| `receive_account_id` | INT | Who received |
| `receive_cancellation_account_id` | INT | Who cancelled receipt |
| `receive_cancellation_on` | TIMESTAMPTZ | When receipt was cancelled |
| `pushing_status` | VARCHAR | Push to shipping provider status |
| `bill_of_lading_on` | TIMESTAMPTZ | B/L date |
| `late_pickup_date` | TIMESTAMPTZ | Late pickup date |
| `late_delivery_date` | TIMESTAMPTZ | Late delivery date |
| `reason_cancel_id` | INT | Cancellation reason ID |

#### Fulfillment Line Item Structure (in `fulfillment_line_items[]`)

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
| `tax_rate_override` | DECIMAL(5,2) | Custom tax rate |
| `is_freeform` | BOOLEAN | Custom line |
| `is_composite` | BOOLEAN | Bundled product |
| `is_packsize` | BOOLEAN | Pack item |
| `product_type` | VARCHAR | Product type |
| `variant_options` | JSON | Variant attributes |
| `serials` | JSON | Serial numbers |
| `lots_dates` | JSON | Lot numbers / expiry |
| `lots_number_code1-4` | VARCHAR | Legacy lot codes |
| `distributed_discount_value` | DECIMAL(15,2) | Allocated discount |
| `distributed_discount_amount` | DECIMAL(15,2) | Calculated allocated |
| `sub_variants` | JSON | Sub-variant detail |
| `created_on` | TIMESTAMPTZ | Creation date |
| `modified_on` | TIMESTAMPTZ | Last update |
| `order_line_item_note` | VARCHAR | Original line note |

#### Shipment Structure (in `shipment{}`)

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Shipment ID |
| `delivery_service_provider_id` | INT | Carrier ID |
| `service_name` | VARCHAR | Service name (e.g., "GHN Standard") |
| `delivery_service_provider` | VARCHAR | Carrier name |
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
| `detail` | JSON | Detailed tracking |
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
| `weight` | DECIMAL | Total weight |
| `length`, `width`, `height` | DECIMAL | Dimensions |
| `shipping_account_id` | INT | Shipping account |
| `partial_tracking_code` | VARCHAR | Partial tracking |
| `partial_tracking_url` | VARCHAR | Partial tracking URL |

---

### `purchase_order` (sapo_raw.purchase_order)

**Business Purpose:** Purchase order (nhập hàng) — goods received from suppliers.

**Ingest Methods:** `history_log` only

**Current State:** 0 rows (table created, no history log events yet)

**API Endpoint:** `/admin/purchase_orders/{id}.json`

**Expected Payload:** Similar to orders but focused on supplier, received quantity, cost per unit, and warehouse receipt tracking.

---

### `order_return` (sapo_raw.order_return)

**Business Purpose:** Return/refund transactions (hoàn/trả hàng) — customer returns and refunds.

**Ingest Methods:** `history_log` only

**Current State:** 0 rows (table created, no history log events yet)

**API Endpoint:** `/admin/order_returns/{id}.json`

**Expected Payload:** References parent order, return reason, returned items, refund amount, and return status tracking.

---

### `stock_adjustment` (sapo_raw.stock_adjustment)

**Business Purpose:** Inventory adjustments (kiểm kho, điều chỉnh tồn kho) — manual stock corrections, physical inventory count, and write-offs.

**Ingest Methods:** `history_log` only

**Current State:** 0 rows (table created, no history log events yet)

**API Endpoint:** `/admin/stock_adjustments/{id}.json`

**Expected Payload:** Location, reason (inventory count, write-off, damage, theft), adjustment lines with product and quantity delta.

---

## Reference & Configuration (History Log Only)

### `customer_group` (sapo_raw.customer_group)

**Business Purpose:** Customer segmentation groups (nhóm khách hàng) — used for tiering, pricing, and targeting.

**Ingest Methods:** `history_log` only

**Current State:** 0 rows (table created, no history log events yet)

**API Endpoint:** `/admin/customer_groups/{id}.json`

#### Expected Payload

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Group ID |
| `code` | VARCHAR | Group code |
| `name` | VARCHAR | Group name (e.g., "VIP", "Wholesale") |
| `description` | VARCHAR | Group description |
| `discount_rate` | DECIMAL(5,2) | Default group discount % |

---

### `price_list` (sapo_raw.price_list)

**Business Purpose:** Pricing tiers and rules (bảng giá) — defines product prices per channel, customer group, or time period.

**Ingest Methods:** `history_log` only

**Current State:** 0 rows (table created, no history log events yet)

**API Endpoint:** `/admin/price_lists/{id}.json`

#### Expected Payload

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Price list ID |
| `code` | VARCHAR | Price list code |
| `name` | VARCHAR | Name (e.g., "Wholesale Q1 2026") |
| `status` | VARCHAR | `active`, `inactive` |
| `start_date` | DATE | Effective from |
| `end_date` | DATE | Effective until |
| `is_default` | BOOLEAN | Default price list |
| `price_list_items` | JSON[] | Product × price mappings |

---

## Resolved via Parent Entity

### `customer_address` (via sapo_raw.customer)

**Business Purpose:** Customer address changes are tracked via history log but resolved by fetching the parent customer entity.

**Ingest Methods:** `history_log` (resolved as `customer`)

**Resolve Strategy:** When history log emits `customer_address` event, the pipeline:
1. Extracts parent customer ID from the log's `uri` field (pattern: `/admin/customers/{customer_id}/addresses.json`)
2. Fetches full customer entity via `/admin/customers/{customer_id}.json`
3. Stores in `customer` table (not separate `customer_address` table)

**Rationale:** Customer addresses are nested within the customer entity; Sapo doesn't provide address-level JSON endpoints. This approach keeps customer master data synchronized and captures all address changes via customer updates.

---

## Content/CMS (Planned)

These entities are registered in the history log entity registry but have **never been observed** in production history logs. URLs are **not verified** against live Sapo endpoints.

| Entity | API Endpoint | Purpose | Status |
|--------|--------------|---------|--------|
| `page` | `/admin/pages/{id}.json` | Website pages | Planned, not observed |
| `blog` | `/admin/blogs/{id}.json` | Blog metadata | Planned, not observed |
| `article` | `/admin/articles/{id}.json` | Blog articles | Planned, not observed |
| `custom_collection` | `/admin/custom_collections/{id}.json` | Custom product collections | Planned, not observed |
| `smart_collection` | `/admin/smart_collections/{id}.json` | Auto-generated collections | Planned, not observed |
| `collect` | `/admin/collects/{id}.json` | Collection membership | Planned, not observed |
| `variant` | `/admin/variants/{id}.json` | Product variant (if standalone) | Planned, not observed |

---

## Other Raw Sources

### `unknown` (sapo_raw.unknown)

**Business Purpose:** Catch-all for webhook events that couldn't be properly entity-typed.

**Ingest Methods:** `webhook`

**Current State:** ~4,646 rows

**Issue:** Orders from webhooks are sometimes received without clear entity-type classification. Inspection shows nearly 100% are orders based on payload structure (presence of `order_line_items`, `fulfillment_status`, etc.).

**Recommended Action:** 
- Add logic to detect and re-classify `unknown` entries as `order` based on payload inspection.
- Track misrouting rate to identify webhook configuration issues.

#### Known Distribution (Last Check)

- `status="finalized"`: 3,526 rows
- `status="completed"`: 573 rows
- `status="draft"`: 441 rows
- `status="cancelled"`: 106 rows

---

### `marketing_spend_raw` (sapo_raw.marketing_spend_raw)

**Business Purpose:** Marketing ad spend for CAC and ROAS analysis.

**Ingest Methods:** `google_sheet`

**Current State:** ~8 rows

**Source:** Manual Google Sheets ingestion (user uploads or automated sync).

#### Schema

| Column | Type | Description |
|--------|------|-------------|
| `date` | DATE | Spend date |
| `spend_code` | VARCHAR | Code for spend category |
| `source_id` | INT | Sales channel source ID |
| `location_id` | INT | Location |
| `campaign_id` | VARCHAR | Campaign identifier |
| `spend_amount` | DECIMAL(15,2) | Cost in VND |
| `clicks` | INT | Ad clicks |
| `impressions` | INT | Ad impressions |

---

### `targets_raw` (sapo_raw.targets_raw)

**Business Purpose:** Sales targets for performance tracking.

**Ingest Methods:** `google_sheet`

**Current State:** ~8 rows

**Source:** Manual Google Sheets ingestion.

#### Schema

| Column | Type | Description |
|--------|------|-------------|
| `setup_date` | DATE | Target setup date |
| `branch_code` | VARCHAR | Store/branch code |
| `team_code` | VARCHAR | Team identifier |
| `staff_email` | VARCHAR | Staff email |
| `sales_channel` | VARCHAR | Sales channel (e.g., "web", "retail") |
| `product_sku` | VARCHAR | Product SKU (if product-specific) |
| `metric_code` | VARCHAR | Metric type (e.g., "revenue", "units") |
| `target_value` | DECIMAL(15,2) | Target value in VND or units |
| `description` | VARCHAR | Notes |

---

## Entity Registry Summary

### Ingestion Status Matrix

| Entity | History Log | Batch | Webhook | Google Sheet | Observed | Notes |
|--------|-------------|-------|---------|--------------|----------|-------|
| **order** | ✓ | ✓ | ✓ | — | ~10k rows | Primary entity |
| **customer** | ✓ | ✓ | — | — | ~1k rows | Core dimension |
| **product** | ✓ | ✓ | — | — | ~1k rows | Core dimension |
| **account** | ✓ | ✓ | — | — | ~50 rows | Staff master |
| **fulfillment** | ✓ | — | — | — | ~3 rows | Recently started |
| **purchase_order** | ✓ | — | — | — | 0 rows | Awaiting PO events |
| **order_return** | ✓ | — | — | — | 0 rows | Awaiting return events |
| **stock_adjustment** | ✓ | — | — | — | 0 rows | Awaiting adjustments |
| **customer_group** | ✓ | — | — | — | 0 rows | Reference data |
| **price_list** | ✓ | — | — | — | 0 rows | Reference data |
| **customer_address** | ✓ (via parent) | — | — | — | — | Resolved as customer |
| **unknown** | — | — | ✓ | — | ~4.6k rows | Misrouted webhooks |
| **marketing_spend_raw** | — | — | — | ✓ | ~8 rows | Manual upload |
| **targets_raw** | — | — | — | ✓ | ~8 rows | Manual upload |

### Skipped Entities

These entities are registered in the entity registry but are **intentionally not fetched**:

| Entity | Reason |
|--------|--------|
| `fulfillment_print_forms` | Low value; printing metadata only |
| `account_authentication` | Security-sensitive; not needed for analytics |
| `tenant_role` | Administrative; low analytics value |
| `policy` | Policy/legal docs; not needed for analytics |

---

## Known Issues & Caveats

### 1. Envelope Partition Cardinality

- **Partitioning by `year` and `month` is necessary** for performance but can create small partitions for newly observed entity types (e.g., fulfillment with only 3 rows).
- **Recommendation:** Use `SHOW PARTITIONS` to identify skewed partitions and consider repartitioning on a rolling basis (e.g., annually).

### 2. Denormalization & Snapshot Consistency

- **Order payloads include snapshots** of `customer_data`, `account` details, and `order_line_items` at order creation time.
- **These snapshots may not match the current row in `customer` or `account`** if those entities were later updated.
- **For historical accuracy:** Always use order-embedded snapshots for fact table construction, not joins to current customer/account dimensions.

### 3. Timezone Handling

- **`event_timestamp` is stored as TIMESTAMPTZ (UTC)** — this is critical for correct date-key assignment.
- **Asia/Ho_Chi_Minh timezone conversions are applied at the serving layer** (Metabase, dashboards), not in the raw tables.
- **Never cast `event_timestamp` to naive TIMESTAMP** — you will lose timezone info and mis-assign dates for 0h–7h orders.

### 4. Unknown Webhook Catch-All

- **`unknown` table contains ~4,600 webhook records**, nearly all of which are orders.
- **Root cause:** Webhook routing occasionally fails to classify entity type correctly.
- **Mitigation:** Automated re-classification logic being added (inspect payload for `order_line_items` presence).

### 5. History Log Lag & Eventual Consistency

- **History log is checked every 30 seconds**, but updates may lag behind the Sapo web UI by a few seconds.
- **Order webhooks are faster** (milliseconds) but may be lost if the integration server is unreachable.
- **Batch sync is a fallback** — runs nightly to catch missed events.

### 6. Payload Size & Nested Complexity

- **Order payloads include deeply nested arrays** (`order_line_items[]`, `fulfillments[]`, `payments[]`, `promotion_redemptions[]`).
- **This can cause parsing issues** if nested structures are not properly handled by downstream tools.
- **Recommendation:** Use dedicated JSON parsing in dbt/Spark; avoid string manipulation on JSON.

### 7. Reference Data Freshness

- **`customer_group` and `price_list` entities have 0 rows** — these will only populate when those entities are modified in Sapo.
- **Initial ingestion may take time** (weeks/months) if these entities are rarely updated.
- **For analytics:** Consider adding a batch fetch of current reference data as a fallback.

---

## Related Documentation

- **Architecture Overview:** `docs/architecture/overview.md`
- **Data Dictionary (Staged & Fact Models):** `docs/architecture/data-dictionary.md`
- **Data Flow Diagram:** `docs/architecture/data-flow.md`
- **History Log Pipeline:** `ingestion/src/sapo/history_log.py`
