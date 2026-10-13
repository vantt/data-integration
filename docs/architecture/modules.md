# Kiến trúc module: authority và boundary theo component

> Tài liệu sống của kiến trúc module. Mỗi thay đổi về module (thư mục, bucket, ma trận phụ thuộc, connector, tenant) cập nhật mục tương ứng **trong cùng commit với code**. Quy ước chung: **mỗi vùng lưu trữ chỉ có một component được ghi**; component khác chỉ đọc qua giao diện đã khai báo.
>
> Lộ trình và lý do: plan `plans/261013-1751-modularize-data-platform-suite/` (gồm `roadmap.md`). Công cụ kiểm chứng refactor: [docs/operations/refactor-safety-harness.md](../operations/refactor-safety-harness.md).

## Trạng thái hiện tại

| Hạng mục | Trạng thái |
|---|---|
| Bucket của mọi dbt model (172 model, kể cả 10 model đang tắt) | ✅ Khai báo trong `scripts/checks/model_buckets.yaml` |
| Ma trận phụ thuộc, import chéo, seed trùng tên, URL cứng trong connector | ✅ Cưỡng chế bằng `scripts/checks/check_boundaries.py` (mục 3, mục 12) |
| Vi phạm đã biết | 61 = 24 phụ thuộc (mục 3) + 37 model tenant chưa dời thư mục, ghi trong `scripts/checks/boundary_allowlist.yaml` kèm lý do và hướng thoát |
| Thư mục dbt theo module `models/<module>/<layer>/` | ✅ 134 model (connectors, cdm, core, packs) + monitoring; ⏳ 37 model `tenant:fine_japan` còn ở `staging/`, `intermediate/`, `marts/` cũ |
| Connector package cho orchestration, tenant overlay, taxonomy module | ⏳ Đích (mục 4, 5, 9, 10) |

Các mục dưới đây mô tả trạng thái đích; chỗ nào đã khớp code được đánh dấu ✅.

## Mục lục

