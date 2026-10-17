# Phase 0: kết quả chốt các ẩn số (chỉ đọc prod)

> Ngày 15/10/2026, khoảng 16:50–17:30 (Asia/Saigon). Chỉ đọc: không dừng container, không chạy job, không ghi vào `app_data`. DuckDB/SQLite chỉ mở `read_only` trên **bản sao** trong scratch (đã xoá sau khi đọc). Không mở nội dung `.env*` (chỉ lấy tên biến bằng `cut -d= -f1`). Chưa làm các bước 1, 3, 4 (phần file thật), 5 của phase 0 (worktree, sửa `design.md`/`plan.md`, khung tài liệu, ADR): theo chỉ đạo, lần này chỉ ghi báo cáo này.
>
> Ánh xạ sang 6 câu hỏi của user: (1) lock → Q4; (2) monitoring_db → Q5, Q6; (3) bảng tích luỹ → Q2, Q3; (4) kích thước → Q7, mục "Kích thước và retention"; (5) seed → Q8; (6) thời lượng nightly → Q12, Q13.

## Tóm tắt: những điều đổi so với design

1. **`ingestion_health.db` là SQLite (WAL), không phải DuckDB**, và **đã có** trong bản backup đêm (84 MB, `integrity_check` = ok). Design §3.1 và §5 dự định `EXPORT DATABASE` của DuckDB cho monitoring. Cần đổi thành SQLite backup API.
2. **Bảng snapshot "tích luỹ" hiện không tích luỹ gì.** `fact_variant_prices_snapshot` và `fact_inventory_snapshot` là model `external` trên thư mục rolling. GC chỉ giữ 3 file mới nhất, và mỗi lần build (vài phút một lần) lại tạo file mới. Trên đĩa hôm nay chỉ còn 3 file, tạo lúc 16:50, 16:51 và 16:54. Không có lịch sử nào để đưa lên off-site, nên ngoại lệ D2 cho hai bảng này không còn tác dụng. Muốn có lịch sử giá/tồn kho thì phải sửa model, và việc đó nằm ngoài plan này.
3. **Bảng duy nhất thực sự không dựng lại được nằm trong `sapo_warehouse.duckdb`: `main.monitor_taxonomy_parity_log`.** Bảng chỉ thêm dòng (`full_refresh=false`), đến nay có 82 dòng, bắt đầu từ 15/10 15:20, và dùng để đếm số đêm parity liên tiếp. Theo D2, file này không lên off-site. Vì vậy bảng này phải được xuất riêng.
4. **CRM backup chạy lúc 09:00 giờ VN chứ không phải 02:00.** `crm_backup_schedule` thiếu `execution_timezone` nên chạy theo UTC. Design §5 và §7 đang sai chỗ này. Với giờ off-site 03:30, bản CRM gần nhất đã cũ khoảng 18,5 giờ, vẫn dưới ngưỡng preflight 26 giờ.
5. **`dagster_home` nặng 11,6 GB.** Trong đó `history/` chiếm 10,1 GB, riêng `history/runs/index.db` là 5,1 GB và chứa event log, tức lịch sử materialization và asset check. Backup hiện bỏ toàn bộ `history/`, nên khôi phục từ backup sẽ mất lịch sử asset. Phần cần thật sự là `schedules/schedules.db` (321 MB, trạng thái và cursor của schedule/sensor).
6. **Raw lake không thuần "chỉ thêm file".**
   - 12 bảng (11 bảng `sapo_v2_raw` và `hug_raw/scan`) là bảng Delta: ghi file nguyên tử, nhưng có checkpoint và tự dọn `_delta_log`.
   - Parquet thường (batch) được ghi bằng `shutil.copyfile` thẳng vào tên cuối, không qua file tạm. Vì vậy không có pattern file tạm nào để `--exclude`.
   - State dlt được ghi **sau** dữ liệu.
   - Lúc 03:30, job incremental và hourly đã bỏ giờ 3, nên chỉ còn writer Delta (nguyên tử) đang chạy.
7. **Có thêm hai đường ghi ra ngoài phải chặn khi diễn tập.**
   - Budget sync 02:30 hằng ngày **ghi** vào Google Sheet (tab `__REF`), dù docstring ghi là chỉ đọc.
   - Consumer webhook Sapo/HUG gọi `ack` để **xoá hàng đợi** trên Worker.
   - Ngoài ra, `caddy-global` dùng `CLOUDFLARE_API_TOKEN` cho DNS-01, tức là sẽ ghi bản ghi DNS.
8. **Ước tính của D12 quá thấp.** Image của dự án tổng cộng khoảng 13,5 GB chưa nén, không phải 2–4 GB.
9. **Lịch sử run Dagster chỉ còn khoảng 1,4 ngày** (`PURGE_KEEP_DAYS` mặc định 1). Vì thế không đo được p95 của 14 đêm từ Dagster. Tôi dùng `ingestion_runs` làm số liệu thay thế: 77 đêm.
10. **Có ba thứ ngoài các backup hiện có:** `cloudflared` (credentials của tunnel nằm ngoài repo, tunnel phục vụ cả app khác), `app_data/analysis` và `.env*`. Ba thứ này hiện không có trong bất kỳ backup nào.

---

## Q1. Thư mục cấp 1 của `app_data/data_lake`: nguồn sự thật hay phái sinh

Kích thước lấy bằng `du -sh app_data/data_lake/*`.

