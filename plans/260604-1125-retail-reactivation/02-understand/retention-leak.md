---
title: "Xô thủng retention — bệnh mạn tính"
stage: 2
status: resolved
source: ../archive/2026-06-04-original-sales-slowdown-playbook.md
---

# Xô thủng retention — bệnh mạn tính

## 1.2 Xô thủng retention

- **71.8% khách lẻ chỉ mua 1 lần**; M1 repeat chỉ **3–17%** (lành mạnh phải 30–50%+ với hàng
  tiêu dùng lặp lại như Fine Japan/FG Care).
- Khách mới đổ vào nhưng không tích lũy → mỗi khi acquisition chững hoặc nhóm sỉ rút, doanh thu sụp
  vì **không có tệp trung thành đỡ phía sau**.

---

## 2.3 Cohort retention — bằng chứng của xô thủng

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

> **⭐ Reframe fresh-scan 2026-06-13 — one-time phần lớn do MIX SẢN PHẨM-CỔNG-VÀO, không chỉ do thiếu nhắc.**
> Entry SKU lớn nhất = UV Care/Kids/Metabo (repeat 10-14%, ngõ cụt) kéo tụt toàn brand; cordyceps/collagen/fucoidan
> entry → 29-37%. Cohort 2025-2026 còn bị **right-censored** (chưa đủ thời gian repeat) nên repeat thật của cohort mới
> có thể cao hơn bảng 2.3. → sửa cửa-vào trước khi xây thêm reminder. [fresh-scan §B](./fresh-scan-260613-data-market.md#b-đòn-bẩy-mới-lớn-nhất--sản-phẩm-cổng-vào-entry-sku--retention)

---

## 2.4 Retention waterfall point-in-time — và cảnh báo model đang sai

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

> **Việc build data** (model waterfall, dashboard Retention Health) → [04-opportunities/data-backlog](../04-opportunities/data-backlog.md).
