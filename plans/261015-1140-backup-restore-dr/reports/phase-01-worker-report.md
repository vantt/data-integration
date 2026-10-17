# Phase 1: báo cáo thực thi (chụp nhất quán cục bộ)

> Ngày 15/10/2026. Worktree `/home/vantt/app/fg-dw-dr`, nhánh `feat/backup-offsite-dr` (trên `f1d646e7`), **chưa commit** (coordinator commit). Không đụng prod: không đổi container, timer, quyền file, schedule. Mọi lần chạy thử dùng bản sao trong shadow/scratch, đã xoá sau khi chạy.

## Kết quả

Code, test và tài liệu của phase 1 xong. Gate M: **FAIL chỉ ở một khác biệt có chủ đích** (giờ CRM, xem dưới); mọi bước khác xanh, golden 83/83 khớp. `scripts/checks/run-all.sh`: PASS.

## File

| File | Thay đổi |
|---|---|
| `scripts/backup/backup.sh` | Nhánh Docker viết lại: chép `data_lake` trừ `monitoring/`; `ingestion_health.db` và `dagster_home/schedules/schedules.db` qua `sqlite_snapshot.py`; chỉ chép thêm `dagster.yaml` (bỏ `history/`, `storage/`); xuất `BACKUP_EXPORT_TABLES` (mặc định `main.monitor_taxonomy_parity_log`) qua `duckdb_snapshot.py`; `manifest.json`; `status/local.json` (`ok`/`partial`/`failed`, ghi trong trap kể cả khi lỗi); xoá và báo lỗi nếu có file `.env*` trong bản backup; precheck đĩa không còn tính `history/` 10 GB; `git_sha` từ `BACKUP_GIT_SHA` hoặc `.git` nếu thấy |
| `scripts/backup/sqlite_snapshot.py` (mới) | SQLite online backup API → bản chụp `journal_mode=DELETE`, `integrity_check`, số dòng từng bảng, sha256 |
| `scripts/backup/duckdb_snapshot.py` (mới) | Mở `read_only` (thử lại 3 → 30 giây, tối đa 180 giây khi file bị khoá ghi), một giao dịch: đếm, `COPY` parquet, đọc lại so số dòng; bảng vắng mặt → `skipped_tables`; tên bảng kiểm bằng regex |
| `scripts/backup/backup_manifest.py` (mới, ngoài danh sách file của phase: cần cho "trình đọc manifest" mà phần Verification đòi) | `dir-entry`, `assemble`, `verify` (tính lại sha256 + số dòng), `status` (ghi nguyên tử) |
| `scripts/backup/metabase_cold_backup.sh` | Kind `nightly` (giữ `weekly`, `pre-deploy`); sau khi healthy xuất JSON qua API vào `<bản chép>.export/` (chỉ đọc `METABASE_API_KEY` từ `.env.docker` bằng `sed`, không `source`, không in, truyền qua env); xoay vòng cả thư mục `.export`; `status/metabase_cold.json` ghi ở mọi lối ra; sửa lỗi cũ: container không tồn tại không bị nhận ra (`docker inspect` in dòng trống nên `|| echo missing` thành `"\nmissing"`) |
| `scripts/backup/systemd/metabase-cold-backup.{service,timer}.in` (mới) | Template `@FG_PROJECT_ROOT@`, `OnCalendar=*-*-* 00:30:00 Asia/Ho_Chi_Minh`, `ExecStart=... nightly` |
| `scripts/backup/systemd/metabase-cold-backup.{service,timer}` | Xoá (thay bằng `.in`). Đã `git rm` rồi `git reset` để không đụng index: file đang ở trạng thái "deleted, unstaged" |
| `scripts/backup/install-units.sh` (mới) | Sinh unit vào `~/.config/systemd/user` (hoặc `--unit-dir`, khi đó chỉ render), `daemon-reload`, `enable --now` timer, cảnh báo khi linger tắt; từ chối thư mục không phải checkout hay có khoảng trắng |
| `orchestration/packs/crm/jobs.py` | `execution_timezone="Asia/Ho_Chi_Minh"` cho `crm_backup_schedule` |
| `orchestration/packs/__tests__/test_schedule_timezones.py` (mới) | Mọi `SCHEDULES` của connector/pack chạy theo giờ VN; riêng CRM `0 2 * * *` |
| `scripts/tests/test_backup_snapshots.py` (mới) | 17 test (xem dưới) |
| `scripts/backup/README.md` | Bảng "What gets backed up", bố cục một bản backup, `status/local.json`, `verify`, Metabase hằng đêm + export, cài unit bằng `install-units.sh` (bỏ hướng dẫn `cp` unit) |
| `docs/operations/deployment.md` | Mục Metabase: chép hằng đêm, `.export/`, `metabase_cold.json`, so số lượng khi khôi phục, timer sinh từ template |
| `docs/operations/backup-and-recovery.md` | Viết "Lịch" (phần cục bộ), "Chụp nhất quán" (bảng thành phần, định dạng manifest, file trạng thái, thời lượng đo), quyền file secret trong "Khoá và bàn giao" (runbook), ghi chú ngoài phạm vi cho `scripts/shadow/*` cứng `/home/vantt`; cập nhật cột "Bản cục bộ hiện nay" |

