# scripts/checks — refactor and boundary checks

Checks that keep the module architecture ([docs/architecture/modules.md](../../docs/architecture/modules.md))
true in code. The shadow gate ([scripts/shadow/README.md](../shadow/README.md)) runs all of them;
`run-all.sh` runs the pre-commit subset in one command (below).

| File | Kind | Purpose |
|---|---|---|
| `run-all.sh` | pre-commit | dbt parse + `check_boundaries.py` + `dagster definitions validate` + pytest, in one command |
| `check_boundaries.py` | rule check | Module dependency matrix, core reading tenant seeds, cross-component imports, duplicate seeds, hard-coded URLs in connectors and packs |
| `check_taxonomy_inventory.py`, `taxonomy_inventory.yaml` | warn-only check + data | Classification `CASE` blocks and expressions still in dbt SQL match the inventory (hash per block); a new `CASE` assigning a known taxonomy column is reported |
| `model_buckets.yaml` | data | Bucket (module) of every dbt model; `pack_connectors` for packs |
| `boundary_allowlist.yaml` | data | Known violations, each with a reason and an exit |
| `golden_snapshot.py`, `public_models.yaml` | data equality | Public tables identical before/after a change |
| `dbt_inventory.py` | dbt contract | Relations, config, refs, tests, compiled SQL unchanged. With `--allow-code-change` a repointed ref is accepted only while the removed dependency stays an ancestor (INFO shows the new route) |
| `dagster_inventory.py` | orchestration contract | Assets, checks, job selections, schedules, sensors, SLA unchanged |
| `instigator_state.py` | deploy | Live schedule/sensor on/off state before vs after a deploy |
| `guard_not_prod.py` | safety | Refuses paths inside the prod checkout |

## run-all.sh (mandatory before every commit)

```bash
scripts/checks/run-all.sh                 # checks the worktree that contains the script
scripts/checks/run-all.sh <worktree>      # or another worktree; the prod checkout is refused
```

| Step | Where | Fails when |
|---|---|---|
| 1. `dbt parse --no-partial-parse` | shadow container | the dbt project does not parse (writes `transformation/target/manifest.json` of the checked worktree) |
| 2. `check_boundaries.py --manifest <that manifest>` | host `python3` (needs `crm/`, `detailView/`) | a new boundary violation or a stale allowlist entry (below) |
| 3. `dagster definitions validate -f orchestration/definitions.py` | shadow container | the Dagster code location does not load |
| 4. `pytest ingestion/tests orchestration scripts/tests` | shadow container | a test fails twice (one re-run, printed as `FLAKY` when it passes) |

The container steps go through `scripts/shadow/run-shadow.sh` (prod image, `--network none`, no
secrets, no `SOURCES__*` variables) on an **empty** scratch lake created under `$SHADOW_ROOT`
and deleted on exit, so they never read customer data. Only `$SHADOW_ROOT/deps` is needed
(`dbt_packages`, DuckDB extensions, pinned pytest), built by `scripts/shadow/prepare-shadow.sh`;
set `SHADOW_ROOT` to use another root. All steps run; the script ends with `RUN-ALL: PASS` (exit 0)
or `RUN-ALL: FAIL` (exit 1). It does not prove data equality: a change that moves models or
edits SQL still needs `scripts/shadow/gate.sh M|S` before deploy.

## check_taxonomy_inventory.py

```bash
python3 scripts/checks/check_taxonomy_inventory.py          # compare code with the inventory (exit 0 always)
python3 scripts/checks/check_taxonomy_inventory.py --list   # print file:line, column and sha256 of every CASE block that assigns a taxonomy column
```

The spec is [transformation/docs/TAXONOMY.md](../../transformation/docs/TAXONOMY.md); this check keeps it from
drifting while the classification rules are still SQL. The machine-readable inventory is
`taxonomy_inventory.yaml` (chosen over parsing the markdown: the hashes stay exact and the test
can load it). Each domain lists its `columns` and its `blocks`:

| Block `kind` | Found by | Meaning of `sha256` |
|---|---|---|
| `case` | `CASE ... END [AS] alias` scan of `transformation/models` and `transformation/macros`; comments and string literals are skipped | sha256 of the block with comments removed and whitespace collapsed |
| `expr` | normalized `snippet` must occur in the normalized file | sha256 of the same snippet |

`columns` entries are a column name (any file) or `file.sql:column` (only that file, for generic names such as `status`).

| Output | Meaning | What to do |
|---|---|---|
| `WARN changed` | An inventoried block no longer matches its hash: the rule was edited | Update `TAXONOMY.md`, then the `line`/`sha256`/`snippet` in the inventory. A change of numbers belongs to an S gate |
| `WARN new` | A `CASE ... END AS <taxonomy column>` that is not inventoried | Add it to the inventory and `TAXONOMY.md`, or reuse the existing rule |
| `WARN missing` | An inventoried file is gone | Update the inventory (file moved or deleted) |
| `INFO moved` | Block unchanged, line number differs | Optional: refresh `line` |

