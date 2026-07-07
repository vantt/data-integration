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

**Tab BUDGET\_ITEMS** (gộp BUDGET\_INPUT + khoản đặc biệt) — finance nhập đầu mỗi tháng:

```
                   │      │       │          │        │          │    T7/2026    │
Dòng tiền          │Chiều │TuầnTT │item_type │Cần tổng│Tháng cần │ Gợi ý │Budget │
─── THU ───────────────────────────────────────────────────────────────────────────
Bán hàng KH        │ Thu  │spread │recurring │        │          │  464M │  480M │
─── CHI THƯỜNG XUYÊN ──────────────────────────────────────────────────────────────
Chi lương          │ Chi  │Tuần 1 │recurring │        │          │  238M │  240M │
Chi BHXH           │ Chi  │Tuần 3 │recurring │        │          │   97M │  100M │
─── CHI ĐẶC BIỆT / DỰ PHÒNG ───────────────────────────────────────────────────────
Để dành máy nén khí│ Chi  │Tuần 4 │reserve   │  80M   │  T10/26  │   27M │   27M │  ← sinking fund
Bảo hiểm tài sản   │ Chi  │Tuần 1 │one_off   │  12M   │  T12/26  │    0  │    0  │  ← 0 đến T12
Sửa chữa mái kho   │ Chi  │Tuần 4 │reserve   │  30M   │    ???   │    5M │    5M │
```

- `recurring`: Gợi ý = rolling avg 3 tháng actual
- `reserve`: Gợi ý phụ thuộc vào `Cần tổng` / `Tháng cần`:
  - Có cả hai → `gap_còn_lại / months_until_target` (sinking fund tự động)
  - Chỉ có target, không deadline → không tính gợi ý; dashboard hiển thị "accumulated X / cần Y — chưa có deadline"
  - Không có cả hai → không tính gợi ý; finance nhập tay mỗi tháng; dashboard hiển thị "đã tích lũy X"
- `one_off`: Gợi ý = 0 trừ tháng target; `Cần tổng` = số chi lần đó

**Tab ALLOCATION\_POLICY** — finance review hàng quý (xem Mục 6):

```
Ưu tiên │ Bucket             │ rule_type      │ value     │ effective_from │ effective_to
  1     │ Emergency buffer   │ fill_to_target │ 330000000 │ 2026-01-01     │            ← value = ngưỡng VND
  2     │ Reserve items      │ from_plan      │           │ 2026-01-01     │            ← từ BUDGET_ITEMS
  3     │ Quỹ phúc lợi NV   │ fixed          │ 2000000   │ 2026-01-01     │            ← open-ended
  4     │ Working capital    │ pct_remaining  │ 30        │ 2026-01-01     │            ← value = %
  5     │ Owner              │ remainder      │           │ 2026-01-01     │
```

- **`value`** là tham số duy nhất của rule — không có cột `target` riêng (target và % đều dùng chung `value`)
- **`effective_from`/`effective_to`**: finance điền khi thay đổi policy. Để `effective_to` trống = đang hiệu lực.
- **Sheet chỉ hiển thị current rows** (effective_to trống). Khi đổi policy: set `effective_to` vào dòng cũ → thêm dòng mới với `effective_from` mới. Script merge với historical rows trong CSV (append-only) — không xóa lịch sử.
- Script validate không có **gap hoặc overlap** giữa các dòng cùng bucket trước khi generate CSV.

### Chống sai sót nhập liệu — Dropdown validation

`cashflow_line` là join key giữa Sheet và pipeline. Typo một ký tự → join 0 rows, không có lỗi, số biến mất im lặng.

**Giải pháp: tab `__REF` + dropdown validation** (đơn giản hơn code column):

```
Tab __REF (ẩn, finance không cần đụng):
  Cột A: toàn bộ cashflow_line hợp lệ (copy từ dim_gl_account.sql CASE expression)
  Cập nhật khi taxonomy thay đổi

Tab BUDGET_ITEMS:
  Cột "Dòng tiền" → Data Validation: List from range = __REF!A:A
  → Finance chỉ chọn từ dropdown, không thể gõ sai
  → Script pull không cần thêm mapping layer
```

**Code column không cần thiết** vì:
- `cashflow_line` (dropdown) đã đủ làm join key cho recurring/one_off
- `item_label` đã phân biệt các reserve items cùng cashflow_line
- `from_plan` bucket trong ALLOCATION_POLICY sum theo `item_type='reserve'`, không cần code riêng
- Nếu sau này cần cross-lookup phức tạp hơn → thêm lúc đó (YAGNI)

