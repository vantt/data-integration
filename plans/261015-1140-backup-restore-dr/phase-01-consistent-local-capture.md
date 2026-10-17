---
phase: 1
title: "Chụp nhất quán cục bộ: schedules.db, monitoring, parity log, manifest Metabase, file trạng thái, giờ CRM, bỏ đường dẫn cứng"
status: pending
priority: P1
effort: "0.75d"
dependencies: [0]
---

# Phase 1: Chụp nhất quán cục bộ

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng. Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/operations/backup-and-recovery.md` mục **Chụp nhất quán** (bảng theo thành phần, định dạng `manifest.json`, file trạng thái) và **Lịch** (phần cục bộ); `scripts/backup/README.md` (bảng "What gets backed up", cách cài unit bằng `install-units.sh`, bỏ hướng dẫn `cp` unit thủ công); `docs/operations/deployment.md` mục "Metabase: backup and restore" (bản chép nguội kèm manifest, cách cài timer mới).

## Mục tiêu

Mỗi thành phần có trạng thái mà off-site cần lấy từ bản cục bộ đều có bản chụp **nhất quán** kèm `manifest.json`, và có file trạng thái để kiểm tuổi. Không thêm job mới. Chỉ đổi giờ ở hai chỗ user đã duyệt sau phase 0 (plan.md mục "Đã chốt"): CRM backup về 02:00 giờ VN, chép nguội Metabase từ hằng tuần sang hằng đêm 00:30.

Đầu vào: [reports/phase-00-findings.md](reports/phase-00-findings.md) Q3, Q4, Q5, Q11, Q16; design §3.1, §4, §5.

## Thiết kế

### `backup.sh` (chạy trong `data_platform`, op giữ `duckdb_lock`)

- **`scripts/backup/sqlite_snapshot.py <src.db> <dst.db>`** (helper chung): `sqlite3.Connection.backup()` vào đích, `PRAGMA integrity_check` trên bản chụp, ghi sha256 + số dòng từng bảng vào manifest.
- **dagster_home:** thay `cp -a` (nhánh Docker, `scripts/backup/backup.sh:158-166`) bằng `sqlite_snapshot.py` **chỉ** cho `schedules/schedules.db` (321 MB: trạng thái + cursor schedule/sensor); chép thường `dagster.yaml` (để so, dù giống bản trong git). **Không** chép `storage/` (498 MB: output IO manager, compute log, tự sinh lại) và `history/` (10,1 GB, gồm event log `runs/index.db`), như `prune_dagster_history` (`:36-42`) đang bỏ `history/`. `schedule_state.db` 0 byte: bỏ.
- **monitoring:** `ingestion_health.db` là **SQLite WAL** (không phải DuckDB) nằm trên named volume `monitoring_db` tại `/app/var/data_lake/monitoring` (`docker-compose.yml:44`). Bước chép `data_lake` loại thư mục `monitoring/` khỏi `cp -a`, rồi `sqlite_snapshot.py /app/var/data_lake/monitoring/ingestion_health.db <ts>/app_data/monitoring/ingestion_health.db`. Không chép `ingestion_health.duckdb` (cũ, không còn writer từ 20/05) và `desktop.ini`.
- **Bảng không dựng lại được:** `scripts/backup/duckdb_snapshot.py <db> <out_dir> --tables main.monitor_taxonomy_parity_log`: mở `sapo_warehouse.duckdb` `read_only` (op đang giữ `duckdb_lock` nên không trùng dbt/serving; writer ngoài khoá chỉ là script chạy tay, F-Q4); nếu bị khoá thì thử lại có lùi thời gian (tối đa 10 lần, 3 giây → 30 giây); trong **một** giao dịch đọc số dòng rồi `COPY <table> TO '<out_dir>/<table>.parquet' (FORMAT parquet)`; ghi manifest. Ghi vào `<ts>/exports/warehouse/`. Danh sách bảng là tham số để plan riêng giá/tồn thêm bảng sau này. Bảng chưa tồn tại (DB mới dựng) thì ghi `skipped`, không lỗi.
- **Chép nóng `sapo_warehouse.duckdb` và `serving`:** giữ nguyên (bản "máy tăng tốc", design §5); ghi rõ trong manifest `role: accelerator`.
- **Manifest tổng** `app_data/backups/<ts>/manifest.json`: `created_at`, `git_sha` (đọc từ `/app` nếu có `.git`, hoặc biến môi trường do runbook đặt), danh sách thành phần với `role` (`source_of_truth` | `accelerator`), sha256 và số dòng.
- **File trạng thái:** cuối script ghi `app_data/backups/status/local.json` (`ok`, `ts`, `duration_s`, `components`, `errors`) bằng cách ghi file tạm rồi đổi tên. Ghi cả khi lỗi (trong trap).
- Không đổi danh sách config ở bước 2 (`:192`); `.env.docker` vẫn không có trong container nên không chép; thêm assert: nếu có file tên `.env*` trong thư mục đích thì xoá và ghi lỗi (bảo vệ quyết định D6 nếu sau này ai mount `.env.docker` vào).
- Thời gian chạy: hiện 17–24 giây (F-Q13); backup API cho `schedules.db` 321 MB và `ingestion_health.db` 84 MB thêm vài giây, bỏ `storage/` bớt ~500 MB chép; vẫn xa `_BACKUP_TIMEOUT_SEC = 600` (`orchestration/ops/system_backup.py:25`), đo lại trên shadow.
- `app_data/analysis` không mount vào `data_platform` và không có writer: không chép vào bản cục bộ, sidecar off-site đọc thẳng (phase 2).

### Giờ CRM backup

`crm_backup_schedule` (`orchestration/packs/crm/jobs.py:15-20`) thêm `execution_timezone="Asia/Ho_Chi_Minh"` như mọi schedule khác; cron giữ `0 2 * * *`. Hiện chạy 09:00 giờ VN (F-Q11). Test: một unit test đọc `SCHEDULES` của pack `crm` và khẳng định timezone (cùng chỗ với test pack hiện có trong `orchestration/`).

### `metabase_cold_backup.sh` (host)

- Sau khi Metabase healthy, chạy `python3 scripts/backup/metabase_export.py <DEST>.export` (cùng script `backup.sh` đang dùng, `scripts/backup/backup.sh:206`) với `METABASE_URL=http://127.0.0.1:3001` và khoá API đọc từ `.env.docker` bằng cách nạp biến (không in). Manifest của export chính là số lượng tại thời điểm chép. Lỗi export là cảnh báo, không làm hỏng bản chép (giữ hành vi `:85-86`).
- Ghi `app_data/backups/status/metabase_cold.json`.
- `PROJECT_ROOT` đã suy ra từ vị trí script (`:22`); giữ nguyên.

