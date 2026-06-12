# Operations Manual

> Daily operations, monitoring, and maintenance guide

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Scheduling](#scheduling)
3. [Monitoring](#monitoring)
4. [Maintenance Tasks](#maintenance-tasks)
5. [Incident Response](#incident-response)
6. [Backup & Recovery](#backup--recovery)

---

## Daily Operations

### Morning Health Check

Run these checks daily to verify system health:

```bash
# 1. Check data freshness
python scripts/testing/verify_hops_readonly.py

# 2. Check Dagster job status
dagster job list --running

# 3. Check for failed runs (last 24h)
# Via Dagster UI: http://localhost:3000 → Runs → Filter by Failed
```

### Key Health Indicators

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| Data freshness (orders) | < 1 hour | 1-4 hours | > 4 hours |
| Data freshness (webhooks) | < 5 min | 5-30 min | > 30 min |
| dbt run duration | < 10 min | 10-30 min | > 30 min |
| Failed jobs (24h) | 0 | 1-2 | > 2 |
| Disk usage | < 70% | 70-85% | > 85% |

### Log Locations

| Component | Log Location |
|-----------|--------------|
| dlt pipelines | `ingestion/.dlt/pipeline_traces/` |
| dbt runs | `transformation/logs/` |
| Dagster | `.dagster_home/logs/` |
| Metabase | `docker logs metabase` |

---

## Scheduling

### Job Schedule Overview

| Job | Schedule | Timezone | Description |
|-----|----------|----------|-------------|
| `ingest_sapo_realtime_job` | */1 * * * * | Asia/Ho_Chi_Minh | Webhook processing |
| `ingest_sapo_incremental_job` | */10 * * * * | Asia/Ho_Chi_Minh | History log gap filling |
| `pipeline_batch_nightly_job` | 0 4 * * * | Asia/Ho_Chi_Minh | Full batch + refresh |
| `ingest_sheets_sync_job` | Manual | - | Google Sheets targets |

### Schedule Dependencies

```
pipeline_batch_nightly_job (04:00 AM)
├── ingest_sapov2_orders_batch_asset
├── sapo_customers_batch_asset
├── sapo_accounts_batch_asset
├── dbt_otp_assets (staging)
├── dbt_olap_assets (marts)
└── serving_generation_asset
```

### Manual Job Execution

```bash
# Run specific job
dagster job execute -j pipeline_batch_nightly_job

# Run specific asset
dagster asset materialize -a ingest_sapov2_orders_batch_asset

# Run dbt manually
python transformation/scripts/run_dbt.py run --select +tag:mart
```

### Disable/Enable Schedules

```bash
# Via Dagster UI:
# 1. Navigate to Schedules
# 2. Toggle schedule on/off

# Or via CLI:
dagster schedule stop ingest_sapo_realtime_schedule
dagster schedule start ingest_sapo_realtime_schedule
```

---

## Monitoring

### Dagster UI Dashboard

Access: http://localhost:3000

**Key Pages:**
- **Overview** - System status at a glance
- **Assets** - Data asset lineage and freshness
- **Runs** - Job execution history
- **Schedules** - Active schedules
- **Sensors** - Event-driven triggers

### Data Freshness Monitoring

```sql
-- Check latest data timestamps
SELECT
    'orders' as entity,
    MAX(event_timestamp) as latest,
    DATEDIFF('minute', MAX(event_timestamp), NOW()) as minutes_ago
FROM read_parquet('data_lake/sapo_raw/order/**/*.parquet')

UNION ALL

SELECT
    'customers',
    MAX(event_timestamp),
    DATEDIFF('minute', MAX(event_timestamp), NOW())
FROM read_parquet('data_lake/sapo_raw/customer/**/*.parquet');
```

### Key Metrics to Watch

| Metric | Query/Check | Threshold |
|--------|-------------|-----------|
| Order count today | `SELECT COUNT(*) FROM fact_orders WHERE date_key = today()` | > 0 |
| Webhook backlog | D1 Database: `SELECT COUNT(*) FROM messages WHERE status = 'pending'` | < 1000 |
| dbt test failures | `dbt test --store-failures` | 0 failures |
| Duplicate records | `SELECT entity_id, COUNT(*) FROM stg_* GROUP BY 1 HAVING COUNT(*) > 1` | 0 |

### Alert Configuration

Set up alerts for:

1. **Job Failure** - Dagster sends notification on run failure
2. **Data Staleness** - No new data for 1+ hour
3. **Disk Space** - Below 15% free
4. **Memory** - DuckDB OOM errors

---

## Maintenance Tasks

### Daily

| Task | Command | Notes |
|------|---------|-------|
| Review failed runs | Dagster UI → Runs → Failed | Fix and retry |
| Check disk space | `df -h data_lake/` | Alert if > 85% |

### Weekly

| Task | Command | Notes |
|------|---------|-------|
| Clean old snapshots | See below | Keep last 7 days |
| Vacuum DuckDB | See below | Reclaim space |
| Review dbt tests | `dbt test` | Fix any failures |

### Monthly

| Task | Command | Notes |
|------|---------|-------|
| Archive old raw data | See below | > 6 months old |
| Review query performance | Metabase slow query log | Optimize if needed |
| Update dependencies | `pip install -U ...` | Test first |

### Cleanup Scripts

```bash
# Clean old rolling snapshots (keep last 7 days)
python scripts/maintenance/cleanup_snapshots.py --days 7

# Vacuum DuckDB databases
python -c "
import duckdb
conn = duckdb.connect('data_lake/sapo_warehouse.duckdb')
conn.execute('VACUUM')
conn.close()
"

# Clean dlt state (old pipeline traces)
python scripts/maintenance/cleanup_dlt_state.py --days 30
```

### Data Lake Cleanup

```bash
# Find large files
du -sh data_lake/sapo_raw/*/ingest_method=*/* | sort -hr | head -20

# Remove old partitions (careful!)
# rm -rf data_lake/sapo_raw/order/ingest_method=batch_sync/year=2024/
```

---

## Incident Response

### Severity Levels

| Level | Description | Response Time | Example |
|-------|-------------|---------------|---------|
| P1 - Critical | Data pipeline down | 15 min | All jobs failing |
| P2 - Major | Significant data delay | 1 hour | Webhooks not processing |
| P3 - Minor | Partial issues | 4 hours | One entity sync failing |
| P4 - Low | Cosmetic/minor | Next business day | Dashboard formatting |

### Common Incidents

#### Incident: Webhook Processing Stopped

**Symptoms:**
- No new webhook data in Parquet
- D1 queue growing

**Diagnosis:**
```bash
# Check consumer status
dagster job list --running | grep ingest_sapo_realtime

# Check D1 queue size
curl -H "Authorization: Bearer $CF_TOKEN" \
  "https://your-worker.workers.dev/poll?limit=1&dry_run=true"
```

**Resolution:**
```bash
# Restart webhook consumer
dagster job execute -j ingest_sapo_realtime_job

# If D1 is full, increase poll limit
python ingestion/run_webhook_consumer.py --batch-size 5000
```

#### Incident: dbt Run Failing

**Symptoms:**
- Dagster job fails at dbt step
- Error in transformation logs

**Diagnosis:**
```bash
# Check dbt logs
cat transformation/logs/dbt.log | tail -100

# Run dbt with debug
python transformation/scripts/run_dbt.py run --select failing_model --debug
```

**Resolution:**
- Fix SQL syntax error
- Handle schema changes
- Increase memory if OOM

#### Incident: DuckDB Locked

**Symptoms:**
- "database is locked" error
- Multiple processes accessing same file

**Resolution:**
```bash
# Find processes using the file
lsof data_lake/sapo_warehouse.duckdb

# Kill conflicting process (careful!)
kill -9 <PID>

# Or restart Metabase container
docker restart metabase
```

### Escalation Path

1. **First Responder** - Check logs, attempt restart
2. **Data Engineer** - Debug pipeline code
3. **Platform Team** - Infrastructure issues
4. **Vendor Support** - External service issues (Sapo, Cloudflare)

---

## Backup & Recovery

### What to Backup

| Component | Backup Method | Frequency | Retention |
|-----------|---------------|-----------|-----------|
| Raw Parquet files | Copy/Sync | Daily | 2 years |
| dlt state | Copy `.dlt/pipelines/` | Daily | 30 days |
| Dagster state | Copy `.dagster_home/` | Daily | 30 days |
| DuckDB databases | Copy `.duckdb` files | Daily | 7 days |
| Configuration | Git repository | On change | Forever |

### Backup Script

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/data-integration/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup raw data (incremental)
rsync -av data_lake/sapo_raw/ $BACKUP_DIR/sapo_raw/

# Backup state
cp -r ingestion/.dlt/pipelines/ $BACKUP_DIR/dlt_state/
cp -r .dagster_home/ $BACKUP_DIR/dagster_state/

# Backup DuckDB
cp data_lake/sapo_warehouse.duckdb $BACKUP_DIR/
cp data_lake/serving/olap.duckdb $BACKUP_DIR/

echo "Backup completed: $BACKUP_DIR"
```

### Recovery Procedures

#### Recover from dlt State Loss

```bash
# If cursor state is lost, pipeline will re-fetch from beginning
# Option 1: Restore state from backup
cp backup/dlt_state/* ingestion/.dlt/pipelines/

# Option 2: Reset and re-backfill
rm -rf ingestion/.dlt/pipelines/sapo_orders/
python ingestion/run_orders_batch.py --backfill --days 90
```

#### Recover from DuckDB Corruption

```bash
# Option 1: Restore from backup
cp backup/sapo_warehouse.duckdb data_lake/

# Option 2: Rebuild from Parquet
rm data_lake/sapo_warehouse.duckdb
python transformation/scripts/run_dbt.py run --full-refresh
```

#### Recover from Raw Data Loss

```bash
# Restore from backup
rsync -av backup/sapo_raw/ data_lake/sapo_raw/

# Re-run transformation
python transformation/scripts/run_dbt.py run --full-refresh
```

### Disaster Recovery Plan

| Scenario | RTO | RPO | Procedure |
|----------|-----|-----|-----------|
| Single component failure | 1 hour | 0 | Restart component |
| DuckDB corruption | 2 hours | 24 hours | Restore from backup |
| Raw data loss | 4 hours | 24 hours | Restore + re-transform |
| Full system loss | 8 hours | 24 hours | Restore all + verify |

---

## Quick Reference

### Common Commands

```bash
# Check system status
python scripts/testing/verify_hops_readonly.py

# Run manual sync
python ingestion/run_orders_batch.py
python transformation/scripts/run_dbt.py run --select +tag:mart
python scripts/provisioning/generate_serving_db.py

# Restart components
docker restart metabase
dagster job execute -j pipeline_batch_nightly_job

# View logs
tail -f transformation/logs/dbt.log
docker logs -f metabase
```

### Contact Information

| Role | Contact |
|------|---------|
| Data Engineering | data-eng@company.com |
| Platform Team | platform@company.com |
| On-Call | oncall@company.com |

---

## Standalone Export (fileserver)

The nightly job materializes all serving views into a self-contained DuckDB file. Two access points (same content, choose what fits):

| URL | Use case |
|---|---|
| `http://<host>:3004/sapo_export_latest.duckdb` | Direct host port — LAN/VPN, scripts, AI tools |
| `https://files.etl.lan.fwg.vn/sapo_export_latest.duckdb` | Via Caddy reverse-proxy — TLS, friendly hostname |

**Auth:** HTTP basic auth on both URLs. Credentials stored in 1Password → "Data Platform / fileserver".

**Download & query:**

```bash
# Direct (host port 3004)
curl -u $FILESERVER_USER:$FILESERVER_PASSWORD \
  http://<host>:3004/sapo_export_latest.duckdb \
  -o sapo.duckdb

# Via Caddy (TLS)
curl -u $FILESERVER_USER:$FILESERVER_PASSWORD \
  https://files.etl.lan.fwg.vn/sapo_export_latest.duckdb \
  -o sapo.duckdb

# Query locally (no pipeline dependency)
duckdb sapo.duckdb -c "SELECT count(*) FROM fact_orders;"
```

**CRITICAL — `$$` escape in `.env.docker`:**
Docker Compose interpolates `$VAR` inside env_file values. bcrypt hashes contain `$` — they
WILL be corrupted unless you escape every `$` as `$$` when pasting `FILESERVER_PASSWORD_HASH`
into `.env.docker`.

Example: raw hash `$2a$14$abc...` must be stored as `$$2a$$14$$abc...`
The container receives the original single-`$` form. See `.env.docker.example` for the annotated example.

**File location (container):** `/app/var/data_lake/serving/standalone/`
**Retention:** last 3 timestamped snapshots + `sapo_export_latest.duckdb` alias.
**Re-run manually:**

```bash
docker compose exec data_platform \
  python scripts/provisioning/build_standalone_export.py
```

---

## Related Documents

- [Troubleshooting](./troubleshooting.md) - Common issues and fixes
- [Deployment](./deployment.md) - Initial setup guide
- [Architecture](../architecture/overview.md) - System design