| Thư mục | Kích thước | Ai ghi (bằng chứng) | Lớp | Đề xuất off-site |
|---|---|---|---|---|
| `sapo_v2_raw` | 542 MB, 23.605 file | dlt qua `ingestion/src/utils/pipeline_runner.py:136` (destination `filesystem`). Writer: realtime `*/3` (`orchestration/connectors/sapo_v2/jobs.py:52`), incremental `*/10 0-2,4-23` (`:82`), hourly `25 0-2,4-23` (`:102`), nightly. Có 11 bảng Delta (`_delta_log`) | **Nguồn sự thật**. `history_log` không lấy lại được do Sapo cắt lịch sử (`docs/operations/backup-restore-completeness-runbook.md:109`, `docs/analytics-handbook/semantic/freshness.md:142`) | Có, hằng ngày |
| `hug_raw` | 164 KB | `ingestion/run_hug_webhook_consumer.py`. Ack xoá sự kiện trên Worker (`ingestion/src/hug/hug_webhook_consumer.py:315`) | **Nguồn sự thật**: sự kiện đã ack thì không lấy lại được | Có |
| `gsheet_raw` | 232 KB | Sensor Sheets (`orchestration/sensors/sheets_modified_sensor.py:120,180`), ghi đè dạng `snapshot/` | Ảnh chụp của Google Sheet. Sheet là gốc, nhưng giá trị cũ thì mất | Có (rẻ) |
| `misa_raw` | 3,4 MB | File drop MISA (`ingestion/run-misa-*-file-drop.py`, `orchestration/connectors/misa_amis/assets.py`) | Phái sinh từ `input_source/misa-amis` và `app_data/analysis` | Có (rẻ, tránh phải nạp lại) |
| `shopee_raw` | 632 KB | File drop Shopee (`ingestion/run-shopee-income-file-drop.py`) | Phái sinh từ `input_source/shopee` | Có (rẻ) |
| `crm_export` | 1,9 MB | `orchestration/packs/crm/crm_writeback_assets.py:177,190` (`COPY` từ SQLite CRM), nằm trong `NIGHTLY_ASSETS` | Phái sinh từ CRM | Không. Dựng lại từ `crm.db` |
| `export` | 64 MB (`rolling/` 57 MB) | Macro `get_rolling_location` (`transformation/macros/get_rolling_location.sql:1`), `publish_rill_assets.py` | Phái sinh (xem Q2) | Không |
| `serving` | 170 MB | `olap.duckdb` do `scripts/provisioning/bootstrap_serving_views.py:98` ghi (ghi lần cuối 05/08). `standalone/` do `orchestration/assets/serving.py:155` ghi. `.known_tables.json` do `refresh_rolling.py` ghi | Phái sinh | Không |
| `sapo_warehouse.duckdb` | 514 MB | dbt | Phái sinh, **trừ** `monitor_taxonomy_parity_log` (Q3) | Không (chỉ xuất bảng log) |
| `monitoring` | lớp host 6,6 MB, đã cũ | Bị named volume `monitoring_db` che (`docker-compose.yml:44` cho data_platform, `:85` cho metabase) | Xem Q5 | Xem Q5 |
| `backup` | 21 MB | Không có writer trong code. Chỉ có `sapo_raw_full_20260413/` và `sapo_raw_text_partition_20260413/`, tạo một lần vào 13/04 | Ảnh chụp thủ công trước một lần migration | **Hỏi user.** Rẻ, nên giữ một lần |
| `sapo_raw_staging` | 44 KB | Không có writer. Chỉ có `init` và `_dlt_version` (sửa lần cuối 12/06) | Mồ côi | Không |
| `test_raw` | 56 KB | Không có writer (07/04) | Mồ côi | Không |

`app_data/analysis`: xem Q19.

## Q2. Model dùng `get_rolling_location()`, và GC có xoá lịch sử không

- Macro này trả về `{DBT_EXPORT_PATH}/rolling/{model}/{model}_{run_started_at}.parquet` (`transformation/macros/get_rolling_location.sql:1`), nên mỗi lần build ra một file mới. Serving chỉ đọc file mới nhất (`scripts/provisioning/bootstrap_serving_views.py:54-74`, `WHERE filename = max(filename)`).
- 76 model dùng macro này, tất cả `materialized: external` theo mặc định của layer trong `dbt_project.yml`. Vì vậy `is_incremental()` luôn sai, kể cả với các model có khối incremental chết như `dim_customers.sql:432` và `fact_inventory_snapshot.sql:30-34,58-61`.
- **GC:** `scripts/provisioning/refresh_rolling.py:54` đặt `ROLLING_KEEP_VERSIONS` mặc định là 3. `garbage_collect()` ở `:69-95` giữ 3 file mới nhất của **mỗi** bảng, không phân biệt bảng nào. GC chạy sau mỗi lần materialize dbt (`orchestration/assets/dbt.py:58-75,158`) và trong `build_serving_db` (`orchestration/assets/serving.py:110`).
- **Bằng chứng trên đĩa (15/10):** `export/marts/rolling/fact_variant_prices_snapshot/` chỉ có 3 file, `..._20261015095024`, `..._20261015095126`, `..._20261015095422` (giờ UTC, tức 16:50–16:54 giờ VN). `fact_inventory_snapshot/` cũng vậy.
- **Kết luận cho D2:** `fact_variant_prices_snapshot.sql:6-8` ghi "historical snapshots accumulate", nhưng `:47` đặt `snapshot_date = CURRENT_DATE` cho giá hiện hành, và GC xoá file cũ sau 3 lần build. Lịch sử đã không tồn tại từ trước. `fact_inventory_snapshot` cũng vậy, vì đọc `int_sapo_inventories` (mức tồn mới nhất của mỗi sản phẩm). **Không có gì để xuất.** Nếu doanh nghiệp cần lịch sử giá/tồn thì đó là lỗi model, cần một plan riêng: sửa model, sau đó mới thêm vào danh sách xuất.

## Q3. 18 model incremental: model nào không dựng lại giống được

`grep materialized='incremental'` ra **18** model chứ không phải 17. Bảng vật lý của chúng nằm trong `sapo_warehouse.duckdb`: tôi đã kiểm `information_schema` trên bản sao, các bảng nằm trong `main_staging.*` và `main_marts.*` dạng `BASE TABLE`.

| Model | Kết luận | Lý do |
|---|---|---|
| 11 `src_sapo_v2_*` (`connectors/sapo_v2/staging/`) và 2 `src_hug_*` | Dựng lại được, nếu raw đầy đủ | `delete+insert` theo khoá, lọc `_dlt_load_id > max`; raw chỉ thêm |
| `monitoring/monitor_taxonomy_parity_log.sql` | **KHÔNG dựng lại được** | `full_refresh=false` (`:4`), `run_at = current_timestamp` (`:12`), mỗi lần build thêm dòng. Trên prod: bảng `main.monitor_taxonomy_parity_log` có 82 dòng, từ 15/10 08:20 đến 09:54 UTC, mới 1 `run_date`. Dùng để đếm số đêm liên tiếp không lệch trước khi chuyển marts sang engine, và tiếp 30 ngày sau đó (comment `:6-10`). Mất bảng thì bộ đếm về 0 |
| `int_customer_metrics` | Dựng lại ra **giá trị theo ngày build**, không giống bảng đang chạy | `recency_days` tính theo `current_date` (`:407`), cộng watermark trừ 3 ngày (`:33-40`). Đây là chênh lệch chấp nhận được, không phải mất dữ liệu |
| `int_customer_discount_metrics` | Như trên | `metric_calculated_at = current_timestamp` (`:163`) |
| `int_customer_entry_attributes` | Bản dựng lại **đúng hơn** bảng đang chạy | Incremental giữ nhãn cũ; full refresh sửa lại (`plans/261014-2225-taxonomy-engine/phase-05-restate-procedure.md:47`) |
| `dim_customers_base` | Bản dựng lại phản ánh trạng thái hiện tại | Watermark `updated_at` (`:87-89`) |

Bằng chứng từ gate S:
- `docs/operations/refactor-safety-harness.md:267-269` (§6.7) và `plans/261014-2225-taxonomy-engine/plan.md:209` cho thấy full refresh khớp 83/83 với prod, ngoài các chênh lệch đã chấp nhận.
- Chênh lệch do ngày chạy đã được ghi ở `refactor-safety-harness.md:161,200`.
- Không có dbt `snapshots/`, không có `post_hook` INSERT.

**Kết luận Q2 + Q3:** chỉ một bảng nhỏ (`monitor_taxonomy_parity_log`) cần xuất. Không rơi vào bước 6 của phase ("nhiều bảng không dựng lại được"), nên **không cần** phương án đưa cả `sapo_warehouse.duckdb` lên off-site hằng tuần.

