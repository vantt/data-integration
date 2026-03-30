# Deploy Metabase Blueprint

Deploy analytics configurations (Dashboards, Questions, Models) from a Markdown blueprint to Metabase.

## Prerequisites

1. Metabase container must be running (`docker ps` to check)
2. Environment variables set: `METABASE_URL`, `METABASE_API_KEY` (or `METABASE_SESSION_ID`)
3. A valid blueprint file in `docs/metabase-workspace/`

## Context

Read `.skills/metabase-automation/SKILL.md` for the full Literate Configuration syntax reference.

## Steps

1. **Verify Blueprint Syntax**:
   - Headers: `## Collection`, `### Dashboard`, `### Model`, `#### Question`
   - Code blocks: ` ```sql `, ` ```json metabase-viz `, ` ```json metabase-pos `

2. **Run Deployment**:
   ```bash
   node .skills/metabase-automation/scripts/deploy_from_markdown.js <blueprint_path>
   ```

3. **Verify in Metabase UI** (http://localhost:3000) — check Collections for new dashboards.

## User Arguments

Blueprint file path: $ARGUMENTS
