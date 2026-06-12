---
spec_version: v1
status: approved
created: 2026-06-12
primary_scope: scope_retail
scope_indicator: "[Retail]"
layer: L2
audience: Marketing, CSKH
---

## Design Spec: Retail Activation Cockpit [Retail]

> **Tài liệu này là bản thiết kế tool-agnostic cho dashboard/report.**
> Nó chuyển playbook thành cấu trúc trình bày cụ thể: views, card roles, loại biểu đồ chuẩn, bộ lọc, thứ tự đọc, so sánh cần có, màu sắc/kích thước theo semantic tokens và các yêu cầu trải nghiệm phân tích.
> Design spec là hợp đồng giữa Analytics Design và bước triển khai BI; nó không phụ thuộc vào bất kỳ công cụ BI hay nền tảng triển khai cụ thể nào, nhưng được dùng làm input để tạo blueprint triển khai cho công cụ BI được chọn.

**Dashboard:** Retail Activation Cockpit [Retail]
**Collection:** Marketing & Customers
**Archetype:** Operational Cockpit (3 tabs — act, analyse, understand)
**Playbook ref:** `docs/analytics-handbook/playbooks/retail_activation_cockpit.md` (to-create)
**Domain refs:** `domains/customer.md`, `semantic/segments.md`, `semantic/metrics.md`

---

## Design Brief

| Field | Value |
|-------|-------|
| Audience | Marketing manager, CSKH ops |
| Purpose | This-week activation list + channel/margin insight + discount restructure signal |
| Hero Metric | Contactable customers OVERDUE/DUE_SOON (Tab A); Channel net margin by channel (Tab B); PROMO_DEPENDENT revenue leakage (Tab C) |
| Comparison Frame | Channel vs channel (Shopee neg vs owned pos); Discount segment vs margin |
| Time Budget | Tab A = current/live; Tab B = last 90d rolling; Tab C = all-time dim snapshot |
| Archetype | Operational Cockpit — not trend-analysis; calls to action per row/segment |

---

## Tab A — Activation Now

**Narrative arc:** "Who should we call this week, in priority order?"

| # | Card Name | Role | Viz | Color Token | Size |
|---|-----------|------|-----|-------------|------|
| A1 | Contactable — OVERDUE/DUE_SOON count | hero | `single-value` | `warning` / `negative` | one-third × short |
| A2 | LTV at Stake (contactable) | supporting | `single-value` | `accent` | one-third × short |
| A3 | Action Queue Table | detail | `data-table-formatted` | conditional on is_margin_negative | full-width × tall |
| A4 | Reactivation Mine — SILVER/GOLD/VIP At-Risk/Churned | supporting | `data-table` | n/a | full-width × medium |
| A5 | Source & Freshness | annotation | `text-annotation` | structural | full-width × minimal |

**Filters (Tab A):** action_type (CategoryDrop), value_group (CategoryDrop), is_contactable default=true (CategoryDrop)

---

## Tab B — Channel: Retention × Margin

**Narrative arc:** "Shopee = low retention AND negative margin → migrate to owned channels."

| # | Card Name | Role | Viz | Color Token | Size |
|---|-----------|------|-----|-------------|------|
| B1 | Channel Net Margin % by Channel | hero | `horizontal-bar` | positive/negative conditional | two-thirds × tall |
| B2 | Repeat Rate by Channel | breakdown | `horizontal-bar` | series-1 | one-third × tall |
| B3 | Channel × Retention × Margin table | detail | `data-table-formatted` | margin neg = red, repeat rate green/red | full-width × medium |
| B4 | Source & Freshness | annotation | `text-annotation` | structural | full-width × minimal |

---

## Tab C — Discount-Dependency × Margin

**Narrative arc:** "PROMO_DEPENDENT = 98.5% of base, eating 55% gross. Must redesign offer, not protect price."

| # | Card Name | Role | Viz | Color Token | Size |
|---|-----------|------|-----|-------------|------|
| C1 | Discount Sensitivity Distribution | hero | `donut` | negative/warning/positive for PROMO/MIXED/FULL | half × medium |
| C2 | Contribution Margin by Discount Sensitivity | breakdown | `horizontal-bar` | conditional (pos/neg) | half × medium |
| C3 | PROMO_DEPENDENT: Discount % of Gross Revenue | supporting | `single-value` | `negative` | one-third × short |
| C4 | 887 Margin-Negative Retail Customers | supporting | `single-value` | `negative` | one-third × short |
| C5 | Discount Sensitivity × Margin Detail | detail | `data-table-formatted` | is_margin_negative = red row | full-width × medium |
| C6 | Source & Freshness | annotation | `text-annotation` | structural | full-width × minimal |
