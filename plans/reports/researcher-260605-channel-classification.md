# Channel Classification Model — Complete Extraction
> **FOR:** Staff-facing guide  
> **SOURCE OF TRUTH:** dim_channels.sql, ref_order_sources.csv, channel-grouping-analysis.md, report_segmentation.md  
> **DATE:** 2026-06-05  
> **STATUS:** Complete — Ready for staff documentation

---

## SECTION 1: THE 3-TIER TAXONOMY

### Tier 1: Channel Category (Business Layer)

**Definition:** Broadest grouping — answers "Is this a sales revenue channel?"

| **channel_category** | **Definition** | **When to Use** | **Business Impact** |
|---|---|---|---|
| **Online-Ecommerce** | Sales via marketplaces, social, or web — digital B2C channels | Daily retail reporting, KPI tracking | Include in sales revenue (unless customer is wholesale) |
| **Offline** | Physical retail stores, wholesale/B2B channels, direct sales (CS/Telesale) | Store operations, B2B tracking, direct sales monitoring | Include in sales revenue |
| **Internal** | System channels (test, gifts, staff benefits) + cross-border fulfillment (US) | Finance/operations dashboards only | EXCLUDE from revenue reporting |

### Tier 2: Channel Format (Operational Layer)

**Definition:** Medium grouping — operational classification within each category.

| **channel_format** | **Tier 1 Maps To** | **Includes** | **Examples** |
|---|---|---|---|
| **Marketplace** | Online-Ecommerce | Shopee, Lazada, Tiki, GrabMart, Sendo | 8075218, 3988158, 3988155, 3988156 |
| **Social** | Online-Ecommerce | Facebook, Instagram, Zalo, TikTok Shop | 3988153, 4461848, 3988154, 6500681 |
| **Web** | Online-Ecommerce | Direct website orders | 3988152, 4609259 |
| **Retail** | Offline | Point-of-Sale (POS) stores | 3988157 |
| **B2B** | Offline | Wholesale channels: Đại Lý, Chợ sỉ | 4164989, 7054173 |
| **Direct** | Offline | CS (Customer Service) or Telesale | 7503763, 4517138 |
| **System** | Internal | Test Sản Phẩm, Ưu đãi NV, Quà Tặng | 6656236, 5384969, 5384956 |
| **CrossBorder Fulfillment** | Internal | US: logistics service for FG Care US → VN | 4110169 |
| **Other** | Internal | Unclassified (fallback, generic "Other") | 3988159 |

### Tier 3: Platform (Specific Implementation)

**Definition:** Platform-specific detail — which marketplace, which store, etc.

**Examples:**
- `Shopee - Fine Japan Vietnam` (composite source 3988158_1)
- `Lazada - JPC SHOP` (composite source 3988155_2)
- `POS - 16 Trương Định` (generic source 3988157 expanded by location)
- `Facebook` (simple source)

---

## SECTION 2: IS_SALES_CHANNEL RULE (CRITICAL)

### Exact Rule — Verbatim from dim_channels.sql Line 138

```sql
channel_format NOT IN ('System', 'CrossBorder Fulfillment', 'Other') as is_sales_channel
```

### Decision Table: Format → is_sales_channel

| **channel_format** | **is_sales_channel** | **Reason** | **Default Scope** |
|---|---|---|---|
| **Marketplace** | `true` | Valid retail/wholesale sales | scope_sales |
| **Social** | `true` | Valid retail/wholesale sales | scope_sales |
| **Web** | `true` | Valid retail/wholesale sales | scope_sales |
| **Retail** (POS) | `true` | Physical store sales | scope_sales |
| **B2B** | `true` | Wholesale sales (Đại Lý, Chợ sỉ) | scope_b2b |
| **Direct** (CS/Telesale) | `true` | Real sales, NOT internal operations | scope_sales |
| **System** | `false` | Internal operations: test, gifts, staff discounts | EXCLUDE |
| **CrossBorder Fulfillment** | `false` | Logistics service (US), NOT FG Care VN revenue | EXCLUDE |
| **Other** | `false` | Unclassified/fallback; treat as excluded | EXCLUDE |

