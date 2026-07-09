# SKU-Level Action Queue — Design & Calculation Reference

> **Scope:** Data Team, CRM Product
> **Updated:** 2026-07-08
> **Status:** Implemented — shipped 2026-07-08 (Plan: `plans/260708-1501-gift-purchase-sku-action-scenario`)

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

## 2. Kiến trúc 4 lớp

```
seed_sku_regimen_config              ← config sản phẩm (static)
        │
        ▼
int_customer_sku_supply_tracking     ← tính depletion window per (customer × SKU × supply_stream)
        │
        ├─────────────────────────────────────────┐
        │                                         │
        ▼                                         ▼
mart_customer_sku_action_queue       seed_action_scenario_registry    ← feature-flag layer
        │                                    │
        │                                    │
        └────────────────────┬───────────────┘
                             ▼
                    mart_customer_sku_action_queue (final output)
```

Queue mới có **grain (customer_key, sku, supply_stream)** — một khách có thể có nhiều rows, mỗi (SKU, stream) một row độc lập.

**supply_stream dimension:**
- `purchased`: mua bằng tiền (dùng normal supply-based timing)
- `gift_only`: khách chỉ từng được tặng SKU này, chưa bao giờ mua tự nguyện (timeline độc lập, kích hoạt `GIFT_TO_PURCHASE` scenario mới)

**Scenario Registry layer:**
Sau khi tính toán action_type, check `seed_action_scenario_registry` để decide xem action_type đó có xuất hiện ở output hay không. Mỗi action_type có flag `enabled=true/false` per `mart` — đổi bật/tắt chỉ cần edit seed + `dbt seed && dbt run`, không sửa SQL branching.

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
`(customer_key, sku, supply_stream)` — một row per khách per SKU per luồng mua.

**supply_stream values:**
- `purchased`: khách đã từng tự mua SKU này (dù là lần đầu hay lần N) — tracking supply days bình thường
- `gift_only`: khách chỉ từng được tặng SKU này (zero non-gift purchase history) — tracking supply days độc lập, trigger scenario `GIFT_TO_PURCHASE`

**Logic xác định stream:**
- Nếu `EXISTS (khách mua non-gift SKU này, bất kỳ lần nào)` → `purchased`
- Nếu `NOT EXISTS (khách mua non-gift SKU này)` AND `EXISTS (khách được tặng SKU này)` → `gift_only`

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
`(customer_key, sku, supply_stream)` — nhiều rows per customer, mỗi (SKU, stream) một action độc lập.

### Timeline journey per SKU — `purchased` stream

```
Ngày 0:   Mua hàng ─────────────────────────────────────────────────────
Day 5-9:  [USAGE_FOLLOWUP]   "Bạn đã bắt đầu dùng chưa? Nhớ uống đúng"
Day 12-16:[PROGRESS_CHECK]   "2 tuần rồi — cảm nhận thế nào?"
Day D-R:  [REORDER_PREEMPT]  "Còn ~R ngày là hết, đặt trước nhé"  ← D = depletion, R = remind_lead_days
Day D+:   [REORDER_NUDGE]    "Hết rồi! Tiếp tục không đứt liệu trình"
Day D+7+: [REORDER_OVERDUE]  "Đã X ngày đứt liều — offer đặc biệt"
```

### Timeline journey per SKU — `gift_only` stream

```
Ngày 0:    Nhận tặng ─────────────────────────────────────────────────
Day D-R:   [GIFT_TO_PURCHASE] "Đã dùng từng bao giờ? Mở rộng luôn!"  ← ships disabled (enabled=false)
```

**GIFT_TO_PURCHASE status:** Tính toán logic sẵn sàng; output không xuất hiện khi `seed_action_scenario_registry` có `action_type='GIFT_TO_PURCHASE', enabled=false`. Cần review timing rule trước khi flip `enabled=true`.

### Điều kiện kích hoạt

```sql
-- Tính candidate action_type từ logic, rồi filter qua scenario registry
WITH candidate_actions AS (
  SELECT
    customer_key, sku, supply_stream,
    CASE
        -- Purchased stream: journey touchpoints (chỉ khi journey_enabled = TRUE)
        WHEN supply_stream = 'purchased'
         AND cfg.journey_enabled
         AND days_since_order BETWEEN 5 AND 9
            THEN 'USAGE_FOLLOWUP'
        WHEN supply_stream = 'purchased'
         AND cfg.journey_enabled
         AND days_since_order BETWEEN 12 AND 16
            THEN 'PROGRESS_CHECK'

        -- Purchased stream: reorder signals (dựa trên depletion_date)
        WHEN supply_stream = 'purchased'
         AND days_until_depletion BETWEEN 0 AND cfg.remind_lead_days
            THEN 'REORDER_PREEMPT'
        WHEN supply_stream = 'purchased'
         AND days_until_depletion BETWEEN -7 AND -1
            THEN 'REORDER_NUDGE'
        WHEN supply_stream = 'purchased'
         AND days_until_depletion < -7
            THEN 'REORDER_OVERDUE'

        -- Gift-only stream: conversion opportunity
        WHEN supply_stream = 'gift_only'
         AND days_until_depletion BETWEEN 0 AND cfg.remind_lead_days
            THEN 'GIFT_TO_PURCHASE'

        ELSE NULL
    END AS candidate_action_type
  FROM base_supply_tracking
  JOIN seed_sku_regimen_config cfg USING (sku)
)
SELECT
  customer_key, sku, supply_stream, candidate_action_type AS action_type
FROM candidate_actions
WHERE candidate_action_type IS NOT NULL
-- Scenario registry filter: only include if enabled for this action_type/mart
  AND EXISTS (
    SELECT 1 FROM seed_action_scenario_registry reg
    WHERE reg.action_type = candidate_action_type
      AND reg.mart = 'mart_customer_sku_action_queue'
      AND reg.enabled = true
  )
```

