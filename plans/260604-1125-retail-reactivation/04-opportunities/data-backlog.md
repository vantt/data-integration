---
title: "Data Backlog — Cơ hội khai thác dữ liệu"
stage: 4
status: idea
source: ../reference/sales-slowdown-diagnosis-and-action-playbook.md
---

# Data Backlog — Cơ hội khai thác dữ liệu

> Bối cảnh: brand hàng tiêu dùng lặp lại ⇒ nhịp mua lại là vàng. Cỗ máy
> `avg_days_between_orders` + `next_purchase_signal` + `predicted_next_purchase_date` đang bị dùng thiếu.
>
> Nguồn: §7 (7.1/7.2/7.3), §3.3, §4.5 — playbook chẩn đoán.

---

## Nhóm 1 — Đã có data, dùng ngay

> Nguồn: §7.1. Không cần build — data đã sẵn trong `mart_customer_action_queue`.

**Customer Care — `mart_customer_action_queue` là call-list đã nấu chín nhưng chưa ai chạy.**

| action_type | Số khách | Value at stake (tr.đ) | Ý nghĩa |
|---|---|---|---|
| WIN_BACK | 47 | **1.134** | Khách giá trị đã churn → kéo về |
| REORDER_NUDGE | 62 | **547** | Khách giá trị OVERDUE → nhắc mua lại |
| CALL_NOW | 9 | 79 | VIP/GOLD đang At-Risk → gọi tay ngay |
| SECOND_ORDER | 59 | 2 | Khách mua-1-lần ngày 15–45 → hích đơn #2 |
| HIGH_CANCEL_RISK | 11 | — | Tỷ lệ hủy >50% → xử lý chất lượng |

→ **~1.76 tỷ VND cơ hội đã nhận diện & xếp ưu tiên, đang nằm im trong bảng không ai mở.**

Bổ sung nhanh: `next_purchase_signal = OVERDUE` có **210 khách = 3.549 tr.đ LTV** đang tuột.
Nâng cấp: thêm action `REORDER_PREEMPT` cho nhóm `DUE_SOON` (nhắc trước khi khách quên — chỉ 14
khách hiện ở DUE_SOON vì cỗ máy chưa được vận hành để giữ họ "on track").

Chưa đụng: `return_reason` (`fact_order_returns`) chưa phân tích — gom nhóm lý do trả = bản đồ
lỗi sản phẩm/kỳ vọng, sửa gốc để giảm hủy & tăng mua lại.

**Marketing:**
- Đừng đổ thêm tiền acquisition khi xô còn thủng. 2026 đã chứng minh acquisition mạnh; ROI biên
  thấp khi 72% rò. Dồn lực vào second-order conversion.
- Rò lãi discount: chỉ 2 khách `FULL_PRICE`, 15% `PROMO_DEPENDENT` — phụ thuộc KM cao. Tách nhóm
  trung thành để không giảm giá người sẵn sàng trả đủ.
- Ghép `mart_inventory_health.is_dead_stock`/`is_slow_mover` với `product_affinity` → campaign
  clearance đúng nhóm mê brand.
- Dùng `avg_days_between_orders` hẹn giờ gửi tin theo chu kỳ cá nhân.

**Sales:**
- Ghép top SKU (`mart_sku_economics_monthly.revenue_share_pct`) với `mart_inventory_health.is_oos` →
  danh sách "phải nhập gấp". OOS trên hero-SKU gây ế trực tiếp.
- `fact_targets` có chỉ tiêu nhưng **actual-vs-target chưa tính** → dựng variance theo kênh/team/tháng.
- Chính thức hóa sỉ ẩn: lọc `discount_type = negotiated_deep` → kênh sỉ có chính sách.

**Plan liên kết:** [../05-action-plans/b2c-reactivation-phases.md](../05-action-plans/b2c-reactivation-phases.md) — P1 (chạy tay call-list) → P2 (worklist Sheet) → P3 (automation nhắc).