It only warns: classification rules may change on purpose, but never silently. The shadow gate prints the
result in step 3c. Tests: `scripts/tests/test_check_taxonomy_inventory.py`.

## check_boundaries.py

```bash
# from a full checkout on the host (crm/ and detailView/ must exist); needs a manifest from `dbt parse`
python3 scripts/checks/check_boundaries.py --manifest <path/to/manifest.json>
```

| Rule | Fails when |
|---|---|
| `py-import` | `crm/` or `detailView/` imports `orchestration`, `ingestion` or `transformation`; `ingestion/` imports `orchestration` |
| `py-scan` | one of those trees is missing (prevents a silent pass inside a container) |
| `orch-import` | a file under `orchestration/connectors/<c>/` imports `orchestration.packs.*`, or a file under `orchestration/packs/<p>/` imports another pack (`orchestration.packs.<q>`, q ≠ p). The kernel loads packs from `modules.yaml`; `__tests__` and the loaders are not scanned |
| `dbt-bucket` | a dbt model (enabled or disabled) has no entry in `model_buckets.yaml` |
| `dbt-path` | a model's file is not under `models/<module folder of its bucket>/` |
| `dbt-ref` | a model depends on a model its bucket may not read (matrix below). `core` → `pack:*` and `core` → `tenant:*` are never allowed by the matrix: such a hook exists only as an allowlist entry |
| `dbt-source` | a model outside `connector:*` / `tenant:*` reads a dbt source |
| `dbt-seed` | a model of `core`, `cdm` or a connector (or of another tenant) depends on a tenant seed, i.e. a seed under `transformation/seeds/tenants/<t>/`. Packs, `monitoring` and `tenant:<t>` itself may read it (pack logic, tenant data). Taxonomy and other seeds are not concerned |
| `seed-duplicate` | two CSVs under `transformation/seeds/` share a basename (dbt parse would fail and `data_platform` would not start) |
| `connector-url` | an `http(s)://` URL (any line) or a domain name inside a string literal (e.g. `"fwg.mysapogo.com"`; module paths and file names do not match) appears under `orchestration/connectors/**` |
| `pack-url` | the same under `orchestration/packs/**`. Tenant values go to `orchestration/tenants/<tenant>/config.py`, read with `orchestration.tenants.setting(name)` |

```mermaid
flowchart LR
    CONN["connector:&lt;x&gt;"] --> CDM[cdm]
    CDM --> CORE[core]
    CDM --> PACK["pack:&lt;p&gt;"]
    CORE --> PACK
    CONN -. "only pack_connectors" .-> PACK
    CONN & CDM & CORE & PACK --> TEN["tenant:&lt;t&gt;"]
```

| Bucket of the model | May depend on |
|---|---|
| `connector:<x>` | `connector:<x>`, seeds, sources |
| `cdm` | `connector:*`, `cdm`, seeds |
| `core` | `cdm`, `core`, seeds |
| `pack:<p>` | `cdm`, `core`, `pack:<p>`, connectors listed in `pack_connectors[<p>]` |
| `tenant:<t>`, `monitoring` | anything |

Seeds: every bucket may read `seeds/taxonomy/` and other shared seeds; seeds under
`seeds/tenants/<t>/` only as the `dbt-seed` rule allows.

Tests (each rule fails on a planted violation; `dbt-seed` also end to end through `main()`):
`scripts/tests/test_check_boundaries.py`.

### Adding a model

1. Put the model in the folder of its module.
2. Add `<model_name>: <bucket>` to `model_buckets.yaml`.
3. Run the check. A violation means the dependency crosses a module boundary: route it through
   the canonical layer (`std_*`), move the model to the right bucket, or, only when neither is
   possible yet, add an allowlist entry with a concrete reason and exit.

### Allowlist

- The check fails on any violation that is not listed **and** on any listed entry that no
  longer occurs, so fixed debt must be removed from the file in the same commit.
- `--write-allowlist` regenerates the file from the current violations and keeps existing
  reasons; new entries get `TODO: reason and exit plan` and must be edited before commit.
- Current entries (36, all generated from the manifest and the orchestration imports): 16 `dbt-ref` (pack hooks core → pack, the tenant hook `mart_data_quality` → `fact_us_shipment_economics`, declared pack → pack and pack → connector edges), 3 `dbt-seed` (core reads the Fine Japan seeds `seed_channel_targets` in `dim_channel_targets`, `seed_sku_regimen_config` in `int_customer_sku_supply_tracking`, `seed_sku_alias_manual` in `dim_sku_alias`; exit: an empty seed with the same columns in core, overridden by the tenant, with `pack_ref` after Đợt 1), 12 `dbt-source` (CRM export read by packs `crm`/`hug`, the overhead sheet read by `finance`) and 5 `orch-import` (four connector jobs and `sales_playbook` importing the crm pack). Summary and exits: `docs/architecture/modules.md` §3 and §10. No `dbt-path` entry: every model sits in its module folder.
