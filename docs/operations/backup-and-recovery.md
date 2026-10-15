# Backup và khôi phục

Tài liệu sống về backup, khôi phục và dựng lại hệ thống. Quyết định và lý do: [ADR-019](../decisions/019-offsite-backup-and-recovery.md).

> **Trạng thái (15/10/2026):** đang xây dựng. Hôm nay chỉ có các backup **cục bộ**, nằm cùng ổ với dữ liệu: bản đêm `backup.sh`, bản chép nguội Metabase H2 và bản CRM. Chưa có bản ngoài máy. Các mục dưới đây được điền dần, mỗi mục cùng commit với phần code của nó. Đã viết: "Phạm vi dữ liệu", "Lịch" (phần cục bộ), "Chụp nhất quán", quyền file secret trong "Khoá và bàn giao".
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
| Bảng `main.monitor_taxonomy_parity_log` | trong `app_data/data_lake/sapo_warehouse.duckdb` | 82 dòng | Không dựng lại được | Có (parquet trong `exports/warehouse/`) | Append-only (`full_refresh=false`), đếm số đêm parity của bộ máy phân loại. Off-site xuất ra parquet |
| Lịch sử vận hành `ingestion_health.db` | named volume `monitoring_db` (`/app/var/data_lake/monitoring`) | 84 MB | Không dựng lại được | Có (SQLite backup API) | Bảng `ingestion_runs`, giữ 90 ngày; check freshness, row_trend, recon, KPI và digest đọc bảng này |
| Trạng thái schedule/sensor Dagster | named volume `dagster_home`, `schedules/schedules.db` | 321 MB | Trạng thái điều phối | Có (SQLite backup API) | Bật/tắt và cursor của schedule/sensor |
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

Phần cục bộ (giờ Asia/Ho_Chi_Minh):

| Giờ | Việc | Cách chạy |
|---|---|---|
| Hằng đêm 00:30 | Chép nguội Metabase H2 + xuất JSON (Metabase dừng ~20 giây) | Timer user `metabase-cold-backup.timer`, sinh bởi `scripts/backup/install-units.sh` |
| ~01:04 | Backup cục bộ `backup.sh` | Sensor `trigger_backup_after_purge` sau purge 01:00; lịch dự phòng 06:05 |
| 02:00 | CRM backup và diễn tập CRM | `crm_backup_schedule` (đã đặt `execution_timezone`; trước đó chạy 09:00 vì cron tính theo UTC) |

Lịch hằng đêm của Metabase và giờ 02:00 của CRM có hiệu lực từ lần deploy kèm thay đổi này (cài lại unit, khởi động lại `data_platform`). Lịch đầy đủ, gồm off-site và diễn tập: [ADR-019](../decisions/019-offsite-backup-and-recovery.md).

## Chụp nhất quán

Mỗi thành phần có trạng thái được chụp ở nơi sở hữu nó, theo cách cho ra một bản tự nhất quán, rồi ghi vào manifest.

| Thành phần | Ai chụp | Kỹ thuật | Bằng chứng nhất quán |
|---|---|---|---|
| Raw lake, `input_source` | `backup.sh` (trong `data_platform`, op giữ `duckdb_lock`) | Chép nóng `cp -a` | File chỉ được thêm; lớp off-site và diễn tập đọc lại mọi file |
| `sapo_warehouse.duckdb`, `serving/` | `backup.sh` | Chép nóng, `role: accelerator` | Không bảo đảm: chỉ dùng khi mở được, không thì `dbt build` |
| `ingestion_health.db` (volume `monitoring_db`) | `backup.sh` → `scripts/backup/sqlite_snapshot.py` | SQLite online backup API, bản chụp chuyển `journal_mode=DELETE` | `PRAGMA integrity_check` = ok, số dòng từng bảng, sha256 |
| `dagster_home/schedules/schedules.db` | `backup.sh` → `sqlite_snapshot.py` | Như trên; kèm `dagster.yaml`. Không chụp `history/`, `storage/` | Như trên |
| `main.monitor_taxonomy_parity_log` | `backup.sh` → `scripts/backup/duckdb_snapshot.py` | Mở `read_only`, trong một giao dịch: đếm dòng, `COPY` ra parquet, đọc lại parquet để so số dòng. File bị khoá ghi (writer chạy tay ngoài `duckdb_lock`) thì thử lại 3 → 30 giây, tối đa 180 giây | Số dòng nguồn = số dòng parquet, sha256 |
| Metabase H2 | Host, `scripts/backup/metabase_cold_backup.sh` | Dừng Metabase, chép, khởi động lại; khi healthy thì xuất JSON qua API vào `<bản chép>.export/` | Kích thước bằng nhau; số collection/card/dashboard lúc chép (`.export/manifest.json`) |
| CRM | `crm/ops/backup_crm.py` | SQLite backup API + gate | Gate A/B của diễn tập CRM |

