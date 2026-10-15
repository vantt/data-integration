# ADR-019: Backup ngoài máy, khôi phục và dựng lại hệ thống

> **Trạng thái:** Proposed
> **Ngày:** 2026-10-15
> **Tham chiếu:** [`docs/operations/backup-and-recovery.md`](../operations/backup-and-recovery.md), [`docs/operations/backup-restore-completeness-runbook.md`](../operations/backup-restore-completeness-runbook.md), [`docs/operations/deployment.md` mục "Metabase: backup and restore"](../operations/deployment.md#metabase-backup-and-restore), [`scripts/backup/README.md`](../../scripts/backup/README.md), [`crm/docs/backup-restore-runbook.md`](../../crm/docs/backup-restore-runbook.md), plan `261015-1140-backup-restore-dr` (thiết kế và bằng chứng phase 0)

## Bối cảnh

Đến 15/10/2026, mọi bản backup nằm cùng ổ với dữ liệu gốc (`app_data/backups/`), không mã hoá, không có secret, và chưa từng khôi phục thử warehouse, Metabase H2 hay Dagster. Chỉ CRM có chuỗi gate đã chứng minh: chụp SQLite nhất quán, so manifest, rồi boot thử bản khôi phục mỗi ngày (`crm_backup_job`). Hỏng ổ hoặc mất máy thì mất cả dữ liệu lẫn backup.

Kiểm tra chỉ đọc trên prod (phase 0 của plan) cho thấy thêm:

- `ingestion_health.db` (lịch sử vận hành 90 ngày) là SQLite WAL và đang được chép nóng bằng `cp -a`, giống `dagster_home`.
- Chỉ một bảng trong warehouse không dựng lại được từ raw: `monitor_taxonomy_parity_log`, append-only. Các bảng "snapshot" giá và tồn kho thực ra không giữ lịch sử, vì GC rolling chỉ giữ 3 lần build.
- dlt ghi parquet thẳng vào tên cuối, không qua file tạm, và ghi state sau dữ liệu.
- Credentials Cloudflare tunnel và `app_data/analysis` không nằm trong bất kỳ backup nào.

Fine Japan là khách đầu tiên; công cụ phải dùng lại được cho khách sau, và khách tự giữ dữ liệu của mình.

## Quyết định

| # | Quyết định |
|---|---|
| D1 | **restic + rclone**, một bộ script cho mọi đích. Đổi đích chỉ bằng `RESTIC_REPOSITORY` và remote rclone (thư mục local, S3, SFTP, Google Drive) |
| D2 | **Parquet-first:** off-site chỉ chứa nguồn sự thật. DuckDB phái sinh (`sapo_warehouse.duckdb`, `serving/`, `export/`, bản standalone) dựng lại bằng dbt. Ngoại lệ là bảng phái sinh nhưng không dựng lại được: xuất ra parquet rồi lên off-site. Hôm nay chỉ có `main.monitor_taxonomy_parity_log` |
| D3 | Đích mặc định cho khách dùng Gmail: Google Drive qua OAuth, app do FG publish, scope `drive.file`. Fine Japan (có Workspace) dùng service account + Shared Drive |
| D4 | Khách có dữ liệu nhạy cảm hoặc từ 100.000 chủ thể dữ liệu trở lên: đích S3 trong nước hoặc NAS, không dùng Google Drive |
| D5 | **Khách sở hữu repo và giữ khoá.** FG không giữ khoá, không vận hành backup thay khách. Bàn giao có biên bản và một lần khôi phục thử trước mặt khách, mở repo bằng khoá của khách |
| D6 | Secret (`.env`, `.env.docker`, `app_data/secrets/`, credentials Cloudflare tunnel) **chỉ** nằm trong repo restic đã mã hoá, không bao giờ có bản rõ ngoài máy hay trong backup cục bộ. `.env.local` (file dev cũ) không đưa lên. File secret trên host để quyền 0600 (hoặc chỉ đọc cho đúng uid của container dùng nó) |
| D7 | Điều phối bằng **systemd timer trên host**, gọi `docker compose --profile ops run --rm backup <lệnh>`. Sidecar `backup` không có Docker socket |
| D8 | Mỗi thành phần có trạng thái được **chụp nhất quán ở nơi sở hữu nó**, ghi vào staging kèm `manifest.json`: SQLite (`schedules.db`, `ingestion_health.db`, CRM) qua backup API; bảng DuckDB qua `COPY` trong op giữ `duckdb_lock`; H2 chép nguội. Sidecar chỉ đọc bản đã chụp, trừ raw parquet (đọc thẳng) |
| D9 | Khôi phục luôn đi hai bước: giải nén vào thư mục scratch, kiểm manifest (`verify`), rồi mới áp vào prod theo từng thành phần, có bản an toàn trước khi ghi đè |
| D10 | **Cài mới và dựng lại dùng chung một công cụ:** cài mới là "khôi phục từ snapshot rỗng" |
| D11 | Cảnh báo hai kênh độc lập: Lark (lỗi chủ động) và dead-man healthchecks.io (bắt cả trường hợp máy chết, job không chạy) |
| D12 | **Không lưu image Docker** lên off-site. Khôi phục build lại image từ git ở đúng sha của snapshot; ghim base image theo digest và ghim phiên bản dependency đang chạy |

Lịch (Asia/Ho_Chi_Minh):

| Giờ | Việc |
|---|---|
| Hằng đêm 00:30 | Chép nguội Metabase H2 |
| ~01:04 | Backup cục bộ |
| 02:00 | CRM backup và diễn tập CRM |
| 03:30 | Off-site + `forget` + `check --read-data-subset n/28` |
| CN 05:15 | Diễn tập khôi phục từ bản ngoài máy (T2) |
| CN đầu tháng 06:00 | Dựng lại bằng dbt (T3) |

Lịch được chọn sau khi đo: nightly kết thúc p95 khoảng 03:14 (đo trên 77 đêm), và trong giờ 3 không có writer parquet thường.

## Phương án đã loại

| Phương án | Lý do loại |
|---|---|
| Dịch vụ backup có quản lý do FG vận hành, FG giữ khoá | User loại; trách nhiệm dữ liệu và khoá thuộc khách (D5) |
| Đưa `sapo_warehouse.duckdb` lên off-site | Dựng lại được bằng dbt. File bị ghi lại cả file mỗi đêm nên dedup kém. Chỉ một bảng không dựng lại được, đã xuất riêng |
| Lưu image bằng `docker save` (đề xuất ban đầu của D12) | Image dự án khoảng 13,5 GB chưa nén, ước 5–7 GB nén. User chọn build lại từ git và ghim phiên bản |
| Sidecar có Docker socket để tự dừng/chụp service | Mở rộng bề mặt tấn công; giữ giới hạn socket chỉ ở `crm_drill_runner` |
| Chạy backup trong Dagster | Backup phải chạy được cả khi Dagster hỏng |
| `--exclude` file tạm của dlt khi đọc raw | dlt không dùng file tạm. File chụp dở được bắt bằng cách đọc mọi file parquet và mở mọi bảng Delta khi diễn tập |
| Lùi cursor dlt 48 giờ sau khôi phục | Chưa có cơ chế. State dlt ghi sau dữ liệu nên chạy tiếp từ cursor trong snapshot là đủ; chỉ thêm cơ chế lùi nếu diễn tập cho thấy thiếu dữ liệu |
| Đích phụ append-only (Object Lock) chống ransomware | Để tuỳ chọn sau |

## Hệ quả

- Mất máy thì dựng lại được trên máy Linux mới từ Recovery Sheet. Mục tiêu RPO 24 giờ, RTO 8 giờ làm việc; đo thật ở diễn tập Fine Japan.
- Bản ngoài máy được chứng minh khôi phục được mỗi tuần (T2) và dựng lại được mỗi tháng (T3), có phép thử phá dữ liệu.
- Diễn tập phải cô lập (`--mode drill`, `--network none`). Lý do là nhiều đường gây tác dụng ra ngoài:
  - ack webhook Sapo/HUG xoá hàng đợi trên Worker;
  - budget sync ghi vào Google Sheet;
  - `caddy-global` ghi DNS;
  - Cloudflare tunnel nhận traffic thật.
- Lịch sử run và event log của Dagster (`history/`) không được backup. Sau khôi phục, UI mất "last materialized" cho tới lần chạy kế.
- Sự kiện webhook HUG đã ack sau thời điểm snapshot thì không lấy lại được (tối đa khoảng RPO).
- Không lưu image nên dựng lại phụ thuộc vào việc build lại thành công. Rủi ro còn lại cho tới khi Đợt 2 ghim toàn bộ dependency và đưa image lên registry.
- `crm_backup_schedule` được thêm `execution_timezone` để chạy đúng 02:00 giờ VN (trước đó chạy 09:00 vì lịch tính theo UTC).

## Khi nào xem xét lại

- Khi Đợt 2 đưa image lên GHCR và ghim dependency: bỏ bước build lại khi khôi phục, kéo image theo digest.
- Khi plan sửa lịch sử giá/tồn kho xong: thêm dữ liệu tích luỹ của nó vào danh sách xuất (D2).
- Khi chuyển Metabase sang Postgres: thay chép nguội H2 bằng `pg_dump` lúc đang chạy.
- Khi có khách có yêu cầu pháp lý về nơi lưu dữ liệu: xem lại D3/D4 khi có ý kiến luật sư.
- Khi có từ ba khách trở lên: giám sát tập trung dựa trên `status/*.json` (Đợt 8).
- ADR chuyển sang Accepted ở cuối plan, kèm RTO đo được, kích thước repo và thời gian build lại image.