## Kiểm chứng

- **pytest** (trong container shadow, prod image, `--network none`): 31 test mới PASS (`test_backup_snapshots.py` 17, `test_schedule_timezones.py` 14 gồm 12 module jobs). Bao phủ:
  - `sqlite_snapshot`: DB WAL có tiến trình khác đang giữ giao dịch ghi mở → bản chụp `integrity_check=ok`, số dòng = dòng đã commit, file tự chứa (`journal_mode=delete`); nguồn thiếu → `skipped`; nguồn hỏng → `error`, không để lại file.
  - `duckdb_snapshot`: xuất đúng một bảng, bảng thiếu → `skipped_tables`; DB thiếu → `skipped`; tiến trình khác giữ khoá ghi 2 giây → thử lại rồi thành công; giữ khoá mãi → lùi 3, 6, 12, 24, 30… giây, bỏ cuộc trong 180 giây (`error`); từ chối tên bảng lạ.
  - Manifest: `assemble` + `verify` PASS; tamper xoá một dòng SQLite → sha256 và số dòng lệch bị bắt; tamper parquet ngắn đi → số dòng lệch bị bắt; file trạng thái liệt kê trạng thái từng thành phần.
  - `backup.sh` đầu-cuối (bố cục Docker giả trong `tmp_path`): đủ thư mục, không có `data_lake/monitoring`, `history/`, `storage/`, `desktop.ini`; manifest đúng vai trò; `verify` sạch; `local.json` `ok`. File `.env.docker` cài vào lake → bị xoá, không in nội dung, trạng thái `partial`. DATA_ROOT rỗng → thoát khác 0, `local.json` `failed`, không để thư mục hỏng.
  - `install-units.sh`: render không còn `@FG_PROJECT_ROOT@`, `ExecStart=<root>/... nightly`, `OnCalendar` hằng đêm; từ chối thư mục không phải checkout.