**Rule in Plain English:**
- ✅ **INCLUDE in revenue:** Marketplace, Social, Web, Retail, B2B, Direct
- ❌ **EXCLUDE from revenue:** System, CrossBorder Fulfillment, Other

---

## SECTION 3: REF_ORDER_SOURCES.CSV — SOURCE OF TRUTH

### Full Table: Every Order Source Mapped

**Columns:** id | name | channel_format | source_type | market | is_generic_source | is_sales_channel (derived) | channel_category (derived)

---

### A. ACTIVE, SALES CHANNELS (is_sales_channel = true)

| **ID** | **Source Name** | **Format** | **source_type** | **Market** | **Generic?** | **Usage** | **Notes** |
|---|---|---|---|---|---|---|---|
| **3988158** | Shopee | Marketplace | channel | Domestic | YES | Generic parent; expanded by storefront + location | Includes 8 child variants (Fine Japan, JPC, etc.) |
| **3988158_1** | Shopee - Fine Japan Vietnam | Marketplace | channel | Domestic | NO | Map directly to orders from this storefront | Composite source (brand-specific) |
| **3988158_2** | Shopee - thehealthyus | Marketplace | channel | Domestic | NO | Map directly | Composite source |
| **3988158_3** | Shopee - JPC SHOP | Marketplace | channel | Domestic | NO | Map directly | Composite source |
| **3988158_4** | Shopee - JPC OFFICIAL | Marketplace | channel | Domestic | NO | Map directly | Composite source |
| **3988158_5** | Shopee - FG CARE | Marketplace | channel | Domestic | NO | Map directly | Composite source |
| **3988158_6** | Shopee - FWG Vietnam | Marketplace | channel | Domestic | NO | Map directly | Composite source |
| **3988158_7** | Shopee - Fine Care | Marketplace | channel | Domestic | NO | Map directly | Composite source |
| **3988158_8** | Shopee - FINE WORLD GROUP | Marketplace | channel | Domestic | NO | Map directly | Composite source |
| **3988155** | Lazada | Marketplace | channel | Domestic | YES | Generic parent; expanded by storefront + location | Includes 7 child variants |
| **3988155_1** | Lazada - Fine Japan Vietnam | Marketplace | channel | Domestic | NO | Map directly | Composite |
| **3988155_2** | Lazada - JPC SHOP | Marketplace | channel | Domestic | NO | Map directly | Composite |
| **3988155_3** | Lazada - The Healthy Us | Marketplace | channel | Domestic | NO | Map directly | Composite |
| **3988155_4** | Lazada - Fine Japan store | Marketplace | channel | Domestic | NO | Map directly | Composite |
| **3988155_5** | Lazada - FINE WORLD GROUP | Marketplace | channel | Domestic | NO | Map directly | Composite |
| **3988155_6** | Lazada - FG CARE | Marketplace | channel | Domestic | NO | Map directly | Composite |
| **3988155_7** | Lazada - Fine Care | Marketplace | channel | Domestic | NO | Map directly | Composite |
| **3988156** | Tiki | Marketplace | channel | Domestic | YES | Generic parent; expanded by brand + location | Includes 2 child variants |
| **3988156_1** | Tiki - FINE WORLD GROUP | Marketplace | channel | Domestic | NO | Map directly | Composite |
| **3988156_2** | Tiki - FG GLOBAL | Marketplace | channel | Domestic | NO | Map directly | Composite |
| **7165820** | POPS | Marketplace | channel | Domestic | NO | (INACTIVE — status=false) | ⚠️ May be archived |
| **7139806** | Leflair | Marketplace | channel | Domestic | NO | (INACTIVE) | ⚠️ May be archived |
| **5686178** | Selly | Marketplace | channel | Domestic | NO | (INACTIVE) | ⚠️ May be archived |
| **6569908** | Chiaki | Marketplace | channel | Domestic | NO | (INACTIVE) | ⚠️ May be archived |
| **7312199** | Tiki Cross Border | Marketplace | channel | **Export** | NO | Cross-border marketplace (separate P&L) | Different from domestic Tiki |
| **3988152** | Web | Web | channel | Domestic | YES | Generic parent; expanded by location (if store-bound) | Direct website |
| **4609259** | WebOrder | Web | channel | Domestic | YES | Generic parent; expanded by location | Ecommerce order form |
| **3988153** | Facebook | Social | channel | Domestic | YES | Generic parent; expanded by location | All FB messages/comments |
| **8075218** | FaceBookJPC | Social | channel | Domestic | NO | JPC-specific Facebook orders | Storefront variant |
| **8075219** | FaceBookFJPTViet | Social | channel | Domestic | NO | Fine Japan Vietnam-specific FB orders | Brand variant |
| **4461848** | Instagram | Social | channel | Domestic | YES | Generic parent; expanded by location | All IG messages/comments |
| **3988154** | Zalo | Social | channel | Domestic | YES | Generic parent; expanded by location | All Zalo messages |
| **6500681** | TiktokShop | Marketplace | channel | Domestic | YES | Generic parent; TikTok Shop orders | Newer marketplace |
| **4999848** | GrabMart | Marketplace | channel | Domestic | YES | Generic parent; Grab food/convenience | Cross-platform |
| **3988157** | Pos | Retail | channel | Domestic | YES | Generic parent; expanded to each store location | Each store gets own row |
| **4164989** | Đại Lý | B2B | customer_type | Domestic | NO | Wholesale distributor orders | B2B channel, sales counted |
| **7054173** | Chợ sỉ | B2B | customer_type | Domestic | NO | Wholesale market orders | B2B channel, sales counted |
| **7503763** | CS | Direct | channel | Domestic | NO | Customer Service manual order creation | **NOW: Sales revenue (confirmed 2026-04-13)** |
| **4517138** | Telesale | Direct | channel | Domestic | NO | Telesale team manual order creation | **NOW: Sales revenue (confirmed 2026-04-13)** |

