---
title: Discount Classification by Nature (Sapo)
status: active
last_modified: 2026-06-29
domain_refs: [domains/finance.md, domains/customer.md]
related_designs: [order-pl-schema-design.md, order_detail_view.md]
---

# Discount Classification by Nature — Sapo Order Discounts

## Vấn đề

Sapo `discount_items[]` hiện được phân loại thành 4 bucket dựa trên `reason` text: `discount_seller_voucher`, `discount_bundle`, `discount_seller`, `discount_manual`. **`discount_manual` = 74.5% volume (~100 tỷ VND)** — chiếm phần lớn nhưng không có tín hiệu phân loại.

### Dữ liệu hiện tại

| Dimension | Phát hiện |
|---|---|
| Discount_manual có empty reason | 93% (3,438/3,690 orders) |
| Nhóm empty reason 40-70% rate | ~19.3 tỷ VND không context |
| Voucher seller rate | Luôn = 0 (amount mang giá trị) |
| High-discount customers | Sapo tag "Retail" nhưng thực tế wholesale signal |

### Nguyên nhân

- **Người dùng không fill reason** → empty text
- **Kênh B2B ghi "Discount"** thay vì "Wholesale Price Gap" → không phân biệt
- **Discount rate không được pass** vào mart (`fact_order_costs`) → mất metric

**Hậu quả:** Retail metrics (avg discount, ARPU) bị contaminate bởi hidden wholesale. Không thể reclassify customer (Sapo logic), phải reclassify discount.

---

## 4-Bucket Customer-Level Taxonomy

Để phục vụ CRM và dim_customers, 10 `discount_type` values được gộp thành **4 bucket analytics**:

| Bucket | Nguồn | discount_type values | Ý nghĩa |
|---|---|---|---|
| `line_discount` | `order_items.discount_amount / (unit_price × quantity)` | N/A (không có label) | Giảm trực tiếp trên dòng sản phẩm |
| `voucher` | `discount_items WHERE discount_type = 'voucher_promotional'` | `voucher_promotional` | Khách **CHỦ ĐỘNG** dùng mã voucher — engagement signal |
| `campaign` | `discount_items` (các type còn lại không phải negotiated) | `bundle`, `campaign`, `sampling_gift` | Merchant **CHỦ ĐỘNG** áp: bundle/CTKM/tặng mẫu — dependency signal |
| `negotiated` | `discount_items` | `negotiated_micro`, `negotiated_standard`, `negotiated_deep`, `wholesale_explicit`, `employee_internal`, `overseas` | Thỏa thuận trực tiếp: đại lý/hợp đồng/nhân viên/overseas |

**Phân biệt quan trọng — voucher vs campaign:**
- `voucher` = khách chủ động nhập mã (engagement signal — khách biết & dùng chương trình)
- `campaign` = merchant chủ động áp discount (dependency signal — khách quen được hưởng giá ưu đãi mà không cần effort)

**Lưu ý double-count:** 31,890 đơn có BOTH line-item discount (từ `order_items`) AND order-level discount (từ `discount_items`). Hai nguồn được track **độc lập**, không cộng gộp. Line discount và order-level discount phản ánh 2 mechanism khác nhau trong Sapo.

**Line discount đến từ `order_items.discount_amount`** — KHÔNG phải từ `discount_items_json`. Đây là discount áp tại dòng sản phẩm, khác với order-level discount items.

---

## 8 Fields trong `dim_customers` (Customer-Level Discount Signals)

Mỗi bucket có 2 fields: `last_*` (đơn gần nhất có bucket đó) và `max_*` (cao nhất từ trước đến nay):

| Field | Mô tả |
|---|---|
| `last_line_discount_rate` | Rate line discount trên đơn gần nhất có line discount |
| `max_line_discount_rate` | Rate line discount cao nhất từ trước đến nay |
| `last_voucher_discount_rate` | Rate voucher discount trên đơn gần nhất có voucher |
| `max_voucher_discount_rate` | Rate voucher discount cao nhất từ trước đến nay |
| `last_campaign_discount_rate` | Rate campaign discount trên đơn gần nhất có campaign |
| `max_campaign_discount_rate` | Rate campaign discount cao nhất từ trước đến nay |
| `last_negotiated_discount_rate` | Rate negotiated discount trên đơn gần nhất có negotiated |
| `max_negotiated_discount_rate` | Rate negotiated discount cao nhất từ trước đến nay |

