# Thiết kế: Backup, khôi phục và tái dựng hệ thống

> Ngày 15/10/2026. Phạm vi: mục "Backup, khôi phục và tái dựng hệ thống" trong [roadmap](../261013-1751-modularize-data-platform-suite/roadmap.md). Đầu vào: [đánh giá hiện trạng](../reports/assessment-261015-1045-backup-restore-current-state.md), [nghiên cứu](../reports/research-261015-1040-offsite-backup-restore-dr.md), [phương pháp gate chain](../../docs/operations/backup-restore-completeness-runbook.md). Plan này **thay thế** stub `plans/260624-2010-warehouse-pipeline-dr-verified-restore/` (giữ hướng parquet-first và các bài học mang sang của stub đó, xem §2 D2).
>
> Trích dẫn `file:dòng` theo checkout prod ngày 15/10/2026. Các điểm chưa xác minh của bản đầu đã được phase 0 kiểm trên prod (chỉ đọc) và thay bằng kết quả; bằng chứng từng câu ở [reports/phase-00-findings.md](reports/phase-00-findings.md) (viết tắt "F-Qn" bên dưới). Quyết định của user sau phase 0 ghi ở [plan.md](plan.md) mục "Đã chốt".

## 1. Mục tiêu và tiêu chí "xong"

Khách nào (Fine Japan là khách đầu tiên) mất máy hoặc hỏng ổ cũng dựng lại được hệ thống trong thời gian đã định trước, với lượng dữ liệu mất tối đa đã định trước, và việc đó đã được **thử thật** trên bản ngoài máy chứ không chỉ có script.

"Xong" nghĩa là đo được:

1. Backup ngoài máy của Fine Japan xanh 14 ngày liên tiếp.
2. Diễn tập khôi phục hằng tuần từ bản ngoài máy PASS hai lần liên tiếp, và các phép thử phá dữ liệu (tamper) đều làm diễn tập FAIL.
3. Một lần diễn tập dựng lại từ con số 0 trên máy khác xong trong RTO (8 giờ làm việc), có nhật ký thời gian và biên bản.

Chi tiết nghiệm thu ở [plan.md](plan.md).

**Không làm trong plan này:** chuyển Metabase sang Postgres; dịch vụ backup có quản lý do FG vận hành (user đã loại); đích phụ append-only/Object Lock chống ransomware (để tuỳ chọn sau); giám sát tập trung nhiều khách (Đợt 8, plan này chỉ để sẵn file trạng thái làm đầu vào); CLI cài đặt hoàn chỉnh `init/doctor/upgrade` (Đợt 5, plan này làm phần lõi khôi phục mà CLI đó sẽ gọi lại); ý kiến luật sư (user hoãn 15/10).

## 2. Quyết định

| # | Quyết định | Lý do | Nguồn |
|---|---|---|---|
| D1 | **restic 0.19.x + rclone**, một bộ script cho mọi đích; đổi đích chỉ bằng `RESTIC_REPOSITORY` và remote rclone | Mã hoá phía client luôn bật, dedup, `check --read-data-subset`, nhiều khoá trên một repo | Nghiên cứu §2 |
| D2 | **Parquet-first:** off-site chỉ chứa nguồn sự thật; DuckDB phái sinh (`sapo_warehouse.duckdb`, `serving/olap.duckdb`, `export/`, bản standalone) **không** lên off-site mà dựng lại bằng dbt. **Ngoại lệ (phase 0 đã chốt):** bảng phái sinh nhưng không dựng lại được được xuất ra parquet và lên off-site. Hôm nay chỉ có **một** bảng: `main.monitor_taxonomy_parity_log` trong `sapo_warehouse.duckdb` (incremental `full_refresh=false`, `run_at = current_timestamp`, F-Q3). `fact_variant_prices_snapshot` và `fact_inventory_snapshot` **không** là ngoại lệ: GC rolling chỉ giữ 3 lần build (`scripts/provisioning/refresh_rolling.py:54,69-95`), nên không có lịch sử để giữ (F-Q2); user cần lịch sử này và đã tách thành plan riêng sửa model, plan đó sẽ thêm bảng vào danh sách xuất | Đúng quyết định của stub 260624 và runbook completeness Part 2 §2.1; dedup kém trên file DuckDB bị ghi lại mỗi đêm | Stub 260624 `plan.md`; nghiên cứu §7.4; F-Q2, F-Q3 |
| D3 | Đích mặc định cho khách Gmail: **Google Drive qua OAuth**, app OAuth do FG sở hữu và publish, scope `drive.file`. Fine Japan (có Workspace): **service account + Shared Drive** cho lần triển khai đầu | User chốt 15/10 | Roadmap mục Backup |
| D4 | Khách có dữ liệu nhạy cảm hoặc từ 100.000 chủ thể dữ liệu trở lên: đích **S3 trong nước hoặc NAS**, không dùng Google Drive | Mặc định an toàn trong khi chưa có ý kiến luật sư (user hoãn 15/10) | Roadmap; nghiên cứu §6.2 |
| D5 | **Khách sở hữu repo và giữ khoá.** FG không giữ khoá, không vận hành backup thay khách. Bàn giao phải có biên bản khách ký nhận việc giữ khoá và **một lần khôi phục thử có khách chứng kiến**, mở repo bằng khoá của khách | User chốt 15/10 | Roadmap |
| D6 | Secret (`.env`, `.env.docker`, `app_data/secrets/`, và credentials Cloudflare tunnel ở `${FG_CLOUDFLARED_DIR}`, trên prod là `/home/vantt/cloudflared-tunnel/config`) **chỉ** nằm trong repo restic đã mã hoá; không bao giờ có bản rõ ngoài máy hay trong thư mục backup cục bộ. `.env.local` (file dev cũ, prod không dùng) **không** đưa vào backup. File secret trên host về quyền 0600 qua runbook (sau khi kiểm container vẫn đọc được) | User chốt 14/10 và 15/10 sau phase 0 | Roadmap mục "Việc vận hành độc lập"; F-Q9, F-Q10 |
| D7 | Điều phối bằng **systemd timer trên host** gọi `docker compose --profile ops run --rm backup <lệnh>`. Sidecar `backup` **không** có Docker socket; `data_platform` cũng không | Timer vẫn chạy khi Dagster hỏng; giữ nguyên giới hạn socket chỉ ở `crm_drill_runner` (`docker-compose.yml:278`) | Nghiên cứu §5.1 |
| D8 | Mỗi thành phần có trạng thái được **chụp nhất quán ở nơi sở hữu nó**, ghi vào vùng staging kèm `manifest.json`; sidecar off-site chỉ đọc bản đã chụp (trừ raw parquet, đọc thẳng vì chỉ thêm file) | Tái dùng gate chain đã chứng minh với CRM; sidecar không phải mở DB đang chạy | Runbook completeness §2 |
| D9 | Khôi phục luôn đi hai bước: **giải nén vào thư mục scratch** (an toàn, mặc định) rồi mới **áp vào prod** theo từng thành phần, có bản an toàn trước khi ghi đè | Không thao tác nào trên prod mà chưa kiểm manifest | Runbook CRM `crm/docs/backup-restore-runbook.md:54-68` |
| D10 | **Cài mới và dựng lại dùng chung một công cụ**: cài mới là "khôi phục từ snapshot rỗng". Đợt 5 bọc lại công cụ này, không viết bộ thứ hai | Mỗi lần cài khách mới cũng là một lần thử đường DR | Nghiên cứu §7.3; roadmap Đợt 5 |
| D11 | Cảnh báo hai kênh độc lập: **Lark** (lỗi chủ động) và **dead-man healthchecks.io** (bắt cả trường hợp máy chết, job không chạy). Tài khoản healthchecks thuộc **khách** | Một backup ngừng chạy mà không ai biết thì coi như không có | Nghiên cứu §5.4; D5 |
| D12 | **Không lưu image Docker** lên off-site. Khôi phục build lại image từ git ở đúng sha của snapshot; rủi ro build ra phiên bản khác được giảm bằng ghim base image theo digest và ghim phiên bản dependency đang chạy (phase 6), phần còn lại do Đợt 2 | Image dự án ~13,5 GB chưa nén, ước 5–7 GB nén cho lần đầu (F-Q18), quá nặng so với lợi ích; image đang chạy đã lệch comment (dlt 1.29.1 so với 1.25.0 ghi ở `Dockerfile.dataplatform:33-37`) nên việc ghim là cần dù có lưu image hay không | User đổi ý 15/10 ~17:15 (bản đầu đề xuất `docker save`) |

