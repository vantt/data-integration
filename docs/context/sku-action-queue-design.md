# SKU-Level Action Queue — Design & Calculation Reference

> **Scope:** Data Team, CRM Product
> **Updated:** 2026-06-29
> **Status:** Design — pre-implementation

---

## 1. Vấn đề với queue cũ

`mart_customer_action_queue` hiện tại dùng `avg_days_between_orders` — trung bình **hành vi lịch sử** của khách, không phân biệt sản phẩm. Điều này gây ra 4 lỗi hệ thống:

| Tình huống | Hậu quả |
|---|---|
| Khách mua Cordyceps (10 ngày) + Natto (30 ngày) cùng đơn | avg_days blended ~20 ngày — sai cho cả 2 SKU |
| Khách giảm liều tự ý (dùng 1 chai thay 2 chai/ngày) | Hộp 10 ngày → dùng thực 20 ngày → OVERDUE giả từ ngày 15 |
| Khách mua 3 hộp (30 ngày cung) | avg_days chỉ 10 ngày → nhắc lại sau 8 ngày, spam |
| Khách lần đầu mua | NULL signal, không có touchpoint nào trong liệu trình |

**Queue mới** giải quyết bằng cách tính depletion date từ **lượng mua và đặc tính sản phẩm**, thay vì behavioral average.

---

## 2. Kiến trúc 3 lớp

```
seed_sku_regimen_config              ← config sản phẩm (static)
        │
        ▼
int_customer_sku_supply_tracking     ← tính depletion window per (customer × SKU)
        │
        ▼
mart_customer_sku_action_queue       ← queue với action_type + journey touchpoints
```

Queue mới có **grain (customer_id, sku)** — một khách có thể có nhiều rows, mỗi SKU một row độc lập.

---

## 3. Seed Config — `seed_sku_regimen_config`

Mỗi SKU được cấu hình với các thuộc tính sau:

| Field | Type | Ý nghĩa |
|---|---|---|
| `sku` | VARCHAR | Sapo base SKU (từ `dim_products.sku`) |
| `product_group` | VARCHAR | Nhóm sản phẩm (dùng cho CRM filter chip) |
| `display_name` | VARCHAR | Tên hiển thị trong CRM |
| `supply_days_per_unit` | INTEGER | **Liều chuẩn nhà SX:** 1 đơn vị bán lẻ dùng được bao nhiêu ngày |
| `dose_reduction_buffer` | DECIMAL | **Hệ số giảm liều thực tế:** được calibrate từ data (xem §4) |
| `remind_lead_days` | INTEGER | Nhắc trước bao nhiêu ngày khi sắp hết (thường 5-7) |
| `journey_enabled` | BOOLEAN | Có bật touchpoint D7/D14 không |

**Công thức cốt lõi:**
```
effective_supply_days = supply_days_per_unit × dose_reduction_buffer
```

Ví dụ: Metabo 1 hộp 30 gói, chuẩn 2 gói/ngày = 15 ngày. Data cho thấy buffer = 1.07 → effective = **16 ngày** (dùng gần đúng liều chuẩn, ít giảm liều).

---

## 4. Calibration dose_reduction_buffer từ data

Buffer được tính từ hành vi mua lại thực tế, không phải giả định.

**Phương pháp:**
1. Lấy tất cả cặp mua lại liên tiếp của cùng product_group theo customer
2. Tính `days_per_unit = days_between_purchases / prev_order_qty`
   — normalize theo số lượng mua lần trước để ra "1 đơn vị dùng được bao nhiêu ngày"
3. Lấy **median** (không dùng mean — outlier bulk buyer skew cao)
4. `implied_buffer = median_days_per_unit / supply_days_per_unit`

**Kết quả calibration từ data thực (2026-06-29):**

| Product Group | n_customers | median_days/unit | p25 | p75 | n_very_fast (≤15d) | n_slow (>60d) |
|---|---|---|---|---|---|---|
| collagen_plus | 156 | **10** | 3 | 21 | 217 (29%) | 210 |
| collagen_swallow | 110 | **10** | 4 | 21 | 91 (20%) | 172 |
| cordyceps_plus | 155 | **10** | 3 | 23 | 140 (25%) | 233 |
| cordyceps_vien | 462 | **14** | 4 | 37 | 338 (24%) | 616 |
| fucoidan | 185 | **15** | 5 | 33 | 156 (23%) | 291 |
| metabo | 133 | **16** | 5 | 38 | 119 (29%) | 128 |
| natto | 137 | **16** | 5 | 54 | 126 (27%) | 181 |
| shark_cartilage | 145 | **12** | 2 | 40 | 162 (29%) | 209 |

> `n_very_fast` = số lần mua lại trong ≤15 ngày sau lần trước — đây là **stacking events** (mua chồng khi còn hàng).
> Tỷ lệ ~25-29% cho thấy 1/4 lần mua cần xử lý stacking đúng cách.

`implied_buffer` cuối cùng cần `supply_days_per_unit` do product team xác nhận. Khi có, buffer = `median_days_per_unit ÷ supply_days_per_unit`.

