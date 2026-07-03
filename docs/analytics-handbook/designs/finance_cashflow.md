---
title: Finance — Báo cáo Dòng tiền Vận hành
archetype: Executive Pulse (View 1) + Exploratory Tool (View 2)
status: phase-03-ready; View 2 spec-ready, waiting on multi-year MISA backfill ingest
last_modified: 2026-07-03
domain_refs: [domains/finance.md]
phase_note: "View 1 cards 1,2,3(actual),4(balance),5,6 = phase-03 buildable. Budget columns in card 3 + forecast dashed line in card 4 = phase-04. View 2 (all cards) = buildable now on fact_cash_movement, but only meaningful once multi-year backfill (2022→present) lands — CF5-CF7 need ≥13 gapless months, seasonality_index needs ≥3 years for reliability."
---

## Design Spec: Finance — Báo cáo Dòng tiền Vận hành

> **Tài liệu này là bản thiết kế tool-agnostic cho dashboard/report.**
> Nó chuyển playbook thành cấu trúc trình bày cụ thể: views, card roles, loại biểu đồ chuẩn, bộ lọc, thứ tự đọc, so sánh cần có, màu sắc/kích thước theo semantic tokens và các yêu cầu trải nghiệm phân tích.
> Design spec là hợp đồng giữa Analytics Design và bước triển khai BI; nó không phụ thuộc vào bất kỳ công cụ BI hay nền tảng triển khai cụ thể nào, nhưng được dùng làm input để tạo blueprint triển khai cho công cụ BI được chọn.

### Brief

**View 1 — Dòng tiền Vận hành (monthly):**

- **Audience:** CEO, CFO, Kế toán trưởng — review dòng tiền hàng tháng
- **Time budget:** 10 phút, trong buổi MBR hoặc review tài chính cuối tháng
- **Primary question:** Số dư quỹ cuối kỳ là bao nhiêu? Dòng tiền ròng dương hay âm?
- **Decision enabled:** Điều chỉnh kế hoạch chi, đánh giá áp lực thanh khoản, phân bổ nguồn tiền
- **Comparison frame:** MoM, waterfall breakdown theo cashflow_line
- **Archetype:** Executive Pulse (single view, glanceable for CFO in monthly MBR)

**View 2 — Xu hướng nhiều năm (quarterly/annual, ADDED — leverages 2022→present backfill):**

- **Audience:** CEO, CFO — quarterly/annual review, board deck prep
- **Time budget:** 10-15 phút, không cần glanceable — người đọc chấp nhận đào sâu hơn View 1
- **Primary question:** Dòng tiền năm nay so với các năm trước ra sao — theo mùa vụ hay theo xu hướng cấu trúc?
- **Decision enabled:** Review cost structure dài hạn (lương, thuê mặt bằng…), phân biệt biến động mùa vụ (bình thường, lặp lại mỗi năm) với suy giảm thật cần can thiệp, chuẩn bị board deck với YoY/multi-year context
- **Comparison frame:** YoY (cùng tháng năm trước), YTD vs YTD, seasonality (trung bình theo tháng dương lịch qua các năm)
- **Archetype:** Exploratory Tool (nhiều card hơn, chấp nhận đọc lâu hơn — không cần ≤10 card như Executive Pulse)
- **Why a second view, not extend View 1:** Different cadence (quarterly/annual vs monthly), different reading behavior (đào sâu vs glanceable) — trộn chung sẽ phá vỡ Executive Pulse's ≤10-card density budget. Xem `COMPOSITION_PATTERNS.md` §4 View Grouping — "nhiều audiences/purposes khác nhau" → multi-view.

