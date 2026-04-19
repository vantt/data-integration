# Hướng dẫn Phân lớp Báo cáo (Report Segmentation Guide)

> **Dành cho:** Tất cả người dùng tạo/xem báo cáo
> **Cập nhật:** 2026-04-19
> **Bảo trì:** Data Team
> **Tham chiếu:** [Sales Segmentation Guide](../../context/sales-segmentation-guide.md), [Customer Segmentation](../../context/customer-segmentation.md)

## Tài liệu này trả lời những câu hỏi nào?

1. Tại sao cần phân lớp báo cáo theo segment?
2. Ba tầng báo cáo (Executive/Operational/Analytics) khác nhau thế nào?
3. Khi nào dùng scope nào?
4. Làm sao để tránh trộn lẫn data Retail và B2B?

---

## TL;DR

- **3 tầng báo cáo:** Executive (All) → Operational (By Business Line) → Analytics (Cross-Segment)
- **3 scope cơ bản:** `scope_sales`, `scope_retail`, `scope_b2b`
- **Quy tắc vàng:** Không bao giờ phân tích promotion/discount trên data chưa filter `customer_type = 'RETAIL'`
- **Naming convention:** Dashboard có suffix `[All]`, `[Retail]`, `[B2B]`, hoặc `[Cross]`

---

## 1. Vấn đề: Trộn lẫn Bản chất Dữ liệu

### Tại sao trộn lẫn data gây sai lệch?

```
fact_orders (ALL)
    │
    ├── RETAIL orders (80%)
    │   └── Discount = promotion (khuyến mãi)
    │
    ├── WHOLESALE orders (15%)
    │   └── Discount = giá sỉ cố định (40-50%)
    │
    └── INTERNAL orders (5%)
        └── Không phải doanh thu (Test SP, Quà tặng)

→ Khi gộp chung: "Discount Rate 35%" = vô nghĩa
→ AOV trộn lẫn retail 450K với wholesale 2.5M = không actionable
```

### Ví dụ sai lệch thực tế

| Metric | Khi trộn lẫn | Retail thực | B2B thực |
|--------|--------------|-------------|----------|
| Discount Rate | 35% | 15% | 45% (giá sỉ) |
| AOV | 650K | 450K | 2.5M |
| Returning Rate | 40% | 35% | 80% |
| Promotion ROI | Sai | Đúng | N/A (không có promotion) |

---

## 2. Kiến trúc 3 Tầng Báo cáo

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: EXECUTIVE                                             │
│  ━━━━━━━━━━━━━━━━━━                                             │
│  Scope: is_sales_channel = true (loại Internal)                 │
│  View: Tổng quan toàn doanh nghiệp                              │
│  Audience: CEO, Founders, Directors                             │
│  Indicator: [All]                                               │
│                                                                 │
│  Examples: CEO Weekly Pulse [All], Order Profitability [All]    │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2: OPERATIONAL                                           │
│  ━━━━━━━━━━━━━━━━━━━                                            │
│  Split theo BUSINESS LINE → Data thuần nhất                     │
│                                                                 │
│  ┌─────────────────────┐  ┌─────────────────────┐               │
│  │  RETAIL OPS         │  │  B2B OPS            │               │
│  │  ─────────────      │  │  ────────           │               │
│  │  Scope: scope_retail│  │  Scope: scope_b2b   │               │
│  │  Indicator: [Retail]│  │  Indicator: [B2B]   │               │
│  │                     │  │                     │               │
│  │  • Daily Sales      │  │  • B2B Daily        │               │
│  │  • Promotion        │  │  • Partner Perf     │               │
│  │  • Customer Ops     │  │  • Credit Tracking  │               │
│  │  • Marketing        │  │  • B2B Margin       │               │
│  └─────────────────────┘  └─────────────────────┘               │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3: ANALYTICS                                             │
│  ━━━━━━━━━━━━━━━━━━━                                            │
│  Scope: Explicit cross-segment với labeling rõ ràng             │
│  View: So sánh, nghiên cứu, deep-dive                           │
│  Indicator: [Cross]                                             │
│                                                                 │
│  Examples: Channel Profitability [Cross], Acquisition [Cross]   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Định nghĩa Scope Cơ bản