## 3. Kiến trúc

```text
 Máy khách (Linux + Docker)                                                      Ngoài máy
 ┌──────────────────────────────────────────────────────────────────────────┐
 │ Chụp nhất quán (nơi sở hữu dữ liệu)               app_data/backups/       │
 │  data_platform 01:04  backup.sh ── schedules.db, ingestion_health.db: SQLite backup API ─► <ts>/  (giữ 7, cục bộ)
 │                                 ── parity log: DuckDB COPY → parquet ─► <ts>/exports  + manifest.json
 │                                 ── Metabase JSON (API) ───────────────► <ts>/metabase_export
 │  host 00:30 hằng đêm metabase_cold_backup.sh ── H2 nguội + manifest ─► metabase/
 │  crm 02:00 (sau khi sửa timezone) backup_crm.py ── SQLite backup API + gate ─► vol crm_backups
 │                                                                          │
 │ host timer 03:30 ─► docker compose run --rm backup offsite               │
 │   (restic+rclone, không socket, mount :ro)                               │  mã hoá AES-256
 │   preflight tuổi + manifest ─► staging ─► restic backup ─► forget ─► check n/28 ─────► Drive (SA/Shared Drive
 │   (CN: prune sau backup)        │                                        │              hoặc OAuth drive.file)
 │                                 └─► app_data/backups/status/*.json       │              | S3 VN | NAS
 │ host timer CN 05:15 ─► restore_drill weekly (T2, đọc từ ngoài máy) ◄──────────────────────┘
 │ host timer CN đầu tháng 06:00 ─► restore_drill monthly (T3: dựng lại bằng dbt)
 │                                                                          │
 │ Dagster health_checks (2h) ── check backup_freshness đọc status/*.json ─► Lark
 └───────────┬──────────────────────────────────────────────────────────────┘
             └─ ping /start, /<exit> ─► healthchecks.io (tài khoản khách) ─► email/Lark của khách
 Khoá restic: key-host (máy, 0600, thu hồi được) · key-customer (bản in niêm phong) · key-customer-2 (người giữ thứ hai của khách)
```

### 3.1 Luồng dữ liệu

| Vào | Biến đổi | Ra |
|---|---|---|
| Raw parquet/Delta + trạng thái dlt (dlt dùng destination `filesystem`, `ingestion/src/utils/pipeline_runner.py:136`, nên state nằm cùng thư mục raw; 12 bảng là Delta, F-Q14) | Đọc thẳng `:ro`, restic chia chunk, mã hoá | Pack trong repo |
| `dagster_home` (named volume, `docker-compose.yml:48`, 11,6 GB trong đó `history/` 10,1 GB) | `backup.sh` trong `data_platform`: SQLite backup API **chỉ** cho `schedules/schedules.db` (trạng thái + cursor schedule/sensor, 321 MB). Bỏ `history/` (kể cả `runs/index.db`, event log) và `storage/` (output IO manager, compute log, tự sinh lại); `dagster.yaml` giống hệt bản trong git (F-Q16) | `app_data/backups/<ts>/app_data/dagster_home` + manifest |
| `monitoring_db` (named volume đè lên `data_lake/monitoring`, `docker-compose.yml:44,85`): `ingestion_health.db` là **SQLite WAL**, không phải DuckDB (F-Q5) | `backup.sh` gọi `sqlite_snapshot.py` (cùng helper với `dagster_home`): SQLite backup API, `PRAGMA integrity_check`, đếm dòng `ingestion_runs`. Bỏ `ingestion_health.duckdb` cũ (không còn writer từ 20/05) | `<ts>/app_data/monitoring/` + manifest |
| `main.monitor_taxonomy_parity_log` trong `sapo_warehouse.duckdb` (bảng duy nhất không dựng lại được, F-Q3) | `backup.sh` (đang trong op giữ `duckdb_lock`) gọi `duckdb_snapshot.py --tables main.monitor_taxonomy_parity_log`: mở `read_only`, trong một giao dịch đếm dòng rồi `COPY ... TO ... (FORMAT parquet)`; thử lại có giới hạn nếu một writer ngoài khoá đang giữ file | `<ts>/exports/warehouse/` + manifest |
| Metabase H2 | Chép nguội như hiện nay (`scripts/backup/metabase_cold_backup.sh:49-63`), thêm: sau khi healthy, xuất JSON + đếm số lượng vào thư mục cạnh bản chép | `metabase/metabase-<kind>-<ts>.mv.db` + `.manifest.json` |
| CRM (`crm.db`, `hug.db`, `cache.db`) | Giữ nguyên `backup_crm.py` (`crm/ops/backup_crm.py:38-39`) | `crm_backups/<ts>/` + manifest |
| Secret (gồm credentials tunnel ở `${FG_CLOUDFLARED_DIR}`), seed do job ghi, `app_data/analysis`, file cấu hình host | Wrapper trên host ghi `repo-state/` (HEAD sha, `git status --porcelain`, `git diff` của checkout) và `host-state/` (unit systemd user, linger, crontab, danh sách stack phụ thuộc như Caddy toàn cục `caddy-global/` trong repo và cloudflared ngoài repo, phiên bản Docker, Tailscale); sidecar đọc secret `:ro` | Chỉ trong repo restic |
| Tất cả bước trên | Sidecar ghi trạng thái từng bước | `app_data/backups/status/{local,metabase_cold,crm,offsite,check,drill_weekly,drill_monthly}.json` |

