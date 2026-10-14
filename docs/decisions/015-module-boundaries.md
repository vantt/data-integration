# ADR-015: Ranh giới module (bucket, ma trận phụ thuộc, kernel, connector, tenant, cưỡng chế)

> **Trạng thái:** Accepted
> **Ngày:** 2026-10-14
> **Tham chiếu:** [`docs/architecture/modules.md`](../architecture/modules.md) (thiết kế sống), [`scripts/checks/README.md`](../../scripts/checks/README.md), [`orchestration/connectors/README.md`](../../orchestration/connectors/README.md), [ADR-016](./016-taxonomy-module.md), [ADR-017](./017-packs-and-tenants.md), plan `plans/261013-1751-modularize-data-platform-suite/` (Đợt 1)

## Bối cảnh

Suite chạy cho Fine Japan lớn lên thành một dbt project và một Dagster code location không có ranh giới bên trong:

1. **Core đọc thẳng staging của nguồn**: 15 cạnh `ref` từ `dim_*`/`fact_*` vào `stg_sapo_v2_*`, `stg_teams`, `src_sapo_v2_orders`... Thêm nguồn thứ hai (Haravan, Nhanh.vn) sẽ phải sửa core.
2. **Import chéo giữa component**: `crm/` import `orchestration`, `definitions.py` import từng asset theo tên, thư mục `models/{staging,intermediate,marts}/` trộn logic của mọi nguồn và mọi sản phẩm.
3. **Giá trị riêng Fine Japan nằm trong code chung**: URL Google Sheet, domain Sapo, endpoint CRM viết cứng làm mặc định.
4. Mục tiêu dài hạn (roadmap) là đóng gói để cài cho doanh nghiệp thứ hai, trong khi hệ thống **vẫn chạy hằng ngày** và không được đổi một con số hay tên bảng public nào.

## Quyết định

### 1. Mỗi dbt model thuộc đúng một bucket, nằm trong thư mục của bucket

`scripts/checks/model_buckets.yaml` là nguồn duy nhất: 182 model (172 bật, 10 tắt), bucket `connector:<x>`, `cdm`, `core`, `pack:<p>`, `tenant:<t>`, `monitoring`. File nằm ở `transformation/models/<module>/<layer>/`. **Layer** (`staging`, `intermediate`, `marts`) quyết định schema, materialization và tag qua YAML anchor trong `dbt_project.yml`; **module** chỉ quyết định quyền sở hữu, nên dời model giữa module không đổi relation.

### 2. Ma trận phụ thuộc

| Bucket của model | Được đọc |
|---|---|
| `connector:<x>` | `connector:<x>`, seed dùng chung, source của nó |
| `cdm` | `connector:*`, `cdm`, seed dùng chung |
| `core` | `cdm`, `core`, seed dùng chung |
| `pack:<p>` | `cdm`, `core`, `pack:<p>`, connector khai báo trong `pack_connectors[<p>]`, seed tenant |
| `tenant:<t>`, `monitoring` | mọi thứ (seed tenant: chỉ của chính `<t>`) |

`cdm/` (các view `std_*`, pass-through trung thành + `source_system`) là **cửa duy nhất** từ connector vào core. Hợp đồng cột của `std_*` kiểm bằng test `std_column_contract` mức **warn**; `contract: enforced` chưa bật (Đợt 3). Đọc source dbt chỉ dành cho connector và tenant.

### 3. Hook: lõi đọc pack hoặc tenant chỉ qua allowlist