### 3.1 scope_sales (Layer 1 - Executive)

**Mục đích:** Tổng quan toàn bộ doanh thu bán hàng thực.

```sql
-- Base filter cho tất cả Layer 1 dashboards
WHERE is_sales_channel = true
  AND status NOT IN ('CANCELLED', 'Voided')
```

**Bao gồm:**
- Retail (customer_type = 'RETAIL')
- Wholesale (customer_type = 'WHOLESALE')
- Partner (customer_type = 'PARTNER')

**Loại trừ:**
- Internal (Test SP, Quà Tặng, Ưu đãi NV)
- CrossBorder Fulfillment (US fulfill)
- STAFF orders (optional — xem quy tắc bên dưới)
- KOL orders (optional — xem quy tắc bên dưới)

### 3.2 scope_retail (Layer 2 - Retail Operations)

**Mục đích:** Phân tích thuần túy cho business line bán lẻ.

```sql
-- Base filter cho tất cả Layer 2 Retail dashboards
WHERE is_sales_channel = true
  AND status NOT IN ('CANCELLED', 'Voided')
  AND customer_type = 'RETAIL'
```

**Bắt buộc dùng khi:**
- Phân tích promotion/discount
- Marketing ROI
- Customer acquisition/retention
- AOV trends
- Product performance (retail)

### 3.3 scope_b2b (Layer 2 - B2B Operations)

**Mục đích:** Phân tích cho business line bán sỉ/đối tác.

```sql
-- Base filter cho tất cả Layer 2 B2B dashboards
WHERE is_sales_channel = true
  AND status NOT IN ('CANCELLED', 'Voided')
  AND customer_type IN ('WHOLESALE', 'PARTNER')
```

**Bắt buộc dùng khi:**
- Theo dõi đơn sỉ
- Partner performance
- Credit/AR tracking
- B2B margin analysis

### 3.4 Xử lý STAFF và KOL

| customer_type | Layer 1 (All) | Layer 2 (Retail) | Layer 2 (B2B) |
|---------------|---------------|------------------|---------------|
| RETAIL | ✅ Bao gồm | ✅ Bao gồm | ❌ Loại |
| WHOLESALE | ✅ Bao gồm | ❌ Loại | ✅ Bao gồm |
| PARTNER | ✅ Bao gồm | ❌ Loại | ✅ Bao gồm |
| **STAFF** | ✅ Bao gồm | ❌ Loại | ❌ Loại |
| **KOL** | ✅ Bao gồm | ❌ Loại | ❌ Loại |

**Lý do loại STAFF/KOL khỏi Layer 2:**
- STAFF: Giá ưu đãi nhân viên ≠ giá retail ≠ giá sỉ
- KOL: Giá ưu đãi KOL + hỗ trợ content → không comparable

**Nếu cần phân tích STAFF/KOL:** Tạo dashboard riêng với scope explicit.

---

## 4. Quy tắc Sử dụng Scope

### 4.1 Decision Tree

```
Tôi đang tạo dashboard cho...
    │
    ├── CEO/Founders/Directors nhìn tổng quan?
    │       → Layer 1: scope_sales [All]
    │
    ├── Ops/Sales team theo dõi hoạt động retail?
    │       → Layer 2: scope_retail [Retail]
    │
    ├── B2B team theo dõi khách sỉ/đối tác?
    │       → Layer 2: scope_b2b [B2B]
    │
    ├── Marketing team phân tích campaign/customer?
    │       → Layer 2: scope_retail [Retail]
    │
    └── Phân tích so sánh cross-segment?
            → Layer 3: scope_sales + explicit breakdown [Cross]
```

