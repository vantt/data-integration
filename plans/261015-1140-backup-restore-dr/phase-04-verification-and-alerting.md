---
phase: 4
title: "Xác minh tự động (T2 tuần, T3 tháng, tamper) + cảnh báo Lark/dead-man + check tuổi backup"
status: pending
priority: P1
effort: "1.5d"
dependencies: [3]
---

# Phase 4: Xác minh tự động và cảnh báo

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng. Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/operations/backup-and-recovery.md` mục **Diễn tập** (T1/T2/T3, gate, tamper, tài nguyên, đọc kết quả, xử lý khi FAIL) và **Cảnh báo** (Lark, healthchecks, check `backup_freshness` với ngưỡng từng thành phần, cách tắt tạm khi bảo trì); `docs/operations/backup-restore-completeness-runbook.md` Part 2 (trỏ tới T2/T3 thật thay cho "to implement") và "Honest limits" (đã có off-site + cảnh báo tuổi); `orchestration/docs/SCHEDULES.md` (thêm dòng check mới; timer host ghi chú ở tài liệu chung); `docs/architecture/locking-and-concurrency.md` (T3 không đụng `duckdb_lock` prod vì chạy trên lake riêng).

## Mục tiêu

Chứng minh định kỳ, tự động, rằng bản **ngoài máy** khôi phục được và dựng lại được hệ thống; mọi hỏng hóc (backup không chạy, chạy lỗi, bản quá cũ, diễn tập FAIL) đều tới người nhận qua hai kênh độc lập. Code làm trên worktree; deploy cùng D2 ở phase 5.

## Thiết kế

### T2: diễn tập khôi phục hằng tuần (`scripts/backup/restore-drill.sh weekly`)

Timer host CN 05:15 (`fg-restore-drill-weekly.timer`, `Persistent=false`). Các bước:

1. Preflight: `MemAvailable ≥ 3 GiB` và đĩa trống ≥ 2 lần kích thước snapshot mới nhất (bài học L58 trong runbook completeness); không đủ → trạng thái `skipped` + Lark mức cảnh báo (không im lặng).
2. Ghi dấu vân tay prod: kích thước + mtime của `metabase.db.mv.db`, `crm.db` (qua `docker run --rm -v <crm_data>:/d:ro alpine stat`), `sapo_warehouse.duckdb`, `dagster_home`.
3. `restore.sh extract --snapshot latest --into <scratch>` **từ repo ngoài máy**, rồi `restore.sh verify` (gate a, b, c ở design §9).
4. Gate d, Metabase: `docker run --rm --name mb-restore-verify --network none -m 1536m -v <scratch>/metabase:/home/metabase/data <image metabase đang chạy>` với biến email tắt; chờ `/api/health` bằng `docker exec ... curl` (image có curl, `Dockerfile.metabase`); đếm collection/card/dashboard qua API trong container bằng khoá API có sẵn trong H2 (khoá nằm trong `.env.docker` đã khôi phục ở scratch, chỉ truyền qua biến môi trường của `docker exec`, không in); so `<copy>.export/manifest.json` của phase 1.
5. Gate e, CRM: `crm/ops/restore_verify_crm.py --backups-dir <scratch>/crm` (phase 3), chạy trên host. Diễn tập CRM ở chế độ host dùng Docker của host trực tiếp, giống chế độ dev đã có; không cần thêm socket cho container nào.
6. Gate f: dấu vân tay prod không đổi.
7. Mỗi quý (tuần đầu tháng 1, 4, 7, 10): bước 3 dùng `RESTIC_PASSWORD_COMMAND` hỏi khoá khách thay khoá host **chỉ khi chạy tay có người**; timer tự động thì ghi nhắc việc vào trạng thái `customer_key_due=true`, check tuổi báo vàng tới khi có lần chạy tay với khoá khách (`restore-drill.sh weekly --customer-key`).
8. Xoá scratch khi PASS; giữ khi FAIL (đến lần chạy kế tiếp). Ghi `status/drill_weekly.json`, ping healthchecks check `drill`, Lark khi FAIL.

### T3: dựng lại hằng tháng (`restore-drill.sh monthly`)

Timer CN đầu tháng 06:00 (`Sun *-*-01..07 06:00`). Tái dùng công cụ shadow:

1. Extract raw (gồm `data_lake/backup`), exports, seeds, input, analysis từ snapshot vào một lake mới dưới `SHADOW_ROOT` riêng của diễn tập (`guard_not_prod.py`).
2. Không đặt `sapo_warehouse.duckdb` (dựng từ đầu); tạo DB rỗng rồi nạp `monitor_taxonomy_parity_log` từ parquet export **trước** `dbt build` (như `restore.sh apply --component exports`). Không còn "bảng tích luỹ rolling" để đặt lại (phase 0: GC giữ 3 lần build, không có lịch sử; plan riêng giá/tồn sẽ thêm).
3. `scripts/shadow/build-lake.sh <checkout đúng git sha của snapshot> <lake>` (build như prod, `run-shadow.sh` đã cô lập mạng và mount); giới hạn `--cpus 2 -m 4g`.
4. So bất biến: số dòng mỗi bảng trong `scripts/checks/public_models.yaml` so với prod tại thời điểm snapshot. Prod hôm nay có thêm dữ liệu sau snapshot, nên so trên dữ liệu có ngày ≤ ngày snapshot khi bảng có cột ngày, ngược lại dùng ngưỡng `row_trend_checks`. Golden snapshot của prod do T3 tự chụp **đọc từ serving prod chỉ đọc** ngay trước khi build (dùng `golden_snapshot.py`, đã chạy chỉ đọc trên prod trong các gate trước).
5. Ghi `status/drill_monthly.json` (gồm thời gian `dbt build`, đầu vào cho RTO), dọn lake.

### Tamper

`restore-drill.sh weekly --tamper <partition|crm-cell|h2-truncate|manifest>` và `monthly --tamper partition`: phá bản đã giải nén rồi chạy gate, **phải** FAIL. Chạy khi nghiệm thu và trong pytest tích hợp mỗi khi đổi `restore_verify.py` hoặc `drill_gates.py`.

### Cảnh báo

- **Lark:** mọi job host gửi qua `notify.py` (bọc `orchestration/notifications/lark_client.py`, cùng định dạng card với `system_backup.py:105-114`). Gửi khi FAIL, `partial`, `skipped`; không gửi khi xanh (tránh nhiễu), trừ tin tổng tuần sau T2.
- **Dead-man (user chốt 15/10):** healthchecks.io gói miễn phí, 5 check: `backup-local` (01:04, ping từ `system_backup.py`/`backup.sh`), `offsite` (03:30, grace 6 giờ), `metabase-cold` (hằng đêm 00:30), `crm` (02:00, ping từ asset `crm_restore_verify` hoặc từ file trạng thái), `drill-weekly` (CN 05:15, grace 12 giờ); `drill-monthly` thêm nếu còn chỗ (gói miễn phí cho 20 check). Kênh: email + webhook vào nhóm Lark nhận cảnh báo. URL ping là secret: đặt trong `.env` (và `${FG_BACKUP_CONFIG_DIR}/env` cho job host), không dán vào chat hay commit. Tài khoản hiện do user đăng ký (Gmail cá nhân); D11 ghi tài khoản thuộc khách, chờ câu hỏi mở 2 của plan.md.
- **Check tuổi backup cho mọi thành phần** `orchestration/asset_checks/backup_freshness_checks.py`: gắn vào một `AssetSpec` ngoài `platform_backups` (không materialize); đọc `/app/var/backups/status/*.json` (thư mục đã mount vào `data_platform`, `docker-compose.yml:44`). Ngưỡng: `local` 26 giờ, `crm` 26 giờ (thay cho cảnh báo tuổi riêng của CRM nếu trùng; phase này kiểm và gộp), `metabase_cold` 26 giờ (user chọn chép hằng đêm), `offsite` 26 giờ, `check` 26 giờ, `drill_weekly` 8 ngày, `drill_monthly` 35 ngày. File thiếu hoặc `ok=false` → check đỏ → failure sensor sẵn có gửi Lark. Check đi vào `health_checks_asset_job` tự động vì job chọn mọi asset check trừ dbt (`orchestration/definitions.py`, định nghĩa `health_checks_asset_job`).

## Files

- Create: `scripts/backup/restore-drill.sh`, `scripts/backup/sidecar/drill_gates.py`, `scripts/backup/systemd/fg-restore-drill-{weekly,monthly}.{service,timer}.in`, `orchestration/asset_checks/backup_freshness_checks.py`, test `orchestration/asset_checks/__tests__/test_backup_freshness_checks.py` (hoặc thư mục test hiện có của asset_checks, theo quy ước), `scripts/tests/backup_integration/test_drills.py`.
- Modify: `orchestration/definitions.py` (đăng ký `AssetSpec` và check), `scripts/backup/install-units.sh`, `scripts/backup/backup.sh` và `scripts/backup/metabase_cold_backup.sh` (ping healthchecks khi biến `HC_PING_URL_*` có giá trị; không có thì bỏ qua), `orchestration/packs/crm/crm_sync.py` (ping sau `crm_restore_verify` pass), tài liệu ở khối đầu.

## Verification

- pytest `backup_freshness_checks`: đủ, quá hạn, thiếu file, `ok=false`, JSON hỏng → kết quả đúng; inventory Dagster (`scripts/checks/dagster_inventory.py`) chỉ khác ở asset spec + check mới.
- Tích hợp trên stack shadow với repo MinIO: T2 PASS; 4 kiểu tamper FAIL; T3 PASS trên lake dựng từ snapshot, tamper partition FAIL; prod fingerprint không đổi (kiểm trên stack shadow theo cùng cơ chế).
- Lark: chạy T2 với repo sai mật khẩu trên worktree → có tin Lark (gửi vào webhook test, không phải nhóm prod).
- Đo tài nguyên T2/T3 (RAM đỉnh, thời gian) ghi vào báo cáo; nếu T3 cần hơn 4 GiB thì nâng giới hạn có lý do.

**Đụng prod:** không (deploy cùng D2 ở phase 5). **Đổi số:** không.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Metabase tạm khởi động gửi email subscription | `--network none` + biến email tắt; kiểm trong test bằng log không có kết nối SMTP |
| T3 chạy lâu chồng lên giờ làm việc sáng Chủ nhật | Đo ở phase này; nếu > 2 giờ thì chuyển 04:00 thứ Bảy hoặc hạ phạm vi xuống chỉ các model public |
| Check tuổi đỏ hàng loạt ngay sau deploy vì chưa có file trạng thái | Check trả `WARN` "chưa có lần chạy" trong 48 giờ đầu sau khi bật (dựa vào thời điểm deploy ghi trong file cấu hình), sau đó mới `ERROR` |
| Khoá khách bị hỏi trong job tự động làm treo | Chỉ hỏi khi có `--customer-key` và có TTY; timer không bao giờ hỏi |

## Rollback

Disable hai timer drill; revert check bằng `git revert` (asset spec không materialize nên không để lại dữ liệu).
