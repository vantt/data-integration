# Global Agent Rules, Context & Configuration

**IMPORTANT:** _MUST READ_ and _MUST COMPLY_ with all _INSTRUCTIONS_ in project based on the context.

## Review Policy

- **Implementation Plan Approval**: Even if the general review policy is set to `Auto-proceeded`, you MUST ALWAYS obtain explicit user approval for any `implementation_plan.md` before proceeding to execution. Do not auto-proceed with implementation plans under any circumstances.

---

## Documentation Map

Comprehensive documentation is available following a **progressive disclosure** model:

### Quick Reference

| Document           | Purpose                       | Location          |
| ------------------ | ----------------------------- | ----------------- |
| **README.md**      | Project overview, quick start | `/README.md`      |
| **docs/README.md** | Documentation navigation hub  | `/docs/README.md` |
| **AGENTS.md**      | AI agent context (this file)  | `/AGENTS.md`      |

### System-Level Documentation (`/docs/`)

| Group | Documents |
| ----- | --------- |
| **Architecture** | `architecture/overview.md`, `architecture/data-flow.md`, `architecture/data-dictionary.md` |
| **Operations** | `operations/deployment.md`, `operations/operations.md`, `operations/troubleshooting.md`, `operations/migration.md` |
| **Development** | `development/contributing.md`, `development/glossary.md` |
| **Context** | `context/sapo-platform.md`, `context/sales-segmentation-guide.md`, `context/marketing-spend-setup.md` |

### Component Documentation

| Component            | Path                      | Key Files                                       |
| -------------------- | ------------------------- | ----------------------------------------------- |
| **Ingestion**        | `/ingestion/docs/`        | PIPELINES, CONFIGURATION, SOURCES, INCREMENTAL  |
| **Transformation**   | `/transformation/docs/`   | MODELS, DEDUPLICATION, TESTING, MATERIALIZATION |
| **Orchestration**    | `/orchestration/docs/`    | ASSETS, JOBS, SCHEDULES, RESOURCES              |
| **Webhook Receiver** | `/webhook_receiver/docs/` | API, SECURITY                                   |
| **Analytics**        | `/docs/analytics-handbook/` | domains/, semantic/, playbooks/, blueprints/, guides/, designs/ |

### Analytics 2-Skill Architecture

| Skill | Path | Role | Phases |
|-------|------|------|--------|
| **Analytics Design** | `.skills/analytics-design/` | Tool-agnostic analyst brain — THINK, DEFINE, DESIGN | Phase 0-6 |
| **Metabase Automation** | `.skills/metabase-automation/` | Metabase-specific engineer brain — TRANSLATE, BUILD, DEPLOY | Phase 7-10 |

**Agent Orchestration**: One agent runs both skills sequentially in a single conversation:
- **Phase 0-6**: Read only `.skills/analytics-design/*`. Output: domain, playbook, design spec.
- **Phase 7-10**: Read only `.skills/metabase-automation/*` + Design Spec + domain files. Output: blueprint.
- Do NOT read metabase-automation docs during Phase 0-6 (prevents tool-specific anchoring).

**Artifact ownership**:
- `domains/`, `playbooks/`, `guides/`, `designs/` → created under analytics-design knowledge
- `blueprints/` → created under metabase-automation knowledge

See `docs/ANALYTICS_2SKILL_SPEC.md` for full specification.

### Architecture Decisions

| Path | Description |
| ---- | ----------- |
| `/docs/decisions/` | 13 ADRs covering pipeline design, concurrency, analytics patterns, technology choices |

---

## Multi-Project Repository Structure

**CRITICAL:** this folder is a monorepo containing THREE main independent functional areas with specific sub-projects:

### 1. Ingestion Pipelines (`data-integration2/ingestion`)

- **Purpose:** General data extraction pipelines (e.g., Sapo orders).
- **Tech:** Python, `dlt` (Data Load Tool), `playwright`.
- **Context:** Python-based ETL scripts.
- **Dependencies:** Independent `requirements.txt` in `/ingestion/`.

### 2. Webhook Receiver (`data-integration2/webhook_receiver`)

