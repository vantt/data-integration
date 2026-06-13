# Customer & Identity Domain — Schema Scan Report

> **Date:** 2026-06-13 | **Scope:** Warehouse read-only scan for CRM architect  
> **Purpose:** Map every customer entity across all layers; document canonical keys, dedup logic, enrichment gaps

---

## 1. Entity Map (Layer-by-Layer)

### 1.1 Raw Sources (`sapo_v2_raw`)

| Source Table | Raw Field | Meaning |
|---|---|---|
| `customer` | `$.id` | Sapo customer integer ID (business key) |
| `customer` | `$.code` | Business-assigned customer code (e.g. CTN00014) |
| `customer` | `$.phone_number` | Phone — primary contact for CS/Sales outreach |
| `customer` | `$.email` | Email |
| `customer` | `$.name` | Full name |
| `customer` | `$.status` | Active/inactive on Sapo |
| `customer` | `$.birthday` / `$.dob` | DOB (two fields, consolidated by COALESCE) |
| `customer` | `$.sex` / `$.gender` | Gender (two fields, consolidated by COALESCE) |
| `customer` | `$.customer_group` | Group code/name — raw basis for customer_type mapping |
| `customer` | `$.addresses[0].*` | First address: city, province, district, ward, address1, country |
| `customer` | `$.total_expense` | Lifetime spend (Sapo-maintained, VAT-inclusive; renamed `total_spend` upstream) |
| `customer` | `$.order_count` | Order count (Sapo-maintained, not warehouse-computed) |
| `customer` | `$.loyalty_point` | Loyalty points balance |
| `customer` | `$.debt` | AR debt balance |
| `customer` | `$.created_on` | Customer creation timestamp |
| `customer` | `$.modified_on` | Last-modified timestamp — dedup sort key |
| `customer_group` | `$.id` | Group ID |
| `customer_group` | `$.code` | Group code (TYPE_WHOLESALE, TYPE_RETAIL, etc.) |
| `customer_group` | `$.name` | Group display name |
| `customer_group` | `$.group_type` | Sapo group type |
| `customer_group` | `$.condition_type` | Manual vs auto condition |
| `customer_group` | `$.count_customer` | Count (Sapo-maintained) |
| `account` | `$.id` | Account/Staff ID |
| `account` | `$.email` / `$.user_name` | Staff identifier |
| `account` | `$.full_name` / `$.first_name` / `$.last_name` | Staff name |
| `account` | `$.mobile` | Staff phone |
| `account` | `$.status` | Staff status |
| `account` | `$.tenant_id` | Tenant identifier |

**Notes:**
- All raw fields extracted from JSON payload in `src_` layer; payload discarded after extraction.
- `customer_group` model is **disabled** (`enabled=false`) — groups are only accessible via the embedded `$.customer_group` string in the customer payload.
- No raw UTM/source/acquisition marketing field exists on Sapo customer payload.

---

### 1.2 Source Layer (`src_`)

| Model | Layer | Materialization | Grain | PK / Unique Key |
|---|---|---|---|---|
| `src_sapo_v2_customers` | source | incremental (delete+insert) | 1 row / `sapo_customer_id` | `sapo_customer_id` |
| `src_sapo_v2_customer_groups` | source | incremental (delete+insert) | 1 row / `customer_group_id` | `customer_group_id` (DISABLED) |
| `src_sapo_v2_accounts` | source | incremental (delete+insert) | 1 row / `account_id` | `account_id` |

**Columns: `src_sapo_v2_customers`**

| Column | RAW vs COMPUTED | Meaning |
|---|---|---|
| `entity_id` | RAW | Content-addressed event ID from dlt pipeline |
| `sapo_customer_id` | RAW (from `$.id`) | Sapo integer customer ID — business natural key |
| `customer_code` | RAW (from `$.code`) | Business code (e.g. CTN prefix groups) |
| `full_name` | RAW | Customer full name |
| `phone_number` | RAW | Primary phone — only contactable channel |
| `email` | RAW | Email |
| `status` | RAW | Active/inactive on Sapo |
| `dob` | RAW (COALESCE birthday/dob) | Date of birth |
| `sex` | RAW (COALESCE sex/gender) | Gender |
| `customer_group` | RAW | Raw group code/name string (embedding of customer_group entity) |
| `city` / `province` / `district` / `ward` / `address1` / `country` | RAW (addresses[0]) | Address — first address only |
| `total_expense` | RAW (Sapo-maintained) | Lifetime spend (Sapo running total; NOT warehouse-computed) |
| `orders_count` | RAW (Sapo-maintained) | Order count (Sapo running total) |
| `loyalty_point` | RAW | Loyalty points |
| `debt` | RAW | AR debt balance |
| `created_on` / `modified_on` | RAW | Timestamps (string, cast downstream) |
| `event_timestamp` / `ingest_method` / `_dlt_load_id` | PIPELINE | Ingestion metadata |

