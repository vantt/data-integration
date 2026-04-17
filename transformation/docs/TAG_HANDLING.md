# Tag Handling System

> Comprehensive guide for order & customer tag processing, categorization, and monitoring.

## Overview

Tags are semi-structured, multi-value JSON arrays attached to orders and customers in Sapo. They encode:
- Channel attribution (Shopee, Lazada storefronts)
- Order classification (consignment, sample, gift)
- Payment/fulfillment status
- Marketing attribution (Ad IDs, Post IDs)
- Deferred discounts (CK SAU codes)

This system provides:
1. **Structured extraction** — Unnest JSON arrays into queryable rows
2. **Semantic categorization** — Pattern-based classification via seed table
3. **New tag monitoring** — Alert on uncategorized tags for review

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              RAW LAYER                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  sapo_raw.order (parquet)                                               │
│  └── payload.tags = '["Shopee","Shopee_JPC SHOP","CK SAU BS 30%"]'     │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           STAGING LAYER                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  src_sapo_orders                                                        │
│  └── tags VARCHAR = '["Shopee","Shopee_JPC SHOP","CK SAU BS 30%"]'     │
│       (JSON string, not yet unnested)                                   │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        INTERMEDIATE LAYER                                │
├─────────────────────────────────────────────────────────────────────────┤
│  int_order_tags (VIEW)                 ref_tag_categories (SEED)        │
│  ├── order_id                          ├── pattern                      │
│  ├── tag_value  ◄──── JOIN ON ────────►├── category                     │
│  └── tag_category                      └── match_type                   │
│                                                                          │
│  Output (1 row per order-tag pair):                                     │
│  ┌──────────┬─────────────────────┬──────────────────────┐              │
│  │ order_id │ tag_value           │ tag_category         │              │
│  ├──────────┼─────────────────────┼──────────────────────┤              │
│  │ 12345    │ Shopee              │ channel_platform     │              │
│  │ 12345    │ Shopee_JPC SHOP     │ channel_storefront   │              │
│  │ 12345    │ CK SAU BS 30%       │ discount_deferred    │              │
│  └──────────┴─────────────────────┴──────────────────────┘              │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         MONITORING LAYER                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  monitor_uncategorized_tags (VIEW)                                      │
│  └── Lists tags with category = 'uncategorized' for review             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Step 1: Raw Ingestion (dlt)

Tags are ingested as part of the order payload via dlt pipelines:

```python
# orchestration/assets/sapo_ingestion.py
# Tags come from Sapo API as JSON array in order.tags field
{
    "id": 12345,
    "code": "SON12345",
    "tags": ["Shopee", "Shopee_JPC SHOP", "CK SAU BS 30%"],
    ...
}
```

**Output:** Parquet files in `app_data/data_lake/sapo_raw/order/`

### Step 2: Source Extraction (dbt)

`src_sapo_orders` extracts tags as VARCHAR:

```sql
-- transformation/models/staging/src_sapo_orders.sql (line 151)
json_extract_string(payload, '$.tags') as tags
```

**Output:** `tags` column contains JSON string like `'["Shopee","Shopee_JPC SHOP"]'`

### Step 3: Tag Unnesting & Categorization (dbt)

`int_order_tags` unnests and categorizes:

```sql
-- transformation/models/intermediate/int_order_tags.sql
SELECT
    order_id,
    tag_value,
    COALESCE(m.category, 'uncategorized') as tag_category
FROM unnested_tags t
LEFT JOIN ref_tag_categories m ON pattern_match(t.tag_value, m.pattern)
```

**Output:** One row per order-tag pair with semantic category

### Step 4: Monitoring (dbt)

`monitor_uncategorized_tags` surfaces new/unknown tags:

```sql
-- transformation/models/monitoring/monitor_uncategorized_tags.sql
SELECT tag_value, COUNT(*) as order_count
FROM int_order_tags
WHERE tag_category = 'uncategorized'
GROUP BY 1
```

**Output:** List of tags needing categorization

---

## File Structure

```
transformation/
├── seeds/
│   ├── ref_tag_categories.csv          # Pattern → Category mapping
│   └── properties.yml                  # Column types for seeds
├── models/
│   ├── intermediate/
│   │   └── int_order_tags.sql          # Unnest + categorize
│   └── monitoring/
│       └── monitor_uncategorized_tags.sql  # Alert on new tags
└── docs/
    └── TAG_HANDLING.md                 # This document
```

