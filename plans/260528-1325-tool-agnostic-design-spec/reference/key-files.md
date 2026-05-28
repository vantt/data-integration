---
title: "Key Files — Complete Index"
status: reference
created: 2026-05-28
updated: 2026-05-28
---

See [research-foundation.md](research-foundation.md) for research report index (moved from origin §2).

**Status legend**:
- 📖 **Reference** — frozen background reading, not modified
- ✅ **Updated** — already edited in this initiative
- 🔧 **To enhance** — existing file, will be modified in upcoming phase
- ✨ **To create** — net new file, comes in upcoming phase
- 🗄️ **To sunset** — kept temporarily for backward compat, archived later
- 🚫 **Unchanged** — exists, related but not touched

---

## 3. Analytics Design Skill (analyst brain)

`.skills/analytics-design/`

| File | Status | Phase | Notes |
|------|--------|-------|-------|
| SKILL.md | ✅ Updated 2026-05-28 | — | Added forthcoming note pointing to plan dir |
| DOMAIN_MODELING.md | 🚫 Unchanged | — | Domain doc structure, executable metric defs come Phase 4 |
| COMPOSITION_PATTERNS.md | 🚫 Unchanged | — | Archetypes, card roles |
| VISUALIZATION_VOCABULARY.md | 🔧 To enhance | Phase 0 | Add per-tool support level column; cross-link to widget-config schema per viz type |
| VISUAL_LANGUAGE.md | 🚫 Unchanged | — | Color/size semantic tokens |
| COMPARATIVE_FRAMING.md | 🚫 Unchanged | — | Comparison rules |
| templates/design_spec_template.md | 🔧 To enhance | Phase 0 | Add Widget Details section, frontmatter fields (spec_version, sql_dialect, grid_base, defaults, tab_standards), Tab Standards section |
| templates/domain_template.md | 🚫 Unchanged Phase 0-3, 🔧 Phase 4 | Phase 4 | Phase 4: add executable metric_def block |
| templates/playbook_template.md | 🚫 Unchanged | — | |
| templates/guide_template.md | 🚫 Unchanged | — | |
| WIDGET_CONFIG_SCHEMA.md | ✨ To create | Phase 0 | Human reference doc for widget-config YAML schema (per ADR-8) |
| schemas/widget-config.schema.json | ✨ To create | Phase 0 | JSON Schema 2020-12 for IDE validation (per ADR-7) |
| lib/design-spec-parser.js | ✨ To create | Phase 2 | Parser, may relocate from metabase-automation when 2nd tool added |

---

## 4. Metabase Automation Skill (engineer brain)

`.skills/metabase-automation/`

| File | Status | Phase | Notes |
|------|--------|-------|-------|
| SKILL.md | 🚫 Unchanged | — | Engineer workflow doc; STRATEGY.md carries direction note |
| STRATEGY.md | ✅ Updated 2026-05-28 | — | Added forthcoming note about direct-deploy path |
| METABASE_VIZ_CATALOG.md | 🔧 To enhance | Phase 2 | Add per-tool support level marker, extend with widget-config translation mappings |
| lib/markdown_parser.js | 🗄️ Legacy | Phase 5 | Blueprint parser, kept until blueprint folder sunsets |
| lib/metabase_core.js | 🚫 Unchanged | — | Metabase API wrapper, reused by new deploy path |
| lib/text-card-helpers.js | 🚫 Unchanged | — | Text card idempotency helpers, reused |
| lib/resources/ | 🚫 Unchanged | — | Resource definitions |
| lib/design-spec-parser.js | ✨ To create | Phase 2 | Initial location (may move to analytics-design later) |
| lib/size-to-grid.js | ✨ To create | Phase 2 | Pure function: size tokens → grid coordinates |
| lib/deploy-core-metabase.js | ✨ To create | Phase 2 | In-memory model → Metabase API |
| scripts/capture_dashboard.js | 🔧 To enhance | Phase 1 | Currently emits Metabase blueprint markdown; enhance to optionally emit enhanced Design Spec |
| scripts/generate-design-spec-from-dashboard.js | 🔧 To enhance | Phase 1 | **Already exists** — currently emits thin v1 spec (composition only). Enhance to emit v2 with Widget Details. **This IS the capture-first entry point.** |
| scripts/deploy_from_design_spec.js | ✨ To create | Phase 2 | Primary entry: spec → Metabase API direct |
| scripts/deploy_from_markdown.js | 🗄️ Legacy | Phase 5 | Blueprint deployer, kept for backward compat |
| scripts/deploy_from_config.js | 🚫 Unchanged | — | JS-config based deploy (rare path) |
| scripts/create_blueprint.js | 🗄️ Legacy | Phase 5 | Blueprint scaffolder, sunset with blueprints |
| scripts/metabase_client.js | 🚫 Unchanged | — | Low-level Metabase REST client |
| scripts/patch-dashcard-viz.js | 🚫 Unchanged | — | Surgical viz patching utility |
| scripts/usage_example.js | 🚫 Unchanged | — | Example usage doc |
| scripts/validate-analytics-artifacts.js | 🔧 To enhance | Phase 0 | Currently validates v1 spec sections; add v2 validation (JSON Schema check, widget-config presence) |
| templates/blueprint_template.md | 🗄️ Legacy | Phase 5 | Blueprint reference, kept for old dashboards |

