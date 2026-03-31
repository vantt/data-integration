# Contributing Guide

> Development workflow, code standards, and PR process

## Table of Contents

1. [Development Setup](#development-setup)
2. [Code Standards](#code-standards)
3. [Development Workflow](#development-workflow)
4. [Testing](#testing)
5. [Pull Request Process](#pull-request-process)

---

## Development Setup

### Prerequisites

- Python 3.10+
- Git
- VS Code (recommended) or PyCharm
- Docker (for Metabase testing)

### Initial Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd data-integration2

# 2. Create feature branch
git checkout -b feature/your-feature-name

# 3. Setup Python environment
cd ingestion
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dev dependencies

# 4. Setup pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

### IDE Configuration

#### VS Code Settings

```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/ingestion/venv/Scripts/python.exe",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "editor.formatOnSave": true,
    "files.exclude": {
        "**/__pycache__": true,
        "**/.dlt/pipelines": true,
        "**/venv": true,
        "data_lake/**": true
    }
}
```

#### Recommended Extensions

- Python
- Pylance
- SQLTools + DuckDB driver
- dbt Power User
- YAML

---

## Code Standards

### Python Code Style

**Formatting:** Black (line length 88)
**Linting:** Pylint + Flake8
**Type Hints:** Required for public functions

```python
# Good
def process_orders(
    orders: list[dict],
    batch_size: int = 100
) -> tuple[int, list[str]]:
    """
    Process order records and return count and errors.

    Args:
        orders: List of order dictionaries
        batch_size: Number of records per batch

    Returns:
        Tuple of (processed_count, error_messages)
    """
    processed = 0
    errors = []
    # ... implementation
    return processed, errors


# Bad
def process_orders(orders, batch_size=100):
    # No type hints, no docstring
    pass
```

### SQL Code Style (dbt)

**Formatting:** sqlfluff (duckdb dialect)
**Naming:** snake_case for all objects

```sql
-- Good
WITH source_data AS (
    SELECT
        entity_id,
        CAST(payload->>'total' AS DECIMAL(15, 2)) AS total_amount,
        event_timestamp
    FROM {{ source('sapo_raw', 'order') }}
    WHERE event_timestamp >= '{{ var("start_date") }}'
),

deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id
            ORDER BY event_timestamp DESC
        ) AS rn
    FROM source_data
)

SELECT
    entity_id AS order_id,
    total_amount,
    event_timestamp
FROM deduplicated
WHERE rn = 1

-- Bad
select entity_id, payload->>'total' as Total, event_timestamp
from {{ source('sapo_raw', 'order') }} where event_timestamp >= '{{ var("start_date") }}'
```

### dbt Model Standards

```yaml
# models/staging/schema.yml
version: 2

models:
  - name: stg_sapo_orders
    description: "Deduplicated order data from all ingestion sources"
    config:
      tags: ['staging', 'orders', 'otp']
    columns:
      - name: order_id
        description: "Primary key - Sapo order ID"
        tests:
          - unique
          - not_null
      - name: total_amount
        description: "Order total in VND"
        tests:
          - not_null
```

### Commit Message Format

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `refactor` - Code change that neither fixes nor adds
- `docs` - Documentation only
- `test` - Adding or updating tests
- `chore` - Maintenance tasks

**Examples:**
```
feat(ingestion): add retry logic for API rate limiting

fix(dbt): resolve OOM in stg_sapo_orders deduplication

docs: update deployment guide for new config format

refactor(orchestration): extract common asset configs
```

---

## Development Workflow

### Branch Naming

```
feature/   - New features
fix/       - Bug fixes
refactor/  - Code improvements
docs/      - Documentation updates
```

Examples:
- `feature/add-product-dimension`
- `fix/webhook-duplicate-handling`
- `docs/update-data-dictionary`

### Development Cycle

```
1. Create branch from main
   git checkout main
   git pull
   git checkout -b feature/your-feature

2. Make changes
   - Write code
   - Add tests
   - Update documentation

3. Test locally
   python scripts/testing/verify_hops_readonly.py
   python transformation/scripts/run_dbt.py test

4. Commit with meaningful messages
   git add .
   git commit -m "feat(dbt): add dim_products dimension table"

5. Push and create PR
   git push -u origin feature/your-feature
   # Create PR via GitHub/GitLab UI

6. Address review feedback
   git commit -m "fix: address review comments"
   git push

7. Merge after approval
```

### Local Testing

```bash
# Test ingestion changes
python ingestion/run_orders_batch.py --dry-run

# Test transformation changes
python transformation/scripts/run_dbt.py run --select your_model
python transformation/scripts/run_dbt.py test --select your_model

# Test orchestration changes
dagster definitions validate

# Full integration test
python scripts/testing/verify_hops_readonly.py
```

---

## Testing

### Test Types

| Type | Location | Command |
|------|----------|---------|
| dbt tests | `transformation/tests/` | `dbt test` |
| Python unit tests | `*/tests/` | `pytest` |
| Integration tests | `scripts/testing/` | `python verify_*.py` |

### dbt Tests

```yaml
# schema.yml
models:
  - name: fact_orders
    tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns:
            - order_id
            - date_key
    columns:
      - name: order_id
        tests:
          - unique
          - not_null
      - name: net_amount
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: ">= 0"
```

### Python Tests

```python
# tests/test_sapo_client.py
import pytest
from src.sapo_client import SapoClient


def test_parse_order():
    raw = {"id": 123, "total": "500000"}
    result = SapoClient.parse_order(raw)
    assert result["order_id"] == "123"
    assert result["total"] == 500000


def test_invalid_order():
    with pytest.raises(ValueError):
        SapoClient.parse_order({})
```

### Running Tests

```bash
# All dbt tests
python transformation/scripts/run_dbt.py test

# Specific dbt tests
python transformation/scripts/run_dbt.py test --select stg_sapo_orders

# Python tests
cd ingestion
pytest tests/ -v

# Integration tests
python scripts/testing/verify_hops_readonly.py
python scripts/testing/test_olap_queries.py
```

---

## Pull Request Process

### PR Checklist

Before submitting:

- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No sensitive data committed
- [ ] Passes all CI checks

### PR Template

```markdown
## Summary
Brief description of changes

## Type of Change
- [ ] New feature
- [ ] Bug fix
- [ ] Refactoring
- [ ] Documentation

## Changes Made
- Added X
- Modified Y
- Removed Z

## Testing
- [ ] dbt tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Documentation
- [ ] README updated
- [ ] CHANGELOG updated
- [ ] Inline comments added

## Screenshots (if applicable)
```

### Review Process

1. **Author** creates PR with description
2. **Reviewer** checks:
   - Code quality and style
   - Test coverage
   - Documentation
   - Performance implications
3. **Author** addresses feedback
4. **Reviewer** approves
5. **Author** merges (squash preferred)

### Merge Guidelines

- **Squash merge** for feature branches (clean history)
- **Merge commit** for release branches
- Delete branch after merge

---

## Project Structure Guidelines

### Adding New Models

```
1. Create source model (if needed)
   transformation/models/staging/src_new_entity.sql

2. Create staging model
   transformation/models/staging/stg_new_entity.sql

3. Update schema.yml with tests
   transformation/models/staging/schema.yml

4. Create dimension/fact if needed
   transformation/models/marts/*/new_model.sql

5. Update documentation
   docs/DATA_DICTIONARY.md
```

### Adding New Pipelines

```
1. Create pipeline script
   ingestion/run_new_entity.py

2. Add source module
   ingestion/src/new_entity_source.py

3. Configure in dlt
   ingestion/.dlt/config.toml

4. Add Dagster asset
   orchestration/assets/sapo_assets.py

5. Update documentation
   ingestion/docs/PIPELINES.md
```

---

## Getting Help

- **Documentation**: Start with [docs/README.md](./README.md)
- **Code Questions**: Search existing code for patterns
- **Architecture**: Review [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Team**: Reach out to data-eng@company.com

---

## Related Documents

- [Architecture](./ARCHITECTURE.md) - System design
- [Data Dictionary](./DATA_DICTIONARY.md) - Schema reference
- [Glossary](./GLOSSARY.md) - Terminology