## 4. Phân loại dữ liệu (đã chốt ở phase 0)

Bằng chứng ai ghi, kích thước và lớp của từng thành phần: F-Q1, F-Q5, F-Q7, F-Q9, F-Q16, F-Q19. Bảng này là nguồn cho `scripts/backup/offsite-include.txt` (phase 2) và mục "Phạm vi dữ liệu" của `docs/operations/backup-and-recovery.md`.

| Thành phần | Kích thước (15/10) | Lớp | Lên off-site | Cách khôi phục |
|---|---|---|---|---|
| `data_lake/sapo_v2_raw` (11 bảng Delta + parquet batch + state dlt) | 542 MB | Nguồn sự thật; `history_log` không lấy lại được do Sapo cắt lịch sử | Có, hằng ngày | Giải nén, rồi để dlt lấy tiếp từ cursor trong snapshot (§8.3) |
| `data_lake/hug_raw` | 164 KB | Nguồn sự thật (sự kiện đã ack bị xoá khỏi Worker) | Có | Giải nén |
| `data_lake/sapo_v2_raw/product_daily_snapshot` (plan `261015-1730-price-inventory-history`, chụp toàn bộ sản phẩm mỗi đêm, append-only, giữ vĩnh viễn) | nhỏ, tăng theo ngày | **Không dựng lại được**: giá và trạng thái sản phẩm của các ngày đã qua không lấy lại được từ Sapo | Có (thêm 15/10/2026) | Giải nén; không chạy lại full refresh đè lên |
| `data_lake/gsheet_raw` | 232 KB | Ảnh chụp Google Sheet (giá trị cũ của Sheet không còn) | Có | Giải nén |
| `data_lake/misa_raw`, `data_lake/shopee_raw` | 3,4 MB, 632 KB | Phái sinh từ file nhập tay (`input_source`, `app_data/analysis`); giữ vì rẻ và khỏi nạp lại | Có | Giải nén |
| `data_lake/backup` (ảnh chụp tay Sapo 13/04 trước migration) | 21 MB | Lưu trữ thủ công, không có writer | Có (user chốt 15/10) | Giải nén |
| `app_data/input_source` | 50 MB | Nhập tay | Có | Giải nén |
| `app_data/analysis` (sổ chi tiết MISA xlsx dùng backfill) | 1,1 MB | Nhập tay, hiện ngoài mọi backup | Có (user chốt 15/10) | Giải nén |
| `main.monitor_taxonomy_parity_log` (trong `sapo_warehouse.duckdb`) | 82 dòng (15/10) | Phái sinh nhưng **không dựng lại được** (append-only, đếm đêm parity) | Có, parquet xuất ra (D2) | Nạp lại vào warehouse trước khi build (`full_refresh=false` nên build không xoá) |
| `monitoring_db`: `ingestion_health.db` (SQLite, bảng `ingestion_runs`, giữ 90 ngày) | 84 MB | Lịch sử vận hành không dựng lại được; freshness, row_trend, digest, recon, KPI đọc | Có (bản SQLite backup API) | Áp vào **named volume** `monitoring_db`, không phải `app_data/data_lake/monitoring` |
| `dagster_home/schedules/schedules.db` | 321 MB | Trạng thái điều phối (schedule/sensor bật tắt, cursor) | Có | Áp vào volume; kiểm instigator bằng `scripts/checks/instigator_state.py` |
| `dagster_home/history/` (gồm `runs/index.db` 5,1 GB), `dagster_home/storage/` | 10,1 GB, 498 MB | Lịch sử run, event log (materialization, asset check), output IO manager | **Không** (ngoài phạm vi; run bị purge sau 1 ngày) | Tự sinh lại; UI mất "last materialized" cho tới lần chạy kế |
| `sapo_warehouse.duckdb` (trừ bảng log ở trên), `serving/`, `export/` (gồm `rolling/`, chỉ giữ 3 lần build), `crm_export/` | 514 MB, 170 MB, 64 MB, 1,9 MB | Phái sinh | Không | `dbt build` + serving; `crm_export` từ `crm.db`; bản cục bộ hằng đêm dùng làm "máy tăng tốc" nếu mở được |
| 18 model incremental | — | 13 model staging dựng lại được từ raw; `int_customer_metrics`, `int_customer_discount_metrics`, `dim_customers_base`, `int_customer_entry_attributes` dựng lại ra giá trị theo ngày build (chấp nhận, không mất dữ liệu); `monitor_taxonomy_parity_log` như trên (F-Q3) | Không (trừ bảng log) | `dbt build` trên DB rỗng |
| `fact_variant_prices_snapshot`, `fact_inventory_snapshot` | 3 file mỗi bảng | Phái sinh; **không có lịch sử** dù comment model nói có (F-Q2) | Không trong plan này; plan riêng sửa model sẽ thêm | `dbt build` |
| `data_lake/sapo_raw_staging`, `data_lake/test_raw`, `monitoring/ingestion_health.duckdb`, lớp host `app_data/data_lake/monitoring` | < 15 MB | Mồ côi / cũ | Không | — |
| `transformation/seeds/` | — | Có trong git, nhưng budget sync 02:30 ghi đè 2 file của tenant giữa các lần commit (`ingestion/src/gsheet_budget_sync/merge.py:35-37`); `sync_seeds.py` chỉ chạy tay (F-Q8) | Có (cả cây, cộng `git diff`) | Giải nén đè lên checkout đúng sha |
| Metabase H2 + JSON | 85 MB (bản nguội ~48 MB) | Nguồn sự thật (nội dung BI) | Có | Áp H2 (giữ owner uid của container), kiểm số lượng với manifest |
| CRM `crm.db`, `hug.db`, `cache.db` (qua `crm_backups`) | 67 MB/bản | Nguồn sự thật (cache tái tạo được) | Có (bản mới nhất đã qua gate) | Theo runbook CRM, rồi refresh cache |
| Secret: `.env` (8 biến), `.env.docker` (37 biến), `app_data/secrets/gsheets-service-account.json`, credentials tunnel (`<tunnel-id>.json`, `cert.pem`, `config.yml`) | < 20 KB | Bí mật | Có, chỉ trong repo mã hoá (D6) | Đặt lại quyền 0600 |
| `.env.local` | 3,5 KB | File dev cũ, prod không dùng | **Không** (user chốt 15/10) | — |
| `docker-compose.yml`, `caddy-global/`, Dockerfile | — | Có trong git | Theo sha (kèm bản trong staging để so) | Theo sha |
| `transformation/profiles.yml` | — | Có trong git | Không cần riêng | Theo sha |
| `ingestion/.dlt/secrets.toml` | — | Không tồn tại trên prod (chỉ có `.sample`) | Không | — |
| Caddy cert (`caddy_data`), Rill state, bản build Evidence, `agent_codex_config` (168 MB), `crm_verify_data`, `metabase.db.trace.db*`, `rill/tmp`, image Docker (D12) | — | Tái tạo được | Không | Tự sinh lại; `codex login` lại; build lại image từ git |
| `rclone.conf`, mật khẩu restic | — | Chìa khoá mở repo | **Không** (gà và trứng) | Từ Recovery Sheet của khách |

