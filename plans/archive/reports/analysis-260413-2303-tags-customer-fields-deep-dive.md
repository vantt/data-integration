# Deep Analysis: Order Tags, Customer Tags, Customer Type & Customer Group

**Date:** 2026-04-13 | **Dataset:** Sapo raw parquet (2,782 unique orders, 202 unique customers)

---

## 1. Order Tags (`$.tags`)

### Coverage
| Metric | Count | % |
|--------|-------|---|
| Total unique orders | 2,782 | 100% |
| Empty tags `[]` | 2,181 | 78.4% |
| **Has real tags** | **601** | **21.6%** |

### Semantic Categories (130 unique individual tags)

| Category | Orders | Key Tags |
|----------|--------|----------|
| **Marketplace Shop ID** | ~350 | `Shopee_Fine Japan Vietnam` (187), `Shopee_JPC SHOP` (109), `Shopee_thehealthyus` (16), `Lazada_Fine Japan Vietnam` (6), `Tiki_FINE WORLD GROUP` (1) |
| **Marketplace Platform** | ~312 | `Shopee` (312), `Lazada` (7), `Tiki` (1) |
| **Payment/Fulfillment Status** | ~208 | `Đơn hàng đã thanh toán` (143), `Giao hàng thành công` (53), `COD` (12) |
| **Discount Deferred (CK SAU)** | ~80 | `CK SAU BS 30%` (32), `CK SAU BS 15%` (14), `CK SAU 10%` (7), `CK SAU 5%` (7), `CK SAU BS 10%` (6), etc. |
| **Consignment (Ký gửi)** | ~40 | `Hàng ký gửi` (32), `Ký gửi` (8) |
| **Sample/Gift** | ~60 | `HÀNG MẪU` (20), `Quà tặng 20.10` (16), `Quà tặng` (11), `Hàng tặng` (8), `Hàng sampling` (6), `Sample` (3) |
| **Source/Channel Tracking** | ~46 | `sapo_social` (16), `sapoweb` (14), `page_*` (22), `bizweb` (1) |
| **Ad/Post Tracking** | ~30 | `Ad_id_*` (~12), `Post_ID_*` (~14), `ID Khách hàng_*` (~10) |
| **Affiliate/KOL** | ~13 | `ECOMOBI BOOKING` (7), `ECOMOBI Affiliate` (3), `KOC Review` (3) |
| **Product Tags** | ~20 | `cordyceps` (11), `Fucoidan` (6), `Collagen` (1), `Vitamin CD` (1) |
| **Invoice** | ~5 | `ĐÃ XUẤT HÓA ĐƠN` (2), `Xuất hóa đơn` (1), `HÀNG XÁCH TAY KHÔNG XUẤT HÓA ĐƠN` (1) |
| **Compensation** | ~10 | `TRẢ THƯỞNG CHƯƠNG TRÌNH DU LỊCH 2024` (8), `TRẢ PHÍ TRƯNG BÀY*` (3) |
| **Shipping** | ~15 | `Freeship` (12), `Ngoại thành` (2), `Giao lại lần 1` (1) |
| **One-off/Noise** | ~15 | Customer names, specific order notes, test tags |

### Key Insight: Tags Already Used for Source Mapping
`stg_sapo_orders.sql` already uses `ref_order_sources.mapping_tag` to split generic Shopee/Lazada source_ids into shop-level sources (e.g., `Shopee_Fine Japan Vietnam` → `3988158_1`). This is the **most critical** current use of order tags.

### Source Distribution (all orders)
| Source | Platform | Count |
|--------|----------|-------|
| US | CrossBorder | 1,096 |
| Đại Lý | Wholesale/B2B | 1,056 |
| Shopee | Ecom | 317 |
| Other | Other | 66 |
| Web | Website | 64 |
| Pos | Retail | 42 |
| Facebook | Social | 34 |
| Zalo | Social | 27 |
| Quà Tặng | System | 25 |
| Chiaki | Ecom | 18 |
| Others (5) | Mixed | ~31 |

---

## 2. Customer Tags (`$.tags`)

### Coverage
| Metric | Count | % |
|--------|-------|---|
| Total unique customers | 202 | 100% |
| Empty tags `[]` | 40 | 19.8% |
| **Has real tags** | **162** | **80.2%** |

