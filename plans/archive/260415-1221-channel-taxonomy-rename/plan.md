# Channel Taxonomy Rename Migration

**Branch:** `refactor/channel-taxonomy-rename`
**Created:** 2026-04-15 12:21 Asia/Saigon
**Scope:** Single atomic PR, no backward compat
**Source of truth:** `docs/context/channel-classification.md`

## Naming Decisions (Final)

| Tier | Column | Values |
|------|--------|--------|
| 1 | `channel_category` (unchanged) | `Online-Ecommerce` / `Offline` / `Internal` |
| 2 | **`channel_format`** (renamed from `platform_group`) | `Marketplace` / `Social` / `Web` / `Retail` / `B2B` / `Direct` / `System` / `CrossBorder Fulfillment` / `Other` |
| 3 | `platform` (unchanged) | Shopee / Lazada / TikTok / ... / System / US / Other |
| 4 | `channel_name` (**kept — not renamed to `storefront`**) | 1:1 with Sapo `order_source.source_name` |

**Rationale for keeping `channel_name`:** consistent `channel_*` prefix across tiers; `storefront` is industry term for physical retail outlet and misleads for marketplace shops; rename adds churn with no semantic gain. `storefront` may be used as conceptual label in docs only.

**Tier 1 value format:** `Online-Ecommerce` (hyphen, no space, no parens) — clean SQL filters, no semantic overlap with tier-2 values.

**Telesale/CS classification:** `channel_category='Offline'` + `channel_format='Direct'` (reclassified from prior `System`). `is_sales_channel = true`.

## Value Mapping (Seed → dim_channels)

| OLD `platform_group` | Source example | NEW `channel_format` | NEW `channel_category` |
|----------------------|----------------|----------------------|------------------------|
| `Ecom` | Shopee, Lazada, Tiki, Grab | `Marketplace` | `Online-Ecommerce` |
| `Social` | Facebook, Zalo | `Social` | `Online-Ecommerce` |
| `Web` | WebOrder, Web | `Web` | `Online-Ecommerce` |
| `Retail` | Pos | `Retail` | `Offline` |
| `B2B` | Đại Lý, Chợ sỉ | `B2B` | `Offline` |
| `System` (Telesale, CS) | Telesale, CS | `Direct` | `Offline` |
| `System` (Test, Gift, NV) | Test SP, Quà Tặng, Ưu đãi NV | `System` | `Internal` |
| `CrossBorder` | US | `CrossBorder Fulfillment` | `Internal` |
| `Other` | Other, Gosumo, POPS | `Other` | `Internal` *(non-sales)* |

`is_sales_channel = channel_format NOT IN ('System', 'CrossBorder Fulfillment', 'Other')`

## Phases

- **P1 — Seed + dbt core** (Task #2): seed CSV, dim_channels.sql, fact_*, std_orders, schema.yml. Single commit.
- **P2 — dbt verify** (Task #3): `dbt seed` + `dbt build` green; 3 distinct values in `channel_category`, 9 in `channel_format`; `is_sales_channel` correct.
- **P3 — Rill** (Task #4): orders_enriched, sales_items_enriched, marketing_spend_enriched (+ `channel_group` → `marketing_spend_bucket` rename to avoid semantic collision); 3 metric YAMLs. `rill build` green.
- **P4 — Docs** (Task #5): SoT + all cascading docs (24 files scanned for `platform_group`, 28 for `channel_category`). Fix bug in `channel_classification_implementation_prompt.md` (wrong is_sales_channel formula).
- **P5 — Metabase** (Task #6): scan cards/dashboards; update field refs + filter values.
- **P6 — Verify + report** (Task #7): grep acceptance + write migration report.

## Acceptance Criteria

1. `dbt build` green
2. `SELECT DISTINCT channel_format FROM dim_channels` → 9 values
3. `SELECT DISTINCT channel_category FROM dim_channels` → `Online-Ecommerce`, `Offline`, `Internal` (+ `Other` for Unknown row — to verify)
4. `rill build` green
5. `grep -r "platform_group" transformation/ rill/ docs/` → 0 matches in code (historical notes in git log acceptable)
6. `grep -r "'Ecommerce'" transformation/ rill/` → 0 matches (excluding `Online-Ecommerce`)
7. `is_sales_channel = false` for `System`, `CrossBorder Fulfillment`, `Other`
8. Marketing spend derived `channel_group` renamed to `marketing_spend_bucket`
9. Metabase dashboards load without broken field refs

## Commits (planned)

1. `refactor(taxonomy): rename platform_group→channel_format, Ecommerce→Online-Ecommerce (seed + dbt)`
2. `refactor(taxonomy): propagate channel_format to Rill layer; rename marketing_spend channel_group→marketing_spend_bucket`
3. `docs(taxonomy): sync handbook/dictionaries/skills to channel_format + Online-Ecommerce`
4. `refactor(taxonomy): update Metabase dashboards to channel_format`

## Open Items Resolved

- ✅ Tier 1 value → `Online-Ecommerce`
- ✅ Tier 4 column → keep `channel_name` (storefront is conceptual label only)
- ✅ Telesale/CS → `Offline`/`Direct`, `is_sales_channel=true`
- ✅ Metabase in same PR

## Post-migration Cleanup (2026-04-16)

- ✅ Rill: `channel_format` already in orders + sales_items metrics; added `channel_format` + `platform` to `marketing_spend_core_metrics.yaml`
- ✅ Metabase H2 DB: no action needed — blueprints are SoT, already redeployed
- ✅ Blueprint display labels: standardized "Ecommerce"/"Ecom" → "Online-Ecom" across 4 blueprints (marketing_weekly_tracker, ceo_weekly_pulse, ceo_monthly_scorecard, marketing_monthly_analysis)
- ✅ `deploy_from_markdown.js --dry-run`: implemented (was documented but no-op)
- ✅ Serving views runbook: added Binder Error section to `docs/operations/troubleshooting.md` with full column-rename procedure

**Status: COMPLETE — archivable**