## 5. Chụp nhất quán theo thành phần

| Store | Kỹ thuật | Ai chạy, khi nào | Bằng chứng nhất quán |
|---|---|---|---|
| Raw parquet/Delta | Đọc thẳng `:ro`. Không có `--exclude-file` cho file tạm: dlt 1.29.1 ghi parquet thường bằng `shutil.copyfile` thẳng vào tên cuối, không có tên tạm (F-Q14); bảng Delta ghi qua deltalake (file dữ liệu trước, commit `_delta_log` sau; log cũ bị dọn sau checkpoint). `duckdb_lock` không che raw (F-Q4) | Sidecar 03:30: trong giờ 3 job incremental và hourly Sapo không chạy (`orchestration/connectors/sapo_v2/jobs.py:82,102`), chỉ còn realtime ghi Delta và sensor file-drop/Sheets khi có file mới | T2 đọc mọi file parquet và mở mọi bảng Delta (mọi file log tham chiếu có trong snapshot); state dlt ghi **sau** dữ liệu nên snapshot không có state mới hơn dữ liệu, chỉ có thể có dữ liệu thừa (ghi trùng khi chạy lại, staging khử trùng) |
| DuckDB: `main.monitor_taxonomy_parity_log` | `read_only` + `COPY ... TO ... (FORMAT parquet)`; số dòng đọc trong **cùng giao dịch** ghi vào manifest | `backup.sh` trong op đang giữ `duckdb_lock` (`orchestration/ops/system_backup.py:79-82`), nên không trùng dbt/serving; writer ngoài khoá (`sync_seeds.py`, `bootstrap_serving_views.py`, đều chạy tay) thì thử lại có giới hạn | Manifest = số dòng nguồn trong snapshot giao dịch; T2 đếm lại trên parquet |
| `sapo_warehouse.duckdb` | Giữ chép nóng hiện có trong bản cục bộ, gọi là "máy tăng tốc", **không** là nguồn khôi phục bắt buộc | Như hiện nay | Khôi phục chỉ dùng nếu mở `read_only` được; không thì `dbt build` |
| SQLite Dagster (`schedules.db`) và monitoring (`ingestion_health.db`, WAL) | `sqlite3` backup API (Python `Connection.backup`). Hôm nay cả hai bị chép bằng `cp -a` (`scripts/backup/backup.sh:158-166`), không an toàn khi đang ghi | `backup.sh` | `PRAGMA integrity_check` trên bản chụp; số dòng bảng chính; manifest sha256 |
| SQLite CRM | Giữ nguyên `backup_crm.py` (gate nguồn == bản chụp) | Dagster 02:00 giờ VN **sau khi** phase 1 thêm `execution_timezone="Asia/Ho_Chi_Minh"` vào `crm_backup_schedule` (`orchestration/packs/crm/jobs.py:15-20`); hiện lịch tính theo UTC nên chạy 09:00 giờ VN (F-Q11) | Đã có; lần diễn tập 15/10 PASS |
| Metabase H2 | Chép nguội (dừng ~18 giây) | Host **hằng đêm 00:30** (user chốt 15/10) + trước deploy | Thêm manifest số card/dashboard/collection lấy qua API **ngay sau** khi healthy |
| Secret, seed, cấu hình | Đọc file; secret chỉ vào repo mã hoá | Sidecar + wrapper host | Manifest sha256 trong staging (không ghi nội dung) |

## 6. Sidecar `backup`

