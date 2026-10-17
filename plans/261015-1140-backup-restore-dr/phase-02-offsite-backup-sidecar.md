---
phase: 2
title: "Sidecar backup + off-site (restic/rclone, nhiều backend, khoá, Recovery Sheet)"
status: pending
priority: P1
effort: "1.5d"
dependencies: [1]
---

# Phase 2: Sidecar `backup` và off-site

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng. Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/operations/backup-and-recovery.md` mục **Off-site** (kiến trúc sidecar, mount, danh sách include và lý do, một lần chạy gồm những bước nào, file trạng thái, retention, cách đổi backend) và **Khoá và bàn giao** (3 khoá, Recovery Sheet, mẫu biên bản); `scripts/backup/backends/{local,s3,sftp,gdrive-sa}.md` (mỗi file: chuẩn bị phía khách, biến cấu hình, lệnh kiểm); `scripts/backup/README.md` (thêm sidecar); ADR 019 cập nhật nếu quyết định đổi.

## Mục tiêu

Một lệnh `scripts/backup/offsite.sh` đẩy bản mã hoá của mọi nguồn sự thật ra một repo restic ở bất kỳ backend nào trong bốn loại (thư mục local cho test, S3, SFTP, Google Drive qua service account + Shared Drive), có forget/prune/check, trạng thái và cảnh báo. Làm và kiểm trên worktree với dữ liệu shadow; **không đụng prod** trong phase này.

## Thiết kế

### Image và service

- `Dockerfile.backup`: `FROM python:3.12-slim@sha256:<digest>`; tải restic 0.19.x và rclone (phiên bản ghim) từ GitHub release, kiểm sha256 cứng trong Dockerfile; `apt-get install sqlite3 ca-certificates`; `pip install requests` (để dùng lại `orchestration/notifications/lark_client.py`, mount `:ro`, thay vì viết client Lark thứ hai). Không Docker CLI.
- `docker-compose.yml` thêm service `backup` với `profiles: [ops]`, `build: Dockerfile.backup`, `env_file: ${FG_BACKUP_CONFIG_DIR}/env`, mount theo design §6, mạng riêng `backup_egress` (bridge, không `caddy_net`), `mem_limit: 1g`, `cpus: 1`. Mount thêm so với bản đầu (phase 0): `./app_data/analysis:/src/analysis:ro` và `${FG_CLOUDFLARED_DIR:-/nonexistent}:/src/cloudflared:ro` (credentials tunnel ngoài repo, trên prod `/home/vantt/cloudflared-tunnel/config`; container `cloudflared` chạy uid 65532 nên sidecar chạy root để đọc được dù quyền là 0400/0600). Không đọc `monitoring_db` hay `dagster_home` trực tiếp: lấy bản chụp SQLite trong bản cục bộ mới nhất (phase 1). Thêm volume `backup_staging`, `restic_cache`. `docker compose up -d` không khởi động service này (profile).
- Cấu hình host `${FG_BACKUP_CONFIG_DIR}` (mặc định `~/.config/fg-backup`, quyền 0700): `env` (0600: `TENANT_ID`, `FG_CLOUDFLARED_DIR`, `RESTIC_REPOSITORY`, `RESTIC_PASSWORD_FILE=/config/restic.pass`, `RCLONE_CONFIG=/config/rclone.conf`, `HC_PING_URL_OFFSITE`, `HC_PING_URL_DRILL`, `LARK_ALERT_WEBHOOK`, `LARK_ALERT_SECRET`), `restic.pass` (0600, `key-host`), `rclone.conf` (0600), `sa.json` khi dùng service account.

### Lệnh trong sidecar (`scripts/backup/sidecar/`)

| Lệnh | Việc |
|---|---|
| `init` | `restic init`; `restic key add` hai lần cho `key-customer`, `key-customer-2` (mật khẩu sinh ngẫu nhiên 6 nhóm từ, hiển thị **một lần** trên terminal để in, không ghi ra đĩa); sinh `recovery-sheet.md` (không chứa khoá, có ô trống để viết tay hoặc dán bản in khoá) |
| `offsite` | Theo design §6.1: preflight tuổi + include không rỗng → staging → `restic backup` → `forget` → (CN) `prune` → `check --read-data-subset` → trạng thái |
| `check-full` | `restic check --read-data` (chạy tay, ví dụ trước bàn giao) |
| `snapshots` | Liệt kê theo tenant |
| `key-rotate-host` | `key add` khoá host mới, `key remove` khoá cũ (khi đổi máy) |

Wrapper host `scripts/backup/offsite.sh`: ping `/start`; ghi `repo-state/` (`git rev-parse HEAD`, `git status --porcelain`, `git diff` của seed và file đã theo dõi) và `host-state/` (unit systemd user, `crontab -l`, đường dẫn compose của stack phụ thuộc theo phase 0 Q10) vào `app_data/backups/offsite-staging/` (owner hiện tại, 0700); `docker compose --profile ops run --rm backup offsite`; ping `/<rc>`; lỗi thì Lark (sidecar gửi khi chạy được; wrapper gửi bằng `curl` khi chính sidecar không khởi động được, ví dụ image hỏng).

### Danh sách include

`scripts/backup/offsite-include.txt` (từ bản nháp trong [reports/phase-00-findings.md](reports/phase-00-findings.md) mục "Bản nháp", sửa theo quyết định user 15/10: thêm `data_lake/backup`, `app_data/analysis`, credentials tunnel; `.env.local` ghi `exclude: file dev cũ, prod không dùng`), mỗi dòng có chú thích. Không có `--exclude` cho file tạm của dlt (dlt ghi thẳng tên cuối, F-Q14); exclude chỉ gồm phái sinh và mồ côi (`sapo_warehouse.duckdb*`, `serving/`, `export/`, `crm_export/`, `sapo_raw_staging/`, `test_raw/`, lớp host `data_lake/monitoring`, `desktop.ini`). Kèm check `scripts/checks/check_backup_scope.py`: so tập file bị gitignore ngoài các thư mục sinh ra (`target`, `dbt_packages`, `__pycache__`, `node_modules`, `logs`) với allowlist trong file include (mỗi file phải được ghi là `include` hoặc `exclude: <lý do>`); file mới chưa phân loại → fail. Chạy thêm một bước trong `scripts/checks/run-all.sh` (đã có, phase 0 xác nhận; bước chạy bằng `python3` host như `check_boundaries.py`) và trong preflight off-site (preflight chỉ cảnh báo, không chặn backup).

### Secret không bao giờ ở dạng rõ ngoài máy

- Sidecar đọc secret trực tiếp từ mount `:ro`, không chép vào staging (staging là volume trên cùng máy, nhưng giữ nguyên tắc "không có bản rõ thứ hai").
- Kiểm sau mỗi lần chạy: `find app_data/backups /staging -name '.env*' -o -name '*.json' -path '*secrets*' -o -name '*.pem' -o -path '*cloudflared*'` phải rỗng; có thì xoá và đánh lỗi.
- Tag thành phần `cloudflared` riêng trong đường dẫn ổn định (`/src/cloudflared`) để `restore.sh --mode drill` bỏ qua được (phase 3).

### Backend

| Backend | `RESTIC_REPOSITORY` | Ghi chú |
|---|---|---|
| Thư mục local (chỉ test) | `/repo` | Volume test |
| S3 (S3 trong nước, MinIO, B2, R2) | `s3:https://<endpoint>/<bucket>/<tenant>` | Path-style tuỳ provider; thử MinIO trong test |
| SFTP (NAS) | `sftp:<user>@<host>:/<path>/<tenant>` | Khoá SSH trong `${FG_BACKUP_CONFIG_DIR}` |
| Google Drive, service account + Shared Drive | `rclone:gdrive:fg-backup/<tenant>` với remote `gdrive` có `service_account_file=/config/sa.json`, `team_drive=<id>`, `scope=drive` | Đường của Fine Japan (phase 5) |
| Google Drive, OAuth `drive.file` | Như trên, remote có `client_id` của app FG, `scope=drive.file`, token | Phase 7 |

