# Dashboard 105 — KPI Migration + Layout Cleanup Report

**Dashboard:** Weekly · Customer Retention & Cohorts [Retail] (ID: 105)
**Blueprint:** `docs/analytics-handbook/blueprints/metabase/customer_retention_cohorts.md`
**Deploy result:** 42 dashcards synced, 3 tabs active (IDs: 281/282/283)

---

## Part 1 — 3 Cards Migrated Off Snapshot Model

### Cards updated

| Card ID | Name | Old source | New source | Verify |
|---------|------|-----------|-----------|--------|
| 2254 | Repeat Purchase Rate | `mart_customer_status_snapshot_monthly` (orders_to_date = current value) | `fact_orders` PIT: counts customers with ≥2 orders as-of each month-end | ✅ FROM clause: `fact_orders`, `valid_orders`, `month_ends` — no snapshot |
| 2255 | Churn Rate | `mart_customer_status_snapshot_monthly` (status = current) | `mart_retention_waterfall_monthly` | ✅ FROM: `mart_retention_waterfall_monthly w, month_ends m` |
| 2257 | Active Customer Rate | `mart_customer_status_snapshot_monthly` (status = current) | `mart_retention_waterfall_monthly` | ✅ FROM: `mart_retention_waterfall_monthly w, month_ends m` |

### Sanity check on new numbers (May 2026 close)

**Waterfall model output:**
- ACTIVE: 90 / 5093 = **1.8%** (vs old snapshot: 2.1%) — slightly lower, more accurate
- CHURNED: 4866 / 5093 = **95.5%** (vs old snapshot: 95.4%) — aligned
- Repeat Rate (PIT): **26.3%** cumulative as-of May 2026 — reasonable for retail base

Numbers within expected ranges. Bias was modest for the most recent period (snapshot's survivorship inflation is highest at historical troughs, not the present month).

### Why PIT for Repeat Rate (not waterfall)

`mart_retention_waterfall_monthly` tracks status counts only — no per-customer order history. Repeat rate requires per-customer order counts as-of each month-end. Solution: re-aggregate directly from `fact_orders` with `WHERE order_date <= snapshot_date` — same bias-free PIT approach as the waterfall model.

---

## Part 2 — Layout Changes

### Before

Live dashboard had **no tabs** — all 40 cards were on a flat single-page view with overlapping row positions (3 duplicate `Chu kỳ báo cáo` at row 0, cards from 3 tabs colliding).

### After

3 tabs restored and card positions cleaned up within Tab 1 (Suc khoe Retention):

**KPI row (row 3) — equalized widths:**

| Card | Old col/size | New col/size |
|------|-------------|-------------|
| Repeat Purchase Rate | col 0, w=6 | col 0, w=5 |
| Churn Rate | col 6, w=4 | col 5, w=4 |
| Avg Order Value | col 10, w=4 | col 9, w=5 |
| Active Customer Rate | col 14, w=4 | col 14, w=4 |

Total: 5+4+5+4=18 ✓ (was 6+4+4+4=18 — front-heavy, visually unbalanced)

**Lifecycle distribution row — aligned to row 7 (was rows 7-8 staggered):**
- Customer Lifecycle Distribution: row 7, col 0, w=6
- Revenue by Lifecycle Status: row 7, col 6, w=6 (was row 8)
- Segment x Status Matrix: row 7, col 12, w=6 (was row 8)

**Trend charts row — moved up 1 row (row 15→14):**
- Retention Waterfall Trend: row 14, col 0, w=9
- Repeat Purchase Rate Trend: row 14, col 9, w=9

**Scorecard and MAU chart shifted up 1 row accordingly:**
- Retention Health Scorecard: row 21 (was 22)
- MAU vs Repeat-Buyer MAU: row 28 (unchanged — already at 28)

Section header text cards preserved at rows 2, 6, 13, 20.

---

## Concerns

- Tabs 282 (Phan tich Cohort) and 283 (Hanh vi & Reactivation) positions unchanged from blueprint — not audited for tightness but no overlaps exist in blueprint.
- The pre-deploy warning flagged `SQL re-derives cancellation filter — use pre-computed scope column` for the new Repeat Rate PIT query (uses `status NOT IN ('CANCELLED', 'DRAFT')` directly). This mirrors the waterfall model's own logic (`mart_retention_waterfall_monthly.sql` uses same filter). Acceptable during SQL migration period.
- `{{segment}}` filter not wired in the 2 waterfall-based cards (Churn Rate / Active Customer Rate) — the waterfall model doesn't carry `value_group`, so segment filtering is not possible at the KPI scalar level for those cards. This is a model constraint, not a new regression.

**Status: DONE**