### 4.2 Quy tắc Vàng

| Loại phân tích | Scope bắt buộc | Lý do |
|----------------|----------------|-------|
| **Promotion/Discount** | scope_retail | Discount B2B = giá sỉ, không phải KM |
| **Marketing ROI** | scope_retail | Marketing target retail customers |
| **Customer Retention** | scope_retail | B2B retention khác logic |
| **AOV Analysis** | scope_retail HOẶC scope_b2b | Không mix 2 mức giá |
| **Revenue Overview** | scope_sales | Cần full picture |
| **Profitability** | scope_sales | COGS không phân biệt segment |

### 4.3 Dual-purpose Channels

**Vấn đề:** Social (Zalo, Facebook) và Direct (Telesale, CS) có cả retail lẫn B2B.

```
Kênh Zalo
    ├── Khách lẻ nhắn mua 1 hộp     → RETAIL
    └── Khách sỉ nhắn mua 50 hộp    → WHOLESALE
```

**Giải pháp:** KHÔNG filter theo channel, LUÔN filter theo `customer_type`.

```sql
-- ❌ SAI: Nghĩ Social = retail
WHERE channel_format = 'Social'

-- ✅ ĐÚNG: Filter theo customer_type
WHERE customer_type = 'RETAIL'
```

---

## 5. Naming Convention

### 5.1 Dashboard Name Format

```
{Purpose} [{Segment Indicator}]
```

### 5.2 Segment Indicators

| Indicator | Layer | Scope | Meaning |
|-----------|-------|-------|---------|
| `[All]` | L1-Executive | scope_sales | Tất cả business lines |
| `[Retail]` | L2-Retail | scope_retail | Chỉ retail (customer_type = 'RETAIL') |
| `[B2B]` | L2-B2B | scope_b2b | Chỉ B2B (WHOLESALE, PARTNER) |
| `[Cross]` | L3-Analytics | scope_sales + breakdown | So sánh cross-segment |

### 5.3 Examples

| Dashboard | Indicator | Layer |
|-----------|-----------|-------|
| CEO Weekly Pulse [All] | [All] | L1 |
| Daily Sales [Retail] | [Retail] | L2 |
| B2B Orders Tracking [B2B] | [B2B] | L2 |
| Channel Profitability [Cross] | [Cross] | L3 |
| Promotion Analysis [Retail] | [Retail] | L2 |
| Customer Operational [Retail] | [Retail] | L2 |

---

## 6. Collection Structure

```
📁 Executive                          [Layer 1]
├── CEO Weekly Pulse [All]
├── CEO Monthly Scorecard [All]
├── Order Profitability [All]
├── Finance P&L [All]
└── Logistics Operations [All]

📁 Operations                         [Layer 2]
├── 📁 Retail Operations
│   ├── 📁 Daily Monitoring
│   │   ├── Daily Sales [Retail]
│   │   ├── Yesterday's Sales [Retail]
│   │   └── Today's Orders [Retail]
│   ├── 📁 Periodic Reviews
│   │   ├── Sales Ops Weekly [Retail]
│   │   └── Sales Ops Monthly [Retail]
│   └── Promotion Analysis [Retail]
│
├── 📁 B2B Operations
│   ├── B2B Daily Sales [B2B]
│   ├── B2B Orders Tracking [B2B]
│   ├── Partner Performance [B2B]
│   └── B2B Margin Analysis [B2B]
│
└── 📁 Ingestion Health
    └── Data Pipeline Health

📁 Marketing & Customers              [Layer 2-Retail]
├── Marketing Weekly Tracker [Retail]
├── Marketing Monthly Analysis [Retail]
├── Customer Operational [Retail]
└── Customer Retention [Retail]

📁 Analytics                          [Layer 3]
├── Customer Intelligence [Cross]
├── Channel Profitability [Cross]
├── Product Profitability [Cross]
└── Acquisition Analysis [Cross]
```