## Q4. Phạm vi `duckdb_lock` và các writer

Cấu hình khoá:
- `duckdb_lock` giới hạn 1, đặt lúc container khởi động (`docker-compose.yml:63`, `dagster instance concurrency set duckdb_lock 1`).
- Khoá mức run `concurrency_group=dbt_rw` giới hạn 1 (`orchestration/dagster.yaml:38-41`, tag `SYNC_TAGS` ở `orchestration/job_support.py:14`).
- Cả `dagster.yaml` trong volume lẫn bản trong git đều giống hệt nhau (`diff` rỗng).

**Op giữ `duckdb_lock`:** chỉ bốn op.
- `sapo_dbt_assets` (`orchestration/assets/dbt.py:85`)
- `build_serving_db` (`orchestration/assets/serving.py:107`)
- `build_standalone_export` (`:155`)
- `run_platform_backup` (`orchestration/ops/system_backup.py:81`)

**Writer KHÔNG giữ khoá:**

| Writer | Ghi gì | Khi nào |
|---|---|---|
| `scripts/maintenance/sync_seeds.py:31` | Mở `sapo_warehouse.duckdb` để ghi, ghi seed CSV (`:89,114`) | Chỉ chạy tay trên host (`scripts/run_pipeline.ps1:61`), không có trong Dagster |
| `scripts/provisioning/bootstrap_serving_views.py:98` | `serving/olap.duckdb` | Chạy tay, hoặc lúc boot qua `bootstrap_reporting.py` (`docker-compose.yml:63`), trước khi Dagster nhận job |
| `scripts/maintenance/cleanup_and_verify.py:9` | DuckDB | Chạy tay |
| `ingestion/run_facebook_ads_batch.py:24`, `run_facebook_messenger_batch.py:42` | File DuckDB riêng của dlt | Không có lịch (dormant) |
| Toàn bộ dlt ghi raw (`sapo_v2_raw`, `hug_raw`, `gsheet_raw`, `misa_raw`, `shopee_raw`) | Parquet/Delta | Không phải DuckDB nên khoá không áp dụng; chạy */3, */10, :25, sensor 300 giây |
| `ingestion_health.db` (`orchestration/ops/ingestion_health.py:150`) | SQLite | Mỗi lần ingestion |
| `dagster_home` | SQLite của Dagster | Liên tục |
| `crm_export` | Parquet | Nightly |
| Budget seed (`ingestion/src/gsheet_budget_sync/merge.py:35-37`) | CSV, ghi tạm rồi `os.replace` (nguyên tử) | 02:30 |
| Sensor, asset check | Chỉ đọc DuckDB (`duckdb_actuals.py` mở `read_only`). Các `duckdb.connect()` trong `kpi_closure`, `reconciliation`, `refresh_rolling` là DB trong bộ nhớ | — |

**Bản backup 01:04 có thể chép file đang ghi dở không?**
- **DuckDB: hầu như không**, vì mọi writer có lịch đều giữ cùng khoá.
- **Raw: có thể.** Sensor `trigger_backup_after_purge` (`orchestration/definitions.py:199`) chỉ kiểm job `dbt_rw` đang chạy (`_has_active_ingestion`, `:143-165`), theo kiểu kiểm tra rồi mới hành động, nên có khe tranh chấp. Lúc 01:00–01:10 có realtime Sapo/HUG */3 và incremental 01:00, 01:10. Hôm nay (15/10) không có run nào chồng lên cửa sổ chép 01:04:38–01:05:06 (đã kiểm qua GraphQL), nhưng không có gì ngăn việc đó xảy ra.
- **SQLite (`dagster_home`, `ingestion_health.db`): có.** `cp -a` không phải snapshot an toàn cho SQLite; `backup.sh:163-166` chấp nhận chép dở. Bản 15/10 của `ingestion_health.db` vẫn qua `integrity_check` = ok, nhưng không có gì bảo đảm điều đó.

**Cách dlt ghi (Q14, đọc mã dlt 1.29.1 đã cài trong image `data_platform`):** xem Q14. Ghi chú: comment ở `Dockerfile.dataplatform:33-37` nói image dùng dlt 1.25.0, nhưng image đang chạy dùng **1.29.1**, và `ingestion/requirements.txt:1` không ghim phiên bản. Điều này củng cố lý do cho D12.

## Q5. `monitoring_db` có trong backup đêm không: **CÓ**

- `backup.sh` chạy trong `data_platform`, `cp -a /app/var/data_lake` (`scripts/backup/backup.sh:158-166`), đi qua mount đè `monitoring_db:/app/var/data_lake/monitoring` (`docker-compose.yml:44`).
- Bản `app_data/backups/20261015-010441/app_data/data_lake/monitoring/` có `ingestion_health.db` 83.898.368 byte (mtime 15/10 01:01), `ingestion_health.duckdb` 14.168.064 byte (mtime 20/05) và `desktop.ini`. Ba file này khớp với nội dung volume (`docker run --rm -v fg-dataware-house_monitoring_db:/b:ro alpine ls -la /b`): `.db` 84.480.000 byte, `.duckdb` 14.168.064 byte. Lớp host bị che (`app_data/data_lake/monitoring`) chỉ có `.db` 0 byte (26/05) và `.duckdb` 6,8 MB (06/05), tức đã cũ.
- **Định dạng:** header `SQLite format 3`, `journal_mode=wal`. `ingestion_health.duckdb` là file DuckDB cũ, không còn ai ghi (mtime 20/05).
- **Bản sao trong backup 15/10:** `PRAGMA integrity_check` = ok, `ingestion_runs` có 86.403 dòng (16/07 → 14/10 18:01 UTC). Bản sống có 86.445 dòng (17/07 → 15/10 09:51 UTC).
- **Kích thước volume:** 98,65 MB (`docker system df -v`), `du` cho 94,1 MB.
- **Hệ quả:** bản sao hiện tại là chép nóng một file WAL. Phase 1 cần dùng `sqlite3` backup API (cùng cách với `dagster_home`), **không** dùng DuckDB `EXPORT` như design §3.1/§5. File `.duckdb` cũ có thể bỏ khỏi off-site. Lưu ý thêm: Metabase cũng mount volume này với quyền **rw** (`docker-compose.yml:85`).

## Q6. Lịch sử `monitoring` có cần giữ không

- **Có một bảng:** `ingestion_runs` (DDL ở `orchestration/ops/ingestion_health.py:88`).
- **Writer:** `record_run` (`:121`, `INSERT OR REPLACE` ở `:150`), được gọi từ các asset sapo, hug, shopee, misa, sheets, cùng `kpi_closure` và `reconciliation`.
- **Retention:** 90 ngày (`orchestration/sensors/health_db_watchdog_sensor.py:30,71-77`).
- **Reader:**
  - `asset_checks/health_db.py`, `freshness_checks.py`, `row_trend_checks.py`, `reconciliation_checks.py`, `kpi_closure_checks.py`
  - `ops/morning_digest.py` (trung vị 7 ngày, SLA 12 giờ ở `:82`)
  - watchdog sensor
