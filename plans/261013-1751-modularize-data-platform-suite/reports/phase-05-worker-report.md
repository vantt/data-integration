status: complete

# Báo cáo p05 a01 — connector packages cho orchestration

## File đổi / dời (chưa commit)
- git mv: `orchestration/assets/{sapo_v2,shopee,misa_amis,sheets,hug}_assets.py` → `orchestration/connectors/<id>/assets.py`
- Mới: `orchestration/config/modules.yaml` (facebook ghi "dormant" trong comment), `orchestration/connectors/__init__.py` (`enabled_ids`, `load_enabled`, `load_enabled_jobs`), `connectors/<id>/{__init__,jobs}.py` ×5, `orchestration/job_support.py` (SYNC_TAGS, has_active_run, long_dbt_rw_holder, FACT_ORDER_RETURNS), `connectors/__tests__/test_load_enabled.py` (7 test)
- Sửa: `definitions.py` (chỉ còn job chéo nguồn nightly/fullrefresh, health, maintain, crm_backup; ghép connector), `asset_checks/__init__.py` (CHECK_ASSET_DEFS), `asset_checks/sla_loader.py` (thiếu file SLA → raise), `ops/morning_digest.py` (DIGEST_ASSETS/DIGEST_DISPLAY), `sensors/stuck_run_alerter.py` (JOB_MAX_RUNTIME), `assets/dbt.py` (SapoDbtTranslator đọc DBT_SOURCE_KEYS), `sensors/file_drop_sensors.py` (thành factory `make_file_drop_sensor`; sensor shopee/misa nằm trong package), `asset_checks/__tests__/test_check_factories_smoke.py` (đường import), `ops/dlt_metrics.py` (comment)
- Không dời file kernel; `sensors/sheets_modified_sensor.py` giữ nguyên chỗ (connector sheets đưa vào SENSORS).
- Quyết định thiết kế: `jobs.py` tách khỏi `__init__.py` để tránh vòng import (dbt.py → load_enabled → jobs → dbt.py). Thêm 2 export ngoài danh sách brief: `NIGHTLY_ASSETS` (để tắt connector không làm vỡ nightly) và `DIGEST_ASSETS` (KNOWN_ASSETS gồm key + recon key). DBT_SOURCE_KEYS của shopee liệt kê 4 bảng thay vì "mọi tên" (khác biệt chỉ khi thêm bảng mới).

## Kiểm tra
`scripts/shadow/gate.sh M` (baseline fg-dw-baseline @ 25b6be42, coordinator đã nâng):
```
baseline: /home/vantt/app/fg-dw-baseline @ 25b6be42...
ok: dbt build (branch) / compare: 83 vs 83 tables, 0 difference(s) / ok: golden
ok: dbt inventory / ok: compiled SQL
boundaries: 46 known, 0 new violation(s), 0 stale / ok: module boundaries
dagster inventory: 0 difference(s), 0 info / ok: dagster inventory
ok: dagster dbt subset run
199 passed / ok: pytest
ok: dbt build on empty rolling / ok: golden on empty-rolling lake
GATE M: PASS
```
- Dagster inventory gồm resolved SLA và unique_id mỗi job: 254 asset, 502 check, 21 job, 17 schedule, 9 sensor, 0 khác biệt.
- Ngoài inventory (so HEAD với working tree): KNOWN_ASSETS, ASSET_DISPLAY, _JOB_MAX_RUNTIME, asset key của mọi dbt source, mô tả/interval sensor → giống hệt.
- Bỏ `hug` khỏi modules.yaml trong shadow: Definitions vẫn load, 253 asset/500 check/20 job/16 schedule; chỉ mất asset hug, `pipeline_hug_realtime_job`, `pipeline_hug_realtime_schedule`, 2 check hug. Đã khôi phục file (git: modules.yaml nguyên như thiết kế, còn hug).
- pytest orchestration: gồm 7 test mới (load_enabled bật/tắt, connector lạ lỗi rõ, hợp đồng export, tên không trùng, thiếu SLA file raise).
- Grep `scripts/maintenance/*.py`: chỉ import `orchestration.ops.*` (không dời) → không ảnh hưởng.

## Tài liệu
`orchestration/README.md`, `orchestration/connectors/README.md` (mới: hợp đồng, thêm/bỏ connector), `docs/architecture/modules.md` (§4 kernel, §5 connectors, bảng trạng thái), `orchestration/docs/{JOBS,README}.md`, `docs/development/contributing.md`.

## Rollback
Revert commit + restart container; tên asset/job/schedule/sensor không đổi nên trạng thái schedule giữ nguyên. Deploy: so sánh `instigator_state.py capture/diff` trước-sau theo runbook (chưa chạy, không deploy).

## Tooling correction đã xác minh
Gate M không thể PASS khi `fg-dw-baseline` ở commit cũ (97d05451, trước std-layer): inventory báo `std_*` added. Coordinator đã nâng baseline lên 25b6be42 và rebuild lake-A → PASS. Lệnh chạy `python -c` trong run-shadow: dùng `python -c "$(cat file)"` vì container chỉ mount thư mục con.

## Blockers
Không. Gợi ý không chặn: thêm `modules.yaml` bỏ-connector thành test tự động (cần cơ chế override đường dẫn modules.yaml); `sheets_modified_sensor.py` URL mặc định chuyển sang tenant config ở phase sau; comment "(Phase 5)" cũ trong `connectors/sheets/assets.py` là chữ có từ trước.
