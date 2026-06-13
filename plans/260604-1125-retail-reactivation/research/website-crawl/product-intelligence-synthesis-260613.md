# Product Intelligence Synthesis — 2026-06-13

**Sources:** finejapanvietnam (15 SKU) + jpcshop (8 SKU) web caches | DuckDB `sapo_export_latest` (economics up to 2026-05)
**Web SKUs:** 18 total (5 on both sites, 2 unavailable/price=0 on fjvn)
**DB economics:** 107 SKUs | **Total retail net revenue:** 12833.4M

## Cross-site SKUs & Price Comparison

| SKU | fjvn price | jpcs price | fjvn disc% | jpcs disc% | fjvn avail |
|-----|-----------|-----------|-----------|-----------|-----------|
| VCSC20001L001 | 1,619,100 | 1,710,000 | 10% | 10% | Y |
| VCSC23054B001 | 99,000 | 136,500 | 75% | 65% | Y |
| VCSL19001H010 | 112,500 | 1,125,000 | anomaly | 50% | Y |
| VCST21003L001 | 0/unavail | 901,600 | 0% | 50% | NO |
| VCST21004L001 | 2,182,500 | 1,952,125 | anomaly | 30% | Y |

> Note: fjvn VCSL19001H010 compare_at=11.25M (10x of actual price) — data entry error; disc% shown from jpcs.
> Note: VCSL21002H010 and VCST21003L001 have price=0 on fjvn (unavailable/sold-out).

## Product Intelligence Table

Columns: `fjvn`/`jpcs` = listed (Y) or not (-); `avail` = purchasable on fjvn; `disc%` = cleaned web discount; `margin%` = avg realized_margin_pct; `rr%` = entry-repeat rate; `EC` = entry customer count

