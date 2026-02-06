# Resource Documentation

> Dagster resource definitions and configurations

## Resource Overview

Resources provide shared configurations and connections to assets. currently, we primarily use the `dbt` resource.

| Resource | Purpose                     | Used By          |
| -------- | --------------------------- | ---------------- |
| `dbt`    | dbt CLI execution interface | `all_dbt_assets` |

---

## dbt Resource

### Configuration

Defined in `orchestration/definitions.py`, configured to use the project's dbt environment.

```python
resources={
    "dbt": DbtCliResource(
        project_dir=dbt.dbt_project.project_dir,
        dbt_executable=dbt_exe
    ),
}
```

### Executable Resolution

The system dynamically resolves the `dbt` executable to ensure compatibility across environments (Docker, Local, Windows/Linux).

1.  Checks system PATH (`shutil.which("dbt")`).
2.  Fallbacks to the local `ingestion/venv/Scripts/dbt.exe` if not found globally.

### Usage in Assets

Used by the `@dbt_assets` decorator in `orchestration/assets/dbt.py` to trigger builds.

```python
@dbt_assets(
    manifest=dbt_project.manifest_path,
    dagster_dbt_translator=SapoDbtTranslator(),
    op_tags={"dagster/concurrency_key": "duckdb_lock"}
)
def sapo_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    # Sets environment variables for export path
    os.environ["DBT_EXPORT_PATH"] = export_base_dir
    yield from dbt.cli(["build"], context=context).stream()
```

---

## Other Integrations

While not strictly defined as Dagster "Resources", other integrations are handled directly within assets:

- **DuckDB**: Accessed via `subprocess` calls to provisioning scripts or direct connection within dlt pipelines (`sapo_serving_db`).
- **Sapo API**: Configured via `load_dlt_configuration()` helper which loads `.env.local` and `.dlt/secrets.toml` directly into `os.environ`.
- **Google Sheets**: Accessed via `dlt` sources with credentials from `secrets.toml`.

---

## Related

- [Assets](./ASSETS.md)
- [Jobs](./JOBS.md)
- [Schedules](./SCHEDULES.md)
