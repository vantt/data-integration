# SME Budget Planning — Kiến thức & Thực hành

> Tài liệu ghi nhận kiến trúc tư duy, kinh nghiệm và practice để xây dựng + duy trì budget planning cho doanh nghiệp SME. Tách biệt khỏi plan kỹ thuật — dùng làm nền tảng thiết kế khi triển khai Phase 04 (budget hybrid layer).
> Cập nhật khi có learnings mới — đây là living document.

---

## 1. Nền tảng — Hiểu trước khi lập kế hoạch

**P&L thực sự** phải rõ trước khi budget có giá trị:

- Gross margin theo **kênh / SKU** — không phải tổng gộp
- Tách rõ **fixed cost vs. variable cost** để biết break-even thực
- **Cash flow ≠ profit** — SME chết vì hết cash, không phải vì lỗ kế toán

**Liên hệ dự án:** Cashflow report (Phase 03) cung cấp nền tảng — opening/closing balance, inflow/outflow theo `cashflow_line`. Phase 04 xây budget layer trên nền đó.

---

## 2. Kiến trúc Budget thực dụng cho SME

### 2.1 Rolling 13-week Cash Forecast (ưu tiên hơn Annual Budget cứng)

| Horizon | Độ chi tiết |
|---|---|
| Tuần 1–4 | Chi tiết từng khoản |
| Tuần 5–8 | Ước lượng theo danh mục |
| Tuần 9–13 | Dự phóng xu hướng |

Annual budget vẫn cần để định hướng — nhưng SME biến động quá nhanh để bám chặt 12 tháng. Reforecast hàng quý là bắt buộc.

### 2.2 Zero-based Budgeting nhẹ cho chi phí gián tiếp

- Mỗi quý justify lại chi phí biến đổi (marketing, SaaS, tư vấn)
- Không tự động rollover từ kỳ trước
- Fixed cost (lương, mặt bằng) không cần zero-base — review annually

### 2.3 Phân tầng ưu tiên chi tiêu

```
Tier 1 — Must survive:  lương, thuê mặt bằng, nguyên vật liệu
Tier 2 — Must grow:     kênh bán hàng sinh doanh thu trực tiếp
Tier 3 — Nice to have:  branding, công cụ tự động hóa, đào tạo
```

Khi cash tight → cắt Tier 3 trước, giữ Tier 1 bằng mọi giá. Tier 2 đánh giá ROI thực trước khi cắt.

---

## 3. Cadence duy trì

| Tần suất | Việc cần làm |
|---|---|
| **Hàng tuần** | Cash balance thực + forecast 4 tuần tới |
| **Hàng tháng** | Actual vs. Budget — deviation >10% phải có giải thích; phân bổ thặng dư theo Waterfall |
| **Hàng quý** | Reforecast cả năm + review allocation policy |
| **Hàng năm** | Zero-based review toàn bộ cost structure |

**Budget owner rõ ràng** — mỗi dòng ngân sách phải có 1 người chịu trách nhiệm.

---

## 4. Input Mechanism — Google Sheet Option C (Hybrid Matrix)

### Tại sao Option C?

Finance không dùng git. CSV nhập tay = chết sau tháng 2. Google Sheet là môi trường quen thuộc, có thể validate trực tiếp, script pull tự động.

"Option C hybrid" = **matrix layout** (tháng là cột) + **`payment_week`** cố định mỗi dòng + **`item_type`** phân loại khoản.

### Cấu trúc Sheet

**Tab BUDGET\_INPUT** — finance nhập đầu mỗi tháng (~15-20 phút):

```
                          │       │         │    T7/2026    │    T8/2026    │
Dòng tiền         │Chiều  │TuầnTT │ Gợi ý   │ Budget        │ Gợi ý  │ Budget │
─── THU ──────────────────────────────────────────────────────────────────────
Thu từ KH         │ Thu   │Trải đều│  464M  │  480M         │  464M  │  490M  │
─── CHI ──────────────────────────────────────────────────────────────────────
Chi lương         │ Chi   │Tuần 1  │  238M  │  240M         │  238M  │  240M  │
Chi BHXH          │ Chi   │Tuần 3  │   97M  │  100M         │   97M  │  100M  │
Thanh toán NCC    │ Chi   │Tuần 4  │   14M  │   15M         │   14M  │   15M  │
Chi bán hàng/QLDN │ Chi   │Trải đều│   19M  │   20M         │   19M  │   20M  │
```

