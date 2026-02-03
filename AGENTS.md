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

| Document                  | Description                           |
| ------------------------- | ------------------------------------- | ------------------------------- |
| `ARCHITECTURE.md`         | System design, components, principles |
| `DATA_FLOW.md`            | 7-hop pipeline flow                   |
| `DATA_DICTIONARY.md`      | Schema, entities, business metrics    |
| `DEPLOYMENT.md`           | Setup and configuration               |
| `OPERATIONS.md`           | Daily operations, monitoring          |
| `TROUBLESHOOTING.md`      | Common issues, recovery               |
| `dagster_dependencies.md` | Dependency logic & race conditions    | `/docs/dagster_dependencies.md` |
| `CONTRIBUTING.md`         | Development workflow                  |
| `GLOSSARY.md`             | Terminology, conventions              |

### Component Documentation

| Component            | Path                      | Key Files                                       |
| -------------------- | ------------------------- | ----------------------------------------------- |
| **Ingestion**        | `/ingestion/docs/`        | PIPELINES, CONFIGURATION, SOURCES, INCREMENTAL  |
| **Transformation**   | `/transformation/docs/`   | MODELS, DEDUPLICATION, TESTING, MATERIALIZATION |
| **Orchestration**    | `/orchestration/docs/`    | ASSETS, JOBS, SCHEDULES, RESOURCES              |
| **Webhook Receiver** | `/webhook_receiver/docs/` | API, SECURITY                                   |

---

## Multi-Project Repository Structure: `data-integration2`

**CRITICAL:** `data-integration2` is a monorepo containing THREE main independent functional areas with specific sub-projects:

### 1. Ingestion Pipelines (`data-integration2/ingestion`)

- **Purpose:** General data extraction pipelines (e.g., Sapo orders).
- **Tech:** Python, `dlt` (Data Load Tool), `playwright`.
- **Context:** Python-based ETL scripts.
- **Dependencies:** Independent `requirements.txt` in `/ingestion/`.

### 2. Webhook Receiver (`data-integration2/webhook_receiver`)

- **Purpose:** Service endpoints to receive and buffer incoming webhooks.
- **Implementations:**
  - **`cloudflareD1` (Recommended):**
    - **Tech:** TypeScript, Cloudflare Workers, SQLite (D1).
    - **Path:** `/webhook_receiver/cloudflareD1/`
    - **Docs:** `/webhook_receiver/cloudflareD1/README.md`
  - **`supabase_queue` (Legacy):**
    - **Tech:** Supabase Edge Functions, PostgreSQL (PGMQ).
    - **Path:** `/webhook_receiver/supabase_queue/`

### 3. Webhook Consumer (`data-integration2/webhook_consumer`)

- **Purpose:** Workers that polling/consume buffered webhooks and load them into the warehouse.
- **Implementations:**
  - **`cloudflared1_consumer`:**
    - **Tech:** Python, `dlt`.
    - **Mechanism:** Polls the Cloudflare Worker API.
    - **Path:** `/webhook_consumer/cloudflared1_consumer/`
  - **`supabase_consumer`:**
    - **Tech:** TypeScript, Node.js.
    - **Path:** `/webhook_consumer/supabase_consumer/`

### 5. Transformation (`data-integration2/transformation`)

- **Purpose:** Clean, enrich, and model data (Hops 4-6) using ELT pattern.
- **Tech:** dbt (Data Build Tool), DuckDB.
- **Context:** SQL models (`.sql`) and YAML configurations.
- **Dependencies:** `dbt-duckdb`.

### 4. Orchestration (`data-integration2/orchestration`)

- **Purpose:** Manage schedules, sensors, and pipeline coordination.
- **Tech:** Dagster.
- **Context:** Python-based assets, jobs, and sensors.
- **Dependencies:** `dagster`, `dagster-duckdb` (managed via root python environment or venv).

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
    - **NEVER** mix dependencies (e.g., do not verify `package.json` if working in a Python `ingestion` folder).

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
**OS**: Windows
**Shell**: PowerShell

## Architecture Map

- **Root**: `d:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2`
- **Component: Ingestion (DLT)**
  - Path: `./ingestion`
  - Interpreter: `./ingestion/venv/Scripts/python.exe`
  - Entry Points:
    - `run_orders_batch.py`: Batch sync for orders.
    - `run_customers_batch.py`: Batch sync for customers.
    - `run_accounts_batch.py`: Batch sync for accounts.
    - `run_history_log.py`: Batch sync for history log for all kind of entities.
    - `run_webhook_consumer.py`: Webhook processor (Args: `--once`, `--loop`) for all kind of entities.
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

