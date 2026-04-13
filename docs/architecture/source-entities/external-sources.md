# External & Special Sources

`marketing_spend_raw`, `targets_raw`, `unknown` — Google Sheets ingestion, webhook catch-all, and misrouted data.

## marketing_spend_raw (sapo_raw.marketing_spend_raw)

**Business Purpose:** Marketing ad spend tracking for CAC (Cost Acquisition) and ROAS (Return on Ad Spend) analysis.

**Ingest Methods:** `google_sheet` (manual upload or automated sync)

**Current State:** ~8 rows

### Envelope

```
entity_id: auto-generated row ID
entity_type: "marketing_spend_raw"
ingest_method: "google_sheet"
event_timestamp: When row was ingested (not spend date)
event_type: "create"
```

### Payload Structure

| Field | Type | Description |
|-------|------|-------------|
| `date` | DATE | Spend date |
| `spend_code` | VARCHAR | Code for spend category |
| `source_id` | INT | Sales channel source ID (FK to order.source_id) |
| `location_id` | INT | Store location ID |
| `campaign_id` | VARCHAR | Campaign identifier (e.g., "FB_Summer2026_V1") |
| `spend_amount` | DECIMAL(15,2) | Cost in VND |
| `clicks` | INT | Ad clicks |
| `impressions` | INT | Ad impressions |

### Analytics Integration

Join to `fact_orders` via `source_id` and `date` to calculate:

```sql
SELECT
  ms.date,
  ms.campaign_id,
  SUM(ms.spend_amount) as total_spend,
  SUM(ms.clicks) as total_clicks,
  COUNT(DISTINCT fo.order_id) as orders,
  SUM(fo.net_amount) as revenue,
  ROUND(SUM(ms.spend_amount) / COUNT(DISTINCT fo.order_id), 0) as cac,
  ROUND(SUM(fo.net_amount) / SUM(ms.spend_amount), 2) as roas
FROM sapo_raw.marketing_spend_raw ms
LEFT JOIN fact_orders fo
  ON ms.source_id = fo.source_id
  AND CAST(fo.created_at AS DATE) = ms.date
GROUP BY ms.date, ms.campaign_id
```

---

## targets_raw (sapo_raw.targets_raw)

**Business Purpose:** Sales targets for performance tracking and KPI measurement.

**Ingest Methods:** `google_sheet` (manual upload)

**Current State:** ~8 rows

### Envelope

```
entity_id: auto-generated row ID
entity_type: "targets_raw"
ingest_method: "google_sheet"
event_timestamp: When row was ingested (not target date)
event_type: "create"
```

### Payload Structure

| Field | Type | Description |
|-------|------|-------------|
| `setup_date` | DATE | Target setup date (when target was created) |
| `branch_code` | VARCHAR | Store/branch code |
| `team_code` | VARCHAR | Team identifier |
| `staff_email` | VARCHAR | Staff email (FK to account.email) |
| `sales_channel` | VARCHAR | Sales channel (e.g., "web", "retail", "shopee") |
| `product_sku` | VARCHAR | Product SKU (if product-specific target) |
| `metric_code` | VARCHAR | Metric type (e.g., "revenue", "units", "transaction_count") |
| `target_value` | DECIMAL(15,2) | Target value (in VND for revenue, units for quantity) |
| `period` | VARCHAR | Target period (YYYY-MM format) |
| `description` | VARCHAR | Notes/description |

### Analytics Integration

Join to `dim_staff`, `dim_locations`, and `fact_orders` to calculate achievement:

```sql
SELECT
  t.period,
  ds.staff_name,
  t.metric_code,
  t.target_value,
  SUM(fo.net_amount) as actual_revenue,
  ROUND(100.0 * SUM(fo.net_amount) / t.target_value, 1) as achievement_pct
FROM sapo_raw.targets_raw t
LEFT JOIN dim_staff ds ON t.staff_email = ds.email
LEFT JOIN fact_orders fo
  ON ds.staff_id = fo.assignee_id
  AND SUBSTRING(CAST(fo.created_at AS VARCHAR), 1, 7) = t.period
WHERE t.metric_code = 'revenue'
GROUP BY t.period, ds.staff_name, t.metric_code, t.target_value
```