### Unit systemd không còn đường dẫn cứng

- `scripts/backup/systemd/metabase-cold-backup.service.in` và `.timer.in` (thay hai file hiện có), dùng `@FG_PROJECT_ROOT@`; `OnCalendar=*-*-* 00:30:00` (hằng đêm, user chốt 15/10). Đổi `kind` của bản chép từ `weekly` sang `nightly` (giữ 7 bản; bản `weekly` cũ để nguyên tới khi hết hạn).
- `scripts/backup/install-units.sh [--project-root <dir>]`: sinh unit vào `~/.config/systemd/user/`, `daemon-reload`, `enable --now` các timer được chỉ định, kiểm linger. Phase 2 và 4 thêm template của mình vào cùng script.
- `scripts/shadow/prepare-shadow.sh:15` và `prepare-deps.sh:11` cũng cứng `/home/vantt`: **không sửa** trong plan này (công cụ shadow nội bộ FG, không cài cho khách); ghi vào mục Ngoài phạm vi của tài liệu.

## Files

- Modify: `scripts/backup/backup.sh`, `scripts/backup/metabase_cold_backup.sh`, `orchestration/packs/crm/jobs.py`, `scripts/backup/README.md`, `docs/operations/deployment.md` (mục Metabase), `docs/operations/backup-and-recovery.md`.
- Create: `scripts/backup/sqlite_snapshot.py`, `scripts/backup/duckdb_snapshot.py`, `scripts/backup/install-units.sh`, `scripts/backup/systemd/metabase-cold-backup.{service,timer}.in`, test `scripts/tests/test_backup_snapshots.py`.
- Delete: `scripts/backup/systemd/metabase-cold-backup.{service,timer}` (thay bằng `.in`).