---

## Seed: ref_tag_categories.csv

### Schema

| Column | Type | Description |
|--------|------|-------------|
| pattern | VARCHAR | Match pattern (supports %, _) |
| category | VARCHAR | Semantic category name |
| match_type | VARCHAR | `exact`, `prefix`, `contains` |
| priority | INTEGER | Lower = higher importance (1-99) |
| description | VARCHAR | Human-readable explanation |

### Priority Guidelines

When a tag matches multiple patterns, **lowest priority number wins**:

| Priority | Category Type | Rationale |
|----------|--------------|-----------|
| 1 | `order_type_*` | Defines order nature, affects reporting logic |
| 2 | `discount_deferred` | Affects revenue calculation |
| 3 | `expense_reimbursement` | Affects accounting |
| 4 | `invoice_status` | Operational tracking |
| 5 | `payment_status` | Operational tracking |
| 6 | `fulfillment_status` | Operational tracking |
| 10 | Channel, marketing, etc. | Standard categories |
| 20 | `order_note` | Low-value metadata |
| 99 | `system_test` | Ignore in analytics |

**Example conflict resolution:**
- Tag: "ĐƠN HÀNG KÝ GỬI THANH TOÁN" matches both `%KÝ GỬI%` (priority 1) and `%THANH TOÁN%` (priority 5)
- Result: `order_type_consignment` (priority 1 wins)

### Match Types

| Type | SQL Equivalent | Example |
|------|---------------|---------|
| `exact` | `tag = pattern` | `Shopee` matches only "Shopee" |
| `prefix` | `tag LIKE pattern` | `Shopee_%` matches "Shopee_JPC SHOP" |
| `contains` | `tag LIKE pattern` | `%ký gửi%` matches "Hàng ký gửi" |

### Categories

| Category | Description | Example Tags |
|----------|-------------|--------------|
| `channel_platform` | Marketplace/social platform | Shopee, Lazada, sapoweb |
| `channel_storefront` | Specific store within platform | Shopee_JPC SHOP |
| `order_type_consignment` | Consignment/ký gửi orders | Hàng ký gửi, Ký gửi |
| `order_type_sample` | Sample/sampling orders | HÀNG MẪU, Sample |
| `order_type_gift` | Gift/promotional orders | Quà tặng, Hàng tặng |
| `discount_deferred` | Post-sale discount codes | CK SAU BS 30% |
| `marketing_ad` | Facebook Ad attribution | Ad_id_120232701042310524 |
| `marketing_post` | Facebook Post attribution | Post_ID_t_3079788605491275 |
| `marketing_customer` | Facebook Customer tracking | ID Khách hàng _7386672441400850 |
| `marketing_affiliate` | Affiliate program | ECOMOBI BOOKING, KOC Review |
| `invoice_status` | Invoice issuance tracking | Xuất hóa đơn |
| `payment_status` | Payment confirmation | Đơn hàng đã thanh toán |
| `fulfillment_status` | Delivery status | Giao hàng thành công |
| `shipping_type` | Shipping classification | Freeship, Ngoại thành |
| `social_page` | Facebook page attribution | page_Japan Premium Collection |
| `product_category` | Product line tags | Fucoidan, cordyceps |
| `uncategorized` | No pattern match (needs review) | — |

### Sample Data

```csv
pattern,category,match_type,priority,description
Shopee,channel_platform,exact,10,Shopee marketplace
Lazada,channel_platform,exact,10,Lazada marketplace
Shopee_%,channel_storefront,prefix,10,Shopee storefronts
Lazada_%,channel_storefront,prefix,10,Lazada storefronts
%ký gửi%,order_type_consignment,contains,1,Consignment orders
%KÝ GỬI%,order_type_consignment,contains,1,Consignment orders (uppercase)
%MẪU%,order_type_sample,contains,1,Sample orders
CK SAU%,discount_deferred,prefix,2,Deferred discount
TRẢ THƯỞNG%,expense_reimbursement,prefix,3,Reward payment
%hóa đơn%,invoice_status,contains,4,Invoice related
%thanh toán%,payment_status,contains,5,Payment status
%giao hàng%,fulfillment_status,contains,6,Delivery status
Ad_id_%,marketing_ad,prefix,10,Facebook Ad ID
Freeship,shipping_type,exact,10,Free shipping
Test_Monitor,system_test,exact,99,System test order
```

---