**Shared:**

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
| So cùng kỳ năm trước | `net_cash_flow_yoy_pct` | `(this_month − same_month_last_year) / ABS(same_month_last_year)` | View 2 only. Needs ≥13 gapless months — see [domains/finance.md#cf5](../domains/finance.md#cf5-so-sánh-cùng-kỳ-năm-trước-net_cash_flow_yoy_pct) |
| Lũy kế từ đầu năm | `net_cash_flow_ytd` | `SUM(metric) WHERE calendar_month <= calendar_month(today), GROUP BY year` | View 2 only. Compare YTD vs YTD, not YTD vs full prior year — see [domains/finance.md#cf6](../domains/finance.md#cf6-lũy-kế-từ-đầu-năm-net_cash_flow_ytd) |
| Chỉ số mùa vụ | `seasonality_index` | `AVG(net_cash_flow) GROUP BY calendar_month, across years` | View 2 only. Reliable at ≥3 years observed — see [domains/finance.md#cf7](../domains/finance.md#cf7-chỉ-số-mùa-vụ-theo-tháng-seasonality_index) |

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
| Kỳ (period_month) | date/month-picker | Current month | View 1, all cards | Xem dòng tiền theo từng tháng |
| Tài khoản tiền (cash_account) | category/single-select | All (111+112 combined) | View 1, all cards | Tách riêng tiền mặt (111) vs tiền gửi (112) khi cần |
| Khoảng năm (year_range) | date/range (year grain) | Toàn bộ lịch sử có (từ 2022 nếu backfill đã ingest) | View 2, all cards | Board review đôi khi chỉ muốn xem 3 năm gần nhất thay vì toàn bộ; không filter theo tháng đơn lẻ ở view này |

---

### Views

Two views: **Dòng tiền Vận hành** (View 1, monthly) + **Xu hướng nhiều năm** (View 2, quarterly/annual — new)

---

### Composition — View 1: Dòng tiền Vận hành

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Tổng quan dòng tiền kỳ này — số dư, thu, chi và dòng tiền ròng" | annotation | text-annotation | structural | full-width × minimal | Dashboard subtitle | — |
| 2 | B | Số dư quỹ cuối kỳ | hero | single-value-with-trend | primary | one-third × short, prominent | Số dư tài khoản 111+112 cuối kỳ | vs previous period (MoM); once ≥13 months history: small companion text below row showing YoY delta (không thêm card mới, không phá density budget) |
| 3 | B | Dòng tiền ròng | supporting | single-value-with-trend | positive/negative | one-quarter × short, standard | Net = thu − chi kỳ này | vs previous period (MoM) |
| 4 | B | Tổng thu | supporting | single-value-with-trend | positive | one-quarter × short, standard | Tổng tiền vào (excl. transfer) | vs previous period (MoM) |
| 5 | B | Tổng chi | supporting | single-value-with-trend | negative | one-quarter × short, standard | Tổng tiền ra (excl. transfer) | vs previous period (MoM) |
| 6 | C | "Biểu đồ thác nước — dòng tiền hình thành như thế nào từ đầu đến cuối kỳ" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 7 | D | Waterfall dòng tiền kỳ này | breakdown | waterfall | positive (inflow bars) + negative (outflow bars) + primary (opening/closing totals) | full-width × medium, standard | Số dư đầu kỳ → +thu theo cashflow_line → −chi theo cashflow_line → Số dư cuối kỳ | additive (opening → closing recon) |
| 8 | E | "Bảng chi tiết theo dòng tiền — để đọc, kiểm tra và xuất báo cáo" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 9 | F | Chi tiết thu/chi theo cashflow_line | detail | pivot-table | conditional-above (inflow positive) + conditional-below (outflow/variance negative) | full-width × tall, standard | rows = cashflow_line; columns = tháng (phase-03: actual only; phase-04: Kế hoạch \| Thực tế \| Chênh lệch \| %) | MoM (phase-03) / vs budget (phase-04) |
| 10 | G | "Xu hướng số dư quỹ — thanh khoản đang tăng hay giảm?" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 11 | H | Xu hướng số dư quỹ theo tháng | trend | area-chart | primary (actual balance) + muted (dashed forecast — phase-04) | two-thirds × medium, standard | Số dư 111+112 closing theo tháng; **default window 24 tháng** (tăng từ 12 — vẫn glanceable, không phải full history) | MoM trend; forecast continuation when phase-04 |
| 12 | H | Thu vs chi vs ròng theo tháng | breakdown | combo-chart | series-1 (thu bar) + series-2 (chi bar) + primary (net line) | one-third × medium, standard | Cột thu/chi mỗi tháng + line dòng tiền ròng; **default window 24 tháng** | MoM |
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

### Composition — View 2: Xu hướng nhiều năm

> Gate: mọi card ở view này chỉ bật khi `fact_cash_movement` có ≥13 tháng liên tục gapless (CF5/CF6); heatmap (card 22) cần ≥3 năm để `seasonality_index` đáng tin — nếu chưa đủ, hiện caveat "cần thêm N năm dữ liệu" thay vì ẩn hẳn card.

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 15 | A | "Xu hướng nhiều năm — dòng tiền năm nay so với các năm trước ra sao, theo mùa vụ hay theo cấu trúc?" | annotation | text-annotation | structural | full-width × minimal | View subtitle | — |
| 16 | B | Lũy kế dòng tiền ròng YTD | hero | single-value-with-trend | positive/negative | one-third × short, prominent | `net_cash_flow_ytd` năm hiện tại | vs YTD cùng mốc tháng năm trước (CF6) |
| 17 | B | Tổng thu YTD | supporting | single-value-with-trend | positive | one-third × short, standard | `cash_inflow_ytd` | vs YTD năm trước |
| 18 | B | Tổng chi YTD | supporting | single-value-with-trend | negative | one-third × short, standard | `cash_outflow_ytd` | vs YTD năm trước |
| 19 | C | "Số dư quỹ toàn lịch sử — xu hướng dài hạn" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 20 | D | Số dư quỹ — full history | trend | area-chart | primary | full-width × medium, standard | `cash_balance` toàn bộ lịch sử có (không giới hạn 12/24 tháng như View 1) | Long-run trend — không so kỳ đơn lẻ |
| 21 | E | "Mùa vụ dòng tiền — tháng nào lịch sử luôn cao/thấp?" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 22 | F | Heatmap mùa vụ (năm × tháng) | breakdown | heatmap | positive/negative diverging (net_cash_flow cao=đậm xanh, thấp/âm=đậm đỏ) | full-width × medium, standard | Rows = năm, Columns = tháng 1-12, intensity = `net_cash_flow`; annotate `years_observed` | Pattern lặp lại qua các năm — không phải 1 kỳ so 1 kỳ |
| 23 | G | "Thu/chi theo năm — tăng trưởng có tương xứng quy mô không?" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 24 | H | Thu vs chi theo năm | breakdown | grouped-bar | series-1 (thu) + series-2 (chi) | two-thirds × medium, standard | 1 nhóm cột/năm: thu cạnh chi, label % YoY trên mỗi cột | YoY (rank theo năm) |
| 25 | H | Bảng tổng hợp theo năm | detail | data-table-formatted | conditional-above (YoY dương) + conditional-below (YoY âm) | one-third × medium, standard | Năm, thu, chi, ròng, YoY % — compact recap cạnh chart | YoY |
| 26 | I | "Cơ cấu chi theo cashflow_line qua các năm — khoản nào tăng trưởng cấu trúc?" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 27 | J | Cơ cấu chi theo năm (stacked) | breakdown | stacked-bar-time | categorical palette theo cashflow_line (không dùng positive/negative — đây là composition, không phải delta) | two-thirds × medium, standard | X = năm, stack = cashflow_line — tỷ trọng nhóm nào phình ra qua thời gian | Composition over time |
| 28 | J | Top cashflow_line tăng nhanh nhất | breakdown | horizontal-bar | negative (chi luôn là outflow) | one-third × medium, standard | Ranking cashflow_line theo tốc độ tăng trưởng YoY trung bình (không phải theo tổng giá trị — khác card 14 ở View 1) | rank by growth rate |
| 29 | K | Chi tiết theo cashflow_line × năm | detail | pivot-table | conditional-above/below | full-width × tall, standard | rows = cashflow_line; columns = năm; values = tổng chi + YoY % — annual grain, bổ sung cho pivot monthly ở View 1 card 9 | YoY |

**Phase mapping per card (View 2):** Tất cả cards 15-29 buildable ngay trên `fact_cash_movement` hiện có (không cần model mới) — nhưng chỉ nên deploy khi multi-year backfill ingest xong, xem gate note ở đầu section.

**View grouping note:** 15 cards ở View 2 vượt mức Executive Pulse (≤10) nhưng nằm trong Exploratory Tool limit (>15, chấp nhận được — xem `VISUAL_LANGUAGE.md` §8 Density Budget). Đây là lý do tách thành view riêng thay vì nhồi vào View 1.

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

**View 2 — Multi-year visual language (additions):**

- **Heatmap color (card 22):** diverging scale — `positive` token (đậm xanh) for high net_cash_flow months, `negative` token (đậm đỏ) for low/negative months, neutral midpoint at 0. Always show `years_observed` as a footnote — a heatmap built from 2 years reads as confidently as one built from 5 if not labeled.
- **Grouped-bar thu/chi by year (card 24):** thu and chi use the SAME positive/negative tokens as View 1 (consistency across views) — do not introduce a new color pair just because it's "by year" instead of "by month".
- **Stacked-bar-time cashflow_line by year (card 27):** use categorical palette (one hue per cashflow_line), NOT positive/negative — this card shows composition, not a delta signal. Cap at ≤7 visible cashflow_line series; group smaller lines into "Khác" if taxonomy has more (same rule as `donut` anti-pattern, applied to stack count instead of slice count).
- **View 2 anti-patterns (additional):**
  - No `multi-line-chart` with one line per year overlaid on a Jan-Dec x-axis to show seasonality — reads cluttered past 3 years; use `heatmap` instead (card 22 already covers this need).
  - No mixing YoY % and absolute VND on the same axis without dual-axis labeling (card 24/25 keep them in separate cards instead of forcing one chart to carry both).

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
| Lũy kế YTD (View 2) | YTD âm hơn cùng mốc năm trước | YoY YTD < −15% | Phân biệt lệch mùa vụ (check heatmap card 22) vs suy giảm thật; nếu thật, escalate CFO |
| Heatmap mùa vụ (View 2) | Tháng nào đó luôn âm/thấp bất thường mọi năm | seasonality_index[m] < 0 với years_observed ≥ 3 | Đây là pattern cấu trúc (VD: thuế/lương T13) — đưa vào kế hoạch dự trữ quỹ trước mỗi năm, không phải xử lý bị động |
| Cơ cấu chi theo năm (View 2) | 1 cashflow_line tăng tỷ trọng liên tục | Tỷ trọng/tổng chi tăng ≥ 3 năm liên tiếp | Review cost structure hàng quý với CFO — có thể cần kế hoạch dài hạn (tuyển dụng, thuê mặt bằng) thay vì cắt giảm ngắn hạn |

<!--
Dashboard Finish Checklist:

View 1 — Dòng tiền Vận hành:
- [x] Hero card (Số dư quỹ cuối kỳ) at top-left, prominent size
- [x] Every KPI has MoM comparison
- [x] Row widths = 18: B=6+4+4+4, D=full, F=full, H=12+6, J=full (annotations full-width)
- [x] Total cards: 14 (annotations count; data cards = 7) — within Executive Pulse 10-card data limit
- [x] Trend cards (11, 12) window widened 12→24 months — still glanceable, full history deferred to View 2

View 2 — Xu hướng nhiều năm (new):
- [x] Hero card (Lũy kế YTD) distinct from View 1 hero — different primary question
- [x] Every KPI has YoY/YTD comparison (not MoM — MoM meaningless at this grain)
- [x] Row widths = 18: B=6+6+6, D=full, F=full, H=12+6, J=12+6, K=full (annotations full-width)
- [x] Total cards: 15 (annotations = 5; data cards = 10) — within Exploratory Tool limit, exceeds Executive Pulse (intentional, justified in Brief)
- [x] Gate condition stated (≥13 months for YoY/YTD, ≥3 years for seasonality_index) — no card silently shows unreliable data
- [x] Reuses fact_cash_movement only — no new dbt model required

Shared:
- [x] Semantic tokens only — no hex, no pixel, no tool names
- [x] Action Map complete for 9 key signals (6 View 1 + 3 View 2)
- [x] Anti-pattern list explicit per view (no pie, no 3D, no gauge, no year-per-line overlay)
- [x] Phase mapping declared per card (phase-03 vs phase-04 vs "buildable now, gated on backfill ingest")
- [x] is_internal_transfer hardcoded-excluded stated in constraints
- [x] Recon anchor documented in metric definitions
- [x] View grouping rationale documented (different cadence/audience-depth, not just "more metrics")
-->
