# Product Inventory & Stock Health — Build Report

**Date:** 2026-06-12

## Blueprint

`docs/analytics-handbook/blueprints/product_inventory_stock_health.md`

## Dashboard

| Field | Value |
|---|---|
| **ID** | 110 |
| **Name** | Product Inventory & Stock Health [All] |
| **URL** | https://bi.lan.fwg.vn/dashboard/110 |
| **Collection ID** | 100 (Merchandising & Product — root level ✅) |
| **Archived** | false |

## Tabs & Cards (29 total)

### Tab: Current Stock (10 cards)
- Chu kỳ báo cáo (scalar, hardcoded date)
- Text: section heading
- OOS SKUs (scalar, id=2363) ✅
- Low Stock SKUs (scalar, id=2364)
- Tổng Giá Trị Tồn Kho (scalar, id=2365)
- Tổng SKU Có Hàng (scalar, id=2366)
- OOS Risk SKUs — mart_product_health.oos_risk (scalar, id=2367)
- Giá Trị Tồn Kho Theo Location (table, id=2368)
- Top 20 SKU Theo Giá Trị Tồn Kho — enriched w/ health_class+abc (table, id=2369)
- Danh Sách SKU OOS — enriched w/ health_class+abc+oos_risk flag (table, id=2370)
- Text: Source & Freshness

### Tab: Slow-Mover & Dead Stock (10 cards)
- Chu kỳ báo cáo
- Text: section heading
- Slow-Mover Value At Risk (scalar, id=2371)
- Dead Stock Value At Risk (scalar, id=2372) ✅
- Slow-Mover SKU Count (scalar, id=2373)
- Dead Stock SKU Count (scalar, id=2374)
- Danh Sách Slow-Mover Chi Tiết — enriched w/ health_class+abc+momentum (table, id=2375)
- Dead Stock Theo Health Class — DOG+DEAD delist signal (table, id=2376) ← NEW
- Slow-Mover Value Theo Category (table, id=2377)
- Text: Source & Freshness

### Tab: Inventory Trend (9 cards)
- Chu kỳ báo cáo
- Text: section heading
- Stock Value Trend 90 Ngày (line, id=2378)
- OOS Rate Trend 90 Ngày (line, id=2379) ✅
- Stock Value Trend Theo Location 30 Ngày (line, id=2380)
- Slow-Mover Value Trend 90 Ngày (line, id=2381)
- Monthly Stock Value Summary (table, id=2382)
- Text: Source & Freshness

## Deploy Tail

```
✅ Connected to Metabase v0.60.2
✅ Collection 'Merchandising & Product' exists (ID: 100)
✅ Created Dashboard 'Product Inventory & Stock Health [All]' (ID: 110)
✅ Synced cards. Dashboard now has 29 cards.
🚀 Deployment Complete.
```

## Verification (3 queries post-deploy)

| Card | Status | Rows |
|---|---|---|
| OOS SKUs (2363) | completed | 1 |
| Dead Stock Value At Risk (2372) | completed | 1 |
| OOS Rate Trend 90 Ngày (2379) | completed | 2 |

## Enrichment Added vs #94

| Card | Enrichment |
|---|---|
| Top 20 SKU Theo Giá Trị Tồn | LEFT JOIN mart_product_health → health_class, abc_class |
| Danh Sách SKU OOS | health_class, abc_class, oos_risk flag |
| Danh Sách Slow-Mover Chi Tiết | health_class, abc_class, velocity_momentum |
| Dead Stock Theo Health Class | NEW — breaks dead stock by BCG class (DOG = delist priority) |
| OOS Risk SKUs scalar | NEW — high-velocity + low-stock count from mart_product_health |

---

**Status:** DONE

**Summary:** Blueprint created and deployed to new dashboard #110 in collection 100 (Merchandising & Product). All 29 cards synced across 3 tabs. 3 post-deploy queries confirmed `completed`. Old dashboard #94 untouched.

**Concerns:**
- Two cards (OOS Risk SKUs, Stock Value Trend Theo Location) emitted a deploy warning: `location_name filter not matched to SQL`. OOS Risk queries mart_product_health which has no location column (product-level, not location-level — by design). Stock Value Trend Theo Location intentionally omits the location filter so the line chart shows all locations as series (filtering by location collapses to one line, making the chart useless). Both warnings are benign.
- mart_product_health has no `snapshot_date` column — it's a current-snapshot mart (1 row/product). The 3 tab "Chu kỳ báo cáo" headers are hardcoded (not filter-driven) since inventory uses latest-snapshot logic, not a date range filter.
