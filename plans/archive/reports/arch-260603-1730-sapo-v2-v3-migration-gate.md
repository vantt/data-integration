# Sapo v2 → v3 migration: where is the gate?

**Question:** v2 freezes, v3 ingests in parallel (all entities, possibly different structure). Find the seam where v3 data merges so downstream marts/dashboards keep history unchanged. Hypothesis: gate at `std_*`.

**Verdict:** Hypothesis is CORRECT in principle — `std_*` is the designed conformance boundary — BUT the std layer is **incomplete**. Several entities bypass std and feed dims/facts directly from `stg_sapo_*`. To make "gate at std" a uniform strategy you must first **complete the std layer** for the bypassing entities.

## Pipeline shape (per entity)

Chain: `raw (dlt) → src_sapo_* (incremental, JSON extract) → stg_sapo_* (view, enrich) → std_* (canonical, source-tagged) → int_/dim_/fact_ → marts → serving snapshots`.

`std_*` is the "GOLD STANDARD" layer: 1 std model ← exactly 1 stg_sapo model; renames to canonical cols, maps statuses, sets `source_system='sapo'`. That is literally a merge gate.

### Entities WITH a std gate (clean) — 6
| std model | reads | consumers |
|---|---|---|
| std_orders | stg_sapo_orders | fact_orders (+4) |
| std_order_items | stg_sapo_order_items | dim_products, fact_orders… (4) |
| std_fulfillments | stg_sapo_fulfillments | fact_orders, fact_fulfillments… (3) |
| std_payments | stg_sapo_payments | fact_payments |
| std_customers | stg_sapo_customers | int_customer_metrics… |
| std_accounts | stg_sapo_accounts | dim_staff… |

### Entities WITHOUT a std gate (bypass: stg_sapo_* → dim/fact directly) — the GAP
| stg_sapo source | consumed directly by | missing std |
|---|---|---|
| stg_sapo_products, stg_sapo_variants | dim_products, dim_sku_alias, int_sapo_inventories | std_products / std_variants |
| stg_sapo_variant_prices | dim_price_lists, fact_variant_prices_snapshot | std_variant_prices |
| stg_sapo_order_returns | fact_order_returns | std_order_returns |
| stg_sapo_order_discount_items | **fact_orders**, fact_order_costs | std_order_discount_items |
| stg_sapo_inventories | int_sapo_inventories | std_inventories |

> Note: `fact_orders` itself reads `stg_sapo_order_discount_items` directly (discount summary) — a v2 leak past the std gate.

## Recommended gate

**Complete the std layer, then union v2+v3 at std.** Per entity:

```
std_<entity> =
    SELECT <canonical cols> FROM stg_sapo_<entity>      -- v2 (existing, frozen)
    UNION ALL
    SELECT <canonical cols> FROM stg_sapo_v3_<entity>   -- v3 (new), mapped to same schema
```
- v3 tree mirrors v2: `sapo_v3_raw` source → `src_sapo_v3_<entity>` (parse v3 JSON) → `stg_sapo_v3_<entity>` → into the std union.
- v2 `src_/stg_` untouched (freeze; incremental just no-ops when raw stops).
- Downstream (int_/dim_/fact_/marts/serving) unchanged — they keep reading `std_`, just see more rows.
- **Prerequisite refactor:** add `std_products, std_variants, std_variant_prices, std_order_returns, std_order_discount_items, std_inventories`; repoint the bypassing dims/facts (incl. fact_orders' discount-items dep) to read the new std models. Without this, those entities have no gate and v3 would have to be unioned scattered across many marts.

Alternative (worse): union per-entity inside each consuming mart. Scatters conformance logic, duplicates mapping, higher drift risk. Prefer the single std gate.

## Critical risks to "history doesn't change" (beyond the union)

1. **Cutover / overlap policy (THE decision).** Guarantee v3 never overwrites v2 rows:
   - Hard date cutover: v2 owns `created_at < T`, v3 owns `>= T` (filter each branch). Simplest; safe if v3 doesn't re-export history (else discard v3 pre-T).
   - OR id anti-join: v3 contributes only ids absent in v2.
   - Encode explicitly in the union. Edge case: v2-era order modified in v3 (late return) → strict v2-immutable misses it → business decision.

2. **Natural-key / surrogate-key conformance (the subtle break).** Marts build surrogate keys via `generate_surrogate_key` on natural keys (customer_id, source_id, location_id, product_id||variant_id, status). If v3 uses different id spaces/formats:
   - OLD rows unchanged (good), but NEW v3 rows resolve to different/"Unknown" dim members → going-forward dashboards fragment; a customer spanning v2+v3 splits into two; channel mapping misses.
   - Mitigation: std/conformance (or ref seeds) must MAP v3 natural keys → canonical v2 key space. Heaviest work; the real continuity risk.

3. **Reference/seed mapping for v3.** Extend `ref_order_sources`, `ref_branch_locations`, `seed_sku_alias`… so v3 source_ids/location_ids/SKUs resolve to the SAME canonical channels/branches/products — else v3 miscategorizes (→ Unknown) and dashboards look different.

4. **SCD/snapshot dims (products, customers).** If v3 restates a shared product/customer's attributes, the dim row changes → grouping by that attribute shifts for ALL periods (incl. history). More sensitive than facts; freeze v2-era attributes or use SCD2.

5. **Discriminator.** Keep `source_system='sapo'` for downstream continuity; add `source_version` ('v2'/'v3') for lineage + to drive the overlap policy.

6. **Validation/acceptance.** Before flipping v3 on (0 rows pre-cutover), prove pre-cutover aggregates (revenue/orders by month) are byte-identical before vs after adding the union. That is the immutability proof.

## Open questions (need business answers) — UNANSWERED as of 2026-06-03

These gate the v3-SPECIFIC design (union mapping, cutover, key conformance). They do NOT block Phase 0 (standardization prep) below.

### Q1 — ID & key-space continuity
**Question:** Does v3 reuse the same id/code spaces as v2 — order_id/order_code, customer_id, product_id/variant_id, source_id (channel), location_id — or issue new ones?
**Why it matters:** Surrogate keys downstream are built from these natural keys. Same space → continuity is automatic. Different space → v3 rows resolve to new/"Unknown" dim members; entities spanning both versions (a customer, a product) split in two.
**Blocks:** Risk #2 (key conformance), all id-based dedup, ref-seed extension scope.
**Options if different:** build a v3→v2 key crosswalk in the std layer or ref seeds (by phone/email for customers, SKU for products, mapping table for channels/branches).

### Q2 — Backfill vs forward-only
**Question:** Will v3 re-export historical periods (backfill), or only emit records from cutover date T forward?
**Why it matters:** Determines overlap handling.
**Blocks:** Cutover policy (Risk #1).
**Options:** forward-only → simple date cutover (`v2: created<T`, `v3: ≥T`). Backfill → must discard v3 pre-T OR id anti-join so v2 history stays authoritative.

### Q3 — Mutation of v2-era records
**Question:** Can v3 modify records that originated in the v2 era (late returns, status edits, refunds on old orders)?
**Why it matters:** Strict "v2 immutable" would drop those updates; "v3 wins" would rewrite history.
**Blocks:** Overlap precedence rule; the immutability guarantee itself.
**Options:** business must pick: freeze v2 history (accept stale late-updates) vs allow v3 to supersede specific late events (and accept history moves for those).

### Q4 — Cutover shape
**Question:** One global cutover timestamp T for all entities, or phased per-entity (e.g., catalog/products migrate before orders)?
**Why it matters:** Per-entity cutover means different T per std model and possible cross-entity referential gaps during transition (v3 order referencing a product only present in v2).
**Blocks:** Sequencing of the union rollout; referential-integrity checks during transition.

### Q5 — Entity coverage & semantics parity
**Question:** Does v3 expose every entity v2 has (orders, items, discount_items, fulfillments, payments, returns, customers, accounts, products, variants, variant_prices, inventories, purchase_orders, stock_adjustments, price_lists, customer_groups), and are the business semantics identical (e.g., are v3 prices still VAT-inclusive? same status vocabulary? same discount model)?
**Why it matters:** Each std union branch must map v3→canonical; any semantic drift (VAT basis, status codes, discount representation) needs explicit handling or it silently corrupts blended metrics.
**Blocks:** Per-entity v3 stg mapping; reuse of existing conformance logic (statuses, VAT).

---

## Phase 0 — Standardization prep (DO NOW, v3-agnostic, zero history change)

Goal: make `std_*` a COMPLETE gate so that when v3 arrives, every Sapo entity merges at exactly one place. This is pure refactor on v2 data — output must be byte-identical, so it's safe to do before any business answer.

**Principle:** new `std_<entity>` = thin conformance over the existing v2 `stg_sapo_<entity>` — keep the SAME column names (pass-through) so consumers only swap `ref()` source, not column refs; add `source_system='sapo'` + `source_version='v2'`. (Canonical column renaming, like the current std_orders does, is a separate later harmonization — don't bundle it here to keep risk zero.)

### T0.1 — Create the 6 missing std models (thin pass-through over v2 stg)
| New model | reads (v2) | grain |
|---|---|---|
| `std_products` | stg_sapo_products | 1/product |
| `std_variants` | stg_sapo_variants | 1/variant (hub: feeds inventories, variant_prices, dims) |
| `std_variant_prices` | stg_sapo_variant_prices | 1/variant×price_list |
| `std_order_returns` | stg_sapo_order_returns | 1/return |
| `std_order_discount_items` | stg_sapo_order_discount_items | 1/discount item |
| `std_inventories` | stg_sapo_inventories | 1/variant×location |

### T0.2 — Repoint every bypassing consumer `stg_sapo_* → std_*`
| Consumer | change |
|---|---|
| dim_products | stg_sapo_products→std_products; stg_sapo_variants→std_variants |
| dim_sku_alias | stg_sapo_variants→std_variants |
| int_sapo_inventories | stg_sapo_variants→std_variants; stg_sapo_inventories→std_inventories |
| dim_price_lists | stg_sapo_variant_prices→std_variant_prices |
| fact_variant_prices_snapshot | stg_sapo_variant_prices→std_variant_prices |
| fact_order_returns | stg_sapo_order_returns→std_order_returns |
| fact_order_costs | stg_sapo_order_discount_items→std_order_discount_items |
| **fact_orders** | stg_sapo_order_discount_items→std_order_discount_items (close the std-gate leak) |

### T0.3 — Add discriminator to ALL std models (existing 6 + new 6)
Add `source_system` (already on some) + `source_version='v2'` columns. Harmless now; becomes the v3 union discriminator + overlap driver later.

### T0.4 — Decide `int_order_tags` (src-level bypass)
`int_order_tags ← src_sapo_orders` directly (reads `$.tags`, no stg/std). Either (a) leave as v2-only for now and add an int_order_tags_v3 later, or (b) route tags through std_orders (expose a tags column) so it inherits the gate. Recommend (b) long-term; note now.

### T0.5 — Tests (schema.yml)
For each new std model: `unique`+`not_null` on PK; `relationships` from consuming marts to the new std. Keep parity with existing std_ test coverage.

### T0.6 — Validation harness (acceptance gate for Phase 0)
Before/after the repoint, prove byte-identical history:
- snapshot current rolling parquet for: dim_products, dim_sku_alias, dim_price_lists, fact_variant_prices_snapshot, fact_order_returns, fact_order_costs, fact_orders, mart_inventory_health.
- after repoint + `dbt build`, assert: same row counts, and matching checksums on key columns (revenue, cogs, discount, refund, price). Any diff = the std pass-through altered data → fix before merge.
- This harness is also reused as the v3 immutability proof (Risk #6).

### T0.7 — Document canonical contracts (docs/)
For each std model, record the exposed column schema = the INTERFACE that v3 `stg_sapo_v3_*` must satisfy later. This turns Phase 0 output into the v3 spec.

**Why Phase 0 is safe & worth doing first:** it only moves the conformance boundary; v2 data flows through unchanged (validated by T0.6). It removes the std-gate gaps so the v3 union later touches exactly the std layer — not 8 scattered marts. None of it depends on Q1–Q5.

### Deliberately NOT in Phase 0 (needs Q1–Q5 first)
- The actual v3 ingestion tree (`sapo_v3_raw` source, `src_sapo_v3_*`, `stg_sapo_v3_*`).
- The UNION branch + cutover/overlap filter in each std model.
- v3→v2 key crosswalk & ref-seed extension.

---

## Naming / terminology audit (do alongside Phase 0 — std becomes the v3 contract)

Reference standards: Kimball (surrogate `_key`, smart date keys), dbt-labs style guide (snake_case, `is_/has_` booleans, `_at` timestamps, no abbreviations), e-commerce/finance domain terms.

### What is already GOOD (keep)
- Surrogate keys: `*_key` everywhere (customer_key, channel_key, product_key, date_key, time_key…). Kimball-correct.
- Booleans: `has_cogs, has_returns, has_platform_fees, is_taxable, is_packsize`.
- Units in name: `weight_grams`, `time_to_complete_hours`. Explicit — excellent.
- Finance terms: `gross_revenue, net_revenue, total_collected, gross_profit, gross_margin_pct, cogs_amount, cod_amount` — standard.

### Inconsistencies (convention drift)
| Theme | Examples | Issue | Recommend |
|---|---|---|---|
| Timestamps | `created_at/shipped_at/paid_at` vs `order_timestamp, sol_timestamp, return_timestamp` vs `last_modified` | mixed `_at` / `_timestamp` / bare | standardize to `_at` (dbt std): `order_timestamp→ordered_at`, `return_timestamp→returned_at`, `sol_timestamp→ordered_at`, `last_modified→last_modified_at` |
| Money | `gross_revenue` (no suffix) vs `cogs_amount/tax_amount/discount_amount` (suffix) vs `shopee_taxes` | loose split | rule: revenue/profit = domain noun (no suffix); line/cost/tax = `_amount`; unify tax naming |
| Ratios | `gross_margin_pct` vs `cancel_rate, discount_rate, max_discount_rate` | `_pct` vs `_rate` | keep `_rate` for true rates, `_pct` for margins — document the rule |
| Counts | `total_orders_count` | redundant total+count | `order_count` |

### Wrong / ambiguous TERMS (P1 — fix before they bake into the v3 contract)
| Current | Problem | Standard term |
|---|---|---|
| `total_expense` (std_customers) | "expense" = cost to business; this is customer SPEND | `total_spend` |
| `item_id` (std_order_items, fact_sales) | "item" ambiguous (product vs line) | `order_line_id` |
| `is_active_status` (dim_products) | malformed boolean | `is_active` |
| `primary_discount_nature` / `discount_nature` | "nature" non-standard | `primary_discount_type` / `discount_type` |
| `tax_amount` / `total_tax_amount` | generic where domain is VAT (8/10%) | `vat_amount` (keep `tax_` only for genuine non-VAT, e.g. US sales tax) |
| `sol_timestamp` | cryptic ("sol"=sales-order-line?) | `ordered_at` |

### Minor (P3 — optional)
`dob→birth_date`, `sex→gender`, `loyalty_point→loyalty_points`, `zip→postal_code`, `order_code→order_number` (Sapo term, optional), `client_details→client_info`, `last_seen_at`/`extracted_at` ok.

### Cost asymmetry (decide scope deliberately)
- **std_ internal renames → CHEAP** (only internal `ref`s; nothing published reads std directly except marts). Do all P1+P2 here in Phase 0 — this is the v3 contract, most important to get right.
- **Published mart/dim renames (fact_orders.net_revenue, dim_customers.*, fact_sales.revenue…) → EXPENSIVE.** Ripples to: Metabase blueprints (`docs/analytics-handbook/blueprints/*`), detailView (`order_mappers.py`, `queries/*.sql`, templates), serving views (rename ⇒ binder error ⇒ stop Metabase + rerun bootstrap_serving_views.py). Requires coordinated migration + the T0.6 validation harness.

### Recommended approach
1. Write a 1-page naming-convention doc (the rules above) → `docs/architecture/`.
2. Apply P1+P2 at the **std contract** during Phase 0 (cheap, high leverage — v3 inherits clean names).
3. Schedule published-mart renames as a separate coordinated pass (marts → serving rebuild → Metabase blueprints → detailView), gated by validation harness. P3 optional.
4. `fact_sales.revenue` → `net_revenue` to match fact_orders (consistency; part of the published pass).
