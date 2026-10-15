# Shadow environment and refactor gate

Design and full explanation (what each check proves, how it works, limits): [docs/operations/refactor-safety-harness.md](../../docs/operations/refactor-safety-harness.md). This README is the command reference.

Prove that a refactor changes no number, no public table name, no dbt relation/config and no
Dagster wiring, without touching production. Production keeps running daily; it changes only
through the deploy runbook in [docs/operations/deployment.md](../../docs/operations/deployment.md#refactor-deploys-shadow-verified).

## Layout

```mermaid
flowchart LR
    subgraph PROD["Prod (read only for this tooling)"]
        BK["app_data/backups/&lt;ts&gt;/<br/>(taken under duckdb_lock)"]
        PK["transformation/dbt_packages"]
        PC["container data_platform<br/>~/.duckdb extensions"]
    end
    subgraph SH["/home/vantt/app/fg-dw-shadow (mode 0700)"]
        BASE["lake-base<br/>warehouse+exports from backup N-1<br/>raw folders from backup N"]
        A["lake-A / lake-A2 / lake-AF<br/>baseline builds"]
        B["lake-B / lake-E / lake-BF<br/>branch builds (deleted after each gate)"]
        INV["inventory/<br/>dbt-*.json, dagster-*.json, instigators-*.json"]
    end
    subgraph TL["~/.cache/fg-dw-tools (SHADOW_DEPS, mode 0700, no data, long-lived)"]
        DEPS["deps/<br/>dbt_packages, home/.duckdb, home/pylib (pytest), wheels"]
    end
    subgraph WT["Worktrees"]
        BL["fg-dw-baseline (main, detached)"]
        BR["branch worktree<br/>(e.g. fg-dw-pack, feat/pack-mechanism)"]
    end
    BK --> BASE
    PK --> DEPS
    PC --> DEPS
    BASE --> A & B
    BL -->|build-lake.sh| A
    BR -->|build-lake.sh| B
```

| Script | Purpose |
|---|---|
| `prepare-shadow.sh <backup_new> <backup_prev>` | Build `lake-base` from two backups, then run `prepare-deps.sh`. |
| `prepare-deps.sh` | Build the offline tools (dbt_packages, DuckDB extensions, pinned pytest) in `$SHADOW_DEPS` (default `~/.cache/fg-dw-tools/deps`). They hold no data and live outside the shadow root, so `cleanup.sh --all` keeps them and `scripts/checks/run-all.sh` works between refactor waves. Re-run after the prod image or `dbt_packages` change. |
| `clone-lake.sh <name> [--empty-rolling]` | Copy `lake-base` and delete rolling parquet files (or the whole `rolling/` tree) so every rolling model must be rebuilt. |
| `run-shadow.sh <code_dir> <lake_dir> <cmd...>` | Run a command in a one-off container from the prod image: `--network none`, current uid, env allowlist, code mounted per subdirectory exactly like `docker-compose.yml`. Refuses any path under the prod checkout. |
| `build-lake.sh <code_dir> <lake> [dbt args]` | Production build sequence: `ensure_dbt_directories.py`, `dbt parse`, `dbt build`, `refresh_rolling.py`. Saves `manifest.json`, `run_results.json`, `build_start` to `<lake>/_shadow_meta/`. |
| `build-profile.sh <code_dir> '<dbt vars>' [lake]` | Build a lake (default `lake-P`, rolling tree emptied) with a non-default dbt profile, e.g. packs off (`'{enabled_packs: []}'`); print the `run_results` summary, or the parse/compile error when dbt built nothing, and the full golden compare with lake-A for information. Exit code = dbt build. Deletes the lake unless `KEEP=1`. Used by gate step 6b. |
| `pytest-shadow.sh <code_dir> <lake> [args]` | pytest in the shadow container (pytest is not in the prod image). |
| `gate.sh <M\|S> [--allow-new] [--allow-code-change]` | The refactor gate (below). |
| `move_models.py --manifest M --buckets <patterns> [--dry-run]` | Move dbt models to `models/<module>/<layer>/` from `scripts/checks/model_buckets.yaml`, splitting properties YAML by text blocks (comments kept) and moving connector sources. |
| `cleanup.sh <lake>... \| --all` | Delete shadow lakes. They hold customer PII; delete them after use and `--all` when the plan closes. |

Checks used by the gate live in `scripts/checks/`:

| Check | What it proves |
|---|---|
| `golden_snapshot.py` | Every public table (`public_models.yaml`: 75 rolling models + 8 non-rolling relations read by CRM/tools) has identical rows, schema, per-column and row-level fingerprints; stale outputs (parquet older than the build, node not `success`) fail. `keyed-diff` shows which keys differ. |
| `dbt_inventory.py` | Relation, schema, alias, full resolved config, refs, SQL checksum and attached tests of every model/seed are unchanged; file paths and `fqn` may change. `compiled-diff` compares the SQL dbt executed per model (whitespace-normalized). |
| `dagster_inventory.py` | Asset keys/groups, asset checks, job selections resolved to dbt unique_ids, schedules (cron, timezone, default status), sensors and resolved SLA are unchanged. |
| `instigator_state.py` | Live on/off state of schedules/sensors on the prod webserver, before vs after a deploy. |
| `check_boundaries.py` | Module dependency matrix, cross-component imports, duplicate seeds, hard-coded URLs in connectors (see `scripts/checks/README.md`). |
| `check_taxonomy_inventory.py` | Classification `CASE` blocks and expressions still in dbt SQL match `taxonomy_inventory.yaml`; warns on a changed hash or a new `CASE` assigning a taxonomy column (see `scripts/checks/README.md`). |
| `guard_not_prod.py` | Refuses paths inside `/home/vantt/app/fg-dataware-house`. |

## One-time setup

```bash
cd /home/vantt/app/fg-dataware-house
git worktree add /home/vantt/app/<branch-worktree> -b <branch> main   # e.g. fg-dw-pack, feat/pack-mechanism
git worktree add --detach /home/vantt/app/fg-dw-baseline main

cd /home/vantt/app/<branch-worktree>
scripts/shadow/prepare-shadow.sh 20261013-010341 20261012-060506   # pick two backups with no deploy between them
scripts/shadow/clone-lake.sh lake-A
scripts/shadow/build-lake.sh /home/vantt/app/fg-dw-baseline lake-A
R=/home/vantt/app/fg-dw-shadow; M=/app/var/data_lake; mkdir -p $R/inventory
scripts/shadow/run-shadow.sh $PWD $R python scripts/checks/golden_snapshot.py init \
  --manifest $M/lake-A/_shadow_meta/manifest.json --out scripts/checks/public_models.yaml   # keeps existing volatile_columns
scripts/shadow/run-shadow.sh $PWD $R python scripts/checks/golden_snapshot.py capture \
  --lake $M/lake-A --models scripts/checks/public_models.yaml --out $M/lake-A/_shadow_meta/golden.json
scripts/shadow/run-shadow.sh $PWD $R python scripts/checks/dbt_inventory.py export \
  --manifest $M/lake-A/_shadow_meta/manifest.json --out $M/inventory/dbt-main.json
# run while the branch's orchestration/ still equals main
scripts/shadow/run-shadow.sh $PWD $R python scripts/checks/dagster_inventory.py export \
  --manifest $M/lake-A/_shadow_meta/manifest.json --out $M/inventory/dagster-main.json
```

`public_models.yaml` `volatile_columns` lists build-timestamp columns (`loaded_at`,
`*_generated_at`, `metric_calculated_at`, ...). They were found by building the same code on
the same data twice (lake-A vs lake-A2): only these columns differed. Re-run that check if a
new table appears.

## The gate

```bash
# run from the branch worktree: BRANCH_DIR defaults to the worktree containing gate.sh
scripts/shadow/gate.sh M     # phases that only move files (1, 2, 5, 6)
scripts/shadow/gate.sh S     # phases that rewrite SQL (3, 4)
BRANCH_DIR=/home/vantt/app/fg-dw-pack scripts/shadow/gate.sh M --allow-new   # explicit branch, new nodes accepted
```

| Step | M | S |
|---|---|---|
| Build branch on fresh `lake-B` (rolling parquet cleared) | ✓ | ✓ |
| Every `labels_mapped` test passes on lake-B (`run_results.json`; the test is warn level in dbt so a new label does not red the nightly, but the gate requires `pass`) | ✓ | ✓ |
| Golden lake-A vs lake-B | ✓ | ✓ |
| dbt inventory diff | ✓ | ✓ |
| Compiled SQL diff (what dbt executed, per model) | ✓ | ✓ |
| Module boundaries (`check_boundaries.py`, host python) | ✓ | ✓ |
| Taxonomy inventory (`check_taxonomy_inventory.py`, host python, warn only: prints `WARN`, never fails) | ✓ | ✓ |
| Dagster inventory diff (incl. job → dbt unique_ids) | ✓ | ✓ |
| dbt subset run through Dagster (`marts/fact_order_returns`, the `_fact_order_returns` job selection) | ✓ | ✓ |
| pytest `ingestion/tests orchestration scripts/tests` | ✓ | ✓ |
| Empty-rolling lake build + golden (catches directory pre-creation bugs) | ✓ | ✓ |
| Bare-core profile: `build-profile.sh` with every pack off (`'{enabled_packs: [], tenant: ""}'`, lake-P); fails only when the build fails, prints the differences with lake-A for review (below) | ✓ | ✓ |
| `--full-refresh` on baseline (lake-AF) and branch (lake-BF) + golden | | ✓ |

The gate first checks that lake-A was built today (ICT) and rebuilds it from the baseline worktree otherwise, because models compute date-relative values. A full S gate takes about 2–3 minutes (dbt build ≈ 20 s per lake). Branch lakes are deleted at
the end. `--allow-new` accepts added nodes/assets and grown job selections (printed as INFO);
`--allow-code-change` accepts SQL checksum changes in the dbt inventory while data equality is
still enforced by the golden snapshot.

## Bare-core profile

Gate step 6b builds the branch with every pack turned off
([docs/architecture/modules.md §8.1](../../docs/architecture/modules.md)) and prints the golden
compare with lake-A. Only the build result decides the step; the printed differences are
reviewed by hand against this list. A table outside it must be explained before the phase is
accepted.

Expected differences (`{enabled_packs: [], tenant: ""}`, Fine Japan data, 15/10/2026 after the classification rule seeds; 157 models and seeds built, 390 tests pass, 5 warn; the engine selftest models are disabled in every profile):

| Table | Expected difference | Why |
|---|---|---|
| 30 pack tables (`fact_order_economics`, `mart_sku_economics_monthly`, `mart_crm_*`, `mart_customer_*_action_queue`, `mart_cashflow_*`, `int_shopee_order_*`, ...) | absent (`only in A`, capture errors `not rebuilt`) | pack folders disabled |
| `int_customer_economics`, `mart_hug_optin`, `int_crm_outreach_effort_events` | captured from stale lake-base files, never rebuilt | pack tables (finance, hug, crm) |
| `dim_customers` | the 10 columns read from finance NULL | `pack_ref('finance', 'int_customer_economics')`, no COALESCE when off |
| `mart_customer_tier` | `lifetime_contribution_margin` NULL | passes through `dim_customers` |
| `dim_staff` | `crm_user_id` NULL | `pack_ref('crm', 'stg_crm__app_user')` |
| `dim_sku_alias` | fewer rows (174 → 120): only `AUTO_PACKSIZE` aliases left | no automatic VTS → VCS alias (`INNER JOIN` on MISA codes of finance) and no manual alias (`tenant_ref('seed_sku_alias_manual')` reads the empty default) |
| `dim_products` | `misa_join_key`, `misa_qty_multiplier` | reads `dim_sku_alias` |
| `dim_channel_targets` | 108 → 1 row (one all-NULL row) | `tenant_ref('seed_channel_targets')` reads the empty default; dbt-duckdb writes an empty `external` model as a parquet file with one all-NULL row to keep the schema (the warehouse view filters it, golden and serving read the file) |
| `int_customer_sku_supply_tracking` | 6 815 → 0 rows | `tenant_ref('seed_sku_regimen_config')` reads the empty default |
| `mart_data_quality` | `total_orders` 0, `cogs_rate_pct`, `platform_fees_rate_pct` NULL | `pack_ref('finance', 'fact_order_economics')` |
| `mart_product_health` | `realized_margin_pct`, `margin_outlier` NULL, `has_margin_data` false, `health_class` NULL for SKUs with sales | margin columns through `pack_ref('finance', 'mart_sku_economics_monthly')` |
| `mart_product_action_queue` | `health_class`, `has_margin_data`, `realized_margin_pct` | reads `mart_product_health` |
| `mart_deadstock_target_queue` | fewer rows (249 → 208) and their values | selects SKUs by `mart_product_health.health_class` (DOG/QUESTION) |

Also expected (not public, so not in the compare): the 5 `lbl_<domain>` models build with every
label `UNMAPPED` (no tenant, empty `taxonomy_label__default`) and their 5 `labels_mapped` tests
`warn` (`status: {... 'warn': 5}`).

Row counts that must stay equal to lake-A (velocity is core): `int_product_velocity_trend`,
`mart_product_health`, `mart_product_action_queue`, `mart_inventory_health`.

## Facts established while building this (2026-10-13)

- dbt build had 633 nodes on 2026-10-13. On 2026-10-15 (after the pack mechanism) it had 718 nodes (179 models: 76 external, 16 incremental, 14 tables, 73 views; 22 seeds; 517 tests) plus 3 exposures, and runs in ≈ 23 s on the shadow lake; baseline result `PASS=717 WARN=1 NO-OP=3 TOTAL=721`. With the three classification rule seeds (same day) it has 727 nodes (25 seeds, 523 tests; the 4 engine selftest models are disabled): `PASS=726 WARN=1 NO-OP=3 TOTAL=730` (the warning is `assert_overhead_accounts_classified`, which also warns in prod).
- `config.location` in the manifest is the unrendered string `{{ get_rolling_location() }}`; rolling models are detected by that string plus `materialized == 'external'` (`stg_marketing_spend` is a view with a stray `location` and writes nothing).
- External models without a location write `<external_root>/<name>.parquet`; the warehouse view embeds an absolute path, so the golden reads the parquet file relative to the lake.
- `orchestration/ops/__tests__/test_ingestion_health_retry.py::test_concurrent_writes_no_lock_error` is flaky (SQLite lock timing, about 1 in 4 full-suite runs, on baseline too). The gate re-runs pytest once after a failure and prints `FLAKY` when the re-run passes; a test that fails twice fails the gate.
- dagster-dbt passes a subset selection to dbt as the model `fqn` from the manifest loaded by the code server (e.g. `--select sapo_warehouse.marts.sales.fact_order_returns`), so a folder move changes the selection string; the code server must load a manifest parsed from the new layout (the container start command does).
- Compiled SQL is deterministic: lake-A vs lake-A2 manifests give 0 differences over 162 models.
- `dagster schedule list -f orchestration/definitions.py` reports all instigators as STOPPED while the webserver runs all 17 schedules and 9 sensors; use `instigator_state.py`.

## Safety rules

- Never pass the prod checkout or `app_data/` to these scripts; the guard refuses it.
- Shadow containers never get `.env.docker`, `app_data/secrets` or network access.
- `lake-base` comes from backups only, never from the live lake.
- Delete branch lakes after each gate (the gate does it) and the whole shadow root when the plan closes (`cleanup.sh --all`).