- **Purpose:** Service endpoints to receive and buffer incoming webhooks.
- **Implementations:**
  - **`cloudflareD1` (Active):** TypeScript, Cloudflare Workers, SQLite (D1). Path: `/webhook_receiver/cloudflareD1/`
  - **`supabase_queue` (Deprecated):** Supabase Edge Functions, PostgreSQL (PGMQ). Path: `/webhook_receiver/supabase_queue/`

### 3. Webhook Consumer (`data-integration2/webhook_consumer`)

- **Purpose:** Workers that polling/consume buffered webhooks and load them into the warehouse.
- **Implementations:**
  - **`cloudflared1_consumer` (Active):** Python, `dlt`. Polls the Cloudflare Worker API. Path: `/webhook_consumer/cloudflared1_consumer/`
  - **`supabase_consumer` (Deprecated):** TypeScript, Node.js. Path: `/webhook_consumer/supabase_consumer/`

### 4. Orchestration (`data-integration2/orchestration`)

- **Purpose:** Manage schedules, sensors, and pipeline coordination.
- **Tech:** Dagster.
- **Context:** Python-based assets, jobs, and sensors.
- **Dependencies:** `dagster`, `dagster-duckdb` (managed via root python environment or venv).

### 5. Transformation (`data-integration2/transformation`)

- **Purpose:** Clean, enrich, and model data (Hops 4-6) using ELT pattern.
- **Tech:** dbt (Data Build Tool), DuckDB.
- **Context:** SQL models (`.sql`) and YAML configurations.
- **Dependencies:** `dbt-duckdb`.

### 6. Detail View App (`data-integration2/detailView`)

- **Purpose:** Read-only web app showing the COMPLETE warehouse insight for ONE order or ONE customer (search by code/id → detail page). Complements Metabase (single-entity drill-down, not aggregation).
- **Tech:** Python, FastAPI + Jinja2 + HTMX. **Hexagonal architecture** (domain ⟂ ports ⟂ adapters).
- **Data:** Opens `data_lake/serving/olap.duckdb` with `read_only=True` (same DB Metabase reads; zero lock risk). Queries `fact_*`/`dim_*`/`mart_*` views only — NEVER `int_*`.
- **Boundaries:** `domain/` + `application/` are pure (NO duckdb/fastapi imports — enforced by an architecture test). SQL lives ONLY in `adapters/outbound/duckdb/`.
- **Runtime:** Docker service `detail_view` (port `3005:8000`, Caddy `detailview.lan.fwg.vn`). No auth (LAN-only). Deps: own `detailView/requirements.txt`.

---

## AI Agent Rules for Multi-Project Repos

**BEFORE performing ANY operation:**

1.  **Verify Current Context:** Always check which sub-project/folder the user is working on.
2.  **Check Working Directory:** Use `pwd` or context clues to determine the location.
3.  **Respect Project Boundaries:**
    - **DLT** files ONLY in `/ingestion/`
    - **Receiver** files ONLY in `/webhook_receiver/`
    - **Consumer** files ONLY in `/webhook_consumer/`
    - **Transformation** files ONLY in `/transformation/`
    - **Orchestration** files ONLY in `/orchestration/`
    - **DetailView** files ONLY in `/detailView/`
    - **NEVER** mix dependencies (e.g., do not verify `package.json` if working in a Python `ingestion` folder).
4.  **Local Context Discovery**:
    - **MANDATORY**: Before starting work in a sub-component (e.g., `transformation/`), check if a local `AGENTS.md` exists (e.g., `transformation/AGENTS.md`).
    - **Action**: If it exists, YOU MUST READ IT. It contains specific constraints (like dbt config rules) that override or supplement this global file.

**When User Context is Ambiguous:**

- Ask which implementation they are working on (e.g., "Are you working on the Cloudflare D1 receiver or the Supabase queue?").
- Do NOT assume - always clarify before making changes.

**File Operations Safety:**

- **NEVER** move files between sub-projects without explicit instruction.
- **When searching:** Scope grep/search to the relevant sub-project directory to avoid false positives from sibling projects.

---

# AI Agent Operation Protocol (machine-readable context)

## System Identity

**System Name**: Data Integration Pipeline v2
**Context**: ETL pipeline syncing Sapo retail data to DuckDB Lakehouse.
**Runtime Environments**: Windows native (dev) | Docker Desktop with Linux containers on Windows host (prod/staging)
**Shell**: PowerShell (Windows) | bash (Docker Linux container)

