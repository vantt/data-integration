---
primary_scope:
scope_indicator: ""
layer: L0
uses_concepts: []
---

# 📘 Blueprint: Welcome to ChợPulse BI

> **Target Collection:** `📍 Start Here`
> **Role:** All users (onboarding)
> **Archetype:** Onboarding landing (1 text card, no tabs, no SQL)

## Segmentation Scope

N/A — onboarding landing page. Scope and segmentation concepts do not apply. Dashboard guides new users to the right collection based on their role and explains scope suffix naming conventions for all downstream dashboards.

System landing page that guides new users to the right collection based on their role + explains scope suffix convention (Rule 6).

## 📂 Collection: 📍 Start Here

---

### 🖥️ Dashboard: Welcome to ChợPulse BI

**Description**: Audience: All users. Scope: Onboarding. Câu hỏi: Tôi nên mở folder nào? Mỗi role → 1 collection. Mỗi dashboard có suffix [All]/[Retail]/[B2B]/[Cross]/[US]/[Internal] cho biết scope.

---

#### 📝 Text: ChợPulse BI Welcome

# ChợPulse BI — Where do I go?

| Role | Collection |
|:---|:---|
| 🏢 CEO / Founder / Board | **Executive** |
| 💰 CFO / Accounting / FP&A | **Finance** |
| 📣 Marketing / Customer Success | **Marketing & Customers** |
| 🏪 Store Manager | **Operations → Daily Monitoring** |
| 📊 Sales Ops Lead | **Operations → Periodic Reviews** |
| 🤝 B2B Account Manager | **Operations → B2B Operations** |
| 🚚 Logistics Manager | **Operations → Logistics** |
| 🛠️ Data Engineer | **Operations → Data Platform** |
| 🔬 Analyst / Researcher | **Analytics** |

## Naming convention

Every dashboard has a **scope suffix**:
- `[All]` — all sales channels (CEO view)
- `[Retail]` — retail customers only (Marketing/CS/Store)
- `[B2B]` — wholesale/partner only
- `[Cross]` — cross-segment comparison (Analytics)
- `[US]` — US CrossBorder fulfillment
- `[Internal]` — internal monitoring (Data team)

See `docs/analytics-handbook/guides/report_segmentation.md` for the full guide.

---

**Last updated:** 2026-05-29

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 18 }
```