**`manifest.json`** (mỗi thư mục `app_data/backups/<YYYYmmdd-HHMMSS>/`, `scripts/backup/backup_manifest.py`): `format`, `created_at`, `git_sha` (từ `BACKUP_GIT_SHA` nếu được đặt), và `components`. Mỗi thành phần có `component`, `kind` (`tree`, `sqlite`, `duckdb_export`), `role` (`source_of_truth`, `accelerator`, `copy`), `state` (`ok`, `skipped` khi nguồn không có, `error`). `tree` ghi số file và byte; `sqlite` ghi `path`, `bytes`, `sha256`, `integrity_check`, số dòng từng bảng; `duckdb_export` ghi từng bảng với `rows`, `bytes`, `sha256` và danh sách bảng vắng mặt (`skipped_tables`).

Kiểm lại một bản theo manifest:

```bash
docker exec data_platform python3 /app/scripts/backup/backup_manifest.py verify /app/var/backups/<YYYYmmdd-HHMMSS>
```

**File trạng thái** trong `app_data/backups/status/`, mỗi file ghi qua file tạm rồi đổi tên:

| File | Ai ghi | Nội dung |
|---|---|---|
| `local.json` | `backup.sh`, kể cả khi lỗi | `ok`, `state` (`ok`, `partial` khi bản chép dữ liệu xong nhưng một bước chụp hỏng, `failed`), `ts`, `duration_s`, `backup_dir`, trạng thái từng thành phần, `errors` |
| `metabase_cold.json` | `metabase_cold_backup.sh`, kể cả khi lỗi | `ok`, `state`, `kind`, `ts`, `duration_s`, `copy_ok`, `healthy`, `export` (`ok`, `failed`, `skipped`), `copy`, `counts` |

Khi `partial`, job Dagster vẫn xanh; thành phần hỏng nằm trong `errors`. Thư mục `status/` thuộc chủ của `app_data/backups` để cả container (root) lẫn script trên host ghi được.

Thời lượng đo trên bản sao cỡ prod (lake 1,4 GB, `schedules.db` 321 MB, `ingestion_health.db` 83 MB): 6 giây, so với 17–24 giây của bản chép cũ (bỏ `dagster_home/storage/`).

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

Ngoài phạm vi: công cụ shadow nội bộ của FG (`scripts/shadow/prepare-shadow.sh`, `scripts/shadow/prepare-deps.sh`) còn đường dẫn `/home/vantt` cứng; chúng không được cài cho khách nên không thuộc đường dựng lại. Mọi script và unit của backup thì không còn đường dẫn cứng (unit sinh từ template bằng `scripts/backup/install-units.sh`).

## Khoá và bàn giao

Chưa viết phần khoá restic, Recovery Sheet và biên bản bàn giao.

### Quyền file secret trên host

Chủ và quyền mà container dùng file vẫn đọc được (quyết định 15/10/2026):

| File | Container đọc | Chủ | Quyền |
|---|---|---|---|
| `app_data/secrets/gsheets-service-account.json` | `data_platform` (chạy root) | giữ nguyên (`vantt`) | `0600` |
| Credentials Cloudflare tunnel (`<tunnel-id>.json`, `cert.pem`, `config.yml` trong thư mục `config/` của stack `cloudflared`) | `cloudflared` (uid `65532`) | `65532:65532` | `0400` |

Áp trong giờ được duyệt, ngoài 02:30–04:00:

```bash
TUN=/home/vantt/cloudflared-tunnel/config          # thư mục credentials của tunnel trên máy này
SA=app_data/secrets/gsheets-service-account.json   # từ thư mục gốc của checkout
docker inspect -f '{{.Config.User}}' cloudflared   # phải là 65532:65532; khác thì dùng uid đó
stat -c '%U:%G %a %n' "$SA" "$TUN"/*               # ghi lại để hoàn tác
chmod 0600 "$SA"
sudo chown 65532:65532 "$TUN"/*.json "$TUN"/cert.pem "$TUN"/config.yml
sudo chmod 0400 "$TUN"/*.json "$TUN"/cert.pem "$TUN"/config.yml
docker restart cloudflared                         # chứng minh tunnel đọc được credentials
docker logs --since 2m cloudflared 2>&1 | grep -i -E 'registered|error' | tail -5
curl -s -o /dev/null -w '%{http_code}\n' https://bi.fwg.vn/api/health
curl -s -o /dev/null -w '%{http_code}\n' https://crm.fwg.vn/
```

Mã 530 hoặc 502 từ Cloudflare nghĩa là tunnel chưa nối lại; mã khác (200, hoặc 302/403 của Cloudflare Access) là tunnel đã chạy.

Kiểm key Google bằng một lần chạy xanh của một asset `sheets_*` trong Dagster. Hoàn tác: `chmod`/`chown` lại theo kết quả `stat` đã ghi, rồi `docker restart cloudflared`. Sau khi đổi, `vantt` không đọc được credentials tunnel nếu không có `sudo`; backup ngoài máy đọc chúng bằng container chạy root.
