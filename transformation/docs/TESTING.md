# Testing Documentation

> Data quality testing with dbt tests

## Overview

dbt tests ensure data quality at every layer of transformation. Tests run automatically after model builds and can be configured to fail or warn.

## Test Types

### Built-in Tests

| Test | Purpose | Example |
|------|---------|---------|
| `unique` | No duplicate values | Primary keys |
| `not_null` | No null values | Required fields |
| `accepted_values` | Value in allowed list | Status fields |
| `relationships` | FK exists in parent | Foreign keys |

### dbt_utils Tests

| Test | Purpose |
|------|---------|
| `unique_combination_of_columns` | Composite uniqueness |
| `expression_is_true` | Custom SQL condition |
| `not_constant` | Values vary |
| `at_least_one` | Has at least one row |
| `cardinality_equality` | Same distinct count |

## Test Configuration

### Schema-Level Tests

```yaml
# models/staging/schema.yml
version: 2

models:
  - name: stg_sapo_orders
    description: "Deduplicated order data"
    tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns:
            - order_id
    columns:
      - name: order_id
        description: "Primary key"
        tests:
          - unique
          - not_null

      - name: status
        tests:
          - not_null
          - accepted_values:
              values: ['draft', 'pending', 'confirmed', 'processing', 'completed', 'cancelled']

      - name: total
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: ">= 0"

      - name: customer_id
        tests:
          - relationships:
              to: ref('stg_sapo_customers')
              field: customer_id
```

### Singular Tests

Custom SQL tests in `tests/` directory:

```sql
-- tests/assert_no_orphan_orders.sql
-- Orders should have valid customers
SELECT o.order_id
FROM {{ ref('stg_sapo_orders') }} o
LEFT JOIN {{ ref('stg_sapo_customers') }} c
    ON o.customer_id = c.customer_id
WHERE o.customer_id IS NOT NULL
  AND c.customer_id IS NULL
```

## Test Severity

### Configure Severity

```yaml
columns:
  - name: email
    tests:
      - not_null:
          severity: warn  # Don't fail build
      - unique:
          severity: error  # Fail build (default)
```

### Severity Levels

| Level | Behavior |
|-------|----------|
| `error` | Fails the dbt run (default) |
| `warn` | Logs warning, continues |

## Running Tests

### All Tests

```bash
python scripts/run_dbt.py test
```

### Specific Model Tests

```bash
# Tests for one model
python scripts/run_dbt.py test --select stg_sapo_orders

# Tests for model and downstream
python scripts/run_dbt.py test --select stg_sapo_orders+
```

### By Tag

```bash
python scripts/run_dbt.py test --select tag:staging
```

### Store Failures

```bash
# Save failed rows for debugging
python scripts/run_dbt.py test --store-failures
```

Failed rows stored in: `{schema}_dbt_test__audit.{test_name}`

## Common Test Patterns

### Primary Key Tests

```yaml
- name: fact_orders
  tests:
    - dbt_utils.unique_combination_of_columns:
        combination_of_columns:
          - order_id
          - date_key
  columns:
    - name: order_key
      tests:
        - unique
        - not_null
```

### Foreign Key Tests

```yaml
columns:
  - name: customer_key
    tests:
      - not_null
      - relationships:
          to: ref('dim_customers')
          field: customer_key
```

### Business Rule Tests

```yaml
columns:
  - name: net_amount
    tests:
      - not_null
      - dbt_utils.expression_is_true:
          expression: ">= 0"
          config:
            where: "status != 'cancelled'"
```

### Data Freshness Tests

```yaml
sources:
  - name: sapo_raw
    freshness:
      warn_after: {count: 12, period: hour}
      error_after: {count: 24, period: hour}
    loaded_at_field: event_timestamp
```

## Model-Specific Tests

### stg_sapo_orders

```yaml
- name: stg_sapo_orders
  tests:
    # No duplicates after deduplication
    - dbt_utils.unique_combination_of_columns:
        combination_of_columns: [order_id]

  columns:
    - name: order_id
      tests: [unique, not_null]

    - name: status
      tests:
        - not_null
        - accepted_values:
            values: ['draft', 'pending', 'confirmed', 'processing', 'completed', 'cancelled']

    - name: total
      tests:
        - not_null
        - dbt_utils.expression_is_true:
            expression: ">= 0"

    - name: net_total
      tests:
        - dbt_utils.expression_is_true:
            expression: "= total - total_discount"
```

### dim_customers

```yaml
- name: dim_customers
  columns:
    - name: customer_key
      tests: [unique, not_null]

    - name: customer_id
      tests: [unique, not_null]

    - name: customer_tier
      tests:
        - accepted_values:
            values: ['Bronze', 'Silver', 'Gold', 'Platinum']
```

### fact_orders

```yaml
- name: fact_orders
  tests:
    - dbt_utils.unique_combination_of_columns:
        combination_of_columns: [order_id, date_key]

  columns:
    - name: order_key
      tests: [unique, not_null]

    - name: date_key
      tests:
        - not_null
        - relationships:
            to: ref('dim_date')
            field: date_key

    - name: customer_key
      tests:
        - relationships:
            to: ref('dim_customers')
            field: customer_key
            config:
              where: "customer_key IS NOT NULL"
```

## Debugging Failed Tests

### View Test SQL

```bash
# Compile test to see SQL
python scripts/run_dbt.py compile --select test_name
```

### Query Failed Rows

```sql
-- If using --store-failures
SELECT * FROM {schema}_dbt_test__audit.unique_stg_sapo_orders_order_id;
```

### Manual Verification

```sql
-- Check specific assertion
SELECT COUNT(*), COUNT(DISTINCT order_id)
FROM {{ ref('stg_sapo_orders') }};

-- Find specific failures
SELECT order_id, COUNT(*) as cnt
FROM {{ ref('stg_sapo_orders') }}
GROUP BY order_id
HAVING COUNT(*) > 1;
```

## Test Automation

### In Dagster

Tests run automatically after model builds:

```python
@dbt_assets(...)
def dbt_assets(context, dbt):
    yield from dbt.cli(["build"], context=context)  # run + test
```

### CI/CD

```yaml
# .github/workflows/dbt.yml
- name: Run dbt tests
  run: python transformation/scripts/run_dbt.py test
```

---

## Related

- [Models Catalog](./MODELS.md)
- [Deduplication](./DEDUPLICATION.md)
- [Data Dictionary](../../docs/architecture/data-dictionary.md)
