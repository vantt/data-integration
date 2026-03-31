# Claude Code Project Context

This file provides Claude Code with project-specific context. For full project documentation, see `AGENTS.md`.

## Skills & Workflows

Shared skills live in `tools/` and are available as slash commands via `.claude/commands/`.

### Metabase Automation

| Command | Purpose |
| --- | --- |
| `/create-metabase-blueprint` | Create a new analytics blueprint (Markdown) |
| `/deploy-metabase-blueprint` | Deploy a blueprint to Metabase |
| `/manage-metabase-resources` | Programmatically manage Metabase resources |
| `/setup-metabase-mcp` | Configure the Metabase MCP server |
| `/purge-dagster-runs` | Clean up old Dagster run history |

### Key References

- **Skill Documentation**: `.skills/metabase-automation/SKILL.md`
- **Strategy Guide**: `.skills/metabase-automation/STRATEGY.md`
- **Blueprint Template**: `.skills/metabase-automation/templates/blueprint_template.md`
- **Existing Blueprints**: `docs/analytics-handbook/blueprints/`

### Deployment Commands

```bash
# Deploy from Markdown blueprint
node .skills/metabase-automation/scripts/deploy_from_markdown.js <blueprint.md>

# Deploy from JS config
node .skills/metabase-automation/scripts/deploy_from_config.js <config.js>

# Scaffold a new blueprint
node .skills/metabase-automation/scripts/create_blueprint.js <domain> <purpose>
```

### Environment Variables (Metabase)

- `METABASE_URL` — Base URL (default: http://127.0.0.1:3000/)
- `METABASE_API_KEY` — API Key (preferred auth method)
- `METABASE_SESSION_ID` — Session token (alternative auth)
- `METABASE_DB_NAME` — Target database name (default: "Sapo DuckDB")

## Important

- **Always read `AGENTS.md`** for full project context (architecture, constraints, multi-project rules).
- **Read `.skills/metabase-automation/STRATEGY.md`** before designing any Metabase dashboard.
- **Read sub-project `AGENTS.md`** files (e.g., `transformation/AGENTS.md`) before working in a sub-component.
