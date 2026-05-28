---
title: "Architecture Decisions (LOCKED)"
status: locked
created: 2026-05-28
updated: 2026-05-28
---

# Architecture Decisions (LOCKED)

Research backing: see [reference/research-foundation.md](reference/research-foundation.md)

---

## D1: Skip Blueprint File (Direct Deploy)

**Choice**: Spec → parser → in-memory model → Metabase API. No blueprint file emitted.
**Rationale**: Blueprint as middleman = drift risk + slower iteration + no audit value beyond spec. Single source of truth.
**Scope**: Always. Legacy `deploy_from_markdown.js` stays until Phase 3 migration complete.
**Implementation note**: New `deploy_from_design_spec.js` + shared `lib/deploy-core.js`. `capture_dashboard.js` emits Design Spec only post-Phase 1.

---

## D2: Endgame = Semantic Layer (Hybrid Spec)

**Choice**: Hybrid — spec supports both `metric_ref` (endgame) and inline SQL (stepping stone).
**Rationale**: SQL-in-spec locks 30 dashboards into format incompatible with Looker/Lightdash. Semantic-layer-first needs aggregation engine now (3+ weeks). Hybrid ships Phase 2 in 2-3 days, endgame still reachable.
**Scope**: Schema from day 1. Phase 2-3: inline SQL. Phase 4: aggregation engine, gradual metric_ref migration.
**Implementation note**: Schema accommodates both `data.metric` + `data.dimensions` (endgame) and `data.sql` + `data.sql_dialect` (stepping stone) in same widget-config block.

---

## D3: Capture-First Migration Strategy

**Choice**: Enhance `capture_dashboard.js` to emit enhanced Design Spec first; auto-migrate 30 dashboards.
**Rationale**: Manual migration = 60-120 hours + schema bugs found late. Capture-first stress-tests schema against real diversity before parser code locks in.
**Scope**: Phase 1 (capture), Phase 3 (migration run). Auto-migrated specs get `draft-from-capture` status — require human review before `final`.
**Implementation note**: Round-trip validation is primary test: live dashboard → capture → spec → deploy → live dashboard. Diff baseline.

---

## D4: Spec Versioning (`spec_version` Field)

**Choice**: `spec_version: 2` in frontmatter. Parser supports v1 + v2 during transition.
**Rationale**: 30 dashboards depend on schema correctness; schema change without versioning = silent breakage.
**Scope**: Always. v1 = existing 25 thin specs (no field). v2 = enhanced with widget details (Phase 0+).
**Implementation note**: JSON Schema versioned alongside `spec_version`. Migration scripts provided on schema bumps. v1 specs parsed via legacy path (composition table only, no widget details, cannot direct-deploy).

---

## D5: Per-Tool Deployer Pattern

**Choice**: Each BI tool gets one deployer script that reads shared parser + per-tool catalog → calls tool API.
**Rationale**: Follows from D1. Per-tool converter (→ markdown file) replaced by per-tool deployer (→ API). Keeps abstraction cost low.
**Scope**: Phase 2+ (Metabase first). Phase 6 adds Evidence/Superset on-demand.
**Implementation note**: Shared `lib/design-spec-parser.js` + `lib/size-to-grid.js`. Scripts: `scripts/deploy_to_{tool}.js`. Phase 2 uses `deploy_from_design_spec.js`; rename to `deploy_to_metabase.js` when 2nd tool added (YAGNI).

---

## D6: Portability Badge (Honest Reporting)

**Choice**: Every deployer emits portability report — native/fallback/unsupported per viz type per tool.
**Rationale**: 7/25 viz types non-universal including most popular (gauge, progress-toward-goal, single-value-with-trend). Silent fallback = degraded output with no warning.
**Scope**: All deployers. `--portability` CLI flag toggles full cross-tool projection.
**Implementation note**: Each viz catalog declares `native | fallback | unsupported` per tool. Spec author sees warning when choosing non-universal viz. `fallback:` field in widget-config for graceful alternative.

---

## D7: JSON Schema from Day 1

**Choice**: Publish `widget-config.schema.json` (JSON Schema 2020-12) in Phase 0.
**Rationale**: YAML in markdown with no schema = silent typo failures. Editor validation is largest DX lever.
**Scope**: Phase 0+. VSCode YAML extension auto-validates via schema reference in YAML header.
**Implementation note**: Location: `.skills/analytics-design/schemas/widget-config.schema.json`. Parser validates against schema before processing. UTF-8 in value fields; ASCII-only kebab-case in keys/slugs.

---

## D8: Spec Schema Location (analytics-design)

**Choice**: `analytics-design` skill owns spec format; per-tool skill owns translation catalog + scripts.
**Rationale**: Analyst brain (tool-agnostic intent) stays separate from engineer brain (tool-specific impl). Prevents leakage.
**Scope**: Always. Cross-cutting concerns (Phase 4 aggregation engine) TBD — may need new skill folder.
**Implementation note**: `analytics-design` owns `WIDGET_CONFIG_SCHEMA.md`, `schemas/widget-config.schema.json`, `templates/design_spec_template.md`. Each `{tool}-automation` skill owns `{TOOL}_VIZ_CATALOG.md` + `lib/` + `scripts/`. Shared parser lives in metabase-automation until 2nd tool added.
