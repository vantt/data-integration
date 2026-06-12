# Documentation Index

> Comprehensive documentation for the Data Integration Pipeline

## Reading Guide

This documentation follows a **progressive disclosure** model. Start with Level 1 for a quick overview, then dive deeper as needed.

---

### Level 1: Understand (15 minutes)

| Document | Description | Time |
|----------|-------------|------|
| [Architecture](./architecture/overview.md) | System design, components, and principles | 10 min |
| [Glossary](./development/glossary.md) | Terminology, abbreviations, and conventions | 5 min |

### Level 2: Explore (1 hour)

| Document | Description | Time |
|----------|-------------|------|
| [Data Flow](./architecture/data-flow.md) | End-to-end pipeline flow, 7 hops explained | 30 min |
| [Data Model](./architecture/data-model.md) | Table relationships, grains, keys, and planned model map | 20 min |
| [Data Dictionary](./architecture/data-dictionary.md) | Column reference, entities, business metrics | 30 min |

### Level 3: Operate (2-3 hours)

| Document | Description | Time |
|----------|-------------|------|
| [Deployment](./operations/deployment.md) | Environment setup, configuration, initial load | 1 hour |
| [Operations](./operations/operations.md) | Daily operations, monitoring, maintenance | 1 hour |
| [Troubleshooting](./operations/troubleshooting.md) | Common issues and recovery procedures | 30 min |

### Level 4: Contribute

| Document | Description |
|----------|-------------|
| [Contributing](./development/contributing.md) | Development workflow, code standards, PR process |
| [Architecture Decisions](./decisions/) | ADRs — rationale behind key design decisions |

---

## Topic Map

Find any topic in one lookup:

### System Overview

| Document | What it covers |
|----------|---------------|
| [Architecture](./architecture/overview.md) | System design, components, principles |
| [Data Flow](./architecture/data-flow.md) | Pipeline flow from source to serving |
| [Data Model](./architecture/data-model.md) | Table inventory, grains, keys, relationships, planned models |
| [Data Dictionary](./architecture/data-dictionary.md) | Entity schemas, column definitions, field meanings |
| [Source Entities](./architecture/source-entities/index.md) | Raw source payloads, ingestion envelope, source-level schemas |
| [Glossary](./development/glossary.md) | Terms, naming conventions |

### Component Documentation

| Component | Entry Point | Key Topics |
|-----------|------------|------------|
| **Ingestion** (dlt) | [ingestion/docs/README.md](../ingestion/docs/README.md) | Sources, Pipelines, Incremental, Config |
| **Transformation** (dbt) | [transformation/docs/README.md](../transformation/docs/README.md) | Models, Materialization, Dedup, Testing |
| **Orchestration** (Dagster) | [orchestration/docs/README.md](../orchestration/docs/README.md) | Jobs, Assets, Schedules, Resources |
| **Webhook System** | [webhook_receiver/docs/README.md](../webhook_receiver/docs/README.md) | API, Security, CloudflareD1 |
| **Analytics** (Metabase) | [analytics-handbook/README.md](./analytics-handbook/README.md) | Domains, Playbooks, Blueprints |
| **detailView** (FastAPI) | [detailView/docs/README.md](../detailView/docs/README.md) | Order/Customer insight pages, hexagonal, read-only DuckDB |

### Documentation Roles

Use these ownership boundaries when deciding where to document tables, sources, metrics, and relationships:

| Document Type | Location | Role |
|---------------|----------|------|
| **Data Model** | [architecture/data-model.md](./architecture/data-model.md) | Owns the system-wide analytical model: table inventory, fact/dimension roles, grain, primary keys, foreign keys, cross-source joins, relationship diagrams, and planned table additions. Use it to answer "what tables exist or should exist, and how do they connect?" |
| **Data Dictionary** | [architecture/data-dictionary.md](./architecture/data-dictionary.md) | Owns table and column definitions: field names, types, descriptions, examples, allowed values, and important business meaning. Use it to answer "what does this table or column mean?" |
| **Source Entity Docs** | [architecture/source-entities/](./architecture/source-entities/index.md) | Own raw source contracts before dbt modeling: API/file payloads, nested JSON structures, raw natural keys, source-specific status/timestamp fields, ingestion envelope, and source availability. Use them to answer "what does the upstream source provide?" |
| **Transformation Model Catalog** | [../transformation/docs/MODELS.md](../transformation/docs/MODELS.md) | Owns dbt model lineage and implementation placement: `src_`, `stg_`, `std_`, `int_`, marts, materialization, and dependencies. Use it to answer "where is this modeled in dbt and what depends on it?" |
| **dbt Schema Files** | [../transformation/models/sources.yml](../transformation/models/sources.yml), `transformation/models/**/schema.yml` | Own executable dbt metadata: source declarations, model columns, tests, and dbt-facing descriptions. Use them to enforce implementation correctness. |
| **Analytics Domains** | [analytics-handbook/domains/](./analytics-handbook/domains/) | Own business questions, metric definitions, formulas, scope, caveats, and references to data models used. They may mark missing sources as `planned`, but they do not own full table schemas or ERDs. |

