---
phase: 0
title: "Safety harness: worktree, shadow lake, golden snapshot, inventory, runbook deploy"
status: completed
priority: P1
effort: "3d"
dependencies: []
---

# Phase 0: Safety harness

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng trong [architecture-boundaries.md](architecture-boundaries.md) (sơ đồ authority/boundary, giao diện, quyền ghi). Trong lúc làm: tài liệu đi cùng commit với code, không dồn về phase 7. Phase chỉ được coi là xong khi tài liệu dưới đây khớp với code thật.
>
> **Tài liệu phải cập nhật trong phase này:** `scripts/shadow/README.md` (cách dùng shadow, gate M/S); `docs/operations/deployment.md` (runbook deploy và rollback có dừng container); `architecture-boundaries.md` §2 (vùng lưu trữ shadow, quy tắc PII).

## Goal

Có bộ công cụ chứng minh bằng máy rằng một thay đổi không đổi con số, không đổi tên bảng public, không đổi relation/config dbt, không đổi wiring Dagster và không làm job nào chọn rỗng; chạy hoàn toàn cô lập khỏi prod. Kèm runbook deploy và rollback dùng cho mọi phase.

## Context (đã kiểm chứng)

- Checkout `/home/vantt/app/fg-dataware-house` được bind-mount vào container prod `data_platform` (`docker-compose.yml` L28-32): sửa file ở đó là sửa prod.
- Lịch realtime `*/3` và incremental `*/10` (`orchestration/definitions.py` L372-421) chạy cả ngày; job realtime build toàn bộ dbt + serving. **Không có khung giờ yên tĩnh.**
- `DBT_EXPORT_PATH` ở prod kết thúc bằng `export/marts`; serving đọc `export/marts/rolling/<name>/` (`scripts/provisioning/bootstrap_serving_views.py`).
- Health DB nằm ở named volume `monitoring_db` phủ lên `/app/var/data_lake/monitoring`, không nằm trong `app_data/data_lake`.
- `transformation/dbt_packages/` bị gitignore (worktree mới không có `dbt_utils`); profile nạp extension `parquet`, `httpfs` lúc chạy.
- Backup có sẵn, chụp dưới `duckdb_lock`: `app_data/backups/<ts>/app_data/data_lake` (`orchestration/ops/system_backup.py` L79-81).
- Có sẵn harness checksum từ lần refactor std: `plans/archive/plans/260603-1730-sapo-std-gate-and-naming/snapshots/checksum.py` + `verification-protocol.md` (T1–T4). Tái sử dụng, không viết lại từ đầu.
- 16 model incremental (manifest): 12 ở `staging/` + `dim_customers_base`, `int_customer_metrics`, `int_customer_entry_attributes`, `int_customer_discount_metrics`.
- Dữ liệu lake chứa PII khách hàng (Sapo customer/address, CRM notes, party insight).

## Files to Create / Modify (trong worktree, không trong checkout prod)

- Create: `scripts/shadow/run-shadow.sh`, `scripts/shadow/prepare-shadow.sh`, `scripts/shadow/cleanup.sh`, `scripts/shadow/README.md`.
- Create: `scripts/checks/guard_not_prod.py`.
- Create: `scripts/checks/golden_snapshot.py` (port từ `checksum.py` archive, bỏ đường dẫn Windows cứng).
- Create: `scripts/checks/public_models.yaml`.
- Create: `scripts/checks/dbt_inventory.py`, `scripts/checks/dagster_inventory.py`.
- Create: `scripts/checks/requirements-dev.txt` (chỉ nếu thật sự cần thư viện ngoài; ưu tiên stdlib + duckdb có sẵn). **Không sửa** `ingestion/requirements.txt`, `scripts/requirements.txt` hay `Dockerfile.dataplatform`.

## Tasks & Steps

### A. Môi trường shadow cô lập

