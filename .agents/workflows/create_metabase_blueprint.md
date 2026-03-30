---
description: Create a new Metabase Blueprint (Markdown) for a specific business domain.
---

# Create Metabase Blueprint

This workflow guides you through creating a new Analytics Blueprint using the Literate Configuration standard.

## 1. Define Requirements

First, clearly state what you want to build.

- **Domain**: e.g., Logistics, Finance, Marketing.
- **Key Metrics**: e.g., "Late Deliveries", "CAC", "Churn".
- **Dashboards**: e.g., "Daily Operations", "Executive Overview".

## 2. Generate the File

Ask the Agent to create the file for you.

> "Create a new blueprint `docs/metabase-workspace/{domain}-blueprint-{purpose}.md` based on the template `.skills/metabase-automation/templates/blueprint_template.md`. Include the following metrics: [List specific metrics]."

**Example Prompt:**

> "Create `docs/metabase-workspace/logistics-blueprint-tracking.md`. It should have a 'Logistics' collection, a 'Shipments' model (from `fact_shipments`), and a dashboard 'Delivery Performance' with a line chart for 'Avg Delivery Time' and a bar chart for 'Shipments by Carrier'."

**Note**: If a playbook doesn't exist yet, consider creating `{domain}-playbook.md` first to document the business context and requirements.

## 3. Refine Logic

The agent will scaffold the file. You must then review and refine:

1.  **SQL Queries**: Ensure table names (`fact_orders`, etc.) match your dbt models.
2.  **Visualizations**: Check `json metabase-viz` blocks for correct chart types (`line`, `bar`, `pie`).
3.  **Descriptions**: Add business context in plain text.

## 4. Deploy

Once the blueprint is ready, use the deployment workflow:
`/deploy_metabase_blueprint`