---

### B. INTERNAL CHANNELS (is_sales_channel = false)

| **ID** | **Source Name** | **Format** | **source_type** | **Market** | **channel_category** | **NOT in Revenue** | **Why** |
|---|---|---|---|---|---|---|
| **6656236** | Test Sản Phẩm | System | purpose | Domestic | Internal | ❌ Test orders, no revenue | Testing & QA |
| **5384969** | Ưu đãi Nhân Viên | System | purpose | Domestic | Internal | ❌ Staff discount pricing | Staff benefit, internal only |
| **5384956** | Quà Tặng | System | purpose | Domestic | Internal | ❌ Gifts (78.7% discount = zero net value) | Promotional gifts, no actual sale |
| **4110169** | US | CrossBorder Fulfillment | arrangement | **Export** | Internal | ❌ FG Care VN is fulfillment only, not seller | Revenue belongs to FG Care US; VN only provides logistics service; doanh thu = 0đ |
| **3988159** | Other | Other | channel | Domestic | Internal | ❌ Unclassified fallback | Catch-all for unmapped sources |

---

### C. INACTIVE/PENDING CONFIRMATION

| **ID** | **Source Name** | **Status** | **Decision** | **Action** |
|---|---|---|---|---|
| **7165820** | POPS | false | Archive? | ⚠️ CẦN XÁC NHẬN: Should this be marked archived? |
| **7139806** | Leflair | false | Archive? | ⚠️ CẦN XÁC NHẬN: Should this be marked archived? |
| **5686178** | Selly | false | Archive? | ⚠️ CẦN XÃC NHẬN: Should this be marked archived? |
| **6569908** | Chiaki | false | Archive? | ⚠️ CẦN XÁC NHẬN: Should this be marked archived? |

---

