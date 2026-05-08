# Templates by Functional Group

> Each template lives in its group subfolder. Copy + customize. See group playbook for context.

## INGEST — `templates/ingest/`

- **`source-template.py`** — DLT source + resource + envelope builder. Pattern A custom envelope.
- **`run-entry-point-template.py`** — DLT entry point wrapper. MUST `return run_pipeline(...)` (L36).
- **`dagster-asset-template.py`** — Dagster ingestion asset. Includes `argv=[]`, `os.chdir`, `load_dlt_configuration`. Job Selection Guide in docstring.

## MODEL — `templates/model/`

- **`src-model-template.sql`** — dbt src_: INCREMENTAL, dedup, JSON extract, _dlt_load_id filter.
- **`dim-model-template.sql`** — dbt dim_ với `location=get_rolling_location()`.
- **`fact-model-template.sql`** — dbt fact_ với surrogate keys + rolling.
- **`sources-yml-template.yml`** — dbt sources với Hive partitioning glob.
- **`schema-yml-template.yml`** — dbt tests (unique, not_null, relationships).

## SERVE — `templates/serve/`

- **`dagster-serving-asset-template.py`** — serving asset, `deps=[dbt_assets]`.

## TRUST — `templates/trust/`

- **`ingestion-health-recorder-template.py`** — record_run API + DDL, composite PK.
- **`dlt-row-count-extractor-template.py`** — 3-layer fallback for filesystem destinations.
- **`ingestion-health-digest-template.py`** — Morning digest op + classification.
- **`backfill-health-rows-written-template.py`** — One-shot backfill, composite-PK-safe UPDATE.

## OPS — `templates/ops/`

- **`dagster-reactive-sensor-template.py`** — Hash polling sensor for external source.
- **`stuck-run-alerter-template.py`** — Activity-based stuck detection + cancel + kill subprocess + free slots.