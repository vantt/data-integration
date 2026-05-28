# Sapo Product Schema Discovery + Analytics Opportunities

> **Created:** 2026-05-28 16:54 ICT
> **Source:** `sapo_raw/product/ingest_method=batch_sync/…/0de4606485.parquet` — 558 products, 682 variants

---

## TL;DR

- **558 products, 682 variants, 679 unique SKUs** confirmed in the batch-sync parquet.
- **MISA coverage jumps from 11.4% → 90.0%** after this sync (23 → 181 of 201 MISA codes matched by direct SKU key). The remaining 20 MISA codes are 13 services/costs (`DV*`, `CPBH`) + 5 discontinued food products + 2 old catalog items — none are sellable product, so the practical ceiling is ~95%.
- **77 composite (bundle) variants** with full `composite_items` data: component SKU + quantity + price — ready to build `dim_bundle_components`.
- **3-location inventory snapshot** (VVT / Hậu Giang / MM An Phú) per variant with on_hand, available, committed, incoming, onway, MAC, bin_location — unblocks `product_inventory` dashboard.
- **17 price lists** across channels (BANLE, GIANHAP, FB, US, WS_FJP, Bansi_Selly, DAILY, etc.) — rich pricing intelligence opportunity.

---

## Schema Discovered

### Top-level product fields

| Column | Type | Sample | Usable |
|--------|------|--------|--------|
| `id` | int | 49514998 | YES — product_id |
| `tenant_id` | int | 445355 | NO — constant |
| `created_on` | str (UTC ISO) | 2022-11-29T04:45:13Z | YES |
| `modified_on` | str (UTC ISO) | 2026-03-18T07:50:48Z | YES |
| `status` | str | active | YES — all 558 are active |
| `brand_id` | int | 1193963 | YES |
| `brand` | str | "Fine Japan" | YES — 81 FJ, 44 Jpanwell, 41 Orihiro, 32 Kirkland… |
| `name` | str | "(*) Royal Reishi" | YES — contains TPBVSK prefix variants |
| `category_id` | int | 2028224 | YES |
| `category` | str | "Dietary Supplement" | YES — 334 DS, 95 Food, 65 null, 22 Vận Hành, 22 Sản phẩm Phụ |
| `category_code` | str | "PGN00007" | YES — standardized |
| `opt1/opt2/opt3` | str | "Kích thước" / null / null | YES — 100% single-option products (no opt2 in catalog) |
| `medicine` | bool | False | YES — 0 products flagged (data may be unreliable) |
| `tags` | str | "woocommerce,độc quyền" | YES — 426/558 have tags; values: woocommerce, độc quyền, Anphabe, Quà tặng, case 1/2/3 |
| `product_type` | str | lots_date | YES — 450 lots_date, 77 composite, 30 normal, 1 serial |
| `vat_pit_category_code` | null | null | NO — all null in batch |
| `image_path/image_name` | str/null | — | LOW — CDN path only |
| `product_medicines` | null | null | NO — all null |

### Variant nesting

Each product has `variants: []` array. Key fields per variant:

| Field | Type | Notes |
|-------|------|-------|
| `id` | int | variant_id — PK for variants |
| `product_id` | int | FK to product |
| `sku` | str | **Primary join key to MISA** |
| `barcode` | str | EAN/custom barcode; some use barcode as alternate SKU (e.g., PVN156 = barcode for VSL19001C004) |
| `status` | str | All 682 active |
| `name` / `product_name` | str | Variant name ≠ product name when multi-variant |
| `unit` | str | "Chai", "Hộp", "Thùng", "lọ" — unit economics basis |
| `packsize` | bool | True = this is a multi-unit pack of another variant |
| `packsize_quantity` | float | Number of base units in pack |
| `packsize_root_id` | int | FK to base variant's variant_id (root_sku/root_name NULL — need join) |
| `weight_value` / `weight_unit` | float/str | Shipping weight |
| `sellable` | bool | All true |
| `composite` | bool | True if bundle component logic applies |
| `input_vat_rate` / `output_vat_rate` | float | 8.0 (standard), null |
| `cost_price` | float | All NULL in current data — MAC in inventories is better |
| `variant_retail_price` | float | Shortcut retail price |
| `variant_import_price` | float | Shortcut import price |
| `expiration_alert_time` | int | Days before expiry to alert (180 common) |
| `product_type` | str | Inherits from product |

**Single-option pattern:** All 558 products have only `opt1` set (size/unit), opt2/opt3 null — no color/flavor variants.

### Variant prices nesting

Each variant has `variant_prices: []` array. Structure per entry:

```
{
  "id": 216239194,
  "value": 2425000.0,           -- price in VND (0 = not configured for this channel)
  "included_tax_price": 2425000.0,  -- tax-inclusive price
  "price_list_id": 1359100,
  "price_list": {
    "code": "BANLE",            -- code used for joins
    "name": "Giá bán lẻ",
    "is_cost": false,           -- GIANHAP is the only is_cost=true list
    "status": "default"         -- BANLE is the default/retail list
  }
}
```

