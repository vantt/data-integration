# Order & Customer Tags Deep Analysis Report

**Date:** 2026-04-17  
**Purpose:** Analyze tag values from raw parquet to inform dbt transformation design

---

## Executive Summary

| Metric | Orders | Customers |
|--------|--------|-----------|
| Total records | 4,700 | 260 |
| With tags | 2,088 (44%) | 202 (78%) |
| Unique tag combinations | ~130 | 8 |
| Unique individual tags | ~130 | 7 |

**Key Finding:** Tags are semi-structured, multi-value arrays with high analytical value for channel attribution, marketing analysis, and order classification.

---

## 1. Order Tags Analysis

### 1.1 Tag Category Distribution

| Category | Unique Tags | Occurrences | Purpose |
|----------|-------------|-------------|---------|
| CHANNEL_PLATFORM | 6 | 1,838 | Marketplace/social platform (Shopee, Lazada, sapoweb) |
| CHANNEL_STOREFRONT | 6 | 1,757 | Specific store within platform (Shopee_JPC SHOP) |
| PAYMENT_STATUS | 3 | 958 | Payment confirmation status |
| FULFILLMENT_STATUS | 3 | 435 | Delivery status tracking |
| DISCOUNT_DEFERRED | 13 | 80 | Post-sale discount codes (CK SAU BS 30%) |
| SOCIAL_PAGE | 4 | 62 | Facebook page attribution |
| SHIPPING_TYPE | 2 | 49 | Freeship, Ngoai thanh |
| ORDER_TYPE_CONSIGNMENT | 3 | 41 | Ky gui (consignment) orders |
| ORDER_TYPE_SAMPLE | 4 | 33 | Sample/sampling orders |
| MARKETING_POST_ID | 17 | 33 | FB post attribution |
| MARKETING_CUSTOMER_ID | 15 | 31 | FB customer tracking |
| MARKETING_AD_ID | 11 | 31 | FB ad campaign attribution |
| PROMO_GIFT | 4 | 29 | Gift/promotional orders |
| PRODUCT_CATEGORY | 4 | 19 | Product line (Fucoidan, cordyceps) |
| INVOICE_STATUS | 4 | 13 | Invoice issuance tracking |
| MARKETING_AFFILIATE | 3 | 13 | ECOMOBI, KOC affiliate |
| ORDER_TYPE_GIFT | 4 | 11 | Gift orders |
| PROMO_CAMPAIGN | 2 | 11 | Campaign tracking |
| ORDER_TYPE_PREORDER | 1 | 10 | Pre-orders (don goi dau) |
| PARTNER_LOCATION | 5 | 7 | Partner/retail locations |

### 1.2 Tag Count Distribution

| Tags per Order | Orders | % |
|----------------|--------|---|
| 1 tag | 221 | 10.6% |
| 2 tags | 701 | 33.6% |
| 3 tags | 871 | 41.7% |
| 4 tags | 255 | 12.2% |
| 5+ tags | 40 | 1.9% |

**Typical pattern:** Platform + Storefront + Status (3 tags)

### 1.3 Top Tag Pairs (Co-occurrence)

| Tag 1 | Tag 2 | Count |
|-------|-------|-------|
| Shopee | Shopee_Fine Japan Vietnam | 11,640 |
| Shopee | Don hang da thanh toan | 8,296 |
| Shopee_Fine Japan Vietnam | Don hang da thanh toan | 7,635 |
| Giao hang thanh cong | Shopee | 3,416 |
| Shopee | Shopee_JPC SHOP | 1,258 |
| Lazada | Lazada_Fine Japan Vietnam | 371 |

### 1.4 Data Quality Issues

**Format variations (same meaning):**
- `Xuat hoa don` / `DA XUAT HOA DON` / `Da xuat hoa don` (3 variants)
- `HANG MAU` / `Hang mau` (2 variants)

---

## 2. Customer Tags Analysis

### 2.1 Individual Tag Values

