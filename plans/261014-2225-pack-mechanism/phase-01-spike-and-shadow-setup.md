---
phase: 1
title: "Dựng lại shadow và spike cơ chế dbt"
status: pending
priority: P1
effort: "0.25d"
dependencies: []
---

# Phase 1: Dựng lại shadow + spike

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng trong `docs/architecture/modules.md`. Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** báo cáo spike `plans/261014-2225-pack-mechanism/reports/spike-dbt-pack-switch.md` (kết quả từng câu hỏi, lệnh đã chạy, phiên bản dbt). Không sửa tài liệu trong repo; kết luận spike được chép vào `docs/architecture/modules.md` §8 ở phase 2.

## Điều kiện bắt đầu

- Đợt 1 đã đóng: phase 6 và 7 của plan `261013-1751` đã deploy, `main` chứa allowlist có rule `dbt-seed` (3 dòng lõi → seed tenant) và `scripts/checks/run-all.sh`. Nếu phase 7 chưa xong thì plan này chờ.
- Phase 7 Đợt 1 xoá shadow và worktree, nên phase này dựng lại theo `docs/operations/refactor-safety-harness.md` §9.1 và §9.4.

## Việc làm

1. Tạo worktree nhánh `feat/pack-mechanism` từ `main` (ví dụ `/home/vantt/app/fg-dw-pack`) và worktree baseline tại `main` (`/home/vantt/app/fg-dw-baseline`). Không đụng checkout prod.
2. Dựng shadow từ hai backup mới nhất (`prepare-shadow.sh`), build `lake-A` từ baseline, capture golden, export `dbt-main.json`/`dagster-main.json` (harness §9.2). Gọi gate với `BRANCH_DIR` trỏ worktree mới.
3. Spike trên một nhánh nháp trong worktree (không commit vào nhánh chính), dbt-duckdb 1.10.1 như prod (`ingestion/requirements.txt:15`), chạy trong container shadow:

| # | Câu hỏi | Cách thử | Kết quả mong đợi |
|---|---|---|---|
| a | `ref()` nằm trong `{% if var(...) %}` cho lineage khi điều kiện đúng và **không** tạo phụ thuộc khi sai | Macro `pack_ref` thử trên một model nháp; `dbt parse` hai lần với `--vars` khác nhau; xem `depends_on.nodes` trong manifest | Đúng: cạnh tới model pack; sai: không có cạnh, parse không lỗi khi model pack bị tắt |
| b | `+enabled: "{{ ('finance' in var('enabled_packs')) \| as_bool }}"` dưới `models: sapo_warehouse: packs: finance:` tắt được cả thư mục | `dbt ls --resource-type model --vars '{enabled_packs: []}'` | Không còn model nào của `packs/finance`; `config.enabled` trong manifest là bool |
| c | Test đơn lẻ trong `transformation/tests/` trỏ vào model đã tắt (6 file: `assert_no_promo_in_overhead_costs`, `assert_overhead_accounts_classified`, `assert_overhead_allocation_closure`, `assert_promo_account_not_in_keep_pool`, `assert_shopee_net_settlement_matches_total_paid`, `assert_shopee_no_platform_service_double_count`) | Như b | dbt cảnh báo và bỏ test, không lỗi. Nếu lỗi: phase 2 dời 6 file vào `tests/packs/<pack>/` và thêm `data_tests: sapo_warehouse: packs: <pack>: +enabled` |
| d | Seed chỉ có dòng tiêu đề + `+column_types` tạo bảng 0 dòng đúng kiểu | Seed nháp `seed_x__default.csv` | Bảng 0 dòng, kiểu đúng như khai báo |
| e | Quan hệ rỗng `SELECT CAST(NULL AS <type>) AS <col> ... WHERE FALSE` dùng được ở mọi chỗ lõi `JOIN`/`LEFT JOIN` | Chạy SQL thử trên lake-A | Chạy được, kiểu đúng |
| f | Đổi `--vars` làm dbt parse lại toàn bộ (không dùng manifest cũ một phần) | Hai lần `dbt parse` liên tiếp với vars khác nhau | Manifest phản ánh vars mới |
| g | `vars` trong `dbt_project.yml` khai báo danh sách (`enabled_packs: [crm, ...]`) và bị `--vars` ghi đè | Như a | Ghi đè đúng |

## Dự phòng (khi a hoặc b không đạt)

- Nếu (a) không đạt: thay `pack_ref` bằng **hai bản model** cho mỗi model lõi có hook, cùng tên relation qua `alias`, mỗi bản `config(enabled=...)` ngược nhau (một bản `ref()` pack, một bản cột NULL). Báo user trước khi đi tiếp vì số file tăng và DRY kém hơn; ước lượng phase 3–4 tăng ~0.5d.
- Nếu (b) không đạt với `as_bool`: đặt `config(enabled=pack_enabled('<pack>'))` trong từng model pack bằng một lệnh sửa hàng loạt (khoảng 50 file theo `find transformation/models/packs -name '*.sql'`), cùng commit phase 2.

## Files

- Create: `plans/261014-2225-pack-mechanism/reports/spike-dbt-pack-switch.md`.
- Không sửa file nào trong repo; nhánh nháp của spike bị xoá sau phase.

## Verification

- Gate trống chạy được: `BRANCH_DIR=<worktree> scripts/shadow/gate.sh M` trên nhánh chưa đổi gì → PASS (chứng minh shadow dựng đúng).
- Báo cáo spike trả lời đủ 7 câu, mỗi câu kèm lệnh và trích manifest.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Backup mới có dữ liệu khác hôm baseline cũ | Baseline và nhánh build cùng ngày (gate tự build lại lake-A khi sang ngày) |
| PII trong shadow | Thư mục 0700, dọn ở phase 9 (`cleanup.sh --all`) |

## Rollback

Không có thay đổi trong repo. Xoá worktree nháp nếu bỏ plan.