- **Image** `Dockerfile.backup`: `python:3.12-slim` ghim digest, restic 0.19.x và rclone (bản ghim, kiểm sha256 khi tải), `sqlite3`. Không cài Docker CLI.
- **Service** trong `docker-compose.yml` với `profiles: [ops]`, nên `docker compose up -d` không khởi động nó; chỉ chạy qua `run --rm`. Khai báo mount ở compose để tên named volume tự phân giải theo project (không phải đoán prefix như runbook CRM, `crm/docs/backup-restore-runbook.md:68`).
- **Mount:** `./app_data/data_lake:/src/lake:ro`, `./app_data/input_source:/src/input:ro`, `./app_data/secrets:/src/secrets:ro`, `./app_data/analysis:/src/analysis:ro`, `${FG_CLOUDFLARED_DIR}:/src/cloudflared:ro` (credentials tunnel, ngoài repo; bỏ trống thì bỏ qua và ghi vào trạng thái), `./app_data/backups:/src/backups:ro`, `crm_backups:/src/crm_backups:ro`, project root `:ro` tại `/src/project` (lấy seed, `.env`, `.env.docker`, compose, và `orchestration/notifications/lark_client.py` để gửi Lark mà không viết client thứ hai), `./app_data/backups/status:/status` (rw, chỉ file trạng thái), `backup_staging:/staging`, `restic_cache:/cache`, thư mục cấu hình backup của host (`${FG_BACKUP_CONFIG_DIR}`) tại `/config` (rw vì rclone ghi lại token OAuth đã làm mới).
- **Mạng:** mạng riêng chỉ đi ra ngoài; không vào `caddy_net`, không publish cổng.
- **Hostname cố định:** `restic backup --host <tenant_id>` để restic tìm đúng snapshot cha (hostname container đổi mỗi lần chạy sẽ làm restic quét lại toàn bộ).
- **Tag:** `tenant=<id>`, `git=<sha>`, `kind=daily|images`, `compose=<sha256 của docker-compose.yml>`.
- **Quyền file:** sidecar chạy root để đọc dữ liệu do container root ghi (`app_data/backups` hiện thuộc root). Lệnh khôi phục nhận `--owner $(id -u):$(id -g)` và `chown` thư mục scratch khi xong, nên người vận hành không cần `sudo` để đọc hay xoá.
- **Đường dẫn tham số hoá:** mọi script nhận `FG_PROJECT_ROOT` (mặc định: suy ra từ vị trí script, như `metabase_cold_backup.sh:22`); unit systemd được **sinh** từ template bởi `scripts/backup/install-units.sh`, không còn đường dẫn `/home/vantt` cứng như `scripts/backup/systemd/metabase-cold-backup.service:8`. Unit chạy ở mức user (cùng mô hình với timer Metabase đang dùng, linger đã bật cho `vantt`).

### 6.1 Một lần chạy off-site

1. Wrapper host (`scripts/backup/offsite.sh`): ping healthchecks `/start`; ghi `repo-state/` và `host-state/` vào staging; gọi sidecar.
2. Preflight trong sidecar: bản backup cục bộ mới nhất < 26 giờ và có manifest; bản CRM mới nhất < 26 giờ; bản H2 nguội < 8 ngày; mọi đường dẫn trong danh sách include tồn tại và không rỗng (bắt trường hợp Đợt 2 đổi volume mà quên sửa mount). Thành phần nào quá hạn thì ghi vào trạng thái, **vẫn backup phần còn lại**, cuối cùng thoát khác 0.
3. Chép các bản đã chụp vào `/staging` theo đường dẫn ổn định (`/staging/dagster_home`, `/staging/crm`, `/staging/metabase`, …).
4. `restic backup` các đường dẫn ổn định + raw lake + input + seed + secret, `--pack-size 64`, `--compression auto`, `--exclude-file` theo `offsite-include.txt` (phái sinh, mồ côi, `.env.local`, `desktop.ini`). Không có mẫu file tạm của dlt để loại (F-Q14).
5. `restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 12` (thêm `--keep-yearly 3` nếu user chọn, câu hỏi mở 9). Chủ nhật: `prune --max-unused 10%` ngay sau đó, trong cùng lần chạy (không có hai tiến trình tranh khoá repo).
6. `restic check --read-data-subset=<n>/28` với `n = (ngày trong năm mod 28) + 1`.
7. Ghi `status/offsite.json` (snapshot id, kích thước thêm, thời lượng, thành phần quá hạn); ping healthchecks `/<exit code>`; lỗi thì gửi Lark.

## 7. Lịch

Đã đối chiếu với các schedule đang có: purge 01:00 (`orchestration/definitions.py:353-357`) kích backup cục bộ ~01:04 (`orchestration/definitions.py:193-208`, dự phòng 06:05 ở `:216-218`); CRM `0 2 * * *` (`orchestration/packs/crm/jobs.py:18`) nhưng **thiếu `execution_timezone`** nên thực chạy 09:00 giờ VN (run 14/10 và 15/10 lúc 09:00, F-Q11), phase 1 sửa về 02:00; Sheets 02:30 (budget sync, có ghi Google Sheet) (`orchestration/connectors/sheets/jobs.py:70`); nightly 03:00 (`orchestration/definitions.py:168-171`, ~5 phút); recon 04:30 và KPI 04:45 (`orchestration/definitions.py:256-273`); realtime Sapo mỗi 3 phút cả ngày (`orchestration/connectors/sapo_v2/jobs.py:52`), incremental và hourly bỏ giờ 3 (`:82`, `:102`); realtime HUG mỗi 3 phút (`orchestration/connectors/hug/jobs.py:17`).

Số đo (F-Q12, F-Q13): lịch sử run Dagster chỉ còn ~1,4 ngày (`PURGE_KEEP_DAYS` mặc định 1), nên p95 tính từ bảng `ingestion_runs` (77 đêm): giai đoạn ingestion của nightly kết thúc p50 03:01:51, p95 03:10:01, max 03:12:18; phần dbt + serving sau đó ~4,3 phút (mẫu Dagster 15/10: 03:00:55 → 03:06:08). Ước nightly kết thúc p95 ~03:14, max ~03:17, trước 03:20, nên **giữ 03:30**. Backup cục bộ 7 đêm gần nhất: 17–24 giây, bắt đầu 01:03–01:07 (12/10 chạy bằng lịch dự phòng 06:05).