## Architecture Map

- **Root**: `d:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2`
- **Component: Ingestion (DLT)**
  - Path: `./ingestion`
  - Interpreter: `./ingestion/venv/Scripts/python.exe`
  - Entry Points: `run_orders_batch.py`, `run_customers_batch.py`, `run_accounts_batch.py`, `run_history_log.py`, `run_webhook_consumer.py` (`--once`, `--loop`)
- **Component: Transformation (DBT)**
  - Path: `./transformation`
  - Wrapper Script: `./transformation/scripts/run_dbt.py`
  - Execution Command: `python transformation/scripts/run_dbt.py [args]`
- **Component: Serving (Provisioning)**
  - Path: `./scripts/provisioning`
  - Generator: `generate_serving_db.py`
- **Orchestrator**: Dagster (`./orchestration`)

## Operation Interface

### 1. Ingestion Actions

To run ingestion tasks, ALWAYS use the venv python.
Pattern: `{venv_python} ingestion/{script_name} [args]`

**Verification Output**: Look for `LoadInfo` object printed to stdout.

### 2. Verification Protocol (Self-Test)

When asked to "verify system health", execute:

1.  **Check Data Hops**: `python scripts/testing/verify_hops_readonly.py` — Expect row counts > 0.
2.  **Dry-Run DBT**: `python transformation/scripts/run_dbt.py --select +tag:mart --target dev` — Expect exit 0.
3.  **Check Dagster**: `dagster definitions validate` — Expect "Definitions validated".

## Troubleshooting Logic

- **`ModuleNotFoundError`**: Ensure you are using `ingestion/venv/Scripts/python.exe`, NOT system python.
- **`dbt not found`**: Use the wrapper `run_dbt.py`, do not run `dbt` directly.
- **Locked Database**: The serving script usually handles this. If persistent, suggest user restart Metabase container.

## Important Constraints

- **Cross-Platform Paths**: System runs on both Windows and Linux (Docker). ALWAYS use `os.path.join()` or forward slashes. Never hardcode backslashes or OS-specific path separators.
- **Python venv resolution**: Windows = `venv/Scripts/python.exe`, Linux/Docker = `venv/bin/python`. Use `sys.platform` to resolve.
- **File Locking**: Windows provides advisory locks (`PermissionError` on locked files). Linux containers do NOT — concurrent file access must be handled explicitly (retry, swap pattern, or graceful skip).
- **Environment API**: Credentials from `ingestion/.dlt/secrets.toml` or OS env vars. Do not hardcode secrets.

---

# AI Context - Data Engineering & Sapo Domain

## Data Sources & Pipeline Overview

Three ingestion channels feed an append-only Parquet data lake with segregated storage:

| Source          | Method        | Key Characteristic |
| :-------------- | :------------ | :----------------- |
| **Batch API**   | `json_api`    | High latency, high volume — daily/hourly snapshots |
| **Webhook**     | `webhook`     | Real-time — pushed to Cloudflare D1 → consumed by DLT |
| **History Log** | `history_log` | Gap filling — polls every 5-10 mins for missed events |

→ **Full detail:** [docs/context/sapo-platform.md](docs/context/sapo-platform.md) | [ingestion/docs/SOURCES.md](ingestion/docs/SOURCES.md)

## Transformation Architecture

4-layer pipeline: `src_ → stg_ → std_ → marts` using Kimball star schema.

→ **Full detail:** [transformation/docs/ARCHITECTURE_DETAIL.md](transformation/docs/ARCHITECTURE_DETAIL.md) | [transformation/docs/DEDUPLICATION.md](transformation/docs/DEDUPLICATION.md)

**CRITICAL CONSTRAINTS (keep inline):**
- `src_` models are INCREMENTAL tables — they extract JSON + deduplicate + discard payload (OOM-safe)
- `stg_` and `std_` are VIEWS only — lightweight, no materialization
- ALWAYS use `location="{{ get_rolling_location() }}"` for marts
- Never `SELECT *` from raw Parquet (OOM risk)
- See `transformation/AGENTS.md` for detailed dbt rules

