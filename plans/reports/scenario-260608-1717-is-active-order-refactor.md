# Scenario Report: is_active_order Refactor

**Target:** `scope_*` / `is_active_order` semantic split — dbt, blueprints, Rill metrics  
**Date:** 2026-06-08 | **Analyst:** ck:scenario

---

## Dimensions analyzed
2-Input Extremes, 3-Timing, 4-Scale, 5-State Transitions, 7-Error Cascades, 9-Data Integrity, 10-Integration, 12-Business Logic

## Dimensions skipped
1-User Types (N/A — data pipeline), 6-Environment (server-side DuckDB), 8-Authorization (N/A), 11-Compliance (no PII changes)

---

| # | Dimension | Scenario | Severity | Expected Behavior |
|---|-----------|----------|----------|-------------------|
| 1 | Input Extremes | `orders.status = NULL` → `is_active_order = NULL` (DuckDB tri-value logic: `NULL != 'CANCELLED'` = NULL) | **High** | NULL-status orders excluded from both revenue AND cancelled count, but included in total order count — "ghost" orders |
| 2 | Input Extremes | `orders.status = 'cancelled'` (lowercase, data quality anomaly) → `is_active_order = TRUE` → counted in revenue | Medium | These orders will be treated as active; add lowercase guard or dbt test |
| 3 | Input Extremes | `orders.status = 'VOIDED'` → `is_active_order = TRUE` | Low | Consistent with old behaviour (old `scope_sales` also didn't exclude VOIDED); document intentionally |
| 4 | Input Extremes | `orders.status = 'DRAFT'` → `is_active_order = TRUE` → included in revenue | Medium | Drafts were included in old scope_sales revenue too; acceptable if intentional — verify with business |
| 5 | Timing | Rill measures (`sales_revenue`, `retail_revenue`, `b2b_revenue`) use `filter (where scope_sales/retail/b2b)` with NO `is_active_order` gate — cancelled revenue now included | **Critical** | `rill/metrics/orders_core_metrics.yaml` lines 157/165/172 must add `AND is_active_order` to expressions |
| 6 | Timing | Rill `orders_executive.yaml` description line 11 still says "excludes internal/cancelled" → misleads future LLM/dev reading this | **High** | Update description; also `orders_core_metrics.yaml` lines 69-75 scope descriptions are stale |
| 7 | Timing | Stale Metabase query cache serves pre-refactor results until cache TTL expires | Low | Cards will self-correct on next cache expiry; no action needed |
| 8 | Scale | All orders for a day are cancelled → `WHERE scope_retail AND is_active_order` = 0 rows → revenue cards show 0/null | Medium | Cards show correctly; verify Metabase null-state display doesn't show misleading "no data" |
| 9 | Scale | 0 cancelled orders → `WHERE NOT is_active_order` count = 0 → Cancelled Orders card shows 0 | Low | Correct; verify card doesn't hide itself on zero value |
| 10 | Scale | Pre-refactor historical KPI comparison: Total Orders now includes cancelled → apparent "spike" in order count vs. historical baselines built before refactor | **High** | Annotate dashboards or add note in Semantic Contract; historical series is discontinuous at 2026-06-08 |
| 11 | State Transitions | Order status changes PENDING → CANCELLED AFTER `fact_orders` materialized → `is_active_order = TRUE` until next pipeline run → order counted in today's revenue incorrectly | Medium | Inherent to daily-batch ETL; same risk existed pre-refactor for scope_sales; acceptable with known SLA |
| 12 | State Transitions | `fact_orders` uses rolling window parquet (full rewrite, not incremental) → no stale `is_active_order = NULL` from old rows | — | **No risk** — full rewrite confirmed; incremental concern N/A |
| 13 | Error Cascades | `is_active_order = NULL` propagates through `WHERE scope_retail AND is_active_order` → row silently excluded from revenue with no error | **High** | Same as #1 — NULL status is the root cause; add dbt test `not_null` on `is_active_order` |
| 14 | Error Cascades | `fact_order_economics.is_active_order` inherited via JOIN — if join drops rows (LEFT JOIN returns NULL for `is_active_order`), finance cards silently undercount | Medium | Check `fact_order_economics` join path; if `is_active_order` can be NULL post-join, wrap: `COALESCE(e.is_active_order, true)` |
| 15 | Data Integrity | Rill `orders_core_metrics.yaml` — `avg_order_value = sum(net_revenue) / count(distinct order_id)` with no `is_active_order` gate; when dashboard filtered by `scope_sales`, denominator includes cancelled orders but numerator revenue of cancelled = 0 → AOV understated | **High** | Fix: `sum(net_revenue) filter (where is_active_order) / nullif(count(distinct order_id) filter (where is_active_order), 0)` |
| 16 | Data Integrity | Blueprints with mixed COUNT + SUM in same CTE where `is_active_order` was applied — order_count in performance tables now excludes cancelled (side effect) | **High** | Affected: `sales_ops_monthly_summary`, `sales_ops_weekly_review` Channel/Branch Performance Tables; already flagged in `issues:` frontmatter — needs SQL fix |
| 17 | Data Integrity | `sales_promotion_analysis` abuse-detection cards: cancelled-after-discount orders no longer detected | **High** | Already flagged in `issues:` frontmatter; needs explicit `scope_retail` (no `is_active_order`) in abuse CTEs |
| 18 | Data Integrity | `ceo_weekly_pulse` & `ceo_monthly_scorecard`: some cards use `channel_key IN (subquery)` instead of `scope_sales` + no `is_active_order` → not updated by refactor → inconsistent revenue definitions across cards on same dashboard | Medium | Already flagged as `[todo]` in issues frontmatter |
| 19 | Integration | Rill `orders_executive.yaml` default_preset `where: "scope_sales = true"` — now includes cancelled orders in the default explore view | **Critical** | Fix: add `AND is_active_order = true` to `where:` clause for revenue-focused explores, OR remove and let measures handle it |
| 20 | Integration | Rill `orders_retail_ops.yaml` / `orders_b2b_ops.yaml` — same `where:` pattern issue for their respective scopes | **Critical** | Same fix as #19 |
| 21 | Business Logic | Ratio cards (Discount Rate = SUM(discount_amount) / SUM(gross_revenue)): both numerator + denominator have `is_active_order` → consistent, cancelled orders properly excluded from both | — | **No risk** — ratio consistent |
| 22 | Business Logic | `Abuse Risk Scorecard` in `sales_promotion_analysis`: `is_active_order` applied to all 3 sub-CTEs (`suspicious_customers`, `suspicious_codes`, `suspicious_staff`) → customer who placed promo order then cancelled = not detected | **High** | Remove `AND is_active_order` from abuse CTEs; keep `scope_retail` only; detection should see ALL promo orders regardless of final status |
| 23 | Business Logic | `Payment Status Summary` in `sales_ops_monthly_summary`: payment breakdown now only covers active orders → recon denominator smaller than expected, "CANCELLED" payments (if any) invisible | **High** | Verify business intent: if card is for payment reconciliation, use `scope_retail` only; if for revenue analysis, keep `is_active_order` |
| 24 | Business Logic | New Customer / Returning Customer customer counts: no `is_active_order` applied (count_all decision) → customer who only has cancelled orders is counted as a customer | Medium | Acceptable if "customer had contact" is the definition; document intent. If "customer who completed a purchase" is intent, needs `is_active_order` |

---

## Summary

| Severity | Count |
|----------|-------|
| **Critical** | 3 (#5, #19, #20) |
| **High** | 9 (#6, #10, #13, #15, #16, #17, #22, #23) + #18 at edge |
| **Medium** | 6 (#2, #4, #8, #11, #14, #18, #24) |
| **Low** | 3 (#3, #7, #9) |
| No Risk | 2 (#12, #21) |
| **Total** | **22 scenarios across 7 dimensions** |

---

## Immediate Actions — Status (2026-06-09)

### ✅ Critical — DONE

**1–3. Rill metrics + explore YAMLs** — verified by agent scan 2026-06-09:
- `orders_core_metrics.yaml`: `sales_revenue`, `retail_revenue`, `b2b_revenue` all have `AND is_active_order` gate
- `avg_order_value` correctly excludes cancelled orders
- Rill explore YAMLs (`orders_executive.yaml`, `orders_retail_ops.yaml`, `orders_b2b_ops.yaml`): `where:` clauses fixed

### ⚠️ High — OUTSTANDING

**4. dbt test** — ✅ `not_null` test added to `transformation/models/marts/schema.yml` (2026-06-09)

**5. Blueprint SQL fix** — ✅ `sales_promotion_analysis.md` abuse-detection CTEs fixed (2026-06-09): removed `AND o.is_active_order` from `suspicious_customers`, `suspicious_codes`, `suspicious_staff`; frontmatter issues note updated to `[fixed]`

**6. Stale Rill descriptions** — not yet verified; lower priority than items 4–5

---

## Original Immediate Actions (for reference)

### 🔴 Critical — fix before Rill is used for revenue reporting

**1. `rill/metrics/orders_core_metrics.yaml`** — Add `is_active_order` gate to revenue measures:
```yaml
- name: sales_revenue
  expression: sum(net_revenue) filter (where scope_sales AND is_active_order)
- name: retail_revenue
  expression: sum(net_revenue) filter (where scope_retail AND is_active_order)
- name: b2b_revenue
  expression: sum(net_revenue) filter (where scope_b2b AND is_active_order)
```

**2. `rill/metrics/orders_core_metrics.yaml`** — Fix `avg_order_value`:
```yaml
- name: avg_order_value
  expression: sum(net_revenue) filter (where is_active_order) / nullif(count(distinct order_id) filter (where is_active_order), 0)
```

**3. Rill explore YAMLs** — `where:` clause in default_preset: ✅ fixed

### 🟠 High — fix before relying on affected cards

**4. dbt test** — Add `not_null` test on `fact_orders.is_active_order` in `schema.yml` — ❌ outstanding

**5. Blueprint SQL fixes:**
- `sales_ops_monthly_summary` + `sales_ops_weekly_review`: split Channel/Branch CTE — ✅ done
- `sales_promotion_analysis`: remove `AND is_active_order` from abuse CTEs — ❌ outstanding (lines ~1774, 1795, 1815)

**6. Stale Rill descriptions:** — not yet verified

---

## Unresolved Questions

1. **Payment Status Summary** (#23): should it cover all orders (scope_retail only) or active orders only (+ is_active_order)? Needs business decision.
2. **New/Returning Customers** (#24): does "customer" require at least one completed order, or just any contact?
3. **Rill explores `where:` clause** (#19, #20): remove the default scope filter from explore presets (let measures handle it) or keep for dimension slicing?
