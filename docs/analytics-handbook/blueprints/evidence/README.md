# Evidence Blueprints

Deployable page content for Evidence.dev dashboards, following the same
domain → semantic → playbook → blueprint chain as `blueprints/metabase/`
and `blueprints/rill/`.

## Directory Structure

```
blueprints/evidence/
├── README.md                 # This file
└── finance_cashflow.md       # Finance Cashflow — Evidence port of metabase blueprint
```

## Why Evidence Blueprints Differ From Metabase Ones

Metabase blueprints are a Markdown DSL (`metabase-viz` / `metabase-pos` JSON
blocks) parsed by `deploy_from_markdown.js` and translated into Metabase API
calls. Evidence has no such translator — an Evidence page **is** Markdown +
SQL + Svelte components, deployed by copying the file into `evidence/pages/`
and restarting the container.

So an Evidence blueprint is the **literal page body**, plus a short header
documenting prerequisites and source lineage. Deploy = copy body verbatim
into `evidence/pages/<slug>/index.md` (or transcribe with only mart-column
renames if the mart changed since the blueprint was written).

## Blueprint Format

```markdown
---
primary_scope: ...
uses_concepts: [...]
last_modified: YYYY-MM-DD
---

# <Dashboard> Blueprint (Evidence)

## Deploy Notes
- Source `.sql` files needed in `evidence/sources/datalake/`
- Prerequisites (marts, serving views)
- Known deviations from the Metabase version (chart types Evidence lacks)

## Page Body

<the actual evidence/pages/<slug>/index.md content, verbatim>
```

## Deployment

1. Add/verify source `.sql` files in `evidence/sources/datalake/` for every mart table referenced.
2. Copy the blueprint's "Page Body" section into `evidence/pages/<slug>/index.md`.
3. Add a link from `evidence/pages/index.md`.
4. `docker compose restart evidence` (rebuild: cp → sources → build → preview).
5. Verify at `http://evidence.lan.fwg.vn/<slug>` (or `localhost:3006/<slug>`).

## Limitations vs Metabase (apply to every Evidence blueprint)

See `.skills/evidence-automation/SKILL.md#limitations-vs-metabase` — no
cross-filtering, no native waterfall/combo/pivot components, no live query
(build-time snapshot only). Blueprints must call out where a Metabase chart
type was approximated (e.g. waterfall → DataTable + BarChart) instead of
silently dropping the view.

## Cross-Reference

| Evidence Blueprint | Playbook | Metabase Blueprint |
|---|---|---|
| finance_cashflow | [playbook](../../playbooks/finance_cashflow.md) | [finance_cashflow.md](../metabase/finance_cashflow.md) |