### Individual Tag Values (7 unique tags)
| Tag | Customers | Meaning |
|-----|-----------|---------|
| `Shopee` | 146 | Acquired via Shopee |
| `Fine Japan Vietnam` | 82 | Shop: Fine Japan Vietnam |
| `JPC SHOP` | 57 | Shop: JPC SHOP |
| `thehealthyus` | 12 | Shop: thehealthyus |
| `Web` | 7 | Acquired via web |
| `sapo_social` | 5 | Acquired via social (Sapo Social) |
| `Lazada` | 5 | Acquired via Lazada |

### Common Tag Combos
| Combo | Count |
|-------|-------|
| `[Shopee, Fine Japan Vietnam]` | 77 |
| `[Shopee, JPC SHOP]` | 57 |
| `[Shopee, thehealthyus]` | 12 |
| `[Web]` | 6 |
| `[Lazada, Fine Japan Vietnam]` | 5 |
| `[sapo_social]` | 4 |
| `[sapo_social, Web]` | 1 |

### Insight
Customer tags = **acquisition channel + shop identifier**. Directly mirrors order marketplace tags. Useful for customer segmentation by acquisition source.

---

## 3. Customer Group (`$.customer_group`, `$.group_name`)

### Primary Group (group_name)
| Group | Code | Count | % |
|-------|------|-------|---|
| **Bán lẻ** (Retail) | BANLE | 198 | 98.0% |
| **Bán buôn** (Wholesale) | BANBUON | 4 | 2.0% |

### Full Customer Group List (from Sapo API `/admin/customer_groups.json`)

| ID | Name | Name (VN) | Code | Type | Customers |
|----|------|-----------|------|------|-----------|
| 1812238 | RETAIL | Bán lẻ | BANLE | Default | 6,447 |
| 1812239 | WHOLESALE | Bán buôn | BANBUON | Default | 159 |
| 1812240 | VIP | Vip | VIP | Default | 1 |
| 2192773 | Số lần mua >= 2 | Số lần mua >= 2 | CTN00005 | Auto-segment | - |
| 2192866 | Mua trên 10tr | Mua trên 10tr | CTN00006 | Auto-segment | - |
| 2192871 | Mua trên 05tr | Mua trên 05tr | CTN00007 | Auto-segment | - |
| 2192872 | Mua dưới 03tr | Mua dưới 03tr | CTN00008 | Auto-segment | - |
| 2192877 | Mua trên 20tr | Mua trên 20tr | CTN00009 | Auto-segment | - |
| 2209885 | Nhóm Test 1 | Nhóm Test 1 | CTN00010 | Test | 0 |
| 2209886 | Nhóm Test 2 | Nhóm Test 2 | CTN00011 | Test | 0 |
| 2281219 | Ký Gửi | Ký Gửi | KY_GUI | Manual | 11 |
| 2308212 | Selly | Selly | CTN00013 | Manual | 104 |
| 2421894 | US | US | CTN00014 | Manual | 662 |
| 2713804 | The Healthy Us | The Healthy Us | THU | Manual | - |
| 2713809 | Fine Japan | Fine Japan | FJP | Manual | - |

**3 loại nhóm:**
- **Default (3):** RETAIL, WHOLESALE, VIP — nhóm hệ thống
- **Auto-segment (5):** Phân khúc tự động theo chi tiêu/tần suất mua (Mua dưới 03tr, Mua trên 05/10/20tr, Số lần mua >= 2)
- **Manual (4):** Nhóm tay — kênh bán (US, Selly, Ký Gửi, The Healthy Us, Fine Japan)
- **Test (2):** Nhóm test — bỏ qua

### Multi-Group Membership (`$.group_ids`)
Customers belong to **multiple groups** via `group_ids` array. Most common combos:

| Combo | Count | Interpretation |
|-------|-------|----------------|
| [RETAIL, Mua dưới 03tr] | 77 | Retail + low-spend segment |
| [RETAIL, Mua dưới 03tr, Fine Japan] | 41 | Retail + low-spend + FJP brand |
| [RETAIL, Fine Japan, Mua dưới 03tr] | 20 | Same as above (order varies) |
| [RETAIL] only | 7 | Retail without auto-segment |
| Others | ~57 | Various multi-group combos |

> **Insight:** `group_ids` = primary group + auto-spending-tier + brand/channel assignment. The auto-segments (spending tiers) are set by Sapo rules, not manually.

---

## 4. Customer Type (`$.type`)

**Result: Field does NOT exist at customer entity level.** All 202 customers return `NULL` for `$.type`.

