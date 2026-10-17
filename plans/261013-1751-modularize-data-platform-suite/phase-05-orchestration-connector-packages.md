---
phase: 5
title: "Orchestration: mỗi connector là một package"
status: completed
priority: P1
effort: "2.5d"
dependencies: [1]
---

# Phase 5: Orchestration connector packages

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng trong `docs/architecture/modules.md` (bản sống trên nhánh; sơ đồ authority/boundary, giao diện, quyền ghi). Trong lúc làm: tài liệu đi cùng commit với code, không dồn về phase 7. Phase chỉ được coi là xong khi tài liệu dưới đây khớp với code thật.
>
> **Tài liệu phải cập nhật trong phase này:** `orchestration/README.md` + `orchestration/connectors/README.md` (hợp đồng connector package, cách thêm/bỏ connector qua `modules.yaml`); `docs/architecture/modules.md` §4–§5 (kernel và connector thật).

## Goal

Mỗi nguồn trở thành package `orchestration/connectors/<id>/` tự khai báo assets, jobs, schedules, sensors và dữ liệu phụ trợ (nhãn digest, thời gian chạy tối đa, map asset-check, map dbt source). `definitions.py` chỉ ghép các package được liệt kê trong `orchestration/config/modules.yaml`. **Asset keys, check keys, job/schedule/sensor names, cron và tập model dbt mỗi job chọn giữ nguyên.**

## Context (đã kiểm chứng)

- Thành viên từng nguồn đang rải ở 10 file ([scout orchestration](reports/scout-orchestration-ingestion-deploy.md)).
- Kiểu dữ liệu thật: `ASSET_DISPLAY: dict[str, tuple[str, str, str]]` (`ops/morning_digest.py:58`), `_JOB_MAX_RUNTIME: dict[str, timedelta]` theo tên job (`sensors/stuck_run_alerter.py:70`).
- Nhiều module tính đường dẫn theo vị trí file (`ops/purge_runs.py:108-113`, `asset_checks/sla_loader.py:16`, `ops/system_backup.py:22-23`) và hỏng âm thầm nếu bị dời → **không dời** các file generic.
- Trạng thái bật/tắt schedule lưu trong `dagster_home` theo code location + repo + tên; code location (`-f orchestration/definitions.py`) không đổi.

## Thiết kế (đơn giản)

```python
# orchestration/connectors/hug/__init__.py
from .assets import hug_webhook_consumer_asset
from .jobs import hug_realtime_job, hug_realtime_schedule

ASSETS = [hug_webhook_consumer_asset]
JOBS = [hug_realtime_job]
SCHEDULES = [hug_realtime_schedule]
SENSORS = []
DIGEST_DISPLAY = {"hug/...": ("...", "...", "...")}   # cùng kiểu ASSET_DISPLAY
JOB_MAX_RUNTIME = {"hug_realtime_job": timedelta(minutes=...)}
CHECK_ASSET_DEFS = {...}
DBT_SOURCE_KEYS = {...}
```

`orchestration/connectors/__init__.py` có `load_enabled()` đọc `modules.yaml` (một danh sách id) và trả về các module; nơi đang hardcode (`asset_checks/__init__.py`, `morning_digest.py`, `stuck_run_alerter.py`, `assets/dbt.py` translator, `file_drop_sensors.py`) ghép dict từ các module đã bật. Giữ **một** file `config/ingestion_sla.yaml`.

Các file generic (sensors/ops/asset_checks/notifications, dbt, serving, rill, reconciliation, kpi_closure) **giữ nguyên vị trí** và được khai báo là "kernel" trong tài liệu phase 7. Các job chéo nguồn (`_fact_order_returns`, nightly batch, full refresh) ở lại `definitions.py`.

## Files to Create / Modify

