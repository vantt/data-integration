---
title: "OPP-004 - Data Backlog"
stage: 4
status: idea
source: ../archive/2026-06-04-original-sales-slowdown-playbook.md
---

# OPP-004 - Data Backlog

**Registry:** [OPP-004](../REGISTRY.md#opp-004)

> Bối cảnh: brand hàng tiêu dùng lặp lại ⇒ nhịp mua lại là vàng. Cỗ máy
> `avg_days_between_orders` + `next_purchase_signal` + `predicted_next_purchase_date` đang bị dùng thiếu.
>
> Nguồn: §7 (7.1/7.2/7.3), §3.3, §4.5 — playbook chẩn đoán.

---

## ⭐ Nhóm 0 — fresh-scan 2026-06-13 (cơ hội mới, ưu tiên cao)

> Nguồn: [../02-understand/FIND-007-fresh-scan-data-market.md](../02-understand/FIND-007-fresh-scan-data-market.md).

**O1 — Lái acquisition khỏi SKU ngõ-cụt sang SKU gateway [đòn bẩy gốc rễ].**
Entry SKU lớn nhất = UV Care Plus (400 khách, repeat 10%, LTV 380K) + Kids Calcium + Metabo Green Tea (~900 khách, 10-14%).
Gateway = Cordyceps/Fucoidan/Collagen (29-37%, LTV 3-15tr) + Đông trùng nước/Reishi (gateway ẩn, 31-50%, undermarketed).
→ Dời ngân sách quảng cáo + ưu tiên listing/bundle sang nhóm gateway. Ước **+450tr LTV**. Trước khi cắt UV Care: kiểm cross-sell path (Q13 — loss-leader có chủ đích?).

**O2 — Bắt liên hệ Shopee tại điểm bán → Zalo OA [đòn bẩy cấu trúc cao nhất].**
Shopee = 70% khách lẻ nhưng 67% vô danh (chỉ 32.6% liên-hệ-được) = doanh thu chết, không reactivate được.
→ Thẻ cảm ơn + QR → Zalo OA kẹp mỗi đơn Shopee/CrossBorder. KPI: % đơn có thẻ, số đăng ký Zalo OA. (đã có ở P4 — nâng lên ưu tiên cấu trúc #1).

**O3 — Lập Zalo OA verified [hạ tầng nền — làm TRƯỚC mọi automation].**
Kênh retention #1 VN (open 60-90% vs email 15-25%). Không có OA thì onboarding/nhắc/win-back đều vô nghĩa. Prerequisite cho O2, P3, P4.

**O4 — Calibrate timing theo chu kỳ thật.** Chu kỳ tái mua median 63 ngày, **cụm lớn nhất ~30 ngày**, kế ~45 ngày.
→ Subscribe&Save có nhịp **30 ngày** (không chỉ 45); nhắc tái mua gửi **ngày ~20-23**; gửi tin **Thứ 2/Thứ 5 ~9h sáng**.

**O5 — Census mép cứu-được tuần này.** 15 khách contactable ngừng mua 31-90 ngày = 80tr LTV (cửa sổ đang đóng). Action queue refresh 2026-06-13 = **116 khách / 1.17 tỷ**. → gọi ngay (đã đưa vào P0).

**O6 — Pocket địa lý chưa khai thác [offline].** HCM 51.7% doanh thu (rủi ro tập trung). Tỉnh nhỏ repeat cao bất ngờ, 0 offline: Bà Rịa-Vũng Tàu 33%, Tây Nguyên (Đắk Lắk/Gia Lai 26-32%), cụm ĐBSCL (An Giang/Vĩnh Long/Bến Tre 25-27%), Đà Nẵng 25%. → thử event/POS hub ở Cần Thơ/Đà Nẵng. Hà Nội repeat dị thường 12.7% — drill kênh.

**O7 — Thử kênh nhà thuốc chuỗi (Long Châu/An Khang).** Kênh niềm tin #1 cho TPCN người già; brand có thể đang vắng mặt (Q14). Đối thủ Orihiro có showroom vật lý.

> **Bổ sung từ audit kênh nhà (crawl 2 site D2C — fresh-scan §I):**

**O8 — Hợp nhất giá + dẹp xung đột kênh nhà [làm ngay, gần như free].** 2 site của mình (finejapanvietnam + jpcshop) lệch giá tới 38% cùng SKU + tự cắt giá nhau. → 1 bảng giá chuẩn, phân vai 2 site rõ (đừng để cạnh tranh nội bộ).

**O9 — Nạp đủ catalog vào kênh nhà.** Site D2C chỉ 8-15 SKU mono-brand trong khi bán hàng trăm SKU đa-brand trên sàn → kênh LTV cao nhất bị bỏ đói. Đưa full catalog (đặc biệt nhóm gateway) lên web/Zalo OA để giữ khách ở kênh nhà thay vì đẩy về sàn.

**O10 — Gift bundle cho kênh nhà [khớp O6/L5].** Cả 2 site KHÔNG có gift set/hộp quà/liệu trình. Xây bundle quà biếu bố mẹ cho Tết + 8-3 + T11.

**O11 — Thêm timeline/liệu trình + bằng chứng vào trang sản phẩm [giải Q17].** SP khớp/xương (repeat 15%) claim "điều trị" nhưng không nói "thấy hiệu quả sau X tuần, dùng đủ liệu trình Y". Thêm kỳ vọng thực tế + testimonial cùng độ tuổi + tem QR chống giả → giảm churn do vỡ kỳ vọng.

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
  > **🔻 Chốt fresh-scan 2026-06-13:** data CHƯA thấy "discount phá loyalty" (nhóm discount sâu repeat ≥ full-price,
  > nhưng sample nhỏ + lẫn B2B/bulk → cần A/B test). Rò lãi THẬT = **45 khách >25% discount nhận 504tr discount trên
  > 410tr revenue (âm gross)**. → đổi trọng tâm: chặn âm-gross deep-discount, không phải sợ "phụ thuộc KM".
- Ghép `mart_inventory_health.is_dead_stock`/`is_slow_mover` với `product_affinity` → campaign
  clearance đúng nhóm mê brand.
- Dùng `avg_days_between_orders` hẹn giờ gửi tin theo chu kỳ cá nhân.

**Sales:**
- Ghép top SKU (`mart_sku_economics_monthly.revenue_share_pct`) với `mart_inventory_health.is_oos` →
  danh sách "phải nhập gấp". OOS trên hero-SKU gây ế trực tiếp.
- `fact_targets` có chỉ tiêu nhưng **actual-vs-target chưa tính** → dựng variance theo kênh/team/tháng.
- Chính thức hóa sỉ ẩn: lọc `discount_type = negotiated_deep` → kênh sỉ có chính sách.

**Plan liên kết:** [PLAN-001-b2c-reactivation-phases](../05-action-plans/PLAN-001-b2c-reactivation-phases.md) — P1 (chạy tay call-list) → P2 (worklist Sheet) → P3 (automation nhắc).

---

## ✅ ĐÃ FIX 2026-06-10: Bug margin mart_sku_economics_monthly

> Phát hiện + fix 2026-06-10 — nguồn: [../02-understand/FIND-005-product-performance-assessment.md](../02-understand/FIND-005-product-performance-assessment.md).

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

→ Xem chi tiết: [cashflow-collection-ar](../02-understand/INV-001-cashflow-collection-ar.md)

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

> Nguồn: [../02-understand/FIND-005-product-performance-assessment.md](../02-understand/FIND-005-product-performance-assessment.md) — 4-agent assessment 2026-06-10.

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

**Plan liên kết:** [PLAN-001-b2c-reactivation-phases](../05-action-plans/PLAN-001-b2c-reactivation-phases.md) — P2 (`is_contactable`, `is_us_gift_recipient`) → P3 (Shopee→owned tracking).

---

## Nhóm 3 — Build lớn, ROI cao

> Nguồn: §7.3 + §3.3. Effort lớn hơn nhưng tạo nền hạ tầng analytics dài hạn.

### Product performance — Tier 2 (HOÃN, chỉ nếu dashboard cần)

> Nguồn: [../02-understand/FIND-005-product-performance-assessment.md](../02-understand/FIND-005-product-performance-assessment.md) — 4-agent assessment 2026-06-10.

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
   → Targets chính thức tại [../06-execute/README.md#kpi-lagging](../06-execute/README.md#kpi-lagging)

**Plan liên kết:** [PLAN-001-b2c-reactivation-phases](../05-action-plans/PLAN-001-b2c-reactivation-phases.md) — P3 (`mart_retention_waterfall_monthly`) → P4 (dashboard Retention Health + automation).