---

### 1.3 Staging Layer (`stg_`)

| Model | Materialization | Grain | Notes |
|---|---|---|---|
| `stg_sapo_v2_customers` | view | 1 row / `sapo_customer_id` | Thin pass-through; consolidates birthday/dob |
| `stg_sapo_v2_accounts` | view | 1 row / `account_id` | Coalesces name fields; casts timestamps |

No further dedup or transformation — all dedup done in `src_`.

---

### 1.4 Standard Layer (`std_`)

| Model | Materialization | Grain | Key Changes |
|---|---|---|---|
| `std_customers` | view | 1 row / `customer_id` | Renames `sapo_customer_id` → `customer_id`; adds `source_system='sapo'`, `source_version='v2'`; renames `total_expense` → `total_spend` |
| `std_accounts` | view | 1 row / `account_id` | Adds `source_system='sapo'`, `source_version='v2'` |

**`std_customers` columns:**

| Column | RAW vs COMPUTED | Meaning |
|---|---|---|
| `customer_id` | RAW | = `sapo_customer_id` (Sapo integer ID, used as warehouse natural key) |
| `customer_code` | RAW | Business code |
| `source_system` | COMPUTED | Literal 'sapo' |
| `source_version` | COMPUTED | Literal 'v2' |
| `full_name` / `email` / `phone` | RAW | Contact fields |
| `city` / `province` / `district` / `ward` / `address1` / `country` | RAW | Address |
| `birth_date` / `gender` | RAW | Demographics |
| `customer_group` | RAW | Group code/name string |
| `loyalty_points` | RAW | Points balance |
| `total_spend` | RAW (renamed) | Lifetime spend from Sapo (not warehouse-computed) |
| `order_count` | RAW (renamed) | Order count from Sapo |
| `debt` | RAW | AR debt |
| `created_at` / `updated_at` | RAW (cast TIMESTAMPTZ) | Timestamps |

---

### 1.5 Dimension Base (`dim_customers_base`)

| Attribute | Value |
|---|---|
| **Model** | `dim_customers_base` |
| **Layer** | mart/core |
| **Materialization** | incremental (unique_key=`customer_key`) |
| **Grain** | 1 row / `customer_key` (includes Unknown sentinel row) |
| **Surrogate Key** | `customer_key` = MD5(`customer_id`) |
| **Natural Key** | `customer_id` (= `sapo_customer_id` string) |
| **Business Key** | `customer_code` |
| **Purpose** | Circular dependency breaker — provides `customer_key` to `fact_orders` before metrics are available |
| **NOT for serving** | End users should use `dim_customers` |

Columns: `customer_key`, `customer_id`, `customer_code`, `full_name`, `email`, `phone`, `birth_date`, `gender`, `customer_group`, `loyalty_points`, `city`, `province`, `district`, `ward`, `address1`, `country`, `created_at`, `updated_at`.

**Unknown sentinel row:** `customer_key = MD5('Unknown')`, all fields = 'Unknown'/NULL — for orders without a linked customer.

---

### 1.6 Dimension Final (`dim_customers`)

**Canonical serving table for all customer analysis.**

| Attribute | Value |
|---|---|
| **Model** | `dim_customers` |
| **Layer** | mart/core |
| **Materialization** | incremental; post_hook exports PARQUET to rolling location |
| **Grain** | 1 row / `customer_key` |
| **Canonical Key** | `customer_key` (surrogate, MD5 of `customer_id`) |

**Full Column Inventory:**

