# Create Metabase Blueprint

Create a new Analytics Blueprint using the 2-skill pipeline: Analytics Design (Phase 0-6) → Metabase Automation (Phase 7-10).

## Step 1: Analytics Design (Phase 0-6)

Execute Phase 0-6 by reading `.skills/analytics-design/SKILL.md`. This produces the Design Spec with archetype, viz selections, composition, and narrative structure.

**Output**: Design Spec at `docs/analytics-handbook/designs/<name>.md`

## Step 2: Metabase Automation (Phase 7-10)

Now read `.skills/metabase-automation/SKILL.md` and `METABASE_VIZ_CATALOG.md`. Input: Design Spec from Step 1.

1. **Phase 7 — Translation**: Map standard vocab → Metabase display types, color/size tokens → hex/grid values
2. **Phase 8 — Configuration**: Generate `metabase-viz` JSON with full settings
3. **Phase 9 — Blueprint Assembly**: Write SQL (DuckDB dialect), wire filters, assemble literate config markdown
4. **Phase 10 — Deploy** (optional): Use `/deploy-metabase-blueprint`

**Output**: Blueprint saved to `docs/analytics-handbook/blueprints/<name>.md`

## Scaffold (alternative)

```bash
node .skills/metabase-automation/scripts/create_blueprint.js <domain> <purpose>
# With tabs:
node .skills/metabase-automation/scripts/create_blueprint.js <domain> <purpose> --tabs
```

## User Arguments

$ARGUMENTS
