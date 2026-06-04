# Coordination — Order-P&L design-doc column-name sync (2026-06-04)

## Context

P1 (R4/R5) + P2 (R8) renames already live in schema/code; order-pl design docs lagged → synced in commit `997fc5c` ("refactor(sapo): propagate v2 column renames to docs, rill metrics, detailView prototype & tests", 2026-06-04). Doc-text only, no logic touched.

**Pre-sync task status:** Both target files were already clean when this task ran (git status showed no uncommitted changes). Grep confirmed 0 occurrences of old tokens — the renames were already applied by `997fc5c`. No further edits were needed or made.

## Changes made (in commit 997fc5c)

- `docs/architecture/order-pl/discount-classification.md`: `discount_nature → discount_type` (36 insertions/deletions, all column-name token replacements, 0 old tokens remaining).
- `docs/architecture/order-pl/order-pl-schema-design.md`: `discount_nature → discount_type`; `return_timestamp → returned_at`; `total_tax_amount → vat_amount` (6 insertions/deletions, 0 old tokens remaining).

## Why

Old names outdated vs actual schema (P1 R4/R5 discount_nature→discount_type, P2 R8 return_timestamp→returned_at + total_tax_amount→vat_amount implemented in std/fact layers).

## Before / after token counts

| Token | Before 997fc5c | After (current HEAD) |
|---|---|---|
| `discount_nature` | present in both files | 0 |
| `return_timestamp` | present in order-pl-schema-design.md | 0 |
| `total_tax_amount` | present in order-pl-schema-design.md | 0 |

## ACTION REQUIRED (collaborators / concurrent session)

`git pull --rebase origin main` BEFORE editing these docs further; use the NEW column names: `discount_type`, `returned_at`, `vat_amount`.

## Same batch — heads-up (coordination notes)

Also in this batch (same session, 2026-06-04):

**Rill metrics fix (commit 997fc5c):**
- `rill/metrics/orders_core_metrics.yaml` — repointed broken metric from `tax_amount` → `vat_amount`
- `rill/metrics/sales_items_core_metrics.yaml` — repointed broken metric from `revenue` → `net_revenue`
- **Gotcha:** clear Rill cache after the metrics change or stale query errors will persist

**2 legacy deploy scripts deleted (commit d10d488):**
- `scripts/deploy_orders_dashboard.js` (143 lines) — orphaned, superseded by blueprint-driven flow
- `scripts/deploy_daily_sales_dashboard.js` (261 lines) — orphaned + already broken on removed `gmv` column

Both scripts are superseded by `deploy_from_markdown.js` + `docs/analytics-handbook/blueprints/`.

## Unresolved questions

None.
