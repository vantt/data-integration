# Transformation Layer Technical Documentation

## 1. Overview

The **Transformation Layer** (Hop 5 & 6) is the engine of the data warehouse, built on **dbt** (Data Build Tool) and **DuckDB**. It transforms raw JSON-based Parquet files into structured, clean, and business-ready data models.

We employ a **Lambda Architecture-inspired** approach, separating transformation into two distinct pipelines to balance latency and throughput:

1.  **OTP Pipeline (Operational)**: Fast, frequent, operational data for apps and daily workflows.
2.  **OLAP Pipeline (Analytical)**: Comprehensive, dimensional data for reporting and BI.

---

## 2. High-Level Architecture Diagram

```mermaid
graph LR
    subgraph Raw["Storage (Hop 3)"]
        P[AParquet Files]
    end

    subgraph Compute["DuckDB Engine"]
        direction TB

        subgraph OTP["OTP Pipeline (10 mins)"]
            Src[Sources] --> Stg[Staging Views]
            Stg --> Int[Intermediate Tables]
        end

        subgraph OLAP["OLAP Pipeline (60 mins)"]
            Int --> Marts[Marts / Star Schema]
        end
    end

    Raw --> Src
    Int --> Reports[Operational Reports]
    Marts -->|Export Parquet| Output[(/data_lake/export)]
    Output -.->|View| Serving[(Serving DB)]
    Serving --> BI[Metabase / BI]

    style OTP fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style OLAP fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
```

---

## 3. Pipeline Design: OTP vs OLAP

| Feature             | OTP Pipeline (Operational)                  | OLAP Pipeline (Analytical)                  |
| :------------------ | :------------------------------------------ | :------------------------------------------ |
| **Goal**            | Clean, standarized data for immediate use   | Deep insights, historical data, aggregation |
| **Frequency**       | **Every 10 minutes** (`*/10 * * * *`)       | **Hourly** (`0 * * * *`)                    |
| **Layers**          | `staging` -> `intermediate`                 | `marts`                                     |
| **Materialization** | Views (Stg), Tables (Int)                   | Tables (Facts, Dims)                        |
| **Latency**         | < 15 mins (Near Real-time)                  | ~ 1 hour                                    |
| **Key Use Case**    | "Did Order #123 sync?" "Current inventory?" | "Monthly Revenue?" "Cohort Retention?"      |

---

## 4. Layer Details & Data Flow

### 4.1. Staging Layer (`models/staging`)

**Role:** Technical cleaning & standardization.

- **Input**: Raw Parquet files (via `read_parquet`).
- **Tasks**:
  - Renaming columns (Snake Case).
  - Type Casting (String -> Integer, Decimal).
  - JSON Unnesting (Extracting fields from `payload` JSON).
  - **Deduplication**: Selecting the latest version of an entity based on `source_timestamp`.
- **Output**: `stg_sapo_orders`, `stg_sapo_customers`.

**Diagram: Staging Logic**

```mermaid
flowchart LR
    File[(Raw Parquet)] -->|Read| Src[Source View]
    Src -->|Window Function| Dedup[Deduplicated CTE]
    Dedup -->|JSON Extract| Clean[Clean Models]
    Clean --> Stg[(Staging View)]
```

### 4.2. Intermediate Layer (`models/intermediate`)

**Role:** Business Logic & Enrichment.

- **Input**: Staging Views.
- **Tasks**:
  - Joins (e.g., Joining Order with Customer).
  - Calculations (Net Price, Discount Amount).
  - Filtering (Removing test orders).
- **Output**: `int_sales_summary`, `int_customer_metrics`.

### 4.3. Marts Layer (`models/marts`)

**Role:** Reporting & API Consumption.

- **Input**: Intermediate Tables.
- **Output**: **Parquet Files** (Saved to `data_lake/export/marts`).
- **Serving**: Uses a lightweight DuckDB file (`serving/olap.duckdb`) containing **Views** that point to these Parquet files.
- **Modeling Strategy**: **Kimball Dimensional Modeling (Star Schema)**.

**Schema Diagram (ERD):**

```mermaid
erDiagram
    FACT_SALES ||--o{ DIM_DATE : "placed_on"
    FACT_SALES ||--o{ DIM_PRODUCT : "contains"
    FACT_SALES ||--o{ DIM_CUSTOMER : "bought_by"
    FACT_SALES ||--o{ DIM_LOCATION : "shipped_from"
    FACT_SALES ||--o{ DIM_ORDER_STATUS : "current_status"
    FACT_SALES ||--o{ DIM_PROMOTIONS : "applied_promo"
    FACT_SALES ||--o{ DIM_GEOGRAPHY : "shipped_to"

    FACT_SALES {
        string order_id
        string product_key FK
        string customer_key FK
        int date_key FK
        decimal revenue
        int quantity
    }

    DIM_PRODUCT {
        string product_key PK
        string sku
        string name
        string category
    }

    DIM_CUSTOMER {
        string customer_key PK
        string email
        string loyalty_tier
    }

    DIM_GEOGRAPHY {
        string geography_key PK
        string province
        string district
    }
```

---

## 5. Orchestration (Dagster Integration)

The separation is enforced at the orchestrator level using **Dagster Jobs** and **dbt Tags**.

### 5.1. Job Configuration

- **`sapo_dbt_otp_job`**: Runs `dbt build --select tag:otp`.
  - Covering: `staging/*`, `intermediate/*`.
- **`sapo_dbt_olap_job`**: Runs `dbt build --select tag:olap`.
  - Covering: `marts/*`.

### 5.2. Schedule Timeline

```mermaid
gantt
    title Pipeline Execution Schedule
    dateFormat HH:mm
    axisFormat %H:%M

    section Ingestion (dlt)
    Webhook/Logs Consumer :active, 08:00, 08:59

    section Transform (dbt)
    OTP Job (Run 1) :done, 08:10, 5m
    OTP Job (Run 2) :done, 08:20, 5m
    OTP Job (Run 3) :done, 08:30, 5m
    OTP Job (Run 4) :done, 08:40, 5m
    OTP Job (Run 5) :done, 08:50, 5m
    OLAP Job (Hourly) :crit, 08:55, 10m
```

---

## 6. Development Workflow

1.  **Modify Model**: Edit SQL in `transformation/models`.
2.  **Tagging**: Ensure `dbt_project.yml` has correct tags (`otp` or `olap`) for the folder.
3.  **Local Test**:

    ```powershell
    # Test OTP logic
    dbt build --select tag:otp

    # Test OLAP logic
    dbt build --select tag:olap
    ```

4.  **Deploy**: Push to Git. Dagster (if configured with CI/CD) will pick up definitions.
