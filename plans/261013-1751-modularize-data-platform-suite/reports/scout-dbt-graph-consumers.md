# Scout: dbt graph, consumers, classification, and FJ overlay

Scope: read-only. No dbt run, no warehouse open. `transformation/target/` was blocked by the scout hook, so `manifest.json` was NOT read; per-node config below comes from `dbt_project.yml`, model `config()` blocks, and macros.

## 1. Materialization and naming

- Root default: `+materialized: view`. `staging`: `+schema: staging`, view, `+tags: ["otp"]`. `intermediate`: external parquet, no `+schema`, subfolder tags `int`+`shopee|misa|us_shipment` (no tag for `sapo`, `cogs`, `overhead`, `tags`, `core`). `marts`: `+schema: marts`, external parquet, `+tags: ["olap"]`, `on_schema_change: sync_all_columns`.
- Model-level tags add `mart`/`dim`/`fact` (e.g. `marts/sales/fact_orders.sql` `tags=['mart','fact']`). `transformation/scripts/run_dbt.py` defaults `--select +tag:mart`, so tag loss changes what a default run builds.
- Location macros (all keyed on `this.name`, not folder):
  - `get_rolling_location()` → `$DBT_EXPORT_PATH/rolling/<name>/<name>_<run_started_at>.parquet` (used by 76 models).
  - `get_parquet_location()` → `$DBT_EXPORT_PATH/<name>.parquet`. Zero callers in models.
  - `get_versioned_location()` → `<external_root>/<name>_<batch>.parquet`. Zero callers in models.
- Answer to "does output path depend on folder?": NO for rolling-located models. The parquet path and the serving table name depend only on the file name. Models without `location=` (see §3) use dbt-duckdb's default external path, which I could not verify without the manifest.
- Moving a `.sql` between folders changes: (a) schema (`+schema` exists only on `staging/` and `marts/`; moving into or out of `intermediate/` drops or adds `main_marts`); (b) folder tags (`int`, `shopee`, `misa`, `us_shipment`, `otp`, `olap`), which affect `+tag:mart` selection; (c) per-folder `schema.yml` tests and docs must move with the model. It does not change the parquet path or the relation name.
- No `generate_schema_name` or `generate_alias_name` override exists in `transformation/macros/` (macros: `duckdb__create_table_as`, `add_fk_constraint`, three location macros). Default dbt schema naming applies, so the target schema `main` plus `+schema: marts` gives `main_marts`.
- `duckdb__create_table_as` is overridden to inject contract PK/FK; it is relevant only when a contract is enforced.
- Incremental models (13 in `staging/`, e.g. `src_sapo_v2_orders` with `delete+insert`): moving or renaming resets the relation and causes a full rebuild or lost history. `int_order_snapshots_ranked` (view, tag `history_log`) depends on history stored in the table.
- Verify before any move: `orchestration/assets/dbt.py` `_gc_rolling_parquet` garbage-collects rolling folders after materialization. Folder moves that change model names change which rolling folders get GC'd.

## 2. Consumers and public names

