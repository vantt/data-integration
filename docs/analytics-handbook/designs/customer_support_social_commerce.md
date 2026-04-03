---
title: "Social Commerce Operations"
archetype: Operational Cockpit
status: final
last_modified: 2026-04-02
domain_refs: [domains/customer_support.md, domains/sales.md]
---

## Design Spec: Social Commerce Operations

### Brief

- **Audience:** CS Team Leader — theo doi hieu suat social commerce hang ngay, revisit nhieu lan trong ngay
- **Time budget:** 5-10 min working session, revisit 2-3 lan/ngay
- **Primary question:** "Hom nay doi social ban duoc bao nhieu so voi hom qua?"
- **Decision enabled:** Dieu phoi nhan vien — ai can ho tro them, kenh nao can day manh, co can dang bai khong
- **Comparison frame:** DoD (today vs yesterday) — real-time so sanh
- **Archetype:** Operational Cockpit
- **Domain references:** [domains/customer_support.md](../domains/customer_support.md), [domains/sales.md](../domains/sales.md)

### Constraints & Filters

**Business Constraints** — luon ap dung, hardcode trong SQL, user khong tuong tac:

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Social channels only | `platform_group = 'Social'` (via dim_channels) | All cards | Dashboard chi theo doi kenh Social (Facebook, Zalo, Instagram) |

**Interactive Filters** — Khong co. Operational Cockpit can zero-interaction.

### Views

Single view — 10 data cards + 5 annotations = 15 cards total. Vua du cho Cockpit density limit (max 16).

---

### Composition

**Narrative flow:** "Doanh thu social hom nay?" → "Facebook vs Zalo dong gop the nao?" → "Nhan vien nao ban tot nhat?" → "Chi tiet don hang social"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Monitor doanh thu Social real-time — doi social dang ban duoc bao nhieu?" | annotation | text-annotation | structural | full-width x minimal | Dashboard subtitle + primary question | — |
| 2 | B | Social Revenue Today | hero | single-value-with-trend | primary, positive/negative (DoD) | one-third x short, prominent | Tong GMV tu Social hom nay | vs previous period (DoD %) |
| 3 | B | Social Orders Today | supporting | single-value-with-trend | secondary, positive/negative (DoD) | one-quarter x short, standard | So don tu Social | vs previous period (DoD %) |
| 4 | B | Social AOV | supporting | single-value-with-trend | secondary, positive/negative (DoD) | one-quarter x short, standard | Gia tri trung binh don Social | vs previous period (DoD %) |
| 5 | B | Social Share of Total | supporting | single-value | neutral | one-quarter x short, standard | % doanh thu Social / tong doanh thu | — |
| 6 | C | "Xac dinh kenh drive doanh thu — Facebook vs Zalo vs Instagram dong gop" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 7 | D | Revenue by Channel | breakdown | donut | series-1, series-2, series-3 | one-third x medium | Ty le dong gop FB vs Zalo vs Instagram | composition |
| 8 | D | Revenue by Channel (7-day trend) | trend | multi-line-chart | series-1 (Facebook) + series-2 (Zalo) + series-3 (Instagram) | two-thirds x medium | Xu huong doanh thu theo kenh 7 ngay | vs previous period (implicit overlay) |
| 9 | E | "Danh gia hieu suat nhan vien — ranking va xu ly kip thoi" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 10 | F | Top Agents by Revenue | breakdown | horizontal-bar | primary | half x medium | Ranking nhan vien theo doanh thu Social | rank/position |
| 11 | F | Top Agents by Orders | breakdown | horizontal-bar | secondary | half x medium | Ranking nhan vien theo so don Social | rank/position |
| 12 | G | "Review chi tiet nhan vien — xac dinh ai can ho tro them" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 13 | H | Agent Performance Table | detail | data-table-formatted | conditional-above/conditional-below on DoD Revenue Change % | full-width x medium, compact | Chi tiet: Agent, Revenue, Orders, AOV, DoD % | vs previous period (DoD) |
| 14 | I | "Kiem tra don hang moi nhat — xac nhan pipeline real-time" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 15 | J | Recent Social Orders | detail | data-table | neutral | full-width x medium, compact | 20 don moi nhat: time, order code, channel, agent, amount, status | — |
| 16 | K | "Source: fact_orders · dim_channels (Social only) · Updated real-time · Filter: platform_group = Social" | annotation | text-annotation | structural | full-width x minimal | Data source & freshness | — |

### Action Map

> Moi card co signal quan trong PHAI co recommended action. Tham chieu Action Triggers trong playbook.

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| Social Revenue Today | Low revenue | DoD < -20% | Kiem tra tin nhan chua doc tren Facebook Page/Zalo OA. Xac nhan bai Flash Sale da dang chua. |
| Social Revenue Today | Revenue spike | DoD > +30% | Xac nhan khong co don trung. Ghi nhan kenh/nhan vien nao drive. |
| Social Orders Today | Low order count | DoD < -15% | Kiem tra tinh trang nhan tin tu khach — co giam traffic khong? |
| Revenue by Channel | Channel imbalance | 1 kenh < 20% tong | Day manh kenh yeu — dang bai, tra loi tin nhan nhanh hon. |
| Top Agents by Revenue | Agent underperform | Agent co 0 don sau 2h | Kiem tra agent co dang online/reply tin nhan. Phan bo lai tin nhan. |
| Agent Performance Table | DoD drop > 30% | Revenue Change % < -30% | Trao doi truc tiep voi agent, kiem tra chat log. |

### Dashboard Finish Checklist

- [x] Moi card co title theo Title Discipline
- [x] Moi KPI co it nhat 1 comparison (DoD)
- [x] Text annotations dung imperative voice
- [x] Action Map day du
- [x] Hero card noi bat (one-third, prominent)
- [x] Row widths sum = full-width (18 cols)
- [x] Single view — 15 cards within Cockpit limit of 16
- [x] Color tokens nhat quan
- [x] Donut <= 5 slices (3 channels)

<!--
Composition Table Notes:
- Row B: one-third + 3 x one-quarter = 6 + 4 + 4 + 4 = 18 ✓
- Row D: one-third + two-thirds = 6 + 12 = 18 ✓
- Row F: half + half = 9 + 9 = 18 ✓
- Row H, J: full-width = 18 ✓
- All annotation rows: full-width = 18 ✓
- Hero (Social Revenue Today) is visually dominant: one-third + prominent text
- Supporting cards are one-quarter + standard text (smaller than hero) ✓
- Donut has 3 slices (FB, Zalo, Instagram) — within <=5 limit ✓
- Total: 10 data cards + 5 annotations = 15 cards — within Cockpit limit of 16 ✓
- Single view — no tabs needed (Cockpit allows up to 4 but single view sufficient here)
-->
