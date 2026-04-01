# Create Metabase Blueprint

Create a new Analytics Blueprint using the 2-skill pipeline: Analytics Design (Phase 0-6) → Metabase Automation (Phase 7-10).

## Step 1: Analytics Design (Phase 0-6)

Read `.skills/analytics-design/SKILL.md` first. Execute Phase 0-6:

1. **Phase 0 — Domain Modeling**: Check/create domain in `docs/analytics-handbook/domains/`
2. **Phase 1 — Playbook Creation**: Check/create playbook in `docs/analytics-handbook/playbooks/`
3. **Phase 2 — Guide Creation**: Only if complex concepts need explanation
4. **Phase 3 — Design Brief**: Audience, hero metric, comparison frame, archetype
5. **Phase 4 — Composition Design**: Card roles, narrative flow, filters, sizing
6. **Phase 5 — Visualization Selection**: Standard vocabulary terms (decision tree)
7. **Phase 6 — Enrichment Check**: Comparisons, data completeness, narrative

**Output**: Design Spec saved to `docs/analytics-handbook/designs/<name>.md`

## Step 2: Metabase Automation (Phase 7-10)

Now read `.skills/metabase-automation/SKILL.md` and `METABASE_VIZ_CATALOG.md`. Input: Design Spec from Step 1.

1. **Phase 7 — Translation**: Map standard vocab → Metabase display types, color/size tokens → hex/grid values
2. **Phase 8 — Configuration**: Generate `metabase-viz` JSON with full settings
3. **Phase 9 — Blueprint Assembly**: Write SQL (DuckDB dialect), wire filters, assemble literate config markdown
4. **Phase 10 — Deploy** (optional): Use `/deploy-metabase-blueprint`

**Output**: Blueprint saved to `docs/analytics-handbook/blueprints/<name>.md`

## Fast-Track

Skip Step 1 when domain + playbook already exist AND dashboard ≤5 cards. Collapse Phase 3-6 into one quick design spec.

## Scaffold (alternative)

```bash
node .skills/metabase-automation/scripts/create_blueprint.js <domain> <purpose>
# With tabs:
node .skills/metabase-automation/scripts/create_blueprint.js <domain> <purpose> --tabs
```

## User Arguments

$ARGUMENTS
