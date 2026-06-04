# Reference Data Entities

`customer_group`, `price_list` — configuration entities tracked via history log for tracking changes over time.

## customer_group (sapo_raw.customer_group)

**Business Purpose:** Customer segmentation groups (nhóm khách hàng) — used for tiering, pricing rules, and targeted marketing.

**Ingest Methods:** `history_log` only

**Current State:** 0 rows (awaiting customer group events in Sapo)

**API Endpoint:** `/admin/customer_groups/{id}.json`

### Envelope

```
entity_id: customer group ID
entity_type: "customer_group"
ingest_method: "history_log"
event_timestamp: Group creation or update time (TIMESTAMPTZ)
event_type: "create" | "update"
```

### Payload Structure

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Customer group ID |
| `code` | VARCHAR | Group code (e.g., "VIP", "WHOLESALE") |
| `name` | VARCHAR | Display name (e.g., "VIP Customers") |
| `description` | VARCHAR | Group description |
| `discount_rate` | DECIMAL(5,2) | Default discount rate (%) for this group |
| `status` | VARCHAR | `active`, `inactive` |
| `created_on` | TIMESTAMPTZ | Creation date |
| `modified_on` | TIMESTAMPTZ | Last update |

### Business Context

Customer groups are used to:

1. **Segment customers** by tier (VIP, wholesale, retail, etc.)
2. **Apply default pricing** — groups can have associated price lists
3. **Target marketing campaigns** — filter customers by group for promotions
4. **Track customer lifecycle** — move customers between groups as they grow

### Example Groups

| Group | Use Case | Typical Discount |
|-------|----------|------------------|
| VIP | High-value customers | 10–15% |
| Wholesale | Bulk orders, resellers | 20–30% |
| Retail | Retail partners | 5–10% |
| Regular | Regular online buyers | 0–5% |

---

## price_list (sapo_raw.price_list)

**Business Purpose:** Pricing tiers and rules (bảng giá) — defines product prices per channel, customer group, or time period.

**Ingest Methods:** `history_log` only

**Current State:** 0 rows (awaiting price list events in Sapo)

**API Endpoint:** `/admin/price_lists/{id}.json`

### Envelope

```
entity_id: price list ID
entity_type: "price_list"
ingest_method: "history_log"
event_timestamp: Price list creation or update time (TIMESTAMPTZ)
event_type: "create" | "update"
```

### Payload Structure

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Price list ID |
| `code` | VARCHAR | Price list code (e.g., "WHOLESALE_Q1") |
| `name` | VARCHAR | Display name (e.g., "Wholesale Q1 2026") |
| `description` | VARCHAR | Description |
| `status` | VARCHAR | `active`, `inactive` |
| `start_date` | DATE | Effective from date |
| `end_date` | DATE | Effective until date (null = no end date) |
| `is_default` | BOOLEAN | Is default price list for tenant |
| `priority` | INT | Priority ranking (higher = applied first) |
| `price_list_items` | JSON[] | Array of product × price mappings (see below) |
| `created_on` | TIMESTAMPTZ | Creation date |
| `modified_on` | TIMESTAMPTZ | Last update |

### Price List Item Structure (price_list_items[])

| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Price item ID |
| `product_id` | INT | FK to product |
| `variant_id` | INT | FK to variant (if variant-specific pricing) |
| `cost_price` | DECIMAL(15,2) | Cost price |
| `selling_price` | DECIMAL(15,2) | Selling price in this price list |
| `compare_at_price` | DECIMAL(15,2) | "Original" price for discount display |
| `profit_margin_pct` | DECIMAL(5,2) | Calculated margin % |

### Business Context

Price lists enable:

1. **Channel-specific pricing** — Different prices for online vs. retail
2. **Customer segment pricing** — Wholesale vs. retail prices
3. **Temporal pricing** — Seasonal or promotional price tiers
4. **Cost-based pricing** — Markup rules based on product cost

### Example Price Lists

| Price List | Scope | Timeline | Use Case |
|------------|-------|----------|----------|
| Default Retail | All products | Always active | Base online prices |
| Wholesale | Selected products | Always active | Bulk order pricing |
| Summer Sale | Selected products | Jun–Aug 2026 | Seasonal promotion |
| Flash Deal | Selected products | Ad-hoc | Limited-time offers |

---

## Analytics Use Cases

### Customer Group Analytics

```sql
-- Segment customers by group for revenue analysis
SELECT
  stg_customers.customer_group,
  COUNT(DISTINCT stg_customers.customer_id) as customer_count,
  SUM(fact_orders.net_amount) as total_revenue,
  AVG(fact_orders.net_amount) as avg_order_value
FROM stg_sapo_customers_v2
LEFT JOIN fact_orders ON stg_customers.customer_id = fact_orders.customer_id
GROUP BY customer_group
ORDER BY total_revenue DESC
```

### Price List Audit Trail

```sql
-- Track price changes over time
SELECT
  entity_id as price_list_id,
  event_timestamp,
  JSON_EXTRACT_SCALAR(payload, '$.name') as price_list_name,
  JSON_EXTRACT_SCALAR(payload, '$.start_date') as effective_from,
  JSON_EXTRACT_SCALAR(payload, '$.status') as status
FROM sapo_raw.price_list
ORDER BY event_timestamp DESC
```

---

## Related Documentation

- **[Envelope Schema](./envelope-schema.md)** — Shared outer structure
- **[Core Business Entities](./core-entities.md)** — `order`, `customer`, `product`, `account`
- **[Logistics & Inventory](./logistics-inventory.md)** — `fulfillment`, `purchase_order`, `order_return`, `stock_adjustment`
- **[Raw Data Sources Reference](../raw-data-sources.md)** — Complete technical specification