| Việc | Giờ (Asia/Ho_Chi_Minh) | Persistent | Ghi chú |
|---|---|---|---|
| Chép nguội Metabase | **Hằng đêm 00:30** (user chốt 15/10; hiện là CN 00:30) | Không | Dừng Metabase ~18 giây; RPO 24 giờ |
| Backup cục bộ (`backup.sh`) | ~01:04 (giữ nguyên) | — | Thêm chụp nhất quán `schedules.db`, `ingestion_health.db` (SQLite API), bảng parity log (DuckDB COPY) |
| CRM backup + diễn tập CRM | 02:00 (sửa từ 09:00 thực tế, phase 1) | — | Thêm `execution_timezone`, deploy D1 |
| **Off-site + forget + check n/28** | **Hằng ngày 03:30** | Có (chỉ đọc, không gây gián đoạn nên chạy bù khi máy bật lại là an toàn) | Có bản CRM trong ngày (sau khi sửa timezone; trước đó bản CRM cũ ~18,5 giờ, vẫn dưới ngưỡng 26 giờ); nightly kết thúc p95 ~03:14 (đo ở trên). User cho phép riêng backup trong khung 02:30–04:00. Off-site không giữ `duckdb_lock` và không đọc gì nightly ghi ngoài raw; trong giờ 3 chỉ có writer Delta (realtime) |
| Prune | CN, ngay sau off-site trong cùng lần chạy | — | Không có timer riêng |
| **Diễn tập khôi phục T2** | **CN 05:15** | Không | Sau recon/KPI, trước digest 06:00; chạy sau bản H2 nguội 00:30 cùng ngày nên kiểm luôn bản H2 mới |
| **Diễn tập dựng lại T3** | **CN đầu tháng 06:00** (`Sun *-*-01..07 06:00`) | Không | Sau T2; giới hạn CPU/RAM; preflight RAM trống |
| Kiểm tuổi backup | Theo `health_checks_asset_schedule` (mỗi 2 giờ, phút 05) | — | Check mới đọc `status/*.json` |
| Dead-man | Liên tục, grace 6 giờ | — | healthchecks.io |

## 8. Khôi phục

### 8.1 `restore.sh` (Linux, thay cho `restore.ps1`)

```text
scripts/backup/restore.sh snapshots                               # liệt kê, lọc theo tenant
scripts/backup/restore.sh extract [--snapshot <id>|latest] [--component <c>...] --into <dir>
scripts/backup/restore.sh verify  --from <dir>                    # gate A: so manifest
scripts/backup/restore.sh apply   --from <dir> --component <c> --confirm   # ghi vào prod
scripts/backup/restore.sh full    --from <dir> --confirm [--mode drill|real]
```

Thành phần: `raw-lake` (gồm `data_lake/backup`), `exports` (bảng parity log; về sau dữ liệu tích luỹ của plan giá/tồn), `monitoring` (vào named volume `monitoring_db`), `input`, `analysis`, `seeds`, `secrets`, `cloudflared` (chỉ ở `--mode real`), `dagster-home` (`schedules.db`), `metabase-h2`, `metabase-export`, `crm`, `config`. `apply` dừng đúng service liên quan, tạo bản an toàn (`.before-restore`), ghi, khởi động lại, kiểm health; với `crm` gọi lại đúng các bước của runbook CRM; với `metabase-h2` theo `docs/operations/deployment.md` mục "Restore the H2 file". Lệnh `apply` và `full` từ chối chạy khi thiếu `--confirm` hoặc khi `verify` chưa PASS trên thư mục đó.

### 8.2 Cô lập khi diễn tập (`--mode drill`)

Một bản dựng lại mà chạy lịch như prod sẽ gây tác dụng ra ngoài. Danh sách đã kiểm ở phase 0 (F-Q17):

| Tác dụng ra ngoài | Nguồn | Cách chặn ở `--mode drill` |
|---|---|---|
| Cloudflare Tunnel: cùng credentials sẽ gắn thêm connector vào tunnel prod và **chia traffic thật** (tunnel còn phục vụ `vnflow`, `hermes`, `fgos` ngoài dự án) | `${FG_CLOUDFLARED_DIR}` (`<tunnel-id>.json`, `cert.pem`, `config.yml`) | Không khởi động `cloudflared`; không giải nén thành phần `cloudflared` vào máy diễn tập |
| **Ack webhook Sapo** xoá hàng đợi trên Worker (mất sự kiện của prod) | `ingestion/src/sapo/webhook_consumer.py:50-58,348`; `WORKER_URL`, `WORKER_POLL_TOKEN` | Rỗng hai biến; tắt schedule/sensor consumer trước khi bật bất cứ thứ gì |
| **Ack webhook HUG** | `ingestion/src/hug/hug_webhook_consumer.py:315`; `WORKER_URL` | Như trên |
| Đẩy HUG D1 (POST có ký) | `crm/src/hug/d1_push.py:66-78`; `HUG_WORKER_URL` (`docker-compose.yml:228`) | Rỗng biến (`push_enabled()` thành false) |
| **Ghi Google Sheet**: budget sync 02:30 ghi tab `__REF` dù docstring nói chỉ đọc; `budget_suggestion_writeback_asset` ngày 1 hằng tháng 08:00 | `orchestration/connectors/sheets/assets.py:294,360` → `ingestion/src/gsheet_budget_sync/sheet_writeback.py:61-81` | Không mount `app_data/secrets` (key service account); rỗng `GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH` |
| ACME DNS-01 qua Cloudflare API (ghi bản ghi TXT lên DNS thật) | `caddy-global`, `CLOUDFLARE_API_TOKEN` | Không chạy `caddy-global` với token thật; rỗng biến |
| Cảnh báo Lark | `orchestration/notifications/lark_client.py:62-63,103` | Rỗng `LARK_ALERT_WEBHOOK`, `LARK_ALERT_SECRET` |
| Email Metabase (subscription; hôm nay 0 subscription theo `metabase_export/manifest.json`) | Cấu hình SMTP trong H2 | Chạy Metabase với SMTP tắt |
| Gọi API Sapo bằng tài khoản thật (chỉ đọc, tốn quota) | `SOURCES__SAPO__*` | Rỗng biến khi không cần kéo dữ liệu |

`--mode drill` sinh file env riêng với các biến trên rỗng, dừng mọi schedule/sensor Dagster ngay sau khi khởi động (dùng `instigator_state.py` để so với trạng thái trong snapshot rồi tắt) và không khởi động `cloudflared` lẫn `caddy-global`. Diễn tập T2/T3 chạy container với `--network none`, nên chặn được mọi dòng trên.

### 8.3 Kéo bù sau khôi phục

Raw trong snapshot là đến 03:30 ngày trước sự cố. Phase 0 xác nhận (F-Q14, F-Q15):