## Model: int_order_tags.sql

```sql
{{ config(
    materialized='view',
    tags=['intermediate', 'orders', 'tags']
) }}

-- =============================================================================
-- INTERMEDIATE: ORDER TAGS
-- =============================================================================
-- Purpose: Unnest order tags JSON array and categorize each tag
-- Input: src_sapo_orders.tags (JSON string)
-- Output: One row per order-tag pair with semantic category
-- =============================================================================

WITH raw_tags AS (
    SELECT
        order_id,
        TRIM(REPLACE(tag.value::VARCHAR, '"', '')) as tag_value
    FROM {{ ref('src_sapo_orders') }},
    LATERAL UNNEST(
        CASE 
            WHEN tags IS NOT NULL AND tags NOT IN ('', '[]') 
            THEN json_extract(tags, '$[*]')
            ELSE NULL
        END
    ) as tag(value)
    WHERE tags IS NOT NULL 
      AND tags NOT IN ('', '[]')
),

category_mappings AS (
    SELECT 
        pattern, 
        category, 
        match_type,
        LENGTH(pattern) as pattern_length  -- for priority (longer = more specific)
    FROM {{ ref('ref_tag_categories') }}
),

matched AS (
    SELECT
        t.order_id,
        t.tag_value,
        m.category as tag_category,
        m.pattern_length,
        ROW_NUMBER() OVER (
            PARTITION BY t.order_id, t.tag_value 
            ORDER BY m.pattern_length DESC NULLS LAST  -- prefer more specific pattern
        ) as rn
    FROM raw_tags t
    LEFT JOIN category_mappings m
        ON (m.match_type = 'exact' AND t.tag_value = m.pattern)
        OR (m.match_type = 'prefix' AND t.tag_value LIKE m.pattern)
        OR (m.match_type = 'contains' AND t.tag_value LIKE m.pattern)
)

SELECT
    order_id,
    tag_value,
    COALESCE(tag_category, 'uncategorized') as tag_category
FROM matched
WHERE rn = 1 OR rn IS NULL  -- rn IS NULL when no pattern matched
```

---

## Model: monitor_uncategorized_tags.sql

```sql
{{ config(
    materialized='view',
    tags=['monitoring', 'tags']
) }}

-- =============================================================================
-- MONITORING: UNCATEGORIZED TAGS
-- =============================================================================
-- Purpose: Surface new/unknown tags for review and categorization
-- Alert threshold: Any tag with category = 'uncategorized'
-- Action: Add pattern to ref_tag_categories.csv
-- =============================================================================

WITH uncategorized AS (
    SELECT
        tag_value,
        COUNT(DISTINCT order_id) as order_count,
        MIN(order_id) as sample_order_id
    FROM {{ ref('int_order_tags') }}
    WHERE tag_category = 'uncategorized'
    GROUP BY 1
)

SELECT
    tag_value,
    order_count,
    sample_order_id,
    CASE
        WHEN tag_value LIKE 'Shopee_%' THEN 'suggest: channel_storefront (Shopee)'
        WHEN tag_value LIKE 'Lazada_%' THEN 'suggest: channel_storefront (Lazada)'
        WHEN tag_value LIKE 'Tiki_%' THEN 'suggest: channel_storefront (Tiki)'
        WHEN tag_value LIKE 'Ad_id_%' THEN 'suggest: marketing_ad'
        WHEN tag_value LIKE 'Post_ID%' THEN 'suggest: marketing_post'
        WHEN tag_value LIKE 'ID Khách hàng%' THEN 'suggest: marketing_customer'
        WHEN tag_value LIKE 'page_%' THEN 'suggest: social_page'
        WHEN tag_value LIKE 'CK %' OR tag_value LIKE 'CHIẾT KHẤU%' THEN 'suggest: discount_deferred'
        ELSE 'review_needed'
    END as suggestion,
    CURRENT_TIMESTAMP as checked_at
FROM uncategorized
ORDER BY order_count DESC
```

---

## Configuration

### properties.yml (seeds)

Add to `transformation/seeds/properties.yml`:

```yaml
  - name: ref_tag_categories
    config:
      column_types:
        pattern: varchar
        category: varchar
        match_type: varchar
        description: varchar
    description: "Tag pattern to category mapping for order tag classification"
```

### dbt_project.yml

Add tags configuration (optional):

```yaml
models:
  sapo_warehouse:
    intermediate:
      +tags: ['intermediate']
    monitoring:
      +tags: ['monitoring']
```