1. `git worktree add /home/vantt/app/fg-dw-modular -b refactor/modularize-suite main` (code mới) và `git worktree add --detach /home/vantt/app/fg-dw-baseline main` (code gốc để build baseline).
2. Thư mục shadow `/home/vantt/app/fg-dw-shadow/` mode `0700`.
3. `prepare-shadow.sh`:
   - **lake-base** = DuckDB + `export/` từ backup **N-1**, cộng các thư mục raw (`*_raw/`) từ backup **N**. Như vậy lần build đầu trên shadow có đúng một ngày load mới để nhánh incremental thật sự xử lý dòng. Không bao giờ chép lake đang chạy.
   - Health DB: chép nội dung volume `monitoring_db` bằng `docker run --rm -v monitoring_db:/src:ro -v <shadow>:/dst alpine cp -a /src/. /dst/monitoring/`.
   - `dbt_packages`: chép read-only từ `transformation/dbt_packages` của checkout prod (đang có do `dbt deps` lúc container start) vào `<shadow>/deps/dbt_packages`.
   - DuckDB extensions: `docker cp data_platform:/root/.duckdb <shadow>/deps/duckdb` (chỉ đọc từ container prod).
4. `run-shadow.sh <code_dir> <lake_dir> <cmd...>`:
   - Gọi `guard_not_prod.py` với `realpath` của **cả hai** đối số; từ chối nếu nằm dưới `/home/vantt/app/fg-dataware-house`.
   - `docker run --rm --network none --user $(id -u):$(id -g) --cpus=2 --memory=6g`.
   - Mount giống prod, từng thư mục con: `ingestion`, `transformation`, `orchestration`, `scripts`, `webhook_consumer` từ `<code_dir>` vào `/app/<dir>`; `<lake_dir>` vào `/app/var/data_lake`; `<lake_dir>/monitoring` vào `/app/var/data_lake/monitoring`; `deps/dbt_packages` vào `/app/transformation/dbt_packages:ro`; `deps/duckdb` vào `$HOME/.duckdb:ro`; `DAGSTER_HOME` trên tmpfs.
   - Env: **allowlist** tường minh lấy tên và giá trị đường dẫn từ khối `environment:` của `docker-compose.yml` và `.env.docker.example` (không mở `.env.docker`): `DBT_DATA_LAKE_PATH`, `DBT_EXPORT_PATH=/app/var/data_lake/export/marts`, `INGESTION_HEALTH_DB`, `DBT_PROJECT_DIR`, `DBT_PROFILES_DIR`, `PYTHONPATH=/app`. Script từ chối nếu thấy `--env-file`, mount `app_data/secrets` hoặc `agent_codex_config`.
   - Tự kiểm tra cô lập mạng: lệnh đầu tiên trong container là `getent hosts github.com` phải thất bại.
5. `cleanup.sh`: xoá lake-B sau mỗi lần compare; xoá toàn bộ `fg-dw-shadow` khi đóng plan (tiêu chí của phase 7).

### B. Công cụ so sánh

6. `public_models.yaml`: sinh từ manifest (model có `config.location` chứa `/rolling/`) + allowlist Rill (`scripts/provisioning/publish_rill_assets.py`) + model non-rolling mà CRM/tools đọc ([scout dbt §2](reports/scout-dbt-graph-consumers.md)). Mỗi bảng có `key:` nếu có khoá nghiệp vụ.
7. `golden_snapshot.py capture|compare`:
   - Trước mỗi build, **xoá `export/marts/rolling/*`** trong lake đích (giữ DuckDB state), để không bảng nào "sạch" nhờ parquet thừa kế.
   - `capture` fail nếu bảng public nào có file mới nhất cũ hơn thời điểm bắt đầu build hoặc trạng thái trong `target/run_results.json` khác `success`.
   - Mỗi bảng: số dòng; danh sách cột + kiểu; checksum từng cột không phụ thuộc thứ tự; **checksum cấp dòng** `sum(hash(row(...)))` + `bit_xor` trên các cột không volatile; với bảng có `key`, **keyed diff** `EXCEPT ALL` hai chiều.
   - Cột volatile (vd. `metric_calculated_at`): khai báo kèm lý do; cột số volatile so với dung sai làm tròn, không bỏ.
