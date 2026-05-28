---
title: "Phase 2 — Direct Deploy"
status: not_started
priority: P0
depends_on: [phase-00, phase-01]
created: 2026-05-28
updated: 2026-05-28
duration_estimate: "2-3 days"
---

## Goal

Build the Design Spec → Metabase API direct deploy path. A single command
`node deploy_from_design_spec.js <spec.md>` reads a v2 spec, validates it, computes grid layout,
and deploys to Metabase — no intermediate blueprint file emitted.

## Scope

**IN**:
- `lib/design-spec-parser.js`: markdown + YAML frontmatter → `DesignSpec` object
- `lib/size-to-grid.js`: pure function, size tokens → grid coordinates
- `lib/deploy-core-metabase.js`: in-memory `DesignSpec` → Metabase API calls
- `scripts/deploy_from_design_spec.js`: entry point CLI script
- Per-tool catalog update: `METABASE_VIZ_CATALOG.md` — add `support_level` column
  (native / fallback / unsupported) per viz type for portability badge (D6)
- Portability badge: `--portability` flag prints support-level table
- Slash command update: `deploy-metabase-blueprint.md` — add v2 path or split

**OUT**:
- Other BI tool deployers (Phase 6, on-demand)
- Migrating production dashboards (Phase 3)
- Sunsetting legacy scripts (Phase 5)
- Aggregation engine / `metric_ref` resolution (Phase 4)

## Steps

1. Read before building:
   - `../reference/architecture.md` §3 Parser Contract, §4 Deployer Contract
   - `D:\Vantt\app\data-integration\.skills\metabase-automation\lib\metabase_core.js` (reuse API wrapper)
   - `D:\Vantt\app\data-integration\.skills\metabase-automation\scripts\deploy_from_markdown.js`
     (extract idempotency logic — match-by-name, update-in-place)
   - Phase 0 output: `widget-config.schema.json`

2. **`lib/design-spec-parser.js`**:
   - Parse frontmatter (js-yaml), markdown sections (markdown-it)
   - Detect `spec_version`: if absent → v1 (composition table only); if `2` → full v2 parse
   - Parse `### Widget Details` section: extract each `#### W:{slug}` block, parse
     `yaml widget-config` fence
   - Validate each widget-config against `widget-config.schema.json`; throw on validation error
     with `file:line` context and suggested fix (resolves E.4)
   - Resolve `inherit_from: defaults` references against frontmatter `defaults:` block
   - Return typed `DesignSpec` object (see `../reference/architecture.md` §3 for shape)

3. **`lib/size-to-grid.js`**:
   - Input: `{ width: SizeToken, height: SizeToken, row: string, grid_base: number }`
   - Width tokens → column count: `full=18`, `two-thirds=12`, `half=9`, `one-third=6`,
     `one-quarter=4` (adjust if `grid_base` differs from 18)
   - Height tokens → row count: `short=2`, `medium=4`, `tall=6`, `hero=8`
   - Accumulate `col` offset per row letter (reset at each new row)
   - Validate: sum of widths per row must equal `grid_base`; throw with row letter on failure
   - Export pure function — no side effects, fully unit-testable
   - Write unit tests covering all token combinations + multi-row + row overflow error

4. **`lib/deploy-core-metabase.js`**:
   - Accept `DesignSpec` + deploy options (`target`, `dryRun`, `emitPortabilityReport`)
   - For each widget: translate `viz.type` → Metabase `display` + `visualization_settings`
     via `METABASE_VIZ_CATALOG.md` forward rules
   - Translate color tokens → Metabase color hex values
   - Render `tab_standards.period_header` as Metabase scalar question with `strftime` SQL
     (tool-native rendering per `../reference/architecture.md` §6)
   - Build filter parameters + auto-wire by widget slug
   - Call `metabase_core.js` API: create/update questions, create/update dashboard tabs,
     place dashcards at computed grid positions
   - Idempotency: match existing cards by tab + card name slug; update in-place, don't duplicate
     (reuse pattern from `deploy_from_markdown.js`)
   - If `dryRun`: print plan without API calls
   - If `emitPortabilityReport`: aggregate per-viz `support_level` across all widgets,
     print portability table