## SECTION 4: CHANNEL ASSIGNMENT — HOW DOES AN ORDER GET ITS CHANNEL?

### Scenario: A Staff Member Creates an Order in Sapo

**Question:** When you create an order in Sapo, what determines its channel_key (and thus channel_category, is_sales_channel, etc.)?

### Flow: Sapo → Pipeline → dim_channels

```
STAFF CREATES ORDER in Sapo
    ↓
order.source_id = [selected by staff from dropdown]
    ↓
stg_sapo_orders.source_id matches ref_order_sources.id
    ↓
dim_channels joins on source_id + location_id (if generic)
    ↓
channel_name, channel_format, channel_category, is_sales_channel
    ↓
fact_orders.channel_key = surrogate_key(source_id, location_id)
```

### WHEN DOES AN ORDER LAND IN "Other" / "Unknown"?

**Scenario 1: Source ID Not Recognized**
- Staff picks a source that no longer exists in ref_order_sources
- Pipeline cannot join → falls back to **Unknown Member**
- Result: channel_name = `'Unknown'`, channel_format = `'Other'`, is_sales_channel = `false`
- **Action:** Update ref_order_sources or verify source still active

**Scenario 2: Source ID = "Other" (ID 3988159)**
- Staff explicitly selects "Other" from dropdown
- Maps to format = `'Other'`, channel_category = `'Internal'`, is_sales_channel = `false`
- **Action:** Ask staff why — should be caught during order entry

**Scenario 3: Generic Source + Unknown Location**
- Staff picks generic source (e.g., POS) but location_id not in ref_branch_locations
- Pipeline can't expand to specific store → creates `'POS - Unknown Location'` fallback row
- Result: channel_category = `'Offline'`, is_sales_channel = `true` (still valid)
- **Action:** Verify location exists in ref_branch_locations; add if missing

### WHAT STAFF MUST DO: SOURCE SELECTION RULES

**For Revenue to Count as Sales:**

| **You Are Creating...** | **Pick This Source** | **NOT This** | **Reason** |
|---|---|---|---|
| **Retail customer order** (1-10 boxes) | Shopee / Lazada / Zalo / Facebook / Web / POS | "Other" | Direct mapping to public channel |
| **Wholesale customer order** (50+ boxes, fixed discount) | Đại Lý or Chợ sỉ | "Other" | B2B channel, discount is price not promotion |
| **Phone/chat order from customer** | CS or Telesale | "Other" | Direct sales team (confirmed 2026-04-13) |
| **Internal use / testing** | Test Sản Phẩm | Any sales channel | Won't count as revenue |
| **Gift / promo giveaway** | Quà Tặng | Any sales channel | Won't count as revenue |
| **Staff personal order** | Ưu đãi Nhân Viên | Any sales channel | Won't count as revenue |
| **US customer fulfillment order** | US | Domestic channels | Cross-border logistics only |

**Formula:**
```
✅ Revenue counts IF:
   source.is_sales_channel = true 
   AND source.channel_format NOT IN ('System', 'CrossBorder Fulfillment', 'Other')
```

---

## SECTION 5: WHOLESALE CUSTOMER IDENTIFICATION (Hidden B2B)

### The Problem

**~36 wholesale customers hide on retail channels:**
- Ordered on Zalo, Facebook, Web, POS, Other
- Labeled "RETAIL" in Sapo
- Discount: 40–73% (fixed wholesale pricing, not promotion)
- Total impact: ~800M net revenue misclassified as retail

### Staff Selection Problem

**Symptom:** Order created with source = "Zalo", customer_type = "RETAIL", but customer is actually a distributor.

**Result:** 
- is_sales_channel = `true` (correct)
- channel_format = `'Social'` (correct)
- but customer_type = `'RETAIL'` (WRONG — should be `'WHOLESALE'`)
- → Discount analysis includes this as "promotion", breaks metrics

### Current Known Wholesale Customers (HIGH CONFIDENCE)

