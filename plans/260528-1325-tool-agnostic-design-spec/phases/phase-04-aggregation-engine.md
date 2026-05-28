---
title: "Phase 4 — Aggregation Engine"
status: not_started
priority: P2
depends_on: [phase-02, phase-03]
created: 2026-05-28
updated: 2026-05-28
duration_estimate: "3-5 days"
---

## Goal

Semantic-layer stage 1: domain files gain executable `metric_def` blocks; a lightweight
aggregation engine resolves `metric_ref` bindings in Design Spec → SQL. At least 1 dashboard
deploys end-to-end using `metric_ref` (no inline SQL) and produces identical query results.

## Scope

**IN** (per `../reference/architecture.md` §7 Semantic Layer Migration Path):
- **Stage 1 — Foundation**: add executable `metric_def` YAML blocks to domain files (start with
  `domains/sales.md`; expand to other 6 domains as engine matures)
- **Stage 2 — Simple aggregation engine**: handles SUM/COUNT/AVG + dimensions + time grain +
  basic filters; generates DuckDB-compatible SQL
- **Stage 3 — Comparison engine**: previous-period, YoY, vs-target delta generation
- **Stretch / Stage 4 — Complex metrics**: composite metrics (Health Score weighted sum) —
  defer to dbt MetricFlow if engine complexity explodes (see open question C.6 / F.1)
- Update `domain_template.md` with `metric_def` block pattern
- Decide C.6 (cross-skill boundary): where does aggregation engine code live?

**OUT**:
- Looker / Lightdash deployers that consume `metric_ref` natively (Phase 6, on-demand)
- Full migration of all 25-26 dashboards to `metric_ref` (gradual, post-engine validation)
- dbt MetricFlow integration (only if custom engine proves insufficient)

## Steps

1. **Spike: dbt MetricFlow viability** (1–2 hours, gates engine build decision):
   - Check DuckDB adapter support for dbt MetricFlow (as of 2026)
   - Check self-host complexity vs custom engine build cost
   - If MetricFlow + DuckDB is production-ready with <1 day setup: adopt it
   - If blocked or requires dbt Cloud: build custom engine
   - Document decision as D9 in `../decisions.md`

2. **Decide aggregation engine location** (resolves B.3 / C.6):
   - Option A: `.skills/analytics-design/lib/aggregation-engine.js` (analyst brain — pure SQL gen)
   - Option B: `.skills/metabase-automation/lib/aggregation-engine.js` (alongside deployer)
   - Option C: new `.skills/semantic-resolver/` folder
   - Recommended: Option A — SQL generation is tool-agnostic; all deployers benefit.
   - Document decision in `../decisions.md` (D9 or addendum).

3. **Add `metric_def` blocks to `domains/sales.md`** (Stage 1):
   ```yaml
   metric_def:
     name: net_revenue
     base_model: fact_orders
     measure: SUM(net_revenue)
     default_filters:
       - is_sales_channel = true
     time_dimension: order_timestamp
     time_zone: Asia/Ho_Chi_Minh   # per memory: feedback_kpi_ict_window.md
   ```
   Start with: `net_revenue`, `order_count`, `aov` (most used across dashboards).
   Update `domain_template.md` with this block pattern.

4. **Build aggregation engine** (Stage 2 — simple cases):
   - Input: `metric_def` + `data` binding from widget-config
     (`metric`, `dimensions`, `filters`, `time_grain`)
   - Output: DuckDB SQL string
   - Handle: SUM/COUNT/AVG aggregations, GROUP BY dimensions, WHERE filters, DATE_TRUNC time grain
   - Time zone: always use ICT window for `date_key` filters (memory: `feedback_kpi_ict_window.md`)
   - Unit tests: for each `metric_def` in `sales.md`, assert generated SQL produces same result
     as existing inline SQL in `sales_daily_operation.md` widgets

5. **Build comparison engine** (Stage 3):
   - `comparisons: [{ type: previous-period, label: "vs hôm qua" }]`
   - Generate previous-period subquery (LAG window or CTE with date offset)
   - `comparisons: [{ type: yoy, label: "vs năm ngoái" }]` → 364-day offset
   - `comparisons: [{ type: vs-target, target_metric: ... }]` → join to target table