- dlt ghi state **sau** dữ liệu (`complete_load`, `dlt/destinations/impl/filesystem/filesystem.py:1138-1140`), nên snapshot không bao giờ có state mới hơn dữ liệu; trường hợp xấu nhất là dữ liệu của một lần load chưa kịp có state, và lần chạy sau lấy lại khoảng đó (ghi trùng, staging `delete+insert` theo khoá khử trùng).
- Không có cơ chế lùi cursor theo khoảng thời gian: chỉ có `--reset-cursor` (xoá state, tải lại toàn bộ, `ingestion/src/utils/pipeline_runner.py:70-111`); cursor Sapo là `dlt.sources.incremental("sync_metadata.event_timestamp")` không nhận tham số ngày.

**Quyết định:** sau khôi phục, để mỗi pipeline chạy tiếp từ cursor trong snapshot; API Sapo trả lại mọi thay đổi từ cursor nên không có khoảng hở cho nguồn còn giữ lịch sử. Không làm "lùi 48 giờ" trong plan này; nếu diễn tập T3 hay phase 6 thấy thiếu dữ liệu thì phase 3 thêm cờ `--rewind-hours N` (sửa `last_value` trong state mới nhất). Ngoại lệ đã biết:

- Sự kiện webhook (Sapo, HUG) đã ack sau thời điểm snapshot thì mất khỏi Worker. Với Sapo, batch incremental lấy lại cùng thực thể từ API; với HUG (chỉ có webhook), mất tối đa khoảng RPO 24 giờ sự kiện scan/opt-in. Ghi vào runbook.
- Kho Sapo có `--window custom --start/--end` (`ingestion/run_sapo_v2_inventory_transactions_batch.py`), chạy lại thì ghi trùng; MISA có script backfill tay theo tháng; Shopee là file drop (nạp lại từ `input_source`).

## 9. Xác minh

| Tầng | Tần suất | Nội dung | FAIL thì |
|---|---|---|---|
| T0 Capture gate | Mỗi lần chụp | Manifest nguồn == bản chụp (CRM đã có; `schedules.db`, `ingestion_health.db`, bảng parity log thêm mới) | Lark + trạng thái đỏ |
| T1 Toàn vẹn repo | Hằng ngày | `restic check --read-data-subset=n/28` | Lark; `restic repair` theo docs |
| T2 Khôi phục | CN 05:15 | Giải nén `latest` **từ ngoài máy** vào scratch rồi: (a) sha256 + số dòng so manifest; (b) `PRAGMA integrity_check` CRM, Dagster; (c) đếm dòng mọi file parquet raw và export, so manifest; mở mọi bảng Delta bằng deltalake và kiểm mọi file log tham chiếu có trong snapshot (bắt file parquet bị chụp dở, vì dlt không ghi qua file tạm); (d) boot Metabase tạm cùng image, `--network none`, giới hạn RAM, chờ `/api/health`, đếm card/dashboard/collection qua API từ bên trong container, so manifest bản H2; (e) diễn tập CRM bằng `restore_verify_crm.py` trỏ vào bản đã giải nén; (f) prod không đổi (dấu vân tay kích thước + mtime trước/sau); (g) mỗi quý mở repo bằng **khoá của khách** (khách nhập tại chỗ, theo biên bản) | Lark, giữ scratch để điều tra |
| T3 Dựng lại | CN đầu tháng | Lake rỗng + raw/seed/export đã giải nén → `build-lake.sh` (tái dùng `scripts/shadow/`) → so bất biến: số dòng các bảng public (`scripts/checks/public_models.yaml`) với prod trong ngưỡng `row_trend_checks` cho dữ liệu đến ngày snapshot, recon pass | Lark |
| Tamper | Khi nghiệm thu và mỗi khi đổi script verify | Xoá một partition parquet, sửa một ô CRM, cắt cụt H2, đổi một dòng manifest: T2/T3 phải FAIL | Không nghiệm thu |

Mức T2 dùng tài nguyên: Metabase tạm 1,5 GiB; preflight đòi `MemAvailable` ≥ 3 GiB, không đủ thì **bỏ qua có cảnh báo** (không im lặng). Lý do: swap host gần đầy (đã ghi ở roadmap; `free` ngày 15/10 cho swap 7/7 GiB dùng hết, RAM còn 16 GiB khả dụng).

## 10. Khoá, bàn giao và chi phí

| Khoá | Ai giữ | Ở đâu |
|---|---|---|
| `key-host` | Máy chủ | `${FG_BACKUP_CONFIG_DIR}/restic.pass` (0600). Mất máy thì `restic key remove` |
| `key-customer` | Chủ doanh nghiệp | Recovery Sheet in ra, niêm phong, cất két |
| `key-customer-2` | Người thứ hai do khách chỉ định | Password manager của khách hoặc bản in thứ hai ở nơi khác |

Recovery Sheet gồm tenant id, `RESTIC_REPOSITORY`, tài khoản Google/S3 chứa repo và cách cấp lại quyền, khoá, phiên bản (git tag) công cụ khôi phục, số hỗ trợ của FG. FG không lưu bản nào. Biên bản bàn giao gồm: snapshot id đầu tiên, kết quả T2 chạy bằng `key-customer` trước mặt khách, chữ ký khách nhận trách nhiệm giữ khoá ("mất cả hai khoá của khách và máy thì không khôi phục được").

**RPO/RTO đề xuất cho SME:**

| Dữ liệu | RPO | RTO |
|---|---|---|
| CRM | 24 giờ | 2 giờ (khôi phục riêng CRM) |
| Raw lake | 24 giờ trên off-site; gần 0 với nguồn còn giữ lịch sử, nhờ kéo bù | Nằm trong RTO toàn hệ thống |
| Metabase | 24 giờ (JSON, dựng lại tay) / 7 ngày (H2 đầy đủ) | 1 giờ sau khi stack chạy |
| Secret, cấu hình, seed | 24 giờ | — |
| **Toàn hệ thống khi mất máy** | **24 giờ** | **8 giờ làm việc** kể từ khi có máy Linux mới có mạng; mục tiêu đo được ở diễn tập ≤ 4 giờ |

