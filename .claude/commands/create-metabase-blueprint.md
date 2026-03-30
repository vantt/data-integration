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
   - Target path: `docs/metabase-workspace/{domain}-blueprint-{purpose}.md`
   - Or use the scaffold script:
     ```bash
     node .skills/metabase-automation/scripts/create_blueprint.js <domain> <purpose>
     ```

3. **Refine the Blueprint**:
   - Ensure SQL table names match dbt models
   - Check `json metabase-viz` blocks for correct chart types
   - Add business context in plain text

4. **Deploy** when ready using `/deploy-metabase-blueprint`

## User Arguments

$ARGUMENTS
