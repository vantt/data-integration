---
title: "Phase 0 — Schema Spike"
status: not_started
priority: P0
depends_on: []
created: 2026-05-28
updated: 2026-05-28
duration_estimate: "1 day"
---

## Goal

Validate that the v2 Design Spec schema can represent real-world complexity by manually
transcribing 5 representative widgets from `sales_daily_operation`. Freeze the schema format
so Phase 1 (capture) and Phase 2 (parser/deployer) can build against a stable contract.

## Scope

**IN**:
- Manually transcribe 5 widgets from `sales_daily_operation` blueprint → enhanced v2 Design Spec:
  - Health Score gauge (composite formula, threshold segments)
  - Net Revenue scalar + trend (single-value-with-trend, DoD comparison)
  - Hourly Sales Trend multi-line (time-series, multiple series)
  - Health Breakdown table + conditional formatting (tabular, color zones)
  - One text annotation (tab_standards/period_header intent)
- Publish `widget-config.schema.json` (JSON Schema 2020-12)
- Publish `WIDGET_CONFIG_SCHEMA.md` (human reference)
- Enhance `VISUALIZATION_VOCABULARY.md`: add per-tool support level column per viz type
- Enhance `validate-analytics-artifacts.js`: v2 schema validation (JSON Schema check + widget-config presence)
- Enhance `design_spec_template.md`: add Widget Details section, new frontmatter fields
- Resolve open questions C.1, C.3, C.6, E.4, G.3 → document decisions in `../critical-problems.md`

**OUT**:
- Building parser or deployer code (Phase 2)
- Migrating other dashboards (Phase 3)
- Aggregation engine (Phase 4)
- Capturing from live Metabase (Phase 1)

## Steps

1. Read source files:
   - `D:\Vantt\app\data-integration\docs\analytics-handbook\blueprints\sales_daily_operation.md` (ground truth)
   - `D:\Vantt\app\data-integration\docs\analytics-handbook\designs\sales_daily_operation.md` (current v1 spec)
   - `../reference/spec-format-design.md` (v2 format specification)
   - `D:\Vantt\app\data-integration\.skills\analytics-design\VISUALIZATION_VOCABULARY.md`
   - D7 and D8 in `../decisions.md`

2. Decide C.3 (monolith vs companion): author the 5 widgets inline; if the file exceeds
   1200 lines and feels painful to navigate, choose companion pattern; document in `../critical-problems.md`.

3. Decide C.1 (DRY thresholds): choose one model for gauge segments:
   - Option A: frontmatter `defaults:` → widgets `inherit_from: defaults` (recommended starting point)
   - Option B: widget-config as single source; document in `../critical-problems.md`.

4. Decide C.6 (composition table vs widget details as source): document in `../critical-problems.md`.

5. Decide G.3 (test fixture location): pick `.skills/analytics-design/__tests__/fixtures/`;
   document in `../critical-problems.md`.

6. Draft v2 frontmatter for `sales_daily_operation.md` (add `spec_version: 2`, `sql_dialect`,
   `grid_base`, `defaults`, `tab_standards`). Mark `status: draft-from-spike`.

7. Add Widget Details section to `sales_daily_operation.md` with the 5 chosen widgets.
   Each widget: `#### W:{slug}`, domain link, `yaml widget-config` fence block.

8. Author `widget-config.schema.json`:
   - JSON Schema 2020-12
   - Required keys: `data`, `viz`, `layout`
   - `data` oneOf: `metric_ref` block OR `sql` block
   - `viz.type` enum from VISUALIZATION_VOCABULARY.md
   - `layout.width` / `layout.height` size token enums
   - Include descriptions for all fields (serves as inline documentation)

9. Author `WIDGET_CONFIG_SCHEMA.md` — human-readable reference mirroring the schema with
   examples for each viz type.

10. Enhance `VISUALIZATION_VOCABULARY.md`: add column "Per-Tool Support"
    (native / fallback / unsupported) for Metabase, Evidence, Superset, Looker, Grafana.
    Source: `../../reports/researcher-260527-visualization-type-mapping.md`.

11. Enhance `validate-analytics-artifacts.js`:
    - If `spec_version: 2` detected: run `widget-config.schema.json` validation on each
      widget-config block
    - Report: widget count, missing IDs, schema validation errors with file:line

12. Enhance `design_spec_template.md`:
    - Add new frontmatter fields (spec_version, sql_dialect, grid_base, defaults, tab_standards)
    - Add `### Widget Details` section template
    - Add `### Tab Standards` section template