- **Kết luận:** nên giữ, theo mặc định đề xuất của design. Mất bảng này thì `row_trend` và freshness không có mốc so sánh trong khoảng 7 ngày đầu, và kết quả KPI/recon 90 ngày mất theo. Chi phí nhỏ (84 MB, nén tốt). Cách chụp: SQLite backup API (Q5).

## Q7. Kích thước named volume

Nguồn: `docker system df -v`, và `du` cho vài volume.

| Volume | Kích thước | Ghi chú |
|---|---|---|
| `fg-dataware-house_dagster_home` | **11,63 GB** | `history/` 10,1 GB (`runs/index.db` 5,1 GB, `runs/` 1.527 mục, `runs.db` 12 MB); `schedules/` 321 MB; `storage/` 498 MB; `dagster.yaml` 4 KB. Xem Q16 |
| `fg-dataware-house_crm_backups` | 490 MB | 7 bản, bản mới nhất `20261015-020029` nặng 66,8 MB (giờ UTC trong container CRM) |
| `fg-dataware-house_agent_codex_config` | 168 MB | Tái tạo được (`codex login`) |
| `fg-dataware-house_monitoring_db` | 98,65 MB | Q5 |
| `fg-dataware-house_crm_data` | 90,98 MB | `crm.db`, `hug.db`, `cache.db` |
| `fg-dataware-house_crm_verify_data` | 0 B | Scratch của diễn tập CRM |
| `caddy-global_caddy_data` | 45,6 KB | Cert, tái tạo được |

Trên cùng host còn có stack `nu-*` (`nu_dagster_home` 599 MB, `nu_metabase_data` 101 MB, `nu_admin_data`) và `mkt-cockpit*`. Các stack này ngoài phạm vi; ghi lại để `host-state/` không lẫn với chúng.

### Kích thước `app_data`, backup và retention hiện tại

- **`app_data`** (`du -sh`): `backups` 14 GB; `data_lake` 1,3 GB; `metabase_data` 185 MB, gồm H2 `metabase.db.mv.db` 85 MB và hai file `trace.db` cũ tổng 108 MB (bỏ được); `input_source` 50 MB; `analysis` 1,1 MB; `secrets` 8 KB; `rill` 4 KB. Ổ `/` còn trống 210 GB / 457 GB.
- **Backup đêm:** giữ 7 bản (`BACKUP_KEEP_COUNT` mặc định 7, `scripts/backup/backup.sh:22`), mỗi bản khoảng 2,0 GB: `data_lake` 1,4 GB, `dagster_home` 568–637 MB (đã bỏ `history/`), `input_source` 50 MB, `config/` 3 file, `metabase_export/`. Không có `.env.docker` (file không được mount vào container; `config/` chỉ có `Dockerfile.dataplatform`, `Dockerfile.metabase`, `docker-compose.yml`). Vì vậy nhận định "backup.sh chép `.env.docker`" của một nguồn tham khảo là **sai**.
- **Metabase nguội:** `app_data/backups/metabase/` 96 MB, gồm 2 bản (`pre-deploy` và `weekly`, mỗi bản 48 MB do H2 được nén gọn khi dừng). Giữ 7 bản mỗi loại. Timer chạy lần tới vào CN 18/10 00:30.
- **CRM:** 7 bản trong volume `crm_backups`.

## Q8. Seed do job ghi

| Seed | Writer | Cách ghi | Lịch |
|---|---|---|---|
| `transformation/seeds/tenants/fine_japan/seed_cashflow_budget.csv`, `seed_cash_allocation_policy.csv` | Budget sync `ingestion/src/gsheet_budget_sync/__init__.py:109-110` (`seed_path`, `ingestion/src/utils/seed_paths.py:27`) | Ghi tạm rồi `os.replace` (`merge.py:35-37`) | Hằng ngày 02:30 (`orchestration/connectors/sheets/jobs.py:70`). `ingestion_runs` xác nhận: `sheets/budget_sheet_sync_asset` chạy lần cuối 14/10 19:30 UTC |
| `transformation/seeds/taxonomy/ref_order_sources.csv`, `ref_branch_locations.csv` | `scripts/maintenance/sync_seeds.py:89,114` | `to_csv(mode='a')`, không nguyên tử | Chỉ chạy tay trên host (`scripts/run_pipeline.ps1:61`) |

- Trên prod lúc kiểm, `git status --short transformation/seeds` **rỗng**. Không có seed nào lệch git, cũng không có seed chưa commit (`git ls-files --others` rỗng).
- `git log` cho thấy lần commit seed gần nhất là `07a3948f` (15/10 12:37).
- Seed **có trong git, nhưng không có trong backup nào**: `backup.sh` không chép `transformation/`.
- Off-site nên chép cả cây `transformation/seeds` cùng `git diff`, như design §4 đã đề xuất. Lý do: budget sync có thể làm seed lệch git trong khoảng giữa hai lần commit.

## Q9. File chỉ có trên máy (bị gitignore, ngoài `app_data/`)

Liệt kê bằng `git status --short --ignored`, đã lọc cache và venv.

| File | Dùng ở đâu | Có cần cho off-site |
|---|---|---|
| `.env` (8 biến: `HUG_ADMIN_SECRET`, `CRM_REFRESH_TOKEN`, `CRM_API_TOKEN`, `DRILL_TOKEN`, `CF_ACCESS_*`, `CRM_ADMIN_EMAILS`) | Compose nội suy `${...}` (`docker-compose.yml:218-227,277`) | **Có** (secret) |
| `.env.docker` (37 biến, gồm Sapo, Lark, Metabase API key, URL Sheet, `CLOUDFLARE_API_TOKEN`, `FILESERVER_PASSWORD_HASH`, `WORKER_POLL_TOKEN`) | `env_file` của các service (`docker-compose.yml:16-17,78-79,163-164,184-185`); `caddy-global` lấy `CLOUDFLARE_API_TOKEN` qua `--env-file .env.docker` (`caddy-global/docker-compose.yml`, comment) | **Có** (secret) |
| `.env.local` (29 biến, gồm thông tin đăng nhập Sapo, `BACKUP_ROOT`) | **Không** có trong compose hay script nào. Chỉ có trong plan đã lưu trữ (`plans/archive/260416-1102-config-ecosystem-reorganization/`) và một comment ở `conftest.py:11` | Không cần để chạy prod. Là file dev cũ chứa secret. Đề xuất: không đưa lên, và hỏi user có xoá không |
| `app_data/secrets/gsheets-service-account.json` | Đường dẫn trong `GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH` | **Có** (secret). Lưu ý: quyền đang là **0644**, nên là 0600 |
| `evidence/sources/datalake/olap-serving.duckdb` | Evidence | Không (phái sinh) |
| `rill/tmp/`, `transformation/logs/`, `plans/.../herdr-cook-runs/`, `.agentkit/adapters/`, `.claude/...` | Cache, log, công cụ | Không |