**Names:** Nguyễn Hiếu, Quang, Huynh Tri Bao, Huỳnh Thị Tuyết Trinh, Petter Phạm, Lê Sơn, chị Quyên, Boilam Vo Xuan, Chị Lan  
**Metric:** discount 55–73%, order count ≥4, AOV ≥2M, channels = Zalo/Facebook/Other/Web/POS  
**Status:** ✅ Found 2026-05-26, file: `plans/reports/wholesale-customers-review-260526.csv`  
**Next:** Await Sales confirmation, tag customer_type = `'WHOLESALE'` in Sapo

### Why This Matters for Staff

**Before Selection:**
- You know customer "Quang" buys in bulk, wants 50% discount
- You create order, pick Zalo (where he contacted you)
- You enter discount 50%

**After Selection:**
- ❌ WRONG PATH: Discount counted as "promotion" in retail analytics
  ```sql
  SELECT SUM(discount) FROM fact_orders 
  WHERE channel_format = 'Social'  -- includes Quang
  -- Result: Zalo discount rate = 28% (inflated by hidden wholesale)
  ```
- ✅ RIGHT PATH: Customer tagged as WHOLESALE
  ```sql
  SELECT SUM(discount) FROM fact_orders 
  WHERE customer_type = 'WHOLESALE'
  -- Result: B2B discount rate = 45% (accurate wholesale pricing)
  ```

**Current Status:** Waiting for Sales team to confirm the 36-person list. Once confirmed, each customer gets tagged in Sapo `customer_type = 'WHOLESALE'` (or PARTNER). Then dim_customers will expose the tag for analysis.

---

## SECTION 6: ORDER_NATURE DIMENSION (PROPOSED)

### Background

Current 3-tier (category/format/platform) classifies "what channel," not "what kind of sale."

Proposed **order_nature** answers "what kind of sale is this?"

### Proposed Values

| **order_nature** | **Definition** | **Source Identification** | **is_sales_channel** | **Include in Revenue** |
|---|---|---|---|---|
| **retail_sale** | B2C sale, market price, no fixed discount | channel NOT in System/CrossBorder/Other + customer_type = 'RETAIL' | ✅ true | ✅ YES |
| **wholesale** | B2B sale, fixed wholesale discount | customer_type = 'WHOLESALE' OR channel = Đại Lý/Chợ sỉ | ✅ true | ✅ YES |
| **cross_border_fulfillment** | Logistics service for FG Care US → VN | channel = 'US' | ❌ false | ❌ NO (doanh thu = 0đ) |
| **staff_benefit** | Staff personal purchase at discount | source = 'Ưu đãi Nhân Viên' | ❌ false | ❌ NO |
| **gift** | Promotional gift / giveaway | source = 'Quà Tặng' | ❌ false | ❌ NO |
| **test** | QA / product testing | source = 'Test Sản Phẩm' | ❌ false | ❌ NO |
| **affiliate** | CTV (content creator) orders | customer_type = 'CTV' | ✅ true | ❓ MAYBE (needs confirmation) |

### Derivation Logic (Pseudo-Code)

```python
IF source.channel_format = 'System':
    order_nature = 'test' | 'gift' | 'staff_benefit' (based on source name)
ELIF source.channel_format = 'CrossBorder Fulfillment':
    order_nature = 'cross_border_fulfillment'
ELIF customer.customer_type = 'WHOLESALE':
    order_nature = 'wholesale'
ELIF customer.customer_type = 'CTV':
    order_nature = 'affiliate'
ELSE:
    order_nature = 'retail_sale'
```

### Why This Matters

**Example: Discount Analysis**

❌ Without order_nature:
```sql
SELECT 
    channel_format,
    AVG(discount_pct) as avg_discount
FROM fact_orders
WHERE is_sales_channel = true
GROUP BY channel_format
-- Result: Zalo 28% (includes hidden wholesale customers)
```

