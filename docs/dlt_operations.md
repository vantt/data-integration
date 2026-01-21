# DLT Operations Guide

This document provides operational guidelines for managing the DLT (Data Load Tool) pipelines used in the Data Warehouse project.

## 1. Configuration

DLT uses a hierarchical configuration system.

### Key Files

- **Secrets (`dlt/.dlt/secrets.toml`)**: Contains sensitive information like database credentials, API keys, and specific destination paths.
  - _Example_: `bucket_url` for filesystem destination, Sapo credentials.
- **Config (`dlt/.dlt/config.toml`)**: Contains non-sensitive, shared configurations.

### Important Settings

- **`bucket_url`**: Defines where the Parquet files are stored (Data Lake path).
  - Location: `[destination.filesystem]` in `secrets.toml`.
  - Value: `file:///d:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake`

## 2. State Management

DLT maintains "State" to track what data has been loaded (Incremental Loading).

### State Locations

1.  **Local State (The "Brain")**
    - **Location**: `C:\Users\<User>\.dlt\pipelines\<pipeline_name>`
    - **Purpose**: Stores the current cursor (e.g., `created_on` timestamp) and schema schema.
    - **Effect**: DLT checks this _first_ to determine what data to fetch next.

2.  **Destination State (The Backup)**
    - **Location**: `data_lake/sapo_raw/_dlt_pipeline_state` (or inside the dataset).
    - **Purpose**: A backup of the state stored alongside the data.
    - **Effect**: If Local State is missing, DLT restores state from here to continue loading.

## 3. Operations & Troubleshooting

### How to Force a Full Refresh (Reset Pipeline)

If a pipeline is missing data or you want to reload everything from scratch:

1.  **Delete Local State**:
    - Remove the directory: `C:\Users\<User>\.dlt\pipelines\<pipeline_name>`
    - _Example_: `rd /s /q C:\Users\van.tran_fgorg\.dlt\pipelines\sapo_orders_batch`

2.  **Delete Destination Data (Optional)**:
    - If you want to ensure no duplicates or clean up old files, delete the corresponding folder in the Data Lake.
    - Path: `data_lake/sapo_raw/<entity_name>`

3.  **Run the Pipeline**:
    - Execute the run script normally. DLT will treat it as a fresh run.

### Common CLI Commands

Run these from the `dlt/` directory with `venv` activated.

- **Check Pipeline Info**:

  ```powershell
  dlt pipeline <pipeline_name> info
  ```

  _Shows synchronization status and load packages._

- **Drop Pipeline State** (Alternative to manual delete):

  ```powershell
  dlt pipeline <pipeline_name> drop --drop-all
  ```

  _Note: Sometimes fails if state is locked or inconsistent. Manual keyword deletion (Step 1 above) is often more reliable._

- **Sync Pipeline**:
  ```powershell
  dlt pipeline <pipeline_name> sync
  ```
  _Resets local state based on destination state._

DBWaver DuckDb
SET file_search_path = 'd:/\_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake';
