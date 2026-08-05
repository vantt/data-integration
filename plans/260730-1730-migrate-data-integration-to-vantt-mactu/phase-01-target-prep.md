# Phase 1 — Chuẩn bị đích trên vantt-mactu

**Mục tiêu**: tạo sẵn thư mục, network, chưa động vào checkout cũ.

## Bước

1. Tạo thư mục đích mới (KHÔNG dùng `~/projects/data-integration` — đó là checkout tháng 4, giữ nguyên làm tham khảo):
   ```bash
   ssh vantt-mactu "mkdir -p ~/data-integration/{app,app_data,.migrate-staging}"
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
Chỉ tạo thư mục rỗng + network — xoá `~/data-integration` nếu cần huỷ, không ảnh hưởng gì khác trên host (network `caddy_net` có thể để lại, không hại).

## Acceptance
- `~/data-integration/{app,app_data,.migrate-staging}` tồn tại, rỗng.
- `docker network ls` có `caddy_net`.
- Port 3000-3007/80/443 trống hoặc đã biết rõ cái gì đang chiếm (nếu không trống, DỪNG, báo user).