| Tag | Count | Unique Customers |
|-----|-------|------------------|
| Shopee | 179 | 151 |
| Fine Japan Vietnam | 100 | 84 |
| JPC SHOP | 71 | 58 |
| thehealthyus | 13 | 13 |
| Web | 13 | 8 |
| sapo_social | 6 | 5 |
| Lazada | 6 | 5 |

### 2.2 Customer Tag Categories

| Category | Tags | Total | Examples |
|----------|------|-------|----------|
| ACQUISITION_CHANNEL | 4 | 204 | Shopee, Web, Lazada, sapo_social |
| STOREFRONT_NAME | 3 | 184 | Fine Japan Vietnam, JPC SHOP, thehealthyus |

**Observation:** Customer tags track acquisition source + storefront, simpler than order tags.

---

## 3. Mapping Coverage (ref_order_sources)

### 3.1 Covered Storefront Tags

| Tag in Data | Mapped |
|-------------|--------|
| Shopee_Fine Japan Vietnam | YES |
| Shopee_JPC SHOP | YES |
| Shopee_thehealthyus | YES |
| Lazada_Fine Japan Vietnam | YES |
| Lazada_Fine Care | YES |
| Tiki_FINE WORLD GROUP | YES |

### 3.2 Mapping Tags NOT in Data (possibly deprecated)

- Shopee_JPC OFFICIAL, Shopee_FG CARE, Shopee_FWG Vietnam
- Shopee_Fine Care, Shopee_FINE WORLD GROUP
- Lazada_JPC SHOP, Lazada_The Healthy Us, Lazada_Fine Japan store
- Lazada_FINE WORLD GROUP, Lazada_FG CARE, Tiki_FG GLOBAL

---

## 4. Transformation Design Recommendations

### 4.1 Proposed New Models

#### A. `int_order_tags_unnested` (Intermediate)
Unnest order tags array for flexible analysis.

```sql
-- Intermediate model: one row per order-tag pair
SELECT
    order_id,
    TRIM(REPLACE(unnest(json_extract(tags, '$[*]'))::VARCHAR, '"', '')) as tag_value
FROM {{ ref('src_sapo_orders') }}
WHERE tags IS NOT NULL AND tags NOT IN ('', '[]')
```

**Use cases:**
- Tag frequency analysis
- Marketing attribution reporting
- Order classification

#### B. `int_order_tags_classified` (Intermediate)
Classify tags into semantic categories.

```sql
SELECT
    order_id,
    tag_value,
    CASE
        WHEN tag_value IN ('Shopee','Lazada','Tiki','sapoweb','sapo_social','bizweb') THEN 'channel_platform'
        WHEN tag_value LIKE 'Shopee_%' OR tag_value LIKE 'Lazada_%' OR tag_value LIKE 'Tiki_%' THEN 'channel_storefront'
        WHEN tag_value LIKE '%thanh toan%' THEN 'payment_status'
        WHEN tag_value LIKE '%giao hang%' THEN 'fulfillment_status'
        WHEN tag_value LIKE 'CK SAU%' OR tag_value LIKE 'CHIET KHAU%' THEN 'discount_deferred'
        WHEN tag_value LIKE 'Ad_id_%' THEN 'marketing_ad'
        WHEN tag_value LIKE 'Post_ID%' THEN 'marketing_post'
        WHEN tag_value LIKE 'ID Khach hang%' THEN 'marketing_customer'
        WHEN tag_value LIKE '%ky gui%' THEN 'order_type_consignment'
        WHEN tag_value LIKE '%MAU%' OR tag_value LIKE '%sampling%' THEN 'order_type_sample'
        WHEN tag_value LIKE '%tang%' OR tag_value LIKE '%Qua%' THEN 'order_type_gift'
        ELSE 'other'
    END as tag_category
FROM {{ ref('int_order_tags_unnested') }}
```

#### C. `dim_order_tags_pivot` (Dimension)
Pivot key tag categories back to order level for easy filtering.