### Environment Variables

No additional environment variables required. Tag handling uses existing dbt/DuckDB configuration.

| Variable | Used By | Purpose |
|----------|---------|---------|
| `DBT_DATA_LAKE_PATH` | src_sapo_orders | Read raw parquet |
| `DBT_EXPORT_PATH` | (if materialized table) | Write output |

---

## Dagster Integration

### No Changes Required

Tag handling models are **views** downstream of `src_sapo_orders`. They automatically refresh when:
1. dbt assets run (existing `dbt_sapo_warehouse` asset group)
2. No separate Dagster asset needed

### Optional: Monitoring Asset

If alerting on uncategorized tags is desired:

```python
# orchestration/assets/monitoring.py (optional)

@asset(
    deps=["dbt_sapo_warehouse"],
    group_name="monitoring"
)
def check_uncategorized_tags(context) -> None:
    """Alert if new uncategorized tags appear."""
    import duckdb
    
    db_path = os.environ["DBT_DATA_LAKE_PATH"] + "/sapo_warehouse.duckdb"
    con = duckdb.connect(db_path, read_only=True)
    
    result = con.execute("""
        SELECT tag_value, order_count 
        FROM monitor_uncategorized_tags 
        WHERE order_count >= 5
        ORDER BY order_count DESC
        LIMIT 10
    """).fetchall()
    
    if result:
        context.log.warning(f"Found {len(result)} uncategorized tags with 5+ orders")
        for tag, count in result:
            context.log.info(f"  {tag}: {count} orders")
```

---

## Maintenance Guide

### Regular Review Schedule

| Frequency | Task | Owner |
|-----------|------|-------|
| Weekly | Check `monitor_uncategorized_tags` for new tags | Data team |
| Monthly | Review category accuracy, merge similar patterns | Data lead |
| Quarterly | Audit unused patterns, update documentation | Data lead |

### Monitoring Commands

```bash
# === DOCKER (Production) ===

# Check uncategorized tags
docker exec data_platform python -c "
import duckdb
con = duckdb.connect('/app/app_data/data_lake/sapo_warehouse.duckdb', read_only=True)
result = con.execute('SELECT * FROM monitor_uncategorized_tags ORDER BY order_count DESC').fetchall()
for row in result:
    print(f'{row[0]:<45} orders:{row[1]:>3}  {row[3]}')
"

# Tag category summary
docker exec data_platform python -c "
import duckdb
con = duckdb.connect('/app/app_data/data_lake/sapo_warehouse.duckdb', read_only=True)
result = con.execute('''
    SELECT tag_category, COUNT(*) as tags, COUNT(DISTINCT order_id) as orders
    FROM int_order_tags GROUP BY 1 ORDER BY tags DESC
''').fetchall()
for row in result:
    print(f'{row[0]:<25} tags:{row[1]:>5}  orders:{row[2]:>5}')
"

# === LOCAL (Windows - requires Python duckdb) ===

# Same queries but with local path
python -c "
import duckdb
con = duckdb.connect('app_data/data_lake/sapo_warehouse.duckdb', read_only=True)
# ... same queries
"
```

### Adding New Pattern

**Step 1: Identify the tag**
```sql
-- Find sample orders with the tag
SELECT order_id, order_code, tags, created_on
FROM src_sapo_orders
WHERE tags LIKE '%NewTagName%'
LIMIT 5;
```

**Step 2: Choose category**

| If tag is... | Use category |
|--------------|--------------|
| Platform name (Shopee, Lazada) | `channel_platform` |
| Store name with platform prefix | `channel_storefront` |
| Consignment/ký gửi related | `order_type_consignment` |
| Sample/mẫu/sampling | `order_type_sample` |
| Gift/quà tặng | `order_type_gift` |
| Discount code (CK SAU, CHIẾT KHẤU) | `discount_deferred` |
| Facebook Ad/Post/Customer ID | `marketing_ad/post/customer` |
| Payment method | `payment_method` |
| Delivery status | `fulfillment_status` |
| Internal note/name | `order_note` |
| New type needed | Create new category |

**Step 3: Choose match_type**

| Pattern | match_type | Example |
|---------|------------|---------|
| Exact string | `exact` | `Shopee` matches only "Shopee" |
| Starts with | `prefix` | `Shopee_%` matches "Shopee_JPC" |
| Contains anywhere | `contains` | `%ký gửi%` matches "Hàng ký gửi" |