Serving chain: dbt writes `$DBT_EXPORT_PATH/rolling/<name>/*.parquet` → `scripts/provisioning/refresh_rolling.py` (GC keeps N versions, schema-drift check) → `scripts/provisioning/bootstrap_serving_views.py` creates `main.<name>` views (`read_parquet(... rolling/<name>/*.parquet, union_by_name=true)`, picks max filename) and `main_marts.<name>` aliases. Invoked by `orchestration/assets/serving.py` (`build_serving_db`, deps on `sapo_dbt_assets`). Metabase must be stopped during bootstrap (see that file's docstring).

Public = any name below. Renaming or moving the file breaks these consumers.

- **Serving views (76 rolling-located models, all Metabase-facing via `main.<name>` / `main_marts.<name>`)**: dim_action_scenario_registry, dim_branch_location, dim_cash_allocation_policy, dim_channels, dim_channel_targets, dim_customer_addresses, dim_customer_contacts, dim_customer_notes, dim_customers, dim_customer_tags, dim_date, dim_geography, dim_gl_account, dim_order_status, dim_payment_methods, dim_price_lists, dim_products, dim_product_types, dim_promotions, dim_sku_alias, dim_staff, dim_teams, dim_time, fact_account_balance_monthly, fact_cashflow_budget, fact_cash_movement, fact_fulfillments, fact_inventory_balance, fact_inventory_movements, fact_inventory_snapshot, fact_marketing_spend, fact_order_costs, fact_order_economics, fact_order_returns, fact_orders, fact_order_transitions, fact_payments, fact_sales, fact_targets, fact_us_shipment_economics, fact_variant_prices_snapshot, int_misa_sales_lines, int_order_cogs_reconciled, int_order_overhead_allocation, int_order_promo_goods_cost, int_overhead_pool_monthly, int_promo_642_monthly_total, int_return_sku_lines, int_sapo_inventories, int_shopee_order_adjustments, int_shopee_order_fees, int_shopee_order_items, int_us_shipment_line_prices, mart_cashflow_budget_vs_actual, mart_cashflow_forecast, mart_cashflow_reserve_status, mart_cashflow_unmapped_actuals, mart_cash_surplus_allocation, mart_cohort_retention, mart_crm_activity_log, mart_crm_outreach_effort_by_action_weekly, mart_customer_action_queue, mart_customer_sku_action_queue, mart_customer_status_snapshot_monthly, mart_customer_tier, mart_data_quality, mart_deadstock_target_queue, mart_hug_attribution, mart_inventory_health, mart_order_cogs_summary, mart_product_action_queue, mart_product_health, mart_retention_waterfall_monthly, mart_sku_economics_monthly, mart_staff_performance_weekly, stg_marketing_spend.
- **Rill** (`rill/models/src_*.yaml`, `scripts/provisioning/publish_rill_assets.py` allowlist, 11 tables): reads flat `$RILL_EXPORT_ROOT/<name>.parquet` copied from rolling: fact_orders, fact_sales, fact_marketing_spend, fact_targets, dim_channels, dim_branch_location, dim_geography, dim_staff, dim_products, dim_order_status, dim_customers.
- **Evidence** (`evidence/sources/datalake/*.sql`, pages query `main_marts`): dim_channels, dim_customers, dim_gl_account, fact_account_balance_monthly, fact_cash_movement, fact_order_economics, fact_order_returns, fact_orders, fact_targets. Source config: `evidence/sources/datalake/connection.yaml`.
- **Metabase blueprints** (`docs/analytics-handbook/blueprints/`): ~50 distinct names, heaviest fact_orders (883 refs), dim_customers, dim_channels, fact_order_economics, dim_date, dim_branch_location, mart_inventory_health, int_misa_sales_lines, fact_sales, int_shopee_order_fees, mart_product_health, fact_cash_movement, mart_sku_economics_monthly, dim_products, mart_product_action_queue, fact_order_costs, fact_order_returns, fact_account_balance_monthly, dim_product_types, mart_staff_performance_weekly, fact_marketing_spend, dim_promotions, mart_customer_status_snapshot_monthly, mart_customer_action_queue, dim_staff, fact_targets, dim_gl_account, fact_fulfillments, mart_cashflow_budget_vs_actual, fact_us_shipment_economics, fact_payments, int_return_sku_lines, mart_retention_waterfall_monthly, mart_cohort_retention, mart_cash_surplus_allocation, fact_order_transitions, dim_channel_targets, fact_cashflow_budget, dim_cash_allocation_policy, mart_cashflow_reserve_status, mart_cashflow_forecast, dim_payment_methods, plus singles (int_us_shipment_line_prices, int_shopee_order_items, int_product_velocity_trend, dim_geography).
- **CRM** (`crm/src`, DuckDB adapters, serving-DB reads): mart_customer_action_queue (66 refs), fact_orders, mart_customer_sku_action_queue, dim_customers, mart_hug_optin, dim_staff, mart_customer_status_snapshot_monthly, fact_order_economics, fact_fulfillments, mart_data_quality, fact_payments, fact_order_returns, int_order_cogs_reconciled, dim_time, dim_payment_methods, dim_date, dim_channels, mart_customer_tier, fact_us_shipment_economics, fact_sales, fact_order_costs, dim_promotions, dim_products, dim_teams, dim_geography, dim_branch_location, int_order_promo_goods_cost.
- **CRM non-rolling consumed names** (no `get_rolling_location`, so no serving view; verify how crm reads them): mart_hug_optin, dim_customers_base, int_customer_metrics (crm, 20 refs), int_customer_economics, int_customer_entry_attributes, int_customer_sku_supply_tracking, dim_fb_ads, fact_fb_ads_insights_daily, dim_fb_conversations, fact_fb_messages, int_crm_outreach_effort_events. Concern: `crm/` and `detailView/` may read a different DB or parquet path than `main.*`. Not traced further.
- **detailView** (`detailView/app`): fact_orders, fact_fulfillments, dim_customers, fact_order_economics, mart_data_quality, mart_customer_action_queue, mart_customer_status_snapshot_monthly, fact_us_shipment_economics, fact_payments, dim_staff, int_order_cogs_reconciled, fact_sales, fact_order_returns, fact_order_costs, dim_payment_methods, dim_channels, dim_products, dim_promotions, dim_time, dim_date, int_us_shipment_line_prices, dim_teams, dim_geography, dim_branch_location, dim_order_status, mart_sku_economics_monthly.
- **Scripts/ingestion/orchestration/tools**: fact_orders, dim_customers, fact_sales, dim_channels, dim_branch_location, dim_products, dim_order_status, dim_gl_account, mart_hug_optin, mart_customer_action_queue, mart_customer_sku_action_queue, fact_targets, fact_order_economics, fact_marketing_spend, dim_staff, dim_geography (scripts); fact_cash_movement, dim_gl_account, mart_cashflow_reserve_status, fact_orders, dim_channels (ingestion); fact_order_returns, fact_cash_movement, fact_targets (orchestration/assets/reconciliation or kpi); dim_customers_base, int_customer_metrics, dim_customers (tools).
- Shell-side: `transformation/scripts/run_dbt.py` (`--select`, default `+tag:mart`), `transformation/scripts/` only one file. Test harness `scripts/testing/verify_hops_readonly.py` reads `$DBT_DATA_LAKE_PATH/sapo_warehouse.duckdb` and queries `main_marts.fact_orders|fact_sales|dim_customers|dim_products`.

## 3. Leaks: marts/intermediate reading stg_/src_ directly

Confirmed (all in `transformation/models/`):
- `marts/core/dim_customer_addresses.sql` → `stg_sapo_v2_customer_addresses` (rolling-located)
- `marts/core/dim_customer_contacts.sql` → `stg_sapo_v2_customer_contacts`
- `marts/core/dim_customer_notes.sql` → `stg_sapo_v2_customer_notes`
- `marts/core/dim_customer_tags.sql` → `stg_sapo_v2_customer_tags`
- `marts/sales/fact_order_transitions.sql` → `stg_sapo_v2_orders`
- `intermediate/tags/int_order_tags.sql` → `src_sapo_v2_orders` (no location, `intermediate`)

Additional leaks found:
- `marts/core/dim_gl_account.sql` and `marts/finance/fact_account_balance_monthly.sql`, `fact_cash_movement.sql` → `src_misa_account_ledger` (plus `std_misa_account_ledger` used elsewhere)
- `marts/sales/fact_order_costs.sql` → `stg_shopee_order_revenue`, `stg_shopee_order_service_fees`
- `marts/core/dim_sku_alias.sql` (refs `std_variants`, fine) — no leak
- `marts/crm/mart_crm_outreach_effort_by_action_weekly.sql`, `marts/crm/mart_staff_performance_weekly.sql`, `marts/customer/mart_crm_activity_log.sql`, `marts/customer/int_crm_party_tag_flags.sql`, `marts/customer/mart_customer_action_queue.sql`, `marts/customer/mart_customer_sku_action_queue.sql`, `marts/core/intermediate/int_crm_outreach_effort_events.sql`, `marts/core/mart_hug_attribution.sql` → `stg_crm__*`
- `marts/sales/fact_sales.sql`, `marts/sales/fact_orders.sql`, `marts/core/dim_teams.sql` → `stg_teams`, `stg_team_members` (gsheet)
- `marts/core/fact_targets.sql` → `stg_targets`; `marts/sales/fact_marketing_spend.sql` → `stg_marketing_spend`
- `marts/facebook_ads/dim_fb_ads.sql` → `stg_fb_ads`, `stg_fb_campaigns`, `stg_fb_ad_sets`; `marts/facebook_messenger/*` → `stg_fb_*`
- `marts/sales/fact_order_costs.sql`: `'sapo_v2'` appears as a literal value in `AS source_system` (lines 159, 194, 300), not as a filter. No model filters on `'sapo_v2'` in marts/intermediate/monitoring. The `'sapo_v2'` literal appears in 13 `staging/standard/std_*` files only as a value.
- `marts/customer/mart_hug_optin.sql` → `stg_hug_optin_event`; `intermediate/us_shipment/int_us_shipment_line_prices.sql` → `stg_us_shipment_prices`; `intermediate/overhead/int_overhead_pool_monthly.sql` → `stg_overhead_account_classification`
- Also: `intermediate/shopee/*` → `stg_shopee_*`, `intermediate/misa/int_misa_sales_lines` refs std/src; `marts/customer/mart_customer_tier`, `marts/core/*` mostly ref `dim_customers`/`fact_*` (clean).

Mostly-clean marts: `marts/core/intermediate/int_customer_*` use `dim_*`/`fact_*`/`dim_customers_base`/`int_*` only.

## 4. Classification inventory (hardcoded)

Duplicated across models (drift risk):
- **Customer group → customer_type (WHOLESALE / PARTNER / STAFF / KOL / CROSSBORDER)**: `marts/core/dim_customers.sql` (~L215-230, LIKE on code OR name; CROSSBORDER also ORs US-channel order); `marts/sales/fact_orders.sql` (~L111-115, no US clause); `marts/core/intermediate/int_customer_benchmarks.sql` (~L47-52, group only, no `_name` match). Rules differ — CROSSBORDER semantics diverge.
- **Monetary value tier (VALUE_VIP ≥50M or freq≥20 / GOLD ≥20M / SILVER ≥5M)**: `dim_customers.sql` ~L233-237, `int_customer_benchmarks.sql` ~L56-60. Also consumed in `mart_customer_tier.sql` and `mart_customer_action_queue.sql` L82-91 (hardcoded value_group names).
- **Recency status (Active ≤30 / At Risk ≤90 / Churned >90)**: `dim_customers.sql` ~L121-124 (`'Active'`, `'At Risk'`, `'Churned'`). `mart_customer_status_snapshot_monthly.sql` ~L79-81 uses `'ACTIVE'`, `'AT_RISK'` (different casing; label drift).
- **Lifecycle (NEW / ACTIVE / AT_RISK by lifespan+frequency+recency)**: `dim_customers.sql` ~L241-244.
- **Next-purchase signal (OVERDUE ≥1.5×avg gap, DUE_SOON ≥0.8×)**: `dim_customers.sql` ~L279-282; `mart_customer_status_snapshot_monthly.sql` ~L125-126.
- **Promo dependency (PROMO_DEPENDENT >0.7, PROMO_MIXED >0.3)**: `dim_customers.sql` ~L271-274.
- **Geo buckets (GEO_HCMC / GEO_HANOI / provinces list)**: `dim_customers.sql` ~L287+.
- **Customer tier strategic_tier (LIVE_CORE, SECOND_ORDER, MASKED_REPEAT, DORMANT_VALUABLE, LAPSED_VALUABLE, NONBUYER)**: `marts/customer/mart_customer_tier.sql` L37-53 (≤90/≤365 days, `source_contact_quality` real/masked).
- **Entry attributes (first_order_total <300k LOW / <1M MID / <3M HIGH; basket_size ≥2)**: `marts/core/intermediate/int_customer_entry_attributes.sql` L106-114.
- **Benchmark percentile bands (>95 top_5pct, >90 top_decile, >75 top_quartile, >50 above_median)**: `int_customer_benchmarks.sql` ~L176-179; min-group guard n≥30 in same file.
- **Discount reason → discount category (voucher seller / sampling / agency / US / CTKM / staff)**: `marts/sales/fact_orders.sql` L48-62 and `marts/sales/fact_order_costs.sql` L110-133 — same ILIKE list duplicated.
- **Order/product price-channel**: `marts/core/dim_channels.sql` L115-123 channel_format → Online-Ecommerce / Offline / Internal; `dim_channels` L23-43 name-LIKE parent matching.
- **Product matrix (STAR / WORKHORSE / QUESTION / DOG)** and **product lifecycle (NEW <90d / DORMANT >90d / DECLINING / GROWING)**: `marts/core/mart_product_health.sql` L158-176.
- **GL account → cashflow line**: `marts/core/dim_gl_account.sql` L73-86 (LIKE '111%' cash etc.); `fact_cash_movement.sql` L41-43, `mart_cashflow_forecast.sql` L25; `111/112` hardcoded in 3 files.
- **SKU VTS prefix**: `marts/core/dim_sku_alias.sql` L69, L97 (`LIKE 'VTS%'`).
- **Time-of-day buckets**: `marts/core/dim_time.sql` L33-54.
- **Status snapshot (ACTIVE/AT_RISK/OVERDUE/DUE_SOON)**: as above.
- **Tag classification**: `intermediate/tags/int_order_tags.sql` L23-55 uses `ref_tag_categories` (seed) with prefix/contains match on `tag_value`; `monitoring/monitor_uncategorized_tags.sql` checks coverage.
- **Action queues**: `mart_customer_action_queue.sql` L82-91, L190 (`last_contact_result IN ('answered','replied','met')`); same in `mart_customer_sku_action_queue.sql` L200.

Seeds (`transformation/seeds/`): ref_order_sources, ref_brands, ref_misa_channel_codes, ref_branch_locations, ref_gl_accounts, ref_payment_methods, ref_spend_category, ref_tag_categories, seed_sku_regimen_config, seed_sku_alias_manual, seed_channel_targets, seed_cashflow_budget, seed_cash_allocation_policy, seed_action_scenario_registry. `transformation/seeds/properties.yml` declares them. Sync: `scripts/maintenance/sync_seeds.py` (writes to `transformation/seeds/`, uses `DBT_DATA_LAKE_PATH` and a regex allowlist for NOT IN ids). `orchestration/assets/sheets_assets.py` writes `seed_cash_allocation_policy.csv` and runs 02:30 ICT before dbt build at 03:00.

Google-Sheet-sourced stg models (`sources.yml` gsheet_raw): stg_targets, stg_marketing_spend, stg_teams, stg_team_members, stg_us_shipment_prices, stg_overhead_account_classification (holds account→overhead classification values).

## 5. Fine Japan-specific models

- **HUG**: `staging/src_hug_scan.sql`, `staging/src_hug_optin_event.sql` (raw), `staging/stg_hug_scan.sql`, `staging/stg_hug_optin_event.sql` (← src_hug_*), `marts/customer/mart_hug_optin.sql` (← stg_hug_optin_event; no location), `marts/core/mart_hug_attribution.sql` (← dim_customers, fact_order_economics, fact_orders, stg_crm__hug_voucher; rolling). Also `stg_crm__hug_voucher` (crm). Consumers: crm (mart_hug_optin 13 refs), scripts (mart_hug_optin), `orchestration/assets/hug_assets.py`, `scripts/ensure_hug_safety_placeholder.py`. Downstream of these: crm writeback/customer push. Not re-traced.
- **US shipment**: `staging/stg_us_shipment_prices.sql` (gsheet), `intermediate/us_shipment/int_us_shipment_line_prices.sql` (← dim_channels, fact_orders, std_order_items, stg_us_shipment_prices), `marts/sales/fact_us_shipment_economics.sql` (← int_us_shipment_line_prices). Consumers: detailView (fact_us_shipment_economics 18), blueprints (13), CRM (3), `mart_data_quality` (dependency). Also `dim_customers` gift/US-channel logic (see §4) and `dim_customers` `CROSSBORDER` uses US channel.
- **CRM**: `staging/stg_crm__*` (10 models, all tag `crm`/`staging`). Marts: `marts/crm/mart_crm_outreach_effort_by_action_weekly.sql` (← dim_staff, int_crm_outreach_effort_events, stg_crm__task), `marts/crm/mart_staff_performance_weekly.sql` (← dim_staff, fact_orders, stg_crm__activity_log/note/party_tag/task), `marts/customer/mart_crm_activity_log.sql`, `marts/customer/int_crm_party_tag_flags.sql` (← stg_crm__party_tag), `marts/core/intermediate/int_crm_outreach_effort_events.sql`. Customer action queues: `marts/customer/mart_customer_action_queue.sql` (← dim_customers, int_crm_party_tag_flags, mart_customer_tier, seed_action_scenario_registry, stg_crm__last_contact), `marts/customer/mart_customer_sku_action_queue.sql` (← dim_customers, int_customer_sku_supply_tracking, mart_customer_tier, seed_action_scenario_registry, stg_crm__last_contact), `marts/core/mart_product_action_queue.sql` (← mart_product_health, mart_sku_economics_monthly), `marts/core/mart_deadstock_target_queue.sql` (← dim_customers, dim_products, fact_sales, mart_customer_tier, mart_product_health), `marts/customer/dim_action_scenario_registry.sql` (← seed). Consumers: crm (mart_customer_action_queue 105 refs total, sku queue 42), detailView, scripts.
- **Cashflow / budget**: `marts/finance/fact_cashflow_budget.sql` (← seed_cashflow_budget), `dim_cash_allocation_policy.sql` (← seed_cash_allocation_policy), `mart_cashflow_budget_vs_actual.sql` (← fact_cashflow_budget, fact_cash_movement), `mart_cashflow_forecast.sql` (← fact_account_balance_monthly, fact_cashflow_budget), `mart_cashflow_reserve_status.sql` (← fact_cashflow_budget), `mart_cashflow_unmapped_actuals.sql` (← dim_gl_account, fact_cashflow_budget, fact_cash_movement), `mart_cash_surplus_allocation.sql` (← dim_cash_allocation_policy, fact_account_balance_monthly, fact_cashflow_budget, mart_cashflow_reserve_status), `fact_account_balance_monthly.sql` and `fact_cash_movement.sql` (← dim_gl_account, src_misa_account_ledger). Consumers: blueprints (mart_cashflow_budget_vs_actual 14, fact_cashflow_budget 7, mart_cashflow_reserve_status 5, mart_cashflow_forecast 5, dim_cash_allocation_policy 6, mart_cash_surplus_allocation 8), evidence (fact_cash_movement 21, fact_account_balance_monthly 8), ingestion (fact_cash_movement 9, mart_cashflow_reserve_status 5), `sheets_assets.py`, `scripts/budget/`. Note: `scripts/budget/` exists; not inspected.
- **Overhead**: `staging/stg_overhead_account_classification.sql` (gsheet), `intermediate/overhead/int_overhead_pool_monthly.sql` (← std_misa_account_ledger, stg_overhead_account_classification), `intermediate/overhead/int_order_overhead_allocation.sql` (← fact_orders, int_overhead_pool_monthly). Tests: `tests/assert_overhead_accounts_classified.sql`, `assert_overhead_allocation_closure.sql`, `assert_no_promo_in_overhead_costs.sql`. Downstream: `fact_order_economics` (presumably; unverified), blueprints.
- **Approach scripts**: `orchestration/assets/approach_script_generation.py`, `scripts/generate_approach_scripts.py`, `scripts/build_approach_prompts.py`, `scripts/approach_script_*.py`, `scripts/load_approach_scripts.py`. Warehouse refs: fact_orders, dim_customers, fact_sales only (via grep). Not fully traced.
- Customer/CRM marts also depend on `dim_action_scenario_registry` seed; `seed_action_scenario_registry` is `enabled: boolean` typed in dbt_project.yml.

## 6. Tests and comparison tooling

- `transformation/tests/`: 8 singular SQL tests — assert_dim_customers_base_unknown_sentinel_unique, assert_int_customer_benchmarks_rankable_count_sane, assert_no_promo_in_overhead_costs, assert_overhead_accounts_classified, assert_overhead_allocation_closure, assert_promo_account_not_in_keep_pool, assert_shopee_net_settlement_matches_total_paid, assert_shopee_no_platform_service_double_count.
- Schema tests in 20 `schema.yml` / `*.yml` files under `transformation/models/`: accepted_values 57, not_null 49, relationships 38, dbt_utils.unique_combination_of_columns 15, dbt_utils.accepted_range 4, unique 3, dbt_utils.expression_is_true 1. Package: `dbt-labs/dbt_utils` 1.1.1 (`packages.yml`).
- Run: `transformation/scripts/run_dbt.py` (`dbt build --select`, default `+tag:mart`, `--full-refresh`, `--target`, plus a hard timeout whose length I did not verify). Dagster runs `sapo_dbt_assets` (`orchestration/assets/dbt.py`) which regenerates the manifest with `dbt parse` first.
- Docs: `transformation/docs/` (MATERIALIZATION.md, TESTING.md, TAG_HANDLING.md, MODELS.md, DEDUPLICATION.md, BUSINESS_LOGIC.md, ARCHITECTURE_DETAIL.md).
- Comparison/golden tooling: `scripts/testing/verify_hops_readonly.py` (read-only row-count probe on `main_marts.*`, hop 4-6 checks); `scripts/testing/test_olap_queries.py` (queries; references `main_marts.dim_product_category`, which is NOT a model here, so it is stale). `scripts/maintenance/cleanup_and_verify.py` and `check_*.py` at repo root (`check_sapo_*`, `check_parquet_date_range.py`, `check_shopee_orders_history.py`) are row/gap checks, not golden diffs. No snapshot/data-diff framework found in `transformation/` (grep for golden/data-diff/snapshot limited hits only in docs and provisioning scripts).

## 7. Proposed buckets (model → bucket → reason)

Bucket counts from folders: staging 79, marts 89, intermediate 20, monitoring 1 SQL (2 files incl. yml).

| Bucket | Models | Reason |
|---|---|---|
| connector:sapo_v2 | src_sapo_v2_{accounts,customer_groups,customers,fulfillments,inventory_transactions,order_returns,orders,price_lists,products,purchase_orders,stock_adjustments} (11, incremental); stg_sapo_v2_{accounts,customer_addresses,customer_contacts,customer_notes,customers,customer_tags,fulfillments,inventories,order_discount_items,order_items,order_returns,orders,payments,products,variant_prices,variants} (16) | Raw source extraction and light staging per source |
| connector:shopee | src_shopee_order_{adjustments,revenue_items,revenue,service_fees} (4); stg_shopee_order_{adjustments,revenue_items,revenue,service_fees} (4); intermediate/shopee int_shopee_order_{adjustments,fees,items} (3) | Shopee raw + Shopee-only intermediates |
| connector:misa | src_misa_account_ledger, src_misa_sales_lines, stg_misa_sales_lines; intermediate/misa int_misa_sales_lines | MISA accounting source |
| connector:crm | stg_crm__{activity_log,app_user,campaign_target,customer_profile_custom,hug_voucher,last_contact,note,party_insight,party_tag,task} (10) | CRM source; note stg_crm__hug_voucher is also HUG |
| connector:hug | src_hug_scan, src_hug_optin_event, stg_hug_scan, stg_hug_optin_event | HUG raw (FJ) |
| connector:facebook_ads | stg_fb_ads, stg_fb_ad_sets, stg_fb_campaigns; marts dim_fb_ads, fact_fb_ads_insights_daily | FB ads source plus marts (pack candidate) |
| connector:facebook_messenger | stg_fb_conversations, stg_fb_messages; marts dim_fb_conversations, fact_fb_messages | Messenger source |
| connector:gsheet | stg_targets, stg_marketing_spend, stg_teams, stg_team_members, stg_us_shipment_prices, stg_overhead_account_classification | Google-Sheet inputs; overhead/us_shipment/targets classification values live here |
| cdm | staging/standard std_* (14: accounts, customers, fulfillments, inventory_movements, misa_account_ledger, misa_sales_lines, order_discount_items, order_items, order_returns, orders, payments, products, variant_prices, variants) | Canonical layer, consumed by core |
| core:dim | dim_branch_location, dim_channels, dim_channel_targets, dim_customers_base, dim_customers, dim_customer_{addresses,contacts,notes,tags}, dim_date, dim_geography, dim_gl_account, dim_order_status, dim_payment_methods, dim_price_lists, dim_products, dim_product_types, dim_promotions, dim_sku_alias, dim_staff, dim_teams, dim_time | Conformed dims, public |
| core:fact | fact_targets, fact_orders, fact_order_economics, fact_order_costs, fact_order_returns, fact_order_transitions, fact_fulfillments, fact_payments, fact_sales, fact_variant_prices_snapshot, fact_inventory_snapshot, fact_inventory_balance, fact_inventory_movements, fact_marketing_spend (see note) | Core facts, public |
| core:customer-metrics | intermediate/core int_customer_{metrics,economics,benchmarks,entry_attributes,discount_metrics,sku_supply_tracking}, mart_cohort_retention, mart_retention_waterfall_monthly, mart_customer_status_snapshot_monthly, mart_customer_tier | Customer analytics; benchmarks duplicates dim_customers classification (taxonomy extraction) |
| core:product | int_product_{discount_dependency,velocity_trend}, int_sku_gift_profile, mart_product_health, mart_sku_economics_monthly, mart_inventory_health, mart_product_action_queue, mart_deadstock_target_queue, mart_data_quality | Product analytics |
| taxonomy | intermediate/tags/int_order_tags, monitoring/monitor_uncategorized_tags, seeds ref_* and seed_* (14), dim_sku_alias (seed + CASE VTS), dim_action_scenario_registry, dim_cash_allocation_policy (seed), CASE rules currently in dim_customers / fact_orders / fact_order_costs / int_customer_benchmarks / mart_customer_tier / mart_product_health | Classification rules to extract; duplicated customer-group and discount-reason rules |
| pack:finance | marts/finance: fact_account_balance_monthly, fact_cash_movement, mart_cashflow_forecast; fact_cashflow_budget, mart_cashflow_budget_vs_actual, mart_cashflow_reserve_status, mart_cashflow_unmapped_actuals, mart_cash_surplus_allocation, dim_cash_allocation_policy | Finance pack. Caution: cashflow/budget is FJ per brief; decide ownership |
| pack:cogs | intermediate/cogs int_order_cogs_reconciled, int_order_promo_goods_cost, int_promo_642_monthly_total; mart_order_cogs_summary | COGS pack |
| pack:inventory | intermediate/sapo int_sapo_inventories, int_return_sku_lines; fact_inventory_* listed under core:fact above | Inventory pack (move fact_inventory_* here if preferred) |
| pack:marketplace (shopee) | connector:shopee intermediates (above) plus fact_order_costs (shopee legs) | Shopee marketplace pack |
| pack:facebook_ads / messenger | see connector rows | Pack candidates |
| tenant:fj | HUG: mart_hug_optin, mart_hug_attribution; US shipment: int_us_shipment_line_prices, fact_us_shipment_economics; CRM marts: marts/crm/* (2), mart_crm_activity_log, int_crm_party_tag_flags, int_crm_outreach_effort_events, mart_customer_action_queue, mart_customer_sku_action_queue, dim_action_scenario_registry; overhead: int_overhead_pool_monthly, int_order_overhead_allocation; cashflow/budget per brief | Fine Japan overlay. Caution: fact_order_economics and dim_customers depend on US/overhead logic and would import FJ rules into core |
| monitoring | monitor_uncategorized_tags | Taxonomy coverage check |

## Risks

- Manifest and target/ were blocked by the scout hook. Node-level `schema`, `tags`, `config.location`, and `depends_on` were NOT verified against the manifest. Before the plan is finalized, run `dbt ls --resource-type model --output json` or read the manifest (needs approval for `target/`). Check whether `dbt ls` opens the DuckDB file; if unsure, skip.
- Any renaming or moving of the 76 rolling-located models changes `rolling/<name>/` and `main.<name>` views, the rill allowlist, and Metabase cards. Keep names stable.
- Non-rolling consumed names (see §2) have no serving view. Confirm how crm and detailView read them before moving.
- `int_customer_metrics`, `dim_customers_base`, and `int_customer_economics` are consumed by crm/tools but have no location config. Their output path is dbt-duckdb's default external path, not verified.
- Incremental `src_*`/`stg_*` models: relocating them resets state. Keep relation names and schemas.
- Folder tags drive `+tag:mart` selection. Moving a mart out of `marts/` or into `intermediate/` changes what a default run builds.
- Dead macros: `get_parquet_location` and `get_versioned_location` have no callers in models.
- Stale test: `scripts/testing/test_olap_queries.py` queries `main_marts.dim_product_category`, which does not exist.
- Label drift: `dim_customers` ('Active'/'At Risk') vs `mart_customer_status_snapshot_monthly` ('ACTIVE'/'AT_RISK'). Do not normalize without a numbers check.
- CROSSBORDER rule differs between dim_customers (adds US-channel OR), fact_orders, and int_customer_benchmarks.

## Unresolved Questions

- How crm/ and detailView read non-rolling models (serving DB, parquet, or a separate cache)?
- Node-level config from the manifest (blocked by hook; needs approval to read `target/`).
- Whether `scripts/budget/` and `orchestration/assets/hug_assets.py` contain additional warehouse reads (not inspected).

Status: DONE_WITH_CONCERNS
Summary: Mapped folder/macro naming, 76 rolling-located serving models (public surface), consumers across Metabase, rill, evidence, crm, detailView, scripts; confirmed 6 named leaks plus ~20 more marts-to-stg/src refs; inventoried classification CASE rules and duplicates; proposed buckets for all 190 models.
Concerns: target/ manifest blocked by the scout hook, so node config is inferred from source, not verified; crm/detailView read paths for non-rolling models are unconfirmed; classification duplicates have diverging CROSSBORDER and label rules.
