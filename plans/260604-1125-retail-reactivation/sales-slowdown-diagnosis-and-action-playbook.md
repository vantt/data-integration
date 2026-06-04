---
title: "Chẩn đoán 'bán ế' & Playbook khai thác dữ liệu cho Marketing / CSKH / Sales"
status: living
last_modified: 2026-06-04
audience: [CEO, Marketing, Customer Care, Sales, Data]
domain_refs: [domains/customer.md, designs/customer_retention_lifecycle.md]
related: [guides/analytics_improvement_opportunities.md, mart_customer_action_queue, mart_customer_status_snapshot_monthly]
---

# Chẩn đoán "bán ế" & Playbook khai thác dữ liệu

> **Mục đích.** Trả lời: "Bán ế — khai thác data nào để gợi ý hành động cho Marketing/CSKH/Sales?"
> Tài liệu dựa trên **số thật** truy vấn từ warehouse 2026-06-04
> (nguồn: `fact_orders`, `dim_customers`, `mart_customer_action_queue`, retail, loại CANCELLED/DRAFT).

> **Lưu ý kỹ thuật:** `fact_orders` là view trỏ path Docker, không resolve trên Windows.
> Truy vấn chạy trực tiếp trên parquet: `app_data/data_lake/export/marts/rolling/`.

---

## 1. Tóm tắt điều hành