Tuỳ chọn rclone cho Drive: `--drive-stop-on-upload-limit`, `--drive-chunk-size 32M`; restic `--pack-size 64`.

## Files

- Create: `Dockerfile.backup`, `scripts/backup/offsite.sh`, `scripts/backup/sidecar/{entrypoint.sh,offsite.sh,init.sh,common.sh,notify.py}`, `scripts/backup/offsite-include.txt`, `scripts/checks/check_backup_scope.py`, `scripts/backup/backends/{local,s3,sftp,gdrive-sa}.md`, `scripts/backup/systemd/fg-offsite-backup.{service,timer}.in`, test `scripts/tests/test_backup_scope.py`, `scripts/tests/backup_integration/` (compose test với MinIO và SFTP).
- Modify: `docker-compose.yml` (service `backup`, mạng `backup_egress`, volume `backup_staging`, `restic_cache`), `scripts/backup/install-units.sh` (thêm timer off-site), `scripts/checks/run-all.sh` (bước `check_backup_scope.py`), tài liệu ở khối đầu.

## Verification

- pytest: preflight tuổi (bản cục bộ 27 giờ → thành phần `stale`, lệnh thoát khác 0 nhưng snapshot vẫn tạo); include rỗng → fail; `check_backup_scope.py` fail khi thêm một file gitignore mới chưa phân loại.
- Tích hợp trên worktree (dữ liệu là một bản sao lake shadow, không phải `app_data` prod): `init` → `offsite` 2 lần (lần 2 chỉ thêm dữ liệu mới, ghi kích thước thêm) → `forget` → `check` với **ba backend** local, MinIO, SFTP. `restic snapshots` có đủ tag; `restic ls latest` có đủ đường dẫn ổn định.
- Mở repo bằng `key-customer` (không có `restic.pass` của host) liệt kê được snapshot.
- Kiểm secret: sau chạy, lệnh `find` ở trên trả rỗng.
- `docker compose config` hợp lệ; `docker compose up -d --dry-run` (hoặc `docker compose config --services` không kèm profile) **không** liệt kê `backup`.
- Thời gian một lần `offsite` trên lake shadow cỡ prod và lượng upload lần đầu ghi vào báo cáo.

**Đụng prod:** không. **Đổi số:** không.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Image restic/rclone tải về bị thay (chuỗi cung ứng) | sha256 cứng trong Dockerfile; build fail nếu lệch |
| Container root ghi file root-owned vào `app_data/backups/status` | Chỉ file trạng thái nhỏ, quyền 0644; người vận hành chỉ cần đọc |
| restic quét lại toàn bộ mỗi lần vì hostname đổi | `--host <tenant>` cố định; kiểm lần 2 nhanh hơn rõ rệt |
| Repo bị khoá treo do lần chạy trước chết giữa chừng | Đầu mỗi lần chạy `restic unlock` (chỉ gỡ khoá cũ hơn 30 phút, mặc định của restic) |

## Rollback

Không deploy prod trong phase này. Trên worktree: xoá service và file mới.