---

## 5. Supply Tracking — `int_customer_sku_supply_tracking`

### Grain
`(customer_key, sku)` — một row per khách per SKU đang active.

### Các bước tính

**Bước 1: Tổng hợp theo ngày mua**

Gộp nhiều line items cùng đơn thành 1 sự kiện mua:
```sql
SELECT customer_key, sku,
       CAST(ordered_at AT TIME ZONE 'Asia/Ho_Chi_Minh' AS DATE) AS purchase_date,
       SUM(quantity) AS total_qty
FROM fact_sales fs
JOIN dim_products dp ON fs.product_key = dp.product_key
JOIN fact_orders fo ON fs.order_id = fo.order_id
WHERE fo.is_active_order = TRUE
GROUP BY customer_key, sku, purchase_date
```

**Bước 2: Tính depletion date với LAG(1) stacking**

```sql
WITH purchase_with_lag AS (
    SELECT *,
        LAG(purchase_date) OVER w AS prev_purchase_date,
        -- Depletion date của lần mua TRƯỚC (cần để stack)
        LAG(
            purchase_date
            + (total_qty * supply_days_per_unit * dose_reduction_buffer)::INT
        ) OVER w AS prev_depletion_date
    FROM purchase_events
    WINDOW w AS (PARTITION BY customer_key, sku ORDER BY purchase_date)
)
SELECT *,
    -- LAG(1) stacking: nếu mua khi còn hàng → cộng dồn vào depletion cũ
    -- GREATEST() xử lý cả 2 case: mua sớm (stack) và mua muộn (reset)
    GREATEST(purchase_date, COALESCE(prev_depletion_date, purchase_date))
        + (total_qty * supply_days_per_unit * dose_reduction_buffer)::INT
        AS depletion_date
FROM purchase_with_lag
```

**Về LAG(1) stacking:** Xử lý đúng khi khách mua chồng ≤1 lần trước khi dùng hết. Bắt ~90% stacking cases. Full N-level stacking (recursive CTE) được để dành cho Phase 2 nếu cần.

**Bước 3: Lấy row gần nhất per (customer, sku)**

```sql
SELECT DISTINCT ON (customer_key, sku) *
FROM stacked_purchases
ORDER BY customer_key, sku, purchase_date DESC
```

**Bước 4: Tính các signal dẫn xuất**

```sql
days_until_depletion = depletion_date - CURRENT_DATE
days_since_order     = CURRENT_DATE - purchase_date  -- (ngày mua gần nhất, không phải depletion)
```

### Fallback cho SKU không có config

Khi `sku` không có trong `seed_sku_regimen_config`, dùng behavioral fallback từ `dim_customers`:
```
days_until_depletion ~ avg_days_between_orders - recency_days
```
Giữ nguyên logic cũ — chỉ SKU configured mới dùng supply-based timing.

---

## 6. Action Types — `mart_customer_sku_action_queue`

### Grain
`(customer_key, sku)` — nhiều rows per customer, mỗi SKU một action độc lập.

### Timeline journey per SKU

```
Ngày 0:   Mua hàng ─────────────────────────────────────────────────────
Day 5-9:  [USAGE_FOLLOWUP]   "Bạn đã bắt đầu dùng chưa? Nhớ uống đúng"
Day 12-16:[PROGRESS_CHECK]   "2 tuần rồi — cảm nhận thế nào?"
Day D-R:  [REORDER_PREEMPT]  "Còn ~R ngày là hết, đặt trước nhé"  ← D = depletion, R = remind_lead_days
Day D+:   [REORDER_NUDGE]    "Hết rồi! Tiếp tục không đứt liệu trình"
Day D+7+: [REORDER_OVERDUE]  "Đã X ngày đứt liều — offer đặc biệt"
```

### Điều kiện kích hoạt

```sql
CASE
    -- Journey touchpoints (chỉ khi journey_enabled = TRUE)
    WHEN cfg.journey_enabled
     AND days_since_order BETWEEN 5 AND 9
        THEN 'USAGE_FOLLOWUP'
    WHEN cfg.journey_enabled
     AND days_since_order BETWEEN 12 AND 16
        THEN 'PROGRESS_CHECK'

    -- Reorder signals (dựa trên depletion_date)
    WHEN days_until_depletion BETWEEN 0 AND cfg.remind_lead_days
        THEN 'REORDER_PREEMPT'
    WHEN days_until_depletion BETWEEN -7 AND -1
        THEN 'REORDER_NUDGE'
    WHEN days_until_depletion < -7
        THEN 'REORDER_OVERDUE'

    ELSE NULL
END AS action_type
```

### Priority rank

| Rank | Action Type | Nguồn | Ý nghĩa |
|---|---|---|---|
| 1 | `CALL_NOW` | customer-level | VIP/Gold At-Risk — gọi ngay |
| 2 | `REORDER_OVERDUE` | sku-level | Đứt liều >7 ngày |
| 3 | `REORDER_NUDGE` | sku-level | Hết hàng hôm nay |
| 4 | `WIN_BACK` | customer-level | Churn — cần offer |
| 5 | `REORDER_PREEMPT` | sku-level | Sắp hết trong R ngày |
| 6 | `PROGRESS_CHECK` | sku-level | D14 journey |
| 7 | `USAGE_FOLLOWUP` | sku-level | D7 journey |
| 8 | `SECOND_ORDER` | customer-level | First-timer push |
| 9 | `HIGH_CANCEL_RISK` | customer-level | Tỷ lệ huỷ cao |

