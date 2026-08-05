# Phase 1 — Chuẩn bị đích trên vantt-mactu

**Mục tiêu**: tạo sẵn thư mục, network tại `~/projects/fg-data-warhouse` (path chốt 2026-08-05 — path MỚI, không đụng checkout cũ `~/projects/data-integration`, tháng 4/2026, giữ nguyên làm tham khảo).

**Layout đích (flat, KHÔNG tách `app/` riêng)**: `docker-compose.yml` dùng path tương đối hardcode (`./app_data/...`, không có `DATA_ROOT` env var như nu-data-pipeline) → git repo phải clone THẲNG vào `~/projects/fg-data-warhouse/` (repo root = nơi chạy `docker compose`), `app_data/` là subdirectory THƯỜNG bên trong đó — không phải sibling của 1 thư mục `app/` riêng. Thư mục staging tạm để ở NGOÀI repo (`~/migrate-staging/`) để không dính build context.

## Bước

1. Tạo thư mục đích + staging (tách riêng, ngoài repo):
   ```bash
   ssh vantt-mactu "mkdir -p ~/projects/fg-data-warhouse ~/migrate-staging"
   ```
2. Tạo `caddy_net` external network (cả `data-integration/docker-compose.yml` lẫn `caddy-global/docker-compose.yml` đều cần network này tồn tại trước):
   ```bash
   ssh vantt-mactu "docker network inspect caddy_net >/dev/null 2>&1 || docker network create caddy_net"
   ```
3. Xác nhận lại port 3000-3007, 80, 443 vẫn trống (đã check 2026-07-30, re-verify vì có thể đổi):
   ```bash
   ssh vantt-mactu "ss -tln | grep -E ':(3000|3001|3002|3003|3004|3005|3006|3007|80|443)\b' || echo 'all clear'"
   ```
4. Xác nhận đĩa trống đủ (~12.2G cần, kỳ vọng còn dư nhiều sau quyết định bỏ backups/orphaned dagster_home):
   ```bash
   ssh vantt-mactu "df -h /"
   ```

## Rollback
Chỉ tạo thư mục rỗng + network — xoá `~/projects/fg-data-warhouse` nếu cần huỷ, không ảnh hưởng gì khác trên host (network `caddy_net` có thể để lại, không hại).

## Acceptance
- `~/projects/fg-data-warhouse/` và `~/migrate-staging/` tồn tại, rỗng.
- `docker network ls` có `caddy_net`.
- Port 3000-3007/80/443 trống hoặc đã biết rõ cái gì đang chiếm (nếu không trống, DỪNG, báo user).