## Domain Specifics

- **Orders**: Immutable ID. Transactional. `modified_on` is reliable.
- **Customers**: Accurate updates are hard via Batch. Rely on Webhooks/History Logs for profile updates.

---

## Metabase MCP Configuration

- **Server Name:** `metabase` | **Tool:** `metabase-ai-assistant` | **URL:** `http://127.0.0.1:3000/`
- **Primary DB:** Sapo (ID=2, type=duckdb, schema=main)
- Use `mcp_metabase_db_schemas(database_id=2)` to explore schemas.
- Many admin/write tools disabled in `mcp_config.json` for safety.

---

## Architecture & Deployment Criticals

### Deployment Environment (IMPORTANT)

The system operates in **two runtime modes** — all code MUST work in both:

| Mode | OS | Python venv | File Locking | Path Style |
|------|----|-------------|--------------|------------|
| **Windows native** (dev) | Windows | `Scripts/python.exe` | Advisory locks (PermissionError) | `os.path.join()` or `/` |
| **Docker Desktop** (prod/staging) | Linux container on Windows host | `bin/python` | No advisory locks — handle explicitly | Forward slashes only |

**Rule**: When writing filesystem, subprocess, or path logic — always verify behavior under both modes. Docker = Linux container, but the host is always Windows (Docker Desktop).

### Triple DuckDB Strategy (IMPORTANT)

Three distinct DuckDB files separate **Write**, **Read**, and **Export**:

1.  **Warehouse DB** (`data_lake/sapo_warehouse.duckdb`): dbt writes here. Uses Docker paths.
2.  **Serving DB** (`data_lake/serving/olap.duckdb`): Metabase reads here. Contains rolling self-refresh views pointing to latest Parquet exports.
3.  **Standalone Export DB** (`data_lake/serving/standalone/sapo_export_*.duckdb`): Self-contained snapshot (no parquet dependency). Built nightly by `sapo_standalone_export` asset. Exposed read-only at `https://files.etl.lan.fwg.vn/` via `data_fileserver` (Caddy). Use for offline analysis, AI tools, or external distribution.

**Critical Rule**: Fixing `dbt` only updates warehouse DB. You **MUST** run `generate_serving_db.py` to propagate changes to serving DB. Ensure `PORTABLE_ROOT` matches the Docker mount path.

**Standalone export is downstream of serving DB** — run order: dbt → `build_serving_db` → `sapo_standalone_export`.

### Dagster Concurrency & DuckDB Locking (CRITICAL)

DuckDB single-file storage DOES NOT support concurrent writes. Ingestion (DLT) writes to Parquet files and IS safe to run in parallel.

**Strategy: Asset-Level Locking** via Dagster Global Concurrency Limits:
- **Key**: `duckdb_lock` | **Limit**: `1`
- `run_dagster.ps1` sets the limit on startup.
- `orchestration/assets/dbt.py` applies `op_tags={"dagster/concurrency_key": "duckdb_lock"}`.

**DO NOT** add `concurrency_group` tags to Jobs (blocks parallel ingestion).
**DO NOT** remove the `set-concurrency-limit` command from startup scripts.

### Explicit Dependencies (Hybrid Jobs)

dbt models may start before ingestion finishes in subset jobs. **Fix**: Manually inject ingestion assets into `upstream_keys` in `dbt.py`.
→ See [orchestration/docs/ASSETS.md](orchestration/docs/ASSETS.md) | [orchestration/docs/SCHEDULES.md](orchestration/docs/SCHEDULES.md)

---

## Proven Solutions & Common Pitfalls (Lessons Learned)

**IGNORE THEM AT YOUR PERIL.**

### A. Concurrency & Locking

1.  **DuckDB is Single-Writer**: Never run dbt models in parallel threads to same `.duckdb` file.
    - **Bad**: `threads: 8` in profiles.yml. **Bad**: job-level `concurrency_group`.
    - **Good**: Asset-level locking (`op_tags`) on dbt assets only.
2.  **Multiprocessing on Windows**: Logic in `definitions.py` (like `ensure_directories()`) runs every process spawn. Move setup logic to `run_dagster.ps1` or Docker `command` chain.

### B. Process Management (Zombie Jobs)

