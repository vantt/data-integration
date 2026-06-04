---
title: "Retail Reactivation — Lộ trình triển khai"
created: 2026-06-04
status: active
doc_ref: ./sales-slowdown-diagnosis-and-action-playbook.md
---

# Retail Reactivation — Lộ trình triển khai

> Nguồn phân tích: [`sales-slowdown-diagnosis-and-action-playbook.md`](./sales-slowdown-diagnosis-and-action-playbook.md)
> Bối cảnh: 1.082 khách lẻ có SĐT; 71.8% one-time; ~1.76 tỷ VND cơ hội trong `mart_customer_action_queue`.
> 76% tệp liên hệ được là người nhận quà US — cần luồng thông điệp riêng.

---

## Tổng quan phase

| Phase | Tên | Thời hạn | Status |
|---|---|---|---|
| P0 | Quick wins (0-build) | Tuần này | pending |
| P1 | Data plumbing | 1–2 tuần | pending |
| P2 | Model retention đúng | 2–4 tuần | pending |
| P3 | Dashboard Retention Health | 3–5 tuần | pending |
| P4 | Chương trình vận hành | ongoing | pending |

---

## P0 — Quick Wins (0-build, tuần này)

**Mục tiêu:** Bắt đầu hành động ngay với data đã có, không cần build thêm gì.

**Dependencies:** không có.

**KPI:** worklist xuất được trong ngày; báo cáo kênh lõi có; OOS hero-SKU có.

### Todo

- [ ] Export ~120 khách high-touch (Luồng 1–4 từ `mart_customer_action_queue`, lọc `phone IS NOT NULL`)
      ra Google Sheet hoặc CSV bên ngoài git.
      **CẢNH BÁO PII: file chứa tên/SĐT khách — KHÔNG commit vào git.**
- [ ] Báo cáo doanh thu **tách kênh lõi vs marketplace** (B2B+Social+Web vs Shopee+CrossBorder),
      chỉ `status='COMPLETED'`, theo tháng 2026. Xem đúng "nhu cầu lõi" thật.
- [ ] Báo cáo OOS / low-stock hero-SKU: ghép `mart_sku_economics_monthly.revenue_share_pct` với
      `mart_inventory_health.is_oos` → danh sách "phải nhập gấp" cho Sales.
- [ ] Sales lead gọi **6 CALL_NOW** (VIP/Gold At-Risk) trong tuần.
- [ ] CSKH Zalo/gọi **31 REORDER_NUDGE** + **16 SECOND_ORDER** nóng (15–45 ngày, có SĐT).
- [ ] Soạn 4 script Zalo mẫu (Luồng 1–4) + 3 mức voucher (offer matrix mục 5.4 trong guide).
- [ ] Ghi outcome (đặt lại Y/N, lý do bỏ) vào Sheet sau mỗi cuộc gọi; review cuối tuần.

**Owner:** Data (export) · Sales lead (Luồng 1–2) · CSKH (Luồng 3–4)

---

## P1 — Data Plumbing

**Mục tiêu:** Thêm các cột/cờ cần thiết để action_queue chạy đúng và tách luồng US.

**Dependencies:** P0 done (biết worklist thiếu gì).

**KPI:** `is_contactable` & `is_us_gift_recipient` có trong `dim_customers`; worklist tuần tự động export.

### Todo

#### dim_customers
- [ ] Thêm cột `is_contactable` (boolean): `phone IS NOT NULL AND phone ~ '^(0|\+84)[0-9]{8,9}$'`
      → dùng làm filter mặc định cho mọi action_queue query.
- [ ] Thêm cột `is_us_gift_recipient` (boolean): `customer_key IN (SELECT DISTINCT customer_key FROM fact_orders WHERE channel_format = 'CrossBorder')`
      → tách luồng thông điệp US riêng.

#### mart_customer_action_queue
- [ ] Thêm filter `is_contactable = true` vào điều kiện mặc định của mart.
- [ ] Thêm cột `last_product_affinity_sku` (SKU/brand hay mua nhất) để cá nhân hóa script.
- [ ] Thêm action type `REORDER_PREEMPT` cho khách có `next_purchase_signal = 'DUE_SOON'`
      (nhắc trước khi hết hàng, không chờ OVERDUE).
- [ ] Thêm cột `is_us_gift_recipient` vào mart để filter/tách luồng US.

#### Dagster automation
- [ ] Tạo job/sensor tự động export worklist tuần (Luồng 1–4, is_contactable=true)
      ra file CSV vào thư mục không-git (hoặc Google Sheet qua API).
      Chạy mỗi thứ Hai sáng.

**Owner:** Data

---

## P2 — Model Retention Đúng

**Mục tiêu:** Thay thế model snapshot sai bằng waterfall point-in-time; thêm first_order_channel.

**Dependencies:** P1 done (dim_customers cập nhật).

**KPI:** `mart_retention_waterfall_monthly` cho số khớp với SQL chẩn đoán ở mục 3.2 của guide;
schema.yml có cảnh báo trên `mart_customer_status_snapshot_monthly`.

### Todo

#### mart_retention_waterfall_monthly (model mới)
- [ ] Build model dbt, grain `(snapshot_month, status)`.
      Logic: point-in-time từ `fact_orders` — tại cuối mỗi tháng, dùng lần mua gần nhất ≤ cuối tháng đó.
      Tham khảo SQL mẫu ở mục 3.2 của guide.
- [ ] Thêm biến thể cột: `value_group`, `product_affinity`, `channel_preference`
      để bóc tách churn theo phân khúc.
