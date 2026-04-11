---
title: Finance P&L Dashboard
archetype: Executive Pulse
status: final
last_modified: 2026-04-10
domain_refs: [domains/finance.md]
---

## Design Spec: Finance P&L Dashboard

### Brief

- **Audience:** CFO, Finance Managers, CEO — monthly P&L review
- **Time budget:** 10 phut, trong buoi MBR hang thang
- **Primary question:** Bien loi nhuan gop co dat target khong? Chi phi san Shopee chiem bao nhieu?
- **Decision enabled:** Dieu chinh gia ban, toi uu kenh, review nha cung cap
- **Comparison frame:** MoM, vs threshold (40% gross margin), waterfall breakdown
- **Archetype:** Executive Pulse (3 views for different P&L aspects)
- **Domain references:** [domains/finance.md](../domains/finance.md)

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude cancelled orders | `status NOT IN ('CANCELLED','Voided')` | Tab 1 revenue cards | Revenue metrics exclude cancelled |
| Exclude promo lines | `NOT is_promo_line` | Tab 2 margin cards | Promo items distort margin |
| Only released payouts | `payout_released_at IS NOT NULL` | Tab 3 Shopee cards | Unreleased payouts incomplete |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Period | date/range | Last 30 days | All cards | View different periods |
| Channel | category/single-select | All | Tab 2 cards | Isolate channel for margin |

### Views

Multi-view: **P&L Overview**, **Channel Profitability**, **Shopee Economics**

---

### Composition — View 1: P&L Overview

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Doanh thu va loi nhuan gop — ket qua kinh doanh ky nay" | annotation | text-annotation | structural | full-width x minimal | Dashboard subtitle | — |
| 2 | B | Net Revenue MTD | hero | single-value-with-trend | primary | one-third x short, prominent | Doanh thu thuan ky nay | vs previous period |
| 3 | B | COGS MTD | supporting | single-value-with-trend | negative | one-quarter x short, standard | Gia von ky nay | vs previous period |
| 4 | B | Gross Profit MTD | supporting | single-value-with-trend | positive/negative | one-quarter x short, standard | Lai gop ky nay | vs previous period |
| 5 | B | Gross Margin % | supporting | gauge | positive(>40%)/warning(25-40%)/negative(<25%) | one-quarter x short, standard | Bien lai gop — on-track? | vs threshold |
| 6 | C | "Xu huong doanh thu va gia von — margin co duy tri?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 7 | D | Revenue vs COGS Trend | trend | combo-chart | primary (revenue bar) + negative (COGS line) | two-thirds x medium, standard | Revenue va COGS theo thang | MoM implicit |
| 8 | D | Revenue Waterfall | breakdown | waterfall | positive + negative | one-third x medium, standard | Gross -> Discount -> Tax -> Net | additive |

### Composition — View 2: Channel Profitability

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 9 | A | "Loi nhuan theo kenh ban hang — kenh nao hieu qua nhat?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 10 | B | Margin by Channel | hero | horizontal-bar | conditional-above(>40%)/conditional-below(<25%) | half x medium, standard | Ranking kenh theo margin % | rank + threshold |
| 11 | B | Revenue vs COGS by Channel | breakdown | grouped-bar | series-1 + series-2 | half x medium, standard | Scale doanh thu vs gia von | cross-channel |
| 12 | C | "Xu huong margin kenh — kenh nao dang cai thien?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 13 | D | COGS Ratio Trend | trend | multi-line-chart | series-1..series-4 | full-width x medium, standard | Ty le gia von theo kenh qua cac thang | MoM per channel |

### Composition — View 3: Shopee Economics

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 14 | A | "Chi phi ban hang tren Shopee — phi san chiem bao nhieu?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 15 | B | Shopee Settlement MTD | hero | single-value-with-trend | primary | one-third x short, prominent | Tien thuc nhan tu Shopee | vs previous period |
| 16 | B | Settlement Margin % | supporting | gauge | positive(>75%)/warning(60-75%)/negative(<60%) | one-quarter x short, standard | Ty le thuc nhan | vs threshold |
| 17 | B | Platform Fee Rate % | supporting | single-value-with-trend | negative/neutral | one-quarter x short, standard | Tong phi san / doanh thu | vs previous period |
| 18 | B | Gross Revenue | supporting | single-value-with-trend | secondary | one-quarter x short, standard | Doanh thu Shopee | vs previous period |
| 19 | C | "Cau truc phi — loai phi nao chiem nhieu nhat?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 20 | D | Fee Breakdown | breakdown | horizontal-bar | series-1..series-7 | half x medium, standard | Ranking phi theo gia tri | rank |
| 21 | D | Revenue to Settlement Flow | breakdown | waterfall | positive + negative | half x medium, standard | Gross -> -Fees -> -Tax -> Net Settlement | additive |

### Action Map

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| Net Revenue MTD | MoM decline | < -15% | Check channel + product breakdown |
| Gross Margin % | Red zone | < 25% | Review COGS increase or pricing drop. Check suppliers. |
| Margin by Channel | Gap > 15pts | Highest vs lowest channel | Shift traffic to higher-margin channel |
| Settlement Margin % | Below 60% | < 60% | Review Shopee fee structure, contact Shopee |
| Platform Fee Rate % | Spike | > 20% or MoM +3pts | Verify tier, check new programs |

<!--
Dashboard Finish Checklist:
- [x] Hero cards in each view at top position
- [x] Every KPI has comparison
- [x] Row widths = 18 (B=6+4+4+4, D=12+6 or 9+9, etc.)
- [x] Total cards: V1=8, V2=5, V3=8 = 21 (within 3-view limit)
- [x] Semantic tokens only
- [x] Action Map complete
-->