Ngoài repo: `/home/vantt/cloudflared-tunnel/` (Q10). Đây là state mức host, **không** có trong backup nào.

## Q10. Cấu hình mức host

- **Caddy toàn cục:**
  - Compose nằm **trong repo** và đã được track: `caddy-global/{docker-compose.yml,Dockerfile.caddy,base.Caddyfile}`.
  - Kết quả `docker inspect`: `working_dir=/home/vantt/app/fg-dataware-house/caddy-global`, image `caddy-global:dns01` build từ `Dockerfile.caddy`, mạng `caddy_net` (external), mount `docker.sock`.
  - Token: `CLOUDFLARE_API_TOKEN` nội suy từ `.env.docker`. Volume `caddy_data` 45 KB.
- **cloudflared:**
  - Compose ở `/home/vantt/cloudflared-tunnel/docker-compose.yml`, **ngoài repo, không có git**. Image `cloudflare/cloudflared:latest` (không ghim), `network_mode: host`.
  - Thư mục `config/` có ba file: `<tunnel-id>.json` (credentials, quyền 0444), `cert.pem` (0644), `config.yml`.
  - Tunnel là loại quản lý tại chỗ, **không** dùng token trong `.env.docker`. Comment `docker-compose.yml:140` nói về `CLOUDFLARE_TUNNEL_TOKEN`, nhưng biến này không có.
  - Ingress phục vụ cả host **ngoài dự án**: `crm.fwg.vn`→3007, `bi.fwg.vn`→3001, `vnflow.fwg.vn`→192.168.20.175:8100, `hermes.fwg.vn`→100.66.22.20:9119 (qua Tailscale), `fgos.fwg.vn`→8765.
- **Tailscale:** `tailscaled` active, node `fg-server` 100.121.46.35.
- **systemd user:** dự án có `metabase-cold-backup.{service,timer}`. `skillhub-server.service` không thuộc dự án. Không có crontab. `Linger=yes`.
- **Docker:** `/etc/docker/` rỗng (daemon dùng cấu hình mặc định), phiên bản 29.7.2, driver `overlayfs`, root `/var/lib/docker`.

## Q11. Lần diễn tập CRM gần nhất: **PASS**

- `crm_backup_job` gồm hai asset `crm_backup` và `crm_restore_verify` (`orchestration/packs/crm/jobs.py:11-14`).
- Lần chạy gần nhất `844cbef3`, 15/10 09:00:27–09:00:40, SUCCESS. Metadata của `crm_restore_verify`: `"status":"pass","exit_code":0`, backup `20261015-020029`.
  - Gate A: `crm.db` có 55.874 dòng, `hug.db` 50 dòng, `cache.db` 254.802 dòng; sha, checksum và số dòng đều khớp.
  - Gate B: `/healthz` ready, đọc OK (`crm_party` 7.738 dòng), thử ghi OK.
- Lần trước (14/10 09:00, run `77e6dbff`) cũng SUCCESS.
- **Lệch giờ:** cron `0 2 * * *` không có `execution_timezone` (`orchestration/packs/crm/jobs.py:15-20`). Mọi schedule khác đều đặt `Asia/Ho_Chi_Minh`. Kết quả là job chạy lúc **09:00 giờ VN**, giữa giờ làm việc.

## Q12. Thời điểm kết thúc nightly

- **Dagster:** chỉ còn 1.528 run, từ 14/10 08:03 (`PURGE_KEEP_DAYS` mặc định 1, `orchestration/ops/purge_runs.py:464`; compose không đặt biến này). Số mẫu `pipeline_batch_nightly_job` theo lịch: **1**, ngày 15/10, chạy 03:00:55 → **03:06:08** (5,2 phút). Cả 9 run SUCCESS (tính cả run chạy tay) dài 5,0–5,5 phút, p50 5,2 phút.
- **Số liệu thay thế 77 đêm:** đọc bảng `ingestion_runs` trên bản sao chỉ đọc. Bảng ghi `run_started_at`/`run_ended_at` của các asset batch trong nightly (cùng `run_id` Dagster: run `ffb92b66` ngày 15/10 có trong bảng).
  - Thời điểm kết thúc giai đoạn ingestion của nightly, qua 77 đêm: p50 **03:01:51**, p95 **03:10:01**, max **03:12:18**.
  - 14 đêm gần nhất (02/10 → 15/10): p50 03:01:53, max 03:02:02.
  - Ngày 15/10 phần dbt và serving sau ingestion mất khoảng 4,3 phút (03:01:51 → 03:06:08).
- **Ước tính kết thúc nightly:** p50 khoảng 03:06, p95 khoảng 03:14, max khoảng 03:17. Mọi giá trị đều trước 03:20, nên **giữ 03:30**.
- **Lưu ý cho cửa sổ 03:30:** trong 03:00–03:45 ngày 15/10 có 13 run `pipeline_sapo_v2_realtime_job` và 12 run `pipeline_hug_realtime_job`. Incremental và hourly bỏ giờ 3 (`sapo_v2/jobs.py:82,102`). Vì vậy lúc 03:30–03:59 writer raw duy nhất là realtime, ghi Delta nguyên tử (Q14), cùng các sensor file-drop/Sheets khi có file mới.

## Q13. Thời gian backup cục bộ

Không đọc được từ Dagster (chỉ còn 1 run: 15/10 01:04:38 → 01:05:06, 28 giây). Tôi dùng 7 file `app_data/backups/backup-*.log` (09/10 → 15/10):

| Chỉ số | Giá trị |
|---|---|
| Thời lượng | 17–24 giây |
| Giờ bắt đầu | 01:03–01:07 |
| Thời gian chép `data_lake` (1,4 GB) | 3–5 giây |
| Thời gian chép `dagster_home` | 13–16 giây |

Ngày 12/10 backup chạy lúc **06:05** (`maintain_backup_fallback_schedule`, `orchestration/definitions.py:218`): sensor sau purge hôm đó không kích. Lịch sử run đã bị purge nên không tìm được lý do.

## Q14. dlt ghi file thế nào

Nguồn: mã dlt **1.29.1** và deltalake 1.6.2, đọc trong image đang chạy.

- **Parquet thường** (batch, file drop, Sheets): `FilesystemLoadJob.run` gọi `fs_client.put_file(local, remote)` (`dlt/destinations/impl/filesystem/filesystem.py:134`). Với ổ local, fsspec làm `put_file` → `cp_file` → `shutil.copyfile(path1, path2)`, tức **ghi thẳng vào tên cuối, không có file tạm hay đổi tên**. Một lần đọc chen giữa có thể thấy file parquet dở, và **không có pattern tên nào để `--exclude`**.
- **Bảng Delta** (`table_format="delta"`: `ingestion/src/sapo/webhook_consumer.py:123,236`, `history_log.py:149`, `ingestion/src/hug/hug_webhook_consumer.py:82,203`): ghi qua `write_delta_table` (`filesystem.py:204-240`, deltalake/object_store). File dữ liệu ghi trước, commit `_delta_log/*.json` sau.
  - Trên đĩa không thấy file tạm nào sót lại.
  - **[suy luận, chưa đọc mã Rust]** object_store local ghi vào file tạm rồi đổi tên, nên có tính nguyên tử.
  - `_delta_log` của `unknown` có 852 mục, nhưng version đã lên tới 4740. Như vậy log cũ **bị dọn** sau checkpoint: raw Delta không thuần "chỉ thêm".
  - Danh sách bảng Delta: `sapo_v2_raw/{order,fulfillment,customer,unknown,product,purchase_order,order_return,location,customer_group,stock_adjustment,account,delivery_collation,price_list,customer_address}` và `hug_raw/scan`.