- [ ] Viết test dbt: so sánh số tháng 2025-05 (`ACTIVE=7`) và 2025-06 (`ACTIVE=8`) với kết quả SQL thủ công.

#### Deprecation model cũ
- [ ] Thêm cảnh báo vào `schema.yml` của `mart_customer_status_snapshot_monthly`:
      mô tả rõ cột `status` phản ánh trạng thái hiện tại (không phải point-in-time), không dùng cho
      biểu đồ xu hướng retention.

#### first_order_channel
- [ ] Thêm cột `first_order_channel` vào `dim_customers` hoặc `mart_customer_retention_cohort`:
      suy từ `fact_orders` bằng `arg_min(channel_format, order_timestamp)` per customer.
      Dùng cho cohort-theo-nguồn và bảng retention theo kênh (mục 4.3 của guide).

**Owner:** Data

---

## P3 — Dashboard Retention Health (Metabase)

**Mục tiêu:** Dashboard thay thế biểu đồ dùng model cũ; bộ lọc đúng để không bị đánh lừa số.

**Dependencies:** P2 done (`mart_retention_waterfall_monthly` ready).

**KPI:** Dashboard live trên Metabase; các số khớp với bảng point-in-time mục 2.4 của guide.

### Todo

- [ ] Card 1: Đường ACTIVE / AT_RISK / CHURNED point-in-time (14 tháng gần nhất).
      Nguồn: `mart_retention_waterfall_monthly`.
- [ ] Card 2: Heatmap cohort retention M0–M6.
      Nguồn: `mart_retention_waterfall_monthly` hoặc cohort query từ `fact_orders`.
- [ ] Card 3: Thẻ số — one-time-rate & M1-repeat-rate (hiện tại + so kỳ trước).
- [ ] Card 4: Đường new-vs-returning buyers/tháng.
- [ ] Bộ lọc: kênh lõi vs marketplace; `status = 'COMPLETED'` only.
      (Không filter = số tổng bị Shopee + CrossBorder-0đ che — xem mục 2.2.)
- [ ] Thêm text card cảnh báo: "Model snapshot cũ không dùng cho trend retention — xem guide."

**Owner:** Data · Marketing (review dashboard)

---

## P4 — Chương trình Vận Hành

**Mục tiêu:** Các sáng kiến có thể lặp lại theo tuần/tháng; mở rộng tệp liên hệ được.

**Dependencies:** P1 done (automation export); P0 có kết quả thực tế để học.

**KPI:** Xem mục 8 của guide (one-time rate, M1 repeat, reactivation rate, US conversion).

### Todo

#### Kéo liên hệ Shopee về kênh nhà (ưu tiên cao nhất về cấu trúc)
- [ ] Thiết kế thẻ cảm ơn + QR → Zalo OA/website, kẹp trong mỗi đơn Shopee.
- [ ] Thiết kế ưu đãi cho đơn trực tiếp lần sau (incentive migrate kênh).
- [ ] KPI: % đơn Shopee có thẻ; số khách Shopee đăng ký Zalo OA; tỷ lệ migrate.

#### Test US gift-recipient (51 khách nóng 0–90 ngày)
- [ ] Lọc 51 khách `is_us_gift_recipient=true` & recency ≤ 90 ngày từ worklist P1.
- [ ] Soạn script riêng (thông điệp mục 6.3 của guide — KHÔNG dùng script win-back thông thường).
- [ ] Chạy test: gọi/Zalo, ghi phản hồi & chuyển đổi.
- [ ] Nếu ≥10% mua nội địa → mở rộng 180 khách ấm (91–365 ngày) → rồi bulk 589 nguội.

#### Second-order onboarding hệ thống
- [ ] Thiết kế luồng tự động: ngày 15–45 sau đơn #1 → Zalo nhắc + ưu đãi đơn #2.
- [ ] Kèm hướng dẫn dùng đúng (tăng cảm nhận hiệu quả → lý do tái mua thật).

#### Market-basket model (nâng AOV)
- [ ] Build model frequently-bought-together từ `fact_sales` (đúng grain dòng-đơn).
- [ ] Ứng dụng: bundle suggestion + cross-sell script cho CSKH.
- [ ] KPI: AOV/đơn lẻ tăng (hiện Shopee 932K, owned ~2–4M).

**Owner:** Marketing (thẻ QR, Zalo OA) · CSKH (test US, second-order) · Data (model market-basket)

---

## Phụ thuộc tổng thể

```
P0 (quick wins, ngay)
  └─→ P1 (data plumbing, 1–2 tuần)
        └─→ P2 (models, 2–4 tuần)
              └─→ P3 (dashboard, 3–5 tuần)
P0 (kết quả thực tế) ──→ P4 (vận hành, song song từ P1+)
```

## Rủi ro & lưu ý

- **PII:** worklist export (tên/SĐT) chỉ lưu ngoài git (Google Sheet / thư mục local không-tracked).
- **DuckDB:** `fact_orders` là view không resolve trên Windows — query trực tiếp parquet
  `app_data/data_lake/export/marts/rolling/`.
- **Model snapshot cũ:** không xóa, chỉ thêm cảnh báo — vẫn dùng cho thuộc tính khách (LTV, value_group).
- **US test:** 51 khách nóng là experiment — không scale trước khi có kết quả conversion thực tế.
- **Holdout:** mỗi luồng action phải giữ 10–20% không tác động để đo incremental (tránh nhận công
  đơn tự đến).