**Cột Gợi ý vs Budget** (2 cột per tháng trong BUDGET_ITEMS):

| | Gợi ý | Budget |
|---|---|---|
| Ai điền | Script (đầu tháng) | Finance |
| Editable | Không (lock cell, màu xám) | Có (màu trắng) |
| recurring | Rolling avg 3 tháng actual | Finance confirm hoặc override |
| reserve | gap_còn_lại / months_until_target | Finance confirm hoặc điều chỉnh |
| one_off | 0 (trừ target_month = item_target) | Finance confirm |
| Vào pipeline | Không | Có → seed CSV → dbt |

**Script phân biệt 2 scripts:**
- `prefill-budget-suggestions.py` — DuckDB → Sheet (ghi cột Gợi ý, chạy đầu tháng)
- `pull-budget-from-sheet.py` — Sheet → CSV (đọc cột Budget, chạy sau khi finance điền xong)

Cả hai cần **Google Sheets API + Service Account** (share Sheet với service account email là Editor). Public share = read-only, không ghi được.

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
item_target        -- tổng cần đạt (nullable — xem validation bên dưới)
target_month       -- tháng cần dùng tiền (nullable — xem validation bên dưới)
```

**Validation target/deadline (script enforce):**

| target | deadline | Xử lý |
|--------|----------|--------|
| có | có | Sinking fund — script tính gợi ý `gap/months` |
| có | không | Tích lũy không áp lực thời gian — finance nhập tay, progress bar hiện `X/target` |
| không | không | Open-ended — finance nhập tay, hiện `tích lũy X` |
| không | có | **REJECT** — deadline không có target là vô nghĩa |

---

## 5. Khoản không thường xuyên — Phân loại và Quản lý

### Hai loại cần tách biệt

| | one\_off | reserve (sinking fund) |
|---|---|---|
| Ví dụ | Bảo hiểm hàng năm T12, thuế môn bài | Máy sắp hư, mua thêm kệ kho |
| Biết timing? | Biết tháng cụ thể | Có thể chưa biết |
| Xử lý | Budget lump sum vào tháng đó | Để dành monthly, tích lũy dần |
| Dashboard | Hiển thị như khoản chi bình thường | Hiển thị "đã để dành X / cần Y" |

**Cả hai đều nằm trong BUDGET_ITEMS** — dù có hay không có target/deadline. Khác nhau chỉ ở cách hệ thống tính Gợi ý và cách dashboard hiển thị:

| Có target + deadline | Sinking fund đầy đủ: progress %, months left, on-track/behind |
|---|---|
| Có target, không deadline | Progress % + "còn thiếu X" — không áp lực thời gian |
| Không target, không deadline | "Đã tích lũy X" — open-ended; finance nhập tay mỗi tháng |

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

### Thứ tự ưu tiên trong Waterfall

**`priority` number là cơ chế sắp xếp duy nhất** — số nhỏ hơn được fill trước. `rule_type` chỉ xác định "lấy bao nhiêu", không xác định thứ tự.

Convention được khuyến nghị (không phải bắt buộc về mặt kỹ thuật):

```
from_plan → fill_to_target → fixed → pct_remaining → remainder
```

Finance tự đặt priority numbers theo ngữ nghĩa business. Chỉ có 1 constraint cứng bắt buộc validate:

> **`remainder` phải là priority cao nhất (số lớn nhất)** — nếu có bucket nào sau `remainder` thì bucket đó không nhận được gì.

### Cấu trúc Waterfall (ví dụ điển hình)

```
Net surplus tháng X
    │
[P1] Emergency buffer      → fill đến target (8–12 tuần outflow)
    │ còn lại
[P2] Reserve contributions → Σ planned_amount của reserve+one_off trong BUDGET_ITEMS tháng đó
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

Finance review hàng quý, không phải hàng tháng. Schema: `(priority, bucket, rule_type, value, effective_from, effective_to)` — không có cột `target` riêng, `value` mang cả hai vai trò (ngưỡng tiền hoặc %).

```
rule_type options:
  fill_to_target  → đổ vào cho đến khi đạt value (VND), thừa xuống bucket tiếp
  from_plan       → allocate đúng Σ planned_amount tháng đó của reserve+one_off trong BUDGET_ITEMS
                    (value = null — amount đến từ Sheet; bao gồm cả open-ended reserves)
  fixed           → cố định N triệu/tháng (value = VND) — dùng cho bucket BYPASS budget planning
                    (không tracked trong BUDGET_ITEMS; nếu surplus không đủ → partial fill + alert)
  pct_remaining   → N% của phần còn lại sau các bucket trên (value = %)
  remainder       → toàn bộ phần còn lại (value = null) — PHẢI là priority cuối cùng
```

