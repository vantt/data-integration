# Sapo API Data Mapping Research

**Date:** 2026-04-11 | **Research Focus:** Raw data endpoints, field inventory, analytics capability

---

## Executive Summary

Sapo.vn provides a comprehensive REST API supporting **Orders, Products, Customers, Variants, Transactions, and Fulfillment** data. Real-time event streaming via **webhooks** covers order lifecycle (create/paid/fulfilled) and inventory changes. API is mature with token-based auth. **Critical gap:** No native cost/COGS fields in product data—cost data must be sourced separately or calculated from margin data if available.

---

## 1. Core API Endpoints & Resources

### Order Management (`/admin/orders.json`)
- `GET /admin/orders.json` — List with filters (date, status, financial_status)
- `GET /admin/orders/{id}.json` — Single order detail
- `GET /admin/orders/count.json` — Total count
- `POST /admin/orders.json` — Create order
- `PUT /admin/orders/{id}.json` — Update
- `DELETE /admin/orders/{id}.json` — Remove
- `POST /admin/orders/{id}/close.json`, `/open.json`, `/cancel.json` — Status ops

### Customer Management (`/admin/customers.json`)
- `GET`, `POST`, `PUT`, `DELETE`, `COUNT` operations
- Support: filtering by date ranges, pagination, selective fields

### Product Management (`/admin/products.json`)
- `GET /admin/products.json` — List (filter by vendor, type, collection)
- `GET /admin/products/{id}.json` — Single product
- `GET /admin/products/count.json` — Total count
- Includes: Product Variants, Images, Collections

### Additional Resources
- **Fulfillments** — order fulfillment tracking
- **Refunds** — refund management
- **Transactions** — payment/transaction records
- **Customer Addresses** — shipping/billing address management

---

## 2. Analytics-Relevant Data Fields

### Order Data (Most Critical)
| Field | Type | Analytics Use |
|-------|------|---|
| `id`, `order_number` | String | Primary key |
| `created_on`, `modified_on` | ISO 8601 | Timeline, cohort analysis |
| `total_price`, `subtotal_price` | Decimal | Revenue, AOV |
| `total_discounts` | Decimal | Discount impact analysis |
| `financial_status` | Enum: pending/authorized/paid/refunded | Payment funnel |
| `fulfillment_status` | Enum: fulfilled/partial/null | Logistics metrics |
| `source_name` | String: web/pos/api | Channel attribution |
| `currency` | ISO 4217 | Multi-currency handling |
| `line_items[]` | Array | Product-level detail, qty, price, SKU |
| `shipping_lines[]` | Array | Shipping method, cost |
| `billing_address`, `shipping_address` | Object | Geographic analysis, shipping patterns |
| Customer reference | Embedded | Customer linking |

### Customer Data
| Field | Analytics Use |
|-------|---|
| `email`, `phone`, `first_name`, `last_name` | Identification |
| `orders_count`, `total_spent`, `last_order_id` | RFM, CLV |
| `accepts_marketing` | Segmentation |
| `addresses[]` | Geographic distribution |
| `created_on` | Cohort tracking |
| `tags`, `note` | Custom segmentation |

### Product Data
| Field | Analytics Use |
|-------|---|
| `id`, `name`, `sku` | Inventory/sales tracking |
| `price`, `compare_at_price` | Pricing analytics |
| `inventory_quantity` | Stock-level reporting |
| **`cost`** ❌ | **NOT AVAILABLE** |
| `vendor`, `product_type`, `tags` | Category analysis |
| `variants[]` | SKU-level detail |

---

## 3. Real-Time Data: Webhooks