When asked to "verify system health", execute the following sequence:

1.  **Check Read-Only Data Hops**:

    ```powershell
    python scripts/testing/verify_hops_readonly.py
    ```

    _Expectation_: Output should show row counts > 0 for `stg_sapo_orders` and `fact_orders`.

2.  **Dry-Run DBT**:

    ```powershell
    python transformation/scripts/run_dbt.py --select +tag:mart --target dev
    ```

    _Expectation_: Exit code 0.

3.  **Check Dagster Validity**:
    ```powershell
    dagster definitions validate
    ```
    _Expectation_: "Definitions validated" message.

## Troubleshooting Logic

- **Issue**: `ModuleNotFoundError`
  - **Fix**: Ensure you are using `ingestion/venv/Scripts/python.exe`, NOT system python.
- **Issue**: `dbt not found`
  - **Fix**: The wrapper `run_dbt.py` handles this. Do not run `dbt` directly. Use the wrapper.
- **Issue**: Locked Database
  - **Fix**: The serving script usually handles this, but if persistent, suggest user restart Metabase container.

## Important Constraints

- **Windows Paths**: Always use backslashes `\` or `os.path.join` compatibility.
- **Environment API**: Credentials are loaded from `ingestion/.dlt/secrets.toml` or OS Environment Variables. Do not hardcode secrets.

---

# AI Context - Data Engineering & Sapo Domain

## 1. Sapo Data Sources & Channels

Understanding where data comes from is crucial for debugging and extending the pipeline.

| Source          | Method        | Characteristics                                                                                                                                      |
| :-------------- | :------------ | :--------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Batch API**   | `json_api`    | **High Latency, High Volume.** Used for daily/hourly snapshots. Good for Orders (modified_on), weak for Customers (can't reliable sort by modified). |
| **Webhook**     | `webhook`     | **Real-time.** The "gold standard" for updates. Pushed to Cloudflare/Supabase -> consumed by DLT.                                                    |
| **History Log** | `history_log` | **Gap Filling.** Polls `/admin/settings/get_logs` every 5-10 mins to catch events missed by webhooks. Critical redundancy.                           |

## 2. Data Flow & Partitioning Mechanism

The ingestion layer (DLT) is **Append-Only** and uses a **Segregated Storage** strategy.

### Partition Structure

`sapo_raw/{entity}/ingest_method={method}/year={YYYY}/month={MM}/{file_id}.parquet`

- **Level 1 (`ingest_method`)**: Separates data by source (`batch_sync`, `webhook`, `history_log`).
  - _Benefit_: Allows selective re-syncing/deletion of a specific source without affecting others.
- **Level 2/3 (`year`/`month`)**: Time-based partitioning for efficient pruning by DuckDB.

### Ingestion Logic

- **No Merging**: DLT does not merge data. It simply capturing snapshots.
- **Redundancy**: A single order update might appear in all 3 channels. This is expected.

## 3. Transformation & Deduplication (The "Magic")

The "One Truth" is constructed in the **DBT Staging Layer**, not during ingestion.

### Deduplication Logic

Since we have multiple streams of the same entity, we use a `Last-Write-Wins` strategy based on `event_timestamp`.

**Algorithm:**

1. **Union** all partitions (via DuckDB hive partitioning).
2. **Window Function**:
   ```sql
   ROW_NUMBER() OVER (
       PARTITION BY entity_id
       ORDER BY
           event_timestamp DESC,      -- Latest business event wins
           CASE ingest_method         -- Source Priority as tie-breaker
               WHEN 'webhook' THEN 3
               WHEN 'history_log' THEN 2
               ELSE 1
           END DESC
   )
   ```
3. **Filter**: Keep only `rn = 1`.

## 4. Incremental Mechanism

- **Ingestion (DLT)**:
  - **Batch**: Cursor-based on `modified_on` (Orders) or `created_on` (Customers).
  - **History Log**: Cursor-based on `occur_at`.
- **Transformation (DBT)**:
  - Uses DuckDB's ability to prune Parquet files.
  - Logic: `WHERE event_timestamp > (SELECT MAX(event_timestamp) FROM {{ this }})`.
  - **Caveat**: Must handle "Late Arriving Data" (e.g., a history log fetching an old order). The partition structure helps, but reliable `event_timestamp` is key.

## 5. Domain Specifics

- **Orders**: Immutable ID. Transactional. `modified_on` is reliable.
- **Customers**: accurate updates are hard via Batch. Rely heavily on Webhooks/History Logs for profile updates (addresses, tags).

---

## Metabase MCP Configuration

The Metabase MCP server is configured and active for this project.

### Connection Details

- **Server Name:** `metabase`
- **MCP Tool:** `metabase-ai-assistant`
- **URL:** `http://127.0.0.1:3000/`
- **Status:** Connected (Verified 2026-01-28)

