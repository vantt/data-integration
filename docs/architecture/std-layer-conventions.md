# std Layer & Source-Versioning Conventions

Rules for working with the Sapo (and future multi-version) source layer in `transformation/`. Established during the P0 std-gate completion (2026-06-03) and the Sapo v2→v3 migration prep. Follow these so every entity is handled consistently — for v2 today and v3 later.

> Companion docs: [`naming-conventions.md`](naming-conventions.md) (column/model names), the migration plan `plans/260603-1730-sapo-std-gate-and-naming/` (`verification-protocol.md` for the exact checks), and `transformation/AGENTS.md` (dbt-layer rules).

## Layer model

```
raw (dlt) → src_<source>_<entity>_v<N> → stg_<source>_<entity>_v<N> → std_<entity> → int_/dim_/fact_ → marts → serving
                    (version-specific, source structure)              (conformed, version-agnostic CONTRACT)
```

## Rules

### R1 — The std gate (mandatory)
Every source entity that feeds a `dim_`, `fact_`, or `int_` model MUST flow through a `std_<entity>` conformance model. Downstream models read `std_*`, **never** `stg_<source>_*` directly. (Upstream `stg → stg` chains are fine; the gate applies to dim/fact/int consumers.)

### R2 — std model = faithful pass-through (no renames in v2)
A `std_<entity>` is a thin `view` over its `stg_<source>_<entity>` source: select ALL columns the stg outputs — **never drop or rename a column** — plus `'sapo' AS source_system` and `'v2' AS source_version`. Column renaming/standardization is a SEPARATE effort (see the P1+ rename phases), not done inside the v2 pass-through.

### R3 — Versioning suffix
The source **version is a `_v<N>` suffix** on src/stg models (`src_sapo_orders_v2`, `stg_sapo_orders_v2`; later `_v3`). The `std_<entity>` model is **version-agnostic — never carries a suffix**; it UNIONs the versions and is the stable contract every downstream model reads. (See `naming-conventions.md` §7.)

### R4 — std contract = the v3 interface
Each `std_<entity>` exposes a fixed column set = the **interface** that a future `stg_<source>_v3_<entity>` must satisfy. Document the column list in a header comment (`-- STD CONTRACT v2 … interface for v3 …`). When adding v3, map v3's structure to the SAME columns; `source_version` discriminates ('v2'/'v3').

### R5 — Don't wrap dead code
If a `stg_*` model has zero consumers (grep `ref('stg_…')` returns nothing), do NOT create a std for it — that violates YAGNI. Flag it as dead code for cleanup instead. (Example: `stg_sapo_inventories` is unused; inventory flows via `std_variants.inventories_json`.)

### R6 — Verify every change physically (no exceptions)
Any change to a std model or a repointed consumer must pass, in order:
1. `dbt parse` clean.
2. A **fresh** Dagster realtime run `RUN_SUCCESS` with `tests: … ERROR=0 FAIL=0` (started AFTER the edit).
3. **Checksum gate**: affected mart parquet byte-identical to baseline — use `plans/260603-1730-sapo-std-gate-and-naming/snapshots/checksum.py`. A pass-through must not change any mart output.
**Create the std model FIRST, then repoint consumers** (a mid-edit auto-run is then safe — consumers still ref stg). Each step = one git commit (revertible).

### R7 — Never move physical raw / dlt state
To version the raw layer, rename only the **dbt source alias** in `sources.yml` (`sapo_raw` → `sapo_v2_raw`) while keeping `external_location` pointed at the physical `…/sapo_raw/{name}/…` folder. **Do NOT** move/rename the physical folder, change dlt `dataset_name`, or touch `sapo_raw/_dlt_pipeline_state`. The raw holds irreplaceable history (Sapo truncates `history_log`; 2021–2025 exists only as the ingested parquet/Delta) — a state reset risks unrecoverable re-ingestion. v3 gets its OWN new raw dataset (`sapo_v3_raw`), no collision.

### R8 — Scheduling reality (this daemon)
`dagster schedule stop/start -f <file>` via CLI is **ineffective** here (ephemeral code-location origin ≠ daemon's), so you cannot pause the pipeline that way and `schedule list` shows a misleading `[STOPPED]`. The realtime job keeps firing every 3 min. To truly pause, use the Dagster UI. Otherwise accept that a mid-edit auto-run may transiently FAIL and self-heal, and rely on R6's fresh-run + checksum gate.

## Checklist — adding or changing a Sapo entity
- [ ] Does it feed a dim/fact/int? → it needs a `std_<entity>` (R1).
- [ ] std = faithful pass-through, all columns, + source_system/source_version (R2), no version suffix (R3).
- [ ] Header documents the column contract (R4).
- [ ] No new std for a consumer-less stg (R5).
- [ ] Capture baseline → create std → repoint → fresh green run + checksum identical → commit (R6).
- [ ] Raw/dlt untouched; source alias only (R7).