| Column | RAW vs COMPUTED | Source | Meaning |
|---|---|---|---|
| `customer_key` | COMPUTED | `dim_customers_base` | Surrogate key (MD5 of customer_id) |
| `customer_id` | RAW | Sapo `$.id` | Natural key — Sapo integer ID |
| `customer_code` | RAW | Sapo `$.code` | Business code |
| `full_name` | RAW | Sapo | Name |
| `email` | RAW | Sapo | Email |
| `phone` | RAW | Sapo `$.phone_number` | Phone |
| `city` / `province` / `district` / `ward` / `address1` / `country` | RAW | Sapo | Address fields |
| `birth_date` | RAW | Sapo | DOB |
| `gender` | RAW | Sapo | Gender |
| `customer_group` | RAW | Sapo | Raw group code string (kept for reference) |
| `loyalty_points` | RAW | Sapo | Loyalty balance |
| `created_at` | RAW | Sapo | Customer creation date |
| `customer_type` | COMPUTED | CASE on `customer_group` | Commercial type: RETAIL / WHOLESALE / PARTNER / STAFF / KOL / CROSSBORDER |
| `value_group` | COMPUTED | `int_customer_metrics` | RFM tier: VALUE_VIP / GOLD / SILVER / BRONZE |
| `lifecycle_stage` | COMPUTED | `int_customer_metrics` | LIFECYCLE_NEW / ACTIVE / AT_RISK / CHURNED |
| `customer_status` | COMPUTED | Recency (RFM) | Active (≤30d) / At Risk (≤90d) / Churned (>90d) |
| `geo_region` | COMPUTED | `province` | GEO_HCMC / HANOI / MEKONG / CENTRAL / OTHER |
| `channel_preference` | COMPUTED | `int_customer_metrics` | CHANNEL_SOCIAL / MARKETPLACE / DIRECT / OFFLINE / OTHER |
| `product_affinity` | COMPUTED | `int_customer_metrics` | Brand >60% revenue share: PRODUCT_FINE_JAPAN / FG_CARE / FINE_CARE / MULTI |
| `payment_behavior` | COMPUTED | `int_customer_metrics` | PAYMENT_COD (>70% COD) / PAYMENT_PREPAID |
| `discount_sensitivity` | COMPUTED | `int_customer_metrics` | PROMO_DEPENDENT (>70%) / PROMO_MIXED (>30%) / FULL_PRICE |
| `acquisition_source` | COMPUTED | First order's `channel_name` | Proxy for acquisition; NULL if no orders |
| `first_order_date` / `last_order_date` | COMPUTED | `int_customer_metrics` | First/last active order timestamps |
| `recency_days` | COMPUTED | Days since last order | |
| `frequency` / `lifetime_value` / `order_count` | COMPUTED | `int_customer_metrics` | RFM metrics |
| `lifespan_days` | COMPUTED | Days first→last order | |
| `avg_days_between_orders` | COMPUTED | `int_customer_metrics` | Inter-purchase cycle; NULL for 1-time buyers |
| `avg_order_spend` | COMPUTED | `int_customer_metrics` | Avg `total_collected` per active order |
| `discount_order_rate` / `cancel_rate` | COMPUTED | `int_customer_metrics` | Behavioral rates |
| `predicted_next_purchase_date` | COMPUTED | last_order + avg_days | NULL for 1-time buyers |
| `next_purchase_signal` | COMPUTED | recency vs avg_cycle | OVERDUE / DUE_SOON / ON_TRACK / NULL |
| `last_purchased_product` / `last_purchased_sku` | COMPUTED | `int_customer_metrics` | Most-recent paid SKU; NULL = only gift lines |
| `top_affinity_product` / `top_affinity_sku` | COMPUTED | `int_customer_metrics` | Most-frequently ordered paid SKU |
| `second_affinity_product` | COMPUTED | `int_customer_metrics` | #2 affinity SKU; NULL if only 1 distinct SKU |
| `lifetime_gross_profit` / `lifetime_contribution_margin` | COMPUTED | `int_customer_economics` | Margin (has_cogs orders only) |
| `avg_order_contribution_margin_pct` / `margin_cogs_coverage_pct` | COMPUTED | `int_customer_economics` | Margin quality metrics |
| `is_margin_negative` | COMPUTED | `int_customer_economics` | TRUE if negative lifetime CM |
| `is_contactable` | COMPUTED | phone IS NOT NULL | Reachability flag |
| `is_us_gift_recipient` | COMPUTED | customer_group LIKE pattern | CrossBorder gift recipient flag |
| `source_updated_at` / `last_modified_at` | COMPUTED | MAX(source_updated_at, metric_calculated_at) | Watermark timestamps |

---

### 1.7 Intermediate Models