### Priority rank

| Rank | Action Type | Nguồn | Stream | Ý nghĩa |
|---|---|---|---|---|
| 1 | `CALL_NOW` | customer-level | N/A | VIP/Gold At-Risk — gọi ngay |
| 2 | `REORDER_OVERDUE` | sku-level | purchased | Đứt liều >7 ngày |
| 3 | `REORDER_NUDGE` | sku-level | purchased | Hết hàng hôm nay |
| 4 | `WIN_BACK` | customer-level | N/A | Churn — cần offer |
| 5 | `REORDER_PREEMPT` | sku-level | purchased | Sắp hết trong R ngày |
| 5.5 | `GIFT_TO_PURCHASE` | sku-level | gift_only | Chuyển đổi khách chỉ được tặng (ships disabled) |
| 6 | `PROGRESS_CHECK` | sku-level | purchased | D14 journey |
| 7 | `USAGE_FOLLOWUP` | sku-level | purchased | D7 journey |
| 8 | `SECOND_ORDER` | customer-level | N/A | First-timer push |
| 9 | `HIGH_CANCEL_RISK` | customer-level | N/A | Tỷ lệ huỷ cao |

---

## 7. Tích hợp với queue customer-level + Tier-aware branching

`mart_customer_action_queue` (customer-level) và `mart_customer_sku_action_queue` (sku-level) tồn tại song song:

- **Customer-level:** CALL_NOW, WIN_BACK, SECOND_ORDER, HIGH_CANCEL_RISK — giữ nguyên action types
- **SKU-level:** USAGE_FOLLOWUP, PROGRESS_CHECK, REORDER_PREEMPT, REORDER_NUDGE, REORDER_OVERDUE, GIFT_TO_PURCHASE — supply-based timing + new gift stream

**Tier-aware filtering (implemented 2026-07-08):**
Cả 2 marts hiện join `mart_customer_tier` để lấy:
- `strategic_tier`: VIP/Gold/Silver/Bronze/Standard/Monitor/Dormant
- `is_contactable`: từ tier (strictly: phone IS NOT NULL AND phone <> ''), thay vì local expression

Ngoài ra, cả 2 marts loại bỏ `is_us_gift_recipient` customers khỏi eligibility (người nhận hàng US, khác customer Sapo VN).

**Scenario Registry layer (implemented 2026-07-08):**
Mỗi action_type có flag `enabled=true/false` trong `seed_action_scenario_registry`:
- Tất cả logic tính toán luôn sẵn sàng chạy
- Output chỉ xuất hiện khi `enabled=true` cho action_type đó
- Đổi bật/tắt = edit seed + `dbt seed && dbt run`
- `GIFT_TO_PURCHASE` ships `enabled=false` pending timing-rule review

CRM detailView Actions tab hiển thị cả 2 loại, sort theo `priority_rank`. Mỗi SKU-level action hiện thị tên sản phẩm, `supply_stream`, và `days_until_depletion`.

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
| `supply_stream` | `purchased` hoặc `gift_only` |
| `product_group` | Nhóm sản phẩm (8 core) |
| `product_name` | Tên hiển thị |
| `action_type` | Loại action (5-6 types tùy enable status) |
| `priority_rank` | Số nhỏ hơn = ưu tiên hơn |
| `days_until_depletion` | Âm = đã hết hàng, dương = còn N ngày |
| `days_since_order` | Ngày kể từ lần mua/tặng cuối |
| `last_purchase_date` | Ngày mua/tặng cuối cùng SKU này |
| `last_order_qty` | Số lượng mua/tặng lần cuối |
| `effective_supply_days` | qty × supply_days × buffer |
| `estimated_depletion_date` | Ngày dự kiến hết hàng |
| `action_rationale` | String giải thích tiếng Việt |
| `dose_reduction_buffer` | Buffer đang dùng (từ config) |
| `supply_days_per_unit` | Liều chuẩn nhà SX |
| `strategic_tier` | Từ `mart_customer_tier` (VIP/Gold/Silver/…) |
| `queue_generated_at` | Timestamp tạo queue |

---

## 10. Unresolved / Cần xác nhận (post-implementation)

1. **`GIFT_TO_PURCHASE` timing rule** — khi nào nhắc khách được tặng: X ngày sau nhận tặng? Hay theo supply_days_per_unit như luồng mua? Chưa chốt. Ships `enabled=false`, cần data-grounded timing review trước khi flip `enabled=true`.

2. **`gift_rate` threshold để gán `sku_role` categorical** — báo cáo finejapan gợi ý >40% nhưng chỉ cover 3/8 core SKU. Để riêng nếu có nhu cầu downstream.

3. **`is_us_gift_recipient` base signal** — hiện dựa 100% vào manual Sapo group tag, cùng lỗ hổng "chưa tag = RETAIL" như `customer_type`. Real fix (tự động từ `EXISTS (channel='US')`) đã quyết định tách thành plan riêng. Plan này tạm dùng cờ thủ công; follow-up riêng nếu tỷ lệ miss cao.

4. **Recursive CTE upgrade path** — nếu error rate từ LAG(1) stacking > 5% sau validation, upgrade lên full N-level stacking. Hiện 90% stacking cases handled.

5. **wh_deadstock_target & mart_product_action_queue** — 2 action-queue engine khác; đánh giá sau nếu cần reuse `is_gift_line`/`supply_stream` logic.
