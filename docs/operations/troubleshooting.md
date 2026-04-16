# Troubleshooting Guide

> Diagnostic commands, common issues, and recovery procedures

## Table of Contents

1. [Diagnostic Commands](#diagnostic-commands)
2. [Common Issues](#common-issues)
3. [Recovery Procedures](#recovery-procedures)
4. [Debug Mode](#debug-mode)

---

## Diagnostic Commands

### Quick Health Check

```bash
# Full system verification
python scripts/testing/verify_hops_readonly.py
```

### Check Data Freshness

```bash
# Check latest timestamps per entity
python -c "
import duckdb
conn = duckdb.connect(':memory:')
result = conn.execute('''
    SELECT 'orders' as entity, MAX(event_timestamp) as latest
    FROM read_parquet('data_lake/sapo_raw/order/**/*.parquet')
    UNION ALL
    SELECT 'customers', MAX(event_timestamp)
    FROM read_parquet('data_lake/sapo_raw/customer/**/*.parquet')
''').fetchall()
for row in result:
    print(f'{row[0]}: {row[1]}')
"
```

### Check Pipeline State

```bash
# dlt pipeline state
python -c "
import dlt
pipeline = dlt.pipeline(pipeline_name='sapo_orders')
print('Last run:', pipeline.last_trace.started_at if pipeline.last_trace else 'Never')
print('State:', pipeline.state)
"

# Dagster job status
dagster job list --running
```

### Check Database Connections

```bash
# Test DuckDB
python -c "
import duckdb
conn = duckdb.connect('data_lake/sapo_warehouse.duckdb')
print('Tables:', conn.execute('SHOW TABLES').fetchall())
"

# Test serving database
python -c "
import duckdb
conn = duckdb.connect('data_lake/serving/olap.duckdb', read_only=True)
print('Views:', conn.execute('SHOW TABLES').fetchall())
"
```

### Check Webhook Buffer (D1)

```bash
# Check pending message count
curl -s "https://your-worker.workers.dev/poll?limit=1&dry_run=true" \
  -H "Authorization: Bearer $CF_TOKEN" | jq '.count'
```

---

## Common Issues

### Ingestion Problems

#### Issue: API Rate Limiting

**Symptoms:**
- 429 Too Many Requests errors
- Slow or incomplete data sync

**Diagnosis:**
```bash
grep "429" ingestion/.dlt/pipeline_traces/*.log
```

**Solution:**
```python
# Reduce parallel requests in config.toml
[extract]
max_parallel_items = 2  # Reduce from 5

# Or add delay between requests in pipeline code
```

---

#### Issue: Webhook Delivery Failures

**Symptoms:**
- Missing real-time data
- D1 queue empty but data not in Parquet

**Diagnosis:**
```bash
# Check D1 for error status messages
curl "https://your-worker.workers.dev/poll?status=error"

# Check worker logs in Cloudflare dashboard
```

**Solution:**
```bash
# Release locked messages for retry
curl -X POST "https://your-worker.workers.dev/release-all"

# Or manually reprocess
python ingestion/run_webhook_consumer.py --reprocess-errors
```

---

#### Issue: Authentication Errors

**Symptoms:**
- 401 Unauthorized from Sapo API
- "Invalid credentials" in logs

**Diagnosis:**
```bash
# Test API credentials
python -c "
from src.sapo_client import SapoClient
client = SapoClient()
print(client.test_connection())
"
```

**Solution:**
```bash
# Check secrets.toml
cat ingestion/.dlt/secrets.toml | grep -A3 '[sources.sapo]'

# Verify credentials haven't expired
# Regenerate API key in Sapo admin if needed
```

---

### Transformation Failures

#### Issue: DuckDB Out of Memory (OOM)

**Symptoms:**
- "Out of Memory" error during dbt run
- Process killed unexpectedly

**Diagnosis:**
```bash
# Check memory usage during run
dbt run --select large_model &
watch -n 1 'ps aux | grep duckdb | grep -v grep'
```

**Solution:**
```sql
-- Option 1: Reduce memory limit in dbt model config
{{ config(
    materialized='incremental',
    duckdb_config={'memory_limit': '4GB'}
) }}

-- Option 2: Use Strict Late Materialization pattern
-- (Already implemented in staging models)
```

---

#### Issue: Deduplication Mismatches

**Symptoms:**
- Duplicate records in staging tables
- Inconsistent counts between raw and staging

**Diagnosis:**
```sql
-- Find duplicates
SELECT entity_id, COUNT(*) as cnt
FROM {{ ref('stg_sapo_orders') }}
GROUP BY entity_id
HAVING COUNT(*) > 1;
```

**Solution:**
```bash
# Check deduplication logic
# Ensure ROW_NUMBER() OVER (PARTITION BY entity_id ...) = 1

# Force full refresh
python transformation/scripts/run_dbt.py run --select stg_sapo_orders --full-refresh
```

---

#### Issue: Schema Evolution Errors

**Symptoms:**
- "Column X not found" errors
- Type mismatch errors

**Diagnosis:**
```bash
# Compare schemas
python -c "
import duckdb
conn = duckdb.connect(':memory:')
print(conn.execute('''
    DESCRIBE SELECT * FROM read_parquet('data_lake/sapo_raw/order/**/*.parquet')
''').fetchall())
"
```

**Solution:**
```sql
-- Add column with default
SELECT
    COALESCE(payload->>'new_column', 'default') as new_column,
    ...
FROM source

-- Or use TRY_CAST for type safety
TRY_CAST(payload->>'amount' AS DECIMAL) as amount
```

---

### Orchestration Issues

#### Issue: Dagster Schedule Not Triggering

**Symptoms:**
- Jobs not running at scheduled time
- Schedule shows as "Running" but no executions

**Diagnosis:**
```bash
# Check schedule status
dagster schedule list

# Check daemon status
dagster-daemon status
```

**Solution:**
```bash
# Restart daemon
dagster-daemon run &

# Or force manual execution
dagster schedule kick ingest_sapo_realtime_schedule
```

---

#### Issue: Asset Materialization Failures

**Symptoms:**
- "Asset materialization failed" in Dagster
- Partial data updates

**Diagnosis:**
```bash
# Check run logs in Dagster UI
# Or via CLI
dagster run view <run_id>
```

**Solution:**
```bash
# Retry failed asset
dagster asset materialize -a failed_asset_name

# If dependency issue, materialize upstream first
dagster asset materialize -a upstream_asset
dagster asset materialize -a failed_asset_name
```

---

### Serving Layer Issues

#### Issue: Metabase Connection Refused

**Symptoms:**
- "Connection refused" in Metabase
- Dashboard queries failing

**Diagnosis:**
```bash
# Check if DuckDB file exists
ls -la data_lake/serving/olap.duckdb

# Check file permissions
stat data_lake/serving/olap.duckdb

# Check Docker mount
docker exec metabase ls -la /data_lake/serving/
```

**Solution:**
```bash
# Regenerate serving database
python scripts/provisioning/generate_serving_db.py

# Restart Metabase
docker restart metabase

# Re-sync database in Metabase admin
```

---

#### Issue: Stale Data in Dashboards

**Symptoms:**
- Old data showing in Metabase
- Latest records not appearing

**Diagnosis:**
```sql
-- Check latest snapshot timestamp
SELECT MAX(_snapshot_ts)
FROM read_parquet('data_lake/export/marts/rolling/fact_orders/*.parquet');
```

**Solution:**
```bash
# Regenerate serving views
python scripts/provisioning/generate_serving_db.py --force

# Or sync Metabase database
# Metabase Admin → Databases → Sapo DuckDB → Sync database schema
```

---

#### Issue: Database Locked

**Symptoms:**
- "database is locked" error
- Concurrent access conflict

**Diagnosis:**
```bash
# Find processes using the file (Linux)
lsof data_lake/sapo_warehouse.duckdb

# Windows
handle.exe data_lake\sapo_warehouse.duckdb
```

**Solution:**
```bash
# Option 1: Wait for other process to finish

# Option 2: Restart conflicting service
docker restart metabase

# Option 3: Use read-only connection in queries
conn = duckdb.connect('file.duckdb', read_only=True)
```

---

## Recovery Procedures

### Partial Rerun (Specific Models)

```bash
# Rerun single model and downstream
python transformation/scripts/run_dbt.py run --select model_name+

# Rerun tag group
python transformation/scripts/run_dbt.py run --select tag:staging --full-refresh
```

### Full Backfill (Entity)

```bash
# Clear existing data
rm -rf data_lake/sapo_raw/order/ingest_method=batch_sync/*

# Re-backfill
python ingestion/run_orders_batch.py --backfill --days 90

# Re-transform
python transformation/scripts/run_dbt.py run --select +stg_sapo_orders+ --full-refresh
```

### State Reset (Pipeline)

```bash
# Reset dlt pipeline state
rm -rf ingestion/.dlt/pipelines/sapo_orders/

# Reset Dagster state (careful!)
# rm -rf .dagster_home/history/
# rm -rf .dagster_home/storage/

# Reinitialize
python ingestion/run_orders_batch.py  # Creates new state
```

### Complete Rebuild

```bash
# 1. Backup existing data
cp -r data_lake data_lake.backup

# 2. Clear everything
rm -rf data_lake/sapo_raw/*
rm -f data_lake/sapo_warehouse.duckdb
rm -rf data_lake/export/marts/*
rm -f data_lake/serving/olap.duckdb

# 3. Full backfill
python ingestion/run_orders_batch.py --backfill --days 365
python ingestion/run_customers_batch.py --backfill --days 365
python ingestion/run_accounts_batch.py

# 4. Full transform
python transformation/scripts/run_dbt.py run --full-refresh

# 5. Regenerate serving
python scripts/provisioning/generate_serving_db.py
```

---

## Debug Mode

### Enable Debug Logging

```bash
# dlt debug mode
export DLT_LOG_LEVEL=DEBUG
python ingestion/run_orders_batch.py

# dbt debug mode
python transformation/scripts/run_dbt.py run --select model --debug

# Dagster debug
dagster dev --log-level debug
```

### Inspect Raw Data

```python
# Interactive exploration
import duckdb
conn = duckdb.connect(':memory:')

# Sample raw data
conn.execute("""
    SELECT * FROM read_parquet('data_lake/sapo_raw/order/**/*.parquet')
    LIMIT 10
""").df()

# Check partition distribution
conn.execute("""
    SELECT ingest_method, year, month, COUNT(*) as cnt
    FROM read_parquet('data_lake/sapo_raw/order/**/*.parquet')
    GROUP BY 1, 2, 3
    ORDER BY 1, 2, 3
""").df()
```

### Test Transformations

```bash
# Compile SQL without running
python transformation/scripts/run_dbt.py compile --select model_name

# View compiled SQL
cat transformation/target/compiled/sapo_analytics/models/staging/stg_sapo_orders.sql
```

---

## Quick Reference

### Error Message → Solution

| Error | Likely Cause | Quick Fix |
|-------|--------------|-----------|
| `ModuleNotFoundError` | Wrong Python | Use `ingestion/venv/Scripts/python.exe` |
| `dbt not found` | Path issue | Use `python scripts/run_dbt.py` wrapper |
| `Database is locked` | Concurrent access | Restart Metabase |
| `Out of Memory` | Large query | Use incremental or reduce batch |
| `429 Too Many Requests` | API throttling | Reduce `max_parallel_items` |
| `Column not found` | Schema change | Add COALESCE/TRY_CAST |

### Emergency Contacts

| Issue Type | Contact |
|------------|---------|
| Pipeline failures | data-eng@company.com |
| Infrastructure | platform@company.com |
| Sapo API issues | support@sapo.vn |
| Cloudflare issues | Cloudflare Dashboard |

---

## Related Documents

- [Operations Manual](./operations.md) - Daily operations
- [Architecture](../architecture/overview.md) - System design
- [Data Flow](../architecture/data-flow.md) - Pipeline flow