| Model | Grain | Purpose |
|---|---|---|
| `int_customer_metrics` | 1 row / `customer_key` | RFM aggregations, channel/product/payment behavior, SKU affinity, behavioral metrics |
| `int_customer_economics` | 1 row / `customer_key` | Lifetime gross profit, contribution margin (from `fact_order_economics`) |
| `int_customer_entry_attributes` | 1 row / `customer_key` (RETAIL only) | Immutable acquisition-time attributes: first_order_month, acquisition_channel, entry_product, basket_size, entry_value_band |

---

### 1.8 Mart Models (Customer Domain)

| Model | Grain | Scope | Purpose |
|---|---|---|---|
| `mart_customer_action_queue` | 1 row / `customer_key` (actionable only) | RETAIL, order_count>0 | Prioritized outreach queue; action_type: CALL_NOW / REORDER_NUDGE / REORDER_PREEMPT / WIN_BACK / SECOND_ORDER / HIGH_CANCEL_RISK |
| `mart_customer_status_snapshot_monthly` | 1 row / (customer_key × snapshot_month) | RETAIL | Monthly status history; WARNING: survivorship bias (uses current last_order_date) |
| `mart_cohort_retention` | 1 row / (cohort_dimension × cohort_value × window_type × period_n) | RETAIL, cohort_size≥10 | 8 single + 2 composite cohort axes; relative + calendar windows |
| `mart_retention_waterfall_monthly` | 1 row / (snapshot_month × status × value_group × product_affinity × channel_preference) | RETAIL | True point-in-time retention (fact_orders-based, no survivorship bias) |

---

## 2. Staff / Account Entity (Separate from Customer)

| Model | Grain | Key | Purpose |
|---|---|---|---|
| `src_sapo_v2_accounts` | 1 row / `account_id` | `account_id` | Raw Sapo staff accounts |
| `stg_sapo_v2_accounts` | 1 row / `account_id` | `account_id` | Cleaned staff data |
| `std_accounts` | 1 row / `account_id` | `account_id` | Standardized; `source_system='sapo'` |

**Staff fields:** `account_id`, `staff_name` (coalesced), `staff_email`, `staff_phone`, `status`, `tenant_id`.  
**FK to orders:** `fact_orders.seller_user_id` (primary) and `creator_user_id` (fallback) → resolves to `dim_staff`.

---

## 3. Canonical Customer Key Chain

```
Sapo API ($.id integer)
    ↓
src_sapo_v2_customers.sapo_customer_id  ← business dedup key (latest modified_on wins)
    ↓
std_customers.customer_id               ← same value, renamed, + source_system tag
    ↓
dim_customers_base.customer_id          ← natural key for fact table FKs
dim_customers_base.customer_key         ← surrogate key = MD5(customer_id)
    ↓
dim_customers.customer_key              ← CANONICAL SERVING KEY
    ↓ (FK)
fact_orders.customer_key
fact_sales.customer_key
int_customer_metrics.customer_key
int_customer_economics.customer_key
mart_customer_action_queue.customer_key
```

**Key summary:**
- `customer_key` (surrogate, MD5 of `customer_id`) — join key for all warehouse joins
- `customer_id` = `sapo_customer_id` = Sapo integer ID — bridge to Sapo API
- `customer_code` — business-assigned code (optional, can be NULL)

---

## 4. Deduplication / Identity-Resolution Logic

### 4.1 Two-Level Dedup in `src_` (All customer entities)

**Level 1 — Technical dedup (entity_id):**
```sql
ROW_NUMBER() OVER (
    PARTITION BY entity_id
    ORDER BY
        try_cast(modified_on AS TIMESTAMPTZ) DESC NULLS LAST,
        CASE ingest_method WHEN 'webhook' THEN 3 WHEN 'history_log' THEN 2 ELSE 1 END DESC
) = 1
```
Removes same event ingested via multiple channels (webhook + batch_sync for same payload).

**Level 2 — Business dedup (sapo_customer_id):**
```sql
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY sapo_customer_id
    ORDER BY
        try_cast(modified_on AS TIMESTAMPTZ) DESC NULLS LAST,
        CASE ingest_method WHEN 'webhook' THEN 1 WHEN 'history_log' THEN 2 ELSE 3 END
) = 1
```
Keeps latest version when same customer has multiple events. Webhook wins over history_log for same timestamp.

**Incremental safety:** New load UNIONs with existing rows for same customer_ids before dedup — prevents late load from overwriting a more-recent cached record.

### 4.2 No Cross-Customer Dedup (Golden Record Gap)

