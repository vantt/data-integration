# Sapo Orders & Customers: Creation Workflows & Data Classification
## Staff-Facing Guide

> **For:** Staff creating orders/customers in Sapo; Data Team validating field requirements
> **Date:** 2026-06-05
> **Based on:** sapo-platform.md, data-model-overview.md, sales-segmentation-guide.md, discount-classification.md

---

## Executive Summary

Orders and customers enter Sapo via **two pathways:**
1. **Manual creation** (staff creates via UI) — staff controls source, customer, location, discount
2. **Auto-sync from marketplaces** (Shopee/Lazada/Tiki via webhook/API) — system auto-populates most fields

**Classification at order-creation time** depends on **which fields staff can control**. This guide maps creation workflows → data classification implications.

---

## SECTION 1: How Orders Enter Sapo

### 1.1 Pathway 1: Manual Creation (Staff)

**When:** Offline orders, Telesale, Direct Sales, Internal orders (Test, Gift, Staff Discount)

**How:** Staff fills UI form with:
- Order date / created_on
- Customer (existing or new; if new, auto-creates customer record)
- Order items (product, quantity, price)
- **Source / Nguồn** (controls channel classification)
- **Branch / Location** (fulfillment point)
- **Discount** (optional; staff-controlled)
- Order notes

**Example scenarios:**
- POS cashier: Rings up sale → Source = "POS - Trương Dinh" (specific store)
- Telesale: Customer calls → creates order → Source = "Telesale" (Direct Sales)
- Internal: Manager creates test order → Source = "Test Sản Phẩm" (Internal)
- Wholesale: B2B customer → Source = "Đại Lý" (Wholesale), Customer Group = Wholesale

**Webhook support:** Yes, order creation triggers webhook
**Historical data:** Sapo stores full creation details

### 1.2 Pathway 2: Auto-Sync from Marketplaces

**When:** Shopee, Lazada, Tiki, Facebook orders arrive via API webhook

**How:** System auto-populates from marketplace payload:
- Order date (marketplace timestamp)
- Customer (from marketplace buyer info; may create new customer)
- Order items (from marketplace cart)
- **Source / Nguồn** (auto-set by integration; e.g., "Shopee - JPC OFFICIAL")
- **Location** (auto-routed by warehouse/fulfillment logic)
- **Discount** (from marketplace promotion data)
- Buyer notes