**Scale:** Tất cả rate là 0.0–1.0 (không phải %). NULL = khách chưa bao giờ có đơn thuộc bucket đó.

**Cũng có trong `wh_customer_insight`** (reverse-ETL sang CRM) để CRM đọc trực tiếp.

---

## Giải pháp: Taxonomy `discount_type`

Thêm 2 column vào `fact_order_costs` (Sapo discounts only):
- `discount_rate` — pass-through từ staging (hiện bị drop)
- `discount_type` — classification kết hợp reason + rate

### Bảng phân loại

| discount_type | Logic | Ghi chú |
|---|---|---|
| `voucher_promotional` | reason ILIKE 'voucher seller:%' | rate=0 luôn; amount mang giá trị |
| `bundle` | reason = 'Bundle Deal' | Chiến lược sản phẩm |
| `sampling_gift` | reason ILIKE '%sampling%' OR '%mẫu%' OR '%tặng%' | Zero/near-zero revenue |
| `wholesale_explicit` | reason ILIKE '%đại lý%' OR '%hợp đồng%' OR '%nhà thuốc%' | Trade labeled |
| `overseas` | reason normalized: '%mỹ%' OR '%us%' | Export pricing |
| `campaign` | reason ILIKE '%ctkm%' OR '%father%' OR '%mascot%' | Marketing programs |
| `employee_internal` | reason ILIKE '%nhân viên%' OR '%ctv%' OR '%hoa hồng%' | Staff/CTV |
| `negotiated_micro` | reason empty AND rate < 20% | Goodwill nhỏ |
| `negotiated_standard` | reason empty AND 20% ≤ rate < 40% | Retail negotiation |
| `negotiated_deep` | reason empty AND rate ≥ 40% | Wholesale signal ẩn |

**Thứ tự evaluation:** voucher_promotional → bundle → sampling_gift → wholesale_explicit → overseas → campaign → employee_internal → negotiated (by rate).

### Thêm vào `fact_orders`

| Column mới | Loại | Mô tả |
|---|---|---|
| `max_discount_rate` | DECIMAL | Highest rate across all discount items |
| `primary_discount_type` | VARCHAR | discount_type with largest amount |

---

## Thay đổi pipeline

### Staging: `stg_sapo_order_discount_items` (không đổi)

Giữ nguyên unnest `discount_items[]`. Vẫn filter B2B price-gap (`rate=100 AND reason=''`).

### Mart: `fact_order_costs`

**Thêm logic classification:**

```sql
WITH classified AS (
  SELECT
    order_id, order_code,
    discount_source, discount_rate, amount, reason,
    CASE
      WHEN reason ILIKE 'voucher seller:%'
        THEN 'voucher_promotional'
      WHEN reason = 'Bundle Deal'
        THEN 'bundle'
      WHEN reason ILIKE '%sampling%' OR reason ILIKE '%mẫu%'
        THEN 'sampling_gift'
      WHEN reason ILIKE '%đại lý%' OR reason ILIKE '%hợp đồng%'
        THEN 'wholesale_explicit'
      WHEN LOWER(REPLACE(reason, '_', '')) ILIKE '%mỹ%'
           OR LOWER(REPLACE(reason, '_', '')) ILIKE '% us%'
        THEN 'overseas'
      WHEN reason ILIKE '%ctkm%' OR reason ILIKE '%father%'
        THEN 'campaign'
      WHEN reason ILIKE '%nhân viên%' OR reason ILIKE '%ctv%'
        THEN 'employee_internal'
      WHEN reason = '' AND discount_rate < 20
        THEN 'negotiated_micro'
      WHEN reason = '' AND discount_rate >= 20 AND discount_rate < 40
        THEN 'negotiated_standard'
      WHEN reason = '' AND discount_rate >= 40
        THEN 'negotiated_deep'
      ELSE 'unknown'
    END AS discount_type
  FROM stg_sapo_order_discount_items
)
SELECT * FROM classified;
```

**Columns trong `fact_order_costs`:**
- Giữ: `order_id`, `order_code`, `discount_source`, `amount`, `reason`
- **Thêm:** `discount_rate`, `discount_type`

