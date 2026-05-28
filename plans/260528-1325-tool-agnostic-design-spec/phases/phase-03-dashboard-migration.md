---
title: "Phase 3 — Dashboard Migration"
status: not_started
priority: P1
depends_on: [phase-01, phase-02]
created: 2026-05-28
updated: 2026-05-28
duration_estimate: "3-5 days"
---

## Goal

Migrate all 25-26 production dashboards from v1 Design Spec + blueprint to v2 Design Spec
deployable via `deploy_from_design_spec.js`. After this phase, every dashboard has a v2 spec
at `docs/analytics-handbook/designs/` and has been validated on staging Metabase.

## Scope

**IN**:
- Run enhanced Phase 1 capture on each production dashboard → emit v2 spec (`draft-from-capture`)
- Human review each spec: fix capture artifacts, promote `status: final`
- Deploy each v2 spec to staging Metabase via Phase 2 deployer → visual diff
- Promote verified specs to production (gradual, low-risk-first)
- Update `designs/README.md` to reflect v2 migration status

**OUT**:
- Sunsetting blueprints (Phase 5) — blueprints kept as rollback throughout this phase
- Aggregation engine / metric_ref migration (Phase 4)
- Migrating `blueprints/rill/` sub-folder (investigate separately in Phase 5)

## Steps

1. List all 25-26 dashboards from `docs/analytics-handbook/designs/` and their corresponding
   blueprints in `docs/analytics-handbook/blueprints/`. Build migration tracking table
   (dashboard name | capture status | review status | staging deploy | production deploy).

2. **Batch capture** (automated): run
   `node generate-design-spec-from-dashboard.js <dashboard_name>` for each dashboard.
   Save output to `docs/analytics-handbook/designs/<name>.md` with `status: draft-from-capture`.
   Each capture = separate git commit for easy revert.

3. **Triage captures**: check each output with `validate-analytics-artifacts.js`.
   Flag dashboards with validation errors or `unknown` viz types for manual review.

4. **Human review** (per dashboard):
   - Verify composition table matches blueprint card list
   - Fix any `unknown` viz types by consulting `METABASE_VIZ_CATALOG.md`
   - Fix Widget Details with malformed SQL (copy from blueprint if needed)
   - Verify domain links in Widget Details (`**Domain**: [...]`)
   - Promote `status: draft-from-capture` → `status: final` when satisfied

5. **Staging deploy** (per dashboard, after review):
   - `node deploy_from_design_spec.js docs/analytics-handbook/designs/<name>.md --target staging`
   - Manual visual diff: open staging vs production side-by-side
   - Record diff result in migration tracking table (pass / minor / major)
   - Fix spec and re-deploy if diff is major

6. **Migration order** (low-risk first):
   - Start: single-tab, few widgets, no complex conditional formatting
   - Middle: multi-tab, standard viz types
   - End: `sales_daily_operation` and other dashboards with gauges, Health Score composites
   - CEO dashboards last (high visibility, conservative)

7. **Production promotion** (per dashboard, after staging pass):
   - `node deploy_from_design_spec.js <name>.md --target production`
   - Monitor for user-reported issues 24h post-deploy
   - Blueprint kept at `docs/analytics-handbook/blueprints/<name>.md` — do NOT archive yet

8. Update `docs/analytics-handbook/designs/README.md`: add v2 migration status column.

## Files Touched

- 🔧 `D:\Vantt\app\data-integration\docs\analytics-handbook\designs\*.md` — all 25-26 specs migrated to v2
- 🔧 `D:\Vantt\app\data-integration\docs\analytics-handbook\designs\README.md` — migration status column
- 🚫 `D:\Vantt\app\data-integration\docs\analytics-handbook\blueprints\*.md` — kept untouched as rollback

## Success Criteria

- [ ] All 25-26 dashboards have `spec_version: 2` spec in `designs/`
- [ ] All specs pass `validate-analytics-artifacts.js` with 0 errors
- [ ] All deployable via `deploy_from_design_spec.js` without manual fixes
- [ ] Staging visual diff each dashboard: ≥ 95% match vs production
- [ ] All production deployments completed with 0 behavioral regressions reported
- [ ] Each migration is an independent git commit (revert possible per dashboard)

## Risks

- **Production dashboard breaks on deploy**: wrong grid, missing filter wiring, viz mismatch.
  Mitigation: staging deploy + visual diff gates production promotion; blueprint kept as rollback;
  revert = re-run `deploy_from_markdown.js <blueprint>`.
- **Health Score / composite metrics not capturable cleanly**: weighted-sum formula may not
  survive capture → widget-config round-trip.
  Mitigation: manual edit post-capture; keep inline SQL verbatim; mark `status: final` only after
  human verification; these dashboards migrate last.
- **Capture returns stale SQL**: question SQL in staging Metabase may differ from production.
  Mitigation: capture from production Metabase instance; note in tracking table if staging-only
  capture was used.

## Cross-references

- **Decisions**: [D3 capture-first migration](../decisions.md#d3-capture-first-migration-strategy)
- **Critical problems**: [migration safety mitigation](../critical-problems.md)
- **Reference**: [`../reference/key-files.md`](../reference/key-files.md) §5.1 Designs list (25-26 targets) · [`../reference/key-files.md`](../reference/key-files.md) §5.2 Blueprints list (rollback sources)
- **Research**: [`../../reports/research-260527-2300-tool-agnostic-design-spec.md`](../../reports/research-260527-2300-tool-agnostic-design-spec.md) §6 Migration Strategy
