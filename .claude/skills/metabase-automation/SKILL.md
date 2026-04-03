---
name: metabase-automation
description: Deploy analytics dashboards to Metabase (Phase 7-10). Use when user asks to deploy blueprint, create Metabase dashboard, manage Metabase resources, or translate design spec to Metabase. Engineer brain — TRANSLATE, BUILD, DEPLOY.
---

# Metabase Automation Skill

Metabase-specific engineer brain. Translates Design Specs into deployed dashboards.

**Full instructions**: Read `.skills/metabase-automation/SKILL.md` before proceeding.
**Strategy guide**: Read `.skills/metabase-automation/STRATEGY.md` for translation workflow.

## When to Activate

- User asks to "deploy dashboard", "create blueprint", "manage Metabase"
- User mentions blueprints, Metabase cards, collections, dashboard deployment
- Any Metabase-specific implementation work (Phase 7-10)

## Prerequisite

Requires a **Design Spec** from the `analytics-design` skill (Phase 0-6). If none exists, run analytics-design first.

## Key Commands

```bash
# Deploy from Markdown blueprint
node .skills/metabase-automation/scripts/deploy_from_markdown.js <blueprint.md>

# Deploy from JS config
node .skills/metabase-automation/scripts/deploy_from_config.js <config.js>

# Scaffold a new blueprint
node .skills/metabase-automation/scripts/create_blueprint.js <domain> <purpose>

# Capture live dashboard → blueprint
node .skills/metabase-automation/scripts/capture_dashboard.js <dashboard_id> [output.md]
```

## Key References

| Resource | Location |
|----------|----------|
| Full API docs | `.skills/metabase-automation/SKILL.md` |
| Strategy | `.skills/metabase-automation/STRATEGY.md` |
| Viz Catalog | `.skills/metabase-automation/METABASE_VIZ_CATALOG.md` |
| Blueprint Template | `.skills/metabase-automation/templates/blueprint_template.md` |
| Existing Blueprints | `docs/analytics-handbook/blueprints/` |

## Environment Variables

- `METABASE_URL` — Base URL (default: http://127.0.0.1:3000/)
- `METABASE_API_KEY` — API Key (preferred)
- `METABASE_SESSION_ID` — Session token (alternative)
- `METABASE_DB_NAME` — Target database (default: "Sapo DuckDB")