- **State:** `complete_load` (`filesystem.py:1138-1140`) ghi `_dlt_loads` và `_dlt_pipeline_state/<pipeline>__<load_id>.jsonl` (`_write_to_json_file` → `write_text`, `:1096-1097`) **sau** khi các job dữ liệu xong, rồi dọn state cũ (`max_state_files`, `:1154-1176`).
  - Nếu snapshot có state thì dữ liệu của lần load đó đã nằm trên đĩa, có thể bị chụp dở.
  - Nếu snapshot có dữ liệu mà thiếu state, khi khôi phục dlt sẽ lấy lại khoảng đó, và vì `append` nên có thể **ghi trùng**.
- **Thư mục làm việc của dlt:** `get_dlt_pipelines_dir()` (`pipeline_runner.py:89,122`), không đặt `DLT_DATA_DIR`. Trong container `/root/.dlt` hiện không tồn tại; thư mục này nằm ở lớp ghi của container, không có trong volume. State thật nằm ở destination (`pipeline_runner.py:118`).
- **Hệ quả cho design §5 và §11:**
  - Không dùng `--exclude-file` cho file tạm.
  - Thay vào đó: chạy off-site lúc không có writer parquet thường (03:30 thoả, Q12), và T2 đọc mọi file parquet để bắt file dở.
  - Hoặc sidecar giữ một "khoá raw" nhẹ. Hiện không có cơ chế này, nên đề xuất cách thứ nhất.
  - Khi khôi phục, chạy dbt dedup theo khoá: staging `delete+insert` theo khoá nghiệp vụ đã khử trùng (Q3).

## Q15. Lùi cursor dlt theo khoảng thời gian

**Không có cách nào.**
- `pipeline_runner.py:40-44` chỉ có các cờ `--full-refresh` (cần `--force`, xoá destination), `--reset-cursor`, `--limit`, `--dev`.
- `--reset-cursor` (`:70-111`) xoá state cục bộ và `_dlt_pipeline_state/*.jsonl`, rồi tải lại **toàn bộ** từ đầu.
- Các cursor Sapo đều là `dlt.sources.incremental("sync_metadata.event_timestamp")` và không có tham số ngày: `orders.py:97`, `customers.py:108`, `products.py:89`, `accounts.py:71`, `history_log.py:179`.

Ngoại lệ:
- Kho Sapo `ingestion/run_sapo_v2_inventory_transactions_batch.py` có `--window custom --start/--end` (`ingestion/src/sapo/sapo_v2_inventory_transactions.py:114-130,246-268`). Không dùng incremental, chạy lại thì ghi trùng.
- MISA có script backfill tay `--from/--to YYYY-MM` (`ingestion/run-misa-account-ledger-backfill.py:60-62`).
- Shopee và HUG chỉ có file drop hoặc webhook.

**Hệ quả:** design §8.3 ("kéo bù snapshot − 48 giờ") chưa có cơ chế. Phase 3 phải thêm một trong hai:
1. Cờ `--rewind-hours N`: sửa giá trị `last_value` trong state jsonl mới nhất trước khi chạy.
2. Chấp nhận để dlt tự lấy từ cursor trong snapshot. State được ghi sau dữ liệu (Q14) nên không có khoảng hở; chỉ có nguy cơ trùng, và staging khử trùng.

Đề xuất cách 2 làm mặc định, cách 1 là tuỳ chọn. Cần user hoặc phase 3 chốt.

## Q16. `dagster_home` ngoài `history/`

Nguồn: `docker run --rm -v fg-dataware-house_dagster_home:/b:ro alpine ...`.

| Thành phần | Kích thước | Cần? |
|---|---|---|
| `dagster.yaml` | 4 KB | Không cần riêng: giống hệt `orchestration/dagster.yaml`, compose chép nếu thiếu (`docker-compose.yml:63`) |
| `schedules/schedules.db` | 321 MB | **Cần.** Gồm trạng thái bật/tắt schedule/sensor, cursor sensor và tick (lịch sử tick dọn sau 30 ngày, `dagster.yaml` `retention`). `schedule_state.db` 0 byte |
| `storage/` | 498 MB | Phần lớn **không cần.** Gồm 1.551 thư mục `<run_id>/compute_logs`, cùng output IO manager theo asset (`storage/sapo/*`, `storage/crm_*`, `storage/__repository__/{health_alert_failure_sensor,trigger_backup_after_purge}`), đều được tạo lại ở lần chạy sau |
| `history/runs.db` và `history/runs/*.db` | 10,1 GB | Backup hiện bỏ (`backup.sh:36-42`). Run bị purge sau 1 ngày nên không cần |
| `history/runs/index.db` | 5,1 GB | Nằm trong `history/` nên **cũng bị bỏ.** Đây là event log index: lịch sử materialization và asset check, cùng bảng concurrency slot (`duckdb_lock` được đặt lại lúc boot). Mất nó thì UI không còn "last materialized", và sensor dựa trên materialization có thể chạy lại. Chấp nhận được (plan đã loại "backup lịch sử run Dagster"), nhưng cần ghi rõ trong runbook |
| `logs/`, `.logs_queue/`, `.nux/` | Rỗng | Không |

**Đề xuất cho phase 1:** chụp bằng SQLite backup API chỉ `schedules/schedules.db` (khoảng 321 MB, hoặc nhỏ hơn sau `VACUUM INTO`). Bỏ `storage/`. Bản `dagster_home` trong backup cục bộ sẽ giảm từ khoảng 570 MB xuống khoảng 320 MB.

## Q17. Đường ghi ra ngoài phải tắt khi diễn tập