**Webhook support:** Yes, real-time for Orders & Customers ✅
**Data completeness caveat:** Marketplace payloads may omit fields (e.g., Shopee doesn't provide vendor info per line item)

**Sync timing:** Real-time via webhook (primary) + History Log API polling (backup for missed events)

---

## SECTION 2: Source/Nguồn Classification

### 2.1 What is "Source" (Sapo `order_source` or `source_id`)?

**Definition:** The immediate sales channel or purpose where the order originated.

**Field in Sapo:** `order_source` (ID) and `source_name` (display name)

**Problem:** Sapo source field **conflates 5 different concepts:**

| Concept | Answers | Example sources | Data classification |
|---------|---------|-----------------|-----|
| **Channel** | "Mua ở ĐÂU?" (Where sold?) | Shopee, Zalo, POS, Web, Telesale | → `channel_format`, `platform` |
| **Customer Type** | "AI mua?" (What type of buyer?) | Đại Lý (Wholesale), Chợ sỉ | → `dim_customers.customer_type` |
| **Team/Function** | "AI XỬ LÝ?" (Which team?) | CS, Telesale | → `dim_teams.revenue_type` |
| **Order Purpose** | "MỤC ĐÍCH gì?" (Why created?) | Test SP, Quà Tặng, Ưu đãi NV | → `is_sales_channel` = false |
| **Business Arrangement** | "HỢP ĐỒNG loại nào?" | US (FG Care USA fulfill in VN) | → `arrangement` |

### 2.2 Source Type Classification

To clarify which concept each source belongs to, data model uses `source_type` field:

| source_type | Meaning | Examples | Staff impact |
|---|---|---|---|
| `channel` | Real sales channel (WHERE) | Shopee, Lazada, POS, Facebook, Telesale, Web | **Include in revenue reports** |
| `customer_type` | Customer segment (WHO) | Đại Lý (Wholesale), Chợ sỉ | **Not a channel; combine with channel for B2C vs B2B** |
| `team` | Team/function handling order | CS, Telesale | **Use for team attribution if `revenue_type = member`** |
| `purpose` | Internal purpose only (WHY) | Test SP, Quà Tặng, Ưu đãi NV | **Exclude from revenue (is_sales_channel=false)** |
| `arrangement` | Special business arrangement | US (CrossBorder Fulfillment) | **Internal fulfillment, exclude from VN revenue** |

### 2.3 How Staff Controls Source at Order Creation

**For manually created orders:**

Staff selects source from dropdown when creating order.

| Order type | Source choice | system auto-set? | Staff can override? |
|---|---|---|---|
| **POS** | Specific store (e.g., "POS - Trương Dinh") | Yes, by location terminal | No (locked to store) |
| **Telesale/Direct** | "Telesale" | No; staff selects | Yes |
| **B2B wholesale** | "Đại Lý" or "Chợ sỉ" | No; staff selects | Yes |
| **Internal/Test** | "Test Sản Phẩm", "Quà Tặng", "Ưu đãi NV" | No; staff selects | Yes |
| **Manual online** | "Web", "Facebook", "Zalo" (if manual creation) | No; staff selects | Yes |

**For auto-synced marketplace orders:**

Integration auto-sets source (staff cannot override during sync).

| Source | Auto-set by | Staff can edit post-sync? |
|---|---|---|
| Shopee, Lazada, Tiki, etc. | Integration mapping (webhook) | Yes, but **not recommended** (breaks audit trail) |
| Facebook, Zalo, Telesale | Webhook or polling | Yes, but breaks history |

**⚠️ Key caveat:** If staff manually changes source post-creation, history log captures the change, but data team cannot retroactively know original source intent.

---

## SECTION 3: Classification Dimensions Staff Influence

Staff directly influence at **order-creation time:**

| Dimension | Field | Staff control? | How it affects reporting | 
|-----------|-------|---|---|
| **Channel Category** | `channel_category` (Tier 1) | Derived from source ✓ indirect | Online-Ecommerce vs Offline vs Internal |
| **Channel Format** | `channel_format` (Tier 2) | Derived from source ✓ indirect | Marketplace vs Social vs Web vs Retail vs B2B vs Direct |
| **Platform** | `platform` (Tier 3) | Derived from source ✓ indirect | Shopee vs Lazada vs POS vs Telesale etc. |
| **Channel Name** | `channel_name` (Tier 4) | ✓ Direct via source selection | Shopee - JPC OFFICIAL vs Shopee - Fine Japan etc. |
| **Source Type** | `source_type` | Derived (lookup) | Whether channel is real or purpose/arrangement |
| **Customer** | `customer_id` | ✓ Direct (select/create) | Enables customer_type join (B2C vs B2B) |
| **Location** | `location_id` (branch) | ✓ Direct | Which facility fulfills order |
| **is_sales_channel** | Derived from source | Automatic | Whether included in revenue (false for Internal/CrossBorder) |
| **Discount** | `discount_items[]` | ✓ Direct (staff enters amounts/reasons) | Discount classification (see Section 5) |

**Summary for staff:**
- **You control:** source (→ channel), customer, location, discount
- **System derives:** channel_category, channel_format, platform, source_type
- **You enable:** customer_type join (wholesale vs retail signals)

---

## SECTION 4: Common Misunderstandings

From sales-segmentation-guide.md §4 — verbatim:

| Misunderstanding | ❌ Wrong | ✅ Right |
|---|---|---|
| **Ecommerce = only Marketplaces** | "Ecommerce = Shopee/Lazada only" | Ecommerce = ANY online channel (Marketplace + Social + Website) |
| **channel_category ≠ channel_format** | Using "Marketplace" when reporting tier-1 data | Tier 1 = `channel_category` (Online-Ecommerce/Offline/Internal). Tier 2 = `channel_format` (Marketplace/Social/Web/...). Don't mix. |
| **channel_brand ≠ product_brand** | "JPC is a product brand" | JPC is a channel brand only. Products on JPC come from Fine Japan, FG Care, etc. (product brands). |
| **Branch ≠ Channel** | "POS at Trương Dinh = different sales channel" | Branch is operational (who fulfills). Channel is sales (where). One Shopee order can be fulfilled from multiple branches. |
| **is_sales_channel=false ≠ zero revenue** | "Internal = no sales" | Internal is non-sales. Direct Sales/Telesale (is_sales_channel=**true**) are real channels. |
| **Social ≠ B2C only** | "Zalo/Facebook = retail only" | Social is dual-purpose: has both retail AND wholesale (hidden). Need `customer_type` to distinguish. |
| **Social discount ≠ always promotion** | "50% off on Zalo = marketing promo" | Could be wholesale pricing (customer_type=WHOLESALE) or promotion. Check customer group. |

---

## SECTION 5: Discount Classification

### 5.1 What Staff Enters

When creating order with discount, staff provides:
- **Amount** (discount value in VND)
- **Reason** (optional; free text — "khuyến mãi", "đại lý", "tặng", etc.)

Sapo does NOT require staff to classify discount type; it's inferred by data team.

### 5.2 Discount Type Taxonomy

Data team classifies discounts into types to distinguish **promotional** vs **wholesale pricing** vs **internal/sampling**:

| discount_type | Logic | Staff signals | Revenue impact |
|---|---|---|---|
| `voucher_promotional` | Marketplace voucher | Automatic from marketplace | Recognized as promo; doesn't contaminate retail metrics |
| `bundle` | Bundle/combo deal | reason = "Bundle Deal" | Pricing strategy; separate metric |
| `sampling_gift` | Free sample or gift order | reason contains "mẫu", "tặng" | Zero/near-zero revenue; excluded from analytics |
| `wholesale_explicit` | Labeled wholesale/B2B | reason contains "đại lý", "hợp đồng" | Classified as wholesale (even if auto-synced as "Retail") |
| `overseas` | Export/US customer | reason contains "Mỹ", "US" | Export logic; separate pricing model |
| `campaign` | Marketing campaign | reason contains "CTKM", "Father Day", etc. | Campaign attribution |
| `employee_internal` | Staff/CTV discount | reason contains "nhân viên", "CTV" | Internal cost; not revenue |
| `negotiated_micro` | Small goodwill discount (empty reason, <20%) | Staff doesn't fill reason; low rate | Retail customer negotiation |
| `negotiated_standard` | Moderate retail discount (empty reason, 20-40%) | Staff doesn't fill reason; moderate rate | Normal retail variance |
| `negotiated_deep` | Large discount (empty reason, ≥40%) | Staff doesn't fill reason; high rate | **Hidden wholesale signal** — customer may be B2B pretending to be retail |

### 5.3 Best Practices for Discount Entry

**If wholesale/B2B:** Use source "Đại Lý" or "Chợ sỉ" **OR** add reason "đại lý" in discount (redundant but safer)

**If promotional:** Sapo auto-fills from marketplace (Shopee vouchers)

**If sampling/gift:** Mark reason as "tặng" or "mẫu" so it excludes from revenue

**If staff negotiation:** Reason field is optional; system will classify by discount rate % if empty

---

## SECTION 6: Customer Creation & Customer Type

### 6.1 When Customer Record is Created

| Pathway | Who creates | When | Data captured |
|---|---|---|---|
| **Manual order creation** | Staff | When staff selects "New Customer" in order form | Staff enters: name, phone, email, address; system auto-sets created_on |
| **Marketplace auto-sync** | Webhook | Marketplace order webhook arrives | Buyer name, email (from marketplace); address extracted from shipping |
| **Manual customer entry** | Staff (admin) | Dedicated "Add Customer" form | Full profile: name, phone, email, address, group |

### 6.2 What Staff Can Classify

At customer creation, staff controls:
- **Customer Group** (manual entry) — e.g., "WHOLESALE", "RETAIL", "PARTNER", "STAFF", "KOL"
- **Addresses** — billing, shipping, default

**Data team derives:**
- `customer_type` (from customer group seed) — determines B2C vs B2B
- `value_group` (RFM, auto-calculated) — VALUE_VIP, VALUE_GOLD, etc.
- `lifecycle_stage` (auto-calculated) — NEW, ACTIVE, AT_RISK, CHURNED
- Other 8 dimensions (see data-model-overview.md §7)

### 6.3 Customer Type vs Value Group

**Don't confuse:**

```
customer_type = Relationship (RETAIL, WHOLESALE, PARTNER, STAFF, KOL)
     ↓
"Is this person a wholesale buyer or retail customer?"

value_group = Contribution (VALUE_VIP, VALUE_GOLD, VALUE_SILVER, VALUE_BRONZE)
     ↓
"How much does this customer spend? (RFM ranking)"
```

**Example:** High-volume retail customer = `customer_type=RETAIL + value_group=VALUE_VIP`

---

## SECTION 7: Real-World Scenarios

### Scenario A: Staff creates POS order at Trương Dinh store

**Staff actions:**
1. Select Source = "POS - Trương Dinh" (locked by terminal)
2. Select Customer or create new
3. Add products & qty
4. (Optional) Apply discount if customer negotiates
5. Save order

**What gets classified:**
- `channel_format` = Retail
- `channel_category` = Offline
- `platform` = POS
- `channel_name` = "POS - Trương Dinh"
- `location_id` = Trương Dinh
- `source_type` = "channel"
- `is_sales_channel` = true → **included in revenue reports**

---

### Scenario B: Telesale creates wholesale order (Đại Lý)

**Staff actions:**
1. Select Source = "Telesale" (or "Đại Lý" if Telesale wholesaler)
2. Select Customer = "Existing B2B customer" (customer_type=WHOLESALE)
3. Add products & qty
4. Apply discount 30% (wholesaler negotiation)
5. Add reason = "đại lý" (or leave empty — system will classify by rate)

**What gets classified:**
- `channel_format` = Direct (if "Telesale") or B2B (if "Đại Lý")
- `channel_category` = Offline
- `platform` = Telesale or Wholesale
- `source_type` = "team" (Telesale) or "customer_type" (Đại Lý)
- `is_sales_channel` = true → **included in revenue**
- `discount_type` = "negotiated_standard" or "wholesale_explicit" (if reason filled)
- **Retail metrics won't be contaminated** because discount classified as wholesale

---

### Scenario C: Marketplace webhook (Shopee order auto-syncs)

**Auto-sync actions (staff does nothing):**
1. Webhook arrives with Shopee order
2. Integration extracts buyer info → auto-creates customer if new
3. System auto-sets Source = "Shopee - JPC OFFICIAL" (mapped in integration config)
4. Items, prices, marketplace discount auto-populated
5. System routes to location (warehouse logic)

**What gets classified:**
- `channel_format` = Marketplace
- `channel_category` = Online-Ecommerce
- `platform` = Shopee
- `channel_name` = "Shopee - JPC OFFICIAL"
- `source_type` = "channel"
- `is_sales_channel` = true
- `discount_type` = "voucher_promotional" (Shopee voucher auto-detected)

**Staff can edit post-sync:** Yes, but not recommended (breaks audit trail). If B2B customer buys on Shopee, change customer_type to WHOLESALE so `dim_customers` join shows correct classification.

---

### Scenario D: Internal test order (QA testing)

**Staff actions:**
1. Select Source = "Test Sản Phẩm"
2. Select (or create) test customer
3. Add products
4. Save order

**What gets classified:**
- `channel_format` = System
- `channel_category` = Internal
- `source_type` = "purpose"
- `is_sales_channel` = false → **EXCLUDED from revenue reports**
- Order will never appear in sales dashboard

---

## SECTION 8: API & Webhook Limitations

### 8.1 What Webhooks Cover

✅ **Real-time event for:**
- Order creation/update
- Customer creation/update

❌ **NOT covered by webhook:**
- Shipments
- Payments
- Products
- Returns
- Inventory
- Locations
- Accounts
- Promotions
- Price lists

→ **For staff:** Only Order & Customer changes sync in real-time. Shipment, payment changes require manual Sapo refresh or daily batch sync.

### 8.2 API Filtering Limitations

**Limitation:** Sapo API does NOT support filtering by created_on date.

→ **For staff:** Daily incremental sync must use webhook + history log polling. Data team cannot "pull just today's orders" via JSON API. Full paginated load is required.

### 8.3 Webhook Completeness Caveat

**Marketplace payloads may omit:**
- Vendor per line item (Shopee) → data team matches product later
- Tax breakdown per line (Sapo calculates VAT on total)
- Historical variant info (SKU changes lost)

→ **For staff:** Don't expect 100% line-item detail for Shopee orders. Sapo standardizes upstream.

---

## SECTION 9: Practical Guidance for Staff

### Do's & Don'ts

| Action | Guidance |
|---|---|
| **✅ DO** | Select correct source when creating manual orders (POS staff: locked; Telesale: pick "Telesale"; B2B: pick "Đại Lý") |
| **✅ DO** | Fill discount reason if you know it (e.g., "đại lý", "tặng", "KM flash sale") → helps data team classify |
| **✅ DO** | Create customer record with correct customer group (WHOLESALE vs RETAIL) → enables correct analytics |
| **✅ DO** | Use marketplace integrations as-is; don't manually reassign orders (audit trail breaks) |
| **❌ DON'T** | Leave discount reason blank AND apply >40% discount (might flag as hidden wholesale) |
| **❌ DON'T** | Mix source types (e.g., "Shopee - Đại Lý" — pick either Shopee channel OR Đại Lý customer type; source field overloads; use customer_group instead) |
| **❌ DON'T** | Manually edit marketplace order source after sync (real-time sync flow breaks) |
| **❌ DON'T** | Assume "Social channel order" is always B2C (could be wholesale; check customer_type) |

### Quick Decision Tree: "Which source should I use?"

```
Order being created manually?
├─ NO → Marketplace webhook auto-syncs → NO ACTION NEEDED
└─ YES → What type of order?
    ├─ POS sale at store → Source = "POS - [store name]" (system auto-selects)
    ├─ Telesale call → Source = "Telesale"
    ├─ B2B wholesale → Source = "Đại Lý" or "Chợ sỉ" (also set customer_type=WHOLESALE)
    ├─ Social channel (manual) → Source = "Zalo" / "Facebook" (also check customer_type for B2C vs B2B)
    ├─ Website order → Source = "Web"
    ├─ Test/QA → Source = "Test Sản Phẩm"
    ├─ Gift/Free → Source = "Quà Tặng"
    └─ Staff discount → Source = "Ưu đãi NV"
```

---

## SECTION 10: Data Quality Checklist for Staff

When order creation workflow is followed correctly:

- [ ] **Source assigned:** Every order has source (POS, Shopee, Telesale, etc.)
- [ ] **Customer linked:** Order references customer record (enables demographic joins)
- [ ] **Location set:** Branch/location captures fulfillment point
- [ ] **Discount reasoned (optional but helpful):** If discount >20%, reason helps data team classify as promo vs wholesale
- [ ] **VAT correctly scoped:** Sapo total already VAT-inclusive; don't double-tax in reports
- [ ] **No manual edits to marketplace orders post-sync:** Keeps audit trail intact

---

## SECTION 11: Data Classification Snapshot

**TL;DR:** This is what staff inputs → this is what data systems see:

| Staff input | System classification | Report grouping |
|---|---|---|
| Source = "Shopee - JPC OFFICIAL" | channel, Marketplace, Shopee, Online-Ecommerce, is_sales_channel=true | Revenue by channel/platform |
| Source = "Telesale" + Customer Type=WHOLESALE | team, Direct, Telesale, Offline, is_sales_channel=true | Revenue by team; hidden wholesale detected |
| Source = "Test Sản Phẩm" | purpose, System, Internal, is_sales_channel=**false** | Excluded from revenue |
| Source = "Đại Lý" + Discount 35% | customer_type, B2B, Offline, is_sales_channel=true, discount_type=wholesale_explicit | B2B revenue (separate metric) |
| Source = "Quà Tặng" | purpose, System, Internal, is_sales_channel=**false** | Zero revenue; inventory impact only |

---

## Unresolved Questions

1. **Discount rate = NULL case?** Voucher promotional rate = 0 by Sapo design. Are there cases where rate is NULL vs 0? Classification logic assumes 0; if NULL exists, needs review.

2. **Source field overloading resolved?** Current docs show 5 concepts in 1 field. `source_type` field added to seed to disambiguate. Has this been implemented in production? Or still in planning?

3. **Customer creation on marketplace sync:** When Shopee webhook creates new customer, does system auto-detect customer_type (B2C) or leave NULL? If NULL, can data team infer from order pattern (single-unit = B2C, bulk = B2B)?

4. **Discount editing post-sync:** If staff changes discount reason on marketplace order after sync, does data team re-run classification? Or treat as "manual override, use new reason"? Audit trail implication unclear.

5. **Overseas (US) orders current status:** Docs mention US shifted from ecommerce to "CrossBorder Fulfillment" (internal arrangement). Is this live? How are US orders currently sourced in Sapo?

6. **POS location mapping:** POS source is generic ("Pos"). Does system expand to "POS - Trương Dinh" per location, or does staff manually edit? If generic, how is fulfillment location determined?

7. **Customer group autocomplete:** Sapo dropdown for customer_type — is this controlled by ref_customer_groups seed? Or free text? If free text, how are typos (e.g., "WHOLESALE" vs "Wholesale") normalized?

---

## Related Documents

- [sapo-platform.md](../context/sapo-platform.md) — API limitations, webhook coverage
- [data-model-overview.md](../context/data-model-overview.md) — Entity relationships, source_type taxonomy
- [sales-segmentation-guide.md](../context/sales-segmentation-guide.md) — 4-tier channel taxonomy, common misunderstandings
- [discount-classification.md](../architecture/order-pl/discount-classification.md) — Discount type logic, rate-based classification
- [team-management.md](./team-management.md) — Team attribution logic (referenced but not provided)
- [customer-segmentation.md](./customer-segmentation.md) — 8 customer dimensions (referenced but not provided)