- Create: `orchestration/config/modules.yaml` (`connectors: [sapo_v2, shopee, misa_amis, sheets, hug]`); `orchestration/connectors/__init__.py`.
- Move (git mv): `assets/{sapo_v2,shopee,misa_amis,sheets,hug}_assets.py` → `connectors/<id>/assets.py`; job/schedule tương ứng từ `definitions.py` → `connectors/<id>/jobs.py`. Kiểm tra từng file được dời: không có đường dẫn tính theo `__file__`, hoặc sửa sang `PYTHONPATH`/env.
- Modify: `orchestration/definitions.py`, `asset_checks/__init__.py`, `ops/morning_digest.py`, `sensors/stuck_run_alerter.py`, `assets/dbt.py`, `sensors/file_drop_sensors.py` (tách phần Shopee/MISA vào package tương ứng), `asset_checks/reconciliation_checks.py` (keys).
- Modify: `asset_checks/sla_loader.py` — fail rõ ràng (raise) khi không tìm thấy file SLA thay vì âm thầm dùng mặc định.

## Tasks & Steps

1. Xuất `dagster-main.json` (phase 0).
2. Làm `hug` end-to-end; Gate M.
3. Lần lượt `sheets`, `shopee`, `misa_amis`, `sapo_v2`; Gate M sau mỗi connector.
4. Thêm vào `dagster_inventory.py`: SLA đã resolve cho từng check key, để bắt việc mất cấu hình SLA.
5. Thử trên shadow: bỏ `hug` khỏi `modules.yaml` → Definitions load, phần còn lại không đổi.

## Verification

- Gate M, gồm SLA resolve và tập `unique_id` mỗi job.
- `dagster definitions validate -f orchestration/definitions.py` trong shadow.
- pytest orchestration pass; thêm test `load_enabled()` (bật/tắt một connector).

## Deploy

Runbook phase 0, bước 14–15: so trạng thái schedule/sensor trước-sau là bắt buộc ở phase này.

## Rollback

Revert commit + restart; tên không đổi nên trạng thái schedule giữ nguyên.

## Ngoài phạm vi

Facebook ingestion (chưa có asset): ghi là "dormant" trong comment `modules.yaml`, chờ quyết định.

## Kết quả thực hiện (2026-10-14)

**Trạng thái: hoàn thành trên nhánh, chưa deploy.** Commit `b718befc`. Thực hiện bởi worker Herdr `p05a01` (Sonnet); coordinator chạy lại gate M: PASS (baseline `25b6be42`).

- 5 connector package `orchestration/connectors/{sapo_v2,shopee,misa_amis,sheets,hug}/` (`assets.py`, `jobs.py`, `__init__.py` export list/dict); `orchestration/config/modules.yaml` liệt kê connector bật (facebook ghi dormant); `orchestration/connectors/__init__.py` (`load_enabled`).
- `orchestration/job_support.py` mới (SYNC_TAGS, kiểm tra run trùng, selection `fact_order_returns`) để tránh import vòng giữa `dbt.py` và connector.
- `definitions.py` chỉ còn job chéo nguồn (nightly, full refresh, health, maintain, crm backup) và ghép connector. File kernel giữ nguyên chỗ; `sheets_modified_sensor.py` giữ chỗ (URL FJ chuyển sang tenant ở phase 6).
- `sla_loader.py`: thiếu file SLA → raise. `file_drop_sensors.py` thành factory.
- Inventory Dagster: 254 asset, 502 check, 21 job, 17 schedule, 9 sensor, SLA, unique_id mỗi job — 0 khác biệt. Bỏ `hug` khỏi `modules.yaml` trên shadow: chỉ mất phần của hug.
- 7 test mới cho `load_enabled`; pytest 199 pass.
- Tài liệu: `orchestration/README.md`, `orchestration/connectors/README.md` (mới), `docs/architecture/modules.md` §4–§5, `orchestration/docs/{JOBS,README}.md`, `docs/development/contributing.md`. Báo cáo worker: `reports/phase-05-worker-report.md`.
- Deploy: dùng runbook, bắt buộc so `instigator_state.py` trước/sau.