**Chi phí mỗi khách** (số đo 15/10, F-Q7): snapshot đầu ~1,2 GB trước nén (raw ~570 MB, `schedules.db` 321 MB, `ingestion_health.db` 84 MB, H2 ~50–85 MB, CRM ~67 MB, input + analysis + `data_lake/backup` ~72 MB); mỗi ngày thêm chủ yếu phần đổi của `schedules.db`, H2, CRM và raw mới. Repo ước 2–6 GB sau dedup với `--keep-daily 7 --keep-weekly 4 --keep-monthly 12`. Không lưu image (D12). Google Drive: nằm trong 15 GB miễn phí hoặc gói Workspace. healthchecks.io: gói miễn phí, 5 check (backup đêm, off-site, chép nguội Metabase, CRM, diễn tập tuần; plan.md mục "Đã chốt"). Chi phí chính là công: ~9 ngày phát triển một lần (plan.md) cộng ~1 giờ cài và ~1 giờ diễn tập chứng kiến cho mỗi khách.

## 11. Chế độ hỏng và giảm thiểu

| Chế độ hỏng | Phát hiện | Giảm thiểu |
|---|---|---|
| Máy chết hoặc timer không chạy | Dead-man (grace 6 giờ) | Tài khoản healthchecks của khách, cảnh báo ngoài máy |
| Token OAuth bị thu hồi (khách đổi mật khẩu, gỡ quyền app) | Off-site lỗi → Lark + dead-man | Runbook cấp lại token; FJ dùng SA nên không bị |
| Một thành phần chụp cục bộ ngừng (vd. `data_platform` hỏng) | Preflight tuổi + check `backup_freshness` | Off-site vẫn đẩy phần còn lại, báo thành phần quá hạn |
| Đợt 2 đổi bind mount thành named volume, mount sidecar trỏ thư mục rỗng | Preflight "đường dẫn tồn tại và không rỗng" | Cùng commit Đợt 2 phải sửa service `backup`; ghi trong phase 6 của plan 260705 (coordinator báo) |
| Parquet bị chụp dở (dlt ghi thẳng tên cuối, F-Q14) | T2 đọc mọi file parquet, mở mọi bảng Delta | Off-site chạy 03:30 khi không có writer parquet thường; bản hôm sau chụp lại file đầy đủ; khi khôi phục bản lỗi thì xoá file dở và để dlt lấy lại (state ghi sau dữ liệu) |
| Bản DuckDB export không nhất quán | Manifest số dòng trong cùng giao dịch; T2 đếm lại | `read_only` + `COPY` trong op giữ `duckdb_lock`, không chép file thô |
| SQLite (`schedules.db`, `ingestion_health.db`) chụp dở | `PRAGMA integrity_check` trên bản chụp | SQLite backup API thay cho `cp -a` |
| Thêm file nguồn sự thật mới mà không ai đưa vào danh sách (bài học `hug.db`) | Check "file bị gitignore mới" so với allowlist; preflight include | Allowlist `scripts/backup/offsite-include.txt`, check fail khi có file mới chưa phân loại |
| Diễn tập gây tác dụng ra ngoài (tunnel, HUG, Lark, email) | Kiểm env drill trước khi start | `--mode drill`, `--network none` cho T2/T3 |
| T2 làm cạn RAM host | Preflight `MemAvailable` | Giới hạn RAM container, bỏ qua có cảnh báo |
| Mất khoá | Không phát hiện được cho tới khi cần | 3 khoá, 2 người; T2 hằng quý mở bằng khoá khách |
| restic/rclone đổi hành vi | Diễn tập | Ghim phiên bản + sha256 trong `Dockerfile.backup` |
| Ransomware xoá repo qua quyền của host | Dead-man + `check` | Ngoài phạm vi; ghi lựa chọn đích phụ Object Lock |

## 12. Ma trận kiểm thử

| Mức | Nội dung | Ở đâu |
|---|---|---|
| Unit (pytest) | `duckdb_snapshot.py` (`COPY` một bảng, số dòng, thử lại khi bị khoá); `sqlite_snapshot.py` (DB WAL đang mở ghi); trình đọc manifest; preflight tuổi; sinh unit từ template (không còn `/home/vantt`); `backup_freshness` check (ngưỡng, thiếu file → đỏ); allowlist file gitignore | `scripts/tests/`, `orchestration/**/__tests__/` |
| Tích hợp | Chu trình init → backup → forget → check → extract → verify với ba backend: thư mục local, MinIO (S3), SFTP (container `atmoz/sftp` hoặc tương đương); khôi phục bằng `key-customer` | Worktree, dữ liệu shadow (không đụng prod) |
| Tamper | 4 kiểu phá dữ liệu ở §9 phải làm T2/T3 FAIL | Worktree |
| E2E Drive | SA + Shared Drive (FJ); OAuth `drive.file` với tài khoản Gmail thử của FG, gồm khôi phục từ máy khác với cùng OAuth client | Phase 5, phase 7 |
| E2E dựng lại | Máy khác, từ Recovery Sheet tới dashboard mở được, nightly drill mode xanh, trong RTO | Phase 6 |

## 13. Quan hệ với các plan khác

- **Thay thế** `plans/260624-2010-warehouse-pipeline-dr-verified-restore/` (stub ba phase chưa có nội dung): phase 1 "Parquet+State Backup" → phase 1–2 ở đây; phase 2 "Rebuild-Restore Verify" → phase 4 (T3); phase 3 "DR Runbook" → phase 6. Session thực thi/coordinator sửa `plan.md` của stub thành `status: cancelled` kèm dòng "superseded by 261015-1140-backup-restore-dr"; planner không sửa.
- **Đợt 2 (260705):** phase 00 (đổi bind mount thành named volume) phải sửa service `backup` trong cùng commit; ghim dependency Python (dlt đang không ghim, `ingestion/requirements.txt:1`) là phần còn lại của rủi ro build lại mà D12 không còn che.
- **Plan riêng lịch sử giá/tồn kho** (user chốt 15/10): sửa `fact_variant_prices_snapshot`/`fact_inventory_snapshot` để tích luỹ thật; khi xong, thêm dữ liệu tích luỹ của chúng vào danh sách xuất của `duckdb_snapshot.py`/`offsite-include.txt`.
- **Đợt 5:** CLI `init` gọi `restore.sh full` với snapshot rỗng; `tenant.yaml` thêm khối `backup:` (backend, repo, healthchecks).
- **Đợt 8:** `status/*.json` là đầu vào cho heartbeat (chỉ trạng thái, không dữ liệu kinh doanh).
- Roadmap mục "Việc vận hành độc lập": hai dòng "`.env.docker` không nằm trong backup nào" và "Backup ra ngoài máy" đóng khi plan này nghiệm thu.