---

## 7. Tích hợp với queue customer-level cũ

`mart_customer_action_queue` (customer-level) và `mart_customer_sku_action_queue` (sku-level) tồn tại song song:

- **Customer-level:** CALL_NOW, WIN_BACK, SECOND_ORDER, HIGH_CANCEL_RISK — giữ nguyên, không phụ thuộc SKU
- **SKU-level:** USAGE_FOLLOWUP, PROGRESS_CHECK, REORDER_PREEMPT, REORDER_NUDGE, REORDER_OVERDUE — mới, dùng supply-based timing

CRM detailView Actions tab hiển thị cả 2 loại, sort theo `priority_rank`. Mỗi SKU-level action hiện thị tên sản phẩm và `days_until_depletion`.

**Deduplication rule:** Nếu khách đang CALL_NOW (customer-level), không hiện thêm SKU REORDER_PREEMPT cùng ngày (noise). CS đã biết cần gọi ngay — SKU detail là thông tin bổ sung, không tạo action riêng.

---

## 8. Xử lý đặc biệt

### Multi-item order
Khách mua nhiều SKU cùng đơn → mỗi SKU tạo tracking độc lập. Depletion dates có thể khác nhau hoàn toàn. CRM có thể group theo order_date khi hiển thị nhưng action queue vẫn per-SKU.

### Mua nhiều hộp cùng lúc (qty > 1)
`effective_supply_days = qty × supply_days_per_unit × buffer`. Nếu khách mua 3 hộp Natto (16 ngày/hộp), effective = 48 ngày → REORDER_PREEMPT trigger ngày thứ 43.

### Mua chồng lên khi còn hàng (stacking)
LAG(1) GREATEST() xử lý: nếu `purchase_date < prev_depletion_date`, depletion mới bắt đầu từ `prev_depletion_date` thay vì `purchase_date`. Tránh tình trạng hệ thống nhắc mua lại khi khách vừa mua xong hôm qua.

### SKU chưa có config
Fallback về behavioral signal từ `dim_customers.avg_days_between_orders`. Action type vẫn là `REORDER_PREEMPT`/`REORDER_NUDGE` nhưng tính từ recency vs avg_days, không có supply data. Journey touchpoints không available.

### Khách dừng dùng (không phải giảm liều)
Khi `days_until_depletion < -30` và không có lần mua mới → chuyển về customer-level WIN_BACK thay vì tiếp tục `REORDER_OVERDUE`. Ngưỡng configurable per SKU.

---

## 9. Mô hình dữ liệu — output columns

`mart_customer_sku_action_queue`:

| Column | Mô tả |
|---|---|
| `customer_key` | FK → dim_customers |
| `customer_id` | Sapo customer ID |
| `sku` | Sapo base SKU |
| `product_group` | Nhóm sản phẩm (8 core) |
| `product_name` | Tên hiển thị |
| `action_type` | Loại action (6 types) |
| `priority_rank` | Số nhỏ hơn = ưu tiên hơn |
| `days_until_depletion` | Âm = đã hết hàng, dương = còn N ngày |
| `days_since_order` | Ngày kể từ lần mua cuối |
| `last_purchase_date` | Ngày mua cuối cùng SKU này |
| `last_order_qty` | Số lượng mua lần cuối |
| `effective_supply_days` | qty × supply_days × buffer |
| `estimated_depletion_date` | Ngày dự kiến hết hàng |
| `action_rationale` | String giải thích tiếng Việt |
| `dose_reduction_buffer` | Buffer đang dùng (từ config) |
| `supply_days_per_unit` | Liều chuẩn nhà SX |
| `queue_generated_at` | Timestamp tạo queue |

---

## 10. Unresolved / Cần xác nhận

1. **`supply_days_per_unit` cho 8 SKU** — cần product team xác nhận. Hiện có `median_days_per_unit` từ data, chờ standard để tính buffer cuối.

2. **shark_cartilage `avg_order_qty = 47.3`** (median = 3) — nghi đơn vị trong Sapo là `viên` không phải `lọ`. Cần xác minh trước khi đưa vào config.

3. **Journey D7/D14 delivery mechanism** — queue tạo task trong CRM (manual CS action). Confirmed: không auto-Zalo.

4. **Suppress REORDER_PREEMPT khi CALL_NOW** — logic nằm ở CRM layer hay ở mart SQL? Đề xuất: suppress ở mart (đơn giản hơn) bằng `WHERE action_type NOT IN ('REORDER_PREEMPT') OR customer_level_action IS NULL`.

5. **Recursive CTE upgrade path** — Phase 2 nếu error rate từ LAG(1) stacking > 5% sau validation.