| Tác dụng | Vị trí | Mức nguy hiểm |
|---|---|---|
| Kết nối thêm vào Cloudflare Tunnel | `/home/vantt/cloudflared-tunnel/config` (credentials file) | Cao: chia traffic thật. Diễn tập không chạy `cloudflared` |
| **Ack webhook Sapo, xoá hàng đợi trên Worker** | `ingestion/src/sapo/webhook_consumer.py:50-58,348`; `WORKER_URL` (`run_sapo_v2_webhook_consumer.py:23`) | **Cao: mất sự kiện của prod** |
| **Ack webhook HUG** | `ingestion/src/hug/hug_webhook_consumer.py:315`; `run_hug_webhook_consumer.py:40,77` | **Cao** |
| Đẩy HUG D1 (POST có ký) | `crm/src/hug/d1_push.py:74,78`, `d1_transport.py:64,107`; `HUG_WORKER_URL` (`docker-compose.yml:228`, `https://hug.fjp.vn`). Bỏ biến thì `push_enabled()` trả false (`d1_push.py:66`) | Cao |
| **Ghi Google Sheet** | Budget sync hằng ngày 02:30 ghi tab `__REF` (`orchestration/connectors/sheets/assets.py:294` → `gsheet_budget_sync/__init__.py:230` → `sheet_writeback.py:61,80-81`); `budget_suggestion_writeback_asset` ngày 1 hằng tháng 08:00 (`sheets/jobs.py:86`, `assets.py:360`). Docstring ghi "chỉ đọc" là sai | **Cao.** Design §8.2 ghi "[chưa xác minh có ghi]": **đã xác minh là CÓ ghi** |
| Lark | `orchestration/notifications/lark_client.py:62-63,103` (`LARK_ALERT_WEBHOOK`, `LARK_ALERT_SECRET`) | Trung bình |
| ACME DNS-01 qua Cloudflare API (`caddy-global`, `CLOUDFLARE_API_TOKEN`) | `caddy-global/docker-compose.yml`, `base.Caddyfile` | Trung bình: ghi bản ghi TXT lên DNS thật. Diễn tập không chạy `caddy-global` với token thật |
| Metabase subscription/email | `metabase_export/manifest.json` 15/10: `subscriptions: 0`. Không có mã SMTP trong repo | Thấp hiện tại; vẫn tắt SMTP |
| Gọi API Sapo (login, đọc) | `ingestion/.dlt/config.toml`, `SOURCES__SAPO__*` | Chỉ đọc, nhưng dùng tài khoản thật và tốn quota. Drill nên chặn mạng |
| POST nội bộ của CRM (refresh, backup, drill) | `orchestration/packs/crm/crm_sync.py:50-57,119-122,157-165`; URL ở `orchestration/tenants/fine_japan/config.py:15-17` | Nội bộ (an toàn nếu mạng drill tách riêng) |

Kết luận: danh sách `--mode drill` cần thêm `WORKER_URL`, `WORKER_POLL_TOKEN`, `GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH` (hoặc không mount `app_data/secrets`), `CLOUDFLARE_API_TOKEN`, và **tắt các schedule/sensor của consumer webhook trước khi bật bất kỳ schedule nào**. T2/T3 dùng `--network none` đã chặn được hết.

## Q18. Kích thước image

Nguồn: `docker image ls`. Kích thước chưa nén.

| Image | Kích thước |
|---|---|
| `fg-dataware-house-data_platform` | 4,47 GB |
| `fg-dataware-house-metabase` | 3,11 GB |
| `fg-dataware-house-evidence` | 2,9 GB |
| `fg-dataware-house-rill` | 1,73 GB |
| `fg-dataware-house-crm` | 612 MB |
| `fg-dataware-house-detail_view` | 347 MB |
| `fg-dataware-house-crm_drill_runner` | 307 MB |
| **Tổng image `fg-dataware-house-*`** | **khoảng 13,5 GB** |
| `caddy-global:dns01` | 155 MB |
| `cloudflare/cloudflared:latest` | 96 MB |
| `caddy:alpine` | 89 MB |

`docker save` nén thường còn khoảng 40–50%, và các layer base dùng chung giữa các image. **Ước tính D12 là 5–7 GB cho lần đầu**, sau đó chỉ thêm phần digest đổi. Con số "2–4 GB" trong design §10 và câu hỏi mở 5 cần sửa. Có thể chỉ lưu `data_platform`, `metabase` và `crm` (khoảng 8,2 GB chưa nén, ước 3,5–4,5 GB nén); evidence và rill build lại được, và hỏng thì cũng không chặn RTO.

## Q19. `app_data/analysis`

- **Nội dung:** `misa-cashflow/So_chi_tiet__202606.xlsx`, `So_chi_tiet_11_202606.xlsx` và `backfill/So_chi_tiet__20260{1..5}.xlsx`, tổng 1,1 MB. Đây là sổ chi tiết MISA xuất tay, dùng để backfill (`plans/archive/260702-1727-misa-cashflow-budget-planner/`).
- **Ai ghi:** không có writer trong code, và thư mục này không được mount vào container. Đây là file nhập tay, là đầu vào gốc của `misa_raw/account_ledger` (các file 03/07).
- **Có trong backup không:** không. `backup.sh` chỉ chép `data_lake`, `dagster_home`, `input_source`.
- **Đề xuất:** đưa lên off-site, vì là nguồn nhập tay, nhỏ và không lấy lại tự động được (MISA download chỉ có từ 08/2026, xem `ingestion_runs`: `misa_*_download_asset` chạy từ 01/08).

---

## Bản nháp `scripts/backup/offsite-include.txt`

Phase 2 sẽ tạo file thật. Đường dẫn trong bản nháp tính theo mount của sidecar ở design §6.

```text
# --- Nguồn sự thật: raw lake (đọc thẳng :ro) ---
/src/lake/sapo_v2_raw          # Sapo API + webhook; history_log không lấy lại được (Sapo cắt lịch sử)
/src/lake/hug_raw              # sự kiện webhook HUG đã ack trên Worker, không lấy lại được
/src/lake/gsheet_raw           # ảnh chụp Google Sheet; giá trị cũ của Sheet không còn
/src/lake/misa_raw             # phái sinh từ input_source + analysis, giữ để khỏi nạp lại (3,4 MB)
/src/lake/shopee_raw           # phái sinh từ input_source/shopee, rẻ (0,6 MB)
/src/lake/backup               # ảnh chụp tay 13/04 trước migration, 21 MB; chờ user quyết
# --- Nhập tay ---
/src/input                     # app_data/input_source (50 MB)
/src/project/app_data/analysis # sổ MISA xlsx dùng backfill (1,1 MB); cần thêm mount
# --- Bản chụp nhất quán do phase 1 tạo (staging) ---
/staging/dagster_home          # chỉ schedules.db (SQLite backup API)
/staging/monitoring            # ingestion_health.db (SQLite backup API; KHÔNG phải DuckDB)
/staging/exports/warehouse     # monitor_taxonomy_parity_log (DuckDB COPY ... TO parquet)
/staging/metabase              # bản H2 nguội mới nhất + manifest
/staging/metabase_export       # JSON API của bản đêm mới nhất
/staging/crm                   # bản CRM mới nhất đã qua gate
/staging/repo-state            # HEAD sha, git status --porcelain, git diff
/staging/host-state            # unit systemd user, linger, danh sách stack phụ thuộc
# --- Seed và cấu hình ---
/src/project/transformation/seeds   # bị budget sync ghi đè giữa các lần commit
/src/project/docker-compose.yml
/src/project/caddy-global           # đã có trong git; giữ để khớp sha
# --- Secret (chỉ trong repo mã hoá) ---
/src/project/.env
/src/project/.env.docker
/src/secrets                        # gsheets-service-account.json
/host/cloudflared-tunnel            # credentials tunnel + config.yml; cần mount riêng :ro

# --- Loại trừ (exclude) ---
/src/lake/sapo_warehouse.duckdb     # phái sinh (dbt); chỉ xuất bảng log ở trên
/src/lake/sapo_warehouse.duckdb.wal
/src/lake/serving                   # phái sinh
/src/lake/export                    # phái sinh; rolling chỉ giữ 3 lần build, không có lịch sử
/src/lake/crm_export                # phái sinh từ crm.db
/src/lake/monitoring                # lớp host đã cũ; bản thật lấy từ /staging/monitoring
/src/lake/sapo_raw_staging          # mồ côi
/src/lake/test_raw                  # mồ côi
**/desktop.ini
# Không có pattern file tạm của dlt để loại: parquet ghi thẳng tên cuối (Q14)
```