**Supported Topics** (triggered POST to endpoint):
- **Order Events**: `orders/create`, `orders/updated`, `orders/paid`, `orders/cancelled`, `orders/fulfilled`, `orders/partially_fulfilled`, `order_transactions/create`
- **Product Events**: `products/create`, `products/update`, `products/delete`
- **Inventory**: Product variant stock changes (via `products/update`)
- **Customer Events**: `customers/create`, `customers/update`, `customers/delete`, `customers/enable`, `customers/disable`
- **Fulfillments**: `fulfillments/create`, `fulfillments/update`
- **Refunds**: `refunds/create`

**Webhook Config**: Register HTTP/HTTPS endpoint to receive JSON or XML; Sapo POSTs full event payload when topic triggers.

---

## 4. Financial & Profitability Data

### What's Available
- Order revenue (total_price, subtotal_price, discounts)
- Payment status tracking
- Transaction records (via Transaction API)
- Fulfillment costs (shipping_lines)

### What's NOT in API
❌ Product cost (COGS, unit cost)  
❌ Inventory cost valuation  
❌ Margin/profit fields  
❌ Tax breakdown detail  
❌ Refund cost impact  

**Implication:** Profitability analysis requires **external cost data** (MISA ledger, warehouse, vendor invoices) or calculated margins from order/product data.

---

## 5. Inventory & Channel Data

### Inventory
- `inventory_quantity` per variant (real-time)
- `inventory_policy` (track vs. don't track)
- Webhooks on product updates (includes stock changes)
- **Note:** No warehouse/location-level detail; assumes single warehouse

### Channel Attribution
- `source_name` field indicates origin: `web`, `pos`, `api`
- No granular channel breakdown (e.g., Facebook Shop, TikTok, etc.)

---

## 6. Authentication & Rate Limits

- **Token-based**: `X-Sapo-Access-Token` header (API key)
- **OAuth** alternative for multi-store integrations
- **Rate limits**: Not explicitly documented in search results; assume standard SaaS limits (check dashboard)

---

## 7. Maturity & Limitations

### Strengths
✓ Complete order/customer/product lifecycle  
✓ Webhook real-time support (create/update/delete)  
✓ Standard REST + JSON  
✓ Filteringby date, status, field selection  

### Weaknesses
✗ No product cost data  
✗ No multi-warehouse/location support  
✗ No fine-grained channel categorization  
✗ Refund data minimal (linked via order, but limited detail)  

---

## 8. Recommended Integration Pattern

**For Your Analytics Stack:**

1. **Batch**: Daily full sync of `orders`, `products`, `customers` → DuckDB
2. **Real-time**: Subscribe to `orders/paid`, `orders/fulfilled`, `orders/cancelled` webhooks → Dagster for incremental refresh
3. **Cost Alignment**: Join Sapo order data with MISA ledger (separate pipeline) on invoice/document ID
4. **Channel Attribution**: Use `source_name` + custom tags in order metadata for multi-channel breakdown

---

## Unresolved Questions

1. **Rate limiting specifics** — API docs silent on throttle rates; check Sapo dashboard
2. **Refund completeness** — Are refund webhooks sufficient for churn/return analysis, or need transaction history?
3. **Webhook retry/delivery guarantee** — Does Sapo retry failed POSTs? (Important for data integrity)
4. **Location/warehouse support** — Can inventory be tracked per location via metafields or undocumented API?
5. **Tax/duty fields** — Are tax amounts broken down in order line items or only total?

---

## Sources

- [Sapo Support: Order API Introduction](https://support.sapo.vn/gioi-thieu-order-api)
- [Sapo Support: Order API Attributes](https://support.sapo.vn/cac-thuoc-tinh-cua-order-api)
- [Sapo Support: Customer API](https://support.sapo.vn/customer)
- [Sapo Support: Product API Methods](https://support.sapo.vn/phuong-thuc-get-cua-product)
- [Sapo Support: Webhook Documentation](https://support.sapo.vn/sapo-webhook)
- [n8n Sapo Integration Docs](https://docs-tech.n8n.vn/sapo)
- [GitHub: Sapo.vn API Reference](https://github.com/HaDuong24/Sapo.vn)
