# Sapo Product Catalog — dbt Expansion Plan

> **Created:** 2026-05-28 16:54 ICT
> **Trigger:** Full 558-product Sapo catalog sync confirmed in parquet. MISA coverage will jump from 11.4% → 90.0% after rebuild.
> **Research:** [Schema + Opportunities Report](../reports/research-260528-1654-sapo-product-schema-opportunities.md)
> **Previous context:** [MISA-Sapo SKU Alignment Diagnostic](../reports/research-260528-1608-misa-sapo-sku-alignment.md)

---

## Overview

558 Sapo products (682 variants, 679 unique SKUs) are now in the data lake. The existing `dim_products` was reverse-engineered from order_items (105 SKUs). This plan expands dbt to exploit the full catalog: fix MISA join, add inventory, bundle, and pricing dimensions.

**Blocking dependency:** Parquet ingestion fix must be complete (agent af4df875570e4dfe8) before any phase can run. The parquet is already readable; the fix ensures ongoing pipeline correctness.

---

## Phases

| Phase | File | Status | Priority | Effort |
|-------|------|--------|----------|--------|
| [Phase 1: Foundational fix](phase-01-foundational-fix.md) | dim_products + dim_product_variants + seed_sku_alias | DONE | P0 | Low |
| [Phase 2: Pricing intelligence](phase-02-pricing-intel.md) | dim_price_lists + fact_variant_prices_snapshot | DONE | P2 | Medium |
| [Phase 3: Inventory views](phase-03-inventory-views.md) | fact_inventory_snapshot + mart_inventory_health | DONE | P3 | Medium |
| [Phase 4: Bundle/composite tracking](phase-04-bundle-components.md) | dim_bundle_components | DROPPED | P4 | — |
| Phase 5: Brand/category enhancement | Augment dim_products with brand_id, category_id | Covered in Phase 1 | P5 | Low |

---

## Key Dependencies

- **Sapo product batch sync** must produce valid parquet (not jsonl.gz) — agent af4df… fixing
- **MISA naming convention** validated: 90.0% direct match confirmed via DuckDB query
- **dim_products rebuild** (Phase 1) is prerequisite for ALL downstream phases
- **mart_sku_economics_monthly** auto-improves after Phase 1 (no model changes needed — just rebuild)
- **fact_inventory_snapshot** (Phase 3) requires new Dagster asset for daily product re-ingestion
- **Do NOT run dbt build** while DuckDB lock held by another agent

---

## Expected Impact After Phase 1

| Metric | Before | After |
|--------|--------|-------|
| dim_products SKU count | 105 | ~679 |
| MISA direct match | 23 (11.4%) | 181 (90.0%) |
| mart COGS coverage (rows) | 32.1% | ~85% (estimated) |
| mart COGS coverage (revenue-weighted) | 18.7% | ~80-85% |
| Inventory data available | None | 3 locations × 682 variants |
| Bundle decomposition | None | 77 bundles, 14 component SKUs |

---

## Files To Create (all phases)

```
transformation/
  seeds/
    seed_sku_alias.csv                          # Phase 1 — legacy → MISA code mapping
  models/
    staging/
      src_sapo_product_variants.sql             # Phase 1 — unnest variants from src_sapo_products
      src_sapo_product_inventories.sql          # Phase 3 — unnest inventories from variants
      src_sapo_variant_prices.sql               # Phase 2 — unnest price lists from variants
      src_sapo_bundle_components.sql            # Phase 4 — unnest composite_items
    marts/
      core/
        dim_products.sql                        # Phase 1 — MODIFY (union order_items + catalog)
        dim_product_variants.sql                # Phase 1 — NEW
        dim_sku_alias.sql                       # Phase 1 — NEW
      products/                                 # Phase 2-4 — NEW directory
        dim_price_lists.sql                     # Phase 2
        fact_variant_prices_snapshot.sql        # Phase 2
        fact_inventory_snapshot.sql             # Phase 3
        mart_inventory_health.sql               # Phase 3
        dim_bundle_components.sql               # Phase 4
```

---

## Files NOT to Touch

- `ingestion/src/sapo/products.py` — being fixed by other agent
- `ingestion/run_products_batch.py` — being fixed by other agent
- `transformation/models/staging/src_sapo_products.sql` — being fixed by other agent
- `transformation/models/marts/sales/mart_sku_economics_monthly.sql` — auto-improves after Phase 1 rebuild, no SQL changes needed
