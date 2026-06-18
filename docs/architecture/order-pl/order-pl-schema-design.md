---
title: Per-Order P&L Schema Standardization
status: draft
last_modified: 2026-05-26
domain_refs: [domains/finance.md]
related_designs: [order_profitability.md, order_detail_view.md]
---

# Per-Order P&L Schema Standardization

## Mục tiêu

Chuẩn hóa schema lưu trữ chi phí để hỗ trợ P&L dashboard per-order:
- Filter/lookup theo `order_code` hoặc `order_id`, drill-down chi tiết
- Hiển thị đầy đủ revenue waterfall + cost breakdown + profit per order
- Extensible: thêm kênh/chi phí mới không phá vỡ schema hiện tại

---

## Trạng thái hiện tại

### `fact_order_economics` — P&L table đang dùng (Dashboard 35)

| Column group | Source | Coverage |
|---|---|---|
| Revenue waterfall (gross → net → collected) | Sapo — **giá bán VAT-inclusive**: `net = total_amount − vat_amount`. Xem [revenue_terminology.md](../analytics-handbook/guides/revenue_terminology.md) | 100% |
| COGS | MISA (voucher_no = order_code) | ~65% |
| Platform fees (service/payment/fixed/affiliate/infra/voucher_xtra) | Shopee Seller Center | Shopee only |
| Discount waterfall | Sapo `discount_items[]` → `discount_type` + `discount_rate` | ✅ Phân loại đủ 10 loại. Xem [discount-classification.md](discount-classification.md) |
| Shipping cost (carrier) | ❌ chưa có | — |
| Returns / refunds | ❌ chưa có | — |
| Payment gateway fee | ❌ chưa có | — |

### Gap theo kênh

| Kênh | Revenue | COGS | Platform Fee | Shipping | Returns |
|---|---|---|---|---|---|
| **Shopee** | ✅ | ✅ ~65% | ✅ Full | ❌ | ❌ |
| **Lazada / Tiki / TikTok / Sendo** | ✅ | ✅ ~65% | ❌ | ❌ | ❌ |
| **POS / Web / Social** | ✅ | ✅ ~65% | N/A | ❌ | ❌ |
| **B2B (Đại Lý / Chợ Sỉ)** | ✅ | ✅ ~65% | N/A | ❌ | ❌ |

---

## Đề xuất schema mới

### A. `fact_order_returns` (mới)

Materialize từ `src_sapo_order_returns` — hiện bị dropped sau ingestion, chưa có stg/std/fact.

```sql
-- grain: 1 row per return
return_id         VARCHAR
order_id          BIGINT
order_code        VARCHAR
return_date       DATE          -- ICT date_key
returned_at       TIMESTAMPTZ
refund_amount     DECIMAL
return_status     VARCHAR
return_reason     VARCHAR
channel_key       VARCHAR
date_key          INTEGER
```

**Convention:** Returns recognized tại ngày return — không restate order gốc. Period P&L net out tự nhiên khi aggregate.

---

### B. `fact_order_costs` (mới — long-format cost ledger)

Source of truth cho tất cả chi phí per-order. Thay cho việc mở rộng `fact_order_economics` theo chiều ngang mỗi khi có source mới.

```sql
-- grain: 1 row per (order_id, cost_type)
order_id        BIGINT
order_code      VARCHAR
cost_type       VARCHAR    -- taxonomy bên dưới
cost_category   VARCHAR    -- COGS | PLATFORM_FEE | SHIPPING | PAYMENT | TAX | DISCOUNT | REFUND
amount          DECIMAL    -- luôn positive (ABS), sign convention theo cost_category
source_system   VARCHAR    -- 'sapo_v2' | 'misa' | 'shopee' | 'carrier_ghtk' | ...
source_record   VARCHAR    -- traceability (voucher_no, invoice_id, ...)
fee_source      VARCHAR    -- 'actual' | 'estimated'
recorded_at     TIMESTAMPTZ
```

**Cost type taxonomy:**

| cost_type | cost_category | Nguồn hiện tại |
|---|---|---|
| `cogs` | COGS | MISA → int_misa_sales_lines |
| `platform_service` | PLATFORM_FEE | Shopee → int_shopee_order_fees |
| `platform_payment` | PLATFORM_FEE | Shopee → int_shopee_order_fees |
| `platform_fixed` | PLATFORM_FEE | Shopee → int_shopee_order_fees |
| `platform_affiliate` | PLATFORM_FEE | Shopee → int_shopee_order_fees |
| `platform_infra` | PLATFORM_FEE | Shopee → int_shopee_order_fees |
| `platform_voucher_xtra` | PLATFORM_FEE | Shopee → int_shopee_order_fees |
| `shipping_platform` | SHIPPING | Shopee → int_shopee_order_fees |
| `shipping_carrier` | SHIPPING | Carrier invoice (GHTK/J&T/GHN/VTP) — chưa build |
| `payment_gateway` | PAYMENT | VNPAY/OnePay — chưa build |
| `tax_vat` | TAX | Shopee/Sapo |
| `tax_pit` | TAX | Shopee |
| `discount_seller_voucher` | DISCOUNT | Shopee |
| `discount_subsidy` | DISCOUNT | Shopee |
| `discount_order` | DISCOUNT | Sapo `total_discount` (mixed) |
| `adjustment_marketing` | PLATFORM_FEE | Shopee → int_shopee_order_adjustments |
| `adjustment_compensation` | PLATFORM_FEE | Shopee → int_shopee_order_adjustments |
| `refund` | REFUND | fact_order_returns |