- Cột **Gợi ý** = script auto-fill từ rolling avg 3 tháng actual (read-only, màu xám)
- Cột **Budget** = finance điều chỉnh (màu trắng, có data validation)
- Cột **Tuần TT** = điền 1 lần lúc setup, không đổi theo tháng

**Tab SPECIAL\_ITEMS** — khoản không thường xuyên (xem Mục 5):

```
Hạng mục          │item_type│Tổng cần│Tháng cần│Để dành/th│Ghi chú
Máy nén khí mới   │reserve  │  80M   │ T10/26  │   15M    │ Máy hiện hư dần
Bảo hiểm tài sản  │one_off  │  12M   │ T12/26  │    0     │ Đóng 1 lần/năm
Sửa chữa mái kho  │reserve  │  30M   │  ???    │    5M    │ Chưa rõ thời điểm
```

**Tab ALLOCATION\_POLICY** — finance review hàng quý (xem Mục 6):

```
Ưu tiên │ Bucket                │ Loại rule      │ Giá trị │ Target
  1     │ Emergency buffer      │ fill_to_target │   —     │ 330M
  2     │ Reserve máy nén khí   │ fixed          │  15M/th │  80M
  3     │ Reserve sửa chữa      │ fixed          │   5M/th │  30M
  4     │ Working capital       │ pct_remaining  │   30%   │  —
  5     │ Owner / reinvestment  │ remainder      │   —     │  —
```

### Auto pre-fill logic

```sql
-- Chạy đầu mỗi tháng, fill tab "Gợi ý" trong Sheet
SELECT
    cashflow_line,
    direction,
    DATE_TRUNC('month', MAX(period_month) + INTERVAL '1 month') AS budget_month,
    ROUND(AVG(actual_amount), -6) AS suggested_amount  -- làm tròn triệu
FROM fact_cash_movement
WHERE period_month >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '3 months'
  AND NOT is_internal_transfer
GROUP BY 1, 2
```

### Seed schema (fact_cashflow_budget grain)

```
cashflow_line      -- join key với actual (exact match dim_gl_account.cashflow_line)
period_month       -- YYYY-MM-01
direction          -- 'inflow' | 'outflow'
planned_amount     -- VND, luôn dương
payment_week       -- 1 | 2 | 3 | 4 | 'spread' (cho weekly view)
item_type          -- 'recurring' | 'one_off' | 'reserve'
item_label         -- tên tự do để hiển thị dashboard (nullable cho recurring)
item_target        -- tổng cần đạt (chỉ dùng khi item_type='reserve')
target_month       -- tháng cần dùng tiền (chỉ dùng khi item_type='reserve'/'one_off')
```

---

## 5. Khoản không thường xuyên — Phân loại và Quản lý

### Hai loại cần tách biệt

| | one\_off | reserve (sinking fund) |
|---|---|---|
| Ví dụ | Bảo hiểm hàng năm T12, thuế môn bài | Máy sắp hư, mua thêm kệ kho |
| Biết timing? | Biết tháng cụ thể | Có thể chưa biết |
| Xử lý | Budget lump sum vào tháng đó | Để dành monthly, tích lũy dần |
| Dashboard | Hiển thị như khoản chi bình thường | Hiển thị "đã để dành X / cần Y" |

### Sinking fund — cơ chế chia tiền theo chu kỳ

```
Mục tiêu: Máy nén khí 80M, cần tháng T10
Hiện tại: T7, còn 3 tháng
→ Cần để dành: 80M / 3 = 26.7M/tháng (hoặc điều chỉnh thủ công)

Script tự tính:
  remaining_gap = item_target - Σ(planned_amount where period_month <= now)
  required_monthly = remaining_gap / months_until_target
  → Đưa vào cột "Gợi ý" tab SPECIAL_ITEMS để finance xem xét
```

### Physical vs. Virtual earmarking

Hệ thống data chỉ track được **virtual earmark** — tiền vẫn trong 1 tài khoản. Để enforce thật, cần kết hợp:

