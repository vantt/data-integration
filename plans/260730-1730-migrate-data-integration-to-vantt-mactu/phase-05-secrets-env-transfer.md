# Phase 5 — Secrets & env

**Scope**: `.env`, `.env.local`, `.env.docker` (3 file gốc, KHÔNG qua git — đều gitignored), `app_data/secrets/gsheets-service-account.json` (đã transfer ở phase 3, verify riêng ở đây).

**Đã xác nhận (2026-08-04)**: `CLOUDFLARE_API_TOKEN` trong `.env.docker` hiện tại ĐÃ rotate sau vụ rò rỉ audit C1 — an toàn để copy thẳng, không cần rotate lại trước.

## Bước

1. scp trực tiếp, KHÔNG qua `app_data/backups` (đúng nguyên nhân gây rò rỉ C1 — robocopy backup script copy `.env.docker` verbatim vào backup snapshot; ở đây ta scp thẳng máy-tới-máy, không tạo bản sao trung gian nào):
   ```bash
   scp .env .env.local .env.docker vantt-mactu:~/projects/fg-data-warhouse/
   ```
2. Verify secrets đã đúng trong `app_data/secrets/` (từ phase 3):
   ```bash
   ssh vantt-mactu "sha256sum ~/projects/fg-data-warhouse/app_data/secrets/gsheets-service-account.json"
   sha256sum app_data/secrets/gsheets-service-account.json
   ```
3. Sửa 1 giá trị cần đổi theo host mới — `DAGSTER_URL` trong `.env.docker` (dùng để build link trong Lark digest, phải trỏ đúng địa chỉ truy cập được từ thiết bị người dùng — Tailscale IP hoặc domain mới tuỳ phase 6):
   ```bash
   ssh vantt-mactu "grep DAGSTER_URL ~/projects/fg-data-warhouse/.env.docker"
   # sửa thủ công nếu domain/IP khác Windows
   ```
4. **KHÔNG** copy `.env.docker.example`/`.env.example` — đã có sẵn trong git clone (phase 2), không phải secret.

## Rollback
Xoá 3 file trên vantt-mactu, làm lại. File nguồn trên Windows không đổi.

## Acceptance
- 3 file `.env*` tồn tại trên vantt-mactu, đúng nội dung (diff nhanh vài dòng đầu để xác nhận không bị corrupt qua scp).
- `DAGSTER_URL` đã review, sửa nếu cần.
- `gsheets-service-account.json` checksum khớp.
