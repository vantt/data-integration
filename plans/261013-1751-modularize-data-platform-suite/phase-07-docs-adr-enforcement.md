---
phase: 7
title: "Tài liệu ranh giới, ADR, cưỡng chế, dọn shadow"
status: pending
priority: P2
effort: "1.5d"
dependencies: [1, 2, 3, 4, 5, 6]
---

# Phase 7: Docs, ADR, enforcement, cleanup

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng trong `docs/architecture/modules.md` (bản sống trên nhánh; sơ đồ authority/boundary, giao diện, quyền ghi). Trong lúc làm: tài liệu đi cùng commit với code, không dồn về phase 7. Phase chỉ được coi là xong khi tài liệu dưới đây khớp với code thật.
>
> **Tài liệu phải cập nhật trong phase này:** ADR 015/016, `AGENTS.md`, `docs/README.md`, `docs/architecture/overview.md`; rà toàn bộ `docs/architecture/modules.md` lần cuối so với code.

## Goal

Ghi lại kiến trúc module đã thành hình, làm cho kiểm tra ranh giới chạy bằng một lệnh, và xoá toàn bộ bản sao dữ liệu shadow.

## Files to Create / Modify

- Create: `docs/decisions/015-module-boundaries.md` — bucket, ma trận phụ thuộc, kernel (các file generic giữ nguyên vị trí), connector package, tenant overlay, tenant hooks.
- Create: `docs/decisions/016-taxonomy-module.md` — taxonomy Đợt 1 là **đặc tả + dời seed, không tách macro** (quyết định 14/10): `TAXONOMY.md` (vị trí + hash từng khối), `check_taxonomy_inventory.py`, seeds taxonomy, `seed_paths.py`, Known divergences; bộ máy phân loại (luật là dữ liệu, nhãn riêng + mã chuẩn) là plan sau Đợt 1, thiết kế ở `docs/architecture/taxonomy-engine.md`.
- Create: `docs/decisions/017-packs-and-tenants.md` — logic là pack, dữ liệu/cấu hình là tenant; chỉ US shipment riêng FJ; CRM, HUG, finance, sales_playbook là pack; lõi giữ doanh thu, finance giữ chi phí và lợi nhuận; số liệu do nguồn cung cấp thuộc lõi, chọn/đối chiếu/tính chi phí thuộc finance; connector lấy dữ liệu, pack dùng dữ liệu, gặp nhau ở `std_*`; hook lõi → pack/tenant và lối ra `pack_ref` sau Đợt 1.
- Modify: `docs/architecture/std-layer-conventions.md` (đã cập nhật ở phase 3; rà lại), `docs/architecture/overview.md` (vị trí cdm/core/packs/tenants trong 7-hop), `AGENTS.md` (Architecture Map, Multi-Project Structure), `transformation/AGENTS.md`, `orchestration/README.md`, `docs/README.md`, `docs/decisions/README.md`.
- Modify: `scripts/checks/check_boundaries.py` — thêm rule **dbt-seed: lõi không đọc seed tenant**, kèm 3 dòng allowlist có lý do (`seed_channel_targets` → `dim_channel_targets`, `seed_sku_regimen_config` → `int_customer_sku_supply_tracking`, `seed_sku_alias_manual` → `dim_sku_alias`); lối ra sau Đợt 1 cùng `pack_ref` (seed mặc định rỗng đúng cột ở lõi, tenant ghi đè). Có test cho rule mới.
- Modify: 6 reader `ingestion/src/gsheet_*.py` (targets, marketing_spend, us_shipment_prices, team_config, overhead_classification, budget) — bỏ URL mặc định viết cứng; báo lỗi rõ khi thiếu `SOURCES__SPREADSHEET_URL__<NAME>`. `sheets_modified_sensor.py` đọc chung các biến `SOURCES__SPREADSHEET_URL__*` thay vì giữ 3 URL riêng trong `tenants/fine_japan/config.py` (mỗi URL khai báo một nơi). Ingestion không import `orchestration.tenants`. `.env.docker.example` ghi đủ tên biến; README tenant ghi đây là cấu hình Fine Japan. Prod `.env.docker` đã có đủ 6 biến (session thực thi kiểm tên, không xem giá trị), nên prod không đổi hành vi. Kiểm trong shadow: thiếu một biến → lỗi rõ ràng.
- Create: `scripts/checks/run-all.sh` — boundaries + `dbt parse` + `dagster definitions validate` + pytest (trong shadow); ghi vào `AGENTS.md` là bước bắt buộc trước commit.
- Modify: `plans/260705-1704-modular-monorepo-boundary-hardening/plan.md` — ghi phase 2, 3, 6 đã được thay bởi plan này; phase 0, 1, 4, 5 (đóng gói image, GHCR, dev/prod) là bước tiếp theo.

## Tasks & Steps

1. Viết ADR/doc từ trạng thái code thật (`modules.yaml`, `dbt_project.yml`, `model_buckets.yaml`, allowlist).
2. Kiểm tra mọi link trong doc mới trỏ tới file tồn tại.
3. Chạy `scripts/shadow/cleanup.sh`; xoá hai worktree (`git worktree remove`).
4. Đối chiếu Acceptance Criteria trong `plan.md`, cập nhật status.

Rule mới và việc dời URL là thay đổi code: chạy gate M trước khi deploy như các phase khác (golden không đổi).

## Verification

- `scripts/checks/run-all.sh` pass trên main.
- **Dữ liệu** shadow (lake-*, golden, inventory, bản sao backup — có PII) không còn tồn tại; `git worktree list` chỉ còn checkout prod.
- **Công cụ** shadow không bị xoá: `deps` (môi trường dbt/Python mà `run-all.sh` dùng) được tách khỏi `$SHADOW_ROOT` sang một vị trí lâu dài không chứa dữ liệu (vd. `~/.cache/fg-dw-tools/deps`, cấu hình qua biến môi trường, ghi trong `scripts/shadow/README.md`), để `run-all.sh` vẫn chạy được trên main sau khi dọn. Đúng nguyên tắc harness §9.4: công cụ dùng lâu dài, dữ liệu shadow dùng theo đợt. (Sửa 14/10/2026: hai tiêu chí cũ "run-all pass" và "xoá toàn bộ shadow" mâu thuẫn nhau.)
- Plan kế tiếp (cơ chế pack) dựng lại lake shadow ở phase 1 của nó.
