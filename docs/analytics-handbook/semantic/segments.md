# Segments

Các named subset của data — pre-computed thành boolean columns trong mart, hoặc ad-hoc filters.

> **Canonical source:** file này
> **Tham chiếu WHY:** [Report Segmentation Guide](../guides/report_segmentation.md)
> **Implementation:** `transformation/models/marts/fact_orders.sql`

## Scope Hierarchy

```
all_orders
    └── scope_sales  (is_sales_channel=true)
            ├── scope_retail  (+ customer_type=RETAIL)
            ├── scope_b2b     (+ customer_type IN WHOLESALE, PARTNER)
            └── [STAFF, KOL]  — included in scope_sales but no named Layer 2 scope

is_active_order  (status NOT IN ('CANCELLED', 'DRAFT')) — cross-cutting, áp dụng độc lập với scope
    → kết hợp với scope_* khi tính revenue, không dùng khi đếm tổng đơn
```

> **CROSSBORDER** excluded at channel level (`is_sales_channel=false`), not at `customer_type` level — never appears in any scope.
> **KY_GUI (ký gửi) = PARTNER → scope_b2b** (confirmed 2026-06-05).

---

## Pre-computed Segments (boolean columns in fact_orders)

---

## scope_sales

> **Type:** Segment | **Domain:** [Sales](../domains/sales.md) | **Status:** `active`
> **Since:** 2026-04-19

**Definition:** Tất cả đơn hàng từ kênh bán hàng hợp lệ (pure channel classification, không phụ thuộc status).

**Rule:**
```sql
-- fact_orders.scope_sales (pre-computed boolean column)
is_sales_channel = true
```

**Intent:** Layer 1 Executive [All] — full picture tất cả đơn từ sales channel, không phân biệt loại khách hay status. Bao gồm Retail, B2B, STAFF, KOL, kể cả cancelled. Dùng cho CEO Weekly Pulse, mọi [All] dashboard. **Để tính revenue: `WHERE scope_sales AND is_active_order`.**

**Use in SQL:** `WHERE scope_sales` (đếm tất cả đơn) | `WHERE scope_sales AND is_active_order` (revenue metrics).

