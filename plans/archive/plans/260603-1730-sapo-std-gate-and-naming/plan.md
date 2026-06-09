---
title: "Sapo std gate completion + column naming standardization"
description: "Complete the std_* conformance layer for 6 missing entities; apply P1/P2/P3 renames as prep for v2→v3 migration."
status: complete
priority: P1
effort: 16h
branch: main
tags: [dbt, sapo, migration-prep, naming, std-layer]
created: 2026-06-03
---

# Plan: Sapo std gate + naming standardization

**Purpose:** Make `std_*` a complete conformance boundary (every Sapo entity gated) and standardize column names before they bake into the v3 contract. Does NOT implement the v3 union — that requires Q1–Q5 business answers first.

**Source analysis:** `plans/reports/arch-260603-1730-sapo-v2-v3-migration-gate.md`
**Naming rules:** `docs/architecture/naming-conventions.md`

> **✅ STATUS 2026-06-04 — ALL PHASES COMPLETE & PUSHED.**
> - **P0** std gate (5 new std models, 8 consumers repointed; 0.6 skipped as dead code).
> - **P1** term renames (6): total_spend, discount_type, is_active, order_line_id, vat_amount, ordered_at(fact_sales).
> - **P2** consistency (5): returned_at, last_modified_at, order_count, net_revenue(fact_sales), ordered_at(fact_orders).
> - **P3** minor (5): birth_date, gender, loyalty_points, client_info, postal_code.
> - **P4** rename 22 `src/stg_sapo_*` → `_v2` + source alias `sapo_v2_raw` (D1 middle-ground; physical raw + dlt state untouched).
> Every rename verified: percol pure-rename, fresh Dagster run PASS=389, serving/blueprint/detailView/rill in sync. Marts byte-stable except renamed columns. Remaining for actual v3: answer Q1–Q5, then build `src_sapo_*_v3`/`stg_sapo_*_v3` + the UNION in each `std_*`.

---

## Phases

| # | File | Description | Status | Depends on |
|---|------|-------------|--------|------------|
| 0 | [phase-00-complete-std-gate.md](phase-00-complete-std-gate.md) | Create 6 missing std models, repoint 8 bypassing consumers, add `source_version`, tests, validation harness | done | — |
| 1 | [phase-01-p1-term-renames.md](phase-01-p1-term-renames.md) | Wrong/ambiguous terms: `total_expense→total_spend`, `item_id→order_line_id`, `is_active_status→is_active`, `discount_nature→discount_type`, `tax_amount→vat_amount`, `sol_timestamp→ordered_at` | done | P0 complete |
| 2 | [phase-02-p2-consistency-renames.md](phase-02-p2-consistency-renames.md) | Consistency: `_timestamp→_at` timestamps, `total_orders_count→order_count`, `fact_sales.revenue→net_revenue`, money/ratio rules | done | P1 complete |
| 3 | [phase-03-p3-minor-renames.md](phase-03-p3-minor-renames.md) | Optional minor: `dob→birth_date`, `sex→gender`, `loyalty_point→loyalty_points`, `zip→postal_code`, `client_details→client_info` | done | P2 complete (optional) |
| 4 | [phase-04-rename-v2-files.md](phase-04-rename-v2-files.md) | Rename v2 `src_sapo_*`/`stg_sapo_*` model files → `_v2` suffix (std_* stays unversioned) so v3 adds `*_v3` cleanly. Internal-only. | done | P0 complete; run after P3 |

**P0 blocks all rename phases.** Each rename phase is independently shippable — user can stop after P0, or after P1, etc. The std-internal renames (in std_* models only) are cheap. Published-mart cascade (fact_*, dim_*, Metabase, detailView) is expensive — treat as a coordinated deploy event.

**Phase 4** (v2 file rename) is INTERNAL-only (src/stg model names + refs + 2 scripts; no Metabase/detailView/serving impact). Depends on P0; recommended last so column-rename phases use stable file paths. `std_*` files MUST NOT be renamed (they are the version-agnostic union gate). Suffix `_v2` per `docs/architecture/naming-conventions.md` §7.