Không đưa lên: `.env.local` (dev cũ), `agent_codex_config`, `caddy_data`, `crm_verify_data`, `metabase.db.trace.db*`, `rill/`, `evidence/sources/.../olap-serving.duckdb`, `history/` của Dagster.

## Những gì đổi ở các phase sau

1. **Phase 1:**
   - `ingestion_health.db` dùng SQLite backup API cùng helper với `dagster_home` (`sqlite_snapshot.py`), và bỏ ý định `EXPORT` DuckDB cho monitoring.
   - `duckdb_snapshot.py` chỉ cần xuất **một** bảng (`main.monitor_taxonomy_parity_log`) từ `sapo_warehouse.duckdb`. Nên chạy trong op đang giữ `duckdb_lock`; mở `read_only` sẽ fail nếu đang có writer, vì DuckDB khoá file độc quyền khi ghi.
   - `dagster_home` chỉ chụp `schedules.db`.
   - Thêm `app_data/analysis` vào bản cục bộ hoặc off-site (cần mount).
2. **Phase 2:**
   - Mount thêm `app_data/analysis` và `/home/vantt/cloudflared-tunnel` (tham số hoá đường dẫn, vì đường này nằm ngoài repo).
   - Không có `--exclude-file` cho file tạm dlt.
   - Preflight tuổi CRM tính theo giờ thật 09:00. Nếu user cho sửa timezone thì đổi lại 02:00.
   - Giữ 03:30: nightly p95 ước khoảng 03:14, và trong giờ 3 không có writer parquet thường.
3. **Phase 3:**
   - Kéo bù sau khôi phục: không có cơ chế lùi cursor theo giờ; chọn "dlt tự lấy từ cursor trong snapshot, staging khử trùng" hoặc thêm `--rewind-hours`.
   - Áp `monitoring` vào **named volume** `monitoring_db`, không phải `app_data/data_lake/monitoring`.
   - H2 thuộc uid lạ trên host (`dnsmasq:systemd-journal`, tức uid của container), nên `apply` phải giữ đúng owner.
4. **Phase 4 (T2):** đọc mọi file parquet raw là cách duy nhất bắt file chụp dở, nên phải giữ. Thêm kiểm `_delta_log` của từng bảng Delta: mở được bằng deltalake, và mọi file được tham chiếu đều có trong snapshot.
5. **Phase 6:**
   - Runbook dựng lại phải gồm cloudflared (credentials file, tunnel phục vụ thêm vnflow/hermes/fgos) và Tailscale.
   - Danh sách drill thêm `WORKER_URL`, `WORKER_POLL_TOKEN`, key Sheets, `CLOUDFLARE_API_TOKEN`, và không chạy consumer webhook.
   - D12 khoảng 5–7 GB.
6. **Design cần sửa** (phase 0 bước 3, chưa làm theo chỉ đạo lần này):
   - §3.1, §5: monitoring là SQLite.
   - §4: phân loại theo bảng Q1. Snapshot không có lịch sử. Có bảng parity log. Thêm `analysis` và `cloudflared`. `.env.local` không cần.
   - §5, §7: CRM 09:00.
   - §7: số đo nightly.
   - §8.2: thêm các mục ở Q17.
   - §8.3: chưa có cơ chế lùi cursor.
   - §10: D12, dung lượng `dagster_home`.
   - Trích dẫn compose lệch dòng: `monitoring_db` ở `:44` (không phải `:39`), `dagster_home` ở `:48` (không phải `:43`).

## Câu hỏi cho user

1. **Giờ CRM backup:** sửa `crm_backup_schedule` thêm `execution_timezone="Asia/Ho_Chi_Minh"` để chạy 02:00 như ý định ban đầu, hay giữ 09:00? Đây là đổi schedule hiện có, nên cần anh duyệt. Đề xuất: sửa, trong một deploy riêng.
2. **Lịch sử giá/tồn kho:** `fact_variant_prices_snapshot` và `fact_inventory_snapshot` không giữ lịch sử, trái với comment trong model. Anh có cần lịch sử này không? Nếu cần thì đó là một plan sửa model riêng; plan backup sẽ đưa bảng lên off-site sau khi model được sửa.
3. **`data_lake/backup` (ảnh chụp tay Sapo 13/04, 21 MB):** giữ trên off-site, hay xoá vì đã qua migration?
4. **`.env.local`:** file dev cũ chứa thông tin đăng nhập Sapo, không còn dùng ở prod. Xoá, hay giữ mà không đưa lên off-site?
5. **cloudflared** phục vụ cả `vnflow`, `hermes`, `fgos` (ngoài dự án). Backup credentials tunnel trong repo restic của Fine Japan có phù hợp không (credentials này không phải của khách), hay để FG giữ riêng?
6. **Quyền file secret:** `app_data/secrets/gsheets-service-account.json` đang 0644, credentials tunnel 0444. Có cho sửa thành 0600 (thay đổi trên prod, cần giờ duyệt) không? *(Bổ sung sau khi user trả lời: container `cloudflared` chạy uid 65532 còn file thuộc `vantt`, nên `0600` giữ chủ `vantt` sẽ làm tunnel không khởi động lại được; xem câu hỏi mở 6 trong `plan.md`.)*
7. **D12:** với ước tính mới 5–7 GB (hoặc khoảng 4 GB nếu chỉ lưu data_platform, metabase, crm), anh có còn đồng ý không?

Status: DONE_WITH_CONCERNS
Summary: Đã trả lời đủ Q1–Q19 và 6 câu hỏi của user bằng bằng chứng chỉ đọc từ prod. Chỉ một bảng thực sự không dựng lại được (`monitor_taxonomy_parity_log`); monitoring là SQLite và đã nằm trong backup đêm; CRM backup thực chạy 09:00.
Concerns/Blockers: Không đo được p95 nightly 14 đêm từ Dagster (lịch sử chỉ còn khoảng 1,4 ngày), nên dùng số liệu thay thế 77 đêm từ `ingestion_runs` cộng 1 mẫu Dagster. Tính nguyên tử của object_store khi ghi Delta là suy luận, chưa đọc mã Rust. Các bước còn lại của phase 0 (worktree, sửa `design.md`/`plan.md`, khung `backup-and-recovery.md`, ADR 019) chưa làm theo chỉ đạo lần này.