| Reserve size | Approach |
|---|---|
| < 20M hoặc < 2 tháng | Virtual — dashboard "Free Cash" đủ kỷ luật |
| 20–100M, 3–6 tháng | **Tài khoản ngân hàng riêng** — chuyển monthly, không thể "lỡ tay" |
| > 100M hoặc > 6 tháng | **Tiết kiệm kỳ hạn ngắn rolling** — 30-60 ngày, có lãi, khó phá vỡ |

**Lưu ý về MISA:** Khi chuyển tiền từ TK vận hành (111) sang TK dự phòng (112x), MISA ghi nhận là internal transfer — bị loại khỏi cashflow operational report (đúng). Cần track separate trong reserve status mart.

### Reserve Status Mart

```sql
-- mart_cashflow_reserve_status
SELECT
    item_label,
    item_target,
    target_month,
    SUM(planned_amount) AS accumulated_plan,
    item_target - SUM(planned_amount) AS gap_remaining,
    DATE_DIFF('month', CURRENT_DATE, target_month) AS months_remaining,
    ROUND((item_target - SUM(planned_amount))
          / NULLIF(DATE_DIFF('month', CURRENT_DATE, target_month), 0), 0
    ) AS required_monthly_adj
FROM fact_cashflow_budget
WHERE item_type = 'reserve'
GROUP BY item_label, item_target, target_month
```

---

## 6. Cash Allocation Waterfall — Phân bổ thặng dư

### Vấn đề cốt lõi

Không có policy phân bổ rõ ràng → thặng dư "tan biến" vào operations tháng sau. Không ai hỏi, không ai thấy.

### Waterfall vs. Phân bổ %

**Phân bổ % (Profit First):** Phù hợp khi cash ổn định. Không phù hợp với business có variance lớn.

**Waterfall (ưu tiên theo bucket):** Fill bucket quan trọng trước, remainder mới xuống bucket tiếp theo. Phù hợp với SME có cash không đều.

### Cấu trúc Waterfall

```
Net surplus tháng X
    │
[P1] Emergency buffer      → fill đến target (8–12 tuần outflow)
    │ còn lại
[P2] Reserve contributions → mỗi item theo plan (fixed/month)
    │ còn lại
[P3] Working capital buffer → giữ N% cho tháng tới
    │ còn lại
[P4] Owner / reinvestment  → remainder
```

### Ngưỡng Emergency Buffer

```
Target buffer = avg_monthly_outflow × 2  (tối thiểu 8 tuần)

Ví dụ thực tế (dự án này):
  avg_monthly_outflow ≈ 170M/tháng
  target_buffer = 170M × 2 = 340M
  current_buffer (T6/2026) = 165M
  → Cash Coverage Weeks = 165M / (170M/4) ≈ 3.8 tuần
  → DƯỚI ngưỡng an toàn → toàn bộ thặng dư ưu tiên fill buffer trước
```

**Hệ quả thực tế:** Business không nên phân bổ reserve/owner cho đến khi buffer đạt 8 tuần.

### Allocation Policy Config

Finance review hàng quý, không phải hàng tháng:

```
rule_type options:
  fill_to_target  → đổ vào đến khi đạt target, thừa mới xuống bucket tiếp
  fixed           → cố định N triệu/tháng (nếu không đủ → partial fill, alert)
  pct_remaining   → N% của phần còn lại sau các bucket trên
  remainder       → toàn bộ phần còn lại
```

### Free Cash Metric — số quan trọng nhất trên dashboard

```
free_cash = closing_balance - Σ(item_target - accumulated_reserve)

Ví dụ:
  closing_balance = 165M
  Máy nén khí còn thiếu: 80M - 30M = 50M
  Sửa mái kho còn thiếu: 30M - 10M = 20M
  free_cash = 165M - 50M - 20M = 95M  ← số thực sự "rảnh" để chi
```

### Surplus Allocation Mart