6. **Update `design-spec-parser.js`** (Phase 2 artifact):
   - When `data.metric` present: call aggregation engine → resolve to SQL
   - When `data.sql` present: pass through as before (inline SQL stepping stone still works)
   - Parser now handles both modes transparently (deployer unchanged)

7. **Migrate 1 dashboard end-to-end** (validation):
   - Choose a simple dashboard (few widgets, SUM/COUNT only, no composite metrics)
   - Update spec: replace inline SQL widgets with `metric_ref` bindings
   - Deploy to staging via `deploy_from_design_spec.js`
   - Assert: Metabase query results identical to existing inline-SQL version (row-level diff)
   - Document migration pattern for moving inline-SQL widgets to `metric_ref`

8. **Document `which-dashboards-use <metric>` lookup** (addresses D.4 risk):
   - Simple grep: `grep -r "metric: net_revenue" docs/analytics-handbook/designs/`
   - Or: build small CLI `node list-metric-usages.js <metric_name>` (only if manual grep insufficient)

## Files Touched

- 🔧 `D:\Vantt\app\data-integration\docs\analytics-handbook\domains\sales.md` — add `metric_def` blocks
- 🔧 `D:\Vantt\app\data-integration\docs\analytics-handbook\domains\*.md` — remaining 6 domains (as engine matures)
- 🔧 `D:\Vantt\app\data-integration\.skills\analytics-design\templates\domain_template.md` — add `metric_def` block pattern
- 🔧 `D:\Vantt\app\data-integration\.skills\metabase-automation\lib\design-spec-parser.js` — wire aggregation engine
- ✨ Aggregation engine code (location TBD — pending Step 2 decision; likely `.skills/analytics-design/lib/aggregation-engine.js`)
- 🔧 `../decisions.md` — D9 (custom engine vs MetricFlow + engine location)

## Success Criteria

- [ ] D9 documented: custom engine vs dbt MetricFlow decision with rationale
- [ ] Engine location decided and documented (resolves B.3)
- [ ] `domains/sales.md` has executable `metric_def` blocks for ≥ 3 metrics (net_revenue, order_count, aov)
- [ ] Aggregation engine generates valid DuckDB SQL for: SUM/COUNT/AVG, GROUP BY dimension, DATE_TRUNC time grain, previous-period comparison
- [ ] Generated SQL produces identical results vs existing inline SQL (unit tests + staging query diff)
- [ ] At least 1 dashboard deployed end-to-end using `metric_ref` (not inline SQL)
- [ ] Migration path documented: how to convert inline-SQL widget → `metric_ref`

## Risks

- **dbt MetricFlow + DuckDB compat unproven**: self-hosted MetricFlow may require dbt Cloud or
  have limited DuckDB adapter support.
  Mitigation: spike in Step 1 (time-boxed 2h); if blocked, build custom engine — it only needs
  to handle SUM/COUNT/AVG + filters + time grain for Phase 4 scope.
- **Composite metrics (Health Score) too complex for custom engine**: Health Score is a weighted
  sum of sub-scores, each with their own SQL.
  Mitigation: keep these as inline SQL; only migrate aggregable simple metrics to `metric_ref`.
  Engine does not need to handle composite metrics in Phase 4.
- **Scope creep — temptation to migrate all 25 dashboards to metric_ref**: engine validation
  should stop after 1 dashboard end-to-end.
  Mitigation: Phase 4 success criteria explicitly requires only 1 dashboard; bulk migration
  is post-Phase-4 gradual work, not a blocker.

## Cross-references

- **Decisions**: [D2 semantic-layer endgame / hybrid spec](../decisions.md#d2-endgame--semantic-layer-hybrid-spec) · D9 (to be created in this phase)
- **Critical problems**: [B.3 cross-skill boundary](../critical-problems.md) · [F.1 aggregation engine build vs dbt MetricFlow](../critical-problems.md)
- **Reference**: [`../reference/architecture.md`](../reference/architecture.md) §7 Semantic Layer Migration Path (Stage 0–4 detail)
- **Research**: [`../../reports/researcher-260527-2348-dashboard-definition-formats.md`](../../reports/researcher-260527-2348-dashboard-definition-formats.md) §Looker LookML / Lightdash dbt-native / dbt MetricFlow trade-offs