1. [Bản đồ tổng thể](#1-bản-đồ-tổng-thể)
2. [Quyền ghi theo vùng lưu trữ](#2-quyền-ghi-theo-vùng-lưu-trữ)
3. [Ma trận phụ thuộc giữa các module dbt](#3-ma-trận-phụ-thuộc-giữa-các-module-dbt)
4. [Kernel](#4-kernel)
5. [Connectors](#5-connectors)
6. [CDM (canonical layer)](#6-cdm-canonical-layer)
7. [Core](#7-core)
8. [Packs](#8-packs)
9. [Taxonomy module](#9-taxonomy-module)
10. [Tenant overlay Fine Japan](#10-tenant-overlay-fine-japan)
11. [Serving và người tiêu thụ](#11-serving-và-người-tiêu-thụ)
12. [Ranh giới Python và container](#12-ranh-giới-python-và-container)

---

## 1. Bản đồ tổng thể

```mermaid
flowchart TB
    subgraph EXT["Hệ thống ngoài"]
        SAPO[Sapo API + webhook]
        CF["Cloudflare Worker + D1"]
        MISA[MISA AMIS]
        SHP[Shopee Excel]
        GS[Google Sheets]
        FB[Facebook API]
    end
    subgraph KERNEL["Kernel (orchestration generic + serving)"]
        K[Dagster definitions, sensors, ops, asset checks,<br/>health DB, notifications, dbt runner, serving builder]
    end
    subgraph CONN["Connectors"]
        C1[sapo_v2]
        C2[shopee]
        C3[misa_amis]
        C4[sheets / gsheet]
        C5["facebook_* (dormant)"]
    end
    subgraph DBT["transformation/ (một dbt project)"]
        CDM[cdm/]
        CORE[core/]
        PACK[packs/]
        TAX[taxonomy macros + seeds]
        MON[monitoring/]
    end
    subgraph FJ["Tenant overlay Fine Japan"]
        FJD["tenants/fine_japan (dbt)"]
        FJO["orchestration/tenants/fine_japan<br/>(crm_sync, writeback, approach, hug)"]
    end
    subgraph SRV["Serving"]
        OLAP[(serving/olap.duckdb)]
    end
    subgraph CONS["Consumers"]
        MB[Metabase]
        EV[Evidence]
        RL[Rill]
        CRMAPP[CRM app]
        DV[detailView]
    end
    SAPO --> C1
    CF --> C1
    MISA --> C3
    SHP --> C2
    GS --> C4
    FB -.-> C5
    C1 & C2 & C3 & C4 --> CDM
    CDM --> CORE --> PACK
    TAX -. "macro dùng trong" .-> CORE & PACK & FJD
    CORE & PACK --> FJD
    CORE & PACK & FJD --> OLAP
    OLAP --> MB & EV & RL & CRMAPP & DV
    K -. "điều phối, giám sát" .-> CONN & DBT & FJO & OLAP
    FJO <-->|"HTTP crm:8090, SQLite export"| CRMAPP
```

## 2. Quyền ghi theo vùng lưu trữ

```mermaid
flowchart LR
    subgraph WRITERS["Component ghi"]
        W1[Connector sapo_v2]
        W2[Connector shopee]
        W3[Connector misa_amis]
        W4[Connector sheets]
        W5["Tenant FJ: hug consumer"]
        W6["Tenant FJ: crm_writeback"]
        W7["dbt (theo module)"]
        W8["Kernel: serving builder"]
        W9["Kernel: health/ops"]
        W10["Tenant FJ: budget sync<br/>+ scripts/maintenance/sync_seeds"]
    end
    subgraph STORE["Vùng lưu trữ"]
        S1["data_lake/sapo_v2_raw/"]
        S2["data_lake/shopee_raw/"]
        S3["data_lake/misa_raw/"]
        S4["data_lake/gsheet_raw/"]
        S5["data_lake/hug_raw/"]
        S6["data_lake/crm_export/"]
        S7[("sapo_warehouse.duckdb<br/>main_staging / main / main_marts")]
        S8["export/marts/rolling/&lt;model&gt;/"]
        S9[("serving/olap.duckdb")]
        S10[("monitoring_db volume<br/>ingestion_health.db")]
        S11["transformation/seeds/**.csv"]
    end
    W1 --> S1
    W2 --> S2
    W3 --> S3
    W4 --> S4
    W5 --> S5
    W6 --> S6
    W7 --> S7
    W7 --> S8
    W8 --> S9
    W9 --> S10
    W10 --> S11
```

| Vùng | Owner (ghi) | Được đọc bởi | Cấm |
|---|---|---|---|
| `data_lake/<source>_raw/{entity}/ingest_method=/year=/month=` | Connector của nguồn đó | `transformation/models/connectors/<source>/_sources.yml` | Connector khác ghi; core/pack đọc trực tiếp |
| `data_lake/crm_export/` | Tenant FJ (`crm_writeback_assets`) | `connectors/crm` (stg_crm__*) | Ghi từ ngoài tenant FJ |
| `sapo_warehouse.duckdb` | dbt (một tiến trình, khoá `duckdb_lock` / `dbt_rw`) | dbt, scripts kiểm tra read-only | Ghi ngoài dbt |
| `export/marts/rolling/<model>/` | dbt model có `get_rolling_location()` | Kernel serving builder, Rill publish | Sửa tay |
| `serving/olap.duckdb` | Kernel (`refresh_rolling.py`, `bootstrap_serving_views.py`) | Metabase, Evidence, CRM, detailView (read-only) | Mọi consumer ghi |
| `monitoring_db` (health DB) | Kernel ops/sensors | Kernel asset checks, digest | Connector ghi trực tiếp (đi qua ops chung) |
| `transformation/seeds/taxonomy/*.csv` | Taxonomy module; writer Python đi qua `seed_paths.py` | dbt seed | Ghi theo đường dẫn cứng |
| `transformation/seeds/tenants/fine_japan/*.csv` | Tenant FJ (budget sync) | dbt seed | Module khác ghi |

### Vùng shadow (công cụ refactor, không phải prod)

| Vùng | Owner | Quy tắc |
|---|---|---|
| `/home/vantt/app/fg-dw-shadow/` (mode 0700) | Công cụ `scripts/shadow/*` | Chỉ tạo từ backup; chứa PII nên xoá lake nhánh sau mỗi gate, xoá toàn bộ khi đóng plan |
| Worktree `fg-dw-modular`, `fg-dw-baseline` | Người làm refactor | Không bao giờ mount vào container prod |
| Checkout prod `/home/vantt/app/fg-dataware-house` | Chỉ runbook deploy | Mọi script shadow từ chối đường dẫn này (`guard_not_prod.py`) |

## 2b. Bố cục thư mục dbt ✅

```text
transformation/models/
├── connectors/
│   ├── sapo_v2/staging/        # src_sapo_v2_* (incremental), stg_sapo_v2_*, _sources.yml
│   ├── sapo_v2/intermediate/   # int_order_snapshots_ranked (đọc thẳng raw history log)
│   ├── shopee/staging/  misa/staging/  gsheet/staging/
│   └── facebook_ads/staging/  facebook_messenger/staging/      # đang tắt
├── cdm/staging/                # std_* (canonical layer)
├── core/
│   ├── intermediate/{cogs,sapo,tags}/
│   └── marts/                  # dim_* ; intermediate/ (int_customer_*), sales/, customer/, inventory/
├── packs/
│   ├── finance/{intermediate/misa,marts}/
│   ├── marketplace/intermediate/shopee/
│   └── facebook_ads/marts/  facebook_messenger/marts/          # đang tắt
├── monitoring/
├── staging/ intermediate/ marts/   # chỉ còn model tenant:fine_japan, sẽ dời vào tenants/fine_japan/
├── sources.yml                 # nguồn của tenant (hug_raw, crm_export)
└── exposures_rill.yml
```

Quy tắc:

- **Module** = thư mục cấp 1 (theo bucket trong `scripts/checks/model_buckets.yaml`); luật `dbt-path` kiểm tra file nằm đúng `models/<module>/`.
- **Layer** = thư mục cấp 2 (`staging`, `intermediate`, `marts`). `dbt_project.yml` cấu hình schema/materialization/tags theo layer bằng YAML anchor (`&layer_staging`, `&layer_intermediate`, `&layer_marts`) và mỗi module tái sử dụng anchor đó, nên relation không phụ thuộc module. Thư mục con `shopee/`, `misa/`, `us_shipment/` trong `intermediate/` mang tag `int` + tên nguồn.
- Properties YAML nằm cạnh model: `_<module>__models.yml`; nguồn dbt của connector ở `connectors/<source>/staging/_sources.yml`.
- Thư mục `rolling/<model>/` được tạo từ manifest (`transformation/scripts/rolling_dirs.py`), không phụ thuộc thư mục model.
- Selection mà dagster-dbt gửi cho dbt dùng `fqn` (gồm thư mục), nên code server phải nạp manifest parse từ bố cục mới; lệnh start của container đã chạy `dbt parse` trước `dagster dev`.

## 3. Ma trận phụ thuộc giữa các module dbt ✅

```mermaid
flowchart TB
    CONN["connectors/&lt;x&gt;"] --> CDM["cdm/"]
    CDM --> CORE["core/"]
    CORE --> PACK["packs/&lt;p&gt;"]
    CDM --> PACK
    CONN -. "chỉ connector pack khai báo<br/>marketplace→shopee, finance→misa,<br/>facebook_*→facebook_*" .-> PACK
    CDM & CORE & PACK & CONN --> TEN["tenants/fine_japan"]
    TAX["macros/taxonomy + seeds/taxonomy"] --> CORE & PACK & TEN
    ALL["mọi module"] --> MON["monitoring/ (chỉ đọc)"]

    CORE -. "❌ cấm: core → connectors" .-x CONN
    CORE -. "⚠ tenant hook (allowlist)" .-> TEN
```

| Từ \ Tới | connectors | cdm | core | packs | tenants | seeds/taxonomy |
|---|---|---|---|---|---|---|
| **connectors/<x>** | chỉ `<x>` | ❌ | ❌ | ❌ | ❌ | ✅ |
| **cdm** | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| **core** | ❌ | ✅ | ✅ | ❌ | ⚠ hook | ✅ |
| **packs/<p>** | connector khai báo | ✅ | ✅ | chỉ `<p>` | ⚠ hook | ✅ |
| **tenants/<t>** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **monitoring** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

⚠ hook = vi phạm đã biết, ghi trong `scripts/checks/boundary_allowlist.yaml` kèm lý do (xem mục 10). `check_boundaries.py` fail khi có cạnh mới ngoài ma trận, và cả khi một mục allowlist không còn xảy ra (để allowlist không phình).

Số model theo bucket (`model_buckets.yaml`):

| Bucket | Model | Bucket | Model |
|---|---|---|---|
| connector:sapo_v2 | 28 | cdm | 14 |
| connector:shopee | 8 | core | 61 |
| connector:misa | 3 | pack:finance | 4 |
| connector:gsheet | 4 | pack:marketplace | 3 |
| connector:facebook_ads (tắt) | 3 | pack:facebook_ads (tắt) | 2 |
| connector:facebook_messenger (tắt) | 2 | pack:facebook_messenger (tắt) | 2 |
| tenant:fine_japan | 37 | monitoring | 1 |

Vi phạm đã biết (24):

| Nhóm | Số | Ví dụ | Hướng thoát |
|---|---|---|---|
| Core đọc thẳng staging của connector | 15 | `dim_customer_addresses` → `stg_sapo_v2_customer_addresses`; `fact_orders` → `stg_teams` | Thêm `std_*` pass-through, core chỉ đọc tầng canonical |
| Tenant hook (core phụ thuộc dữ liệu FJ) | 4 | `dim_staff` → `stg_crm__app_user`; `fact_order_costs` → `int_order_overhead_allocation`; `mart_data_quality` → `fact_us_shipment_economics` | Tách phần FJ vào tenant overlay |
| Core dùng dữ liệu kế toán MISA | 2 | `dim_sku_alias`, `mart_sku_economics_monthly` → `int_misa_sales_lines` | Đưa ledger qua tầng canonical như input tuỳ chọn |
| Core trộn phí sàn Shopee | 3 | `fact_order_costs` → `stg_shopee_*`; `fact_order_economics` → `int_shopee_order_fees` | Chuyển phần phí sàn sang `pack:marketplace` |

**Quyết định phân loại (13/10/2026):** COGS (`int_order_cogs_reconciled`, `int_order_promo_goods_cost`, `int_promo_642_monthly_total`, `mart_order_cogs_summary`) và tồn kho (`fact_inventory_*`, `int_sapo_inventories`, `int_return_sku_lines`, `mart_inventory_health`) thuộc **core**, không phải pack: các fact lõi (`fact_order_costs`, `fact_order_economics`, `mart_sku_economics_monthly`, `mart_product_health`) phụ thuộc vào chúng, và đây là phần chuẩn của bán hàng thương mại điện tử. `int_order_snapshots_ranked` đọc thẳng raw Sapo nên thuộc `connector:sapo_v2`.

## 4. Kernel

Kernel là phần dùng chung cho mọi tenant. Các file kernel **giữ nguyên vị trí** (dời sẽ làm hỏng đường dẫn tính theo `__file__`) và được nhận diện bằng tài liệu.

```mermaid
flowchart TB
    subgraph KERNEL["Kernel"]
        DEF["orchestration/definitions.py<br/>ghép connector + tenant từ modules.yaml<br/>job chéo nguồn: nightly, full refresh, _fact_order_returns"]
        REG["orchestration/connectors/__init__.py<br/>load_enabled()"]
        CFG["orchestration/config/<br/>modules.yaml, ingestion_sla.yaml"]
        DBTA["assets/dbt.py<br/>@dbt_assets, translator ghép DBT_SOURCE_KEYS<br/>tạo thư mục rolling theo manifest"]
        SERV["assets/serving.py, rill.py<br/>scripts/provisioning/*"]
        CHK["asset_checks/<br/>freshness, row_trend, cursor, reconciliation,<br/>kpi_closure, sla_loader, health_db"]
        SEN["sensors/<br/>failure_alerting, stuck_run_alerter,<br/>concurrency_pool_janitor, health_db_watchdog"]
        OPS["ops/<br/>ingestion_health, dlt_metrics, file_metrics,<br/>morning_digest, system_backup, purge_runs"]
        NOTI["notifications/lark_client.py"]
        RUN["ingestion/src/utils/<br/>pipeline_runner, shared_cookie_manager, seed_paths<br/>ingestion/src/file-drop-utils.py"]
    end
    CFG --> REG --> DEF
    DEF --> DBTA & SERV & CHK & SEN & OPS
    CHK & SEN & OPS --> NOTI
    REG -. "ghép DIGEST_DISPLAY,<br/>JOB_MAX_RUNTIME, CHECK_ASSET_DEFS" .-> OPS & SEN & CHK
```

| Giao diện kernel cung cấp | Ai dùng |
|---|---|
| `SYNC_TAGS` / `duckdb_lock` (khoá ghi DuckDB) | Mọi job ghi warehouse |
| `run_pipeline(...)` (dlt) | Connector sapo_v2, hug |
| `get_data_lake_path()`, partition writer | Connector shopee, misa_amis |
| `seed_path(name)` | Taxonomy writers, budget sync |
| `send_lark_card(...)` | Sensors, ops |
| SLA (`ingestion_sla.yaml`, khoá `<prefix>/<function_name>`) | Asset checks |

**Kernel không import connector hay tenant**; chỉ nhận dữ liệu qua `load_enabled()`.

## 5. Connectors

### 5.1 Hợp đồng chung của một connector

```mermaid
flowchart LR
    subgraph PKG["orchestration/connectors/&lt;id&gt;/"]
        A["assets.py<br/>ASSETS"]
        J["jobs.py<br/>JOBS, SCHEDULES, SENSORS"]
        M["__init__.py<br/>DIGEST_DISPLAY, JOB_MAX_RUNTIME,<br/>CHECK_ASSET_DEFS, DBT_SOURCE_KEYS"]
    end
    subgraph ING["ingestion/"]
        E["run_*.py + src/&lt;source&gt;/"]
    end
    subgraph DBTC["transformation/models/connectors/&lt;id&gt;/"]
        SRC["_sources.yml"]
        ST["src_*, stg_*"]
    end
    RAW["data_lake/&lt;id&gt;_raw/"]
    A -->|"import / importlib"| E --> RAW
    RAW --> SRC --> ST
    ST --> CDM["cdm/std_*"]
    M --> KER["Kernel registry"]
```

| Connector | Ingestion | Raw | dbt | Ra cdm |
|---|---|---|---|---|
| `sapo_v2` | 7 `run_sapo_v2_*.py`, `src/sapo/` (batch, history log, webhook consumer từ D1) | `sapo_v2_raw/` | `src_sapo_v2_*` (11, incremental), `stg_sapo_v2_*` (16) | `std_orders`, `std_order_items`, `std_customers`, `std_products`, `std_variants`, … |
| `shopee` | `run-shopee-income-file-drop.py`, `src/shopee/` | `shopee_raw/` | `src_shopee_*`, `stg_shopee_*` | (đi thẳng `packs/marketplace`) |
| `misa_amis` | 6 `run-misa-*.py`, `src/misa_amis/` | `misa_raw/` | `src_misa_*`, `stg_misa_sales_lines` | `std_misa_sales_lines`, `std_misa_account_ledger` |
| `sheets` | `src/gsheet_*.py` | `gsheet_raw/` | `stg_targets`, `stg_marketing_spend`, `stg_teams`, `stg_team_members` | `std_targets`, `std_marketing_spend`, `std_teams`, `std_team_members` |
| `facebook_*` | `run_facebook_*_batch.py` (chưa có asset, dormant) | `facebook_ads`, `raw_messenger_data` | `stg_fb_*` | (đi thẳng `packs/facebook_*`) |

### 5.2 Connector sapo_v2 (chi tiết)

```mermaid
flowchart LR
    API["Sapo API v2"] --> B["batch: orders, customers,<br/>accounts, products,<br/>inventory_transactions"]
    API --> H["history_log (lấp khoảng trống)"]
    WH["Sapo webhook"] --> CF["Cloudflare Worker + D1"] --> WC["webhook_consumer asset (*/3)"]
    B --> R["sapo_v2_raw/&lt;entity&gt;/ingest_method=batch_sync"]
    H --> R2["ingest_method=history_log"]
    WC --> R3["ingest_method=webhook"]
    R & R2 & R3 --> SRC["src_sapo_v2_* (incremental, dedup)"]
    SRC --> STG["stg_sapo_v2_* (flatten, unnest)"]
    STG --> STD["cdm/std_* (+ source_system='sapo_v2')"]
```

Đích: connector sapo_v2 **không** chứa giá trị riêng của Fine Japan; domain Sapo và worker URL nằm ở cấu hình tenant.

## 6. CDM (canonical layer)

```mermaid
flowchart LR
    subgraph IN["Vào từ connectors"]
        I1[stg_sapo_v2_*]
        I2[stg_misa_* / src_misa_*]
        I3["gsheet stg_*"]
    end
    subgraph CDM["models/cdm/ (std_*)"]
        O["std_orders, std_order_items, std_order_discount_items,<br/>std_order_returns, std_payments, std_fulfillments"]
        C["std_customers, std_customer_addresses/contacts/notes/tags"]
        P["std_products, std_variants, std_variant_prices,<br/>std_inventory_movements"]
        E["std_order_events, std_order_tags"]
        S["std_accounts, std_teams, std_team_members"]
        T["std_targets, std_marketing_spend"]
        L["std_misa_sales_lines, std_misa_account_ledger"]
    end
    IN --> CDM
    CDM --> OUT["core/, packs/, tenants/"]
```

Luật của tầng này theo `docs/architecture/std-layer-conventions.md`: R1 downstream không đọc `stg_*`; R2 pass-through trung thành + `source_system`. Mỗi `std_*` có test danh sách cột/kiểu mức **warn**. Owner: module CDM; connector chỉ cung cấp `stg_*` đầu vào.

## 7. Core

```mermaid
flowchart TB
    CDM["cdm/std_*"] --> DIMS
    CDM --> FACTS
    subgraph CORE["models/core/"]
        DIMS["dims/<br/>dim_customers, dim_customers_base, dim_customer_*,<br/>dim_products, dim_product_types, dim_channels,<br/>dim_staff, dim_teams, dim_date, dim_time,<br/>dim_geography, dim_branch_location, dim_order_status,<br/>dim_payment_methods, dim_promotions, dim_sku_alias,<br/>dim_price_lists, dim_channel_targets"]
        FACTS["facts/<br/>fact_orders, fact_sales, fact_order_economics,<br/>fact_order_costs, fact_order_returns, fact_order_transitions,<br/>fact_fulfillments, fact_payments, fact_targets,<br/>fact_marketing_spend, fact_variant_prices_snapshot"]
        CUST["customer/<br/>int_customer_* (4 incremental), mart_customer_tier,<br/>mart_cohort_retention, mart_retention_waterfall_monthly,<br/>mart_customer_status_snapshot_monthly"]
        PROD["product/<br/>mart_product_health, mart_sku_economics_monthly,<br/>mart_data_quality, ..."]
        COGS["cogs/<br/>int_order_cogs_reconciled, int_order_promo_goods_cost,<br/>int_promo_642_monthly_total, mart_order_cogs_summary"]
        INV["inventory/<br/>int_sapo_inventories, int_return_sku_lines,<br/>fact_inventory_balance/movements/snapshot, mart_inventory_health"]
    end
    DIMS --> FACTS --> CUST & PROD
    COGS & INV --> FACTS
    TAX["macros/taxonomy"] -. "phân loại" .-> DIMS & FACTS & CUST & PROD
    CORE --> ROLL["export/marts/rolling/&lt;model&gt;/"]
```

- Core chỉ đọc `cdm/`, `core/`, seeds và macro taxonomy.
- Mọi tên model ở đây là **public** (76 serving view, Rill, CRM, detailView): không đổi tên khi refactor module.
- Nợ còn lại: xem bảng vi phạm đã biết ở mục 3.

## 8. Packs

```mermaid
flowchart LR
    CORE["core/"] --> FIN & MKT & FBA
    CDM["cdm/"] --> FIN
    MISA["connectors/misa"] --> FIN
    SHP["connectors/shopee"] --> MKT
    FBC["connectors/facebook_*"] --> FBA
    subgraph PACKS["models/packs/"]
        FIN["finance/<br/>dim_gl_account, int_misa_sales_lines,<br/>fact_account_balance_monthly, fact_cash_movement"]
        MKT["marketplace/<br/>int_shopee_order_items/fees/adjustments"]
        FBA["facebook_ads, facebook_messenger/<br/>dim_fb_*, fact_fb_*"]
    end
```

Một pack chỉ được đọc connector mà nó khai báo trong `pack_connectors` của `model_buckets.yaml` (finance → misa, marketplace → shopee, facebook_* → facebook_*); pack không đọc pack khác.

## 9. Taxonomy module

```mermaid
flowchart TB
    subgraph TAX["Taxonomy module"]
        MAC["transformation/macros/taxonomy/&lt;domain&gt;.sql<br/>một macro cho mỗi biến thể luật<br/>(customer_type__dim_customers, __fact_orders, __benchmarks, ...)"]
        SEED["transformation/seeds/taxonomy/<br/>ref_order_sources, ref_brands, ref_misa_channel_codes,<br/>ref_payment_methods, ref_spend_category, ref_tag_categories,<br/>ref_gl_accounts, ref_branch_locations"]
        DOC["transformation/docs/TAXONOMY.md<br/>kiểm kê + Known divergences"]
        SP["ingestion/src/utils/seed_paths.py"]
    end
    WR1["scripts/maintenance/sync_seeds.py"] --> SP
    WR2["ingestion/src/gsheet_marketing_spend.py"] --> SP
    SP --> SEED
    MAC --> CORE["core/, packs/, tenants/"]
    SEED -->|"ref()"| CORE
```

| Thuộc sản phẩm | Thuộc tenant |
|---|---|
| Danh sách domain, tên macro, cơ chế `seed_path`, kiểm tra trùng seed | Giá trị seed, nội dung luật trong từng macro biến thể (sau này chuyển thành dữ liệu) |

## 10. Tenant overlay Fine Japan

```mermaid
flowchart TB
    subgraph FJ["Tenant overlay Fine Japan"]
        subgraph FJDBT["transformation/models/tenants/fine_japan/"]
            HUG["hug/<br/>src_hug_*, stg_hug_*, mart_hug_optin, mart_hug_attribution"]
            US["us_shipment/<br/>stg_us_shipment_prices, int_us_shipment_line_prices,<br/>fact_us_shipment_economics"]
            CRMD["crm/<br/>stg_crm__* (10), mart_crm_*, mart_staff_performance_weekly,<br/>mart_customer_action_queue, mart_customer_sku_action_queue,<br/>int_crm_*, dim_action_scenario_registry"]
            CASH["cashflow/<br/>fact_cashflow_budget, mart_cashflow_*, mart_cash_surplus_allocation,<br/>dim_cash_allocation_policy"]
            OH["overhead/<br/>stg_overhead_account_classification,<br/>int_overhead_pool_monthly, int_order_overhead_allocation"]
        end
        subgraph FJORCH["orchestration/tenants/fine_japan/"]
            O1[crm_sync, crm_writeback_assets]
            O2[approach_script_generation]
            O3["hug webhook consumer"]
            O4["config.py: sheet URLs, Sapo domain, worker URL"]
        end
        FJSEED["seeds/tenants/fine_japan/<br/>seed_cashflow_budget, seed_cash_allocation_policy,<br/>seed_channel_targets, seed_sku_regimen_config,<br/>seed_sku_alias_manual, seed_action_scenario_registry"]
    end
    CORE["core/"] --> FJDBT
    PACKS["packs/"] --> FJDBT
    CORE -. "⚠ hook" .-> OH
    CORE -. "⚠ hook" .-> US
    CORE -. "⚠ hook" .-> CRMD
    O4 -. "cấu hình cho" .-> CONN["connectors sapo_v2, sheets"]
```

### Tenant hooks (core/pack đang phụ thuộc tenant, ghi trong allowlist)

| Model lõi | Phụ thuộc FJ | Hướng xử lý |
|---|---|---|
| `fact_order_costs` | ref `int_order_overhead_allocation` | Tách phần overhead ra tenant |
| `fact_order_economics` | ref `int_order_overhead_allocation` | Như trên |
| `dim_staff` | ref `stg_crm__app_user` | Tách enrich CRM ra tenant |
| `mart_data_quality` | ref `fact_us_shipment_economics` | Tách check US ra tenant |
| `dim_customers` | Logic SQL: CROSSBORDER dùng đơn kênh US (không phải cạnh ref, checker không thấy) | Quyết định nghiệp vụ + taxonomy |

`int_customer_economics` và các model đọc `fact_order_costs` phụ thuộc tenant gián tiếp; khi tách phần overhead, các model này đổi theo.

Danh sách đầy đủ là các mục tenant hook trong `scripts/checks/boundary_allowlist.yaml`, sinh từ `depends_on` của manifest.

## 11. Serving và người tiêu thụ

```mermaid
flowchart LR
    DBT["dbt models có get_rolling_location()"] --> ROLL["export/marts/rolling/&lt;model&gt;/&lt;model&gt;_&lt;ts&gt;.parquet"]
    ROLL --> RR["refresh_rolling.py<br/>(GC giữ 3 bản, kiểm tra schema drift)"]
    RR --> BS["bootstrap_serving_views.py"]
    BS --> OLAP[("serving/olap.duckdb<br/>main.&lt;name&gt; + main_marts.&lt;name&gt;")]
    ROLL --> RP["publish_rill_assets.py<br/>(allowlist 11 bảng)"] --> RILLF["RILL_EXPORT_ROOT/&lt;name&gt;.parquet"] --> RL[Rill]
    OLAP --> MB["Metabase (~50 bảng)"]
    OLAP --> EV["Evidence (9 bảng)"]
    OLAP --> DV["detailView"]
    OLAP --> CRMAPP["CRM app"]
    WH[("sapo_warehouse.duckdb<br/>model non-rolling")] -. "cần xác minh cách đọc" .-> CRMAPP
```

| Người tiêu thụ | Đọc từ | Quyền |
|---|---|---|
| Metabase | `serving/olap.duckdb` (`main_marts.*`) | read-only |
| Evidence | `evidence/sources/datalake/connection.yaml` → serving | read-only |
| Rill | `RILL_EXPORT_ROOT/<name>.parquet` | read-only |
| detailView | `serving/olap.duckdb` (`read_only=True`) | read-only |
| CRM | serving + (cần xác minh) model non-rolling | read-only với warehouse; ghi SQLite riêng |

Tên các bảng này là hợp đồng public; danh sách nằm ở `scripts/checks/public_models.yaml`.

## 12. Ranh giới Python và container ✅

```mermaid
flowchart TB
    subgraph DPC["container data_platform"]
        ORCH["orchestration/"]
        ING["ingestion/"]
        TRF["transformation/"]
        SCR["scripts/"]
    end
    subgraph CRMC["container crm"]
        CRMSRC["crm/src, crm/ops"]
        CRMDB[("CRM SQLite")]
    end
    subgraph OTHER["container khác"]
        MBC[metabase]
        EVC[evidence]
        RLC[rill]
        DVC[detail_view]
    end
    ORCH -->|import| ING
    ORCH -->|"dbt CLI"| TRF
    ORCH -->|"subprocess"| SCR
    SCR -. "import (ops tooling)" .-> ORCH
    ORCH -->|"HTTP crm:8090"| CRMSRC
    ORCH -->|"đọc SQLite (writeback)"| CRMDB
    CRMSRC -. "❌ cấm import orchestration/ingestion/transformation" .-x ORCH
    DVC -. "❌ cấm import" .-x ORCH
```

| Quy tắc | Cưỡng chế |
|---|---|
| `crm/`, `detailView/` không import `orchestration`, `ingestion`, `transformation` | `check_boundaries.py` (ast) |
| `ingestion/` không import `orchestration` | `check_boundaries.py` |
| `orchestration/connectors/**` không chứa URL/domain cứng | `check_boundaries.py` |
| Giao tiếp CRM ↔ orchestration chỉ qua HTTP và file export | Review + quy tắc import |
