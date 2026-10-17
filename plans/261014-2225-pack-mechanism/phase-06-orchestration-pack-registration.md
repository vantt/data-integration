---
phase: 6
title: "Đảo chiều crm_cache_refresh: pack đăng ký asset chạy sau serving"
status: pending
priority: P2
effort: "0.25d"
dependencies: [2]
---

# Phase 6: Connector không import pack

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng trong `docs/architecture/modules.md`. Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `orchestration/packs/README.md` (hợp đồng thêm export `AFTER_SERVING_ASSETS`; bỏ câu "four connector jobs that select `crm_cache_refresh`"); `orchestration/connectors/README.md` (job connector gắn đuôi sau serving qua `job_support.after_serving_selection()`); `orchestration/packs/crm/README.md`; `docs/architecture/modules.md` §4 (kernel) và §5.1 (hợp đồng connector).

## Hiện trạng (đã kiểm)

Sáu job của bốn connector chọn `crm_sync.crm_cache_refresh` và import `orchestration.packs.crm`:

| File | Dòng import | Job chọn `crm_cache_refresh` |
|---|---|---|
| `orchestration/connectors/sapo_v2/jobs.py` | L4 | `pipeline_sapo_v2_realtime_job` (L18), `pipeline_sapo_v2_incremental_job` (L25) |
| `orchestration/connectors/shopee/jobs.py` | L6 | 1 job (L24) |
| `orchestration/connectors/misa_amis/jobs.py` | L6 | 2 job (L42, L57) |
| `orchestration/connectors/sheets/jobs.py` | L4 | 1 job (L41) |

Pack `crm` đã có mẫu tương tự cho nightly: `NIGHTLY_ASSETS` trong `orchestration/packs/crm/__init__.py`, kernel gộp ở `orchestration/definitions.py:95-96`. `orchestration/job_support.py` là kernel, connector đã import nó.

## Thiết kế

- Hợp đồng pack thêm export `AFTER_SERVING_ASSETS` (list, mặc định rỗng): asset chạy sau `build_serving_db` trong các job đồng bộ của connector. Pack `crm`: `AFTER_SERVING_ASSETS = [crm_sync.crm_cache_refresh]`; 6 pack còn lại `[]`.
- `orchestration/job_support.py` thêm `after_serving_selection() -> AssetSelection`: gộp `AFTER_SERVING_ASSETS` của các pack đang bật (`orchestration.packs.load_enabled()`). **Import pack bên trong hàm**, không ở đầu module, để không tạo vòng import (pack có thể import kernel).
- 4 file `jobs.py` của connector: bỏ `from orchestration.packs.crm import crm_sync`, thay `| AssetSelection.assets(crm_sync.crm_cache_refresh)` bằng `| after_serving_selection()`. Tên job, tag, schedule, sensor giữ nguyên.
- Xoá 4 dòng allowlist `orch-import` connector → `orchestration.packs.crm`. Dòng `sales_playbook` → `crm` giữ nguyên (ngoài phạm vi).

## Files

- Modify: `orchestration/job_support.py`, `orchestration/connectors/{sapo_v2,shopee,misa_amis,sheets}/jobs.py`, `orchestration/packs/*/__init__.py` (7 pack thêm `AFTER_SERVING_ASSETS`), `scripts/checks/boundary_allowlist.yaml`, test trong `orchestration/packs/__tests__/` và `orchestration/connectors/__tests__/`, tài liệu ở khối đầu.

## Verification

- **Gate M**: inventory Dagster **giống hệt** (asset, check, selection từng job gồm tập `unique_id` dbt, schedule, sensor); golden không đổi vì không đụng dbt.
- pytest mới: với `modules.yaml` tạm có `packs: [crm]` → 6 job chọn `crm_cache_refresh`; với `packs: []` → Definitions nạp được, 6 job không chọn asset đó.
- `check_boundaries.py` pass với allowlist đã bớt 4 dòng; thêm tạm một `from orchestration.packs.crm import crm_sync` vào connector → fail.

**Đổi số:** không.

## Deploy D2 (sau phase 6, gộp phase 5–6)

Như D1. Kiểm thêm: run đầu tiên của `pipeline_sapo_v2_realtime_job` sau deploy có bước `crm_cache_refresh` thành công.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Vòng import khi `job_support` nạp pack | Import trong thân hàm; test nạp `orchestration.definitions` trong pytest |
| Thứ tự chạy đổi | Selection là tập asset, thứ tự do phụ thuộc asset (`crm_cache_refresh` deps `build_serving_db`) quyết định, không đổi |

## Rollback

`git revert` theo runbook; không có trạng thái lưu nào đổi (tên job/schedule/sensor giữ nguyên).
