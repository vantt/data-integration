# std Layer & Source-Versioning Conventions

Rules for working with the Sapo (and future multi-version) source layer in `transformation/`. Established during the P0 std-gate completion (2026-06-03) and the Sapo v2→v3 migration prep. Follow these so every entity is handled consistently — for v2 today and v3 later.

> Companion docs: [`canonical-layer.md`](canonical-layer.md) (what the canonical layer does and how: views, column tests, boundary checks, verification), [`naming-conventions.md`](naming-conventions.md) (column/model names), the migration plan `plans/260603-1730-sapo-std-gate-and-naming/` (`verification-protocol.md` for the exact checks), and `transformation/AGENTS.md` (dbt-layer rules).

## Layer model

```
raw (dlt) → src_<source>_<entity>_v<N> → stg_<source>_<entity>_v<N> → std_<entity> → int_/dim_/fact_ → marts → serving
                    (version-specific, source structure)              (conformed, version-agnostic CONTRACT)
```

## Rules

### R1 — The std gate (mandatory)
Every source entity that feeds a `dim_`, `fact_`, or `int_` model MUST flow through a `std_<entity>` conformance model. Downstream models read `std_*`, **never** `stg_<source>_*` directly. (Upstream `stg → stg` chains are fine; the gate applies to dim/fact/int consumers.)

### R2 — std model = faithful pass-through (no renames in v2)
A `std_<entity>` is a thin `view` over its `stg_<source>_<entity>` source: select ALL columns the stg outputs — **never drop or rename a column** — plus `'sapo_v2' AS source_system`. Column renaming/standardization is a SEPARATE effort (see the P1+ rename phases), not done inside the v2 pass-through. **No `source_version` column** — version is embedded in `source_system`.

### R3 — Versioning suffix
The source **version is a `_v<N>` suffix** on src/stg models (`src_sapo_orders_v2`, `stg_sapo_orders_v2`; later `_v3`). The `std_<entity>` model is **version-agnostic — never carries a suffix**; it UNIONs the versions and is the stable contract every downstream model reads. (See `naming-conventions.md` §7.)

*Current state (reviewed 2026-10-14):* the existing v2 models carry the version inside the source identifier instead (`src_sapo_v2_<entity>`, `stg_sapo_v2_<entity>` in `models/connectors/sapo_v2/staging/`, matching `source_system = 'sapo_v2'` of ADR-014). They were not renamed: relation names are a public contract. Decide the naming of v3 models before adding them.

### R4 — std contract = the v3 interface
Each `std_<entity>` exposes a fixed column set = the **interface** that a future `stg_<source>_v3_<entity>` must satisfy. Document the column list in a header comment (`-- STD CONTRACT v2 … interface for v3 …`). When adding v3, map v3's structure to the SAME columns; `source_system` discriminates (`'sapo_v2'`/`'sapo_v3'`).

### R5 — Don't wrap dead code
If a `stg_*` model has zero consumers (grep `ref('stg_…')` returns nothing), do NOT create a std for it — that violates YAGNI. Flag it as dead code for cleanup instead. (Example: `stg_sapo_inventories` is unused; inventory flows via `std_variants.inventories_json`.)

### R6 — Verify every change physically (no exceptions)
Any change to a std model or a repointed consumer must pass, in order:
1. `dbt parse` clean.
2. A **fresh** Dagster realtime run `RUN_SUCCESS` with `tests: … ERROR=0 FAIL=0` (started AFTER the edit).
3. **Checksum gate**: affected mart parquet byte-identical to baseline — use `plans/260603-1730-sapo-std-gate-and-naming/snapshots/checksum.py`. A pass-through must not change any mart output.
**Create the std model FIRST, then repoint consumers** (a mid-edit auto-run is then safe — consumers still ref stg). Each step = one git commit (revertible).

