# Backup và khôi phục

Tài liệu sống về backup, khôi phục và dựng lại hệ thống. Quyết định và lý do: [ADR-019](../decisions/019-offsite-backup-and-recovery.md).

> **Trạng thái (15/10/2026):** đang xây dựng. Hôm nay chỉ có các backup **cục bộ**, nằm cùng ổ với dữ liệu: bản đêm `backup.sh`, bản chép nguội Metabase H2 và bản CRM. Chưa có bản ngoài máy. Các mục dưới đây được điền dần, mỗi mục cùng commit với phần code của nó. Mục "Phạm vi dữ liệu" đã chốt.
>
> Hướng dẫn đang dùng cho backup cục bộ: [`scripts/backup/README.md`](../../scripts/backup/README.md), [`deployment.md` mục "Metabase: backup and restore"](./deployment.md#metabase-backup-and-restore), [`crm/docs/backup-restore-runbook.md`](../../crm/docs/backup-restore-runbook.md).

## Mục lục

1. [Phạm vi dữ liệu](#phạm-vi-dữ-liệu)
2. [Lịch](#lịch)
3. [Chụp nhất quán](#chụp-nhất-quán)
4. [Off-site](#off-site)
5. [Khôi phục](#khôi-phục)
6. [Diễn tập](#diễn-tập)
7. [Cảnh báo](#cảnh-báo)
8. [Dựng lại từ con số 0](#dựng-lại-từ-con-số-0)
9. [Khoá và bàn giao](#khoá-và-bàn-giao)

## Phạm vi dữ liệu

Phân loại mọi thành phần có trạng thái. Kích thước đo ngày 15/10/2026 trên máy chủ Fine Japan.

- **Nguồn sự thật:** mất là mất hẳn.
- **Không dựng lại được:** dữ liệu phái sinh nhưng có lịch sử mà nguồn không còn.
- **Phái sinh:** dựng lại bằng `dbt build` và serving.
- **Tái tạo được:** tự sinh lại hoặc build lại.

### Đưa lên off-site

| Thành phần | Vị trí | Cỡ | Lớp | Bản cục bộ hiện nay | Ghi chú |
|---|---|---|---|---|---|
| Raw Sapo (`sapo_v2_raw`) | `app_data/data_lake/sapo_v2_raw` | 542 MB | Nguồn sự thật | Có (`cp -a`) | 11 bảng Delta + parquet batch + state dlt. `history_log` không lấy lại được vì Sapo cắt lịch sử |
| Raw HUG | `app_data/data_lake/hug_raw` | 164 KB | Nguồn sự thật | Có | Sự kiện đã ack bị xoá khỏi Worker |
| Raw Google Sheets | `app_data/data_lake/gsheet_raw` | 232 KB | Nguồn sự thật | Có | Ảnh chụp; giá trị cũ của Sheet không còn |
| Raw MISA, Shopee | `app_data/data_lake/{misa_raw,shopee_raw}` | 4 MB | Phái sinh từ file nhập tay | Có | Giữ vì rẻ, khỏi nạp lại |
| Ảnh chụp tay Sapo 13/04 | `app_data/data_lake/backup` | 21 MB | Lưu trữ | Có | Không có writer |
| File nhập tay | `app_data/input_source` | 50 MB | Nguồn sự thật | Có | |
| Sổ MISA xlsx dùng backfill | `app_data/analysis` | 1,1 MB | Nguồn sự thật | **Không** | Chỉ trên host, không mount vào container |
| Bảng `main.monitor_taxonomy_parity_log` | trong `app_data/data_lake/sapo_warehouse.duckdb` | 82 dòng | Không dựng lại được | Chép nóng cả file DuckDB | Append-only (`full_refresh=false`), đếm số đêm parity của bộ máy phân loại. Off-site xuất ra parquet |
| Lịch sử vận hành `ingestion_health.db` | named volume `monitoring_db` (`/app/var/data_lake/monitoring`) | 84 MB | Không dựng lại được | Có (`cp -a` nóng một file SQLite WAL) | Bảng `ingestion_runs`, giữ 90 ngày; check freshness, row_trend, recon, KPI và digest đọc bảng này |
| Trạng thái schedule/sensor Dagster | named volume `dagster_home`, `schedules/schedules.db` | 321 MB | Trạng thái điều phối | Có (`cp -a` nóng) | Bật/tắt và cursor của schedule/sensor |
| Metabase H2 | `app_data/metabase_data/metabase.db.mv.db` | 85 MB | Nguồn sự thật | Chép nguội + JSON qua API | Dashboard, card, collection, user, quyền |
| CRM `crm.db`, `hug.db`, `cache.db` | named volume `crm_data` → `crm_backups` | 67 MB/bản | Nguồn sự thật | Có (SQLite API + gate, 7 bản) | `cache.db` tái tạo được |
| Seed dbt | `transformation/seeds/` | — | Trong git, nhưng budget sync 02:30 ghi đè 2 file của tenant | Không | Lên off-site cả cây, kèm `git diff` |
| Secret | `.env`, `.env.docker`, `app_data/secrets/` | < 20 KB | Bí mật | Không | Chỉ trong repo mã hoá |
| Credentials Cloudflare tunnel | ngoài repo (trên prod: `/home/vantt/cloudflared-tunnel/config`) | < 1 KB | Bí mật | Không | Tunnel còn phục vụ host ngoài dự án. Chỉ khôi phục ở chế độ thật, không bao giờ khi diễn tập |

### Không đưa lên off-site

| Thành phần | Vị trí | Cỡ | Lý do |
|---|---|---|---|
| Warehouse (trừ bảng log ở trên) | `app_data/data_lake/sapo_warehouse.duckdb` | 514 MB | Phái sinh: `dbt build` |
| Serving, export, standalone | `app_data/data_lake/{serving,export}` | 234 MB | Phái sinh. Thư mục `export/marts/rolling` chỉ giữ 3 lần build gần nhất, không có lịch sử |
| `crm_export` | `app_data/data_lake/crm_export` | 1,9 MB | Phái sinh từ `crm.db` |
| Lịch sử run và event log Dagster | `dagster_home/history/` | 10,1 GB | Lịch sử run bị purge sau 1 ngày. Sau khôi phục, UI mất "last materialized" cho tới lần chạy kế |
| Output IO manager, compute log | `dagster_home/storage/` | 498 MB | Tự sinh lại |
| Thư mục mồ côi, file cũ | `sapo_raw_staging`, `test_raw`, `monitoring/ingestion_health.duckdb`, lớp host `app_data/data_lake/monitoring` | < 15 MB | Không còn writer |
| `.env.local` | gốc repo | 3,5 KB | File dev cũ, prod không dùng |
| Cert Caddy, cấu hình Codex, scratch diễn tập CRM | `caddy_data`, `agent_codex_config`, `crm_verify_data` | 168 MB | Tái tạo được |
| Image Docker | — | ~13,5 GB | Build lại từ git ở đúng sha (ADR-019 D12) |
| `rclone.conf`, mật khẩu restic | — | — | Chìa khoá mở repo, lấy từ Recovery Sheet của khách |

**Thêm file nguồn sự thật mới** (DB mới, file cấu hình bị gitignore, thư mục nhập tay) thì phải phân loại ở bảng trên và trong danh sách include của off-site, cùng commit.

## Lịch

Hiện có:

| Giờ | Việc | Tình trạng |
|---|---|---|
| ~01:04 | Backup cục bộ (`maintain_backup_platform_job`); lịch dự phòng 06:05 | Đang chạy |
| CN 00:30 | Chép nguội Metabase | Đang chạy. Sẽ chuyển sang hằng đêm |
| 09:00 | CRM backup và diễn tập CRM | Đang chạy. Cron `0 2 * * *` thiếu timezone nên chạy theo UTC; sẽ sửa về 02:00 |

Lịch đầy đủ sau khi triển khai: [ADR-019](../decisions/019-offsite-backup-and-recovery.md).

## Chụp nhất quán

Chưa viết. Mục này sẽ mô tả cách chụp từng thành phần (SQLite backup API, `COPY` DuckDB, chép nguội H2), định dạng `manifest.json` và các file `status/*.json`.

## Off-site

Chưa viết. Mục này sẽ gồm: sidecar `backup`, backend (thư mục, S3, SFTP, Google Drive), danh sách include, retention và `check`.

## Khôi phục

Hôm nay mỗi thành phần khôi phục theo một tài liệu riêng:

- Metabase H2: [`deployment.md` mục "Restore the H2 file"](./deployment.md#restore-the-h2-file).
- CRM: [`crm/docs/backup-restore-runbook.md`](../../crm/docs/backup-restore-runbook.md).

Công cụ `restore.sh` dùng chung cho mọi thành phần sẽ được ghi vào đây.

## Diễn tập

Hôm nay chỉ CRM có diễn tập tự động hằng ngày (`crm_restore_verify`); lần 15/10/2026 PASS. Diễn tập tuần (T2) và tháng (T3) từ bản ngoài máy sẽ được ghi vào đây.

## Cảnh báo

Hôm nay `maintain_backup_platform_job` gửi Lark khi xong, và failure sensor gửi Lark khi lỗi. Dead-man healthchecks.io và check tuổi backup sẽ được ghi vào đây.

## Dựng lại từ con số 0

Chưa viết. Mục này sẽ là runbook dựng lại trên máy mới, có thời gian mục tiêu và nhật ký diễn tập.

## Khoá và bàn giao

Chưa viết. Mục này sẽ gồm: ba khoá restic, Recovery Sheet, biên bản bàn giao, và runbook đổi quyền file secret trên host (0600, hoặc chỉ đọc cho đúng uid của container dùng file).