```sql
-- mart_cash_surplus_allocation
-- Input: net_surplus from mart_cashflow_budget_vs_actual (closed periods)
-- Apply: allocation policy rules in priority order
-- Output: per-bucket allocated amount + free_cash

SELECT
    period_month,
    net_surplus,
    LEAST(net_surplus, GREATEST(0, buffer_target - prior_buffer))    AS alloc_buffer,
    LEAST(remaining_after_buffer, reserve_fixed_total)               AS alloc_reserves,
    remaining_after_reserves * working_capital_pct                   AS alloc_working_capital,
    remaining_after_wc                                               AS alloc_owner,
    closing_balance - total_reserve_gap                              AS free_cash
FROM ...
```

---

## 7. Dashboard Design — Cards cần thiết

| Card | Metric chính | Cập nhật |
|---|---|---|
| **Cash Position** | Free cash / Total cash / Reserved | Daily |
| **Budget vs Actual** | Variance % per cashflow_line | Monthly |
| **Cash Forecast** | Projected balance 6 tháng tới (actual + forecast band) | Monthly |
| **Reserve Status** | Mỗi item: đã để dành / cần / gap / deadline | Monthly |
| **Allocation Tracker** | Tháng vừa rồi: thặng dư phân bổ ra sao | Monthly |
| **Upcoming Large Items** | Khoản đặc biệt sắp đến (one_off + reserve chưa đủ) | Monthly |
| **Cash Coverage Weeks** | Tuần buffer hiện tại vs. target 8 tuần | Weekly |

---

## 8. Sai lầm phổ biến

| Sai lầm | Hậu quả | Phòng tránh |
|---|---|---|
| Optimistic revenue, realistic cost | Cash crunch quý 2–3 | Budget revenue = P50 scenario |
| Không tách working capital | Hàng tồn kho + công nợ ăn mòn cash ngầm | `cashflow_line = 'working_capital_change'` riêng |
| Budget bị "khóa tủ" | Lập xong không ai nhìn | Monthly review bắt buộc + alert tự động |
| Không có buffer | Một cú sốc là vỡ cash | 8–12 tuần fixed cost target |
| Sinking fund không được enforce | "Mượn" reserve lúc tight, không trả lại | Tài khoản ngân hàng riêng cho reserve > 50M |
| Phân bổ thặng dư không có policy | Tiền "biến mất" vào operations | Waterfall policy được cấu hình + review quý |
| Gộp intra-company transfer | Inflow/outflow bị inflate ảo | Exclude transfers khỏi cashflow operational |

**Lưu ý dự án:** Internal transfers (299M VND T6/2026) đã được exclude đúng trong `fact_cash_movement`.

---

## 9. Tooling theo giai đoạn

| Giai đoạn | Tool phù hợp |
|---|---|
| Startup (<10 người) | Google Sheets + template tốt |
| Scale-up (<50 người) | QuickBooks / Xero — link actual tự động |
| Data-driven | DuckDB + dbt + Metabase (như hệ thống này) |
| Enterprise | ERP với budget module tích hợp |

**Nguyên tắc:** Đừng mua phần mềm phức tạp khi process chưa ổn định. Hệ thống chỉ tốt khi có người vận hành đúng cadence.

**Về MISA budget module:** Finance không dùng → không scrape được → budget source duy nhất là Google Sheet → CSV. Nếu sau này finance adopt MISA budget module thì mới xem xét Phase 05.

---

## 10. Liên kết với dự án này

| Phase | Tài liệu | Status |
|---|---|---|
| GL modeling | `plans/260702-1727-misa-cashflow-budget-planner/phase-02-gl-modeling.md` | ✅ Done |
| Cashflow report | `plans/260702-1727-misa-cashflow-budget-planner/phase-03-cashflow-report.md` | ✅ Done (live) |
| Budget hybrid layer | `plans/260702-1727-misa-cashflow-budget-planner/phase-04-budget-hybrid.md` | ⏳ Pending |
| MISA budget scraper | — | ❌ Dropped (finance không dùng MISA budget module) |
| Finance domain | `docs/analytics-handbook/domains/finance.md` | — |
| Cashflow design spec | `docs/analytics-handbook/designs/finance_cashflow.md` | — |

---

*Cập nhật: 2026-07-03 — thêm Sections 4-6 từ thảo luận thiết kế Phase 04 (Option C Sheet, irregular items, sinking fund, Cash Allocation Waterfall).*