13. Validate: run `node validate-analytics-artifacts.js` on the updated `sales_daily_operation.md`.
    All 5 widgets must pass JSON Schema validation.

14. Document E.4 (error reporting quality bar) decision in `../critical-problems.md`.

## Files Touched

- ✨ `D:\Vantt\app\data-integration\.skills\analytics-design\WIDGET_CONFIG_SCHEMA.md` — new human reference doc
- ✨ `D:\Vantt\app\data-integration\.skills\analytics-design\schemas\widget-config.schema.json` — JSON Schema 2020-12
- 🔧 `D:\Vantt\app\data-integration\.skills\analytics-design\VISUALIZATION_VOCABULARY.md` — add per-tool support column
- 🔧 `D:\Vantt\app\data-integration\.skills\analytics-design\templates\design_spec_template.md` — add Widget Details section + new frontmatter fields
- 🔧 `D:\Vantt\app\data-integration\.skills\metabase-automation\scripts\validate-analytics-artifacts.js` — v2 schema validation
- 🔧 `D:\Vantt\app\data-integration\docs\analytics-handbook\designs\sales_daily_operation.md` — 5 widgets transcribed, `status: draft-from-spike`
- 🔧 `../critical-problems.md` — document C.1, C.3, C.6, E.4, G.3 resolutions

## Success Criteria

- [ ] 5 widgets transcribed with `yaml widget-config` blocks (gauge, scalar-trend, multi-line, table-conditional, text annotation)
- [ ] All 5 pass `node validate-analytics-artifacts.js` JSON Schema validation with 0 errors
- [ ] `widget-config.schema.json` published to `.skills/analytics-design/schemas/`
- [ ] Schema gaps (if any) documented and schema updated before closing phase
- [ ] Format spec v2 frozen: `spec_version: 2` frontmatter fields stable, ready for Phase 1 to emit
- [ ] C.1 resolved: threshold DRY model chosen and documented
- [ ] C.3 resolved: monolith vs companion decision recorded
- [ ] C.6 resolved: composition table vs widget details source-of-truth chosen
- [ ] E.4 resolved: error reporting quality bar defined
- [ ] G.3 resolved: test fixture location decided
- [ ] VISUALIZATION_VOCABULARY.md has per-tool support column for all viz types

## Risks

- **Schema misses edge case**: Health Score gauge has composite formula (weighted sum of sub-scores).
  Mitigation: pick widgets that cover ALL distinct viz config shapes — gauge, scalar-trend, multi-line,
  table+conditional-format, text. If composite formula doesn't fit, extend schema before closing Phase 0.
- **C.1 threshold decision blocks progress**: multiple options viable (inherit, widget-config-only, etc.).
  Mitigation: default to simplest model (frontmatter `defaults:` + `inherit_from`) on day 1;
  spike reveals if authoring pain is real; never block on perfect solution.
- **Updated `sales_daily_operation.md` diverges from v1 content**: existing v1 composition table
  must remain readable (backward compat read path).
  Mitigation: append Widget Details section — don't reformat existing sections; parser handles both.

## Cross-references

- **Decisions**: [D2 hybrid spec](../decisions.md#d2-endgame--semantic-layer-hybrid-spec) · [D4 versioning](../decisions.md#d4-spec-versioning-spec_version-field) · [D7 JSON Schema](../decisions.md#d7-json-schema-from-day-1) · [D8 schema location](../decisions.md#d8-spec-schema-location-analytics-design)
- **Critical problems resolved**: [C1](../critical-problems.md#c1-dry-thresholds--comparisons-duplicated) · [C2](../critical-problems.md#c2-monolith-spec-vs-companion-file) · [C3](../critical-problems.md#c3-composition-table-vs-widget-details--source-of-truth) · [C4](../critical-problems.md#c4-error-reporting-quality) · [C5](../critical-problems.md#c5-test-fixture-location)
- **Reference**: [`../reference/spec-format-design.md`](../reference/spec-format-design.md) · [`../reference/architecture.md`](../reference/architecture.md) §2 Design Spec Format v2
- **Research**: [`../../reports/research-260527-2300-tool-agnostic-design-spec.md`](../../reports/research-260527-2300-tool-agnostic-design-spec.md) §3 Enhanced Format Design · [`../../reports/researcher-260527-visualization-type-mapping.md`](../../reports/researcher-260527-visualization-type-mapping.md) (viz × tools support matrix)