#### 🎯 When to Use
Use khi cần toàn bộ doanh thu không phân khúc. Nếu cần phân tích AOV, discount, hay retention → dùng [scope_retail](segments.md#scope_retail) hoặc [scope_b2b](segments.md#scope_b2b) thay thế.

#### ⚠️ Conflicts
| Source | Definition | When it appears | Note |
|---|---|---|---|
| Pre-refactor code | `scope_sales` embedded `status != 'CANCELLED'` | Code trước 2026-06-08 | scope_sales không còn loại cancelled; dùng `AND is_active_order` thay thế |

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| [scope_retail](segments.md#scope_retail) | segments.md | Subset: chỉ customer_type=RETAIL | Phân tích retail metrics (AOV, discount, promo) |
| [scope_b2b](segments.md#scope_b2b) | segments.md | Subset: chỉ WHOLESALE + PARTNER | Phân tích B2B metrics |

#### ❌ Anti-patterns
```sql
-- ❌ Re-deriving thủ công thay vì dùng pre-computed column
WHERE is_sales_channel = true

-- ❌ Dùng scope_sales cho revenue mà không có is_active_order — bao gồm cancelled
SELECT SUM(net_revenue) FROM fact_orders WHERE scope_sales

-- ❌ Mix scope_sales với discount/AOV analysis — kết quả vô nghĩa vì pha retail+B2B
SELECT AVG(revenue) FROM fact_orders WHERE scope_sales AND is_active_order  -- ~650K VND, meaningless blend
```

#### 📊 Data Quality
| Dimension | Status | Note |
|---|---|---|
| STAFF/KOL coverage | Partial | customer_type migration incomplete; old codes default to RETAIL — don't trust for historical |

#### 🏷️ Used In
- CEO Weekly Pulse
- Order Profitability
- Mọi [All] dashboard

---

## scope_retail

> **Type:** Segment | **Domain:** [Sales](../domains/sales.md) | **Status:** `active`
> **Scope:** [scope_sales](segments.md#scope_sales) | **Since:** 2026-04-19

**Definition:** Đơn hàng từ khách hàng retail qua kênh bán hàng hợp lệ.

**Rule:**
```sql
-- fact_orders.scope_retail (pre-computed boolean column)
scope_sales = true
AND customer_type = 'RETAIL'
```

**Intent:** Layer 2 Retail [Retail] — loại B2B, internal, CROSSBORDER. Chuẩn cho promotion analysis, discount rate, AOV retail. AOV ~450K VND. Kết hợp với `is_active_order` khi tính revenue: `WHERE scope_retail AND is_active_order`.

**Use in SQL:** `WHERE scope_retail` — không re-derive `customer_type = 'RETAIL' AND is_sales_channel = true`.

#### 🎯 When to Use
Bắt buộc cho mọi metric có ngữ cảnh retail: [discount_rate](metrics.md#discount_rate), [discount_amount](metrics.md#discount_amount), [aov](metrics.md#aov), [retention_rate](metrics.md#retention_rate). Không dùng scope_sales khi phân tích promotion — B2B discount = giá sỉ cố định, sẽ méo kết quả.

#### ⚠️ Conflicts
| Source | Definition | When it appears | Note |
|---|---|---|---|
| Naive filter | `customer_type='RETAIL'` only | Code không dùng pre-computed | Thiếu `is_sales_channel` filter |

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| [scope_sales](segments.md#scope_sales) | segments.md | Parent: bao gồm cả B2B + STAFF/KOL | Cần toàn bộ sales không phân khúc |
| [scope_b2b](segments.md#scope_b2b) | segments.md | Cùng parent, khác customer_type | Phân tích B2B |

#### ❌ Anti-patterns
```sql
-- ❌ Mix scope_retail và scope_b2b trong cùng AOV analysis
SELECT AVG(revenue) FROM fact_orders WHERE scope_retail OR scope_b2b
-- Retail AOV ~450K, B2B ~2.5M → blend cho ~650K, vô nghĩa về business

-- ❌ Dùng scope_retail cho discount analysis B2B
-- B2B discount là giá sỉ cố định 40-50%, không phải promotion
```

#### 🏷️ Used In
- [`daily-sales-retail`](../blueprints/daily-sales-retail.md) — Daily Sales [Retail]
- Promotion Analysis [Retail]
- Marketing Weekly Tracker
- Required by: [discount_rate](metrics.md#discount_rate), [discount_amount](metrics.md#discount_amount), [aov](metrics.md#aov), [retention_rate](metrics.md#retention_rate)

---

## scope_b2b

> **Type:** Segment | **Domain:** [Sales](../domains/sales.md) | **Status:** `active`
> **Scope:** [scope_sales](segments.md#scope_sales) | **Since:** 2026-04-19

**Definition:** Đơn hàng từ khách hàng B2B (wholesale + partner/ký gửi) qua kênh bán hàng hợp lệ.

**Rule:**
```sql
-- fact_orders.scope_b2b (pre-computed boolean column)
scope_sales = true
AND customer_type IN ('WHOLESALE', 'PARTNER')
```

**Intent:** Layer 2 B2B [B2B] — phân tích riêng B2B. KY_GUI (ký gửi) = PARTNER, thuộc scope này (confirmed 2026-06-05). AOV ~2.5M VND. Discount ở đây = giá sỉ cố định 40–50%, không phải promotion.

**Use in SQL:** `WHERE scope_b2b`.

#### 🎯 When to Use
Dùng cho B2B Daily Sales, B2B Orders Tracking, bất kỳ phân tích nào chỉ nhắm WHOLESALE + PARTNER. Không dùng khi phân tích promotion effectiveness — B2B không có promo mechanics.

#### ⚠️ Conflicts
| Source | Definition | When it appears | Note |
|---|---|---|---|
| CROSSBORDER confusion | `customer_type='CROSSBORDER'` | Code cũ tưởng đây là B2B CrossBorder | CROSSBORDER đã bị loại ở `is_sales_channel=false` — không vào scope nào |

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| [scope_sales](segments.md#scope_sales) | segments.md | Parent: bao gồm cả retail + STAFF/KOL | Cần toàn bộ sales |
| [scope_retail](segments.md#scope_retail) | segments.md | Cùng parent, customer_type=RETAIL | Phân tích retail, promo, discount |

#### ❌ Anti-patterns
```sql
-- ❌ Mix B2B discount với retail discount analysis
-- B2B discount = giá sỉ cố định, không phải promotion — bản chất khác hoàn toàn

-- ❌ Tưởng CROSSBORDER thuộc B2B và viết thêm filter
WHERE scope_b2b AND customer_type != 'CROSSBORDER'  -- redundant, CROSSBORDER không bao giờ vào scope_b2b
```

#### 🏷️ Used In
- B2B Daily Sales
- B2B Orders Tracking

---

## is_active_order

> **Type:** Segment | **Domain:** [Sales](../domains/sales.md) | **Status:** `active`
> **Since:** 2026-06-08

**Definition:** Đơn hàng đã confirmed và chưa bị huỷ — status gate cho revenue calculations.

**Rule:**
```sql
-- fact_orders.is_active_order (pre-computed boolean column)
status NOT IN ('CANCELLED', 'DRAFT')
```

**Intent:** Cross-cutting gate — dùng kết hợp với scope_* khi tính revenue/doanh thu. Không dùng khi đếm tổng số đơn (cancelled/draft vẫn cần đếm để tính tỷ lệ huỷ, conversion). DRAFT excluded vì chưa committed — không phải đơn thật về mặt business.

**Use in SQL:**
- Revenue metrics: `WHERE scope_retail AND is_active_order`
- Order counts (all, incl. cancelled+draft): `WHERE scope_retail`
- Cancelled count: `WHERE scope_retail AND status = 'CANCELLED'`

#### 🎯 When to Use
- `SUM(net_revenue)`, `SUM(gross_revenue)`, `SUM(total_collected)`, `AVG(...)` → bắt buộc thêm `AND is_active_order`
- `COUNT(*)`, `COUNT(DISTINCT order_id)` không kèm revenue → **KHÔNG** thêm (đếm tất cả đơn kể cả cancelled/draft)
- Card cancelled orders → `WHERE scope_retail AND status = 'CANCELLED'`

#### ❌ Anti-patterns
```sql
-- ❌ Embed status vào scope_* definition (scope_* không còn loại cancelled)
WHERE is_sales_channel = true AND status != 'CANCELLED'

-- ❌ Dùng raw status thay vì is_active_order
WHERE scope_retail AND status != 'CANCELLED'

-- ❌ Bỏ sót is_active_order khi tính revenue
SELECT SUM(net_revenue) FROM fact_orders WHERE scope_retail  -- bao gồm cancelled revenue
```

#### 🏷️ Used In
- Mọi revenue card (Net Revenue, Gross Revenue, Total Collected, AOV, Discount Amount)
- Available in: `fact_orders`, `fact_order_economics`

---

## Scope Matrix

| Scope | customer_type included | is_sales_channel | status |
|---|---|---|---|
| scope_sales | ANY (RETAIL, WHOLESALE, PARTNER, STAFF, KOL) | ✅ true | any — use `AND is_active_order` for revenue |
| scope_retail | RETAIL only | ✅ true (via scope_sales) | any — use `AND is_active_order` for revenue |
| scope_b2b | WHOLESALE, PARTNER | ✅ true (via scope_sales) | any — use `AND is_active_order` for revenue |
| is_active_order | — (cross-cutting gate) | — | NOT CANCELLED |
| *(no scope)* | CROSSBORDER | ❌ false | — |
| *(no named L2)* | STAFF, KOL | ✅ true (in scope_sales) | any |

---

## Ad-hoc Filters (phải viết WHERE thủ công — không phải column)

---

## filter_us

> **Type:** Segment | **Domain:** [Sales](../domains/sales.md) | **Status:** `active`
> **Since:** 2026-04-19

**Definition:** Đơn xuất khẩu US B2B (chuyển hàng nội bộ tập đoàn, 100% discount).

**Rule:**
```sql
-- Không có pre-computed column — phải viết WHERE thủ công
WHERE channel_name = 'US'
-- Lấy từ dim_channels.channel_name, join qua fact_orders.channel_id
```

**Intent:** Dashboard chuyên theo dõi đơn US xuất khẩu (US CrossBorder Daily [US]). Loại khỏi mọi revenue dashboard vì 100% discount làm méo chỉ số.

**Use in SQL:** `WHERE channel_name = 'US'` — join dim_channels nếu cần.

#### 🎯 When to Use
Chỉ dùng cho US CrossBorder dashboard. Trong mọi revenue/discount dashboard khác: exclude `channel_name = 'US'` hoặc đảm bảo scope đã loại (scope_retail/scope_b2b không chứa US nếu `is_sales_channel=false` cho channel đó).

#### ⚠️ Conflicts
| Source | Definition | When it appears | Note |
|---|---|---|---|
| `customer_type='CROSSBORDER'` | Phân loại khách theo type | Code cũ nhầm field | Đây là customer_type, không phải channel filter — dùng `channel_name='US'` |

#### 🔗 Similar (not synonym)
*None.*

#### ❌ Anti-patterns
```sql
-- ❌ Nhầm customer_type với channel filter
WHERE customer_type = 'CROSSBORDER'  -- sai field; dùng channel_name='US'
```

#### 🏷️ Used In
- US CrossBorder Daily [US]

---

## filter_internal

> **Type:** Segment | **Domain:** [Sales](../domains/sales.md) | **Status:** `active`
> **Since:** 2026-04-19

**Definition:** Đơn nội bộ: nhân viên ưu đãi, quà tặng, test, telesale.

**Rule:**
```sql
-- Không có pre-computed column — phải viết WHERE thủ công
WHERE channel_category = 'Internal'
```

**Intent:** Loại khỏi mọi revenue và discount analysis — giá nội bộ không đại diện cho business performance.

**Use in SQL:** `WHERE channel_category = 'Internal'` (thường dùng để EXCLUDE: `AND channel_category != 'Internal'`).

#### 🎯 When to Use
Dùng để exclude khi build revenue report mà muốn chắc chắn không có internal orders lọt vào — dù scope_sales đã loại phần lớn qua `is_sales_channel`.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
*None.*

#### ❌ Anti-patterns
```sql
-- ❌ Include internal orders trong revenue/discount analysis
-- Giá nội bộ méo hoàn toàn mọi chỉ số performance
```

#### 🏷️ Used In
*Not tracked yet.*

---

## filter_social

> **Type:** Segment | **Domain:** [Sales](../domains/sales.md) | **Status:** `active`
> **Since:** 2026-04-19

**Definition:** Đơn từ kênh social (Facebook, Zalo, Instagram).

**Rule:**
```sql
-- Không có pre-computed column — phải viết WHERE thủ công
WHERE channel_format = 'Social'
-- KHÔNG dùng thay cho customer_type filter khi phân tích segment
```

**Intent:** Channel-level analysis cho social channels. Social channels có cả retail lẫn B2B orders — filter này chỉ đủ cho channel performance, không thay thế segment filter.

**Use in SQL:** `WHERE channel_format = 'Social'`.

#### 🎯 When to Use
Chỉ dùng cho channel-level analysis (e.g., "Social channel revenue"). Nếu cần phân tích segment trong social → kết hợp thêm `scope_retail` hoặc `scope_b2b`.

#### ⚠️ Conflicts
| Source | Definition | When it appears | Note |
|---|---|---|---|
| `channel_format='Social'` dùng như segment | Filter channel thay vì customer segment | Code dùng nhầm cho segment analysis | Social bao gồm cả retail lẫn B2B — không phải segment |

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| [scope_retail](segments.md#scope_retail) | segments.md | Customer segment, không phải channel | Phân tích retail customers (kể cả qua social) |

#### ❌ Anti-patterns
```sql
-- ❌ Dùng channel_format='Social' thay cho customer segment filter
WHERE channel_format = 'Social'  -- sai nếu mục tiêu là "retail customers on social"
-- Đúng:
WHERE channel_format = 'Social' AND scope_retail
```

#### 🏷️ Used In
*Not tracked yet.*

---

## filter_has_cogs

> **Type:** Segment | **Domain:** [Sales](../domains/sales.md) | **Status:** `active`
> **Since:** 2026-04-19

**Definition:** Đơn có dữ liệu COGS (Sapo-MAC hoặc MISA) để tính P&L.

**Rule:**
```sql
-- Không có pre-computed boolean — dùng column has_cogs trong fact_order_economics
WHERE has_cogs = true
```

**Intent:** Bắt buộc khi phân tích gross_profit, channel_net_profit. Coverage ~65% đơn hoàn thành trong date range MISA.

**Use in SQL:** `WHERE has_cogs = true` — áp dụng trên `fact_order_economics`, không phải `fact_orders`.

#### 🎯 When to Use
Bắt buộc cho mọi P&L analysis. Không apply → denominator bao gồm đơn không có COGS → gross_profit/margin bị understated.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| [cogs_amount](metrics.md#cogs_amount) | metrics.md | Metric (giá trị), không phải filter | Tính toán COGS value |
| [gross_profit](metrics.md#gross_profit) | metrics.md | Derived metric cần has_cogs=true | Output cuối của P&L |
| [channel_net_profit](metrics.md#channel_net_profit) | metrics.md | Net profit sau overhead | Output cuối channel P&L |

#### ❌ Anti-patterns
```sql
-- ❌ Tính gross_profit mà không filter has_cogs
SELECT SUM(revenue - cogs_amount) FROM fact_order_economics
-- Các đơn null COGS cho cogs_amount=0 → gross_profit bị overstated

-- Đúng:
SELECT SUM(revenue - cogs_amount) FROM fact_order_economics WHERE has_cogs = true
```

#### 📊 Data Quality
| Dimension | Status | Note |
|---|---|---|
| Coverage | Partial (~65%) | Chỉ đơn trong date range MISA có COGS; pre-MISA = no data |
| Source | Mixed | Sapo-MAC hoặc MISA; `cogs_source` column ghi rõ nguồn |

#### 🏷️ Used In
- Order Profitability (P&L section)
- Channel Net Profit analysis