---

## 5. Production Artifacts (analytics handbook)

`docs/analytics-handbook/`

### 5.1 Designs (25 specs — migration targets)

| File | Status | Phase |
|------|--------|-------|
| designs/README.md | 🚫 Unchanged | — |
| designs/sales_daily_operation.md | 🔧 Phase 0 spike + Phase 3 migrate | Phase 0+3 | **Primary validation target** — most complex dashboard (4 views, ~30+ widgets, all viz types). Phase 0 manually transcribes 5 widgets. Phase 3 auto-migrates entire file. |
| designs/sales_yesterday_operation.md | 🔧 Phase 3 | Phase 3 | |
| designs/ceo_monthly_scorecard.md | 🔧 Phase 3 | Phase 3 | |
| designs/ceo_weekly_pulse.md | 🔧 Phase 3 | Phase 3 | |
| designs/{22 others}.md | 🔧 Phase 3 | Phase 3 | All v1 specs auto-migrated via enhanced capture |

### 5.2 Blueprints (35 blueprints — sunset targets)

| File | Status | Phase |
|------|--------|-------|
| blueprints/sales_daily_operation.md | 🗄️ Sunset Phase 5 | Phase 5 | Primary validation source. Kept as ground-truth for round-trip validation, then archived. |
| blueprints/{34 others}.md | 🗄️ Sunset Phase 5 | Phase 5 | All blueprints kept until Phase 5; archived to `blueprints/archive/` or removed |
| blueprints/rill/ | 🚫 Unchanged | — | Separate sub-folder (different deployment target?) — investigate Phase 5 |

### 5.3 Domains (7 files — Phase 4 semantic-layer source)

| File | Status | Phase |
|------|--------|-------|
| domains/sales.md | 🔧 Phase 4 | Phase 4 | Add executable metric_def blocks for net_revenue, orders, AOV, etc. |
| domains/customer.md | 🔧 Phase 4 | Phase 4 | |
| domains/customer_support.md | 🔧 Phase 4 | Phase 4 | |
| domains/finance.md | 🔧 Phase 4 | Phase 4 | |
| domains/logistics.md | 🔧 Phase 4 | Phase 4 | |
| domains/operations.md | 🔧 Phase 4 | Phase 4 | |
| domains/product.md | 🔧 Phase 4 | Phase 4 | |

### 5.4 Playbooks, Guides (referenced, mostly unchanged)