Ma trận **không bao giờ** cho phép core → pack, core → tenant, hay core → seed tenant. Chỗ chưa tách được là một mục trong `scripts/checks/boundary_allowlist.yaml` kèm **lý do và lối ra**. Allowlist **sinh từ manifest** và import Python (`check_boundaries.py --write-allowlist`, giữ lý do cũ), không viết tay; mục không còn xảy ra cũng làm check fail, nên nợ đã trả phải xoá trong cùng commit. Hiện có 36 mục: 16 `dbt-ref`, 3 `dbt-seed`, 12 `dbt-source`, 5 `orch-import` (chi tiết và lối ra: [modules.md mục 3](../architecture/modules.md#3-ma-trận-phụ-thuộc-giữa-các-module-dbt-)).

### 4. Kernel giữ nguyên vị trí và không biết module theo tên

Kernel là phần dùng chung: `orchestration/definitions.py`, `module_registry.py`, `job_support.py`, `assets/{dbt,serving,rill,...}.py`, `sensors/`, `ops/`, `asset_checks/`, `notifications/`, cùng `ingestion/src/utils/` (`pipeline_runner`, `seed_paths`). Các file này **không dời** (nhiều đường dẫn tính theo `__file__`: `ops/purge_runs.py`, `asset_checks/sla_loader.py`, `ops/system_backup.py`) và được nhận diện bằng tài liệu. Kernel nạp connector, pack, tenant từ `orchestration/config/modules.yaml` qua `module_registry.py`; không import chúng theo tên.

### 5. Mỗi connector là một package

`orchestration/connectors/<id>/` (5 connector: `sapo_v2`, `shopee`, `misa_amis`, `sheets`, `hug`) export list/dict thuần, không có lớp registry: `ASSETS`, `CHECK_ASSET_DEFS`, `NIGHTLY_ASSETS`, `DIGEST_ASSETS`, `DIGEST_DISPLAY`, `JOB_MAX_RUNTIME`, `DBT_SOURCE_KEYS` (`__init__.py`) và `JOBS`, `SCHEDULES`, `SENSORS` (`jobs.py`). Bỏ một connector chỉ cần xoá id khỏi `modules.yaml`. Connector chỉ ghi `data_lake/<source>_raw/`; tên asset key, job, schedule, sensor không đổi khi dời code (trạng thái bật/tắt trên prod gắn với tên).

### 6. Tenant overlay

Phần riêng của một doanh nghiệp nằm ở `transformation/models/tenants/<t>/`, `transformation/seeds/tenants/<t>/` và `orchestration/tenants/<t>/config.py` (đọc qua `orchestration.tenants.setting(name)`, fail closed); URL Google Sheet chỉ ở biến môi trường `SOURCES__SPREADSHEET_URL__<NAME>`. Ranh giới giữa pack và tenant: [ADR-017](./017-packs-and-tenants.md).

### 7. Cưỡng chế bằng máy, chạy trước mỗi commit

`scripts/checks/check_boundaries.py` kiểm các luật `py-import` (`crm/`, `detailView/` không import code platform; `ingestion/` không import `orchestration`), `orch-import`, `dbt-bucket`, `dbt-path`, `dbt-ref`, `dbt-source`, `dbt-seed`, `seed-duplicate`, `connector-url`, `pack-url`; mỗi luật có test fail trên vi phạm cài sẵn. `scripts/checks/run-all.sh` chạy `dbt parse` + check này + `dagster definitions validate` + pytest trong một lệnh và là **bước bắt buộc trước commit** (`AGENTS.md`). Thay đổi dời model hoặc sửa SQL còn phải qua gate shadow `scripts/shadow/gate.sh M|S` (golden, inventory dbt/Dagster) trước khi deploy.

## Hệ quả

- Thêm nguồn mới chỉ chạm `connectors/<id>/` và các view `std_*`; core không đổi.
- Mọi đường vượt ranh giới hiện hình trong một file có lý do và lối ra; không thể thêm cạnh mới mà không ai thấy.
- Vẫn là **một** dbt project và **một** code location: chưa bật/tắt được pack (cần `pack_ref`, sau Đợt 1), chưa đóng gói image (Đợt 2).
- `check_boundaries.py` cần `crm/` và `detailView/`, nên chạy bằng python của host, không trong container.

## Alternatives Rejected

- **Tách thành nhiều dbt project hoặc dbt package ngay**: cần `contract`, cross-project ref và đổi selection Dagster; quá rủi ro khi hệ thống đang chạy hằng ngày. Để Đợt 3.
- **Bật `contract: enforced` cho `std_*`**: chặn build khi kiểu lệch nhẹ; chọn test mức warn trước.
- **Dời các file kernel vào `orchestration/kernel/`**: làm hỏng đường dẫn tính theo `__file__`, không thêm giá trị kiểm chứng được.
- **Lớp registry/plugin cho connector**: list thuần đủ cho 5 connector; Dagster Components cân nhắc khi có ≥3 connector cùng mẫu.
- **Allowlist viết tay**: dễ phình và lệch thực tế; sinh từ manifest và fail trên mục cũ.

## Khi nào xem xét lại

- Khi có doanh nghiệp thứ hai hoặc connector thứ hai cho cùng loại dữ liệu (Haravan): kiểm lại ma trận và `std_*`.
- Khi `pack_ref` có (sau Đợt 1): các mục allowlist pack hook và `dbt-seed` phải giảm; ma trận có thể cho phép core → pack qua macro.
- Khi đóng gói image (Đợt 2) hoặc tách dbt package (Đợt 3).