✅ With order_nature:
```sql
SELECT 
    channel_format,
    AVG(discount_pct) as avg_discount
FROM fact_orders
WHERE is_sales_channel = true
  AND order_nature = 'retail_sale'
GROUP BY channel_format
-- Result: Zalo 12% (accurate for retail-only)
```

---

## SECTION 7: REPORT SCOPES & FILTERING RULES

### Three Mandatory Scopes for Reporting

From report_segmentation.md § 3:

#### scope_sales (Layer 1: Executive)
```sql
WHERE is_sales_channel = true
  AND status NOT IN ('CANCELLED', 'Voided')
```
**Use for:** CEO dashboards, total revenue overview, business health  
**Includes:** Retail + Wholesale + Partner (all valid sales)  
**Excludes:** System, CrossBorder, Other, Cancelled  

#### scope_retail (Layer 2: Retail Operations)
```sql
WHERE is_sales_channel = true
  AND status NOT IN ('CANCELLED', 'Voided')
  AND customer_type = 'RETAIL'
```
**Use for:** Promotion analysis, marketing ROI, customer acquisition, discount trends  
**Includes:** B2C orders only  
**Excludes:** B2B, staff, gift, test, cancelled  
**⚠️ MANDATORY** for any discount/promotion report  

#### scope_b2b (Layer 2: B2B Operations)
```sql
WHERE is_sales_channel = true
  AND status NOT IN ('CANCELLED', 'Voided')
  AND customer_type IN ('WHOLESALE', 'PARTNER')
```
**Use for:** Wholesale performance, partner tracking, B2B margin  
**Includes:** All B2B customers  
**Excludes:** Retail, staff, internal  

### Golden Rule: Discount Analysis MUST Use scope_retail

**Why:**
- Retail discount = promotion (5–30%)
- B2B discount = wholesale price (40–73%)
- System discount = gift/test (77–100%)
- If mixed: "Avg discount 35%" = meaningless

**Evidence from analysis (2026-04-13):**

| Segment | Avg Discount | Reason |
|---|---|---|
| Retail only | 15% | Real promotions |
| B2B only | 45% | Fixed wholesale pricing |
| Mixed (current mistake) | 28% | Masks reality |

---

## SECTION 8: STAFF/KOL SPECIAL HANDLING

From report_segmentation.md § 3.4:

| **customer_type** | **Layer 1 [All]** | **Layer 2 [Retail]** | **Layer 2 [B2B]** | **Notes** |
|---|---|---|---|---|
| RETAIL | ✅ Include | ✅ Include | ❌ Exclude | Normal customer |
| WHOLESALE | ✅ Include | ❌ Exclude | ✅ Include | Fixed B2B pricing |
| PARTNER | ✅ Include | ❌ Exclude | ✅ Include | Business partner |
| **STAFF** | ✅ Include | ❌ Exclude | ❌ Exclude | Staff discount ≠ market price |
| **KOL** | ✅ Include | ❌ Exclude | ❌ Exclude | KOL discount + content support |

**Implication for Staff:**
- When you create a STAFF order or KOL order, it will count in **Layer 1 (CEO dashboards)** but NOT in Layer 2 operational dashboards
- This is correct — staff orders are real revenue but not comparable to retail or B2B sales

---

## SECTION 9: THE 4 KEY PROBLEMS SOLVED

### Problem 1: "US channel inflates discount avg"

**Before:** US orders (100% discount, 0đ net) mix with domestic retail/B2B  
**Fix:**
- source = 'US' → channel_format = `'CrossBorder Fulfillment'` → channel_category = `'Internal'` → is_sales_channel = `false`
- All revenue dashboards filter `WHERE is_sales_channel = true` → US excluded automatically
- Decision log (2026-04-13): ✅ CONFIRMED

### Problem 2: "B2B discount looks like failed promotion"

