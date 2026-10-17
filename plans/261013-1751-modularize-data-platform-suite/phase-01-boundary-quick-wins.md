---
phase: 1
title: "Ranh giới nhanh: cắt import chéo, sửa macro hỏng, kiểm tra ranh giới tự động"
status: completed
priority: P1
effort: "0.5d"
dependencies: [0]
---

# Phase 1: Boundary quick wins

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng trong [architecture-boundaries.md](architecture-boundaries.md) (sơ đồ authority/boundary, giao diện, quyền ghi). Trong lúc làm: tài liệu đi cùng commit với code, không dồn về phase 7. Phase chỉ được coi là xong khi tài liệu dưới đây khớp với code thật.
>
> **Tài liệu phải cập nhật trong phase này:** tạo `docs/architecture/modules.md` từ `architecture-boundaries.md` (bản sống của kiến trúc module, các phase sau cập nhật từng mục); §12 ranh giới Python/container; `scripts/checks/README.md` (các quy tắc của `check_boundaries.py` và cách thêm allowlist).

## Goal

Cắt import chéo còn lại giữa component và dựng `check_boundaries.py` (không thêm dependency) trước khi di chuyển file lớn.

## Context (đã kiểm chứng)

- `crm/ops/backup_crm.py:254-258` import `send_lark_alert` không tồn tại; `_alert()` chỉ được gọi từ CLI `main()` (L234-246). Prod chạy backup qua `POST /admin/backup` (`crm/src/adapters/inbound/http/admin_handler.py:307-334`) và khi lỗi trả 500 → asset `crm_backup` raise → `failure_alerting` gửi Lark. Prod **đã** được cảnh báo; chỉ đường CLI bị mất cảnh báo.
- `transformation/macros/duckdb__create_table_as.sql` thiếu dòng mở `{% macro ... %}` (L1) nhưng có `{% endmacro %}` (L51); không model nào dùng contract.
- `pipeline_runner.run_pipeline` không có default `dataset_name`; chỉ `setup_dlt_env` có (không ảnh hưởng hành vi). Không cần sửa.

## Files to Create / Modify

- Modify: `crm/ops/backup_crm.py` — bỏ import `orchestration`; `_alert()` in ra stderr với mức lỗi rõ ràng. Không thêm credential nào cho CRM.
- Modify hoặc Delete: `transformation/macros/duckdb__create_table_as.sql` — commit riêng. Trước hết xác định dbt đang làm gì với file này (đọc log `dbt parse` trong shadow); nếu đang bị bỏ qua thì xoá, nếu đang được dùng một cách nào đó thì sửa đúng cú pháp. Điều kiện: SQL trong `target/run` không đổi.
- Create: `scripts/checks/check_boundaries.py` (stdlib `ast` + đọc `manifest.json`):
  1. Python: `crm/`, `detailView/` không import `orchestration|ingestion|transformation`; `ingestion/` không import `orchestration`.
  2. dbt: ma trận phụ thuộc theo bucket (bucket = thư mục gốc của `original_file_path`; trước phase 2 dùng map tạm theo tên model sinh từ bảng bucket của scout).
  3. Seeds: không có hai file `.csv` trùng basename dưới `transformation/seeds/`.
  4. Không có file `.sql` nằm ngoài các thư mục bucket đã biết (áp dụng sau phase 2).
  Vi phạm hiện có ghi vào `scripts/checks/boundary_allowlist.yaml` (sinh từ manifest, có cột lý do); check fail khi có vi phạm **mới**.

## Verification

- Gate M (phase 0).
- `check_boundaries.py` pass; thêm thử `import orchestration` vào một file trong `crm/` → fail; thêm thử một ref core → `stg_*` → fail; tạo thử seed trùng tên → fail.
- `python crm/ops/backup_crm.py` với đích backup không ghi được (trong shadow) → in lỗi ra stderr, exit code khác 0.

## Rollback

Revert commit; không có relation hay seed mới.

## Kết quả thực hiện (2026-10-13)

**Trạng thái: hoàn thành trên nhánh, chưa deploy.** Commit `b617c072`, `3b3520fa`, `4721817d`.

| Việc | Kết quả |
|---|---|
| Macro hỏng `duckdb__create_table_as.sql` | Xoá. Manifest chỉ có macro của adapter (`macro.dbt_duckdb.duckdb__create_table_as`); compiled SQL 162 model không đổi. `add_fk_constraint` cũng là macro chết (không model nào dùng); để lại, ghi vào roadmap. |
| Import chéo CRM → orchestration | Bỏ `_alert()`; CLI giữ stderr + exit 1 (đã chạy thử trong container CRM không mạng). Prod vẫn được cảnh báo qua Dagster failure sensor. |
| `check_boundaries.py` | 7 luật: `py-import`, `py-scan`, `dbt-bucket`, `dbt-ref`, `dbt-source`, `seed-duplicate`, `connector-url`. Chạy trên host (cần `crm/`, `detailView/`). 22 unit test. |
| `model_buckets.yaml` | 172 model (gồm 10 model đang tắt: Facebook ×9, `src_sapo_v2_customer_groups`). |
| Allowlist | 24 vi phạm có lý do và hướng thoát: 15 core đọc staging, 4 tenant hook, 2 MISA, 3 Shopee. |
| Gate M | PASS (golden, dbt inventory, compiled SQL, boundaries, dagster inventory, pytest, lake trống). |
| Tài liệu | `docs/architecture/modules.md` (bản sống), `scripts/checks/README.md`, `docs/README.md`. |

**Quyết định thiết kế phát sinh:** COGS và tồn kho thuộc **core**, không phải pack, vì các fact lõi phụ thuộc vào chúng. Packs còn: `finance` (+`int_misa_sales_lines`, `dim_gl_account`), `marketplace`, `facebook_ads`, `facebook_messenger`. `int_order_snapshots_ranked` thuộc `connector:sapo_v2` (đọc thẳng raw).

**Phát hiện:** phép thử phản chứng đầu tiên pass giả vì container shadow không mount `crm/` → đã thêm luật `py-scan` và chạy checker trên host. `.gitignore` bỏ qua `check_*.py` → thêm ngoại lệ cho `scripts/checks/check_boundaries.py`.

**Deploy:** gộp với phase 2 (phase 1 chỉ thêm công cụ, xoá file không có tác dụng, và sửa CLI CRM không chạy trên prod), theo runbook `docs/operations/deployment.md` § Refactor deploys.
