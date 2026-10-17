---
phase: 2
title: "Bố cục module cho dbt (chỉ di chuyển file, relation và config giữ nguyên)"
status: completed
priority: P1
effort: "2.5d"
dependencies: [0, 1]
---

# Phase 2: dbt module layout

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng trong `docs/architecture/modules.md` (bản sống trên nhánh; sơ đồ authority/boundary, giao diện, quyền ghi). Trong lúc làm: tài liệu đi cùng commit với code, không dồn về phase 7. Phase chỉ được coi là xong khi tài liệu dưới đây khớp với code thật.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/architecture/modules.md` §3, §5–§8 (bố cục thư mục dbt thật, `model_buckets.yaml`); `transformation/docs/MODELS.md`, `transformation/AGENTS.md`; skills `.skills/data-pipeline/*`, `.skills/analytics-design/*` (nơi tạo model mới).

## Goal

Sắp xếp `transformation/models/` theo module trong **một** dbt project (quyết định: tách thư mục trước, đóng gói image sau qua plan 260705), mà relation, schema, alias, location, toàn bộ config, tag quyết định selection và selection của từng job Dagster giữ nguyên.

## Context (đã kiểm chứng)

- Schema đến từ `+schema` theo folder (`staging/` → `main_staging`, `marts/` → `main_marts`, `intermediate/` → `main`); không có override `generate_schema_name`.
- `marts:` còn mang `+on_schema_change: sync_all_columns`, `+tags: ["olap"]`, materialized `external`.
- Asset key dbt mặc định gồm schema đã cấu hình (vd. `AssetKey(["marts","fact_order_returns"])` ở `orchestration/definitions.py:137`); đổi schema là đổi asset key.
- Ba chỗ **tạo trước thư mục rolling bằng cách quét tên thư mục**: `orchestration/assets/dbt.py:113-122`, `scripts/ensure_dbt_directories.py:21` (chạy lúc container start), `transformation/scripts/run_dbt.py:74`.
- 16 model incremental: 12 ở `staging/` (`src_sapo_v2_*` ×10, `src_hug_*` ×2) và 4 ở `marts/core` (`dim_customers_base`, `int_customer_metrics`, `int_customer_entry_attributes`, `int_customer_discount_metrics`).
- 51 file trong `.skills/` và `docs/` trỏ tới `models/staging|marts|intermediate`, gồm template agent `.skills/data-pipeline/templates/model/schema-yml-template.yml:3`.

## Bố cục đích

```text
models/connectors/<sapo_v2|shopee|misa|gsheet|hug|crm|facebook_ads|facebook_messenger>/
models/cdm/                      # staging/standard/std_*
models/core/{dims,facts,customer,product,cogs,inventory}/
models/packs/{finance,marketplace,facebook_ads,facebook_messenger}/
models/tenants/fine_japan/       # tạo rỗng ở phase này, điền ở phase 6
models/monitoring/
```

Bucket của từng model đã có trong `scripts/checks/model_buckets.yaml` (phase 1, nguồn duy nhất). Phase này di chuyển model **không thuộc tenant** vào thư mục của bucket; model `tenant:fine_japan` để phase 6.

## Files to Create / Modify

- Move (git mv): mọi `.sql` theo `model_buckets.yaml`; tách `schema.yml` theo thư mục mới (giữ nguyên nội dung test/doc).
- Modify: `transformation/dbt_project.yml` — config cho từng thư mục mới tái tạo **chính xác** config cũ; ngoại lệ đặt ở cấp model. Seed chưa di chuyển ở phase này.
- Modify: `transformation/models/sources.yml` → tách thành `models/connectors/<source>/_sources.yml` (nội dung giữ nguyên).
- Modify: `orchestration/assets/dbt.py`, `scripts/ensure_dbt_directories.py`, `transformation/scripts/run_dbt.py` — danh sách model rolling lấy từ `manifest.json` (model có `config.location` chứa `/rolling/`), không theo tên thư mục.
- Modify: `.skills/data-pipeline/*`, `.skills/analytics-design/*`, `transformation/docs/*.md`, `transformation/AGENTS.md` và các file trong `docs/` trỏ đường dẫn cũ (danh sách từ `grep -rl "models/staging\|models/marts\|models/intermediate" .skills docs transformation`).
- Create: `scripts/shadow/move_models.py` — đọc `model_buckets.yaml`, `git mv`, tách `schema.yml`.

## Tasks & Steps

1. Xuất inventory main (phase 0).
2. Sửa ba chỗ quét thư mục sang manifest **trước** khi di chuyển, chạy Gate M (phải sạch ngay trên bố cục cũ).
3. Chạy `move_models.py`, cập nhật `dbt_project.yml`.
4. Lặp `dbt parse` → `dbt_inventory diff` đến khi chỉ khác các trường trong danh sách bỏ qua (`original_file_path`, `fqn`, `path`).
5. `dagster_inventory diff`: asset keys và tập `unique_id` của từng job giống hệt.
6. Build lake-B, Gate M; kiểm tra lake trống (rolling bị xoá) build thành công.
7. Cập nhật skills/docs; `check_boundaries.py` bật quy tắc "không `.sql` ngoài thư mục bucket".

## Verification

- Gate M sạch; build trên lake trống sạch.
- Log dbt lần build đầu trên lake-B: không model nào trong 16 model incremental bị `create table` lại.
- `dbt ls --select +tag:mart` và `dbt ls --select tag:hourly` cho cùng tập trên main và branch.
- Số test trong manifest bằng nhau.

## Rollback

Revert commit; vì relation không đổi nên không có gì cần dọn trong warehouse. Manifest được tạo lại khi container start.

## Kết quả thực hiện (2026-10-13)

**Trạng thái: hoàn thành trên nhánh, chưa deploy.** Commit `52f31693` (thư mục rolling theo manifest), `85fffa78` (dời model).

| Việc | Kết quả |
|---|---|
| 3 chỗ quét thư mục cố định | Gom về `transformation/scripts/rolling_dirs.py` (manifest: model `external` + `get_rolling_location`; không có manifest thì quét toàn bộ `models/`). Dùng ở container start, trong `sapo_dbt_assets` **sau** `dbt parse`, và `run_dbt.py` (trước đây tạo sai đường dẫn, thiếu `rolling/`). Chạy thật op Dagster trên lake trống: tạo đủ 75 thư mục. |
| Bố cục | `models/<module>/<layer>/`: 134 model dời (connectors 47, cdm 14, core 61, packs 12). 37 model tenant + 1 monitoring giữ chỗ. |
| Config dbt | Mỗi layer định nghĩa một lần bằng YAML anchor (`&layer_staging`, `&layer_intermediate`, `&layer_marts`), module tái sử dụng → relation/schema/tags không đổi. |
| Properties YAML | Tách theo khối văn bản (giữ comment) vào `_<module>__models.yml`; nguồn connector vào `connectors/<source>/staging/_sources.yml`. |
| Checker | Thêm luật `dbt-path`; allowlist 61 (24 phụ thuộc + 37 model tenant chưa dời). |
| Gate | Thêm bước chạy job con dbt **qua Dagster**; pytest chạy lại một lần khi fail, báo `FLAKY`. Gate M: PASS. |
| Tài liệu | `docs/architecture/modules.md` §2b (cây thư mục thật, quy tắc), `transformation/AGENTS.md`, `transformation/docs/*`, skill `.skills/data-pipeline/*` (checklist, template), 25 tài liệu analytics-handbook (đường dẫn model). Nhật ký lịch sử (journals, changelog, lessons-learned) giữ nguyên. |

**Phát hiện:**

- dagster-dbt gửi selection cho dbt bằng `fqn` (vd. `sapo_warehouse.marts.sales.fact_order_returns`); sau khi dời thành `sapo_warehouse.core.marts.sales.fact_order_returns`. Code server phải nạp manifest parse từ bố cục mới; runbook deploy dừng/khởi động lại container nên lệnh start tự `dbt parse` trước `dagster dev`.
- dbt cắt khoảng trắng cuối file properties: khối YAML nằm cuối file mất newline cuối của `description` dạng `>`. Inventory so `description` đã strip; script dời luôn để một dòng trống sau mỗi khối.
- `test_concurrent_writes_no_lock_error` fail khoảng 1/4 số lần chạy (cả baseline) → gate chạy lại một lần.

**Deploy:** chưa thực hiện. Đề xuất deploy gộp phase 0–2 theo runbook (dừng `data_platform` vài phút, ngoài khung 02:30–04:00), sau đó theo dõi một vòng nightly trước khi deploy phase tiếp theo.