Có **hai** vấn đề chồng nhau. Cái cấp tính (#1) bị số tổng che lấp.

### 1.1 Cơn đau cấp tính — doanh thu lõi/B2B đang sụp, bị marketplace che

"Số đơn 2026 tốt" là **ảo giác** do trộn ba thứ khác nhau:

| Nguồn (2026) | Đơn | Bản chất |
|---|---|---|
| **Shopee** (Marketplace) | 319 | Kênh MỚI (0 đơn nửa đầu 2025). AOV chỉ 1.48M, rơi xuống 939K (T5). Đơn nhỏ lẻ tự động |
| **CrossBorder/US** | 78 | Doanh thu thật chỉ T1 (129M); T2–T5 = **0đ** → bản ghi giao vận, không phải bán hàng |
| **B2B + Social + Web** | ~130 | Việc kinh doanh **lõi** — đang teo nhanh |

**Nhu cầu lõi thật** (bỏ Shopee + CrossBorder-0đ): T1 **326M → T5 chỉ 14M** (sụp ~95%).
Riêng **B2B**: T1 **42 đơn/278M → T5 2 đơn/2M**. Nhóm sỉ ~5–10 khách/tháng gánh cả công ty
(rủi ro cô đặc) — họ ngừng mua là sụp ngay. **Đây chính là "ế" mà chủ cảm nhận.**

> Phải tách **kênh lõi vs marketplace** và **completed vs OPEN** thì mới thấy đúng (xem mục 2.2).

### 1.2 Bệnh mạn tính — xô thủng retention

- **71.8% khách lẻ chỉ mua 1 lần**; M1 repeat chỉ **3–17%** (lành mạnh phải 30–50%+ với hàng
  tiêu dùng lặp lại như Fine Japan/FG Care).
- Khách mới đổ vào nhưng không tích lũy → mỗi khi acquisition chững hoặc nhóm sỉ rút, doanh thu sụp
  vì **không có tệp trung thành đỡ phía sau**.

### 1.3 Trọng tâm đã chọn & tài sản ẩn

Chủ quyết định tập trung **khách lẻ (B2C)** ở giai đoạn này.

Tài sản ẩn quan trọng: **~824 người nhận quà từ Mỹ** (814 có SĐT Việt, contactable) là nhóm
đã cầm & dùng sản phẩm Fine Japan nhưng chưa từng tự trả tiền — tiềm năng chuyển đổi sang mua
nội địa nếu tiếp cận đúng thông điệp (xem mục 6).

---

## 2. Chẩn đoán bằng số thật

### 2.1 Xu hướng theo năm — tăng trưởng giả nhờ wholesale, rồi sụp

| Năm | Đơn hợp lệ | Doanh thu (tr.đ) | Số khách | Nhận định |
|---|---|---|---|---|
| 2021 | 556 | 255 | 411 | Nền bán lẻ nhỏ, AOV thấp |
| 2022 | 623 | 1.879 | 397 | Doanh thu nhảy 7×, AOV tăng mạnh |
| 2023 | 456 | 2.865 | **128** | **Khách sụt 397→128 nhưng DT đỉnh** → lệ thuộc sỉ/B2B |
| 2024 | 398 | 1.916 | 120 | Tiếp tục cô đặc vào ít khách lớn |
| 2025 | 387 | **1.095** | 196 | **DT thấp nhất kể từ 2021** — "ế" cảm nhận từ đây |
| 2026* | 656 | 2.394 | 367 | *5 tháng. Bùng nổ đơn & khách mới |

**Rủi ro cô đặc:** giai đoạn 2023–2024 doanh thu được kéo bởi ~120–128 khách (AOV 5–6M ⇒ sỉ ẩn).
Khi nhóm này giảm mua → 2025 sụp. Doanh thu phụ thuộc số ít khách lớn, không được nâng đỡ bởi tệp
lẻ rộng.

> Taxonomy `discount_type = negotiated_deep` (giảm ≥40%) đang đánh dấu **sỉ trá hình** lẫn trong
> tệp RETAIL. Cần tách & chính thức hóa kênh sỉ.

### 2.2 Xu hướng theo tháng — bóc tách kênh (tại sao "số đơn tốt" là ảo giác)

**Bảng tổng tháng (all channels):**

| Tháng | Đơn | DT (tr) | Người mua | Mới | Quay lại | AOV (ng.đ) |
|---|---|---|---|---|---|---|
| 2025-04 | 11 | 27 | 8 | 1 | 7 | 2.474 |
| 2025-05 | 8 | 20 | 7 | 3 | 4 | 2.443 | ← đáy gần-chết |
| 2025-07 | 65 | 76 | 53 | 34 | 19 | 1.163 | ← phục hồi |
| 2025-12 | 56 | 107 | 41 | 19 | 22 | 1.910 |
| 2026-01 | 144 | 428 | 103 | **77** | 26 | 2.973 |
| 2026-03 | 151 | 382 | 108 | **70** | 38 | 2.527 |
| 2026-05 | 135 | 306 | 98 | **71** | 27 | 2.264 |

Mỗi tháng 2026 có ~70 khách mới nhưng chỉ ~26–42 quay lại. Acquisition đang gánh toàn bộ;
retention gần bằng 0 hiệu lực.

**Bóc tách kênh 2026 (completed):**

| channel_format | platform | Đơn | DT (tr) | AOV (ng.đ) | Ghi chú |
|---|---|---|---|---|---|
| Marketplace | **Shopee** | 319 | 471 | 1.478 → **939 (T5)** | Kênh mới, đơn nhỏ, đang co |
| CrossBorder | US | 78 | 129 (chỉ T1) | T2–T5 = **0** | Bản ghi giao vận, không phải sales |
| **B2B** | — | 85↓ | — | 6.000–10.000 | **Cỗ máy thật — đang chết** |
| Social/Web | — | ~40 | — | 3.000–4.000 | Nhỏ |

**B2B theo tháng (completed):** T1 42đơn/278tr → T2 15/137 → T3 16/101 → T4 10/103 → **T5 2/2**.

**Nhu cầu lõi** (loại Marketplace + CrossBorder-0đ + System): T1 **326tr** → T3 261 → T4 209 →
**T5 14tr**. Lõi sụp ~95%; số tổng được đỡ bởi Shopee nhỏ lẻ + giao vận 0đ.

> **Caveat cần kiểm chứng:** (1) **Mùa Tết** — T1 cao có thể do đại lý gom hàng trước Tết (~17/2/2026),
> chững sau Tết bình thường; nhưng tụt còn 2 đơn B2B thì dốc hơn mức thường. (2) **Đơn OPEN** —
> T5–T6 còn đơn chưa completed ⇒ tháng gần nhất có thể bị đếm thiếu; nhưng đà giảm B2B đã rõ từ T1→T4.

### 2.3 Cohort retention — bằng chứng của xô thủng

% khách cohort (tháng mua đầu) quay lại ở M+n:

| Cohort | Cỡ cohort | M+1 | M+2 | M+3 | Tích lũy 6 tháng |
|---|---|---|---|---|---|
| 2025-12 | 19 | 5% | 5% | 5% | 26% |
| 2026-01 | 77 | 14% | 16% | 13% | **31%** |
| 2026-02 | 35 | 17% | 11% | 3% | 23% |
| 2026-03 | 70 | 10% | 10% | 1% | 17% |
| 2026-04 | 46 | 9% | 2% | 0% | 11% |

**M+1 chỉ 3–17%.** Benchmark hàng tiêu dùng lặp lại: 30–50%+. Chênh lệch này là cơ hội doanh thu
lớn nhất đang bị bỏ phí.

**Toàn tệp:** trong **1.386** khách lẻ từng mua, **995 (71.8%) chỉ mua đúng 1 lần**; chỉ 28.2%
từng mua lần 2.

### 2.4 Retention waterfall point-in-time — và cảnh báo model đang sai

Đếm đúng "tại cuối mỗi tháng" có bao nhiêu khách ACTIVE/AT_RISK/CHURNED, tính từ `fact_orders`:

| Cuối tháng | Tệp lũy kế | ACTIVE | AT_RISK | CHURNED |
|---|---|---|---|---|
| 2025-05 | 980 | **7** | 18 | 955 |
| 2025-06 | 982 | **8** | 10 | 964 |
| 2026-01 | 1.152 | 103 | 48 | 1.001 |
| 2026-05 | 1.374 | 98 | 150 | 1.126 |

**`mart_customer_status_snapshot_monthly` đang sai cho mục đích này.** Model dùng
`dim_customers.last_order_date` (lần mua gần nhất hiện tại), không phải point-in-time. Hệ quả:
**mọi khách còn active hôm nay bị đóng dấu ACTIVE ngược về quá khứ.**

| Cuối tháng | ACTIVE (đúng, từ fact_orders) | ACTIVE (model hiện tại) |
|---|---|---|
| 2025-05 | **7** | 71 |
| 2025-06 | **8** | 71 |
| 2026-05 | 98 | 124 |

Model thổi phồng ACTIVE gần **9×** đúng ngay tháng đáy, xóa sạch sự kiện gần-chết 2025 khỏi
dashboard. Bất kỳ biểu đồ retention nào build trên bảng này sẽ **ru ngủ** người xem.
**Khuyến nghị: thay bằng waterfall point-in-time (SQL ở mục 3).**

Tới 2026-05 có **~1.126 khách CHURNED** (LTV lũy kế ~4.015 tr.đ) — hậu quả của xô thủng
và cũng là **mỏ reactivation** khổng lồ.

---

## 3. Phương pháp Retention-Waterfall Diagnostic

### 3.1 Tại sao phải tự dựng lại (không dùng model cũ)

`mart_customer_status_snapshot_monthly` dùng `last_order_date` hiện tại ⇒ thiên lệch
"survivorship": khách còn sống hôm nay làm đẹp mọi tháng quá khứ, giấu churn. Bản đúng phải tính
trạng thái **point-in-time**: tại mỗi cuối tháng, chỉ nhìn đơn có ngày `<=` mốc đó.

### 3.2 SQL chẩn đoán (DuckDB — chạy trực tiếp trên parquet)

```sql
-- Point-in-time retention waterfall (retail). DuckDB. Set TimeZone='Asia/Ho_Chi_Minh'.
-- Lưu ý: 'asof' là từ khóa DuckDB -> đặt tên CTE khác; tránh alias 'month'.
WITH vo AS (   -- valid orders, retail thật
  SELECT o.customer_key, o.order_timestamp::date AS d
  FROM fact_orders o
  JOIN dim_customers c USING(customer_key)
  WHERE o.status NOT IN ('CANCELLED','DRAFT')
    AND c.customer_type = 'RETAIL'
    AND c.customer_id <> 'Unknown'
),
months AS (    -- 14 mốc cuối tháng gần nhất (đã đóng kỳ)
  SELECT (date_trunc('month', gs) + INTERVAL 1 MONTH - INTERVAL 1 DAY)::date AS me
  FROM unnest(generate_series(
         date_trunc('month', current_date) - INTERVAL 14 MONTH,
         date_trunc('month', current_date) - INTERVAL 1  MONTH,
         INTERVAL 1 MONTH)) AS t(gs)
),
pit AS (       -- as-of: lần mua gần nhất TÍNH ĐẾN cuối mỗi tháng
  SELECT m.me, v.customer_key, MAX(v.d) AS last_d
  FROM months m JOIN vo v ON v.d <= m.me
  GROUP BY 1, 2
)
SELECT strftime(me,'%Y-%m') AS ym,
  COUNT(*) AS base,
  COUNT(*) FILTER (WHERE date_diff('day',last_d,me) <= 30)             AS active,
  COUNT(*) FILTER (WHERE date_diff('day',last_d,me) BETWEEN 31 AND 90) AS at_risk,
  COUNT(*) FILTER (WHERE date_diff('day',last_d,me) > 90)              AS churned
FROM pit GROUP BY me ORDER BY me;
```

**Cohort retention** (mục 2.3) và **one-time rate** dùng `MIN(order_date)` làm cohort,
đếm distinct customer theo `date_diff('month', cohort, order_month)`.

### 3.3 Đề xuất productionize

1. **Thêm model `mart_retention_waterfall_monthly`** (point-in-time từ `fact_orders`) — grain
   `(snapshot_month, status)` + biến thể có `value_group`, `product_affinity`, `channel_preference`
   để bóc tách churn theo phân khúc. Giữ model snapshot cũ cho thuộc tính khách, **nhưng ngừng dùng
   cột `status` cho biểu đồ xu hướng** — gắn cảnh báo vào `schema.yml`.
2. **Dashboard "Retention Health" (Metabase):** (a) đường ACTIVE/AT_RISK/CHURNED point-in-time;
   (b) heatmap cohort M0–M6; (c) thẻ số one-time-rate & M1-repeat-rate; (d) đường new-vs-returning;
   (e) bộ lọc kênh lõi/marketplace + completed-only.
3. **Mục tiêu:** M1 repeat **3–17% → ≥25%** trong 2 quý; one-time-rate **72% → <60%**.

---

## 4. Tệp khách lẻ liên hệ được — phân khúc & rào cản

### 4.1 Phân khúc tệp 1.082 khách có SĐT

| Phân khúc | Số khách | LTV (tr) | Đặc điểm | Cách tiếp cận |
|---|---|---|---|---|
| **Active** (≤30 ngày) | 32 | 2.973 | AOV cao 2.661K, đang khỏe | Giữ ấm, upsell |
| **At Risk** (31–90 ngày) | 64 | 897 | Đang nguội, cứu kịp | High-touch |
| **Churned** (>90 ngày) | 986 | 2.299 | 91% tệp, TB nguội ~3.4 năm | Tách nóng/lạnh |
| — OVERDUE (lặp lại quá hạn) | 166 | 2.199 | Từng mua đều (~82 ngày/lần) rồi biến mất | Win-back ưu tiên |
| — one-timer | 844 | 630 | Mua đúng 1 lần, đa số rất cũ | Bulk + second-order |

**Phân bổ công sức:** ~120 khách giá-trị/đúng-hạn (action queue, **~1.3 tỷ value at stake**)
→ high-touch (gọi/Zalo cá nhân); ~700+ khách nguội → bulk low-touch (Zalo blast).
Đừng gọi tay khách nguội 3 năm.

> Brand chủ lực **Fine Japan (739 khách)** — collagen/supplement là hàng tiêu dùng tái mua tự nhiên.
> Đòn bẩy mạnh nhất: nhắc **đúng lúc hết hàng** theo chu kỳ cá nhân (`avg_days_between_orders`).

### 4.2 Tín hiệu mua tiếp (`next_purchase_signal`)

Bảng `mart_customer_action_queue` đã có cột này; kết hợp `predicted_next_purchase_date` để hẹn giờ
tiếp cận cá nhân, không blast đại trà.

### 4.3 Retention theo kênh acquisition

| Acquired via | Khách | % mua lại | Đơn/đời | Liên hệ được |
|---|---|---|---|---|
| Retail (offline) | 26 | **38.5%** | 3.96 | 81% |
| Web | 24 | **33.3%** | 3.79 | 96% |
| **Shopee** | 246 | 22.4% | 1.47 | **chỉ 10%** |
| Social | 59 | 11.9% | 1.20 | 98% |

Kênh nhà giữ chân tốt hơn Shopee **2–3×**.

### 4.4 Rào cản cấu trúc — Shopee "thuê" không "sở hữu"

246 khách Shopee, chỉ 54 mua lần 2 — **52/54 lại trên Shopee, chỉ 2 chuyển kênh nhà**. Và
**chỉ 10% có SĐT** ⇒ toàn bộ cỗ máy CSKH/`action_queue` **vô dụng với 90% tệp lẻ lớn nhất**.

> **LƯU Ý QUAN TRỌNG:** 823/1.082 ≈ 76% tệp "khách lẻ liên hệ được" là **người nhận quà US** —
> nhóm này chưa từng tự trả tiền mua, cần thông điệp khác hoàn toàn so với win-back thông thường
> (xem mục 6).

### 4.5 Data cần để vận hành tệp lẻ

| Cần | Trạng thái | Việc |
|---|---|---|
| `first_order_channel` (kênh acquisition) | chưa surface | suy từ `fact_orders` (arg_min theo order_timestamp) → cohort & retention theo kênh |
| `is_contactable` (có SĐT hợp lệ) | tính được từ `dim_customers.phone` | thêm cột để lọc tệp chạy được CSKH |
| `is_us_gift_recipient` | chưa có | thêm cờ để tách luồng US khỏi win-back thông thường |
| Shopee→owned migration tracking | chưa có | field nguồn đăng ký Zalo OA / mã voucher direct-first |
| Market-basket (mua kèm) | chưa có | model mới từ `fact_sales` |

---

## 5. Kế hoạch hành động: làm khách liên hệ được mua lại

> Tệp đích: **1.082 khách lẻ có SĐT đã từng mua** (lưu ý 76% là người nhận quà US — xem mục 6
> để tách luồng). Số liệu thật 2026-06-04.

### 5.1 Bốn nguyên tắc bất biến

1. **Timing theo chu kỳ cá nhân, không blast đồng loạt.** Dùng `predicted_next_purchase_date` /
   `avg_days_between_orders` → nhắc khi họ sắp hết hàng.
2. **Mức chạm theo giá trị.** VIP/Gold → gọi điện người thật. Silver → Zalo cá nhân. Bronze/nguội → blast.
3. **Offer theo độ nhạy giảm giá** (`discount_sensitivity`). FULL_PRICE/ON_TRACK → đừng tặng voucher
   (họ mua đủ giá), tặng quà/sample/ưu tiên. Chỉ dùng voucher cho win-back/nhạy KM.
4. **Luôn hỏi "vì sao ngừng".** Mỗi cuộc win-back ghi lý do → xây bản đồ nguyên nhân bỏ để chữa gốc.

### 5.2 Năm luồng hành động

**Luồng 1 — CALL_NOW: VIP/Gold đang At-Risk** · *6 khách · ~56tr* · **Owner: Sales lead**
- Trigger: `value_group∈(VIP,GOLD)` & `customer_status='At Risk'`. Gọi điện trong 48h.
- Script: hỏi thăm cá nhân → "bên em vừa về lô [brand] mới / có ưu đãi cho khách thân thiết" →
  chốt đơn hoặc hẹn lại. KHÔNG mở đầu bằng giảm giá.
- KPI: 100% được gọi trong tuần; ≥40% đặt lại/hẹn.

**Luồng 2 — WIN_BACK: khách giá trị đã churned** · *35 khách · ~911tr* · **Owner: CSKH + Sales lead**
- Trigger: `value_group∈(VIP,GOLD,SILVER)` & churned. Gọi/Zalo cá nhân, kèm micro-survey "vì sao ngừng".
- Offer: voucher comeback có thời hạn (7–10 ngày) + freeship; ưu tiên SKU theo `product_affinity`.
- Script Zalo: *"Chào anh/chị [tên], [shop] thấy lâu rồi chưa phục vụ mình. Em gửi ưu đãi quay lại
  [X%] cho [Fine Japan ...] tới hết [ngày]. Tiện em hỏi: lần trước mình ngưng mua vì lý do gì ạ?"*
- KPI: ≥50% tiếp cận có phản hồi; ≥15% mua lại trong 30 ngày; thu ≥20 lý-do-bỏ.

**Luồng 3 — REORDER_NUDGE: OVERDUE** · *31 khách action-queue (166 toàn tệp) · ~344tr* · **Owner: CSKH**
- Trigger: `next_purchase_signal='OVERDUE'`. Nhắc theo chu kỳ cá nhân.
- Script: *"Anh/chị [tên] ơi, [sản phẩm] mình hay dùng chắc sắp hết rồi. Em giữ hàng + giao nhanh
  giúp mình nhé?"* (nhắc tiện lợi, không cần giảm giá).
- KPI: M1 reorder ≥25%.

**Luồng 4 — SECOND_ORDER: one-timer mới** · *16 nóng (15–45 ngày) + 25 (46–90) · ~2tr* · **Owner: CSKH**
- Trigger: `total_orders_count=1` & recency 15–45 ngày. Cú hích chuyển 1-lần → 2-lần.
- Offer: ưu đãi đơn #2 nhỏ + hướng dẫn dùng đúng (tăng cảm nhận hiệu quả → lý do tái mua thật).
- KPI: tỷ lệ one-timer→repeat tăng. Pool nhỏ vì acquisition chủ yếu Shopee không liên hệ được →
  ưu tiên song song nước đi "bắt liên hệ Shopee" để nuôi pool này.

**Luồng 5 — BULK win-back nguội** · *~700+ one-timer/churned cũ* · **Owner: Marketing**
- Kênh: Zalo OA broadcast/SMS, theo đợt. Low-touch, chi phí thấp.
- Nội dung: chiến dịch theo mùa/brand (Fine Japan) + voucher comeback, phân nhóm theo `product_affinity`.
- KPI: response ≥3–5%; đo doanh thu/đợt.

### 5.3 Lịch vận hành tuần

| Thứ | Việc | Ai |
|---|---|---|
| T2 | Export worklist tuần (Luồng 1–4, lọc có SĐT) từ `mart_customer_action_queue` → Google Sheet | Data/CSKH |
| T2–T4 | Gọi Luồng 1 (CALL_NOW) + Luồng 2 (WIN_BACK cao giá trị) | Sales lead |
| T3–T6 | Zalo Luồng 2 (còn lại) + Luồng 3 (REORDER) + Luồng 4 (SECOND_ORDER) | CSKH |
| T5 | 1 đợt Bulk (Luồng 5) theo brand/mùa | Marketing |
| T7 | Cập nhật kết quả (đặt lại / lý do bỏ) vào Sheet → review | CSKH lead |

### 5.4 Offer matrix

| | ON_TRACK / Active | At-Risk | Churned/nguội |
|---|---|---|---|
| **VIP/Gold** | Quà tặng, ưu tiên hàng mới | Gọi tay + quà | Gọi + voucher comeback mạnh |
| **Silver** | Sample kèm đơn | Zalo + ưu đãi nhẹ | Voucher comeback |
| **Bronze/one-timer** | Nhắc tiện lợi | Ưu đãi đơn #2 | Bulk voucher (Luồng 5) |

### 5.5 Đo lường (bắt buộc có nhóm chứng)

- **Holdout 10–20%** mỗi luồng (không tác động) để đo incremental — tránh nhận công cho đơn tự đến.
- KPI tổng: M1 reorder tệp owned **3–17% → ≥25%** (2 quý); reactivation rate win-back ≥15%/30 ngày;
  doanh thu reactivation/tháng; số lý-do-bỏ thu được.

### 5.6 Tuần 1 — checklist khởi động (0-build)

- [ ] Export ~120 khách high-touch (Luồng 1–4, có SĐT) ra Sheet (cảnh báo: chứa PII — không commit vào git).
- [ ] Soạn 4 script Zalo mẫu + 3 mức voucher (offer matrix).
- [ ] Sales lead gọi 6 CALL_NOW + 10 WIN_BACK giá trị nhất (T2–T4).
- [ ] CSKH Zalo 31 REORDER + 16 SECOND_ORDER nóng.
- [ ] Ghi outcome + lý-do-bỏ vào Sheet; review T7.

---

## 6. Đơn US — mỏ người nhận tại Việt Nam

### 6.1 Bản chất luồng kiều bào

Luồng **người MUA ở Mỹ, người NHẬN ở VN**. Trong data, `customer_key` của đơn US = người nhận VN.
Địa chỉ ship & bill đều là địa chỉ VN thật (Đà Nẵng, TP HCM, Đồng Nai...).

- **824 người nhận VN**; 823 `customer_type=RETAIL`; **814 có SĐT Việt (0/+84), 0 SĐT Mỹ → contactable**.
- Họ đã cầm & dùng sản phẩm (chủ yếu Fine Japan) nhưng **chưa bao giờ tự trả tiền** (người nhà ở Mỹ trả).
- Hầu như **không mua nội địa**: 816 khách/1.188 đơn CrossBorder; chỉ ~10–15 người từng mua qua kênh VN
  (Web 3, Retail 3, Social 3, Direct 1).
- **823 người này ≈ 76% của tệp "1.082 khách lẻ liên hệ được"** → tệp đó thực chất phần lớn là
  người nhận quà US, không phải khách đã từng chủ động mua.

### 6.2 Phân tầng độ ấm (theo recency)

| Nhóm | Recency | Số khách | Ghi chú |
|---|---|---|---|
| Nóng nhất | 0–90 ngày | **51** | Đang hoặc vừa nhận hàng gần đây |
| Ấm | 91–365 ngày | 129 | Trong vòng 1 năm |
| Nguội | 1–2 năm | 55 | |
| Rất nguội | >2 năm | **589** | Yield thấp, bulk cuối cùng |

→ **~180 khách trong vòng 1 năm** là tệp ấm đáng làm. 51 nóng là điểm test đầu tiên.

### 6.3 Thông điệp tiếp cận

> *"Anh/chị vừa nhận [Fine Japan] do người nhà gửi từ Mỹ. Bên em là nhà phân phối chính hãng tại
> VN — cần dùng tiếp thì đặt trực tiếp, giao tận nơi, giá nội địa, khỏi chờ gửi từ Mỹ."*

Góc bonus: (1) re-gift/giới thiệu cho người quen; (2) kéo người mua ở Mỹ đặt trực tiếp từ VN
(rẻ hơn cross-border) — phụ, thứ yếu.

### 6.4 Rủi ro và cảnh báo (TEST chưa kiểm chứng)

| Rủi ro | Mô tả |
|---|---|
| Chưa từng trả tiền | Không biết giá, không có thói quen mua nội địa |
| Bối cảnh quà biếu | Người nhận có thể lớn tuổi, không rành online |
| Tế nhị/quyền riêng tư | Gọi lạnh cho người chưa từng là khách trực tiếp |
| 589 khách >2 năm | Yield rất thấp — bulk cuối cùng, không ưu tiên |

### 6.5 Khuyến nghị triển khai

1. **TEST nhỏ: 51 khách nóng (0–90 ngày)** — đo phản hồi & tỷ lệ chuyển đổi sang mua nội địa.
2. Nếu ≥10% mua nội địa → mở rộng 180 ấm → rồi bulk 589 nguội.
3. **Thêm cờ `is_us_gift_recipient`** vào `dim_customers` để `mart_customer_action_queue` tách
   luồng này riêng (thông điệp khác, không dùng win-back thông thường).

---

## 7. Bản đồ khai thác dữ liệu theo đội

Bối cảnh: brand hàng tiêu dùng lặp lại ⇒ nhịp mua lại là vàng. Cỗ máy
`avg_days_between_orders` + `next_purchase_signal` + `predicted_next_purchase_date` đang bị dùng thiếu.

### 7.1 Đã có data — triển khai trong vài ngày

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

### 7.2 Có trong raw nhưng chưa surface — build nhỏ

| Data | Đang ở đâu | Mở khóa |
|---|---|---|
| **FB Messenger** (chat-to-order, response time) | models đã viết nhưng `enabled=false` | Social-commerce VN: tốc độ rep = tỷ lệ chốt. Bật pipeline + tính FRT/AHT |
| `debt` (công nợ khách) | `std_customers`, chưa surface | Khách sỉ chạm trần nợ → không đặt thêm → đè doanh thu |
| `tags` sản phẩm | `dim_products.tags` (JSON chưa parse) | Merchandising/affinity theo công dụng, dòng da |
| `source_id` đơn | `fact_orders`, mới dùng làm channel | Proxy thô cho nguồn acquisition |
| `status` khách (Sapo) | `stg_sapo_customers`, chưa surface | Lọc active/inactive thật |

### 7.3 Chưa có — build lớn, ROI cao

1. **Nguồn acquisition / first-touch** — `acquisition_source` luôn NULL. Quick-win: suy
   `first_order_channel` từ đơn đầu mỗi khách (`fact_orders`) → cohort-theo-nguồn ngay.
2. **Market-basket** — `fact_sales` đúng grain nhưng chưa có model frequently-bought-together
   → bundle + upsell (đòn bẩy AOV).
3. **ROAS cấp chiến dịch** — `fact_fb_ads_insights_daily` disabled.
4. **Phễu trước mua** (session, add-to-cart) — chỉ có đơn, không thấy nơi rớt trước checkout.
5. **Churn-propensity / CLV dự báo** — hiện chỉ rule-based.
6. **NPS / voice-of-customer** — chưa thu gì.

---

## 8. Đo lường & KPI bắc cầu

**Định nghĩa "hết ế":**

| KPI | Hiện tại | Mục tiêu | Thời hạn |
|---|---|---|---|
| One-time rate | **72%** | < 60% | 2 quý |
| M1 repeat rate | **3–17%** | ≥ 25% | 2 quý |
| Returning buyers/tháng | ~30 | ≥ 60 | 2 quý |
| ACTIVE point-in-time (cuối tháng) | ~98 | tăng đều | theo dõi liên tục |
| Reactivation rate win-back | — | ≥ 15%/30 ngày | per campaign |
| US gift → nội địa conversion | 0 (test chưa có) | ≥ 10% → mở rộng | sau P4 test |

**Đo đúng:** luôn tách kênh lõi vs marketplace; dùng completed-only; waterfall point-in-time
(không dùng `mart_customer_status_snapshot_monthly` cho xu hướng).

---

## 9. Câu hỏi chưa giải đáp

1. **6.025 khách lẻ "New/Unknown" (LTV=0)** trong `dim_customers` là gì? Lead/đăng ký chưa mua,
   hay đơn COD hủy? Cần xác minh trước khi coi là tệp reactivation.
2. "Ế" mà chủ cảm nhận là **doanh thu/biên lợi nhuận** hay **số đơn**? Data cho thấy lượng 2026
   tốt — cần xác nhận góc nhìn để chọn đúng KPI.
3. Nhóm wholesale ẩn (`negotiated_deep`) chiếm bao nhiêu % doanh thu 2023–2025? (cần chạy thêm).
4. Có ngân sách/nhân sự CSKH để **chạy call-list hằng ngày** không? Nếu không, ưu tiên tự động hóa
   nhắc qua Zalo/SMS theo `predicted_next_purchase_date`.
5. **Người nhận quà US** (mục 6): họ có biết sản phẩm mình nhận là Fine Japan / nhà phân phối tại
   VN không? Người gửi (ở Mỹ) có thể là "người giới thiệu tự nhiên" không?
6. Tỷ lệ chuyển đổi US gift → mua nội địa thực sự ra sao? (chưa có data — cần test 51 nóng trước).
7. Bối cảnh đơn US: người nhận thường được báo trước hay nhận bất ngờ? (ảnh hưởng cách cold-contact).

---

*Kế hoạch triển khai chi tiết (phase P0–P4, todo, owner, KPI):*
[`plan.md`](./plan.md)
