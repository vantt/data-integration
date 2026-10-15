# Pack packages

One package per product pack under `orchestration/packs/<id>/`. A pack is reusable product logic (CRM, HUG, finance, sales playbook) that runs on the data the connectors bring in; the business (tenant) only supplies data and configuration. The kernel (`definitions.py`) knows packs only through the ids listed under `packs:` in [`../config/modules.yaml`](../config/modules.yaml). Architecture: [docs/architecture/modules.md §8](../../docs/architecture/modules.md).

Enabled today (all seven dbt pack folders): `crm`, `hug`, `finance`, `sales_playbook`, `marketplace`, `facebook_ads`, `facebook_messenger`. The dbt side of each pack lives in `transformation/models/packs/<id>/`. The same list is the dbt variable `enabled_packs` (below).

## Contract

Plain Python exporting lists — no base class, no registry object.

| File | Export | Consumed by |
|---|---|---|
| `<id>/__init__.py` | `ASSETS` (list of asset definitions) | `definitions.py` (Definitions assets) |
| `<id>/__init__.py` | `NIGHTLY_ASSETS` (subset of `ASSETS`) | `pipeline_batch_nightly_job` and `pipeline_batch_fullrefresh_job` |
| `<id>/jobs.py` | `JOBS`, `SCHEDULES`, `SENSORS` | `definitions.py` |

A pack with no Dagster code of its own (`hug`, `finance`, `marketplace`, `facebook_ads`, `facebook_messenger`: their models run inside the kernel's dbt assets, or are disabled) exports empty lists, so the enabled packs match the dbt side. `orchestration.packs` exposes `enabled_ids()`, `load_enabled()` and `load_enabled_jobs()` (same loader as connectors: `orchestration/module_registry.py`).

| Pack | Assets | Job (schedule) | README |
|---|---|---|---|
| `crm` | `crm_cache_refresh` (group `reporting_layer`), 11 `crm_*_export` (group `crm_writeback`), `crm_backup`, `crm_restore_verify` (group `ops_maintenance`) | `crm_backup_job` (`crm_backup_schedule`, 02:00) | [crm/README.md](crm/README.md) |
| `sales_playbook` | `approach_script_autogen` (group `approach_script_autogen`) | — | [sales_playbook/README.md](sales_playbook/README.md) |
| `hug` | — | — | [hug/README.md](hug/README.md) |
| `finance` | — | — | [finance/README.md](finance/README.md) |
| `marketplace` | — | — | [marketplace/README.md](marketplace/README.md) |
| `facebook_ads` | — (dbt models disabled in their own config) | — | [facebook_ads/README.md](facebook_ads/README.md) |
| `facebook_messenger` | — (dbt models disabled in their own config) | — | [facebook_messenger/README.md](facebook_messenger/README.md) |

## Rules

- Names are the identity of live state: asset keys, groups, job, schedule and sensor names, cron and default status do not change when code moves.
- Packs import from the kernel (`orchestration.assets.*`, `orchestration.job_support`, `orchestration.tenants.setting`), never from a connector.
- A pack does not import another pack and a connector does not import a pack (`check_boundaries.py`, rule `orch-import`). Known couplings are allowlisted per file: the four connector jobs that select `crm_cache_refresh`, and `sales_playbook` running after `crm_cache_refresh`. Exit after Đợt 1.
- No hard-coded `http(s)://` URL or domain in this tree (rule `pack-url`). Endpoints are tenant settings: `orchestration.tenants.setting("<NAME>")` reads the env var `<NAME>` or `orchestration/tenants/<tenant>/config.py`, and fails with `TenantConfigError` when neither has it.

## Turning a pack off

Design: [docs/architecture/modules.md §8.1](../../docs/architecture/modules.md#81-bậttắt-pack-công-tắc-pack).

`packs:` in `config/modules.yaml` is the source; `transformation/dbt_project.yml` keeps a checked copy because dbt cannot read this file:

| Where | What |
|---|---|
| `config/modules.yaml` `packs:` | Packs of this deployment. Dagster loads only these packages |
| `dbt_project.yml` `vars.enabled_packs` | Same ids, same order. `pack_enabled()` / `pack_ref()` read it in models |
| `dbt_project.yml` `models: sapo_warehouse: packs: <id>: +enabled` | One line per pack folder, with the same list as `var()` default (dbt renders this file before its own `vars:`). Disables the whole folder |
| `transformation/macros/packs/pack_enabled.sql` `pack_ids()` | Every pack folder, enabled or not |

`python3 scripts/checks/check_boundaries.py --manifest <manifest>` (rule `module-config`, also in `scripts/checks/run-all.sh` and the shadow gate) fails when these disagree and prints the block to paste.

Steps, once core reads the pack only through `pack_ref`:

1. Remove the id from `packs:` in `config/modules.yaml`.
2. Run `check_boundaries.py` and paste the printed block into `dbt_project.yml` (`vars.enabled_packs` and every `+enabled` default).
3. Run `scripts/checks/run-all.sh`; a pack that another enabled pack depends on fails `dbt parse` (hug → finance, finance → marketplace, sales_playbook → crm).
4. Restart the Dagster code server.

**Not possible yet in production:** dbt already builds with every pack off (shadow gate step 6b, `docs/architecture/modules.md` §8.1), but core still reads three Fine Japan tenant seeds and the connector jobs still select the crm pack's `crm_cache_refresh`. Plan `plans/261014-2225-pack-mechanism/` removes these (phases 5–6).