**17 distinct price lists:**

| Code | Name | is_cost | Purpose |
|------|------|---------|---------|
| BANLE | Giá bán lẻ | false | Retail (default) |
| GIANHAP | Giá nhập | **true** | Import/cost price — most reliable COGS proxy in Sapo |
| FB | Facebook | false | Facebook channel pricing |
| US | US | false | US export channel |
| US01 | US | false | US (alternate) |
| DAILY | AEON/JAPANA/PHANO | false | FMCG distributor price |
| Bansi_Selly | Selly | false | Selly distributor |
| WS_FJP | WS FJP Giá Bán | false | Fine Japan wholesale sell |
| WS_FJP_LISTING | WS FJP Niêm Yết | false | Fine Japan wholesale list |
| WS_THU | WS TheHealthyUs | false | TheHealthyUs wholesale |
| Thuocsi_1 | Thuốc sỉ | false | Pharmacy wholesale |
| BANBUON | Giảm 30% | false | Bulk discount |
| NHANVIEN | Ưu đãi Nhân VIên | false | Staff discount |
| 35 / 40 | Giảm 35%/40% | false | Promo price list |
| GIFT | Hàng Tặng | false | Gift/promo items |
| GN002 | Giá Nhập A | false | Secondary import price |

**Key insight:** Many `value=0.0` entries mean "not set for this channel." GIANHAP (`is_cost=true`) is the Sapo-side COGS source — currently not used in dbt, but could supplement MISA COGS for non-matched SKUs.

### Inventories nesting

Each variant has `inventories: []` — one entry per warehouse location:

| Field | Type | Notes |
|-------|------|-------|
| `location_id` | int | Maps to ref_branch_locations: 452566=VVT, 494912=Hậu Giang, 624127=MM An Phú |
| `variant_id` | int | Same as parent variant |
| `on_hand` | float | Total physical stock |
| `available` | float | on_hand - committed |
| `committed` | float | Reserved (pending orders) |
| `incoming` | float | Incoming PO quantity |
| `onway` | float | In transit |
| `mac` | float | Moving Average Cost — **only 2.6% non-zero** (54 records); cost data sparse |
| `bin_location` | str | e.g. "B3-A11-A1" — 1.2% non-null, VVT only |
| `min_value` / `max_value` | float | Reorder min/max |
| `wait_to_pack` | float | Allocated to pending packs |
| `modified_on` | null | Always null in current data |
| `amount` | int | Always 0 |

**682 variants × 3 locations = 2,046 inventory records.** 125 (6.1%) have on_hand > 0.

### Composite items (bundles)

`composite_items: []` present on 77 variants (product_type = 'composite'). Structure:

```json
{
  "sub_product_id": 49776380,
  "sub_variant_id": 72561096,
  "price": 2168000.0,       -- component unit price at time of bundle creation
  "quantity": 2.0,           -- units of component in bundle
  "sub_product_type": "lots_date",
  "sub_sku": "VCST21004L001",
  "sub_name": "Thực phẩm bảo vệ sức khỏe Shark Cartilage Extract - Lọ",
  "medicine": false
}
```

**Key insight:** Multi-component bundles are rare — most bundles are 1 component × N quantity (e.g., "3x Shark Cartilage"). 14 unique component SKUs appear across all 77 bundle variants.

---

## MISA Join Hit Rate (Critical Fix)

### Before sync (current `dim_products` — 105 SKUs from order_items only)

| Metric | Value |
|--------|-------|
| dim_products distinct SKUs | 105 (104 real + Unknown) |
| MISA distinct product_codes | 201 |
| Direct SKU match | **23 = 11.4% of MISA** |
| mart_sku_economics_monthly rows with COGS | 87/271 = **32.1%** |
| Revenue-weighted COGS coverage | **18.7%** (~1.0B / 5.5B VND) |

### After sync (558 products → 679 unique Sapo SKUs)

| Metric | Value |
|--------|-------|
| Sapo unique SKUs | 679 |
| MISA direct match | **181 = 90.0% of MISA** |
| New matches gained | **+158 SKUs** |
| Remaining unmatched (20) | 13 DV*/CPBH services + 5 food SKUs + 2 discontinued |
| Practical ceiling | ~95% (services will never be in Sapo) |

**Unmatched 20 breakdown:**
- `DV*` (DVCCNS, DVVC, DVNUOC, DVQL, DVRENTAL, DVVS, DVDIEN, DVGX) = utility/staffing services — total COGS 0, revenue ~1.6B VND (B2B/service revenue, NOT product sales)
- `CPBH` = selling expense account, not a product
- `SCLH`, `SNK20`, `TO200`, `DAHC`, `SCLH1`, `NHS225`, `DAOC` = 7 food/snack products sold in small quantities (~7.5M VND COGS combined) — likely discontinued/sampled
- `VCFB22108G001` = Calbee chocolate (COGS: 2.9M) — discontinued
- `VCSP20002G001` = Metabo Green Tea (COGS: 352M) — **largest unmatched product** — check if sold under different SKU in Sapo

