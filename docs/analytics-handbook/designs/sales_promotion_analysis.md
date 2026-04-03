---
title: "Sales Promotion & Discount Analysis"
archetype: Exploratory Tool
status: final
last_modified: 2026-04-02
domain_refs: [domains/sales.md]
---

## Design Spec: Sales Promotion & Discount Analysis

### Brief

- **Audience:** Marketing Manager, Sales Ops, Finance — ad-hoc analysis sessions to evaluate campaign ROI and discount spending
- **Time budget:** 15-30 min deep-dive session, revisit after each campaign ends
- **Primary question:** "Chuong trinh khuyen mai co hieu qua khong? Chi phi chiet khau co hop ly?"
- **Decision enabled:** Continue/adjust/stop promotions; flag discount abuse; optimize discount strategy by channel
- **Comparison frame:** MoM (this month vs last month) + Promo vs Non-Promo segmentation
- **Archetype:** Exploratory Tool
- **Domain references:** [domains/sales.md](../domains/sales.md) — Sections 13 (Discount Impact), 14 (Promotion Performance)

### Constraints & Filters

**Business Constraints** — luon ap dung, hardcode trong SQL, user khong tuong tac:

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude cancelled orders | `status != 'cancelled'` | All cards | Cancelled orders skew discount metrics |

**Interactive Filters** — user co the thay doi tren dashboard:

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Date Range | date/range | Last 30 days | All cards | Analyze different campaign periods |
| Channel | category/multi-select | All | All cards | Isolate channel-specific promo impact |
| Promotion Code | category/multi-select | All | View 2 cards | Focus on specific campaign |

### Views

Multi-view — 3 views:
1. Tong quan chiet khau (Discount Overview)
2. Hieu suat khuyen mai (Promotion Performance)
3. Phan tich kenh & chi tiet (Channel Impact & Detail)

---

### View 1 — Tong quan chiet khau

**Narrative flow:** "Chi phi chiet khau tong the?" -> "Ty le va cuong do chiet khau?" -> "Promo vs Non-Promo ket qua?" -> "Xu huong chiet khau theo thoi gian?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Kiem soat chi phi chiet khau — co vuot nguong va dang tang hay giam?" | annotation | text-annotation | structural | full-width x minimal | Section heading + purpose | — |
| 2 | B | Total Discount Amount | hero | single-value-with-trend | primary, positive/negative (MoM) | one-third x short, prominent | Tong tien chiet khau ky nay | vs previous period (MoM %) |
| 3 | B | Discount Rate % | supporting | single-value-with-trend | warning (khi > 15%), neutral | one-quarter x short, standard | Ty le CK/GMV | vs previous period (MoM %) |
| 4 | B | Discount Frequency % | supporting | single-value-with-trend | neutral, positive/negative (MoM) | one-quarter x short, standard | % don co chiet khau | vs previous period (MoM %) |
| 5 | B | Discounted Orders | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-quarter x short, standard | So don co CK | vs previous period (MoM %) |
| 6 | C | "So sanh Promo vs Non-Promo — khuyen mai co uplift AOV?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 7 | D | Promo vs Non-Promo Summary | breakdown | grouped-bar | series-1 (Promo) + series-2 (Non-Promo) | two-thirds x medium | So sanh Revenue, Orders, AOV giua 2 nhom | categorical (Promo vs Non-Promo) |
| 8 | D | AOV Uplift | supporting | single-value-with-trend | positive/negative | one-third x medium, prominent | AOV(Promo) vs AOV(Non-Promo) delta | vs benchmark (Non-Promo AOV) |
| 9 | E | "Phan tich do sau chiet khau — phat hien don bat thuong > 30%" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 10 | F | Discount Depth Histogram | breakdown | vertical-bar | primary, accent (buckets > 30%) | two-thirds x medium | Phan bo don theo % CK (0-10%, 10-20%, ...) | composition |
| 11 | F | Avg Discount % by Channel | breakdown | horizontal-bar | series-1..series-N | one-third x medium | Ranking kenh theo ty le CK trung binh | rank/position |
| 12 | G | "Theo doi xu huong chiet khau — trend amount va rate" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 13 | H | Discount Amount & Rate Trend | trend | combo-chart | primary (Discount Amount bar) + accent (Discount Rate % line) | full-width x medium | Xu huong tien CK va ty le CK theo thang | vs previous period (MoM overlay) |

---

### View 2 — Hieu suat khuyen mai

**Narrative flow:** "Khuyen mai nao hieu qua nhat?" -> "Chi tiet tung chuong trinh?" -> "Xu huong su dung promo theo thoi gian?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 14 | A | "Xac dinh promotion hieu qua — ranking doanh thu va usage" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 15 | B | Total Promo Revenue | hero | single-value-with-trend | primary, positive/negative (MoM) | one-third x short, prominent | Tong doanh thu tu don co promo | vs previous period (MoM %) |
| 16 | B | Promo Usage Count | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-quarter x short, standard | Tong so don dung promo | vs previous period (MoM %) |
| 17 | B | Unique Promos Active | supporting | single-value | neutral | one-quarter x short, standard | So chuong trinh dang active | — |
| 18 | B | Avg Revenue per Promo | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-quarter x short, standard | Doanh thu TB moi chuong trinh | vs previous period (MoM %) |
| 19 | C | "Review top 10 promotion — doanh thu va luot su dung" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 20 | D | Top 10 Promotions by Revenue | breakdown | horizontal-bar | primary | half x medium | Ranking CT khuyen mai theo doanh thu | rank/position |
| 21 | D | Top 10 Promotions by Usage | breakdown | horizontal-bar | secondary | half x medium | Ranking CT khuyen mai theo luot su dung | rank/position |
| 22 | E | "Tra cuu chi tiet promotion — code, usage, revenue, discount rate" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 23 | F | Promotion Performance Table | detail | data-table-formatted | conditional-above/conditional-below on Discount Rate % | full-width x tall | Code, Usage, Revenue, Discount, Discount Rate %, AOV, Type | rank/position |
| 24 | G | "Theo doi xu huong su dung promotion — top 5 codes" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 25 | H | Promo Usage Trend | trend | stacked-bar-time | series-1..series-5 (top 5 promos) | full-width x medium | Phan bo luot dung promo theo thang, chia theo top 5 codes | vs previous period (MoM) |

