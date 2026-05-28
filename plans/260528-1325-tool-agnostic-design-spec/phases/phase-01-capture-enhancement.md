---
title: "Phase 1 — Capture Enhancement"
status: not_started
priority: P0
depends_on: [phase-00]
created: 2026-05-28
updated: 2026-05-28
duration_estimate: "1-2 days"
---

## Goal

Enhance the existing `generate-design-spec-from-dashboard.js` script to emit v2 Design Spec
(with Widget Details section, v2 frontmatter, `spec_version: 2`). Running one command against
a live Metabase dashboard produces a spec that passes Phase 0's JSON Schema validation.

## Scope

**IN**:
- Enhance `generate-design-spec-from-dashboard.js`: read live Metabase dashboard → emit v2 spec
  with `### Widget Details` section (per-widget `yaml widget-config` blocks)
- Map Metabase `visualization_settings` → standard vocab terms via `METABASE_VIZ_CATALOG.md`
  reverse rules; output must contain no `unknown` viz types
- Emit `status: draft-from-capture` and `spec_version: 2` in frontmatter
- Ensure `METABASE_VIZ_CATALOG.md` has complete reverse-disambiguation for all Metabase viz types
- Update slash command wrapper `capture-metabase-dashboard.md`

**OUT**:
- Deploying captured specs to Metabase (Phase 2)
- Promoting `draft-from-capture` → `final` (per-dashboard editorial work, Phase 3)
- Migrating all 25-26 dashboards (Phase 3)

## Steps

1. Read starting point:
   - `D:\Vantt\app\data-integration\.skills\metabase-automation\scripts\generate-design-spec-from-dashboard.js`
   - `D:\Vantt\app\data-integration\.skills\metabase-automation\METABASE_VIZ_CATALOG.md`
     (check §4 or equivalent reverse-mapping section)
   - Phase 0 output: `widget-config.schema.json` (must be stable before this phase starts)

2. Audit `METABASE_VIZ_CATALOG.md` reverse rules: for each Metabase `display` value
   (`table`, `bar`, `line`, `area`, `scalar`, `smartscalar`, `gauge`, `progress`, `funnel`, `pie`,
   `row`, `waterfall`, `combo`, `scatter`, `map`), confirm a standard vocab term is mapped.
   Add missing entries. Note: `smartscalar` + `scalar.comparisons` quirk (v0.58.11 broken —
   see memory `feedback_metabase_scalar_comparisons.md`) — map to `single-value-with-trend` with
   a `capture_note` field warning deployers.

3. In `generate-design-spec-from-dashboard.js`, extend the output generation:
   - After emitting existing composition table section, add `### Widget Details` section
   - For each dashcard:
     - Generate `#### W:{slug}` header (slugify card name, ASCII kebab-case)
     - Emit domain link if card name matches a known domain metric keyword (best-effort, fallback empty)
     - Emit `yaml widget-config` fence block:
       - `data:` with `sql_dialect: duckdb` and `sql:` (preserve verbatim SQL from question)
       - `viz:` with `type:` (mapped via METABASE_VIZ_CATALOG.md reverse), viz-specific settings
       - `layout:` with `row:`, `width:`, `height:` (reverse-compute from grid coords)
       - `overrides.metabase:` for any Metabase-specific settings that don't map to vocab
   - Emit Widget ID column in composition table (9-col v2 format)
   - Emit v2 frontmatter: `spec_version: 2`, `sql_dialect: duckdb`, `grid_base: 18`,
     `status: draft-from-capture`, `last_modified: {today}`

4. Handle size token reverse-mapping:
   - Metabase grid is 18 columns. Width: 18→full, 9→half, 6→one-third, 12→two-thirds, etc.
   - Row height: short (<4), medium (4-6), tall (>6) — use thresholds or document exact mapping

5. Handle multi-tab dashboards: group dashcards by `dashboard_tab_id`, emit one Widget Details
   subsection per tab.

6. Handle text cards (HTML/markdown): map to `viz.type: annotation` with `content:` field.
   These are tab_standards candidates.

7. Validate output: after generation, pipe captured spec through
   `validate-analytics-artifacts.js` (enhanced in Phase 0). Assert 0 schema errors.

8. Update `capture-metabase-dashboard.md` slash command:
   - Document that output is now v2 Design Spec (not blueprint)
   - Update usage example

9. Run end-to-end test: capture `sales_daily_operation` from staging Metabase.
   - Output file must pass JSON Schema validation
   - Composition table must match v1 spec in card count + tab structure
   - Widget Details section must be present for all cards

## Files Touched

- 🔧 `D:\Vantt\app\data-integration\.skills\metabase-automation\scripts\generate-design-spec-from-dashboard.js` — extend to emit v2
- 🔧 `D:\Vantt\app\data-integration\.skills\metabase-automation\METABASE_VIZ_CATALOG.md` — complete reverse-disambiguation
- 🔧 `D:\Vantt\app\data-integration\.claude\commands\capture-metabase-dashboard.md` — update docs

## Success Criteria

- [ ] `node generate-design-spec-from-dashboard.js sales_daily_operation` emits v2 spec with `spec_version: 2`
- [ ] Output passes `validate-analytics-artifacts.js` JSON Schema validation: 0 errors
- [ ] Output composition table matches v1 spec in tab count + card count
- [ ] Widget Details section present for all cards (no skipped widgets)
- [ ] All Metabase viz types map to standard vocab: 0 `unknown` entries in output
- [ ] Round-trip readiness: captured spec can be fed into Phase 2 deployer without manual edits

## Risks

- **`scalar.comparisons` reverse-mapping ambiguous**: Metabase v0.58.11 has broken `scalar.comparisons`
  (memory: `feedback_metabase_scalar_comparisons.md`). Capture may see malformed settings.
  Mitigation: map `smartscalar` display → `single-value-with-trend`; emit `capture_note:` in
  `overrides.metabase` block warning that comparison may need manual review.
- **SQL from captured questions has legacy quirks**: timezone assumptions, old table names.
  Acceptable — mark `status: draft-from-capture`. Phase 3 human review promotes to `final`.
- **Grid reverse-computation loses precision**: non-standard grid widths (e.g., 7 or 11 cols)
  don't map to clean size tokens. Mitigation: use nearest token + emit `overrides.metabase.col`
  and `overrides.metabase.size_x` for exact values.

## Cross-references

- **Decisions**: [D3 capture-first](../decisions.md#d3-capture-first-migration-strategy) · [D5 per-tool deployer](../decisions.md#d5-per-tool-deployer-pattern)
- **Reference**: [`../reference/spec-format-design.md`](../reference/spec-format-design.md) §Widget Details · [`../reference/architecture.md`](../reference/architecture.md) §3 Parser Contract
- **Research**: [`../../reports/research-260527-2300-tool-agnostic-design-spec.md`](../../reports/research-260527-2300-tool-agnostic-design-spec.md) §Reverse-Flow · [`../../reports/researcher-260527-2300-bi-dashboard-formats.md`](../../reports/researcher-260527-2300-bi-dashboard-formats.md) §Metabase visualization_settings
