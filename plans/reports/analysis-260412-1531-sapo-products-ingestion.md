# Sapo Products Ingestion - Analysis Report

**Date:** 2026-04-12 | **Total Products:** 558 | **Total Variants:** 682

## Files Created/Modified

| File | Action |
|------|--------|
| `ingestion/src/sapo/products.py` | Created - Products source (envelope schema) |
| `ingestion/run_products_batch.py` | Created - Entry point |
| `orchestration/assets/sapo_assets.py` | Modified - Added `sapo_products_batch_asset` |
| `orchestration/definitions.py` | Modified - Added to `sapo_nightly_reconciliation_job` |

## Ingestion Config

- **API:** `/admin/products.json?sort_by=modified_on&sort_direction=desc`
- **Page size:** 50 (products have large nested payloads)
- **Overlap buffer:** 100 items
- **Schedule:** Daily via `sapo_nightly_reconciliation_job` (04:00 HCM)
- **Pipeline:** `sapo_products_batch` → dataset `sapo_raw` → table `product`

## Data Profile

### Product-Level Columns

| Column | Type | Notes |
|--------|------|-------|
| `id` | bigint | PK |
| `tenant_id` | bigint | Always 445355 |
| `created_on` | timestamp | UTC |
| `modified_on` | timestamp | UTC, used for incremental |
| `status` | text | 100% "active" |
| `brand` / `brand_id` | text/bigint | 87 nulls, top: Fine Japan(81), Jpanwell(44), Orihiro(41) |
| `name` | text | Product display name |
| `description` | text | Often empty |
| `category` / `category_id` / `category_code` | text/bigint/text | 8 categories |
| `product_type` | text | lots_date(450), composite(77), normal(30), serial(1) |
| `opt1` / `opt2` / `opt3` | text | opt1 used (mostly "Kich thuoc"), opt2/opt3 always null |
| `tags` | text | case 1(192), case 3(110), case 2(84), others sparse |
| `medicine` | bool | 100% false |
| `image_path` / `image_name` | text | Product image ref |
| `vat_pit_category_code` | text | Mostly null |
| `variants` | json array | 1-6 per product (avg 1.2) |
| `options` | json array | Product option definitions |
| `images` | json array | Product images |
| `product_medicines` | null | Always null |

### Category Distribution

| Category | Count |
|----------|-------|
| Dietary Supplement | 335 |
| Food (Supplemented) | 94 |
| (uncategorized/null) | 65 |
| Van Hanh | 22 |
| San pham Phu | 22 |
| Cosmetic | 16 |
| Uncategorized | 3 |
| Medicine | 1 |

### Variant-Level Columns

| Column | Type | Notes |
|--------|------|-------|
| `id` | bigint | Variant PK |
| `product_id` | bigint | FK to product |
| `sku` / `barcode` | text | Variant identifiers |
| `name` / `product_name` | text | Variant/product names |
| `status` | text | 100% "active" |
| `sellable` | bool | 664 true, 18 false |
| `composite` | bool | 77 true (maps to product_type=composite) |
| `variant_retail_price` | double | 0 - 44,388,000 VND (avg ~1.5M) |
| `variant_import_price` | double | 0 - 5,472,000 VND (avg ~192K) |
| `variant_whole_price` | double | Wholesale price |
| `init_price` / `init_stock` | double | Initial values |
| `cost_price` | double | Often null |
| `unit` | text | Highly inconsistent (Lo/lo, Hop/hop, etc.) |
| `taxable` | bool | 403 true, 279 false |
| `tax_included` | bool | Tax included in price flag |
| `input_vat_rate` / `output_vat_rate` | double | 8%(414), null(209), 10%(58) |
| `weight_value` / `weight_unit` | double/text | Weight info |
| `opt1` / `opt2` / `opt3` | text | Variant option values |
| `variant_prices` | json array | 16-17 price lists per variant |
| `inventories` | json array | 3 locations per variant |
| `images` | json array | Variant images |
| `composite_items` | json array | For composite products |
| `packsize` | bool | Pack size flag |
| `warranty` | bool | Warranty flag |

### Inventory (3 Locations)

| Location ID | On Hand | Available | Committed |
|-------------|---------|-----------|-----------|
| 452566 | 122,530 | 122,475 | 55 |
| 494912 | 100,843 | 100,843 | 0 |
| 624127 | -18 | -18 | 0 |

### Price Lists (17 distinct)

Gia nhap (GIANHAP), Gia ban le (BANLE), Giam 30% (BANBUON), Giam 35%, Giam 40%, Facebook, WS FJP Gia Ban, WS FJP Niem Yet, WS TheHeathyUs, Gia Nhap A, US, Selly, Thuoc si, Uu dai Nhan Vien, Hang Tang, AEON/JAPANA/PHANO, Hopt 6

## Transformation Recommendations

### Staging Layer (dbt)

1. **`src_sapo_products`** - Raw extraction from envelope (same pattern as `src_sapo_orders`)
   - Extract scalars from payload JSON
   - Tech dedup: ROW_NUMBER by (entity_id, event_timestamp DESC)

2. **`stg_sapo_products`** - Business dedup
   - Dedup by product_id, latest modified_on wins
   - Clean/standardize category, brand, product_type
   - Normalize `unit` inconsistencies (Lo/lo -> Lo, Hop/hop -> Hop)

3. **`stg_sapo_variants`** - Unnest variants array
   - One row per variant
   - Extract SKU, barcode, prices, unit, tax info
   - Join back to product for category/brand context

4. **`stg_sapo_variant_prices`** - Unnest variant_prices array
   - One row per (variant_id, price_list_id)
   - Flatten price_list metadata
   - Key price lists: GIANHAP (cost), BANLE (retail)

5. **`stg_sapo_inventories`** - Unnest inventories array
   - One row per (variant_id, location_id)
   - Track on_hand, available, committed

### Key Observations for Transformation

- **Unit normalization needed**: 60+ distinct unit values, many are case variants (Lo/lo, Hop/hop)
- **Tags are business-meaningful**: "case 1/2/3" likely pricing tiers
- **Price lists**: GIANHAP = cost price, BANLE = retail price are the key ones
- **Composite products** (77): Have `composite_items` for BOM tracking
- **All products active**: No status filtering needed currently
- **3 inventory locations**: Map to physical warehouses

## Unresolved Questions

- What do "case 1/2/3" tags mean? (pricing tier? product grade?)
- Which location_id maps to which warehouse?
- Should composite_items be unnested for BOM analysis?
