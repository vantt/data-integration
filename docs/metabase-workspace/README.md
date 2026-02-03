# Metabase Workspace

Welcome to the Metabase Workspace - your centralized hub for analytics documentation, blueprints, and deployment guides.

## 📂 Structure Overview

```
metabase-workspace/
├── {domain}-playbook.md         # Business context + technical guide
├── {domain}-blueprint-{purpose}.md  # Deployable Metabase configurations
└── guides/                      # How-to documentation
```

## 🎯 Quick Start

### For Business Users

1. Start with the playbook for your domain (e.g., `sales-playbook.md`)
2. Understand the KPIs, metrics, and dashboard designs
3. Review the business context and use cases

### For Developers

1. Read the playbook to understand requirements
2. Use the corresponding blueprint files for deployment
3. Check `guides/` for technical documentation

### For Agents/Automation

1. Scaffold blueprint: `node .agent/skills/metabase-automation/scripts/create_blueprint.js [domain] [purpose]`
2. Parse blueprint files directly using the Metabase Automation skill
3. Deploy using: `node .agent/skills/metabase-automation/scripts/deploy_from_markdown.js [blueprint-file]`

## 📚 Available Domains

### Sales Analytics

- **Playbook**: [sales-playbook.md](sales-playbook.md) - Complete guide to sales metrics and dashboards
- **Blueprints**:
  - [sales-blueprint-daily.md](sales-blueprint-daily.md) - Daily operations dashboard
  - [sales-blueprint-overview.md](sales-blueprint-overview.md) - Sales overview dashboard

### Coming Soon

- **Financial Analytics**: P&L, cash flow, and financial KPIs
- **Customer Analytics**: Segmentation, LTV, and behavior analysis
- **Logistics Analytics**: Track delivery performance and operations
- **Product Analytics**:

## 🔧 Working with This Workspace

### Understanding the Naming Convention

```
{domain}-playbook.md            # The "what", "why" and "how (logic)"
{domain}-blueprint-{purpose}.md # The "recipe" (deployable config)
```

**Example**:

- `sales-playbook.md` - Explains sales metrics, KPIs, business rules
- `sales-blueprint-daily.md` - Metabase configuration for daily dashboard
- `sales-blueprint-executive.md` - Metabase configuration for C-level

### Creating New Analytics

1. **Start with a Playbook**
   - Define business requirements
   - Document KPIs and metrics
   - Design dashboard layouts
   - Test SQL queries

2. **Create Blueprint(s)**
   - Use scaffold script: `node .agent/skills/metabase-automation/scripts/create_blueprint.js [domain] [purpose]`
   - Transform playbook into deployable format
   - Follow the blueprint template syntax
   - One blueprint per dashboard/purpose

3. **Deploy to Metabase**
   ```bash
   # Using the automation skill
   node .agent/skills/metabase-automation/scripts/deploy_from_markdown.js [blueprint]
   ```

### Cross-References

Playbooks and blueprints are linked:

- Playbooks reference blueprint sections: `[sales-blueprint-daily.md#revenue-section]`
- Blueprints link back to playbooks: `[sales-playbook.md#daily-sales-metrics]`

## 🛠️ Tools and Skills

### Metabase Automation Skill

Located at `.agent/skills/metabase-automation/`

- Deploy blueprints programmatically
- Manage collections, models, and dashboards
- Support for variables and filters

### Available Workflows

- `/create_metabase_blueprint` - Generate new blueprint from template
- `/deploy_metabase_blueprint` - Deploy blueprint to Metabase
- `/manage_metabase_resources` - CRUD operations on Metabase

## 📋 Best Practices

1. **One Playbook, Multiple Blueprints**
   - Keep business logic in playbooks
   - Create focused blueprints for specific use cases

2. **Version Control**
   - Track changes in Git
   - Use meaningful commit messages
   - Tag stable blueprint versions

3. **Documentation**
   - Always update playbooks when requirements change
   - Keep SQL queries documented and tested
   - Include performance notes

4. **Naming Consistency**
   - Use lowercase with hyphens
   - Be descriptive but concise
   - Follow the `{domain}-{type}-{purpose}` pattern

## 🔄 Migration Status

We've recently reorganized from the old structure:

- ✅ Consolidated requirements into playbooks
- ✅ Renamed blueprints with clear naming convention
- ✅ Simplified folder structure
- 🔄 Creating additional domain playbooks

## 📞 Support

- For Metabase issues: Check `guides/troubleshooting.md`
- For skill problems: See `.agent/skills/metabase-automation/SKILL.md`
- For questions: Ask in the main chat with context

---

_Last updated: February 2026_