### Database Information

| ID  | Name            | Type   | Key Schemas | Notes                   |
| --- | --------------- | ------ | ----------- | ----------------------- |
| 1   | Sample Database | h2     | PUBLIC      | Metabase default sample |
| 2   | Sapo DuckDB     | duckdb | main        | Primary Data Warehouse  |

### Usage Notes

- Use `mcp_metabase_db_schemas(database_id=2)` to explore the main warehouse schemas.
- Many administrative/write tools are disabled in `mcp_config.json` to reduce context noise and safety.

## 6. Architecture & Deployment Criticals

### Dual DuckDB Strategy (IMPORTANT)

The system uses TWO distinct DuckDB files to separate **Transformation (Write)** from **Serving (Read)** to prevent locking and ensure stability.

1.  **Warehouse DB (`sapo_warehouse.duckdb`)**:
    - **Location**: `data_lake/sapo_warehouse.duckdb`
    - **Purpose**: The "Write" database. `dbt` builds models here.
    - **Paths**: Uses `/app/data_lake/export/...` (Absolute Docker Path).

2.  **Serving DB (`serving/olap.duckdb`)**:
    - **Location**: `data_lake/serving/olap.duckdb`
    - **Purpose**: The "Read" database for Metabase/BI.
    - **Mechanism**: Contains "Smart Views" that point to the _latest_ parquet export of the Warehouse.
    - **Sync**: Must be updated via `scripts/provisioning/generate_serving_db.py` after dbt runs.

**Critical Rule**:

- When fixing "Path not found" errors in Metabase, you are likely looking at `olap.duckdb`.
- Fixing `dbt` only updates `sapo_warehouse.duckdb`.
- You **MUST** run `generate_serving_db.py` to propagate changes/paths to `olap.duckdb`.
- Ensure `PORTABLE_ROOT` in the script matches the Docker mount path (e.g., `/app/data_lake`).

### Dagster Concurrency & DuckDB Locking (CRITICAL)

DuckDB single-file storage (`sapo_warehouse.duckdb`) DOES NOT support concurrent writes.
However, **Ingestion (DLT)** writes to files and IS safe to run in parallel.

**Strategy: Asset-Level Locking**
We use Dagster's **Global Concurrency Limits** to lock ONLY the `dbt` step.

- **Key**: `duckdb_lock`
- **Limit**: `1`
- **Implementation**:
  - `run_dagster.ps1` sets the limit on startup.
  - `orchestration/assets/dbt.py` applies `op_tags={"dagster/concurrency_key": "duckdb_lock"}`.

**DO NOT** add `concurrency_group` tags to Jobs anymore. This blocks parallel ingestion.
**DO NOT** remove the `set-concurrency-limit` command from startup scripts.

### Script Updates

- **Note**: The `scripts/` folder is baked into the Docker image (usually). If you edit a script locally, you must **Rebuild Container** or **Docker CP** it to apply changes immediately.

### Explicit Dependencies (Hybrid Jobs)

- **Issue**: dbt models start before specific ingestion assets finish in a job that runs a subset of ingestion (e.g., Incremental).
- **Cause**: Dagster only respects `get_asset_key` source mappings. If the source maps to a Batch asset (excluded from job), Dagster assumes no dependency for the active job.
- **Fix**: Must manually inject `sapo_history_log_asset` (or relevant ingestion asset) into `upstream_keys` in `dbt.py` for Staging/Source models. **Always check `dagster_dependencies.md`**.

## 7. dbt & DuckDB OOM Optimization Guide

