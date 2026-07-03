---
title: Finance — Báo cáo Dòng tiền Vận hành
archetype: Executive Pulse
status: phase-03-ready
last_modified: 2026-07-02
domain_refs: [domains/finance.md]
phase_note: "Cards 1,2,3(actual),4(balance),5,6 = phase-03 buildable. Budget columns in card 3 + forecast dashed line in card 4 = phase-04."
---

## Design Spec: Finance — Báo cáo Dòng tiền Vận hành

> **Tài liệu này là bản thiết kế tool-agnostic cho dashboard/report.**
> Nó chuyển playbook thành cấu trúc trình bày cụ thể: views, card roles, loại biểu đồ chuẩn, bộ lọc, thứ tự đọc, so sánh cần có, màu sắc/kích thước theo semantic tokens và các yêu cầu trải nghiệm phân tích.
> Design spec là hợp đồng giữa Analytics Design và bước triển khai BI; nó không phụ thuộc vào bất kỳ công cụ BI hay nền tảng triển khai cụ thể nào, nhưng được dùng làm input để tạo blueprint triển khai cho công cụ BI được chọn.

### Brief

- **Audience:** CEO, CFO, Kế toán trưởng — review dòng tiền hàng tháng
- **Time budget:** 10 phút, trong buổi MBR hoặc review tài chính cuối tháng
- **Primary question:** Số dư quỹ cuối kỳ là bao nhiêu? Dòng tiền ròng dương hay âm?
- **Decision enabled:** Điều chỉnh kế hoạch chi, đánh giá áp lực thanh khoản, phân bổ nguồn tiền
- **Comparison frame:** MoM, waterfall breakdown theo cashflow_line
- **Archetype:** Executive Pulse (single view, glanceable for CFO in monthly MBR)
- **Domain references:** [domains/finance.md](../domains/finance.md)
- **Playbook reference:** [playbooks/finance_cashflow.md](../playbooks/finance_cashflow.md)

### Data Sources

| Source | Grain | Key Fields Used |
|--------|-------|-----------------|
| `fact_cash_movement` | line × period_month | `period_month`, `cash_account`, `offset_account`, `cashflow_line`, `direction` (inflow/outflow), `is_internal_transfer`, `amount`, `running_balance`, `opening_balance` |
| `fact_account_balance_monthly` | account × month | `opening_balance`, `closing_balance` |
| `dim_gl_account` | account | `cashflow_line`, `is_cash` |

### Metric Definitions

| Metric | Column Alias | Formula | Notes |
|--------|-------------|---------|-------|
| Số dư quỹ cuối kỳ | `cash_balance` | `closing_balance` of accounts 111+112 | From `fact_account_balance_monthly` |
| Tổng thu | `cash_inflow` | `SUM(amount) WHERE direction='inflow' AND NOT is_internal_transfer` | Exclude internal transfers always |
| Tổng chi | `cash_outflow` | `SUM(amount) WHERE direction='outflow' AND NOT is_internal_transfer` | Exclude internal transfers always |
| Dòng tiền ròng | `net_cash_flow` | `cash_inflow − cash_outflow` | Positive = net inflow |
| Số dư đầu kỳ | `opening_balance` | `opening_balance` of accounts 111+112 | From `fact_account_balance_monthly` |

**Recon anchor (June-2026):** opening 134.2M → thu 464.4M → chi 434.0M → net +30.4M → closing 164.5M

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude internal transfers | `NOT is_internal_transfer` | All thu/chi metrics | Thu/chi thuần không bao gồm luân chuyển nội bộ giữa tài khoản tiền |
| Cash accounts only | `is_cash = TRUE` (dim_gl_account) | All cards | Chỉ tài khoản 111, 112 |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Kỳ (period_month) | date/month-picker | Current month | All cards | Xem dòng tiền theo từng tháng |
| Tài khoản tiền (cash_account) | category/single-select | All (111+112 combined) | All cards | Tách riêng tiền mặt (111) vs tiền gửi (112) khi cần |

---

### Views

Single view: **Dòng tiền Vận hành**

---