```sql
SELECT
    order_id,
    MAX(CASE WHEN tag_category = 'channel_platform' THEN tag_value END) as channel_platform,
    MAX(CASE WHEN tag_category = 'channel_storefront' THEN tag_value END) as channel_storefront,
    MAX(CASE WHEN tag_category = 'discount_deferred' THEN tag_value END) as discount_code,
    BOOL_OR(tag_category = 'order_type_consignment') as is_consignment,
    BOOL_OR(tag_category = 'order_type_sample') as is_sample,
    BOOL_OR(tag_category = 'order_type_gift') as is_gift,
    BOOL_OR(tag_value LIKE '%hoa don%') as needs_invoice,
    STRING_AGG(CASE WHEN tag_category = 'marketing_ad' THEN tag_value END, ',') as marketing_ad_ids
FROM {{ ref('int_order_tags_classified') }}
GROUP BY order_id
```

### 4.2 Seed Data Updates

#### Add missing tag variations to normalization:
```csv
# ref_tag_normalization.csv (NEW)
raw_tag,normalized_tag,category
"HANG MAU","Hang mau",order_type_sample
"DA XUAT HOA DON","Xuat hoa don",invoice_status
"Da xuat hoa don","Xuat hoa don",invoice_status
"Qua tang","Qua tang",promo_gift
```

### 4.3 Fact Table Enhancements

Add to `fact_orders`:
```sql
-- Join with dim_order_tags_pivot for filtering
LEFT JOIN {{ ref('dim_order_tags_pivot') }} otp ON o.order_id = otp.order_id

-- Add columns
otp.is_consignment,
otp.is_sample,
otp.is_gift,
otp.needs_invoice,
otp.discount_code
```

### 4.4 Customer Tags (Lower Priority)

Customer tags are simple (acquisition channel + storefront). Current extraction in `src_sapo_customers` does NOT include tags field.

**Recommendation:** Add tags extraction to `src_sapo_customers.sql`:
```sql
json_extract_string(payload, '$.tags') as tags
```

Then create `int_customer_acquisition_channel`:
```sql
SELECT
    sapo_customer_id,
    MAX(CASE WHEN tag IN ('Shopee','Lazada','Web','sapo_social') THEN tag END) as acquisition_channel,
    MAX(CASE WHEN tag NOT IN ('Shopee','Lazada','Web','sapo_social') THEN tag END) as acquisition_storefront
FROM unnested_customer_tags
GROUP BY sapo_customer_id
```

---

## 5. Analytics Value Assessment

### High Value (Implement First)
1. **Channel/Storefront Attribution** - Already partially implemented via `mapping_tag`, but direct tag parsing enables richer analysis
2. **Order Type Classification** - Consignment, sample, gift orders need different treatment in revenue reporting
3. **Deferred Discount Tracking** - "CK SAU BS 30%" tags indicate post-sale discounts affecting true margin

### Medium Value
4. **Marketing Attribution** - Ad/Post/Customer IDs enable ROAS calculation when joined with marketing spend
5. **Invoice Requirements** - Helps operations identify B2B orders needing VAT invoices

### Lower Value (Nice-to-have)
6. **Product Category Tags** - Only 19 occurrences, better derived from product master
7. **Partner Location Tags** - Sparse data, limited analytical use

---

## 6. Implementation Priority

| Phase | Model | Effort | Impact |
|-------|-------|--------|--------|
| 1 | `int_order_tags_unnested` | Low | Foundation for all tag analysis |
| 1 | `int_order_tags_classified` | Medium | Semantic categorization |
| 2 | `dim_order_tags_pivot` | Medium | Easy filtering in fact tables |
| 2 | Update `fact_orders` with tag flags | Low | Direct business value |
| 3 | Customer tags extraction | Low | Acquisition analysis |
| 3 | Marketing attribution join | High | ROAS calculation |

---

## Unresolved Questions

1. **Deferred discount tags ("CK SAU BS 30%")** - How are these reconciled? Is there a separate discount adjustment transaction?
2. **Consignment orders** - Should these be excluded from standard revenue reporting?
3. **Sample/gift orders** - What's the accounting treatment? Zero revenue or cost-only?
4. **Marketing spend data** - Is `marketing_spend_raw` table joinable with Ad_id tags?