---

### View 3 — Phan tich kenh & chi tiet

**Narrative flow:** "Kenh nao chi nhieu nhat cho khuyen mai?" -> "Khuyen mai anh huong doanh thu kenh nhu the nao?" -> "Chi tiet don hang de dieu tra"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 26 | A | "Phan tich tac dong promo theo kenh — kenh nao phu thuoc nhieu?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 27 | B | Promo Revenue Share by Channel | breakdown | stacked-bar | series-1 (Promo Revenue) + series-2 (Non-Promo Revenue) | half x medium | Ty le doanh thu promo vs non-promo theo kenh | composition |
| 28 | B | Discount Rate by Channel | breakdown | horizontal-bar | primary, accent (channels > 15% discount rate) | half x medium | Ranking kenh theo ty le CK | rank/position |
| 29 | C | "So sanh hieu suat kenh MoM — highlight bien dong lon" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 30 | D | Channel Promo Performance Table | detail | data-table-formatted | conditional-above/conditional-below on MoM Change % | full-width x medium | Channel, Promo Orders, Promo Revenue, Discount Amount, Discount Rate %, MoM Change % | vs previous period (MoM) |
| 31 | E | "Dieu tra don chiet khau cao — flag don > 30% CK de audit" | annotation | text-annotation | structural | full-width x minimal | Section heading + alert threshold | — |
| 32 | F | High-Discount Orders List | detail | data-table-formatted | conditional-above on Discount % (> 30% = accent) | full-width x tall | Order Code, Date, Channel, Promo Code, Gross Revenue, Discount, Discount %, Net Revenue | — |
| 33 | G | "Source: fact_orders · dim_promotions · dim_channels · Updated daily · Excludes cancelled orders" | annotation | text-annotation | structural | full-width x minimal | Data source & freshness | — |

---

### Action Map

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| Total Discount Amount | Spike | MoM > +20% | Kiem tra co chuong trinh moi khong, review Discount Depth Histogram cho don bat thuong |
| Discount Rate % | High | > 15% of GMV | Review kenh co Discount Rate cao nhat (View 3), kiem tra Discount Abuse (Scenario B in playbook) |
| Discount Depth Histogram | Outlier bucket | Bucket > 30% co nhieu don | Drill vao High-Discount Orders List (View 3), xac nhan co dung promo hay CK tuy y |
| AOV Uplift | Negative | Promo AOV < Non-Promo AOV | Promo dang hut khach gia thap, can dieu chinh target audience hoac min order value |
| Top 10 Promotions by Revenue | Concentration | Top 1 chiem > 50% | Rui ro phu thuoc — da dang hoa portfolio khuyen mai |
| Promotion Performance Table | Low efficiency | Discount Rate > 20% ma Usage < 50 | Chuong trinh chi phi cao nhung it su dung — can stop hoac dieu chinh |
| Channel Promo Performance Table | Drop | MoM Revenue Change < -15% | Kiem tra kenh cu the, co thay doi chinh sach CK hay mat khach |
| High-Discount Orders List | Abuse pattern | Nhieu don > 30% CK tu cung chi nhanh/staff | Bao cao Sales Ops, audit chi nhanh/nhan vien lien quan |

---

### Data Source Notes

- **Primary table:** `fact_orders` — contains `discount_amount`, `discount_codes`, `gross_revenue`, `net_revenue`, `promotion_key`
- **Dimension:** `dim_promotions` — provides `promotion_code`, `promotion_type`, `discount_amount` per promo
- **Dimension:** `dim_channels` — channel name and category for channel-level analysis
- **Dimension:** `dim_date` — date hierarchy for MoM comparison
- **Promo vs Non-Promo segmentation:** `CASE WHEN discount_amount > 0 THEN 'Promo' ELSE 'Non-Promo' END`
- **Discount depth buckets:** `FLOOR((discount_amount / NULLIF(gross_revenue, 0)) * 10) * 10`
- **Number format:** VND compact (1.2M), percentages 1 decimal (12.3%)
- **Date format:** DD/MM/YYYY

### Dashboard Finish Checklist

- [x] Moi card co title theo Title Discipline
- [x] Moi KPI co it nhat 1 comparison (MoM, Promo vs Non-Promo, hoac rank)
- [x] Text annotations dung imperative voice
- [x] Action Map day du (8 action items)
- [x] Hero card noi bat (one-third, prominent)
- [x] Row widths sum = full-width (18 cols)
- [x] Density Exploratory Tool: V1=13, V2=12, V3=7
- [x] Moi view co section divider
- [x] Color tokens nhat quan
- [x] Grouped-bar cho Promo vs Non-Promo comparison
- [x] Number formatting: VND compact, percentage 1 decimal