The `type` field exists **inside the `customer_group` nested object** (`customer_group.type = "customer"`), which is a Sapo system field, not a user-defined classification. Not useful for analytics.

---

## 5. Assessment for dbt Transformation Design

### What's Already Working
- **Order tags → source mapping** via `ref_order_sources.mapping_tag` in `stg_sapo_orders` — correctly splits marketplace shop-level sources.

### High-Value Transformation Opportunities

#### A. Order Tag Classification (NEW `stg_order_tags` or enrichment in `stg_sapo_orders`)
Unnest order tags into a bridge table or flag columns:

| Derived Field | Logic | Value |
|---------------|-------|-------|
| `is_consignment` | tag ILIKE '%ký gửi%' | Exclude from revenue reporting |
| `is_sample_or_gift` | tag matches sample/mẫu/tặng/quà | Exclude from revenue, track as marketing cost |
| `has_deferred_discount` | tag LIKE '%CK SAU%' or '%CHIẾT KHẤU%' | Flag for margin analysis, discount reconciliation |
| `deferred_discount_pct` | Extract % from CK SAU tags | Quantify deferred discount impact |
| `is_compensation` | tag LIKE '%TRẢ THƯỞNG%' or '%TRẢ PHÍ%' | Exclude from organic revenue |
| `ad_tracking_ids` | Extract Ad_id, Post_ID, ID Khách hàng | Link to Facebook ad attribution |
| `is_affiliate` | tag matches ECOMOBI/KOC | Flag affiliate channel orders |
| `product_focus` | tag matches Fucoidan/cordyceps/Collagen | Product-level campaign tagging |

#### B. Customer Acquisition Source (NEW dim or enrichment in `dim_customers`)
From customer tags:

| Derived Field | Logic |
|---------------|-------|
| `acquisition_platform` | First tag: Shopee/Lazada/Web/sapo_social |
| `acquisition_shop` | Second tag: Fine Japan Vietnam/JPC SHOP/thehealthyus |

#### C. Customer Group Enhancement (NOW RESOLVED)
All 15 group IDs mapped via Sapo API. Actionable groups:

| Field | Source | Value |
|-------|--------|-------|
| `customer_group_primary` | `$.customer_group.name` | RETAIL / WHOLESALE / VIP |
| `customer_spending_tier` | Extract from `group_ids` matching spending-segment IDs | Mua dưới 03tr / Mua trên 05tr / 10tr / 20tr |
| `customer_purchase_frequency` | `group_ids` contains 2192773 | Số lần mua >= 2 (repeat buyer flag) |
| `customer_brand_group` | `group_ids` matching brand IDs | Fine Japan / The Healthy Us |
| `customer_channel_group` | `group_ids` matching channel IDs | US / Selly / Ký Gửi |

**Recommendation:** Create a `ref_customer_groups` seed from the API data, then unnest `group_ids` in a bridge model to enable multi-group analytics.

#### D. Customer Type
- **Skip entirely** — field doesn't exist at entity level. Not extractable.

### Noise Tags to Ignore
- `Đơn hàng đã thanh toán`, `Giao hàng thành công` — duplicates fulfillment/payment status already tracked in order fields
- `Thanh toán khi giao hàng (COD)`, `OnePay...` — duplicates payment method info
- `Freeship`, `Ngoại thành` — shipping metadata, low volume
- Customer names, specific invoice references — one-off operational notes

### Recommended Priority
1. **P0:** Order tag → `is_consignment`, `is_sample_or_gift` flags (directly impacts revenue accuracy)
2. **P1:** `has_deferred_discount` + `deferred_discount_pct` (margin analysis)
3. **P2:** Customer `acquisition_platform` + `acquisition_shop` (customer segmentation)
4. **P3:** Ad tracking extraction (Facebook attribution — only ~30 orders, low ROI for now)
5. **Skip:** Customer type (no data), customer group_ids (unmapped), status-duplicate tags

---

## Unresolved Questions
1. ~~Customer group IDs~~ → **RESOLVED** via Sapo API. All 15 groups mapped.
2. Are deferred discount tags (`CK SAU BS 30%`) reconciled somewhere? Is the discount already reflected in `total_discount` or is it truly deferred (applied later)?
3. Should consignment orders (`Hàng ký gửi`) be completely excluded from revenue or tracked separately?
4. Auto-segment groups (spending tiers) — are they maintained by Sapo rules automatically, or do they need manual updates?