### Composition — View 1: Dòng tiền Vận hành

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Tổng quan dòng tiền kỳ này — số dư, thu, chi và dòng tiền ròng" | annotation | text-annotation | structural | full-width × minimal | Dashboard subtitle | — |
| 2 | B | Số dư quỹ cuối kỳ | hero | single-value-with-trend | primary | one-third × short, prominent | Số dư tài khoản 111+112 cuối kỳ | vs previous period (MoM) |
| 3 | B | Dòng tiền ròng | supporting | single-value-with-trend | positive/negative | one-quarter × short, standard | Net = thu − chi kỳ này | vs previous period (MoM) |
| 4 | B | Tổng thu | supporting | single-value-with-trend | positive | one-quarter × short, standard | Tổng tiền vào (excl. transfer) | vs previous period (MoM) |
| 5 | B | Tổng chi | supporting | single-value-with-trend | negative | one-quarter × short, standard | Tổng tiền ra (excl. transfer) | vs previous period (MoM) |
| 6 | C | "Biểu đồ thác nước — dòng tiền hình thành như thế nào từ đầu đến cuối kỳ" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 7 | D | Waterfall dòng tiền kỳ này | breakdown | waterfall | positive (inflow bars) + negative (outflow bars) + primary (opening/closing totals) | full-width × medium, standard | Số dư đầu kỳ → +thu theo cashflow_line → −chi theo cashflow_line → Số dư cuối kỳ | additive (opening → closing recon) |
| 8 | E | "Bảng chi tiết theo dòng tiền — để đọc, kiểm tra và xuất báo cáo" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 9 | F | Chi tiết thu/chi theo cashflow_line | detail | pivot-table | conditional-above (inflow positive) + conditional-below (outflow/variance negative) | full-width × tall, standard | rows = cashflow_line; columns = tháng (phase-03: actual only; phase-04: Kế hoạch \| Thực tế \| Chênh lệch \| %) | MoM (phase-03) / vs budget (phase-04) |
| 10 | G | "Xu hướng số dư quỹ — thanh khoản đang tăng hay giảm?" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 11 | H | Xu hướng số dư quỹ theo tháng | trend | area-chart | primary (actual balance) + muted (dashed forecast — phase-04) | two-thirds × medium, standard | Số dư 111+112 closing theo tháng; dashed extension = forecast (phase-04) | MoM trend; forecast continuation when phase-04 |
| 12 | H | Thu vs chi vs ròng theo tháng | breakdown | combo-chart | series-1 (thu bar) + series-2 (chi bar) + primary (net line) | one-third × medium, standard | Cột thu/chi mỗi tháng + line dòng tiền ròng | MoM |
| 13 | I | "Cơ cấu chi — khoản nào chiếm nhiều nhất?" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 14 | J | Top khoản chi theo cashflow_line | breakdown | horizontal-bar | negative (all bars, sorted desc by amount) | full-width × medium, standard | Ranking cashflow_line theo tổng chi — top N outflow lines | rank (current period) |

**Phase mapping per card:**

| Card # | Card name | Phase |
|--------|-----------|-------|
| 2–5 | Scorecard row | phase-03 |
| 7 | Waterfall | phase-03 |
| 9 | Pivot table (actual columns only) | phase-03 |
| 9 | Pivot table (budget columns + variance) | phase-04 |
| 11 | Area chart (actual line only) | phase-03 |
| 11 | Area chart (dashed forecast extension) | phase-04 |
| 12 | Combo chart | phase-03 |
| 14 | Horizontal bar | phase-03 |

---

### Visual Language

**Number formatting:** VND, abbreviated — dưới 1 tỷ dùng "M" (e.g., 164.5M), từ 1 tỷ trở lên dùng "tỷ" (e.g., 1.2 tỷ). Nhất quán toàn dashboard. Ký hiệu ₫ hoặc suffix "VND" kèm theo giá trị trong axis label và card subtitle.

**+/− semantics:**
- `positive` token: inflow bars (waterfall), Tổng thu card, net > 0
- `negative` token: outflow bars (waterfall), Tổng chi card, net < 0
- `conditional-above`/`conditional-below`: pivot-table variance cells (phase-04) và directional delta trong scorecard

**Waterfall bar encoding:**
- Opening/closing totals: `primary` (floating total bars)
- Inflow lines (+): `positive` (green up-bars)
- Outflow lines (−): `negative` (red down-bars)
- Bar labels: show VND amount (abbreviated) on each bar — do NOT hide labels (CFO needs exact values)

**Anti-patterns explicitly prohibited:**
- No pie/donut for cashflow_line breakdown — outflow categories typically >5 lines; use `horizontal-bar`
- No 3D charts of any kind
- No gauge — cash balance has no fixed healthy/unhealthy range threshold agreed
- No stacked area for thu/chi (hides the net line signal) — use `combo-chart`

**Forecast visual (phase-04 only):**
- Dashed line style for forecast portion in area-chart (card 11)
- Annotate dashed section with label "Dự báo" to avoid ambiguity

---

### Action Map

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| Số dư quỹ cuối kỳ | Sụt giảm mạnh | MoM < −20% | Kiểm tra cashflow_line chi lớn bất thường trong kỳ; xem waterfall |
| Dòng tiền ròng | Âm | net_cash_flow < 0 | Xem pivot table: dòng chi nào vượt kế hoạch; check Tổng chi vs Tổng thu ratio |
| Waterfall | Outflow line đột biến | 1 line chiếm > 40% tổng chi | Drill vào offset_account_name để xác định giao dịch cụ thể |
| Pivot table variance | Chênh lệch âm lớn | Variance < −10% so với kế hoạch (phase-04) | Review kế hoạch chi; escalate nếu > 20% |
| Xu hướng số dư quỹ | Xu hướng giảm liên tục | ≥ 3 tháng consecutive decline | Đánh giá áp lực thanh khoản; lên kế hoạch bổ sung nguồn tiền |
| Top khoản chi | Khoản chi leo top | Line mới xuất hiện trong top 3 | Xác nhận với kế toán: chi thường kỳ hay chi bất thường |

<!--
Dashboard Finish Checklist:
- [x] Hero card (Số dư quỹ cuối kỳ) at top-left, prominent size
- [x] Every KPI has MoM comparison
- [x] Row widths = 18: B=6+4+4+4, D=full, F=full, H=12+6, J=full (annotations full-width)
- [x] Total cards: 14 (annotations count; data cards = 7) — within Executive Pulse 10-card data limit
- [x] Semantic tokens only — no hex, no pixel, no tool names
- [x] Action Map complete for 6 key signals
- [x] Anti-pattern list explicit (no pie, no 3D, no gauge)
- [x] Phase mapping declared per card (phase-03 vs phase-04)
- [x] is_internal_transfer hardcoded-excluded stated in constraints
- [x] Recon anchor documented in metric definitions
-->