---

### C. Extend `fact_order_economics` (thay đổi tối thiểu)

Giữ nguyên toàn bộ column hiện tại. Thêm:

| Column mới | Source | Ghi chú |
|---|---|---|
| `has_cogs` | MISA join | BOOLEAN |
| `has_platform_fees` | source system | BOOLEAN — true nếu Shopee hoặc có actual fee |
| `cod_amount` | std_fulfillments | COD value collected từ khách |
| `carrier_id` | std_fulfillments | Tên đơn vị vận chuyển |
| `return_amount` | fact_order_returns | Tổng refund của đơn nếu có |
| `shipping_carrier_cost` | fact_order_costs (shipping_carrier) | Khi có carrier invoice |

`fact_order_economics` giữ vai trò **wide rollup table** cho dashboards hiện tại. `fact_order_costs` là source granular để pivot.

---

## Phạm vi triển khai

| Hạng mục | Ưu tiên | Trạng thái |
|---|---|---|
| `fact_order_returns` (stg → std → fact) | P0 | 🔲 Cần build |
| Extend `fact_order_economics` (flags + cod_amount + return_amount) | P0 | 🔲 Cần build |
| `fact_order_costs` — COGS rows (từ int_misa_sales_lines) | P1 | 🔲 Cần build |
| `fact_order_costs` — Shopee fee rows (từ int_shopee_order_fees) | P1 | 🔲 Cần build |
| Carrier invoice ingestion (GHTK/J&T/GHN/VTP) | P2 | ⏳ Chờ quyết định format |
| Lazada / Tiki / TikTok pipeline | P3 | ⏳ Ít đơn, ưu tiên thấp |
| Payment gateway fee (VNPAY/OnePay) | P3 | ⏳ Chờ quyết định |

---

## Câu hỏi chưa giải quyết

### Nhóm 1 — Đơn đại lý (B2B)

**Q1.1 — Revenue baseline cho đại lý là gì?**
Sapo ghi `total_discount` = wholesale price gap (giá lẻ − giá đại lý) — không phải promotion thực sự. Trong P&L per-order:
- Option A: Dùng `net_revenue` làm baseline (giá đại lý thực trả), không show "discount" vì không có discount thực
- Option B: Giữ gross_revenue = giá lẻ + label `discount` thành "Wholesale Price Gap" để management thấy contribution so với retail

**Q1.2 — Identify đơn đại lý bằng gì?**
Hiện tại dùng `scope_b2b` filter (channel-based, qua source_name). Câu hỏi: đại lý có mua qua kênh retail không, hay 100% đơn đại lý đi qua kênh riêng (Chợ Sỉ, Đại Lý)?

**Q1.3 — COGS đơn đại lý có đặc thù không?**
Mua số lượng lớn → MISA có ghi nhận COGS per-unit khác retail không? Hay giống nhau?

**Q1.4 — Discount label trong P&L**
Khi show Order Detail cho đơn đại lý, dòng "Discount" có nên đổi label thành "Wholesale Price Gap" để tránh nhầm lẫn với promotional discount không?

---

### Nhóm 2 — Discount taxonomy

**Q2.1 — Sapo discount_codes có per-code amount không?**
Array `discount_codes` trong order payload chứa gì? Chỉ có code string hay có cả amount per code? Cần xem raw payload để xác định có thể decompose `total_discount` thành (coupon + combo + B2B gap + employee) không.

**Q2.2 — Có loại discount đặc biệt nào cần xử lý khác không?**
Ví dụ: discount nhân viên, đơn dùng thử, quà tặng — có cần flag riêng hay exclude khỏi discount analytics?

---

### Nhóm 3 — Shipping (Carrier cost)

**Q3.1 — Format hóa đơn carrier**
GHTK / J&T / GHN / Viettel Post — export dưới dạng Excel hay có API? Tần suất đối soát: ngày / tuần / tháng?

**Q3.2 — Mapping method**
Map carrier cost vào order bằng `tracking_code` (từ std_fulfillments) hay `order_code`? Có trường hợp 1 đơn giao nhiều lần (re-delivery, return pickup) phát sinh nhiều dòng carrier cost không?

---

### Nhóm 4 — Marketing attribution

**Q4.1 — Chấp nhận channel-level attribution?**
Hiện tại `fact_marketing_spend` chỉ ở mức channel × date. Chấp nhận không có per-order marketing attribution, hay cần plan UTM tracking về sau?

**Q4.2 — Shopee Ads per-order**
`adjustment_marketing` trong Shopee settlement có đủ để tính marketing cost per-order Shopee không, hay cần data từ Shopee Ads dashboard riêng?

---

### Nhóm 5 — MISA coverage & COGS gap

**Q5.1 — Kênh nào thường thiếu MISA record?**
35% đơn không có COGS — phân bố theo kênh như thế nào? (Giúp ưu tiên fix ở nguồn hay build fallback đúng chỗ.)

**Q5.2 — Có cần preliminary P&L cho đơn chưa có MISA không?**
Có cần hiển thị P&L ước tính (dùng avg COGS per SKU từ dim_products) cho đơn gần đây chưa được MISA sync chưa, hay ẩn hẳn và chờ MISA?