---

## ✅ ĐÃ FIX 2026-06-10: Bug margin mart_sku_economics_monthly

> Phát hiện + fix 2026-06-10 — nguồn: [../02-understand/product-performance-assessment.md](../02-understand/product-performance-assessment.md).

✅ **ĐÃ FIX 2026-06-10:** seed `misa_qty_multiplier=1` cho 5 SKU H010 (Hyaluron&Collagen, Cordyceps Plus, Swallow Nest — MISA ghi theo Hộp, không phải Chai → multiplier=10 cũ làm COGS ×10 SAI) + thêm cột `realized_margin_pct` = (net_revenue−cogs_amount)/net_revenue vào `mart_sku_economics_monthly`. Pipeline đã materialize 2026-06-10 03:xx ICT. H010 biên thực +59→83% (không bán dưới giá vốn). "Lỗ 440M" là artifact hoàn toàn. [Tier 1 — DONE]

---

## 🔴 Lỗ hổng đo lường nghiêm trọng

> Phát hiện 2026-06-09 — chặn mọi phân tích cashflow & biên cho đến khi fix.

**Pipeline thanh toán (`fact_payments` rỗng / `payment_status` đáng ngờ)** — không đo được tiền thực thu → chặn mọi phân tích cashflow & biên. `payment_status` suy từ cờ đơn hàng Sapo (chưa chắc phản ánh thanh toán thực tế). ~2.7 tỷ AR B2B ghi nhận nhưng không biết đã thu chưa.

Việc cần làm:
1. Điều tra vì sao `fact_payments` rỗng — pipeline Sapo có chứa data thanh toán không?
2. Surface dữ liệu thanh toán Sapo (nếu có) vào mart.
3. Kiểm chứng độ tin cậy `payment_status`: có được cập nhật khi khách trả tiền không?
4. Thêm cột `debt` (`std_customers`, chưa surface trong parquet) — hạn mức gối đầu khách sỉ.

→ Xem chi tiết: [cashflow-collection-ar](../02-understand/cashflow-collection-ar.md)

---

## Nhóm 2 — Build nhỏ

> Nguồn: §7.2 + §4.5. Data có trong raw/dim nhưng chưa surface — effort nhỏ, mở khóa nhanh.

### §7.2 — Có trong raw nhưng chưa surface

| Data | Đang ở đâu | Mở khóa |
|---|---|---|
| **FB Messenger** (chat-to-order, response time) | models đã viết nhưng `enabled=false` | Social-commerce VN: tốc độ rep = tỷ lệ chốt. Bật pipeline + tính FRT/AHT |
| `debt` (công nợ khách) | `std_customers`, chưa surface | Khách sỉ chạm trần nợ → không đặt thêm → đè doanh thu |
| `tags` sản phẩm | `dim_products.tags` (JSON chưa parse) | Merchandising/affinity theo công dụng, dòng da |
| `source_id` đơn | `fact_orders`, mới dùng làm channel | Proxy thô cho nguồn acquisition |
| `status` khách (Sapo) | `stg_sapo_customers`, chưa surface | Lọc active/inactive thật |

### Product performance — Tier 1 (justified, làm sớm)

> Nguồn: [../02-understand/product-performance-assessment.md](../02-understand/product-performance-assessment.md) — 4-agent assessment 2026-06-10.

- **`product_group`/function seed** (gộp variant `(*)` + nhóm công dụng — parse tên) [Tier 1] — mở khóa phân tích theo brand/dòng
- **Bắt buộc `return_reason` + fix `int_return_sku_lines` mapping** (hiện 2/10, reason 90% trống) [Tier 1]
- **Mở rộng `inventory_health`** ra tất cả hero SKU (hiện chỉ 8 Cordyceps) [Tier 1]

### §4.5 — Data cần để vận hành tệp lẻ