**Step 4: Add to CSV**

```csv
# Edit: transformation/seeds/ref_tag_categories.csv
# Add new row:
NewPattern,category_name,match_type,Human readable description
```

**Step 5: Deploy**

```bash
# Docker
docker exec data_platform bash -c "
  cd /app/transformation && \
  dbt seed --select ref_tag_categories && \
  dbt run --select int_order_tags monitor_uncategorized_tags
"

# Verify
docker exec data_platform python -c "
import duckdb
con = duckdb.connect('/app/app_data/data_lake/sapo_warehouse.duckdb', read_only=True)
result = con.execute(\"\"\"
    SELECT tag_value, tag_category 
    FROM int_order_tags 
    WHERE tag_value LIKE '%NewPattern%'
\"\"\").fetchall()
print(result)
"
```

**Step 6: Commit**

```bash
git add transformation/seeds/ref_tag_categories.csv
git commit -m "feat(tags): add pattern for NewTagName -> category_name"
git push
```

### Adding New Category

When existing categories don't fit:

1. **Name convention:** `{domain}_{type}` (e.g., `order_type_preorder`, `customer_type_agent`)
2. **Add multiple patterns** for case variations (Vietnamese diacritics)
3. **Update this documentation** with new category in the Categories table
4. **Consider impact** on downstream analytics

```csv
# Example: Adding "order_type_preorder" category
Đơn gối đầu,order_type_preorder,exact,Pre-order/deposit orders
%gối đầu%,order_type_preorder,contains,Pre-order variations
```

### Handling Edge Cases

**Case sensitivity (Vietnamese)**
```csv
# Add both cases for Vietnamese text
%ký gửi%,order_type_consignment,contains,lowercase
%Ký gửi%,order_type_consignment,contains,capitalized
%KÝ GỬI%,order_type_consignment,contains,uppercase
```

**Overlapping patterns**
- Longer/more specific pattern wins (by `LENGTH(pattern) DESC`)
- If conflict: make patterns mutually exclusive

**Tags to ignore**
- Personal names, one-time notes → leave as `uncategorized`
- System test tags → `system_test` category
- Don't create patterns for single-use tags

### Cleanup Procedures

**Remove unused patterns:**
```sql
-- Find patterns with no matches
SELECT c.pattern, c.category
FROM ref_tag_categories c
LEFT JOIN int_order_tags t ON t.tag_value LIKE c.pattern
WHERE t.order_id IS NULL;
```

**Merge duplicate patterns:**
```sql
-- Find patterns matching same tags
SELECT t.tag_value, STRING_AGG(DISTINCT c.pattern, ', ') as patterns
FROM int_order_tags t
JOIN ref_tag_categories c 
  ON t.tag_value LIKE c.pattern
GROUP BY 1
HAVING COUNT(DISTINCT c.pattern) > 1;
```

### Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TAG MAINTENANCE FLOW                             │
└─────────────────────────────────────────────────────────────────────────┘

   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
   │ New order    │────►│ Tags in JSON │────►│ int_order_   │
   │ with tags    │     │ array        │     │ tags (VIEW)  │
   └──────────────┘     └──────────────┘     └──────┬───────┘
                                                    │
                        ┌───────────────────────────┴───────────────────┐
                        │                                               │
                        ▼                                               ▼
              ┌─────────────────┐                            ┌─────────────────┐
              │ Pattern matched │                            │ No match found  │
              │ → category set  │                            │ → uncategorized │
              └─────────────────┘                            └────────┬────────┘
                        │                                             │
                        ▼                                             ▼
              ┌─────────────────┐                            ┌─────────────────┐
              │ Analytics ready │                            │ monitor_        │
              │ (fact tables)   │                            │ uncategorized   │
              └─────────────────┘                            └────────┬────────┘
                                                                      │
                                          ┌───────────────────────────┘
                                          ▼
                               ┌─────────────────────┐
                               │ Weekly review       │
                               │ by data team        │
                               └──────────┬──────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼
          ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
          │ Add new pattern │   │ Ignore          │   │ Create new      │
          │ to existing cat │   │ (one-time note) │   │ category        │
          └────────┬────────┘   └─────────────────┘   └────────┬────────┘
                   │                                           │
                   └─────────────────┬─────────────────────────┘
                                     ▼
                          ┌─────────────────────┐
                          │ Edit CSV            │
                          │ ref_tag_categories  │
                          └──────────┬──────────┘
                                     ▼
                          ┌─────────────────────┐
                          │ dbt seed && run     │
                          └──────────┬──────────┘
                                     ▼
                          ┌─────────────────────┐
                          │ Verify & commit     │
                          └──────────┬──────────┘
                                     ▼
                          ┌─────────────────────┐
                          │ Tag now categorized │
                          └─────────────────────┘
