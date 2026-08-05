# Phase 6 — Caddy global reverse-proxy + DNS-01 cert

**Status (cập nhật 2026-08-04): DEFERRED — chạy SAU phase 8, KHÔNG phải prerequisite.** User đã hạ ưu tiên `*.lan.fwg.vn`, chỉ cần `bi.fwg.vn`/`crm.fwg.vn` hoạt động trước (2 domain đó đi qua Cloudflare Tunnel ở phase 8, không phụ thuộc Caddy). Phase 7 (verify) giờ dùng port trực tiếp qua Tailscale IP thay vì domain Caddy — xem `phase-07-verify-non-crm-services.md`.

**Khi nào làm phase này**: sau khi phase 8 xong và ổn định, nếu vẫn muốn có domain đẹp/basic_auth cho các service nội bộ (`etl.lan.fwg.vn`, `rill.lan.fwg.vn`, ...). Không phải điều kiện chặn migrate.

**Phụ thuộc**: `caddy_net` network đã tạo ở phase 1. `CLOUDFLARE_API_TOKEN` đã có trong `.env.docker` (phase 5, đã rotate, an toàn).

## Bước

1. `caddy-global/` đã transfer cùng code ở phase 2 (nằm trong repo). Verify:
   ```bash
   ssh vantt-mactu "ls ~/projects/fg-data-warhouse/caddy-global/"
   ```
2. Deploy caddy-global (stack chính `data-integration` đã chạy từ phase 7, labels caddy-docker-proxy sẽ được Caddy tự pick up ngay khi container này lên):
   ```bash
   ssh vantt-mactu "cd ~/projects/fg-data-warhouse/caddy-global && docker compose --env-file ../.env.docker up -d --build"
   ```
3. Verify Caddy container healthy, đọc được docker socket:
   ```bash
   ssh vantt-mactu "docker logs caddy-global --tail 30"
   ```
4. **DNS**: xác nhận `*.lan.fwg.vn` trỏ được tới vantt-mactu — cần user xác nhận cách DNS đang resolve (Tailscale IP `100.94.42.82` hay LAN IP `192.168.20.49`), chưa recon được từ repo.
5. Verify cert issuance qua DNS-01:
   ```bash
   ssh vantt-mactu "docker logs caddy-global 2>&1 | grep -i -E 'certificate obtained|error'"
   ```

## Rủi ro cần lưu ý
- Let's Encrypt / ACME rate limit theo domain — nếu Windows Caddy vẫn còn chạy trỏ cùng domain lúc làm phase này, tránh 2 bên cùng cấp cert 1 tên miền. Vì Windows sẽ bị wipe theo phase 9, khả năng cao lúc làm phase 6 Windows Caddy đã tắt hẳn rồi — ít rủi ro hơn dự tính ban đầu.

## Rollback
`docker compose down` trên vantt-mactu, DNS record revert (nếu đã đổi).

## Acceptance
- Caddy-global container healthy trên vantt-mactu.
- Ít nhất 1 domain test (vd `etl.lan.fwg.vn`) cấp cert thành công, truy cập HTTPS được.
- DNS đã xác nhận trỏ đúng (bước 4 — cần user input, không tự suy diễn).