| Folder | Status |
|--------|--------|
| playbooks/*.md | 🚫 Unchanged — Referenced by specs for Action Triggers |
| guides/*.md | 🚫 Unchanged — Referenced for concept explanations |

---

## 6. Slash Commands (analytics workflows)

`.claude/commands/`

| File | Status | Phase | Notes |
|------|--------|-------|-------|
| design-dashboard.md | 🚫 Unchanged Phase 0-2, 🔧 Phase 3+ | Phase 3+ | Currently designs v1 spec. Update to author v2 spec post-schema-stable |
| create-metabase-blueprint.md | 🗄️ Legacy | Phase 5 | Full pipeline Phase 0-6 + 7-10 → blueprint. Sunsets with blueprint folder. |
| deploy-metabase-blueprint.md | 🗄️ Legacy → 🔧 Rename Phase 2 | Phase 2 | Currently wraps `deploy_from_markdown.js`. Add v2 path or split into `deploy-design-spec.md` |
| capture-metabase-dashboard.md | 🔧 To enhance | Phase 1 | Wraps `capture_dashboard.js` + reverse-flow. Update to emit v2 Design Spec |
| manage-metabase-resources.md | 🚫 Unchanged | — | |
| setup-metabase-mcp.md | 🚫 Unchanged | — | |

---

## 7. Project Root References

| File | Status | Notes |
|------|--------|-------|
| CLAUDE.md (project) | 🚫 Unchanged | Lists skills and slash commands; update only after Phase 2 stabilizes new path |
| AGENTS.md | 🔧 Possibly Phase 2+ | Update if direct-deploy changes recommended workflow |
| README.md | 🚫 Unchanged | |

---

## 8. Memory References (cross-session knowledge)

`C:\Users\Vantt\.claude\projects\D--Vantt-app-data-integration\memory\`

Relevant entries (read-only; reference during implementation):

| Entry | Relevance |
|-------|-----------|
| feedback_metabase_scalar_comparisons.md | Metabase v0.58.11 scalar.comparisons quirks affect single-value-with-trend support |
| feedback_metabase_field_filter_required.md | Filter config quirks affect interactive filter schema |
| feedback_blueprint_db_override.md | Database override mechanism, relevant to direct-deploy |
| project_timezone_architecture.md | UTC vs ICT, affects SQL generation in Phase 4 aggregation engine |
| feedback_duckdb_view_rebuild.md | DuckDB view rebuild after column rename, relevant to migration |

---

## 9. External References

| Reference | Status | Use |
|-----------|--------|-----|
| Metabase API docs | 📖 | `deploy-core-metabase.js` reference |
| dbt MetricFlow docs | 📖 | Phase 4 aggregation engine evaluation |
| JSON Schema 2020-12 spec | 📖 | `widget-config.schema.json` authoring |
| markdown-it / js-yaml NPM | 📖 | Existing dependencies, used by parser |

---

## Summary Counts

| Category | Count | Status mix |
|----------|-------|-----------|
| Plan dir docs | 5 created + 7-8 phase docs pending | 5 ✅, 7-8 ✨ |
| Research reports | 6 | 6 📖 |
| Analytics-design skill files | 11 (incl. templates) | 1 ✅, 1 🔧, 8 🚫, 2 ✨ |
| Metabase-automation skill files | 16 | 1 ✅, 4 🔧, 6 🚫, 3 ✨, 4 🗄️ |
| Production designs | 26 | 25 🔧 (migrate), 1 🚫 |
| Production blueprints | 35 | 35 🗄️ (sunset) |
| Production domains | 7 | 7 🔧 (Phase 4) |
| Slash commands | 6 | 2 🔧, 4 🚫/🗄️ |

**Files touched / created across all phases**: ~50+ files
**Files purely sunset (archive)**: ~35 blueprints + 4 legacy scripts/templates

---

## Quick Navigation by Phase

### Phase 0 (Schema Spike — 1 day)
Read: [spec-format-design.md](spec-format-design.md) §1-3, [parser-deployer-spec.md](parser-deployer-spec.md) §3
Touch: `WIDGET_CONFIG_SCHEMA.md` ✨, `schemas/widget-config.schema.json` ✨, `templates/design_spec_template.md` 🔧, `VISUALIZATION_VOCABULARY.md` 🔧, `validate-analytics-artifacts.js` 🔧
Validate against: `designs/sales_daily_operation.md` + `blueprints/sales_daily_operation.md`
Phase plan: [../phases/phase-00-schema-spike.md](../phases/phase-00-schema-spike.md)

### Phase 1 (Capture Enhancement — 1-2 days)
Read: existing `generate-design-spec-from-dashboard.js` (it's the starting point!)
Touch: `generate-design-spec-from-dashboard.js` 🔧, `capture-metabase-dashboard.md` (slash cmd) 🔧
Validate: capture `sales_daily_operation` from staging Metabase, output passes Phase 0 schema
Phase plan: [../phases/phase-01-capture-enhancement.md](../phases/phase-01-capture-enhancement.md)

### Phase 2 (Direct Deployer — 2-3 days)
Touch: `design-spec-parser.js` ✨, `size-to-grid.js` ✨, `deploy-core-metabase.js` ✨, `deploy_from_design_spec.js` ✨, `METABASE_VIZ_CATALOG.md` 🔧
Validate: round-trip on `sales_daily_operation`
Phase plan: [../phases/phase-02-direct-deploy.md](../phases/phase-02-direct-deploy.md)

### Phase 3 (Migration — 3-5 days)
Run captures on 25 production dashboards → emit v2 specs
Touch: `designs/*.md` 🔧 (25 files)
Deploy to staging, visual diff, promote to production
Phase plan: [../phases/phase-03-dashboard-migration.md](../phases/phase-03-dashboard-migration.md)

### Phase 4 (Aggregation Engine — 3-5 days)
Touch: `domains/*.md` 🔧 (7 files), new aggregation engine code
Validate: 1 dashboard converts from inline SQL → metric_ref end-to-end
Phase plan: [../phases/phase-04-aggregation-engine.md](../phases/phase-04-aggregation-engine.md)

### Phase 5 (Sunset Blueprints — 0.5 day)
Archive: `blueprints/` → `blueprints/_archive_2026-XX/`
Remove: `deploy_from_markdown.js`, `create_blueprint.js`, `blueprint_template.md`
Update: slash commands, `CLAUDE.md`, `AGENTS.md`
Phase plan: [../phases/phase-05-blueprint-sunset.md](../phases/phase-05-blueprint-sunset.md)
