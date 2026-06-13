# Deploy Evidence Page

Generate and deploy an Evidence.dev dashboard page from a playbook or design spec.

## Context

Read `.skills/evidence-automation/SKILL.md` for full syntax reference, SQL rules, and component mapping.

## Steps

1. **Read the playbook/design spec** — identify metrics, time windows, viz types, sections
2. **Check existing pages** — `ls evidence/pages/` to avoid duplicating or pick up an existing stub
3. **Generate page files** in `evidence/pages/<dashboard-slug>/`:
   - `index.md` — primary tab (most important metrics)
   - Additional `.md` files per logical section/tab
   - Each page must have frontmatter `title:` and nav links at top
4. **SQL rules** (mandatory):
   - Schema-qualify all tables: `main_marts.fact_orders`, etc.
   - Use `scope_sales AND is_active_order` filters from `fact_orders`
   - Combine WoW KPIs into one query per time window
5. **Rebuild the container**:
   ```bash
   docker compose restart evidence
   ```
6. **Verify at** http://evidence.lan.fwg.vn (or http://localhost:3006)
7. **Check logs if build fails**:
   ```bash
   docker compose logs evidence
   ```

## Dashboard URL Pattern

- Main page: `/evidence/pages/<dashboard-slug>/index.md` → `http://evidence.lan.fwg.vn/<dashboard-slug>/`
- Sub-pages: `/evidence/pages/<dashboard-slug>/<tab>.md` → `http://evidence.lan.fwg.vn/<dashboard-slug>/<tab>/`

## User Arguments

Playbook or design spec path: $ARGUMENTS