```

### Quick Reference Commands

```bash
# === CHECK STATUS ===
# Uncategorized count
docker exec data_platform python -c "
import duckdb
con = duckdb.connect('/app/app_data/data_lake/sapo_warehouse.duckdb', read_only=True)
print(con.execute('SELECT COUNT(*) FROM monitor_uncategorized_tags').fetchone()[0], 'uncategorized tags')
"

# === ADD PATTERN ===
# 1. Edit CSV (use any editor)
nano transformation/seeds/ref_tag_categories.csv

# 2. Deploy
docker exec data_platform bash -c "cd /app/transformation && dbt seed --select ref_tag_categories"

# 3. Verify (views auto-refresh)
docker exec data_platform python -c "
import duckdb
con = duckdb.connect('/app/app_data/data_lake/sapo_warehouse.duckdb', read_only=True)
print(con.execute('SELECT COUNT(*) FROM monitor_uncategorized_tags').fetchone()[0], 'uncategorized tags remaining')
"

# === COMMIT ===
git add transformation/seeds/ref_tag_categories.csv
git commit -m 'feat(tags): add pattern for X'
git push
```

---

## Analytics Use Cases

### Tag Frequency Report

```sql
SELECT 
    tag_category,
    tag_value,
    COUNT(DISTINCT order_id) as order_count
FROM int_order_tags
GROUP BY 1, 2
ORDER BY 1, 3 DESC
```

### Orders by Type

```sql
SELECT 
    order_id,
    BOOL_OR(tag_category = 'order_type_consignment') as is_consignment,
    BOOL_OR(tag_category = 'order_type_sample') as is_sample,
    BOOL_OR(tag_category = 'order_type_gift') as is_gift,
    MAX(CASE WHEN tag_category = 'discount_deferred' THEN tag_value END) as discount_code
FROM int_order_tags
GROUP BY 1
```

### Channel Attribution

```sql
SELECT 
    COALESCE(
        MAX(CASE WHEN tag_category = 'channel_storefront' THEN tag_value END),
        MAX(CASE WHEN tag_category = 'channel_platform' THEN tag_value END)
    ) as channel,
    COUNT(DISTINCT order_id) as orders
FROM int_order_tags
GROUP BY 1
```

### Marketing ROAS (join with spend)

```sql
SELECT 
    t.tag_value as ad_id,
    COUNT(DISTINCT t.order_id) as orders,
    SUM(o.total_amount) as revenue,
    s.spend,
    SUM(o.total_amount) / NULLIF(s.spend, 0) as roas
FROM int_order_tags t
JOIN src_sapo_orders o ON t.order_id = o.order_id
LEFT JOIN marketing_spend s ON t.tag_value = s.ad_id
WHERE t.tag_category = 'marketing_ad'
GROUP BY 1, 4
```

---

## Troubleshooting

### Tag Not Being Categorized

1. **Check pattern exists:** `SELECT * FROM ref_tag_categories WHERE pattern LIKE '%keyword%'`
2. **Check match_type:** `exact` won't match substrings
3. **Check case sensitivity:** DuckDB LIKE is case-sensitive by default
4. **Add ILIKE variant:** For Vietnamese diacritics, add both cases

### Duplicate Categorization

If a tag matches multiple patterns:
- **Most specific wins:** Longer pattern takes priority (`LENGTH(pattern) DESC`)
- **If same length:** First match (non-deterministic)
- **Solution:** Make patterns mutually exclusive or add priority column

### Performance

`int_order_tags` is a VIEW. If slow:
1. Check `src_sapo_orders` row count
2. Consider materializing as TABLE if > 1M orders
3. Add `WHERE created_on >= '2025-01-01'` filter for time-bounded queries

---

## Related Documentation

- [MODELS.md](./MODELS.md) — Full model catalog
- [DEDUPLICATION.md](./DEDUPLICATION.md) — Dedup logic in src_ models
- [config-guide.md](../../docs/config-guide.md) — Environment configuration
