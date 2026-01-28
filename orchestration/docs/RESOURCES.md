# Resource Documentation

> Dagster resource configurations for dbt, DuckDB, and external services

## Resource Overview

Resources provide shared configurations and connections to assets and ops.

| Resource | Purpose | Used By |
|----------|---------|---------|
| `dbt` | dbt CLI execution | dbt_assets |
| `duckdb` | DuckDB connection | serving_database |

---

## dbt Resource

### Configuration

```python
from dagster_dbt import DbtCliResource

dbt_resource = DbtCliResource(
    project_dir=Path(__file__).parent.parent / "transformation",
    profiles_dir=Path(__file__).parent.parent / "transformation",
    target="dev"
)
```

### Path Resolution

The dbt executable is resolved in this order:

1. System PATH
2. Virtual environment: `ingestion/venv/Scripts/dbt.exe`
3. Fallback error

```python
def resolve_dbt_path():
    # Check PATH first
    if shutil.which("dbt"):
        return "dbt"

    # Check venv
    venv_dbt = Path(__file__).parent.parent / "ingestion/venv/Scripts/dbt.exe"
    if venv_dbt.exists():
        return str(venv_dbt)

    raise FileNotFoundError("dbt not found")
```

### Environment Variables

```python
dbt_resource = DbtCliResource(
    project_dir=...,
    env={
        "DATA_LAKE_PATH": os.environ.get("DATA_LAKE_PATH"),
        "DBT_EXPORT_PATH": os.environ.get("DBT_EXPORT_PATH")
    }
)
```

### Usage in Assets

```python
from dagster_dbt import dbt_assets, DbtCliResource

@dbt_assets(manifest=manifest_path)
def all_dbt_assets(context, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()
```

---

## DuckDB Resource

### Configuration

```python
from dagster import ConfigurableResource
import duckdb

class DuckDBResource(ConfigurableResource):
    database_path: str

    def get_connection(self, read_only: bool = False):
        return duckdb.connect(self.database_path, read_only=read_only)
```

### Usage

```python
@asset
def serving_database(duckdb: DuckDBResource):
    conn = duckdb.get_connection()
    conn.execute("CREATE VIEW ...")
    conn.close()
```

---

## Resource Registration

### definitions.py

```python
from dagster import Definitions

defs = Definitions(
    assets=[...],
    jobs=[...],
    schedules=[...],
    resources={
        "dbt": DbtCliResource(
            project_dir=TRANSFORMATION_DIR,
            profiles_dir=TRANSFORMATION_DIR
        ),
        "duckdb": DuckDBResource(
            database_path=str(DATA_LAKE_PATH / "serving/olap.duckdb")
        )
    }
)
```

---

## Environment Configuration

### Development

```python
# Local development resources
dev_resources = {
    "dbt": DbtCliResource(
        project_dir=TRANSFORMATION_DIR,
        target="dev"
    ),
    "duckdb": DuckDBResource(
        database_path="data_lake/serving/olap.duckdb"
    )
}
```

### Production

```python
# Production resources with different paths
prod_resources = {
    "dbt": DbtCliResource(
        project_dir="/app/transformation",
        target="prod"
    ),
    "duckdb": DuckDBResource(
        database_path="/data/serving/olap.duckdb"
    )
}
```

### Environment-Based Selection

```python
import os

env = os.environ.get("DAGSTER_ENV", "dev")

resources = dev_resources if env == "dev" else prod_resources

defs = Definitions(
    assets=[...],
    resources=resources
)
```

---

## Custom Resources

### Example: Sapo API Client

```python
from dagster import ConfigurableResource
import requests

class SapoResource(ConfigurableResource):
    api_key: str
    api_secret: str
    store_url: str

    def get_client(self):
        from ingestion.src.sapo_client import SapoClient
        return SapoClient(
            api_key=self.api_key,
            api_secret=self.api_secret,
            store_url=self.store_url
        )

# Usage
@asset
def sapo_orders_batch(sapo: SapoResource):
    client = sapo.get_client()
    orders = client.get_orders()
    ...
```

### Example: Cloudflare D1 Client

```python
class CloudflareD1Resource(ConfigurableResource):
    api_token: str
    account_id: str
    database_id: str
    worker_url: str

    def poll_messages(self, limit: int = 1000):
        response = requests.get(
            f"{self.worker_url}/poll",
            params={"limit": limit},
            headers={"Authorization": f"Bearer {self.api_token}"}
        )
        return response.json()
```

---

## Secrets Management

### From Environment

```python
import os

defs = Definitions(
    resources={
        "sapo": SapoResource(
            api_key=os.environ["SAPO_API_KEY"],
            api_secret=os.environ["SAPO_API_SECRET"],
            store_url=os.environ["SAPO_STORE_URL"]
        )
    }
)
```

### From dlt Secrets

```python
import dlt

secrets = dlt.secrets

sapo_resource = SapoResource(
    api_key=secrets["sources.sapo.api_key"],
    api_secret=secrets["sources.sapo.api_secret"],
    store_url=secrets["sources.sapo.store_url"]
)
```

---

## Resource Dependencies

Resources can depend on other resources:

```python
class AnalyticsResource(ConfigurableResource):
    duckdb: DuckDBResource

    def run_query(self, sql: str):
        conn = self.duckdb.get_connection(read_only=True)
        result = conn.execute(sql).fetchall()
        conn.close()
        return result
```

---

## Testing Resources

### Mock Resources

```python
from unittest.mock import MagicMock

def test_asset_with_mock_dbt():
    mock_dbt = MagicMock(spec=DbtCliResource)
    mock_dbt.cli.return_value.stream.return_value = iter([])

    result = my_dbt_asset(dbt=mock_dbt)
    assert result is not None
```

### Test Fixtures

```python
import pytest

@pytest.fixture
def test_duckdb():
    return DuckDBResource(database_path=":memory:")

def test_serving_database(test_duckdb):
    result = serving_database(duckdb=test_duckdb)
    assert result is not None
```

---

## Related

- [Assets](./ASSETS.md)
- [Jobs](./JOBS.md)
- [Schedules](./SCHEDULES.md)
