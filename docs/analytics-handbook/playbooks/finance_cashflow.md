# Playbook: Finance — Báo cáo Dòng tiền Vận hành (Operational Cashflow)

> **Tài liệu này mô tả mục đích và cách sử dụng dashboard/report từ góc nhìn người dùng nghiệp vụ.**
> Nó giải thích dashboard dành cho ai, dùng để trả lời câu hỏi nào, cần đọc theo luồng nào, dùng những metric nào từ domain documents, và khi thấy tín hiệu bất thường thì ai cần làm gì.
> Playbook không định nghĩa công thức tính metric; mọi logic nghiệp vụ phải được tham chiếu từ `domains/`.

## Overview

- **Audience:** CEO, CFO, Kế toán trưởng
- **Goal:** Theo dõi dòng tiền vận hành thực tế hàng tháng — tổng thu, tổng chi, số dư quỹ, và breakdown chi tiết theo nhóm nghiệp vụ (cashflow_line). Phương pháp: trực tiếp (thu-chi + số dư quỹ). Không phải báo cáo lưu chuyển tiền tệ gián tiếp theo TT200.
- **Tool:** metabase (primary), evidence (offline/static mirror)
- **Collection:** `Finance`
- **Cadence:** Monthly review (đọc sau khi tháng kế toán đóng) cho View 1; Quarterly/Annual review (MBR, board review) cho View 2 — Xu hướng nhiều năm
- **Domain Reference:** [domains/finance.md — Context: Cashflow (Dòng tiền vận hành)](../domains/finance.md#context-cashflow-dòng-tiền-vận-hành)
- **Blueprint (Metabase):** [blueprints/metabase/finance_cashflow.md](../blueprints/metabase/finance_cashflow.md)
- **Blueprint (Evidence):** [blueprints/evidence/finance_cashflow.md](../blueprints/evidence/finance_cashflow.md) — same metrics/recon anchor; no interactive filter, waterfall/combo/pivot approximated (see blueprint's Deviations table)

## Data Lineage

- **Core Model:** [`fact_cash_movement`](../../../transformation/models/marts/finance/fact_cash_movement.sql) — 1 row per MISA cash journal line (111x/112x accounts). Built and validated (phase-03).
- **Balance Model:** [`fact_account_balance_monthly`](../../../transformation/models/marts/finance/fact_account_balance_monthly.sql) — opening/closing balance per (account_code, period_month). **Planned phase-02** — needed for zero-movement months.
- **Dimension:** [`dim_gl_account`](../../../transformation/models/marts/core/dim_gl_account.sql) — account_code, cashflow_line taxonomy, is_cash flag.
- **Key rule:** `is_internal_transfer = TRUE` rows are HARDCODED-excluded from all thu/chi totals. These are intra-fund transfers between 111/112 accounts that net to zero and must never appear in user-visible inflow/outflow numbers.

## Key Business Questions

Questions answered **now** (phase-03 data available):

| # | Question | Metric |
|---|----------|--------|
| 1 | Tháng này quỹ tăng hay giảm? | `net_cash_flow` |
| 2 | Tổng thu vào quỹ là bao nhiêu? Từ đâu? | `cash_inflow` by `cashflow_line` |
| 3 | Tổng chi ra ngoài là bao nhiêu? Chi vào đâu? | `cash_outflow` by `cashflow_line` |
| 4 | Số dư quỹ cuối kỳ? | `cash_balance` |
| 5 | Chi tiết từng giao dịch? | Drill to voucher_no / offset_account |

Questions answered **now once multi-year backfill (2022→present) ingest xong** — cùng model, không cần build gì thêm:

| # | Question | Metric |
|---|----------|--------|
| 6 | Tháng này so với cùng kỳ năm trước tăng/giảm bao nhiêu? (loại nhiễu mùa vụ so với MoM) | `net_cash_flow_yoy_pct` (CF5) |
| 7 | Lũy kế năm nay tính đến giờ so với cùng mốc năm ngoái ra sao? | `net_cash_flow_ytd` (CF6) |
| 8 | Tháng nào trong năm lịch sử luôn cao/thấp (mùa vụ lương T13, thưởng Tết...)? | `seasonality_index` (CF7) |
| 9 | Khoản chi nào (cashflow_line) đang tăng trưởng cấu trúc qua nhiều năm, không phải one-off? | `cash_outflow` by `cashflow_line`, multi-year trend |

Questions answered **after phase-04** (needs `fact_cashflow_budget`):

| # | Question | Status |
|---|----------|--------|
| 10 | Thu/chi so với kế hoạch tháng như thế nào? | Planned (phase-04) |
| 11 | Số dư quỹ dự báo cuối quý? | Planned (phase-04) |

## Reading Flow

**View 1 — Dòng tiền Vận hành (monthly, mỗi tháng):**

1. **Số dư quỹ** — Đây là số tuyệt đối "tiền trong két và ngân hàng hôm nay". Đủ để vận hành ≥ 1 tháng tới không?
2. **Net cash flow** — Kỳ này dương hay âm? So với kỳ trước (MoM) như thế nào?
3. **Tổng thu breakdown** — Thu từ đâu? Chủ yếu từ "Bán hàng & phải thu KH" hay có nguồn bất thường?
4. **Tổng chi breakdown** — Chi nhiều nhất vào đâu (Lương / BHXH / NCC / QLDN)? Khoản nào tăng bất thường?
5. **Action** — Nếu net_cash_flow âm liên tục hoặc cash_balance < 1 tháng chi phí → escalate CFO ngay.

**View 2 — Xu hướng nhiều năm (quarterly/annual, MBR/board review — chỉ hữu ích khi ≥13 tháng lịch sử):**

6. **Lũy kế YTD vs cùng kỳ năm trước** — Năm nay đang tốt hơn hay xấu hơn cùng mốc năm ngoái?
7. **Số dư quỹ toàn lịch sử** — Xu hướng dài hạn: quỹ đang tăng trưởng cấu trúc hay dao động quanh 1 mức?
8. **Thu/chi theo năm** — Tăng trưởng YoY theo năm có tương xứng với tăng trưởng doanh thu/quy mô công ty không?
9. **Mùa vụ (heatmap năm × tháng)** — Tháng nào lặp lại pattern cao/thấp mọi năm? (VD: chi luôn đột biến Q1 do lương T13 + Tết)
10. **Cơ cấu chi theo cashflow_line qua các năm** — Khoản chi nào đang tăng trưởng cấu trúc (cần review dài hạn) vs khoản chi biến động 1 lần?
11. **Action** — Nếu 1 cashflow_line tăng YoY liên tục ≥ 3 năm và tăng nhanh hơn tổng chi → đưa vào review cost structure hàng quý với CFO.

## Filters

**View 1:**
- **period_month** — Bộ lọc chính. Default: tháng trước (tháng kế toán vừa đóng). Range: 12 tháng gần nhất (giữ glanceable — full history ở View 2).
- **cash_account** — 111 (tiền mặt) / 112 (ngân hàng) / ALL. Default: ALL.

**View 2:**
- **year_range** — Range chọn số năm hiển thị (default: toàn bộ lịch sử có, tối thiểu hiển thị từ năm đầu backfill 2022 nếu có).
- Không có filter theo tháng đơn lẻ — view này để nhìn pattern nhiều năm, không phải drill 1 tháng cụ thể (đó là việc của View 1).

**Không có filter is_internal_transfer** — đây là hardcoded exclusion ở tất cả các metric, không phải lựa chọn người dùng.

## Action Triggers

| Metric | Threshold | Owner | Action |
|--------|-----------|-------|--------|
| `net_cash_flow` | Âm ≥ 2 tháng liên tiếp | CFO | Review chi theo cashflow_line, xem xét điều chỉnh kế hoạch thu chi |
| `cash_balance` | < tổng chi trung bình 1 tháng | CFO, Kế toán trưởng | Cảnh báo thanh khoản — ưu tiên thu hồi công nợ, trì hoãn chi không cấp thiết |
| `cash_outflow` (cashflow_line = Lương) | Tăng > 20% MoM đột ngột | Kế toán trưởng | Xác minh bảng lương + BHXH — có thể trả 2 kỳ trong 1 tháng |
| `cash_outflow` (cashflow_line = NCC) | Tăng > 50% MoM | CFO | Review hợp đồng mua hàng, kiểm tra thanh toán trước hạn |
| `cash_inflow` | Giảm > 30% MoM | CEO, CFO | Kiểm tra công nợ KH, doanh thu tháng, xem finance_pl.md |
| `net_cash_flow_yoy_pct` | Âm > 20% so với cùng kỳ năm trước, không giải thích được bằng mùa vụ (`seasonality_index`) | CFO | Phân biệt suy giảm thật vs lệch mùa vụ trước khi báo động |
| `cash_outflow` by `cashflow_line`, multi-year | 1 line tăng YoY liên tục ≥ 3 năm, tốc độ nhanh hơn tổng chi | CFO | Đưa vào review cost structure hàng quý — có thể là chi phí cấu trúc (tăng nhân sự, thuê mặt bằng) cần kế hoạch dài hạn thay vì xử lý từng tháng |

## Visualizations

### Section 1: Tổng quan số dư quỹ

| Chart Title | Visualization Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **Số dư quỹ** | Scalar | [cash_balance](../domains/finance.md#cf1-số-dư-quỹ-cash_balance) | Closing balance tháng được chọn. VND. |
| **Dòng tiền ròng** | Scalar | [net_cash_flow](../domains/finance.md#cf4-dòng-tiền-ròng-net_cash_flow) | Dương = tốt. Color: green if > 0, red if < 0. |
| **Tổng thu** | Scalar | [cash_inflow](../domains/finance.md#cf2-tổng-thu-cash_inflow) | Excl. internal transfers. |
| **Tổng chi** | Scalar | [cash_outflow](../domains/finance.md#cf3-tổng-chi-cash_outflow) | Excl. internal transfers. |

### Section 2: Xu hướng theo tháng

| Chart Title | Visualization Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **Thu/Chi theo tháng** | Combo Chart | [cash_inflow](../domains/finance.md#cf2-tổng-thu-cash_inflow), [cash_outflow](../domains/finance.md#cf3-tổng-chi-cash_outflow) | Bar: Thu (xanh), Chi (đỏ). Line: Số dư quỹ. 12-month rolling. |
| **Số dư quỹ trend** | Line Chart | [cash_balance](../domains/finance.md#cf1-số-dư-quỹ-cash_balance) | Closing balance cuối từng tháng. Annotate nếu giảm 2 tháng liên tiếp. |

### Section 3: Breakdown chi tiết

| Chart Title | Visualization Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **Chi theo nhóm (cashflow_line)** | Horizontal Bar | [cash_outflow](../domains/finance.md#cf3-tổng-chi-cash_outflow) | Sort descending. Group by cashflow_line. Tháng được chọn. |
| **Thu theo nhóm (cashflow_line)** | Horizontal Bar | [cash_inflow](../domains/finance.md#cf2-tổng-thu-cash_inflow) | Sort descending. Group by cashflow_line. |
| **Chi tiết giao dịch** | Data Table | All CF metrics | Columns: posting_date, offset_account_name, cashflow_line, direction, amount, voucher_no, description. Filterable. |

### Section 4: Xu hướng nhiều năm (View 2 — cần ≥13 tháng lịch sử)

| Chart Title | Visualization Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **Lũy kế YTD vs năm trước** | Scalar w/ comparison | [net_cash_flow_ytd](../domains/finance.md#cf6-lũy-kế-từ-đầu-năm-net_cash_flow_ytd) | Comparison = YTD cùng mốc tháng năm trước, không phải total năm trước |
| **Số dư quỹ toàn lịch sử** | Area Chart | [cash_balance](../domains/finance.md#cf1-số-dư-quỹ-cash_balance) | Full history, không giới hạn 12 tháng |
| **Thu/chi theo năm** | Grouped Bar | [cash_inflow](../domains/finance.md#cf2-tổng-thu-cash_inflow), [cash_outflow](../domains/finance.md#cf3-tổng-chi-cash_outflow) | 1 cột/năm, kèm % YoY label |
| **Mùa vụ dòng tiền** | Heatmap | [seasonality_index](../domains/finance.md#cf7-chỉ-số-mùa-vụ-theo-tháng-seasonality_index) | Rows = năm, Columns = tháng (1-12), intensity = net_cash_flow. Cần ≥3 năm để đáng tin. |
| **Cơ cấu chi theo năm** | Stacked Bar (time) | [cash_outflow](../domains/finance.md#cf3-tổng-chi-cash_outflow) by cashflow_line | X = năm, stack = cashflow_line — thấy khoản nào tăng tỷ trọng qua thời gian |
| **Bảng tổng hợp theo năm** | Pivot Table | All CF metrics | rows = cashflow_line, columns = năm, kèm YoY % — annual grain, khác bảng monthly ở Section 3 |

## Implementation Notes

### Data Constraints

1. **is_internal_transfer exclusion is mandatory.** June-2026 recon: 299M internal transfers between 111/112 — if included, thu/chi are inflated by ~64%. The mart sets this flag; always verify flag coverage before go-live.
2. **Metabase serving TZ = Asia/Ho_Chi_Minh (ICT).** `posting_date` and `period_month` in `fact_cash_movement` are already ICT — no manual offset needed in WHERE clauses.
3. **Zero-movement months.** Until `fact_account_balance_monthly` (phase-02) is live, `cash_balance` is derived from the last `running_balance` row per account per month. Months with no transactions for an account will have gaps — interim workaround: COALESCE with prior month's closing via LAG window.
4. **cashflow_line taxonomy is provisional.** Derived from offset_account prefix in `dim_gl_account`. Needs finance team sign-off before use in official management reports.
5. **View 2 (multi-year) needs continuous monthly history.** MISA GL backfill (2022→present) is downloaded to staging but not yet ingested — YoY/YTD queries use `LAG(..., 12)` which assumes no gaps in `period_month`. Verify gapless series before enabling View 2; if gaps exist, use `generate_series` to pad missing months first.

### What Is NOT Covered Here

| Feature | Status |
|---------|--------|
| Budget-vs-Actual variance | Phase-04 (`fact_cashflow_budget` not built) |
| Cash flow forecast / projection | Phase-04 |
| AR/AP aging | Separate domain (Balance Sheet & Liquidity — Planned) |
| TT200 3-section indirect statement | Out of scope for this report |

### Recon Anchor for QA

Use June-2026 as validation baseline when deploying:

| Item | Expected |
|------|----------|
| Opening balance | 134.2M VND |
| cash_inflow | 464.4M VND |
| cash_outflow | 434.0M VND |
| net_cash_flow | +30.4M VND |
| cash_balance (closing) | 164.5M VND |
| Internal transfers (must be excluded) | 299M VND |

---

## Open Questions

1. **cashflow_line taxonomy sign-off** — Current labels are prefix-derived from dim_gl_account. Finance team must review and approve groupings before this report is used for management decisions. Who is the sign-off owner and what is the target date?
2. **fact_account_balance_monthly timeline** — Phase-02 dependency. Until live, zero-movement months have balance gaps. What is the expected delivery date?
3. **Budget comparison (phase-04)** — `fact_cashflow_budget` not yet planned. When can finance provide monthly budget figures for thu/chi?
4. **111 vs 112 split** — Is the CFO audience interested in seeing cash-in-hand (111) vs bank (112) as separate views, or only combined ALL?
5. **View 2 activation timing** — Multi-year backfill ingest is owned by another agent/process. Should View 2 ship hidden/disabled until history is confirmed gapless (≥13 months), or ship with a visible "data còn thiếu" caveat banner that clears itself once history is complete?
6. **seasonality_index reliability threshold** — Spec sets ≥3 years as a soft minimum for trusting seasonality_index. Does finance want a harder gate (e.g., hide the heatmap card entirely until 3 full years exist) instead of showing it with a low-confidence caveat?