### Mart: `fact_orders`

```sql
SELECT
  o.*,
  MAX(CASE WHEN cost_type ILIKE 'discount%' THEN discount_rate ELSE 0 END)
    OVER (PARTITION BY order_id) AS max_discount_rate,
  FIRST_VALUE(discount_type)
    OVER (PARTITION BY order_id ORDER BY amount DESC)
    AS primary_discount_type
FROM fact_orders o
LEFT JOIN fact_order_costs c ON o.order_id = c.order_id;
```

---

## Sử dụng trong report

### Standard Retail Metrics (không bị contaminate)

```sql
SELECT
  DATE_TRUNC('month', order_date) AS month,
  COUNT(*) AS order_count,
  AVG(CASE
    WHEN primary_discount_type NOT IN ('wholesale_explicit', 'overseas', 'negotiated_deep')
      THEN max_discount_rate
    ELSE NULL
  END) AS avg_discount_rate_retail
FROM fact_orders
WHERE primary_discount_type IS NOT NULL
  AND primary_discount_type NOT IN ('wholesale_explicit', 'overseas', 'negotiated_deep')
GROUP BY 1;
```

### Discount Decomposition View

```sql
SELECT
  primary_discount_type,
  COUNT(*) AS order_count,
  SUM(total_discount) AS total_discount_amount,
  ROUND(100.0 * SUM(total_discount) / SUM(SUM(total_discount)) OVER (), 2) AS pct
FROM fact_orders
WHERE primary_discount_type IS NOT NULL
GROUP BY 1
ORDER BY total_discount_amount DESC;
```

### Track Hidden Wholesale Behavior

```sql
SELECT
  DATE_TRUNC('month', order_date) AS month,
  COUNT(*) FILTER (WHERE primary_discount_type = 'negotiated_deep') AS negotiated_deep_orders,
  SUM(CASE WHEN primary_discount_type = 'negotiated_deep' THEN total_discount ELSE 0 END) AS amount
FROM fact_orders
GROUP BY 1
ORDER BY 1 DESC;
```

---

## Lưu ý quan trọng

### 1. Voucher seller rate = 0 không phải error

Sapo không populate `rate` cho voucher discount — `amount` là signal duy nhất. Đó là design Sapo, không phải data issue.

### 2. B2B price-gap filter

Staging đã exclude `rate=100 AND reason=''` (B2B wholesale price gap). **Không** đưa lại vào fact_order_costs. Nó không phải discount thực sự.

### 3. Overseas normalization

Reason field chứa "Khách Mỹ", "US", "us", "Hàng chị Thơ mang qua Mỹ" (inconsistent). Cần `REPLACE(reason, '_', '')` + LOWER trước ILIKE để catch biến thể.

### 4. Micro-reasons giữ nguyên

Lưu `reason` text gốc trong `fact_order_costs` để drill-down. Classification logic dùng regex, nhưng analyst có thể inspect raw reason.

### 5. Edge case: Multiple discounts per order

Đơn có 3 discount items (e.g., voucher + bundle + seller) → 3 rows trong `fact_order_costs`. `primary_discount_type` = nature của item có amount lớn nhất (metric cho order-level logic).

---

## Phạm vi triển khai

| Hạng mục | Ưu tiên | Trạng thái |
|---|---|---|
| Add `discount_rate`, `discount_type` to `fact_order_costs` | P0 | 🔲 Cần build |
| Add `max_discount_rate`, `primary_discount_type` to `fact_orders` | P0 | 🔲 Cần build |
| Discount decomposition dashboard | P1 | 🔲 Cần build |
| Validate taxonomy on historical data | P1 | 🔲 Cần build |

---

## Câu hỏi chưa giải quyết

**Q1 — Có loại discount nào khác cần capture?**
Hiện tại taxonomy dựa trên scan 3,690 orders. Có khả năng `reason` mới xuất hiện sau, cần review quarterly.

**Q2 — Discount rate = NULL case?**
Voucher promotional rate = 0. Có case nào rate NULL không? (Nếu có, xử lý như negotiate_micro hay ignore?)

**Q3 — Negative discount (refund)?**
Pipeline hiện exclude refund vào `fact_order_returns`. Discount_items có negative `amount` không?