**Verified match:** variant_id=72204389 of product 49514998 "Hyaluron & Collagen Plus" has `sku: "VCSL19001C001"` = confirmed MISA code. Structure validated.

**Expected mart COGS coverage after rebuild:** ~80-85% revenue-weighted (from 18.7%).

---

## Analytics Opportunities (Ranked)

| Priority | Opportunity | Data Available | Dashboards That Benefit | Effort | Blocker |
|----------|-------------|---------------|------------------------|--------|---------|
| **P0** | MISA join fix (90% coverage) | YES — 679 SKUs with MISA codes | mart_sku_economics, product_performance, shopee_channel_economics, finance_pl | Low | Parquet ingestion fix (agent af4df…) |
| **P1** | dim_products full rebuild | YES — 558 products with brand/category/type | product_performance, channel_pl, CEO scorecard | Low | Same |
| **P2** | dim_product_variants (1-row per variant) | YES — 682 variants with unit/packsize/weight | product_profitability, SKU drill | Medium | Same |
| **P3** | fact_inventory_snapshot (per location) | YES — 3 locations, 682 variants | product_inventory blueprint (DEFERRED → unblocked) | Medium | Needs daily snapshot mechanism |
| **P4** | dim_bundle_components | YES — 77 bundles, 14 component SKUs | promotion analysis, COGS rollup for bundles | Low-Medium | Same |
| **P5** | dim_price_lists / pricing analysis | YES — 17 price lists, full price matrix | channel economics, margin analysis | Medium | — |
| **P6** | SKU alias seed for legacy codes | Partial — needs business validation | MISA join for SHA1/CORP.H/COR1 (remaining ~10%) | Low | Business input |
| **P7** | Brand-level performance | YES — brand in payload | brand analytics (currently ref_brands only) | Low | — |
| **P8** | Category hierarchy analysis | YES — category_code (PGN00007 etc.) | product categorization | Low | — |
| **P9** | Channel pricing intelligence | YES — price per channel from variant_prices | channel profitability, pricing strategy | High | Multi-day snapshot |
| **P10** | Tag-based subsetting | YES — woocommerce, độc quyền, Anphabe | channel-specific analysis | Low | — |

---

## Data Quality Risks

| Risk | Description | Mitigation |
|------|-------------|------------|
| Variant duplication | 682 variants for 558 products — packsize variants (e.g., VCSL19001H010 = 10×VCSL19001C001) inflate SKU count | Filter `packsize=false` for base-SKU only analysis |
| SKU naming inconsistency | Legacy short codes (SHA1, COR1) coexist with MISA-style codes — 178 Sapo SKUs don't match MISA | Seed alias table (Phase 1 dim_sku_alias) |
| Composite items edge cases | 77 bundles — some have multiple distinct components; quantity can be fractional (1766.6667 on_hand for pack-of-3) | Normalize quantity at component level in dim_bundle_components |
| MAC sparsity | Moving Average Cost only 2.6% non-null — can't substitute for MISA COGS | Use GIANHAP price list as secondary COGS proxy (~510K for Shark Cartilage matches MISA COGS) |
| Inventory data is point-in-time | No `modified_on` on inventory records — parquet is a snapshot, not event log | Snapshot daily via separate Dagster asset to build time-series |
| packsize_root_sku NULL | packsize_root_id is populated but root_sku/root_name are NULL — need join to find base unit | Join on variant_id = packsize_root_id within the same product |
| VCSP20002G001 Metabo Green Tea | 352M VND COGS in MISA, not in Sapo catalog — likely sold historically, now discontinued | Add to seed_sku_alias if historical COGS reconciliation needed |
| Services in MISA (DV*) | 1.6B VND revenue from staffing/utilities coded as "product sales" in MISA — inflates revenue_gross | Filter DV*/CPBH codes in int_misa_sales_lines or mart |

---

## Unresolved Questions

1. **VCSP20002G001 Metabo Green Tea (352M COGS)** — was it sold on Sapo under a different SKU? If so, which? Need business owner input.
2. **packsize_root_sku = NULL** — is this a Sapo API bug or intentional? Need to confirm that `packsize_root_id` is reliable for join.
3. **MAC sparsity (2.6%)** — why is MAC only non-zero for 54 records? Is it set after first purchase order or stock receive event? Does it update from MISA purchases?
4. **GIANHAP price as COGS proxy** — for the 10% of MISA codes that Sapo has in a different price (services excluded), can GIANHAP price be used as COGS? Needs finance sign-off.
5. **Daily inventory snapshot mechanism** — should this be a new Dagster asset that re-ingests product payload daily? Or is there a separate `/inventory` API endpoint?
6. **vat_pit_category_code all null** — is this intentional (not configured in Sapo), or a mapping issue with the batch_sync endpoint?
7. **DV*/CPBH MISA codes** — should these be filtered from int_misa_sales_lines entirely, or kept with a flag (is_service_line) so they appear in finance P&L but not SKU economics?