**CRITICAL:** There is NO cross-customer identity resolution. Dedup is only within the same `sapo_customer_id`. The warehouse does NOT:
- Merge duplicate customers with different Sapo IDs but same phone/email
- Detect customers registered under multiple phones
- Create a golden record from multiple Sapo customer records

**Identity relies entirely on Sapo's own customer dedup.** If Sapo has duplicate records for the same real person, the warehouse inherits them as separate customers.

### 4.3 No SCD2 / Historical Profiles

Customer dimension is a Type 1 SCD (current state only). There is no history of address changes, name changes, or group membership changes over time.

---

## 5. Key Relationships (FK Map)

```
dim_customers_base.customer_key → fact_orders.customer_key
dim_customers.customer_key      → fact_orders.customer_key (via dim_customers_base)
dim_customers.acquisition_source → dim_channels.channel_name (validated by relationships test)
dim_customers.customer_group    → (no FK; raw string; customer_group entity disabled)
fact_orders.seller_user_id      → dim_staff.account_id
fact_orders.channel_key         → dim_channels.channel_key
```

---

## 6. customer_type Derivation & Migration State

```sql
CASE
    WHEN customer_group LIKE '%WHOLESALE%'        THEN 'WHOLESALE'
    WHEN customer_group LIKE '%TYPE_PARTNER%'
      OR customer_group LIKE '%KY_GUI%'           THEN 'PARTNER'
    WHEN customer_group LIKE '%TYPE_STAFF%'        THEN 'STAFF'
    WHEN customer_group LIKE '%TYPE_KOL%'          THEN 'KOL'
    WHEN customer_group LIKE '%TYPE_CROSSBORDER%'
      OR customer_group LIKE '%CTN00014%'          THEN 'CROSSBORDER'
    ELSE                                            'RETAIL'  -- default
END
```

**Migration caveat (from MEMORY.md + dimensions.md):**
- Only ~3 WHOLESALE records are live in production (new TYPE_* group codes as of 2026-04-19)
- Historical B2B data pre-2026 not reliably tagged — old group codes default to RETAIL
- `customer_type` WHOLESALE/PARTNER/STAFF/KOL are unreliable for historical trend before 2026
- `customer_type` detection is pattern-matched on the raw group string, not on a FK to the disabled `customer_group` table

---

## 7. Scope / Segment Architecture

| Scope | Rule | Use case |
|---|---|---|
| `scope_sales` | `is_sales_channel = true` | All sales orders |
| `scope_retail` | `scope_sales AND customer_type='RETAIL'` | Retail KPIs, promo analysis, cohort |
| `scope_b2b` | `scope_sales AND customer_type IN ('WHOLESALE','PARTNER')` | B2B analysis |
| CROSSBORDER | `is_sales_channel=false` | Excluded from all scopes |

---

## 8. Timezone Notes

- `created_on` / `modified_on` from Sapo are cast to `TIMESTAMPTZ` at `std_` layer.
- All timestamps stored UTC in warehouse; Metabase displays ICT via session TZ.
- `date_key` is pre-computed ICT — use for date filters, not `ordered_at::DATE`.
- Customer acquisition entry attributes use `ordered_at` (TIMESTAMPTZ) for cohort month assignment — ICT-correct.

---

## 9. RAW vs COMPUTED Fields Summary

| Category | RAW (source of truth, Sapo write-back candidates) | COMPUTED (warehouse-only) |
|---|---|---|
| Identity | `customer_id`, `customer_code` | `customer_key` (surrogate) |
| Contact | `phone`, `email`, `full_name` | `is_contactable` |
| Demographics | `birth_date`, `gender` | `geo_region` |
| Address | `province`, `district`, `ward`, `address1`, `country`, `city` | — |
| Grouping | `customer_group` (raw string) | `customer_type`, `value_group`, `lifecycle_stage` |
| Sapo financials | `loyalty_points`, `debt`, `total_spend` (Sapo-maintained totals) | All RFM metrics, contribution margin |
| Timestamps | `created_at`, `updated_at` | `last_modified_at`, `metric_calculated_at` |
| Behavior | — | `channel_preference`, `product_affinity`, `payment_behavior`, `discount_sensitivity`, `next_purchase_signal` |
| SKU affinity | — | `last_purchased_product/sku`, `top/second_affinity_*` |
| Economics | — | `lifetime_gross_profit`, `lifetime_contribution_margin`, `is_margin_negative` |
| Acquisition | — | `acquisition_source` (proxied from first order channel) |

---

## 10. CRM Enrichment Gaps