**Verification protocol:** Every atomic step ends with a physical checkpoint; the pipeline must be GREEN before the next step. Every step is a single git commit so it is independently revertible. See [`verification-protocol.md`](verification-protocol.md) for exact commands, lock-handling guidance, and rollback actions.

---

## Key dependencies & risks

- **DuckDB single-writer**: always run `dbt build` while Dagster container has exclusive write access. Never run dbt in parallel with Metabase writes.
- **Metabase binder error**: any mart column rename requires (1) stop Metabase, (2) `bootstrap_serving_views.py`, (3) restart Metabase. Skipping causes silent wrong data.
- **detailView baked image**: code changes require `docker compose up -d --build detail_view`. `docker cp` is ephemeral.
- **Validation harness** (T0.6) is reused as the immutability proof for each rename phase. Do NOT merge any phase without passing harness.
- **`order_timestamp` used in 24 blueprint files** — largest blast radius rename in P2.

---

## File ownership (phases must NOT run in parallel)

| Phase | Files owned |
|-------|------------|
| P0 | `transformation/models/staging/standard/std_*.sql` (new + existing), `transformation/models/staging/standard/schema.yml`, 8 consumer SQL files (dim_products, dim_sku_alias, int_sapo_inventories, dim_price_lists, fact_variant_prices_snapshot, fact_order_returns, fact_order_costs, fact_orders) |
| P1 | std models (std_customers, std_order_items, fact_orders, fact_order_costs, fact_sales, dim_products) + serving + blueprints + detailView |
| P2 | fact_orders, fact_sales, int_us_shipment_line_prices, int_customer_metrics, dim_customers, mart_customer_*, 24 blueprint files + detailView |
| P3 | std_customers, dim_customers, dim_customers_base, customer query files |
| P4 | `transformation/models/staging/src_sapo_*.sql` + `stg_sapo_*.sql` (rename →`_v2`), 27 referencing models, `staging/schema.yml`, `scripts/testing/verify_hops_readonly.py`, `scripts/maintenance/cleanup_and_verify.py` |

---

## Success criteria (plan level)

- `dbt build` clean after each phase (no errors, no test failures)
- Validation harness: affected mart row counts + key-column checksums match pre-change snapshot
- `olap.duckdb` serves correct data (bootstrap_serving_views.py runs without binder error)
- Metabase dashboards load without broken queries
- detailView renders order detail correctly

---

## Open questions (block v3 union, NOT these phases)

**Q1** — Does v3 reuse same id/code spaces (order_id, customer_id, product_id, source_id, location_id) as v2?
**Q2** — Will v3 re-export historical periods (backfill) or forward-only from cutover date T?
**Q3** — Can v3 modify v2-era records (late returns, status edits)?
**Q4** — One global cutover timestamp T or phased per-entity?
**Q5** — Does v3 expose every entity v2 has, with identical semantics (VAT basis, status vocab, discount model)?

These five answers gate the actual UNION design in each std model. Phases 0–3 are safe to execute without them.

## Decision log

**D1 — v2 ingestion rename scope: RESOLVED = middle-ground.**
Phase 4 renames the dbt `src_/stg_` model files + 2 scripts + the dbt **source alias** (`sapo_raw` → `sapo_v2_raw` in `sources.yml`) while keeping `external_location` pointed at the physical `sapo_raw/` folder unchanged. No physical folder move, no dlt `dataset_name` change, no dlt state touch. The ~10 `source('sapo_raw', …)` refs in `src_sapo_*_v2` models are updated to `source('sapo_v2_raw', …)`. A checkpoint in Step 4.6 proves `sapo_raw/_dlt_pipeline_state` mtime is unchanged and a fresh ingestion still appends to `sapo_raw/`. Full physical folder rename (Option B) is deferred and requires explicit approval.
