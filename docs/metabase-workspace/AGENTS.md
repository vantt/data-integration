# Metabase Workspace - Agent Guide

## 📋 Overview

The `metabase-workspace/` follows a simplified structure focused on clarity and ease of use:

- **Playbooks**: Complete guides combining business context with technical implementation
- **Blueprints**: Deployable Metabase configurations
- **Guides**: How-to documentation and best practices

## 🗂️ Structure and Purpose

### 📘 Playbooks

Comprehensive guides that combine business and technical aspects for each domain.

**Format**: `{domain}-playbook.md`

**What's Inside**:

1. **Business Context**
   - Who uses this analytics
   - Why it's needed
   - Update frequency

2. **Key Metrics & KPIs**
   - Definitions and formulas
   - Business rules
   - Targets and benchmarks

3. **Data Requirements**
   - Source tables
   - Data quality checks
   - Freshness SLAs

4. **SQL Library**
   - Tested queries with performance notes
   - Comments explaining logic
   - Sample outputs

5. **Dashboard Designs**
   - Layout mockups
   - Chart selection rationale
   - Filter strategies

6. **Cross-references to Blueprints**
   - Links to deployable configurations

**Example**:

```markdown
# Sales Analytics Playbook

## Business Context

Store managers need daily visibility into...

## Key Metrics

| Metric  | Formula    | Target    |
| ------- | ---------- | --------- |
| Revenue | SUM(total) | >$10k/day |

📘 **Blueprint**: [sales-blueprint-daily.md#revenue-section]
```

### 📄 Blueprints

Deploy-ready Metabase configurations following the Literate Configuration standard.

**Format**: `{domain}-blueprint-{purpose}.md`

**Structure**:

````markdown
# Sales Daily Dashboard Blueprint

📖 **Playbook**: [sales-playbook.md#daily-sales-metrics]

## Collection: Sales Analytics

### Dashboard: Daily Operations

#### Question: Revenue Today

```sql
SELECT SUM(total) FROM fact_orders WHERE DATE(created_on) = CURRENT_DATE
```
````

```json metabase-viz
{
  "display": "scalar",
  "scalar.field": "sum"
}
```

````

### 📚 Guides
How-to documentation for common tasks.

**Contents**:
- `metabase-concepts.md` - Understanding Models, Metrics, Questions
- `blueprint-syntax.md` - How to write deployable blueprints
- `troubleshooting.md` - Common issues and solutions

## 🔄 Workflow for Agents

### 1. Creating New Analytics

**Step 1: Understand Requirements**
- Read existing playbook or create new one
- Identify KPIs and metrics needed
- Determine update frequency

**Step 2: Design Solution**
- Choose appropriate visualizations
- Write and test SQL queries
- Plan dashboard layout

**Step 3: Create Blueprint**
- Use the scaffold script to generate a new file:
  ```bash
  node .agent/skills/metabase-automation/scripts/create_blueprint.js [domain] [purpose]
````

- Transform requirements into the blueprint format
- Add cross-references to playbook
- **Note**: Models are supported, but Metrics are currently experimental.

**Step 4: Deploy**

```bash
node .agent/skills/metabase-automation/scripts/deploy_from_markdown.js [blueprint-file]
```

### 2. Updating Existing Analytics

**For Content Changes**:

1. Update the playbook with new requirements
2. Modify the corresponding blueprint
3. Re-deploy to Metabase

**For Bug Fixes**:

1. Fix SQL in the blueprint directly
2. Document the fix in playbook
3. Re-deploy

## 📝 Best Practices for Agents

### When Writing Playbooks:

1. **Be Specific**: Don't say "need sales report", say "need hourly sales to optimize staffing"
2. **Document Why**: Always explain the business reason behind metrics
3. **Test Queries**: Include sample outputs and performance metrics
4. **Link to Blueprints**: Use anchor links for easy navigation

### When Writing Blueprints:

1. **Follow Template**: Use exact syntax for parser compatibility
2. **One Purpose**: Each blueprint serves one specific dashboard/use case
3. **Reference Playbook**: Always link back to business context
4. **Use Meaningful IDs**: For filters, questions, and dashboards

### Naming Conventions:

```
{domain}-playbook.md              # Business + technical guide
{domain}-blueprint-{purpose}.md   # Deployable configuration

Examples:
sales-playbook.md
sales-blueprint-daily.md
sales-blueprint-executive.md
logistics-playbook.md
logistics-blueprint-tracking.md
```

## 🎯 Common Tasks

### Task: "Create analytics for [domain]"

1. Create `{domain}-playbook.md` with full business context
2. Design dashboards and test queries
3. Create one or more `{domain}-blueprint-{purpose}.md` files
4. Deploy using the automation skill

### Task: "Update existing dashboard"

1. Find the relevant blueprint file
2. Make changes to SQL or visualization
3. Update the playbook if business logic changed
4. Re-deploy

### Task: "Debug Metabase error"

1. Check `guides/troubleshooting.md`
2. Verify SQL syntax in blueprint
3. Test queries directly in database
4. Check Metabase logs if needed

## 🔗 Related Resources

- **Skill**: `.agent/skills/metabase-automation/`
- **Workflows**: `.agent/workflows/*metabase*.md`
- **Templates**: `.agent/skills/metabase-automation/templates/`

## 💡 Tips for Success

1. **Start Small**: Begin with one domain and expand
2. **Iterate**: Playbooks and blueprints evolve over time
3. **Document Everything**: Future agents will thank you
4. **Test Before Deploy**: Always verify SQL queries work
5. **Use Cross-References**: Link between related documents

Remember: Playbooks are for humans to understand the "what" and "why", while blueprints are for machines to execute the "how".
