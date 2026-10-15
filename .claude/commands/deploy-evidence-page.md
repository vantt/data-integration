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
5. **Product reports are not hand-written**: a report in `analytics/catalog/catalog.yml` with
   `engine: evidence` is a spec (`analytics/specs/`), rendered with `python3 -m analytics render evidence`.
   Hand-written pages (this command) are legacy pages in `evidence/pages/` (area `legacy`).
6. **Request a build** once the change is live (a container restart does not rebuild):
   launch `report_site_build_job` in Dagster, or
   ```bash
   docker exec evidence bash /app/scripts/build-areas.sh --once
   ```
7. **Verify** at https://evidence.lan.fwg.vn (login with a `legacy` account; no host port) and
   `cat app_data/data_lake/report_build/status.json`
8. **Check logs if the build fails**:
   ```bash
   docker compose logs --tail 50 evidence
   ```

## Dashboard URL Pattern

- Main page: `/evidence/pages/<dashboard-slug>/index.md` → `http://evidence.lan.fwg.vn/<dashboard-slug>/`
- Sub-pages: `/evidence/pages/<dashboard-slug>/<tab>.md` → `http://evidence.lan.fwg.vn/<dashboard-slug>/<tab>/`

## User Arguments

Playbook or design spec path: $ARGUMENTS
