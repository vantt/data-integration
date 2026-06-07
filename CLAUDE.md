# Claude Code Project Context

This file provides Claude Code with project-specific context. For full project documentation, see `AGENTS.md`.

## Skills & Workflows

Shared skills live in `.skills/` and are available as slash commands via `.claude/commands/`. Each command is a thin wrapper — logic lives in the skill's `SKILL.md`.

### Analytics Design (Tool-Agnostic)

| Command | Purpose |
| --- | --- |
| `/design-dashboard` | Design a dashboard (Phase 0-6 only, outputs Design Spec) |
| `/create-metabase-blueprint` | Full pipeline: Design (Phase 0-6) → Metabase Blueprint (Phase 7-10) |

### Metabase Automation (Implementation)

| Command | Purpose |
| --- | --- |
| `/deploy-metabase-blueprint` | Deploy a blueprint to Metabase |
| `/capture-metabase-dashboard` | Capture live dashboard → blueprint (layout, SQL, viz) |
| `/manage-metabase-resources` | Programmatically manage Metabase resources |
| `/setup-metabase-mcp` | Configure the Metabase MCP server |
| `/purge-dagster-runs` | Clean up old Dagster run history |

### Metabase Debugging

| Command | Purpose |
| --- | --- |
| `/debug-metabase <dashboard_url>` | Debug metric discrepancies — summary → pick card → deep-dive SQL + filters |

### Key References

- **Analytics Design Skill**: `.skills/analytics-design/SKILL.md`
- **Visualization Vocabulary**: `.skills/analytics-design/VISUALIZATION_VOCABULARY.md`
- **Metabase Skill**: `.skills/metabase-automation/SKILL.md`
- **Metabase Strategy**: `.skills/metabase-automation/STRATEGY.md`
- **Metabase Viz Catalog**: `.skills/metabase-automation/METABASE_VIZ_CATALOG.md`
- **Blueprint Template**: `.skills/metabase-automation/templates/blueprint_template.md`
- **Existing Blueprints**: `docs/analytics-handbook/blueprints/`
- **Design Specs**: `docs/analytics-handbook/designs/`
- **Debug Metabase Skill**: `.skills/debug-metabase/SKILL.md`

### Deployment Commands

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

### Environment Variables (Metabase)

- `METABASE_URL` — Base URL (default: http://127.0.0.1:3000/)
- `METABASE_API_KEY` — API Key (preferred auth method)
- `METABASE_SESSION_ID` — Session token (alternative auth)
- `METABASE_DB_NAME` — Target database name (default: "Sapo")

## Important

- **Always read `AGENTS.md`** for full project context (architecture, constraints, multi-project rules).
- **Read `.skills/analytics-design/SKILL.md`** before designing any dashboard (Phase 0-6).
- **Read `.skills/metabase-automation/STRATEGY.md`** before implementing in Metabase (Phase 7-10).
- **Read sub-project `AGENTS.md`** files (e.g., `transformation/AGENTS.md`) before working in a sub-component.