5. **`scripts/deploy_from_design_spec.js`**:
   - CLI: `node deploy_from_design_spec.js <spec.md> [--target staging|production] [--dry-run]
     [--portability]`
   - Default target: `staging`
   - Load env vars: `METABASE_URL`, `METABASE_API_KEY` (see project `.env`)
   - Read `> **Database:**` override from spec header (same as existing blueprint deploy,
     memory `feedback_blueprint_db_override.md`)
   - Call parser → deployer → print result summary

6. **`METABASE_VIZ_CATALOG.md`** additions:
   - Add `support_level` column: `native | fallback | unsupported`
   - Add `fallback_to` field for non-native types (informs portability badge output)

7. **`deploy-metabase-blueprint.md`** slash command:
   - Add section documenting v2 path: `node deploy_from_design_spec.js <spec.md>`
   - Keep legacy v1 path documented until Phase 5 sunset

8. Validate round-trip on `sales_daily_operation`:
   - Use Phase 1 captured v2 spec
   - Deploy to staging Metabase
   - Run `generate-design-spec-from-dashboard.js` on the newly deployed dashboard
   - Diff output against source spec: composition table must match, Widget Details present

## Files Touched

- ✨ `D:\Vantt\app\data-integration\.skills\metabase-automation\lib\design-spec-parser.js`
- ✨ `D:\Vantt\app\data-integration\.skills\metabase-automation\lib\size-to-grid.js`
- ✨ `D:\Vantt\app\data-integration\.skills\metabase-automation\lib\deploy-core-metabase.js`
- ✨ `D:\Vantt\app\data-integration\.skills\metabase-automation\scripts\deploy_from_design_spec.js`
- 🔧 `D:\Vantt\app\data-integration\.skills\metabase-automation\METABASE_VIZ_CATALOG.md` — add `support_level` + `fallback_to`
- 🔧 `D:\Vantt\app\data-integration\.claude\commands\deploy-metabase-blueprint.md` — add v2 deploy path

## Success Criteria

- [ ] Parser validates input against `widget-config.schema.json`; returns typed `DesignSpec`
- [ ] Parser errors include `file:line` reference and suggested fix (not raw JSON Schema output)
- [ ] `size-to-grid.js` unit tests pass: all width/height token combinations, multi-row accumulation,
  row overflow throws with row letter
- [ ] `deploy_from_design_spec.js sales_daily_operation_v2.md --target staging` completes without errors
- [ ] Round-trip: Phase 1 capture → v2 spec → deploy → re-capture → composition table matches
- [ ] Visual diff (manual): deployed staging dashboard vs existing production ≥ 95% match
- [ ] `--portability` flag prints support-level table with native/fallback/unsupported per widget
- [ ] `--dry-run` prints full deploy plan without API calls

## Risks

- **Idempotency edge cases (renamed cards orphaned)**: if a widget slug changes between deploys,
  old card lingers.
  Mitigation: match by tab + card name (same as `deploy_from_markdown.js`); document slug-rename
  as breaking change in spec changelog.
- **Filter wiring auto-mapping breaks on complex filter configs**: slug-based matching may miss
  field_id-dependent filters (memory: `feedback_metabase_field_filter_required.md`).
  Mitigation: reuse `metabase_core.js` field-filter resolution; emit clear error if field_id
  cannot be resolved.
- **Grid calc fails on multi-tab dashboards with non-uniform row widths**: each tab's rows
  accumulate independently.
  Mitigation: `size-to-grid.js` resets accumulator per tab+row; unit test multi-tab case explicitly.

## Cross-references

- **Decisions**: [D1 skip blueprint](../decisions.md#d1-skip-blueprint-file-direct-deploy) · [D5 per-tool deployer](../decisions.md#d5-per-tool-deployer-pattern) · [D6 portability badge](../decisions.md#d6-portability-badge-honest-reporting) · [D7 JSON Schema](../decisions.md#d7-json-schema-from-day-1)
- **Critical problems**: [C.4 error reporting](../critical-problems.md#c4-error-reporting-quality) · [C.5 test fixtures](../critical-problems.md#c5-test-fixture-location)
- **Reference**: [`../reference/architecture.md`](../reference/architecture.md) §3-4 Parser + Deployer contracts · [`../reference/spec-format-design.md`](../reference/spec-format-design.md)
- **Research**: [`../../reports/researcher-260527-2348-dashboard-json-formats.md`](../../reports/researcher-260527-2348-dashboard-json-formats.md) §Metabase grid + viz JSON