For a new datasource that is needed by a metric but not yet implemented in dbt, document it in layers: raw payload in `source-entities/`, analytical grain and relationships in `data-model.md`, column details in `data-dictionary.md`, implementation metadata in dbt YAML once built, and only a `planned` reference from the relevant analytics domain.

### Architecture Decisions (ADR)

| Document | What it covers |
|----------|---------------|
| [ADR Index](./decisions/) | All architecture decision records |
| [ADR-001](./decisions/001-pipeline-7-hop-elt.md) | Pipeline 7-hop và ELT pattern |
| [ADR-002](./decisions/002-immutable-data-lake.md) | Immutable append-only data lake |
| [ADR-003](./decisions/003-deduplication-3-layer.md) | 2-level dedup và src/stg/std split |
| [ADR-004](./decisions/004-three-channel-ingestion.md) | 3-channel ingestion redundancy |
| [ADR-005](./decisions/005-dual-duckdb.md) | Dual DuckDB (warehouse vs serving) |
| [ADR-006](./decisions/006-concurrency-strategy.md) | Asset-level locking, priority hierarchy |
| [ADR-007](./decisions/007-hybrid-job-dependencies.md) | Hybrid job explicit dependencies |
| [ADR-008](./decisions/008-analytics-as-code.md) | Analytics-as-Code (Markdown blueprints) |
| [ADR-009](./decisions/009-collection-by-audience.md) | Collection by audience, not topic |
| [ADR-010](./decisions/010-dashboard-owns-questions.md) | Dashboard owns its questions |
| [ADR-011](./decisions/011-dashboard-archetypes.md) | Dashboard archetypes (Pulse/Cockpit/Exploratory) |
| [ADR-012](./decisions/012-technology-stack.md) | Technology stack choices |
| [ADR-013](./decisions/013-development-heuristics.md) | Explicit > Implicit, Golden Sample |

### Operations

| Document | What it covers |
|----------|---------------|
| [Deployment](./operations/deployment.md) | Setup, install, deploy all components |
| [Operations](./operations/operations.md) | Daily ops, monitoring, health checks |
| [Troubleshooting](./operations/troubleshooting.md) | Diagnostics, recovery procedures |
| [Migration](./operations/migration.md) | Metabase DB migration |

### Domain Knowledge

| Document | What it covers |
|----------|---------------|
| [Sapo Platform](./context/sapo-platform.md) | Sapo e-commerce context, API limitations |
| [Sales Segmentation Guide](./context/sales-segmentation-guide.md) | Revenue segmentation: channel, product, team, employee |
| [Marketing Spend Setup](./context/marketing-spend-setup.md) | Marketing data configuration |
| [Analytics Domains](./analytics-handbook/domains/) | Business metrics by domain (Sales, Customer, Product, etc.) |

### Guides & How-To

| Document | What it covers |
|----------|---------------|
| [dbt vs Metabase](./guides/dbt-vs-metabase.md) | Architecture separation patterns |
| [Rill + Metabase](./guides/rill-with-metabase.md) | Recommended architecture for adding Rill alongside Metabase |
| [Targets Sheet](./guides/targets-sheet.md) | Google Sheets targets configuration |
| [Facebook Ads](./guides/facebook-ads.md) | FB Ads data integration |
| [Facebook Messenger](./guides/facebook-messenger.md) | FB Messenger integration |
| [Dashboard Design Patterns](./analytics-handbook/guides/dashboard_design_patterns.md) | Metabase dashboard best practices |
| [Metabase Concepts](./analytics-handbook/guides/metabase_concepts.md) | Metabase terminology and concepts |

### AI Agent Instructions

| Document | Scope |
|----------|-------|
| [AGENTS.md](../AGENTS.md) | Global rules & constraints |
| [transformation/AGENTS.md](../transformation/AGENTS.md) | dbt-specific rules |
| [analytics-handbook/AGENTS.md](./analytics-handbook/AGENTS.md) | BI/dashboard rules |

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
| `ingest_sapo_realtime_job` | Every 1 min | Webhook processing |
| `ingest_sapo_incremental_job` | Every 10 min | History log gap filling |
| `pipeline_batch_nightly_job` | 04:00 AM | Full batch reconciliation |

---

## For AI Agents

If you're an AI assistant working with this codebase:

- **Primary context file:** [AGENTS.md](../AGENTS.md)
- Contains: Repository structure, operation protocol, troubleshooting logic
- Always read AGENTS.md first before making changes

---

## Archive

Legacy design documents (Vietnamese, Phase 1) are preserved in [docs/archive/](./archive/README.md) for historical context.