8. `dbt_inventory.py`: từ `manifest.json`, với mọi model/seed/test xuất `relation_name`, `schema`, `alias`, `resource_type`, **toàn bộ `config`** trừ danh sách bỏ qua tường minh (`original_file_path`, `fqn`, `path`), `location` chuẩn hoá bỏ hậu tố timestamp, seed `column_types`, số lượng test theo model. Lệnh `diff`.
9. `dagster_inventory.py`: asset keys, asset check keys, job names, schedule names + cron + job, sensor names, và **với mỗi job: tập dbt `unique_id` mà selection của job resolve ra** (qua manifest + translator). Fail nếu tập rỗng hoặc khác giữa main và branch.

### C. Quy trình kiểm chứng (gate)

10. **Baseline:** lake-A = bản sao lake-base; build bằng `fg-dw-baseline`: `dbt seed && dbt build` (như Dagster chạy), sau đó `refresh_rolling.py` + `bootstrap_serving_views.py`; `capture`. Build lại lake-A2 cùng ngày để xác định cột volatile.
11. Hai mức gate:
    - **Gate M (phase chỉ di chuyển file: 1, 2, 5, 6):** `dbt_inventory diff` + `dagster_inventory diff` (gồm resolve selection) + diff SQL trong `target/run` sau một build thật (chuẩn hoá khoảng trắng) + một lần golden compare + pytest.
    - **Gate S (phase đổi SQL: 3, 4):** Gate M + golden pass thứ hai sau `--full-refresh` toàn project trên lake-AF (baseline) và lake-BF (branch).
12. Kiểm tra lake trống: một lần mỗi phase, build trên lake có `export/marts/rolling/` bị xoá hoàn toàn để bắt lỗi tạo thư mục.
13. pytest: `python -m pytest ingestion/tests orchestration scripts/tests -q` trong shadow.

### D. Runbook deploy và rollback (dùng cho mọi phase)

14. Trước deploy: chụp trạng thái schedule/sensor (bật/tắt) từ Dagster prod (`dagster schedule list`, `dagster sensor list` qua `docker exec`, chỉ đọc).
15. Deploy:
    1. `docker compose stop data_platform` (dừng mọi lịch; run đang chạy được chờ xong hoặc ghi nhận bị huỷ).
    2. `git -C /home/vantt/app/fg-dataware-house status`: nếu seed CSV bị job sửa (budget/sheets/sync_seeds), commit nội dung đang sống lên `main` trước, rồi rebase branch lên đó.
    3. `git merge --ff-only refactor/modularize-suite`.
    4. `docker compose start data_platform` (lệnh start chạy `dbt deps && dbt parse` trước `dagster dev`).
    5. So trạng thái schedule/sensor với bước 14; chạy tay một job realtime và kiểm tra xanh.
    6. Theo dõi một vòng nightly; so số dòng bảng public với ngày trước trong ngưỡng `row_trend_checks`.
16. Rollback: `docker compose stop data_platform` → `git revert` (hoặc reset về SHA ghi lại ở bước 15.3) → `start`. Mỗi phase ghi trong file của mình các relation/seed mới cần dọn nếu rollback.

## Verification

- lake-A vs lake-A2: golden sạch (sau khi khai báo volatile); inventory sạch.
- Sửa một dòng seed trên lake-B → golden báo đúng bảng/cột; hoán đổi hai giá trị giữa hai dòng → checksum cấp dòng báo lỗi.
- Đổi `+schema` của một folder trên nhánh thử → `dbt_inventory diff` báo; đổi selection của một job thành rỗng → `dagster_inventory diff` báo.
- `run-shadow.sh` với đường dẫn lake prod → bị từ chối; `getent hosts` trong container thất bại.
- File tạo trong shadow thuộc user `vantt`; `cleanup.sh` xoá sạch.
- `git -C /home/vantt/app/fg-dataware-house status` không có thay đổi do phase này (trừ file plan).