---

## 7. SQL Templates

### 7.1 Layer 1 - Executive Query Template

```sql
-- Dashboard: {Name} [All]
-- Scope: scope_sales (tất cả doanh thu bán hàng)

SELECT
    -- metrics
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE c.is_sales_channel = true
  AND o.status NOT IN ('CANCELLED', 'Voided')
  [[AND date(o.order_timestamp) >= {{date_range}}]]
```

### 7.2 Layer 2 Retail Query Template

```sql
-- Dashboard: {Name} [Retail]
-- Scope: scope_retail (chỉ khách lẻ)

SELECT
    -- metrics
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
JOIN dim_customers cu ON o.customer_key = cu.customer_key
WHERE c.is_sales_channel = true
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND cu.customer_type = 'RETAIL'
  [[AND date(o.order_timestamp) >= {{date_range}}]]
```

### 7.3 Layer 2 B2B Query Template

```sql
-- Dashboard: {Name} [B2B]
-- Scope: scope_b2b (khách sỉ/đối tác)

SELECT
    -- metrics
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
JOIN dim_customers cu ON o.customer_key = cu.customer_key
WHERE c.is_sales_channel = true
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND cu.customer_type IN ('WHOLESALE', 'PARTNER')
  [[AND date(o.order_timestamp) >= {{date_range}}]]
```

### 7.4 Layer 3 Cross-Segment Query Template

```sql
-- Dashboard: {Name} [Cross]
-- Scope: scope_sales với explicit segment breakdown

SELECT
    cu.customer_type AS "Segment",
    -- metrics
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
JOIN dim_customers cu ON o.customer_key = cu.customer_key
WHERE c.is_sales_channel = true
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND cu.customer_type IN ('RETAIL', 'WHOLESALE', 'PARTNER')
  [[AND date(o.order_timestamp) >= {{date_range}}]]
GROUP BY cu.customer_type
```

---

## 8. Checklist Khi Tạo Dashboard Mới

- [ ] Xác định Layer (1/2/3) và audience
- [ ] Chọn scope phù hợp (scope_sales / scope_retail / scope_b2b)
- [ ] Thêm segment indicator vào tên dashboard
- [ ] Áp dụng base filter cho TẤT CẢ queries trong dashboard
- [ ] Nếu phân tích promotion: BẮT BUỘC dùng scope_retail
- [ ] Nếu phân tích B2B: BẮT BUỘC dùng scope_b2b
- [ ] Document scope trong blueprint header

---

## 9. Migration Guide cho Dashboards Hiện tại

| Blueprint hiện tại | Action | New Indicator |
|-------------------|--------|---------------|
| sales_daily_operation | Thêm `customer_type = 'RETAIL'` | [Retail] |
| sales_yesterday_operation | Thêm `customer_type = 'RETAIL'` | [Retail] |
| sales_promotion_analysis | Thêm `customer_type = 'RETAIL'` | [Retail] |
| marketing_weekly_tracker | Thêm `customer_type = 'RETAIL'` | [Retail] |
| customer_operational_dashboard | Thêm `customer_type = 'RETAIL'` | [Retail] |
| ceo_weekly_pulse | Ensure `is_sales_channel = true` | [All] |
| order_profitability | Ensure `is_sales_channel = true` | [All] |
| channel_profitability_monthly | Add segment breakdown | [Cross] |

---

## Liên kết Tài liệu

- [Sales Segmentation Guide](../../context/sales-segmentation-guide.md) — Gom nhóm theo channel/product/team
- [Customer Segmentation](../../context/customer-segmentation.md) — 8 chiều phân loại khách hàng
- [Collection Organization](./collection_organization.md) — Cấu trúc collection Metabase
- [Dashboard Design Patterns](./dashboard_design_patterns.md) — Quy chuẩn layout
