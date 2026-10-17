# Deploy phase 1 (chụp cục bộ nhất quán) — 15/10/2026 17:49

## Kết quả

Phase 1 đã lên prod và chạy xanh; user duyệt deploy ngay (15/10 ~17:40). `main` fast-forward
`69e021f4` → `4e330772` (nhánh `feat/backup-offsite-dr`: `292a596d` ADR 019 + khung tài liệu,
`4dd4ba6d` chụp nhất quán, `4e330772` thẻ Lark theo trạng thái) theo runbook: stop `data_platform`
17:49:05, merge, start 17:49:15 (không đổi `docker-compose.yml`). Rollback point `69e021f4`; các bước
hoàn tác ở `reports/phase-01-worker-report.md` mục Rollback.

## Trước deploy

- Gate M (baseline `69e021f4`, build cùng ngày): mọi bước xanh (golden 83/83 0 khác biệt, cả rolling
  trống; dbt inventory; compiled SQL; boundaries; pytest; lõi trần), trừ Dagster inventory: một khác
  biệt duy nhất `crm_backup_schedule` timezone `None` → `Asia/Ho_Chi_Minh`, đúng thay đổi user đã
  duyệt; coordinator chấp nhận (`dagster_inventory.py` không có cờ cho thay đổi schedule).
- `run-all.sh` PASS (440 test sau khi thêm test thẻ Lark).

## Sau deploy

- Healthy; instigator 26/26 `diff` 0; log không lỗi.
- `crm_backup_schedule`: `0 2 * * *`, `executionTimezone = Asia/Ho_Chi_Minh`, tick kế 16/10 02:00 +07
  (trước đây chạy 09:00 giờ VN vì thiếu timezone).
- Timer Metabase cài lại bằng `scripts/backup/install-units.sh` (`ExecStart=…/metabase_cold_backup.sh
  nightly`). Lúc `enable --now` timer kích hoạt ngay một lần — đúng ý user muốn chép ngay: 17:49:33
  dừng Metabase, chép `metabase-nightly-20261015-174933.mv.db` (48 MB), healthy lại sau 19 giây, export
  API 43 dashboard / 888 card / 23 collection; `status/metabase_cold.json` `state=ok`, `export=ok`.
  Lần kế: 16/10 00:30.
- Backup thử (`maintain_backup_platform_job` run `c907c902`, 17:51): `status/local.json` `state=ok`,
  15 giây, 20 thành phần ok (gồm `monitoring` và `dagster_home` qua SQLite backup API,
  `exports_warehouse` = `monitor_taxonomy_parity_log`, `metabase_export`); `backup_manifest.py verify`
  OK; 1,8 GB.
- Quyền file secret (runbook `docs/operations/backup-and-recovery.md` "Quyền file secret trên host"),
  quyền cũ ghi lại trong scratchpad của session:
  - `app_data/secrets/gsheets-service-account.json`: `0644` → `0600` (coordinator, 17:5x);
    `data_platform` chạy root vẫn đọc được (kiểm bằng đọc JSON trong container).
  - Credentials tunnel (`<tunnel-id>.json`, `cert.pem`, `config.yml`): **đã áp** bởi user (~18:05, cần
    `sudo`): `65532:65532`, `0400`; `cloudflared` restart; log có `Registered tunnel connection`;
    `bi.fwg.vn/api/health` và `crm.fwg.vn` trả 302 (Cloudflare Access) → tunnel đã nối lại.

## Theo dõi sáng 16/10

- `status/metabase_cold.json` của lần 00:30: `state=ok`, `export=ok`, số lượng ≈ 43/888/23.
- `status/local.json` của backup 01:04: `state=ok`; thẻ Lark xanh.
- `crm_backup_job` chạy ~02:00 giờ VN, `crm_restore_verify` pass.
- Nightly 03:00 xanh.

## Kết quả sáng 16/10 (kiểm 09:23, chỉ đọc): tất cả đạt

- Chép nguội Metabase 00:30 (timer): `metabase-nightly-20261016-003031.mv.db`, Metabase healthy lại sau
  17 giây, export 43 dashboard / 888 card / 23 collection; `status/metabase_cold.json` `state=ok`,
  `export=ok`, 23 giây.
- Backup 01:07 `20261016-010722`: `status/local.json` `state=ok`, 14 giây, không lỗi;
  `backup_manifest.py verify` OK.
- `crm_backup_job` `30660890` chạy **02:00 giờ VN** (lần đầu theo giờ mới; lần trước 15/10 09:00):
  SUCCESS.
- Nightly 03:01 `3af400cf-2333-46db-a2f6-580655158eb8`: SUCCESS, 59/59 step, 567 check, 0 đỏ mới so
  với `24b759ee`; 5,3 phút.
- Lỗi duy nhất từ 15/10 18:52: `budget_sheet_sync_job` 02:30 (đã biết: sheet BUDGET_ITEMS dùng mã TK
  cha 112/334).