| # | SKU | Name (short) | Cat | fjvn | jpcs | avail | disc% | Rev (M VND) | margin% | EC | rr% |
|---|-----|-------------|-----|------|------|-------|-------|------------|---------|-----|-----|
| 1 | VCSC20001L001 | Thực phẩm bảo vệ sức khỏe Cordyceps | Dietary Suppleme | Y | Y | Y | 10% | 1831.2M | 69.2% | 196 | 31.1% |
| 2 | VCST21004L001 | Thực phẩm bảo vệ sức khỏe Shark Cartilage … | Dietary Suppleme | Y | Y | Y | 30% | 1604.2M | 64.6% | 376 | 22.3% |
| 3 | VTSC19002L001 | (*) Thực phẩm bảo vệ sức khỏe Fucoidan | Dietary Suppleme | - | Y | - | 19% | 1443.9M | 54.1% | 42 | 31.0% |
| 4 | VCSL21002H010 | Thực phẩm bảo vệ sức khỏe Cordyceps Plus | Dietary Suppleme | Y | - | NO | - | 1205.1M | 80.7% | 67 | 34.3% |
| 5 | VTST23023L001 | (*) Thực phẩm bảo vệ sức khỏe Fine Japan S… | Dietary Suppleme | - | - | - | - | 941.1M | 68.6% | 76 | 10.5% |
| 6 | VTSC20001L001 | (*) Thực phẩm bảo vệ sức khỏe Cordyceps | Dietary Suppleme | - | - | - | - | 816.9M | 69.0% | 120 | 28.3% |
| 7 | VCST21003L001 | Thực phẩm bảo vệ sức khỏe Natto Kinase | Dietary Suppleme | Y | Y | NO | 50% | 765.3M | 73.0% | 257 | 26.1% |
| 8 | VTSL24009H010 | (*) TPBVSK Fine Japan Cordyceps Plus | Dietary Suppleme | - | Y | - | 23% | 677.0M | 76.9% | 4 | 50.0% |
| 9 | VCSL19001H010 | Thực phẩm bảo vệ sức khỏe Hyaluron & Colla… | Dietary Suppleme | Y | Y | Y | 50% | 556.4M | 51.6% | 109 | 30.3% |
| 10 | VTSL21001H010 | (*) TPBVSK Hyaluron & Collagen with Swallo… | Dietary Suppleme | - | Y | - | 22% | 536.3M | 78.0% | 9 | 55.6% |
| 11 | VCSC22006L001 | Thực phẩm bảo vệ sức khỏe Fine Japan Chond… | Dietary Suppleme | - | - | - | - | 249.5M | 58.2% | 22 | 22.7% |
| 12 | VCSC23166L001 | Thực phẩm bảo vệ sức khỏe Cordyceps | Dietary Suppleme | - | - | - | - | 199.2M | 23.0% | 87 | 17.2% |
| 13 | VCST22014G001 | Viên uống giảm cân cao cấp Calorie Burn - … | Dietary Suppleme | - | - | - | - | 196.6M | 34.9% | 48 | 25.0% |
| 14 | VCSC22003G001 | Viên uống chống nắng UV Care Plus | Dietary Suppleme | - | - | - | - | 157.0M | 22.7% | 401 | 10.5% |
| 15 | VTSL24010H010 | (*) Thực phẩm bảo vệ sức khỏe Hyaluron & C… | Dietary Suppleme | - | - | - | - | 155.8M | 51.5% | 5 | 20.0% |
| 16 | VCSC23052H001 | Viên uống cải thiện huyết áp cao Gaba bloo… | Dietary Suppleme | - | - | - | - | 124.3M | 61.2% | 87 | 23.0% |
| 17 | VTSC21006L001 | (*) Royal Reishi | Dietary Suppleme | - | - | - | - | 93.3M | -35.9% | 52 | 30.8% |
| 18 | VCSP22001B001 | Bột uống Bone's Calcium for Kids | Dietary Suppleme | - | - | - | - | 84.1M | 38.1% | 262 | 14.1% |
| 19 | VB24010 | Combo 2 lọ Cordyceps | Dietary Suppleme | Y | - | Y | 15% | 77.7M | N/A | 11 | 36.4% |
| 20 | VCSC23054B001 | Viên uống trắng da Coix Beauty tablets Wit… | Dietary Suppleme | Y | Y | Y | 75% | 70.1M | 52.7% | 117 | 16.2% |
| 21 | PVN147 | Combo 2 Hộp Collagen Plus | Dietary Suppleme | Y | - | Y | 50% | 62.9M | N/A | 12 | 50.0% |
| 22 | VCST21003L002 | Thực phẩm bảo vệ sức khỏe Natto Kinase | Dietary Suppleme | - | - | - | - | 62.3M | 77.4% | 12 | 8.3% |
| 23 | VTSP20002H030 | (*) TPBVSK Fine Japan Metabo Green Tea | Dietary Suppleme | - | - | - | - | 59.2M | -1347.0% | 40 | 12.5% |
| 24 | VCSC23030L001 | TPBVSK Genki Fami Kanzo Ukon 90 viên | Dietary Suppleme | - | - | - | - | 54.3M | 43.4% | 43 | 20.9% |
| 25 | VTST23042L001 | (*) TPBVSK Fine Japan Natto Kinase | Dietary Suppleme | - | - | - | - | 53.5M | 22.8% | 28 | 21.4% |
| 26 | PVN150 | Combo 2 hộp Shark Cartilage | Dietary Suppleme | Y | - | Y | 20% | 51.7M | N/A | 6 | 33.3% |
| 27 | VCST23024L001 | TPBVSK hỗ trợ điều trị tiểu đường Insuna F… | Dietary Suppleme | - | - | - | - | 47.1M | 37.7% | 48 | 27.1% |
| 28 | PVN146 | Combo 2 hộp Cordyceps Plus |  | Y | - | Y | 25% | 43.8M | N/A | 4 | 25.0% |
| 29 | VCSC23166L002 | Thực phẩm bảo vệ sức khỏe Cordyceps | Dietary Suppleme | - | - | - | - | 39.3M | 53.3% | 19 | 21.1% |
| 30 | VCST23026L001 | TPBVSK hạ huyết áp Fujina Cardio Nhật Bản … | Dietary Suppleme | - | - | - | - | 36.8M | 34.7% | 75 | 10.7% |
| 46 | VCSC19002L001 | Thực phẩm bảo vệ sức khỏe Fucoidan | Dietary Suppleme | Y | - | Y | 15% | 11.9M | 40.2% | 255 | 28.6% |
| 52 | PVN151 | Combo 2 hộp Natto Kinase | Dietary Suppleme | Y | - | Y | 50% | 8.4M | N/A | 6 | 16.7% |
| 54 | VCSL21001H010 | Thực phẩm bảo vệ sức khỏe Hyaluron & Colla… | Dietary Suppleme | Y | - | Y | 20% | 8.1M | -329.5% | 55 | 36.4% |
| 108 | PVN149 | Fine Japan Vietnam | Dietary Suppleme | Y | - | Y | 20% | — | N/A | 9 | 22.2% |
| 109 | PVN148 | (Combo 2) Nước Uống Collagen Yến Fine Japa… |  | Y | - | Y | 25% | — | N/A | - | N/A |