- **`backup.sh` trên bản sao cỡ prod** (thư mục scratch dưới `/home/vantt/app/fg-dw-shadow`, chạy bằng `scripts/shadow/run-shadow.sh`; lake = bản sao `lake-A` 1,4 GB, `schedules.db` 321 MB lấy từ bản backup cục bộ 15/10 01:04 (đọc file, không đụng volume prod), `input_source` 50 MB từ cùng bản backup): **6 giây** (bản cũ 17–24 giây), `state=ok`, 17 thành phần, `monitoring` 85.299 dòng `integrity ok` 0,5 giây, `dagster_home` 211.035 dòng `integrity ok` 1,8 giây, `exports_warehouse` 2 dòng 0,4 giây, `backup_manifest.py verify` OK. Metabase export báo cảnh báo như dự kiến (không mạng).
- **`metabase_cold_backup.sh`** trên một project giả trong scratch (file H2 giả, container `alpine` thay Metabase, API Metabase giả trên `127.0.0.1`, health qua `file://`): đường xanh (`state=ok`, `export=ok`, counts có), export lỗi (bản chép vẫn giữ, `export=failed`, thư mục `.export` bị xoá, exit 0), Metabase không healthy (`state=failed`, `healthy=false`, container được khởi động lại), container không tồn tại (`failed`, exit 1). Khoá API giả không xuất hiện trong log hay file trạng thái (`grep` = 0). Container và tiến trình thử đã dọn.
- **Unit:** `install-units.sh --unit-dir <scratch>` render xong, `systemd-analyze --user verify` PASS, lịch kế tiếp `Fri 2026-10-16 00:30:00 +07`. `grep -rn /home/vantt scripts/backup` = 0 dòng.
- **Gate M** (`scripts/shadow/gate.sh M` từ worktree): `GATE M: FAIL`, rc 1. Bước xanh: dbt build nhánh, `labels_mapped`, golden lake-A vs lake-B, dbt inventory, compiled SQL, module boundaries, dbt subset qua Dagster, pytest (436 passed), build lake rỗng + golden, bare-core profile (khác biệt in ra để đối chiếu, như mọi lần). Bước đỏ duy nhất: `4. dagster inventory`, một khác biệt: `schedules.crm_backup_schedule` `timezone: None -> 'Asia/Ho_Chi_Minh'` (cron, job, trạng thái mặc định giữ nguyên). Đây đúng là thay đổi user đã duyệt; `dagster_inventory.py diff` không có cờ chấp nhận thay đổi schedule (chỉ `--allow-new` cho phần thêm mới), nên gate không thể xanh với thay đổi này. Cần coordinator/user chấp nhận khác biệt này khi duyệt deploy. Lake nhánh đã được gate dọn.
- **`scripts/checks/run-all.sh`**: PASS (dbt parse, module boundaries, `dagster definitions validate`, pytest 436 passed, selftest engine 43/43).

## Runbook deploy D1 (chưa chạy; cần giờ user duyệt)

Giờ: ngoài 02:30–04:00, tránh 00:25–00:35 (chép nguội Metabase) và 00:55–01:10 (purge + backup). Deploy không đổi `docker-compose.yml` nên `docker compose start` là đủ.

1. Ghi trạng thái instigator (chỉ đọc):
   ```bash
   cd /home/vantt/app/fg-dataware-house
   python3 scripts/checks/instigator_state.py capture --out /tmp/instigators-before.json
   ```
2. `docker compose stop data_platform`
3. `git status --short` — commit seed CSV do job ghi trước (theo runbook "Refactor deploys" bước 3).
4. Ghi điểm rollback và fast-forward:
   ```bash
   git rev-parse HEAD > /tmp/deploy-rollback-sha
   git rev-parse feat/backup-offsite-dr > /tmp/deploy-branch-sha
   git merge --ff-only feat/backup-offsite-dr
   git diff "$(cat /tmp/deploy-rollback-sha)" "$(cat /tmp/deploy-branch-sha)" -- docker-compose.yml   # phải rỗng
   ```
5. `docker compose start data_platform`
6. Kiểm instigator: `capture --out /tmp/instigators-after.json` rồi `diff` với bản trước (không có schedule/sensor nào đổi trạng thái). Kiểm giờ CRM mới qua GraphQL (chỉ đọc), `scheduleOrError` của `crm_backup_schedule` cho `executionTimezone = Asia/Ho_Chi_Minh`, tick kế 02:00 +07.
7. Cài lại timer Metabase (tên unit giữ nguyên, nên `install-units.sh` ghi đè hai file cũ):
   ```bash
   systemctl --user cat metabase-cold-backup.service > /tmp/metabase-units-before.txt
   systemctl --user cat metabase-cold-backup.timer  >> /tmp/metabase-units-before.txt
   scripts/backup/install-units.sh                                       # render, daemon-reload, enable --now
   systemctl --user list-timers metabase-cold-backup.timer               # NEXT = 00:30 đêm nay
   systemctl --user cat metabase-cold-backup.service | grep ExecStart    # ... metabase_cold_backup.sh nightly
   ```