**Before:** Đại Lý 46.8% discount treated as marketing failure  
**Fix:**
- Đại Lý orders have customer_type = `'WHOLESALE'` or channel = B2B
- Discount reports MUST filter `WHERE customer_type = 'RETAIL'`
- B2B discount is fixed pricing, not promotion — analyzed separately
- Decision log: ✅ CONFIRMED, separate B2B dashboards created

### Problem 3: "Telesale/CS look like internal operations"

**Before:** CS/Telesale team orders classified as System → not counted as revenue  
**Fix:**
- source = 'CS' or 'Telesale' → channel_format = `'Direct'` → channel_category = `'Offline'` → is_sales_channel = `true`
- Both teams are sales teams, not operations — revenue counts
- Decision log (2026-04-13): ✅ CONFIRMED
- Note: Currently only 124 orders (0.2% volume), but if they scale, upgrade to dual-tracking (e.g., "CS-Shopee" to know original channel)

### Problem 4: "Other channel is a dumping ground"

**Before:** "Other" mixes VIP customers, CTV, hidden wholesale, unknown sources  
**Fix:**
- Create customer_type dimension: tag known wholesale customers
- Create order_nature dimension: separate retail_sale, wholesale, cross_border, test, gift, affiliate
- If customer_type = WHOLESALE (tagged), order_nature = wholesale
- If source = System → order_nature = test/gift/staff_benefit
- Remaining "Other" orders → order_nature = retail_sale (unless retail, then loosen filter)
- Decision log (2026-05-26): ✅ 36 wholesale customers found & tagged (pending Sales confirmation)

---

## SECTION 10: DECISION LOG & RECOMMENDATIONS

### ✅ CONFIRMED (Ready to Implement)

| Decision | Date | Confirmation | Action | Status |
|---|---|---|---|---|
| US channel = cross-border fulfillment, is_sales_channel = false | 2026-04-13 | Business team | Change source format to `CrossBorder Fulfillment`, exclude from revenue | ✅ READY |
| Telesale & CS = sales revenue (Offline/Direct Sales) | 2026-04-13 | Business team | Change source format to `Direct`, change to is_sales_channel = true | ✅ READY |
| Discount reports MUST use scope_retail | 2026-04-13 | Data team | Add mandatory filter to all Metabase promotion dashboards | ✅ READY |

### 🔍 SCANNED (Awaiting Confirmation)

| Decision | Date | Status | What's Needed | Impact If Not Done |
|---|---|---|---|---|
| 36 wholesale customers need tagging | 2026-05-26 | Found & listed | Sales team reviews CSV, confirms customer_type | ~800M net revenue misclassified as retail |
| Add order_nature dimension | — | Proposed | Business + Data align on 7-value set | Can't separate retail_sale, wholesale, test in reporting |

### ❓ OPEN (Need Discussion)

| Question | Impact | Owner | Action |
|---|---|---|---|
| POPS, Leflair, Selly, Chiaki: archive or keep? | Small (inactive) | Business | Decide: mark as status=inactive, or remove from source list? |
| "Other" channel: any Sapo tags to identify VIP/CTV/wholesale? | Medium (2,568 orders) | Sales/Sapo admin | Check if customer notes/tags exist in Sapo to auto-classify |
| Hidden wholesale on B2C channels: Is 40% discount a rule threshold, or need manual confirmation? | Medium (ongoing) | Sales | Define: Flag discount ≥40% for review? Or require explicit WHOLESALE tag? |
| Staff/KOL: How to track original channel if team creates order? (e.g., "CS-Shopee") | Low (currently) | Sales ops | If CS/Telesale volume grows, implement dual-tracking naming |

---

## SECTION 11: EXACT CASE-WHEN MAPPING (FROM DIM_CHANNELS.SQL)

**Lines 115–125 — channel_format → channel_category:**

```sql
CASE channel_format
    WHEN 'Marketplace' THEN 'Online-Ecommerce'
    WHEN 'Social'      THEN 'Online-Ecommerce'
    WHEN 'Web'         THEN 'Online-Ecommerce'
    WHEN 'Retail'      THEN 'Offline'
    WHEN 'B2B'         THEN 'Offline'
    WHEN 'Direct'      THEN 'Offline'
    WHEN 'System'      THEN 'Internal'
    WHEN 'CrossBorder Fulfillment' THEN 'Internal'
    ELSE 'Internal'
END as channel_category
```