## Finding a — Gateway SKUs absent from both D2C sites

**21 SKUs** with ≥5 entry customers and repeat rate ≥20% are listed on NEITHER finejapanvietnam NOR jpcshop.

| SKU | Name | Category | EC | rr% | Rev (M) | margin% | Rev rank |
|-----|------|---------|-----|-----|---------|---------|---------|
| VTSC20001L001 | (*) Thực phẩm bảo vệ sức khỏe Cordyceps | Dietary Supplement | 120 | 28.3% | 816.9M | 69.0% | 6 |
| VCSL19001C001 | Thực phẩm bảo vệ sức khỏe Hyaluron & Collagen Plus | Dietary Supplement | 88 | 27.3% | 1.2M | -283.3% | 88 |
| VCSC23052H001 | Viên uống cải thiện huyết áp cao Gaba blood Fine J… | Dietary Supplement | 87 | 23.0% | 124.3M | 61.2% | 16 |
| VTSC21006L001 | (*) Royal Reishi | Dietary Supplement | 52 | 30.8% | 93.3M | -35.9% | 17 |
| VCST23024L001 | TPBVSK hỗ trợ điều trị tiểu đường Insuna Fujina 12… | Dietary Supplement | 48 | 27.1% | 47.1M | 37.7% | 27 |
| VCST22014G001 | Viên uống giảm cân cao cấp Calorie Burn - Chitosan… | Dietary Supplement | 48 | 25.0% | 196.6M | 34.9% | 13 |
| VCSC23030L001 | TPBVSK Genki Fami Kanzo Ukon 90 viên | Dietary Supplement | 43 | 20.9% | 54.3M | 43.4% | 24 |
| VTST23042L001 | (*) TPBVSK Fine Japan Natto Kinase | Dietary Supplement | 28 | 21.4% | 53.5M | 22.8% | 25 |
| VB23006 | Combo 2 gói Hatomugi | Dietary Supplement | 18 | 27.8% | 14.0M | N/A | 39 |
| VCST24001L001 | TPBVSK Natto Ichou Genki Fami 90v | Dietary Supplement | 15 | 33.3% | 24.6M | 40.5% | 36 |
| VCSC22006L001 | Thực phẩm bảo vệ sức khỏe Fine Japan Chondroitin &… | Dietary Supplement | 22 | 22.7% | 249.5M | 58.2% | 11 |
| VCSC23166L002 | Thực phẩm bảo vệ sức khỏe Cordyceps | Dietary Supplement | 19 | 21.1% | 39.3M | 53.3% | 29 |
| VB24018 | Thực phẩm bảo vệ sức khỏe Hyaluron & Collagen Plus | Dietary Supplement | 11 | 36.4% | 25.0M | -616.4% | 35 |
| VCSC23030L002 | TPBVSK Genki Fami Kanzo Ukon 90 viên | Dietary Supplement | 7 | 57.1% | 16.1M | 42.8% | 38 |
| VCST23024L002 | TPBVSK hỗ trợ điều trị tiểu đường Insuna Fujina 12… | Dietary Supplement | 10 | 30.0% | 34.1M | 37.1% | 33 |

**Top 5 gateway-absent SKUs combined revenue: 1082.9M**

## Finding b — Web catalog quality: dead-end + phantom listings

All web SKUs with repeat rate data have repeat_rate >15%. No clear dead-ends detected at this threshold.

**2 web SKU(s) with zero revenue in DB** (phantom/new/non-Sapo):
- `PVN149` — Fine Japan Vietnam
- `PVN148` — (Combo 2) Nước Uống Collagen Yến Fine Japan Hyaluron & Colla

**2 fjvn SKU(s) listed but price=0 (unavailable/sold-out):**
- `VCSL21002H010` — Thực phẩm bảo vệ sức khỏe Cordyceps Plus | rr%=34.3% | rev=1205.1M
- `VCST21003L001` — Thực phẩm bảo vệ sức khỏe Natto Kinase | rr%=26.1% | rev=765.3M

