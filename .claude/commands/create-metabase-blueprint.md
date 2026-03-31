# Create Metabase Blueprint

Create a new Analytics Blueprint using the Literate Configuration standard.

## Context

Read these files before proceeding:
- `.skills/metabase-automation/STRATEGY.md` — Dashboard archetypes & visualization heuristics
- `.skills/metabase-automation/templates/blueprint_template.md` — Markdown syntax reference

## Steps

1. **Define Requirements** with the user:
   - **Domain**: e.g., Logistics, Finance, Marketing
   - **Key Metrics**: e.g., "Late Deliveries", "CAC", "Churn"
   - **Dashboards**: e.g., "Daily Operations", "Executive Overview"

2. **Generate the Blueprint File**:
   - Target path: `docs/analytics-handbook/blueprints/{domain}_{purpose}.md`
   - Or use the scaffold script:
     ```bash
     node .skills/metabase-automation/scripts/create_blueprint.js <domain> <purpose>
     # With tabs:
     node .skills/metabase-automation/scripts/create_blueprint.js <domain> <purpose> --tabs
     ```

3. **Refine the Blueprint**:
   - Ensure SQL table names match dbt models
   - Check `json metabase-viz` blocks for correct chart types
   - Add business context in plain text
   - Use `### 📑 Tab: <Name>` to organize questions into tabs (optional)

4. **Deploy** when ready using `/deploy-metabase-blueprint`

## User Arguments

$ARGUMENTS
