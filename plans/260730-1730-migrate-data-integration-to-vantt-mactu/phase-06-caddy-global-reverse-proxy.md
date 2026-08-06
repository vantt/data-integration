# Phase 6 — Caddy global reverse-proxy + DNS-01 cert

**Status: ĐÃ CHẠY THẬT 2026-08-06, PASS phần deploy.** `caddy-global` build + start thành công trên vantt-mactu, cấp cert Let's Encrypt thật cho cả 6 domain (`etl`/`bi`/`rill`/`evidence`/`files`/`detailview`.lan.fwg.vn) qua DNS-01, verify HTTPS trả 200 (files.lan.fwg.vn 401 đúng kỳ vọng — basic_auth). **Còn treo: DNS.**

**Phát hiện quan trọng khi chạy**: `*.lan.fwg.vn` KHÔNG resolve qua Cloudflare (wildcard A record cũ trong `caddy-global/DNS-CERTIFICATE-SETUP.md` đã bị xoá từ trước — verify qua Cloudflare API, 0 record). User xác nhận: đã chuyển sang **split-horizon DNS qua router nội bộ** (`192.168.20.1` tự trả lời `*.lan.fwg.vn`, không forward Cloudflare) — đúng theo §6 của doc đó, nhưng checklist đầu file doc chưa cập nhật nên gây nhầm lẫn lúc điều tra. **Agent KHÔNG có quyền vào router** — user phải tự đổi DNS record trên router từ `192.168.20.33` (Windows) sang `192.168.20.49` (vantt-mactu) cho cả 6 domain (hoặc wildcard nếu router hỗ trợ).

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
- Caddy-global container healthy trên vantt-mactu. ✅
- Cả 6 domain cấp cert LE thật, HTTPS trả 200 (test qua `curl --resolve ... 192.168.20.49`, bypass DNS cũ). ✅
- DNS router trỏ đúng `192.168.20.49` — **CHƯA**, user tự làm (agent không có quyền router).
