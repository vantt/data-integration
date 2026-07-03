# Playbook: Finance — Báo cáo Dòng tiền Vận hành (Operational Cashflow)

> **Tài liệu này mô tả mục đích và cách sử dụng dashboard/report từ góc nhìn người dùng nghiệp vụ.**
> Nó giải thích dashboard dành cho ai, dùng để trả lời câu hỏi nào, cần đọc theo luồng nào, dùng những metric nào từ domain documents, và khi thấy tín hiệu bất thường thì ai cần làm gì.
> Playbook không định nghĩa công thức tính metric; mọi logic nghiệp vụ phải được tham chiếu từ `domains/`.

## Overview

- **Audience:** CEO, CFO, Kế toán trưởng
- **Goal:** Theo dõi dòng tiền vận hành thực tế hàng tháng — tổng thu, tổng chi, số dư quỹ, và breakdown chi tiết theo nhóm nghiệp vụ (cashflow_line). Phương pháp: trực tiếp (thu-chi + số dư quỹ). Không phải báo cáo lưu chuyển tiền tệ gián tiếp theo TT200.
- **Tool:** metabase
- **Collection:** `Finance`
- **Cadence:** Monthly review (đọc sau khi tháng kế toán đóng)
- **Domain Reference:** [domains/finance.md — Context: Cashflow (Dòng tiền vận hành)](../domains/finance.md#context-cashflow-dòng-tiền-vận-hành)
- **Blueprint:** [blueprints/metabase/finance_cashflow.md](../blueprints/metabase/finance_cashflow.md) *(to be created — phase-03)*

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

Questions answered **after phase-04** (needs `fact_cashflow_budget`):

| # | Question | Status |
|---|----------|--------|
| 6 | Thu/chi so với kế hoạch tháng như thế nào? | Planned (phase-04) |
| 7 | Số dư quỹ dự báo cuối quý? | Planned (phase-04) |

## Reading Flow

1. **Số dư quỹ** — Đây là số tuyệt đối "tiền trong két và ngân hàng hôm nay". Đủ để vận hành ≥ 1 tháng tới không?
2. **Net cash flow** — Kỳ này dương hay âm? So với kỳ trước như thế nào?
3. **Tổng thu breakdown** — Thu từ đâu? Chủ yếu từ "Bán hàng & phải thu KH" hay có nguồn bất thường?
4. **Tổng chi breakdown** — Chi nhiều nhất vào đâu (Lương / BHXH / NCC / QLDN)? Khoản nào tăng bất thường?
5. **Action** — Nếu net_cash_flow âm liên tục hoặc cash_balance < 1 tháng chi phí → escalate CFO ngay.

## Filters

- **period_month** — Bộ lọc chính. Default: tháng trước (tháng kế toán vừa đóng). Range: 12 tháng gần nhất.
- **cash_account** — 111 (tiền mặt) / 112 (ngân hàng) / ALL. Default: ALL.

**Không có filter is_internal_transfer** — đây là hardcoded exclusion ở tất cả các metric, không phải lựa chọn người dùng.

## Action Triggers

| Metric | Threshold | Owner | Action |
|--------|-----------|-------|--------|
| `net_cash_flow` | Âm ≥ 2 tháng liên tiếp | CFO | Review chi theo cashflow_line, xem xét điều chỉnh kế hoạch thu chi |
| `cash_balance` | < tổng chi trung bình 1 tháng | CFO, Kế toán trưởng | Cảnh báo thanh khoản — ưu tiên thu hồi công nợ, trì hoãn chi không cấp thiết |
| `cash_outflow` (cashflow_line = Lương) | Tăng > 20% MoM đột ngột | Kế toán trưởng | Xác minh bảng lương + BHXH — có thể trả 2 kỳ trong 1 tháng |
| `cash_outflow` (cashflow_line = NCC) | Tăng > 50% MoM | CFO | Review hợp đồng mua hàng, kiểm tra thanh toán trước hạn |
| `cash_inflow` | Giảm > 30% MoM | CEO, CFO | Kiểm tra công nợ KH, doanh thu tháng, xem finance_pl.md |

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

## Implementation Notes

### Data Constraints

1. **is_internal_transfer exclusion is mandatory.** June-2026 recon: 299M internal transfers between 111/112 — if included, thu/chi are inflated by ~64%. The mart sets this flag; always verify flag coverage before go-live.
2. **Metabase serving TZ = Asia/Ho_Chi_Minh (ICT).** `posting_date` and `period_month` in `fact_cash_movement` are already ICT — no manual offset needed in WHERE clauses.
3. **Zero-movement months.** Until `fact_account_balance_monthly` (phase-02) is live, `cash_balance` is derived from the last `running_balance` row per account per month. Months with no transactions for an account will have gaps — interim workaround: COALESCE with prior month's closing via LAG window.
4. **cashflow_line taxonomy is provisional.** Derived from offset_account prefix in `dim_gl_account`. Needs finance team sign-off before use in official management reports.

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