8. Chạy thử một backup cục bộ ngay (Dagster UI → `maintain_backup_platform_job` → Launch; giữ `duckdb_lock` khoảng 10 giây; bản thêm này đẩy bản cũ nhất ra khỏi vòng 7 bản), rồi:
   ```bash
   cat app_data/backups/status/local.json                    # state = ok
   B=$(ls app_data/backups | grep -E '^[0-9]{8}-' | sort | tail -1)
   docker exec data_platform python3 /app/scripts/backup/backup_manifest.py verify /app/var/backups/$B   # verify: OK
   ls app_data/backups/$B/exports/warehouse/ app_data/backups/$B/app_data/monitoring/ app_data/backups/$B/app_data/dagster_home/schedules/
   ```
9. Quyền file secret: các lệnh ở `docs/operations/backup-and-recovery.md` mục "Quyền file secret trên host" (ghi `stat` trước; `chmod 0600` key Google; `sudo chown 65532:65532` + `chmod 0400` credentials tunnel; `docker restart cloudflared`; kiểm log `Registered tunnel connection`, `bi.fwg.vn`, `crm.fwg.vn` không trả 530/502; một asset `sheets_*` chạy xanh).
10. Sáng hôm sau (chỉ đọc): `metabase_cold.json` `state=ok`, `export=ok`, counts ≈ 43/888/23; `local.json` `state=ok`; `crm_backup_job` chạy ~02:00 (GraphQL `runsOrError`), `crm_restore_verify` `pass`; nightly 03:00 xanh. Ngày deploy CRM có thể chạy hai lần (09:00 cũ trước deploy, 02:00 mới sau): vô hại.

**Rollback:**
```bash
docker compose stop data_platform
git revert --no-edit "$(cat /tmp/deploy-rollback-sha)".."$(cat /tmp/deploy-branch-sha)"
docker compose start data_platform
cp scripts/backup/systemd/metabase-cold-backup.service scripts/backup/systemd/metabase-cold-backup.timer ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user restart metabase-cold-backup.timer
```
Quyền file: đặt lại theo `stat` đã ghi ở bước 9, `docker restart cloudflared`. Bản backup đã tạo theo định dạng mới vẫn đọc được bằng tay.

## Câu hỏi và việc còn mở

0. **Chấp nhận khác biệt gate:** gate M đỏ chỉ vì `crm_backup_schedule` có `execution_timezone` (thay đổi đã duyệt). Coordinator xác nhận chấp nhận trước deploy D1; nếu muốn gate tự cho qua những thay đổi như vậy thì cần thêm cờ cho `scripts/checks/dagster_inventory.py` (ngoài phạm vi phase này).

1. **Thông báo Lark khi `partial`:** `orchestration/ops/system_backup.py` (ngoài danh sách file của phase 1) vẫn gửi card "Backup xong" màu xanh khi `local.json` là `partial`. Đề xuất phase 4 (cảnh báo, check `backup_freshness` đọc `state`) xử lý, hoặc cho phép sửa ngay trong phase này.
2. **`git_sha` trong manifest ở prod sẽ rỗng:** container chỉ mount thư mục con, không có `.git`; `BACKUP_GIT_SHA` chưa được đặt. Wrapper off-site (phase 2) ghi `repo-state/` trên host nên không chặn; nếu muốn có ngay thì cần sửa `docker-compose.yml` (thuộc phase 2/6).
3. **Chạy thử chép nguội Metabase ngay khi deploy** (Metabase dừng ~20 giây) hay đợi 00:30? Runbook mặc định đợi.
4. Bản chép nguội `weekly` cũ (2 file, 96 MB) nằm lại tới khi xoá tay; ghi trong README.