Fields a salesperson would want in a CRM that do NOT exist today:

| Gap | Priority | Notes |
|---|---|---|
| **Cross-customer dedup / golden record** | CRITICAL | No identity resolution across Sapo customer IDs. If same person has 2 Sapo records (2 phones), warehouse shows 2 separate customers. CRM MUST own this. |
| **UTM / marketing acquisition source** | HIGH | No UTM params on Sapo customer payload. `acquisition_source` is only a proxy (first-order channel). CRM needs true marketing attribution (ad campaign, keyword, referral). |
| **Contact history / interaction log** | HIGH | No call log, message log, or CRM touch history. Current system only tracks WHAT was purchased, not sales conversations, follow-ups, or CS tickets. |
| **SCD2 / historical profile snapshots** | HIGH | Only current-state data. No history of name/phone/address changes, group migrations, or when customer_type was assigned. CRM needs SCD2 for compliance + trust. |
| **Custom CRM fields / tags** | MEDIUM | No free-form tags, salesperson notes, deal stage, opportunity pipeline stage, or custom segmentation labels. |
| **Multi-address management** | MEDIUM | Only `addresses[0]` extracted. Customers with multiple delivery addresses lose the others. |
| **Social/OA channel IDs** | MEDIUM | No Zalo OA user ID, Facebook PSID, TikTok ID — only phone is tracked as a contactable channel. Limits re-engagement automation. |
| **Consent / PDPA flags** | MEDIUM | No marketing consent, opt-in/opt-out, or communication preference stored. Required for PDPA compliance in CRM. |
| **Debt / AR reconciliation** | LOW | `debt` field from Sapo is unreliable (noted in MEMORY: `fact_payments` is empty/1-row placeholder). CRM would need real AR balance from MISA. |
| **Wholesale relationship details** | LOW | B2B customers only identified via group code pattern matching. No contract terms, credit limit, assigned account manager, or reseller tier in warehouse. |

---

## 11. Data Quality Caveats for CRM Architect

1. **customer_type migration incomplete** — ~3 WHOLESALE records live; all pre-2026 B2B defaults to RETAIL. Do not trust for B2B segmentation history.
2. **`customer_group` entity disabled** — `src_sapo_v2_customer_groups` is `enabled=false`. Group metadata (description, condition rules) not synced. Only the raw group string embedded in customer record is available.
3. **`debt` unreliable** — `fact_payments` has 1 all-NULL placeholder row. AR/cashflow must use soft `payment_status` flag (unverified).
4. **`total_spend` / `orders_count` are Sapo-maintained** — Not recalculated from warehouse facts. May drift from `int_customer_metrics.monetary_value` / `frequency` if Sapo's internal counts lag.
5. **No dedup across Sapo customer IDs** — Duplicate real-person records in Sapo propagate into warehouse unchanged.
6. **`is_contactable` = phone only** — No Zalo OA, no email click-through data. All outreach funnels through phone.
7. **`customer_group` pattern-matching** — Customer type detection is fragile LIKE-match on raw string. New group codes not following TYPE_* naming convention default silently to RETAIL.
8. **Sapo `history_log` truncation** — Sapo truncates history over time. Pre-2021 customer events may be lost. Historical accuracy for tenure/acquisition dating degrades for oldest customers.

---

## Open Questions

1. **CRM golden record strategy**: Will the CRM be the system of record for dedup (phone/email matching across Sapo IDs)? If so, how does the CRM customer key map back to warehouse `customer_key` (1:N)?
2. **Write-back scope**: Which RAW fields (phone, email, name, address, customer_group) should the CRM be able to update back into Sapo? Is there a Sapo API write-back path?
3. **customer_type source of truth**: Should CRM own `customer_type` classification (overriding Sapo group codes), or should it remain Sapo-group-driven? The migration to TYPE_* codes is incomplete.
4. **`customer_group` entity re-enable**: Is there a plan to re-enable `src_sapo_v2_customer_groups`? Currently group metadata (rules, conditions) is inaccessible in warehouse.
5. **Loyalty points sync**: CRM needs real-time loyalty balance. Warehouse is a 24h+ lag snapshot. Should loyalty balance be fetched from Sapo API directly in CRM, or use warehouse as cache?
6. **PDPA compliance**: Is there a consent management requirement for the CRM? None exists in current warehouse.
7. **Debt/AR**: Will the CRM surface AR balance? If so, needs MISA integration — warehouse `debt` and `fact_payments` are unreliable.