---

## unknown (sapo_raw.unknown)

**Business Purpose:** Catch-all for webhook events that couldn't be properly classified by entity type.

**Ingest Methods:** `webhook` only

**Current State:** ~4,600 rows (nearly all are orders)

**Root Cause:** Webhook routing occasionally fails to classify entity type correctly or the webhook payload is missing the expected entity-type header.

### Envelope

```
entity_id: auto-generated row ID
entity_type: "unknown"
ingest_method: "webhook"
event_timestamp: Webhook receipt timestamp (TIMESTAMPTZ)
event_type: "create" | "update"
```

### Payload Structure

Variable structure — typically mirrors an order payload based on inspection:

```json
{
  "id": 12345678,
  "code": "SON000001",
  "status": "finalized",
  "fulfillment_status": "unshipped",
  "payment_status": "paid",
  "customer_id": 9876543,
  "order_line_items": [...],
  "fulfillments": [...],
  ...
}
```

### Status Distribution (Last Check)

| Status | Count | % | Notes |
|--------|-------|---|-------|
| `finalized` | 3,526 | 75.9% | Confirmed, awaiting fulfillment |
| `completed` | 573 | 12.3% | Delivered/completed |
| `draft` | 441 | 9.5% | Not yet confirmed |
| `cancelled` | 106 | 2.3% | Cancelled orders |

### Data Quality Issues

1. **Misclassification**: All 4,600 rows appear to be orders based on payload structure (presence of `order_line_items`, `fulfillment_status`).
2. **Routing failure**: Webhook ingestion loses entity-type classification.
3. **Impact**: Orders in `unknown` table are not deduplicated with `order` table; analytics double-counts these orders if both tables are queried.

### Remediation Strategy

**Automated Re-Classification:**

```python
# Proposed logic: inspect payload structure to infer entity_type
def infer_entity_type(payload: dict) -> str:
    if 'order_line_items' in payload and 'fulfillment_status' in payload:
        return 'order'
    elif 'customer_group_name' in payload and 'addresses' in payload:
        return 'customer'
    elif 'variants' in payload and 'category' in payload:
        return 'product'
    else:
        return 'unknown'
```

**Recommended steps:**
1. Add entity-type inference to webhook ingestion pipeline
2. Re-classify existing `unknown` rows as `order`
3. Deduplicate with `order` table using `(entity_id, event_timestamp)`
4. Monitor webhook routing to prevent future misclassifications

---

## External Data Integration

### Google Sheets Workflow

1. **User uploads** data to a Google Sheet (or automated tool writes to it)
2. **dlt ingestion pipeline** periodically reads the sheet
3. **Rows are inserted** into `sapo_raw` with `ingest_method="google_sheet"`
4. **Envelope metadata** tracks when each row was ingested

### Considerations

- **No real-time sync** — Depends on ingestion schedule (daily, hourly, etc.)
- **Manual updates** — Requires user to edit sheet or external system to push updates
- **Data validation** — Recommended to validate columns and data types before ingestion
- **Schema changes** — If sheet columns change, the pipeline may break; schema versioning is important

### Related Tables

- `fact_targets` — Staging of targets_raw with proper dimensional links
- `fact_marketing_spend` — Staging of marketing_spend_raw (planned)
- `dim_channels` — Channel mapping for marketing spend analysis

---

## Related Documentation

- **[Envelope Schema](./envelope-schema.md)** — Shared outer structure
- **[Core Business Entities](./core-entities.md)** — `order`, `customer`, `product`, `account`
- **[Logistics & Inventory](./logistics-inventory.md)** — `fulfillment`, `purchase_order`, `order_return`, `stock_adjustment`
- **[Reference Data](./reference-data.md)** — `customer_group`, `price_list`
- **[Raw Data Sources Reference](../raw-data-sources.md)** — Complete technical specification
