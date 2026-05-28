---
title: "Architecture — Tool-Agnostic Design Spec"
status: reference
created: 2026-05-28
updated: 2026-05-28
---

See [research-foundation.md](research-foundation.md) for sources.

## 1. Current State + Pain Points

**Current flow**: Blueprint `.md` hand-authored → `deploy_from_markdown.js` → Metabase API

**Problems**:
- 35 blueprints × 500-1500 lines = tedious manual authoring (60-120h migration cost)
- Metabase-locked: blueprint format only understood by Metabase deployer, no reuse for other tools
- Dashboard intent (WHAT to measure) tightly coupled to tool implementation (HOW Metabase renders it)
- Drift risk: spec and blueprint can diverge if one is updated without the other
- No machine-readable widget config → no schema validation, silent YAML typos

**Target**: Design Spec = tool-agnostic source of truth. No blueprint intermediate file. See `../critical-problems.md` for detailed problem statements.

---

## 2. Target System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  Domain Files (docs/analytics-handbook/domains/*.md)                │
│  - Phase 0-3: descriptive (Business Definition, Formula, SQL hint)  │
│  - Phase 4+: executable metric defs (semantic-layer source)         │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ (metric_ref resolution, Phase 4+)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Design Spec  (docs/analytics-handbook/designs/*.md)                │
│  - Frontmatter (spec_version: 2, archetype, defaults)               │
│  - Brief, Constraints & Filters (structured YAML)                   │
│  - Views, Composition table                                         │
│  - Widget Details (per-widget SQL or metric_ref + config YAML)      │
│  - Action Map, Tab Standards, Finish Checklist                      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ parse
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Parser  (.skills/analytics-design/lib/design-spec-parser.js)       │
│  - Validates against widget-config.schema.json                      │
│  - Resolves metric_ref → SQL (Phase 4+) OR passes through inline SQL│
│  - Computes grid positions from size tokens                         │
│  - Returns in-memory DesignSpec object                              │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ in-memory model
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Metabase    │  │  Evidence    │  │  Superset    │
│  Deployer    │  │  Deployer    │  │  Deployer    │
│ (Phase 2)    │  │ (on-demand)  │  │ (on-demand)  │
│              │  │              │  │              │
│ Uses:        │  │ Uses:        │  │ Uses:        │
│ METABASE_VIZ │  │ EVIDENCE_VIZ │  │ SUPERSET_VIZ │
│ _CATALOG.md  │  │ _CATALOG.md  │  │ _CATALOG.md  │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                  │                  │
       ▼                  ▼                  ▼
   Metabase API     Evidence pages      Superset API
```

No blueprint markdown file emitted. Direct deploy.

---

## 3. File Layout (Post-Implementation)

```
.skills/analytics-design/                       # Analyst brain (tool-agnostic)
├── SKILL.md                                    # Updated: Phase 5-6 includes widget-config authoring
├── DOMAIN_MODELING.md                          # Unchanged
├── COMPOSITION_PATTERNS.md                     # Unchanged
├── VISUALIZATION_VOCABULARY.md                 # Unchanged
├── VISUAL_LANGUAGE.md                          # Unchanged
├── COMPARATIVE_FRAMING.md                      # Unchanged
├── WIDGET_CONFIG_SCHEMA.md                     # NEW — schema reference doc
├── templates/
│   ├── design_spec_template.md                 # Enhanced (Widget Details section)
│   ├── domain_template.md
│   ├── playbook_template.md
│   └── guide_template.md
└── schemas/
    └── widget-config.schema.json               # NEW — JSON Schema (machine validation)

.skills/metabase-automation/                    # Engineer brain (Metabase-specific)
├── SKILL.md                                    # Updated: refer to direct-deploy path
├── STRATEGY.md                                 # Updated: blueprint deprecation timeline
├── METABASE_VIZ_CATALOG.md                     # Unchanged (translation table)
├── lib/
│   ├── design-spec-parser.js                   # NEW (shared — extracts later)
│   ├── size-to-grid.js                         # NEW
│   ├── deploy-core-metabase.js                 # NEW (in-memory model → Metabase API)
│   ├── markdown_parser.js                      # Legacy (blueprint format, kept for old dashboards)
│   ├── metabase_core.js                        # Unchanged
│   └── text-card-helpers.js                    # Unchanged
├── scripts/
│   ├── deploy_from_design_spec.js              # NEW — primary path
│   ├── deploy_from_markdown.js                 # Legacy (backward compat)
│   ├── capture_dashboard.js                    # ENHANCED — emits enhanced Design Spec
│   ├── create_blueprint.js                     # Legacy
│   └── ... (other existing scripts)
└── templates/
    └── blueprint_template.md                   # Legacy (kept for reference)

docs/analytics-handbook/
├── designs/*.md                                # Enhanced specs (spec_version: 2)
├── blueprints/*.md                             # Legacy (sunset Phase 5)
├── domains/*.md                                # Phase 4+: executable metric defs
├── playbooks/*.md
└── guides/*.md
```

---

## 4. Problems Identified

Major problems driving this initiative — detail in `../critical-problems.md`:

- **Blueprint-as-bottleneck**: 35 blueprints hand-authored, Metabase-locked, cannot reuse intent for other tools. Blueprint folder will reach 50+ if not addressed.
- **No widget-level machine-readable config**: Current specs have composition table (human-readable) but no YAML widget config. Parser cannot validate, deployer cannot auto-wire filters or compute positions.
- **SQL hardcoded in blueprints**: Same SQL duplicated across dashboards (e.g., net_revenue across 8 dashboards). Domain file is descriptive, not executable — no DRY metric layer.
- **Capture gap**: `generate-design-spec-from-dashboard.js` emits thin v1 spec (composition table only). Cannot round-trip: re-deploying a captured spec loses all widget config detail.