1.  **Background Threads**: DLT/dbt telemetry threads keep processes alive. **Fix**: `DLT_TELEMETRY_DISABLED=true`, `DBT_SEND_ANONYMOUS_USAGE_STATS=false`.
2.  **Scheduling Overlaps**: Use `context.instance.get_runs()` to `SkipReason` if already active.
    - **Priority Hierarchy**: Realtime(1m) yields to Nightly/Incremental. Nightly runs with exclusivity.
    - **Schedule Offset**: Incremental at `*/10`, Realtime at `1-9,11-19...` to prevent start-time races.

### C. Docker & CLI

1.  **CLI Versioning**: Commands like `set-concurrency-limit` may change between Dagster versions. **Always verify** inside container.
2.  **Network Timeouts**: Docker build TLS failures? Allow `up -d` to continue if code is volume-mounted.

### D. Development Heuristics

1.  **Check Local Standards First**: When fixing/adding a model, **ALWAYS** compare against a working "Golden Sample" in the same directory. Don't assume `dbt_project.yml` handles everything.
2.  **Explicit > Implicit**: If unsure if a config is inherited, declare it explicitly.

---

## Semantic Layer Contract (Project-Wide)

**Canonical source:** `docs/analytics-handbook/semantic/`

Business concepts (segments, metrics, dimensions, business rules) are defined ONCE in the semantic layer and implemented downstream. All sub-projects that touch data or BI must be aware.

### Influence flow

```
Domain (WHY)       docs/analytics-handbook/domains/
    ↓ drives
Semantic (WHAT)    docs/analytics-handbook/semantic/    ← single source of truth
    ↓ constrains
Transformation     transformation/models/marts/          ← implements as columns
Rill               rill/metrics/*.yaml                   ← implements as measures
Metabase           docs/analytics-handbook/blueprints/   ← consumes columns
Detail View        detailView/                           ← consumes mart views
```

### Sub-project responsibilities

| Sub-project | Responsibility |
|---|---|
| **transformation/** | Implement semantic columns in mart exactly per definition. Never rename/change semantic columns without updating `semantic/`. |
| **docs/analytics-handbook/** | Maintain `semantic/` as canonical. Blueprints must use semantic columns, not re-derive logic. Declare `uses_concepts:` in blueprint frontmatter. |
| **rill/** | Measures and filters must reference mart semantic columns (`scope_retail`, etc.), not re-derive raw conditions. |
| **detailView/** | Query mart views only. Semantic columns available as-is — no re-derivation needed. |
| **ingestion/** | No direct semantic concern. Outputs raw data; transformation owns semantic mapping. |

### Key semantic files

| File | Covers |
|---|---|
| `semantic/segments.md` | scope_retail, scope_b2b, scope_sales — filter rules |
| `semantic/metrics.md` | net_revenue, gross_revenue, discount_rate, AOV |
| `semantic/dimensions.md` | date_key (ICT), customer_type, channel_* |
| `semantic/rules.md` | VAT treatment, cancellation, is_completed, COUNT(DISTINCT) |
| `semantic/freshness.md` | Data SLA per mart table |

### Non-negotiable rules

1. **Do not re-derive** semantic concepts from raw conditions — use pre-computed mart columns
2. **Do not rename** semantic columns without updating `semantic/` and notifying all consumers
3. **New concept** → define in `semantic/` first, implement in mart, then use in BI

---

## Analytics-as-Code (Literate Configuration)

We treat Metabase configuration as code, defined in Markdown.

- **Strategy**: Blueprints in `docs/analytics-handbook/blueprints/` double as documentation and deployment configs.
- **Execution**: `node .skills/metabase-automation/scripts/deploy_from_markdown.js <file.md>`
- **Template**: `.skills/metabase-automation/templates/blueprint_template.md`

### Workflow

1.  Define requirements via domain metrics in `docs/analytics-handbook/domains/`.
2.  Check/add semantic definitions in `docs/analytics-handbook/semantic/`.
3.  Create a playbook in `docs/analytics-handbook/playbooks/`.
4.  Formalize into a Blueprint Markdown file in `docs/analytics-handbook/blueprints/`.
5.  Deploy using the script.
6.  Verify in Metabase UI.