**`from_plan` bao gồm tất cả BUDGET_ITEMS contributions** (không phân biệt có hay không có target/deadline):
- reserve có target+deadline → monthly contribution được tính tự động
- reserve có target, không deadline → finance nhập tay → vẫn thuộc `from_plan`
- reserve không có cả hai → finance nhập tay → vẫn thuộc `from_plan`

**Phân biệt `fixed` vs `from_plan`:**

| | `fixed` | `from_plan` |
|---|---|---|
| Amount định nghĩa ở đâu | ALLOCATION_POLICY (hardcode) | BUDGET_ITEMS (reserve/one_off rows) |
| Finance theo dõi monthly? | Không — set-and-forget trong policy | Có — cập nhật mỗi tháng trong Sheet |
| Ví dụ | Cổ tức cố định bypass ngân sách | Quỹ phúc lợi, để dành mua laptop, máy nén khí |
| Khi mục tiêu đủ | Không dừng tự động | Finance xóa/update dòng trong BUDGET_ITEMS |

### Thay đổi Policy tạm thời (1 tháng)

Effective dating cho phép thay đổi policy cho 1 tháng cụ thể rồi revert — hệ thống tự ghi nhận đúng từng kỳ.

**Ví dụ:** T7 tăng working capital lên 50%, T8 revert về 30%:

```
bucket          | rule_type     | value | effective_from | effective_to
Working capital | pct_remaining |  30   | 2026-01-01     | 2026-06-30   ← đóng
Working capital | pct_remaining |  50   | 2026-07-01     | 2026-07-31   ← T7 only
Working capital | pct_remaining |  30   | 2026-08-01     |              ← revert
```

Mart join `WHERE effective_from <= period_month AND (effective_to IS NULL OR effective_to >= period_month)` → T6 lấy dòng 1, T7 lấy dòng 2, T8+ lấy dòng 3. Không cần can thiệp gì thêm sau khi chỉnh Sheet.

**Quy tắc kỹ thuật bắt buộc:**

1. `mart_cash_surplus_allocation` phải dùng materialization **`table`** (full rebuild), KHÔNG phải `incremental`.
   - `table` → recalculate lại tất cả tháng, mỗi tháng dùng đúng policy của kỳ đó → correct
   - `incremental` → past months bị frozen kể cả khi CSV đã có đủ history rows → sai

2. Script pull Sheet phải **validate không có gap hoặc overlap** trong `effective_from`/`effective_to` cho cùng 1 bucket:
   - Gap → mart trả về 0 rows cho tháng đó (bucket bị bỏ qua im lặng)
   - Overlap → mart trả về 2 rows cho cùng tháng (double-allocate)
   - Nếu phát hiện → reject + báo lỗi rõ dòng nào bị conflict

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
| **Reserve Status** | Mỗi item theo 3 chế độ hiển thị (xem bên dưới) | Monthly |
| **Allocation Tracker** | Tháng vừa rồi: thặng dư phân bổ ra sao | Monthly |
| **Upcoming Large Items** | Khoản đặc biệt sắp đến (one_off + reserve chưa đủ) | Monthly |
| **Cash Coverage Weeks** | Tuần buffer hiện tại vs. target 8 tuần | Weekly |

**Reserve Status — 3 chế độ hiển thị:**

| Loại reserve | Dashboard hiển thị |
|---|---|
| target + deadline | Progress bar %, months left, on-track / behind |
| target, không deadline | Progress bar %, "còn thiếu X" — không áp lực thời gian |
| Không target, không deadline | "Đã tích lũy X" — open-ended accumulation |

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
| GL modeling | `plans/260707-1207-misa-gl-infrastructure/phase-02-gl-modeling.md` | ✅ Done |
| Cashflow report | `plans/260702-1727-misa-cashflow-budget-planner/phase-03-cashflow-report.md` | ✅ Done (live) |
| Budget hybrid layer | `plans/260702-1727-misa-cashflow-budget-planner/phase-04-budget-hybrid.md` | ✅ Done |
| MISA budget scraper | — | ❌ Dropped (finance không dùng MISA budget module) |
| Finance domain | `docs/analytics-handbook/domains/finance.md` | — |
| Cashflow design spec | `docs/analytics-handbook/designs/finance_cashflow.md` | — |

---

*Cập nhật: 2026-07-03 — thêm Sections 4-6 từ thảo luận thiết kế Phase 04 (Option C Sheet, irregular items, sinking fund, Cash Allocation Waterfall).*