## Risks

- Shadow build tốn tài nguyên trên máy prod: giới hạn 2 CPU/6 GB, chạy ngoài khung nightly 02:30–04:00.
- Backup N-1 và N có thể lệch schema raw nếu có thay đổi ingestion giữa hai ngày: chọn hai backup không có deploy xen giữa.

## Kết quả thực hiện (2026-10-13)

**Trạng thái: hoàn thành.** Code trên nhánh `refactor/modularize-suite` (worktree `/home/vantt/app/fg-dw-modular`); prod không bị đụng.

| Thành phần | File | Ghi chú |
|---|---|---|
| Guard | `scripts/checks/guard_not_prod.py` | Từ chối mọi đường dẫn dưới checkout prod (realpath, không override bằng env) |
| Shadow | `scripts/shadow/{prepare-shadow,clone-lake,run-shadow,build-lake,pytest-shadow,cleanup,gate}.sh` | `--network none` (tự kiểm tra DNS), uid 1000, env allowlist, mount từng thư mục con như compose |
| Golden | `scripts/checks/golden_snapshot.py` + `public_models.yaml` | 83 bảng (75 rolling + 8 relation CRM/tools đọc), 48 có khoá; 17 cột volatile (timestamp build) |
| dbt inventory | `scripts/checks/dbt_inventory.py` | 176 node (162 model + 14 seed); `compiled-diff` so SQL đã chạy |
| Dagster inventory | `scripts/checks/dagster_inventory.py` | 244 asset, 492 check, 21 job (kèm tập dbt unique_id), 17 schedule, 9 sensor, 12 SLA |
| Trạng thái instigator | `scripts/checks/instigator_state.py` | GraphQL webserver prod (chỉ đọc): 26/26 đang RUNNING |
| Test | `scripts/tests/test_golden_snapshot.py` | 5 test: hoán đổi giá trị giữa dòng, parquet cũ, node không `success` |
| Tài liệu | `docs/operations/refactor-safety-harness.md` (thiết kế đầy đủ: làm gì, bằng cách nào, giới hạn), `scripts/shadow/README.md` (lệnh), `docs/operations/deployment.md` § Refactor deploys | Runbook deploy/rollback dừng container, `git revert` theo range. Commit tài liệu `97d05451` |

**Bằng chứng gate:**

- lake-A vs lake-A2 (cùng code, cùng dữ liệu): 0 khác biệt sau khai báo 17 cột timestamp build; compiled SQL 0 khác biệt trên 162 model.
- Phản chứng: sửa 1 dòng seed → golden báo đúng `dim_payment_methods.payment_method_type`, keyed-diff chỉ đúng khoá; đổi `+schema` của `intermediate/` → dbt inventory báo 42 khác biệt; đổi cron realtime → dagster inventory báo đúng schedule; asset key sai → Dagster tự từ chối load.
- Lake trống (xoá cả thư mục `rolling/`) build lại đủ 94 thư mục, golden khớp.
- `gate.sh S` trên nhánh: PASS trong 2 phút 18 giây; `gate.sh M` (có compiled SQL): PASS.
- pytest: 163 pass (158 có sẵn + 5 mới); `test_concurrent_writes_no_lock_error` fail 1/8 lần do timing SQLite, pass trên baseline và các lần còn lại.

**Phát hiện mới:**

- `dagster schedule list -f ...` báo mọi schedule/sensor STOPPED trong khi webserver đang chạy cả 26 → runbook dùng `instigator_state.py`.
- `stg_marketing_spend` có `location` nhưng là view, không ghi parquet → không phải bảng public (scout cũ tính nhầm).
- Image prod không có pytest → cài pytest 8.3.3 (+pluggy, iniconfig, `--no-deps`) vào thư mục shadow, không đụng image.
- Build toàn bộ trên shadow chỉ khoảng 18 giây, nên chạy gate nhiều lần không tốn tài nguyên prod.
