---
phase: 2
title: "Công tắc pack: enabled_packs, +enabled, pack_ref, hợp đồng cột, check đồng bộ"
status: pending
priority: P1
effort: "0.5d"
dependencies: [1]
---

# Phase 2: Công tắc pack

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng trong `docs/architecture/modules.md`. Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/architecture/modules.md` §3 (cạnh lõi → pack chỉ qua `pack_ref`), §8 (bật/tắt pack: nguồn khai báo, biến dbt, `+enabled`, hợp đồng cột, phụ thuộc pack → pack đã biết, giới hạn); `orchestration/packs/README.md` (danh sách pack đủ 7, mục "Turning a pack off" viết lại); README mới cho `orchestration/packs/{marketplace,facebook_ads,facebook_messenger}`; `transformation/AGENTS.md` (quy tắc: lõi đọc pack chỉ qua `pack_ref`, hợp đồng nằm ở `pack_contracts()`); `scripts/checks/README.md` (rule mới).

## Mục tiêu

Có công tắc và điểm cắm, **chưa** đổi model nào. Fine Japan: compiled SQL giống hệt, golden 0 khác biệt.

## Thiết kế

### Nguồn khai báo: `modules.yaml` là chuẩn, `dbt_project.yml` là bản sao có kiểm

dbt không đọc được file YAML tuỳ ý lúc parse, và `dbt parse` chạy ở nhiều nơi không qua Dagster (lệnh start container `docker-compose.yml:58`, `scripts/shadow/build-lake.sh:28-29`, `orchestration/assets/dbt.py` gọi `parse` rồi `build`). Truyền `--vars` ở mọi nơi dễ sót, nên:

- `transformation/dbt_project.yml` khối `vars:` thêm `enabled_packs: [crm, hug, finance, sales_playbook, marketplace, facebook_ads, facebook_messenger]` (cùng thứ tự `modules.yaml`). Phase 5 thêm `tenant`, phase 7 thêm `enabled_connectors`.
- `scripts/checks/check_boundaries.py` thêm rule **`module-config`**: tập `packs` trong `orchestration/config/modules.yaml` phải bằng `vars.enabled_packs`; lệch thì fail và in sẵn dòng cần dán. Test pytest: lệch → fail; khớp → pass.
- Profile thử nghiệm (lõi trần) truyền `--vars` lúc build trên shadow; không dùng cho prod.

### `modules.yaml` liệt kê đủ pack có model dbt

Hôm nay `modules.yaml` có 4 pack (`orchestration/config/modules.yaml`) nhưng dbt có 7 thư mục pack (`transformation/models/packs/`). Thêm `marketplace`, `facebook_ads`, `facebook_messenger` vào `packs:` và tạo 3 package rỗng `orchestration/packs/<id>/{__init__.py,jobs.py}` xuất `ASSETS = []`, `NIGHTLY_ASSETS = []`, `JOBS = SCHEDULES = SENSORS = []` (cùng mẫu `packs/finance`, `packs/hug`; loader `orchestration/module_registry.py:import_each` báo lỗi khi thiếu package). Cập nhật chú thích đầu `modules.yaml` (bỏ câu "Turning a pack off is not supported yet").

### Tắt cả thư mục pack

`dbt_project.yml`, dưới `models: sapo_warehouse: packs: <pack>:` thêm `+enabled: "{{ ('<pack>' in var('enabled_packs')) | as_bool }}"` cho 7 pack (dạng chính xác theo kết quả spike b). Không đụng các anchor `&layer_*` đang dùng.

### Macro (thư mục mới `transformation/macros/packs/`)

| Macro | Hợp đồng |
|---|---|
| `pack_enabled(pack)` | Trả bool: `pack in var('enabled_packs')`. Pack không có thư mục `models/packs/<pack>` → lỗi biên dịch (bắt lỗi gõ sai) |
| `pack_contracts()` | Trả dict `{ '<model>': {'pack': '<pack>', 'columns': {'<col>': '<duckdb type>', ...}} }`. **Một chỗ duy nhất** khai báo cột lõi được đọc từ pack. Phase 2 tạo dict rỗng; phase 3–4 thêm mục |
| `pack_ref(pack, model, columns=none)` | `pack_enabled(pack)` → `{{ return(ref(model)) }}` (nên SQL compile ra đúng chuỗi relation như `ref` cũ). Tắt → chuỗi `(SELECT CAST(NULL AS <type>) AS <col>, ... WHERE FALSE)`. `columns` mặc định lấy từ `pack_contracts()[model]`; `pack` khác với `pack` trong hợp đồng → lỗi biên dịch |
| test generic `pack_contract` (`transformation/tests/generic/pack_contract.sql`) | Gắn vào model pack trong file properties của pack; so `adapter.get_columns_in_relation(model)` với `pack_contracts()[model].columns` (tên + kiểu, không phân biệt hoa thường); trả dòng cho mỗi cột thiếu/sai kiểu; mức `error` |

Không dùng `run_query` hay `graph` lúc parse; mọi quyết định dựa trên `var`, nên lineage tĩnh (spike a, f).

### Kiểm tra ranh giới nhận `pack_ref`

Khi pack bật, manifest vẫn ghi cạnh lõi → pack (vì `pack_ref` gọi `ref`). `check_boundaries.py` rule `dbt-ref` đổi như sau: cạnh `core → pack:<p>` tới model `m` hợp lệ **khi và chỉ khi** `raw_code` của model nguồn có lời gọi `pack_ref('<p>', '<m>'` (regex, nháy đơn hoặc kép) và `m` có mục trong `pack_contracts()` (đọc bằng regex từ `transformation/macros/packs/pack_contracts.sql` hoặc từ một file YAML đi kèm; chọn một, ghi trong `scripts/checks/README.md`). `ref('<m>')` thẳng vẫn là vi phạm. Test pytest cho cả ba trường hợp.

## Files

- Modify: `transformation/dbt_project.yml` (vars, `+enabled` 7 pack), `orchestration/config/modules.yaml`, `scripts/checks/check_boundaries.py` (+ test trong `scripts/tests/`), `orchestration/packs/__tests__/test_pack_registry.py` (7 pack nạp được), các tài liệu ở khối đầu.
- Create: `transformation/macros/packs/{pack_enabled,pack_ref,pack_contracts}.sql`, `transformation/tests/generic/pack_contract.sql`, `orchestration/packs/{marketplace,facebook_ads,facebook_messenger}/{__init__.py,jobs.py,README.md}`, `scripts/shadow/build-profile.sh` (clone lake với `--empty-rolling`, `build-lake.sh <branch> <lake> --vars '<json>'`, in `run_results` tóm tắt và `golden_snapshot.py compare` so với lake-A **chỉ để xem**; exit theo kết quả build).
- Nếu spike c báo lỗi: Move 6 test đơn lẻ vào `transformation/tests/packs/<pack>/` + `data_tests:` `+enabled` (tên test giữ nguyên nên `unique_id` không đổi).

## Verification

- **Gate M** (`--allow-new` cho 3 package Dagster rỗng nếu inventory báo; không thêm asset nào): golden 83/83, compiled SQL giống hệt (không model nào đổi), inventory dbt chỉ khác `config.enabled` dạng chuỗi/bool nếu có (đọc kỹ, không chấp nhận khác biệt khác), inventory Dagster giống hệt.
- `check_boundaries.py` pass; test mới của rule `module-config` và `dbt-ref`/`pack_ref` pass.
- `scripts/shadow/build-profile.sh` với `{enabled_packs: [crm, hug, finance, sales_playbook, marketplace, facebook_ads, facebook_messenger]}` cho golden 0 khác biệt (tự kiểm script). Với `{enabled_packs: []}` script chạy được và **dự kiến fail** ở các model lõi còn `ref()` thẳng (đúng 8 model trong allowlist `core -> pack`); ghi danh sách lỗi vào báo cáo phase làm mốc cho phase 3–4.

**Đổi số:** không.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| `+enabled` Jinja làm config của mọi model pack trong inventory đổi dạng | Spike b xác nhận kiểu; nếu inventory báo khác chỉ ở `enabled: true` (chuỗi → bool) thì ghi rõ, không phải đổi relation |
| Regex đọc `pack_ref` bỏ sót cách viết khác | Quy ước một cách viết trong `transformation/AGENTS.md`; test pytest có ca viết sai phải fail |

## Rollback

`git revert` theo runbook; không có relation mới. Package Dagster rỗng không tạo asset nên Dagster không đổi trạng thái.
