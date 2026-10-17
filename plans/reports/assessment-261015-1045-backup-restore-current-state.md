# Đánh giá hiện trạng backup / khôi phục / tái dựng (15/10/2026)

> Agent Explore khảo sát chỉ đọc (không mở file dữ liệu khách, không đọc secret); controller ghi ra file. Dẫn chứng file:dòng theo checkout prod ngày 15/10.

## Kết luận

Dữ liệu warehouse, trạng thái Dagster và Metabase đều có backup hằng ngày/hằng tuần, CRM có snapshot kèm diễn tập khôi phục tự động. Nhưng **mọi bản sao nằm cùng một ổ** (`/dev/nvme0n1p2`), **không có bản ngoài máy, không mã hoá, không có secret**, và **chưa có lần khôi phục thử nào** cho warehouse, Metabase H2 hay Dagster. Timer chép nguội Metabase chưa tự chạy lần nào (lần đầu: CN 18/10 00:30).

## 1. Thành phần có trạng thái

| Thành phần | Nơi lưu | Backup | Cách | Nhất quán | Lịch / giữ |
|---|---|---|---|---|---|
| Data lake (DuckDB `sapo_warehouse.duckdb` + WAL, parquet raw, serving, export, monitoring, gsheet_raw, crm_export) | bind `app_data/data_lake` (docker-compose.yml:37) | Có | `cp -a` nóng trong container (`backup.sh:158-166`) | Chép nóng file DuckDB + WAL, chỉ dựa vào khoá Dagster `duckdb_lock` (`orchestration/ops/system_backup.py:79-82`); **chưa xác minh mọi writer (dlt) có giữ khoá** | Hằng ngày ~01:04; giữ 7 |
| `dagster_home` | named volume | Có (bỏ run history) | Chép nóng + `prune_dagster_history` | SQLite chép nóng, không dùng backup API | Hằng ngày |
| `input_source` (50 MB) | bind | Có | `cp -a` | File | Hằng ngày |
| Cấu hình (compose, Dockerfile) | git | Có (bản phụ) | `cp` | — | Hằng ngày |
| Metabase nội dung | API | Có, JSON | `metabase_export.py`; lỗi chỉ cảnh báo | Không đủ để khôi phục toàn bộ (không id, mật khẩu, settings) | Hằng ngày (43/888/23) |
| Metabase H2 (~48 MB sau nén) | bind | Có | Chép nguội: dừng → `cp` → khởi động → `/api/health` (`metabase_cold_backup.sh:49-63`) | Đúng nghĩa | Timer user CN 00:30; giữ 7 mỗi loại (weekly, pre-deploy) |
| CRM (`crm.db`, `hug.db`, `cache.db`) | named volume `crm_data` | Có | `crm/ops/backup_crm.py`: checkpoint WAL → `Connection.backup()` → so số dòng + checksum → manifest | Nhất quán, có kiểm | `crm_backup_job` 02:00; volume `crm_backups`; giữ 7 |
| Diễn tập khôi phục CRM | sidecar `crm_drill_runner` | Tự động | `restore_verify_crm.py` (gate A file/manifest, gate B boot CRM tạm) | — | Sau mỗi backup CRM; **chưa xác minh được lần PASS gần nhất** |

`monitoring_db` là named volume mount đè lên `data_lake/monitoring`: chưa xác minh có nằm trong bản backup.

## 2. Không được backup

- **Secret:** `app_data/secrets` (GCP service account) bị xoá khỏi bản backup (`backup.sh:145-147`); `.env` / `.env.docker` không mount vào container nên không chép; `ingestion/.dlt/secrets.toml`, `transformation/profiles.yml` chỉ ở máy hiện tại.
- Caddy (certs, thuộc stack Caddy toàn cục), Rill state, bản build Evidence (dựng lại được), `app_data/analysis`, volume `agent_codex_config`, `hug_push_state.db` của CRM.
- Lịch sử Google Sheet (chỉ có ảnh chụp `gsheet_raw` trong lake).
- Chưa kiểm: seed dbt do job ghi có cần backup riêng không.

## 3. Quy trình khôi phục

| Quy trình | Có tài liệu/script | Đã thử |
|---|---|---|
| CRM | Có (`crm/docs/backup-restore-runbook.md:54-68`, diễn tập tự động) | Có cơ chế; chưa xác minh lần PASS gần nhất |
| Metabase H2 | Có (`deployment.md:779-789`) | **Chưa** (log chỉ có lần chép) |
| Metabase từ JSON | Không có script | Không |
| data_lake / dagster_home trên Linux | **Không có script** (chỉ `restore.ps1` bản Windows cũ) | Không |
| Dựng shadow từ backup (`prepare-shadow.sh`) | Có | Có chạy thật: chứng minh dữ liệu backup đọc và dùng được, nhưng không phải khôi phục prod |
| DR warehouse (dựng lại từ raw) | Chỉ stub: `plans/260624-2010-warehouse-pipeline-dr-verified-restore` (pending) | Không |
| Runbook tổng `docs/operations/operations.md:296-321` | **Lỗi thời** (đường dẫn sai) | — |

## 4. Điểm chết đơn lẻ

- Cùng một ổ: mất ổ/máy là mất cả dữ liệu lẫn backup (ổ 457 GB, dùng 255 GB).
- Không ngoài máy, không mã hoá (backup có PII khách, token HUG, user Metabase).
- Giữ 7 bản: lỗi âm thầm phát hiện sau 7 ngày thì hết bản tốt.
- Backup đêm chạy trong container `data_platform`: container hỏng thì không backup.
- Đường dẫn cứng `/home/vantt/...` trong systemd unit và script; thư mục backup thuộc `root` (cần sudo khi khôi phục).
- Chỉ CRM có cảnh báo tuổi backup; backup warehouse không có cảnh báo.

## 5. Kích thước

| Mục | Dung lượng |
|---|---|
| Một bản backup đêm | ~2,0 GB (data_lake 1,4 GB, dagster_home 574 MB, input 50 MB, metabase_export 11 MB) |
| 7 bản đêm | ~14 GB |
| Một bản chép nguội Metabase | ~48 MB |
| Named volume CRM, dagster, monitoring | Chưa đo (cần quyền root hoặc `docker run --rm -v <vol>:/b:ro alpine du -sh /b`) |

Ước tính ngoài máy tối thiểu: bản đêm mới nhất (~2 GB) + Metabase (~48 MB) + CRM; giữ như hiện tại ~15 GB + CRM.

## 6. Khoảng trống cho runbook "dựng lại từ con số 0"

1. Secret không có trong backup → cần bản mã hoá (đã chốt) hoặc trình quản lý mật khẩu.
2. Đường dẫn cứng phải tham số hoá.
3. Named volume (`crm_backups` nằm cùng ổ với `crm_data`) cần đẩy ngoài máy.
4. Chưa có `restore.sh` cho Linux (data_lake, dagster_home, Metabase).
5. Chưa có/chưa thử quy trình dựng lại warehouse từ raw.
6. Image build cần mạng; nên ghim/đẩy image (Đợt 2).
7. Caddy dựng riêng.
8. Khôi phục Metabase chưa có bước kiểm (so số với manifest export).
9. Dagster: kiểm lại lịch chạy sau khôi phục.
10. Sửa `operations.md` lỗi thời.

## Câu hỏi còn mở

- Lần diễn tập CRM gần nhất có PASS không?
- `monitoring_db` có trong bản backup không?
- Có writer dlt nào không giữ `duckdb_lock` (rủi ro bản chép DuckDB không nhất quán)?
- Dung lượng các named volume CRM/dagster.