**Problem**: `dbt build --full-refresh` crashes with OOM (Out Of Memory) on large models (e.g., `stg_sapo_orders`).

**Root Cause**: DuckDB aggressively uses RAM for Window Functions and Sorts. If a table has huge JSON columns (`payload`), carrying them through a deduplication step will explode memory usage.

**Optimization Strategies (Applied & Proven):**

1.  **Strict Late Materialization (Double Deduplication)**:
    - **Concept**: Never `SELECT *` or select heavy columns (JSON) in the deduplication CTE.
    - **Step 1**: Extract ONLY lightweight keys (`id`, `timestamp`) -> Dedup -> Get `winner_ids`.
    - **Step 2**: Join `winner_ids` back to Source to get Payload -> Extract fields -> **DROP Payload immediately**.
    - **Step 3 (Critical)**: Ensure NO further sorting/deduplication happens after the heavy payload is read. Using `QUALIFY` on the final dataset triggers a massive sort -> **OOM**.

2.  **Profile Tuning (`profiles.yml`)**:
    - **`memory_limit`**: Set LOWER than container limit (e.g., `5GB` or `7GB` for a 16GB machine). This forces DuckDB to **Spill to Disk** early instead of crashing.
    - **`threads`**: Set to `1` or `2`. High threads = High concurrent buffer usage = OOM. Sequential processing is slower but stable.

3.  **Handling Exact Duplicates**:
    - If source has 100% duplicate rows, a JOIN will multiply them. Use `QUALIFY ROW_NUMBER() ... = 1` solely on the UNIQUE ID constraint at the very end, but ensure the dataset is ALREADY pruned of heavy columns if possible.

## 8. Proven Solutions & Common Pitfalls (Lessons Learned)

These are hard-earned lessons from debugging the system. **IGNORE THEM AT YOUR PERIL.**

### A. Concurrency & Locking

1.  **DuckDB is Single-Writer**: Never run dbt models in parallel threads if they write to the same `.duckdb` file.
    - **Bad**: `threads: 8` in profiles.yml.
    - **Bad**: job-level `concurrency_group` (blocks parallel ingestion).
    - **Good**: Asset-level locking (`op_tags={"dagster/concurrency_key": "duckdb_lock"}`) on dbt assets only.
2.  **Multiprocessing on Windows**:
    - **Import Side-Effects**: Logic in `definitions.py` (like `ensure_directories()`) runs **every time** a process spawns. **Fix**: Move setup logic to `run_dagster.ps1` or Docker `command` chain.

### B. Process Management (Zombie Jobs)

1.  **Background Threads**: If a Dagster job finishes logic but hangs in `Started` state, a child thread is keeping the process alive.
    - **Culprit**: `DLT` and `dbt` telemetry threads.
    - **Fix**: Set `DLT_TELEMETRY_DISABLED=true` and `DBT_SEND_ANONYMOUS_USAGE_STATS=false` in generic environment variables.
2.  **Scheduling Overlaps**:
    - **Issue**: Incremental jobs taking longer than schedule interval pile up.
    - **Fix**: Use `context.instance.get_runs()` in the `@schedule` function to `SkipReason` if a run is already active.

### C. Docker & CLI

1.  **CLI Versioning**: Commands like `set-concurrency-limit` might change between Dagster versions. **Always verify** commands inside the container (`docker compose run ... --help`) before codifying them in scripts.
2.  **Network Timeouts**: Docker build failing on TLS handshake? Allow `up -d` to continue if code is mounted via volumes (hot-reload).

## 8. Analytics-as-Code (Literate Configuration)

We treat Metabase configuration as code, defined in Markdown.

### 1. The Strategy

- **Documentation is Code**: We write blueprints in `docs/` that double as documentation and deployment configs.
- **Execution**: `node .agent/skills/metabase-automation/scripts/deploy_from_markdown.js <file.md>`

### 2. File Locations

- **Blueprints**: `docs/blueprint_*.md` (e.g., `blueprint_sales.md`).
- **Template**: `.agent/skills/metabase-automation/templates/blueprint_template.md` (Syntax Reference).
- **Parsers**: `.agent/skills/metabase-automation/lib/markdown_parser.js`.

### 3. Workflow

1.  Discuss requirements in `docs/reports_and_metrics.md`.
2.  Formalize agreed logic into a Blueprint Markdown file.
3.  Deploy using the script.
4.  Verify in Metabase UI.
