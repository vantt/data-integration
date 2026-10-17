# Deploy 14/10/2026 21:58: backup Metabase

## Kết quả

`main` fast-forward `c2915881` → `82368d21` (nhánh `chore/metabase-backup`) theo runbook:
không có run nào đang chạy; dừng `data_platform` 21:58:05 (sau tick realtime 21:57), merge,
start 21:58:15. Sau deploy: healthy, instigator 26/26 không đổi, run realtime đầu tiên SUCCESS,
log không lỗi. Cài timer systemd của user `vantt`.

Trước đó (xem `investigation-261014-2009-metabase-backup.md`) không có cơ chế nào sao lưu
Metabase.

## Hai lớp backup

| Lớp | Cơ chế | Lịch | Kiểm chứng |
|---|---|---|---|
| Export qua API | `scripts/backup/metabase_export.py`, bước 2b của `backup.sh` (trong `data_platform`); lỗi chỉ là cảnh báo | Mỗi đêm, cùng job backup ~01:04 | Chạy thử trong container: 43 dashboard, 888 card, 23 collection, 5 user, nhóm quyền, permission graph, collection graph, 0 subscription; 938 file JSON đều đọc được; 11 MB; API key không có trong file nào. `backup.sh` chạy trọn với dữ liệu giả: export OK, rc 0; khi bỏ API key: chỉ cảnh báo, rc 0 |
| Chép H2 nguội | `scripts/backup/metabase_cold_backup.sh weekly\|pre-deploy` trên host: stop metabase, chép `.mv.db`, start, chờ `/api/health`, giữ 7 bản mỗi loại | Timer `metabase-cold-backup.timer` Chủ nhật 00:30 (lần đầu 18/10); bằng tay trước deploy ghi vào Metabase | Chạy 2 lần (22:04 bằng tay, 22:11 qua systemd): mỗi lần Metabase gián đoạn 18 giây, health OK. Khôi phục thử bản sao vào một Metabase tạm (mạng internal, không cổng): healthy, 43/888/23 khớp prod |

Ghi chú: khi Metabase tắt sạch, H2 tự nén file. `metabase.db.mv.db` giảm từ 263 MB xuống
~50 MB, nội dung không đổi (đếm qua API trước/sau và trên bản khôi phục đều 43/888/23).

Bản sao hiện có: `app_data/backups/metabase/metabase-pre-deploy-20261014-220401.mv.db`,
`metabase-weekly-20261014-221050.mv.db`; log `app_data/backups/metabase/cold-backup.log`.

## Tài liệu

- `docs/operations/deployment.md` §8 "Metabase: backup and restore": hai lớp, chép trước deploy,
  kiểm tra, khôi phục.
- `scripts/backup/README.md` viết lại theo prod Linux (bảng cái gì được backup, cài timer);
  script PowerShell ghi là bản Windows cũ. Sửa: `.env.docker` không được `backup.sh` chép (không
  mount vào container), trước đây README ghi là có.
- Comment đầu `backup.sh` ghi đúng: không chép Metabase, chỉ export API.

## Việc tiếp

- Kiểm log lần chạy timer đầu tiên Chủ nhật 18/10 00:30 và bản export trong backup 15/10 01:04.
- Chưa làm (user quyết, plan riêng): chép backup ra ngoài máy; chuyển DB Metabase sang Postgres.
- Phase 6 (`95e6d1d7`) phải rebase lên `main` hiện tại (`82368d21`) trước khi deploy.