## Finding c — Deep discount (>30%) x realized margin

Using cleaned discount data (compare_at anomalies discarded). fjvn price=0 SKUs excluded.

| SKU | Name | Sites | Web disc% | Web price | margin% | Rev (M) | Assessment |
|-----|------|-------|-----------|-----------|---------|---------|-----------|
| VCSC23054B001 | Viên uống trắng da Coix Beauty tablets Wit… | fjvn+jpcs | 75% | 99,000 | 52.7% | 70.1M | healthy margin |
| VCST21003L001 | Thực phẩm bảo vệ sức khỏe Natto Kinase | jpcs | 50% | 901,600 | 73.0% | 765.3M | healthy margin |
| VCSL19001H010 | Thực phẩm bảo vệ sức khỏe Hyaluron & Colla… | fjvn+jpcs | 50% | 1,125,000 | 51.6% | 556.4M | healthy margin |
| PVN147 | Combo 2 Hộp Collagen Plus | fjvn | 50% | 2,250,000 | N/A | 62.9M | healthy margin |
| PVN151 | Combo 2 hộp Natto Kinase | fjvn | 50% | 1,568,000 | N/A | 8.4M | healthy margin |

**Note on VCST21003L001 and VCSL21002H010:** these have price=0 on fjvn (unavailable). Their jpcs discount is 50% and 0% respectively — not included in margin-risk analysis.

## Finding d — D2C catalog revenue coverage

| Metric | Value |
|--------|-------|
| Total internal retail net revenue | 12833.4M |
| Revenue covered by web-listed SKUs | 8954.0M (69.8%) |
| Revenue NOT on any D2C site | 3879.4M (30.2%) |
| DB SKUs not on web | 12 shown below (top 12 by rev) |

### Top revenue SKUs absent from both D2C sites

| SKU | Name | Rev (M) | Rev rank | margin% | rr% | Category |
|-----|------|---------|----------|---------|-----|---------|
| VTST23023L001 | (*) Thực phẩm bảo vệ sức khỏe Fine Japan Shark Car… | 941.1M | 5 | 68.6% | 10.5% | Dietary Supplement |
| VTSC20001L001 | (*) Thực phẩm bảo vệ sức khỏe Cordyceps | 816.9M | 6 | 69.0% | 28.3% | Dietary Supplement |
| VCSC22006L001 | Thực phẩm bảo vệ sức khỏe Fine Japan Chondroitin &… | 249.5M | 11 | 58.2% | 22.7% | Dietary Supplement |
| VCSC23166L001 | Thực phẩm bảo vệ sức khỏe Cordyceps | 199.2M | 12 | 23.0% | 17.2% | Dietary Supplement |
| VCST22014G001 | Viên uống giảm cân cao cấp Calorie Burn - Chitosan… | 196.6M | 13 | 34.9% | 25.0% | Dietary Supplement |
| VCSC22003G001 | Viên uống chống nắng UV Care Plus | 157.0M | 14 | 22.7% | 10.5% | Dietary Supplement |
| VTSL24010H010 | (*) Thực phẩm bảo vệ sức khỏe Hyaluron & Collagen … | 155.8M | 15 | 51.5% | 20.0% | Dietary Supplement |
| VCSC23052H001 | Viên uống cải thiện huyết áp cao Gaba blood Fine J… | 124.3M | 16 | 61.2% | 23.0% | Dietary Supplement |
| VTSC21006L001 | (*) Royal Reishi | 93.3M | 17 | -35.9% | 30.8% | Dietary Supplement |
| VCSP22001B001 | Bột uống Bone's Calcium for Kids | 84.1M | 18 | 38.1% | 14.1% | Dietary Supplement |
| VCST21003L002 | Thực phẩm bảo vệ sức khỏe Natto Kinase | 62.3M | 22 | 77.4% | 8.3% | Dietary Supplement |
| VTSP20002H030 | (*) TPBVSK Fine Japan Metabo Green Tea | 59.2M | 23 | -1347.0% | 12.5% | Dietary Supplement |

## Finding e — Web price vs internal last-sold price

Both prices are VAT-inclusive. `last_sold_price` from dim_products = last recorded Sapo transaction price.