**Line 138 — is_sales_channel rule:**

```sql
channel_format NOT IN ('System', 'CrossBorder Fulfillment', 'Other') as is_sales_channel
```

**Unknown Member (Lines 150–164):**
```sql
SELECT
    {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }} as channel_key,
    'Unknown' as channel_name,
    'UNK' as channel_code,
    'Internal' as channel_category,
    'Other' as channel_format,
    'Other' as platform,
    cast(null as varchar) as channel_brand,
    'Domestic' as market,
    'channel' as source_type,
    false as is_sales_channel,  -- NOT counted as sales
    ...
```

---

## SECTION 12: QUICK REFERENCE FOR STAFF

### Cheat Sheet: "What source should I pick?"

```
IF customer buys from me on marketplace (Shopee/Lazada/Tiki)
    → System automatically maps to marketplace channel ✅

IF customer buys from social (Zalo/Facebook/Instagram)
    → Pick Zalo, Facebook, or Instagram ✅
    → If high-discount repeat buyer (40%+), tell Sales for WHOLESALE tag 🏷️

IF customer buys direct (phone/chat)
    → Pick CS (customer service) or Telesale ✅

IF customer is wholesale distributor
    → Pick Đại Lý or Chợ sỉ ✅
    → Tell Sales if buying through social (needs WHOLESALE tag) 🏷️

IF you're testing a product
    → Pick Test Sản Phẩm ✅
    → Won't count in revenue reports

IF you're giving a gift
    → Pick Quà Tặng ✅
    → Won't count in revenue reports

IF staff orders for personal use
    → Pick Ưu đãi Nhân Viên ✅
    → Won't count in operational revenue

IF you don't know
    → Do NOT pick "Other" — ask Data team instead ❌
```

---

## SECTION 13: UNRESOLVED QUESTIONS

1. **Inactive sources (POPS, Leflair, Selly, Chiaki):** Should these be marked `status = false` in ref_order_sources, or fully removed? Currently they have `status = false` but still joinable. *Owner: Business*

2. **Hidden wholesale threshold:** Is discount ≥40% a hard rule for flagging as "review-required", or does every ambiguous case need manual Sales sign-off? *Owner: Sales*

3. **"Other" channel disambiguation:** Do the customer notes/tags in Sapo exist (e.g., "CTV", "VIP", "Sỉ" in customer_notes field) that could auto-populate customer_type? *Owner: Sapo admin*

4. **Affiliate (CTV) revenue inclusion:** Should CTV orders (100% discount) count toward gross revenue or be excluded like gifts/staff? Currently treated as retail but heavily discounted. *Owner: Finance/Sales*

5. **Dual-tracking for CS/Telesale:** If CS/Telesale volume grows significantly, should we change source naming to "CS-Shopee" to preserve original channel? Current policy: not needed now (0.2% volume). *Owner: Sales ops*

6. **Retail-only KPIs:** Should "Promotion Analysis" dashboard hard-filter customer_type = 'RETAIL', or present both retail + B2B with clear labeling? Current: hard-filter per report_segmentation.md. *Owner: Metabase team*

---

## REFERENCES

- **Source of Truth:** `transformation/seeds/ref_order_sources.csv`
- **Channel Dimension:** `transformation/models/marts/core/dim_channels.sql`
- **Channel Grouping Analysis:** `docs/context/channel-grouping-analysis.md`
- **Report Segmentation Guide:** `docs/analytics-handbook/guides/report_segmentation.md`
- **Sales Domain:** `docs/analytics-handbook/domains/sales.md`
- **Wholesale Customer List:** `plans/reports/wholesale-customers-review-260526.csv`

---

**END OF EXTRACTION**
