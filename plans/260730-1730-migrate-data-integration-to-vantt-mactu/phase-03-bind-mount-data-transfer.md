# Phase 3 — Transfer data (bind-mount `app_data/*`)

**Scope**: `data_lake` (1.10G), `metabase_data` (0.73G), `input_source` (0.05G), `secrets` (~0), `analysis` (1.1M). **KHÔNG** gồm `backups`, `dagster_home` (orphaned), `metabase_data.backup.*`, `crm_data_safety`, `crm_verify_tmp`, `logs`, `rill` (theo quyết định đã chốt).

**Lesson áp dụng**: dừng writer trước khi copy (lesson #1) — `data_platform` là writer duy nhất ghi `data_lake`; `metabase` giữ H2 file mở khi chạy.

## Bước

1. Dừng service ghi vào các thư mục sắp copy (downtime ngắn, có kiểm soát):
   ```powershell
   docker compose stop data_platform metabase
   ```
2. Mirror qua ssh bằng tar (không có rsync trên Git Bash Windows — lesson #6). Mirror toàn bộ `app_data/` rồi exclude, KHÔNG liệt kê subdir thủ công (lesson #9 — tránh sót file như vụ `warehouse/` bị bỏ quên ở nu-data-pipeline):
   ```bash
   tar -C app_data \
     --exclude=backups \
     --exclude=dagster_home \
     --exclude='metabase_data.backup.*' \
     --exclude=crm_data_safety \
     --exclude=crm_verify_tmp \
     --exclude=logs \
     --exclude=rill \
     -cf - . | ssh vantt-mactu "tar -C ~/data-integration/app_data -xf -"
   ```
3. Verify file-count + byte-count TUYỆT ĐỐI, KHÔNG dùng BusyBox `du -sb` (lesson #7 — lệch do disk-block-usage). Dùng `find -printf` hai bên:
   ```bash
   # Windows (Git Bash)
   find app_data/data_lake app_data/metabase_data app_data/input_source app_data/secrets app_data/analysis -type f | wc -l
   find app_data/data_lake app_data/metabase_data app_data/input_source app_data/secrets app_data/analysis -type f -printf '%s\n' | paste -sd+ | bc
   ```
   ```bash
   # vantt-mactu
   ssh vantt-mactu "find ~/data-integration/app_data -type f | wc -l"
   ssh vantt-mactu "find ~/data-integration/app_data -type f -printf '%s\n' | paste -sd+ | bc"
   ```
   → hai cặp số phải khớp tuyệt đối.
4. Verify integrity từng file DuckDB/H2 quan trọng:
   ```bash
   ssh vantt-mactu "docker run --rm -v ~/data-integration/app_data/data_lake:/d python:3.11-slim bash -c 'pip install duckdb -q && python -c \"import duckdb; duckdb.connect(\\\"/d/sapo_warehouse.duckdb\\\", read_only=True).execute(\\\"PRAGMA database_list\\\").fetchall()\"'"
   ```
   (hoặc đơn giản hơn: sha256sum các file `.duckdb` chính hai bên, so khớp — DuckDB/H2 không hỗ trợ `PRAGMA integrity_check` như SQLite, dùng checksum thay thế vì file không bị ghi trong lúc copy do đã dừng service ở bước 1.)
   ```bash
   sha256sum app_data/data_lake/sapo_warehouse.duckdb app_data/data_lake/serving/olap.duckdb app_data/metabase_data/metabase.db.mv.db
   ssh vantt-mactu "sha256sum ~/data-integration/app_data/data_lake/sapo_warehouse.duckdb ~/data-integration/app_data/data_lake/serving/olap.duckdb ~/data-integration/app_data/metabase_data/metabase.db.mv.db"
   ```
5. Khởi động lại service trên Windows (chưa cutover, Windows vẫn là nguồn sống chính cho tới khi phase 7 verify xong):
   ```powershell
   docker compose start data_platform metabase
   ```

## Rollback
Windows không đổi gì (chỉ dừng/start lại). Trên vantt-mactu, xoá `~/data-integration/app_data/*` và làm lại nếu checksum lệch.

## Acceptance
- File-count khớp tuyệt đối.
- Byte-count khớp tuyệt đối.
- sha256 khớp 100% cho 3 file DB chính.
- Windows service đã start lại, không có downtime kéo dài (~1-3 phút).