## Verification

- pytest: `sqlite_snapshot.py` trên DB có WAL đang mở ghi ở tiến trình khác cho bản chụp `integrity_check = ok` và số dòng khớp; `duckdb_snapshot.py --tables` xuất đúng một bảng, bảng thiếu thì `skipped`, thử lại khi file đang bị một tiến trình khác giữ ghi rồi thành công khi tiến trình đó đóng; manifest khớp số dòng nguồn; tamper (xoá một dòng ở bản chụp) bị trình đọc manifest bắt.
- Chạy `backup.sh` trên shadow (`scripts/shadow/run-shadow.sh` với `BACKUP_ROOT` trong shadow): có manifest, có `status/local.json`, thời gian chạy ghi vào báo cáo.
- `install-units.sh --project-root <worktree>` sinh unit không chứa `/home/vantt` (`grep`), `systemd-analyze --user verify` pass.
- **Deploy D1 (cần giờ user duyệt, ngoài 02:30–04:00):** theo runbook "Refactor deploys"; sau đó cài lại timer Metabase bằng `install-units.sh` (timer cũ disable trước). Kiểm: `systemctl --user list-timers` thấy timer mới chạy hằng đêm 00:30; đêm kế tiếp có `metabase-nightly-*.mv.db.export/manifest.json`, `maintain_backup_platform_job` xanh, `status/local.json` `ok=true`, manifest có `schedules.db` và `ingestion_health.db` với `integrity_check = ok`, số dòng `monitor_taxonomy_parity_log` khớp truy vấn đếm trên bản chụp; run kế tiếp của `crm_backup_job` bắt đầu ~02:00 giờ VN (GraphQL `runsOrError`) và `crm_restore_verify` vẫn `pass`.
- **Quyền file secret (cùng giờ deploy D1, user chốt 15/10):** trước khi đổi, ghi lại owner/mode hiện có. `app_data/secrets/gsheets-service-account.json` → `0600` (chỉ `data_platform` đọc, chạy root); kiểm bằng một lần `sheets_*` asset xanh. Credentials tunnel: **chờ câu hỏi mở 6 của plan.md** (container `cloudflared` chạy uid 65532, file thuộc `vantt`: `0600` giữ chủ `vantt` sẽ làm tunnel không khởi động lại được); sau khi đổi, `docker restart cloudflared` trong giờ duyệt và kiểm `bi.fwg.vn`, `crm.fwg.vn` trả lời. Ghi bước vào `docs/operations/backup-and-recovery.md` mục "Khoá và bàn giao".

**Đụng prod:** có (deploy D1). **Đổi số dashboard:** không.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| `COPY` bảng parity log bị khoá lâu (writer chạy tay ngoài `duckdb_lock`) làm backup quá 600 giây | Giới hạn tổng thời gian thử lại 3 phút; quá thì ghi lỗi thành phần đó, các thành phần khác vẫn xong (không làm đỏ cả job, trạng thái ghi `partial`) |
| Sửa timezone CRM làm job chạy hai lần trong ngày deploy (09:00 cũ và 02:00 mới) | Vô hại (backup + diễn tập idempotent); ghi vào nhật ký deploy |
| Chép nguội Metabase hằng đêm làm gián đoạn ~18 giây mỗi đêm | Đã được user chấp nhận; giờ 00:30 ngoài giờ dùng |
| `sqlite_snapshot.py` khoá DB Dagster làm daemon chờ | Backup API chép theo trang, giữ khoá đọc ngắn; chỉ `schedules.db` (321 MB); đo trên shadow |
| Đổi tên file unit làm timer cũ còn chạy song song | Bước deploy disable timer cũ trước khi cài mới; kiểm `list-timers` chỉ còn một |

## Rollback

`git revert` theo runbook; `install-units.sh` chạy lại với bản cũ hoặc copy lại hai file unit cũ từ git. Bản backup đã tạo theo định dạng mới vẫn đọc được bằng tay (chỉ thêm file, không bỏ file cũ).
