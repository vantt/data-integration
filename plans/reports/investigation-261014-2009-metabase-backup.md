# Metabase backup: hiện trạng và đề xuất (14/10/2026)

## Kết luận

**Hiện không có cơ chế nào sao lưu Metabase.** File `app_data/metabase_data/metabase.db.mv.db`
(H2, 263 MB, ghi lần cuối 14/10 20:09) chứa 43 dashboard, 888 card, 23 collection (Metabase
v0.62.3, đếm qua API). Nếu file này hỏng hoặc mất, toàn bộ dashboard và câu hỏi mất theo; chỉ một
phần có bản "as code" trong `docs/analytics-handbook/blueprints/metabase/` (45 file).

## Bằng chứng (chỉ đọc)

- **`scripts/backup/backup.sh`** chạy trong container `data_platform` (job
  `maintain_backup_platform_job`, khoảng 01:04 hằng ngày). Trong container không có
  `/app/app_data`, nên script đi nhánh "Docker volume layout" và chỉ chép `data_lake`,
  `dagster_home`, `input_source`. Container `data_platform` không mount `metabase_data`.
- **Bản backup 14/10** (`app_data/backups/20261014-010406/`): `app_data/` chỉ có ba thư mục trên;
  `config/` có `Dockerfile.dataplatform`, `Dockerfile.metabase`, `docker-compose.yml`. Không có
  dữ liệu Metabase.
- **Host:** user `vantt` không có crontab; `/etc/cron.d` chỉ có `anacron`, `e2scrub_all`; không
  có systemd timer (hệ thống hay user) nào liên quan Metabase hay backup.
- **Không có bản sao H2 nào khác** trên đĩa (tìm `metabase*.mv.db*`, `*metabase*backup*`).
- **Tài liệu lệch thực tế:** `scripts/backup/README.md` liệt kê Metabase là "Critical" và mô tả
  quy trình dừng container trước khi backup; đó là biến thể PowerShell/Windows cũ, không phải
  script đang chạy trên prod. Comment đầu `backup.sh` cũng nói "Metabase H2 DB may have minor
  inconsistency", ngụ ý có chép Metabase, nhưng thực tế không chép.
- **Rủi ro phụ:** mọi bản backup nằm cùng ổ đĩa với dữ liệu gốc (`app_data/backups/`, ổ
  `/dev/nvme0n1p2`, còn trống 185 GB). Hỏng ổ thì mất cả hai.

## Đề xuất (chưa áp dụng lên prod)

Hai lớp, vì mỗi lớp che một kiểu hỏng khác nhau.

### 1. Export qua API hằng đêm (không downtime)

Script `scripts/backup/metabase_export.py`, gọi từ `backup.sh` (bước mới, lỗi ở bước này chỉ
cảnh báo, không làm hỏng phần backup dữ liệu). `data_platform` và `metabase` cùng mạng
`caddy_net`, nên gọi được `http://metabase:3000` bằng `METABASE_API_KEY` (đã có trong
`.env.docker`). Ghi vào `<BACKUP_DIR>/metabase_export/`:

- `collections.json`, `cards/<id>.json` (`GET /api/card/:id`, đủ SQL và cấu hình hiển thị),
  `dashboards/<id>.json` (`GET /api/dashboard/:id`, đủ dashcard, filter, layout);
- bỏ card/dashboard đã archive; ghi `manifest.json` (thời điểm, version, số lượng).

Lớp này giữ được nội dung khi file H2 hỏng âm thầm, và so sánh được giữa các đêm. Nó **không**
phải bản khôi phục đầy đủ (không có user, quyền, cài đặt, lịch sử; id đổi khi tạo lại).
Metabase serialization (`export`) là tính năng bản trả phí, nên dùng API thường.

### 2. Bản chép H2 nguội trong cửa sổ bảo trì (bản khôi phục thật)

Chép `metabase.db.mv.db` khi Metabase đã dừng thì file nhất quán. `data_platform` không có Docker
socket và không mount `metabase_data`, nên việc này chạy trên host: script
`scripts/backup/metabase_cold_backup.sh` + systemd timer (hoặc cron) của user `vantt`:

```bash
docker compose stop metabase            # ~10 giây
cp -a app_data/metabase_data/metabase.db.mv.db app_data/backups/metabase/<ngày>.mv.db
docker compose start metabase           # Metabase khởi động lại ~1–2 phút
# giữ 7 bản gần nhất; kiểm tra /api/health trả 200 sau khi start
```

Đề xuất chạy **hằng tuần**, Chủ nhật khoảng 00:30 (ngoài 02:30–04:00 của nightly, trước backup
01:04). Mỗi lần Metabase không truy cập được khoảng 1–2 phút. Nếu anh muốn hằng đêm thì cùng
giờ đó.

### 3. Tài liệu

Thêm mục "Metabase" vào `docs/operations/deployment.md`: dữ liệu nằm đâu, hai lớp backup, lịch
chạy, cách khôi phục (dừng Metabase, chép đè file `.mv.db`, start, kiểm `/api/health`, mở một
dashboard), và cách dùng bản export JSON khi chỉ mất vài dashboard. Sửa `scripts/backup/README.md`
và comment đầu `backup.sh` cho khớp thực tế.

### Ngoài phạm vi, ghi lại để anh cân nhắc

- Chuyển DB ứng dụng của Metabase từ H2 sang Postgres: Metabase không khuyến nghị H2 cho prod;
  Postgres cho phép `pg_dump` lúc đang chạy, bỏ được cửa sổ dừng.
- Chép backup ra ngoài máy (ổ khác, NAS, cloud).

## Câu hỏi cho anh

1. Bản chép H2 nguội: hằng tuần (Chủ nhật 00:30) hay hằng đêm?
2. Cho phép thêm một systemd timer/cron của user `vantt` trên host không (hiện host chưa có job
   nào của dự án)?
3. Làm bản export API trước (không downtime, deploy như code bình thường), còn bản chép nguội chờ
   anh chọn giờ, được không?
