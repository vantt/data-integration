# Documentation

> Comprehensive documentation for the Data Integration Pipeline

## Reading Guide

This documentation follows a **progressive disclosure** model. Start with Level 1 for a quick overview, then dive deeper as needed.

---

### Level 1: Understand (15 minutes)

Get a high-level understanding of the system.

| Document | Description | Time |
|----------|-------------|------|
| [Architecture](./ARCHITECTURE.md) | System design, components, and principles | 10 min |
| [Glossary](./GLOSSARY.md) | Terminology, abbreviations, and conventions | 5 min |

---

### Level 2: Explore (1 hour)

Understand how data flows through the system.

| Document | Description | Time |
|----------|-------------|------|
| [Data Flow](./DATA_FLOW.md) | End-to-end pipeline flow, 7 hops explained | 30 min |
| [Data Dictionary](./DATA_DICTIONARY.md) | Schema reference, entities, business metrics | 30 min |

---

### Level 3: Operate (2-3 hours)

Learn to deploy, operate, and troubleshoot the system.

| Document | Description | Time |
|----------|-------------|------|
| [Deployment](./DEPLOYMENT.md) | Environment setup, configuration, initial load | 1 hour |
| [Operations](./OPERATIONS.md) | Daily operations, monitoring, maintenance | 1 hour |
| [Troubleshooting](./TROUBLESHOOTING.md) | Common issues and recovery procedures | 30 min |

---

### Level 4: Contribute

Extend and improve the system.

| Document | Description |
|----------|-------------|
| [Contributing](./CONTRIBUTING.md) | Development workflow, code standards, PR process |

---

## Component Documentation

Deep dive into specific layers of the pipeline.

| Component | Path | Description |
|-----------|------|-------------|
| **Ingestion** | [ingestion/docs/](../ingestion/docs/) | dlt pipelines, Sapo API, incremental loading |
| **Transformation** | [transformation/docs/](../transformation/docs/) | dbt models, deduplication, materialization |
| **Orchestration** | [orchestration/docs/](../orchestration/docs/) | Dagster jobs, schedules, assets |
| **Webhook Receiver** | [webhook_receiver/docs/](../webhook_receiver/docs/) | Cloudflare Workers, D1 buffer |

---

## Quick Reference

### Key Paths

```
data-integration2/
├── ingestion/venv/Scripts/python.exe    # Python interpreter
├── ingestion/.dlt/secrets.toml          # API credentials
├── transformation/profiles.yml           # dbt connection
├── data_lake/sapo_raw/                   # Raw Parquet files
├── data_lake/serving/olap.duckdb        # Serving database
└── .dagster_home/                        # Dagster state
```

### Common Commands

```bash
# Run ingestion
python ingestion/run_orders_batch.py

# Run transformation
python transformation/scripts/run_dbt.py --select +tag:mart

# Start orchestrator
dagster dev

# Generate serving layer
python scripts/provisioning/generate_serving_db.py
```

### Key Schedules

| Job | Schedule | Description |
|-----|----------|-------------|
| `sapo_realtime_sync_job` | Every 1 min | Webhook processing |
| `sapo_incremental_sync_job` | Every 10 min | History log gap filling |
| `sapo_nightly_reconciliation_job` | 04:00 AM | Full batch reconciliation |

---

## For AI Agents

If you're an AI assistant working with this codebase:

- **Primary context file:** [AGENTS.md](../AGENTS.md)
- Contains: Repository structure, operation protocol, troubleshooting logic
- Always read AGENTS.md first before making changes

---

## Document Status

| Document | Status | Last Updated |
|----------|--------|--------------|
| Architecture | Complete | 2026-01-28 |
| Data Flow | Complete | 2026-01-28 |
| Data Dictionary | Complete | 2026-01-28 |
| Deployment | Complete | 2026-01-28 |
| Operations | Complete | 2026-01-28 |
| Troubleshooting | Complete | 2026-01-28 |
| Contributing | Complete | 2026-01-28 |
| Glossary | Complete | 2026-01-28 |

---

## Feedback

Found an issue or have suggestions? Update the relevant document and submit a PR, or contact the Data Engineering team.