### R7 — Never move physical raw / dlt state
To version the raw layer, rename only the **dbt source alias** in the connector's `_sources.yml` (`models/connectors/sapo_v2/staging/_sources.yml`; `sapo_raw` → `sapo_v2_raw`) while keeping `external_location` pointed at the physical `…/sapo_raw/{name}/…` folder. **Do NOT** move/rename the physical folder, change dlt `dataset_name`, or touch `sapo_raw/_dlt_pipeline_state`. The raw holds irreplaceable history (Sapo truncates `history_log`; 2021–2025 exists only as the ingested parquet/Delta) — a state reset risks unrecoverable re-ingestion. v3 gets its OWN new raw dataset (`sapo_v3_raw`), no collision.

### R8 — Scheduling reality (this daemon)
`dagster schedule stop/start -f <file>` via CLI is **ineffective** here (ephemeral code-location origin ≠ daemon's), so you cannot pause the pipeline that way and `schedule list` shows a misleading `[STOPPED]`. The realtime job keeps firing every 3 min. To truly pause, use the Dagster UI. Otherwise accept that a mid-edit auto-run may transiently FAIL and self-heal, and rely on R6's fresh-run + checksum gate.

### R9 — Module dependency matrix and the std gate
The gate is enforced by `scripts/checks/check_boundaries.py` (rule `dbt-ref`), not only by review: `core/` may `ref` only `cdm/`, `core/` and shared seeds (not tenant seeds: rule `dbt-seed`), so a core model can never read a connector model (`stg_*`, `src_*` or a connector `int_*`). Packs read connectors through `cdm/` too, except the connectors declared in `pack_connectors` of `model_buckets.yaml`. Run `scripts/checks/run-all.sh` before committing. A connector that needs to reach core exposes the data through a `std_*` view in `models/cdm/staging/` (full matrix: [modules.md §3](modules.md)). A new `std_*` also needs an entry in `scripts/checks/model_buckets.yaml` (bucket `cdm`). Core models that read a std view keep an **explicit column list**, so `source_system` never leaks into a public table.

Std views added for the core gate (all pass-through, `source_system` last, no `source_version`):

| std | Source | `source_system` |
|---|---|---|
| `std_customer_addresses`, `std_customer_contacts`, `std_customer_notes`, `std_customer_tags` | `stg_sapo_v2_customer_*` | `sapo_v2` |
| `std_order_events` | `int_order_snapshots_ranked` (history-log status snapshots) | `sapo_v2` |
| `std_order_tags` | `src_sapo_v2_orders` (`order_id`, `tags`) | `sapo_v2` |
| `std_teams`, `std_team_members`, `std_targets`, `std_marketing_spend` | `stg_teams`, `stg_team_members`, `stg_targets`, `stg_marketing_spend` | `gsheet` |

### R10 — Schema test at warn level
Every `std_*` added for the core gate carries the generic test `std_column_contract` (`transformation/tests/generic/std_column_contract.sql`) with `config: {severity: warn}`. It compares the view's column names, order and types with the list in the model's properties file and returns one row per mismatch. Types are copied from `information_schema` of a built warehouse, never written from memory. The test warns in the Dagster test results and does not block the nightly run; `contract: enforced` is deliberately not enabled yet.

## Checklist — adding or changing a Sapo entity
- [ ] Does it feed a dim/fact/int? → it needs a `std_<entity>` (R1).
- [ ] std = faithful pass-through, all columns, + `source_system` and no `source_version` (R2), no version suffix (R3).
- [ ] Header documents the column contract (R4).
- [ ] No new std for a consumer-less stg (R5).
- [ ] Capture baseline → create std → repoint → fresh green run + checksum identical → commit (R6).
- [ ] Raw/dlt untouched; source alias only (R7).
- [ ] Added to `model_buckets.yaml` (cdm); no allowlist entry left for the leak it closes (R9).
- [ ] `std_column_contract` test at `severity: warn` with types from the warehouse (R10).