| SKU | Name | Web price | Last sold | Delta% | Notes |
|-----|------|-----------|-----------|--------|-------|
| VCSC23054B001 | Viên uống trắng da Coix Beauty tablets Wit… | 99,000 | 390,000 | -74.6% | web lower |
| VCSL19001H010 | Thực phẩm bảo vệ sức khỏe Hyaluron & Colla… | 1,125,000 | 2,250,000 | -50.0% | web lower |
| PVN151 | Combo 2 hộp Natto Kinase | 1,568,000 | 3,136,000 | -50.0% | web lower |
| VCST21003L001 | Thực phẩm bảo vệ sức khỏe Natto Kinase | 901,600 | 1,568,000 | -42.5% | web lower |
| PVN150 | Combo 2 hộp Shark Cartilage | 3,880,000 | 4,850,000 | -20.0% | web lower |
| VCSL21001H010 | Thực phẩm bảo vệ sức khỏe Hyaluron & Colla… | 2,640,000 | 3,300,000 | -20.0% | web lower |
| VCST21004L001 | Thực phẩm bảo vệ sức khỏe Shark Cartilage … | 1,952,125 | 2,425,000 | -19.5% | web lower |
| VTSL21001H010 | (*) TPBVSK Hyaluron & Collagen with Swallo… | 2,662,296 | 3,300,000 | -19.3% | web lower |
| VTSL24009H010 | (*) TPBVSK Fine Japan Cordyceps Plus | 3,248,014 | 4,000,000 | -18.8% | web lower |
| PVN146 | Combo 2 hộp Cordyceps Plus | 6,000,000 | 7,336,000 | -18.2% | web lower |
| PVN148 | (Combo 2) Nước Uống Collagen Yến Fine Japa… | 4,950,000 | 5,936,000 | -16.6% | web lower |
| VB24010 | Combo 2 lọ Cordyceps | 3,058,300 | 3,598,000 | -15.0% | web lower |
| VCSC19002L001 | Thực phẩm bảo vệ sức khỏe Fucoidan | 1,950,750 | 2,295,000 | -15.0% | web lower |
| VTSC19002L001 | (*) Thực phẩm bảo vệ sức khỏe Fucoidan | 1,955,340 | 2,295,000 | -14.8% | web lower |
| PVN147 | Combo 2 Hộp Collagen Plus | 2,250,000 | 2,598,000 | -13.4% | web lower |
| PVN149 | Fine Japan Vietnam | 3,672,000 | 4,198,000 | -12.5% | web lower |
| VCSC20001L001 | Thực phẩm bảo vệ sức khỏe Cordyceps | 1,619,100 | 1,799,000 | -10.0% | close |

## Summary of Key Numbers

| Metric | Value |
|--------|-------|
| Web products fjvn / jpcs | 15 / 8 |
| Web SKUs total (union) | 18 |
| SKUs on BOTH sites | 5 |
| fjvn SKUs unavailable (price=0) | 2 |
| DB economics SKUs | 107 |
| Economics date range | 2024-06 to 2026-05 |
| Total retail net revenue | 12833.4M |
| D2C web revenue coverage | 8954.0M (69.8%) |
| Gateway SKUs absent from web (≥5 EC, ≥20% rr) | 21 |
| Dead-end SKUs on web (rr ≤15%) | 0 |
| Web SKUs with zero DB revenue (phantoms) | 2 |
| Deep-discount SKUs on web (>30%, cleaned) | 5 |

## Unresolved questions / caveats

- `avg_margin_pct` = simple average across snapshot months, not revenue-weighted; seasonally skewed SKUs may show distorted margin.
- `VTSC20001L001` (top gateway absent, rev 816.9M) — SKU with `(*)` prefix in name; verify if it is a bundle/pack SKU vs. single unit before prioritising for listing.
- Entry-repeat rate: 'COR1' appeared as entry_sku in top results — likely an old/non-standard SKU code without dim_products mapping; excluded from main table.
- jpcshop has no `data-fgotracking` HTML tags; SKU extracted from `variants[0].sku` directly.
- PVN147/PVN148/PVN149/PVN150/PVN151 on fjvn are non-standard SKU codes (no `V` prefix pattern match) — likely non-Fine-Japan or promotional bundles; no DB economics row found.
- H010 SKUs (VTSL24009H010, VTSL21001H010) use `realized_margin_pct` which has the 2026 COGS repoint correction applied — values should be trustworthy.
- Web price vs last_sold_price gap analysis: if last_sold_price reflects a B2B/wholesale transaction, comparison to D2C web price may be misleading.