| Cần | Trạng thái | Việc |
|---|---|---|
| `first_order_channel` (kênh acquisition) | chưa surface | suy từ `fact_orders` (arg_min theo order_timestamp) → cohort & retention theo kênh |
| `is_contactable` (có SĐT hợp lệ) | tính được từ `dim_customers.phone` | thêm cột để lọc tệp chạy được CSKH |
| `is_us_gift_recipient` | chưa có | thêm cờ để tách luồng US khỏi win-back thông thường |
| Shopee→owned migration tracking | chưa có | field nguồn đăng ký Zalo OA / mã voucher direct-first |
| Market-basket (mua kèm) | chưa có | model mới từ `fact_sales` |

**Plan liên kết:** [../05-action-plans/b2c-reactivation-phases.md](../05-action-plans/b2c-reactivation-phases.md) — P2 (`is_contactable`, `is_us_gift_recipient`) → P3 (Shopee→owned tracking).

---

## Nhóm 3 — Build lớn, ROI cao

> Nguồn: §7.3 + §3.3. Effort lớn hơn nhưng tạo nền hạ tầng analytics dài hạn.

### Product performance — Tier 2 (HOÃN, chỉ nếu dashboard cần)

> Nguồn: [../02-understand/product-performance-assessment.md](../02-understand/product-performance-assessment.md) — 4-agent assessment 2026-06-10.

- **product-cohort mart** (first_product×cohort→retention) [Tier 2 — hoãn, chỉ nếu dashboard cần]
- **market-basket / cross-product-path model** [Tier 2 — hoãn]

### §7.3 — Chưa có, build mới

1. **Nguồn acquisition / first-touch** — `acquisition_source` luôn NULL. Quick-win: suy
   `first_order_channel` từ đơn đầu mỗi khách (`fact_orders`) → cohort-theo-nguồn ngay.
2. **Market-basket** — `fact_sales` đúng grain nhưng chưa có model frequently-bought-together
   → bundle + upsell (đòn bẩy AOV).
3. **ROAS cấp chiến dịch** — `fact_fb_ads_insights_daily` disabled.
4. **Phễu trước mua** (session, add-to-cart) — chỉ có đơn, không thấy nơi rớt trước checkout.
5. **Churn-propensity / CLV dự báo** — hiện chỉ rule-based.
6. **NPS / voice-of-customer** — chưa thu gì.

### §3.3 — Productionize Retention Waterfall

> `mart_customer_status_snapshot_monthly` hiện dùng `last_order_date` hiện tại → thổi phồng ACTIVE
> gần 9× tháng đáy, xóa sạch sự kiện gần-chết 2025 khỏi dashboard. Cần thay bằng point-in-time.

1. **Thêm model `mart_retention_waterfall_monthly`** (point-in-time từ `fact_orders`) — grain
   `(snapshot_month, status)` + biến thể có `value_group`, `product_affinity`, `channel_preference`
   để bóc tách churn theo phân khúc. Giữ model snapshot cũ cho thuộc tính khách, **nhưng ngừng dùng
   cột `status` cho biểu đồ xu hướng** — gắn cảnh báo vào `schema.yml`.
2. **Dashboard "Retention Health" (Metabase):** (a) đường ACTIVE/AT_RISK/CHURNED point-in-time;
   (b) heatmap cohort M0–M6; (c) thẻ số one-time-rate & M1-repeat-rate; (d) đường new-vs-returning;
   (e) bộ lọc kênh lõi/marketplace + completed-only.
3. **Targets** (link sang execute): M1 repeat **3–17% → ≥25%** trong 2 quý; one-time-rate **72% → <60%**.
   → Targets chính thức tại [../06-execute/kpi.md](../06-execute/kpi.md)

**Plan liên kết:** [../05-action-plans/b2c-reactivation-phases.md](../05-action-plans/b2c-reactivation-phases.md) — P3 (`mart_retention_waterfall_monthly`) → P4 (dashboard Retention Health + automation).
