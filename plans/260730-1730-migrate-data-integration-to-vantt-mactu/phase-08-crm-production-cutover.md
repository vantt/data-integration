# Phase 8 — CRM/Metabase production cutover (Cloudflare Tunnel)

**GATE**: chỉ bắt đầu sau khi user xác nhận rõ ràng phase 7 đã ổn định. Production thật, nhân viên dùng qua domain public.

**Bối cảnh chốt 2026-08-04**: máy Windows sẽ bị **uninstall và cài lại** sau khi migrate thành công — không phải "giữ song song rollback vô thời hạn" như phase 9 draft ban đầu, mà là mốc cứng. Cloudflare Tunnel hiện tại là **locally-managed tunnel** (không phải token-based), chạy như Windows Service, dùng chung cho NHIỀU service không thuộc repo này — phải xử lý cẩn thận, không chỉ tắt Windows Service là xong.

## Recon đã xác nhận (2026-08-04)

Nguồn: `C:\ProgramData\cloudflared\config.yml` (đang chạy — `cloudflared.exe --config ... tunnel run`, KHÔNG dùng `TUNNEL_TOKEN`).

| Hostname | Origin hiện tại | Reachable từ vantt-mactu? | Thuộc scope migrate này? |
|---|---|---|---|
| `crm.fwg.vn` | `127.0.0.1:3007` | Có, nếu CRM + tunnel cùng ở vantt-mactu | **Có** |
| `bi.fwg.vn` | `127.0.0.1:3001` | Có, nếu Metabase + tunnel cùng ở vantt-mactu | **Có** |
| `vnflow.fwg.vn` | `192.168.20.175:8100` | **Không — đã test ping, 100% packet loss từ vantt-mactu** (LAN khác segment) | Không — project khác, ngoài scope |
| `hermes.fwg.vn` | `100.66.22.20:9119` (Tailscale, host `design-lap`) | Có, đã test ping OK | Không — project khác, ngoài scope |
| `fgos.fwg.vn` | `100.66.22.20:8765` (cùng `design-lap`) | Có | Không — project khác, ngoài scope |

**Quyết định 2026-08-04**: chuyển nguyên cụm tunnel connector sang vantt-mactu, chạy Docker. `vnflow.fwg.vn` SẼ gãy sau khi Windows bị wipe — **user đã xác nhận chấp nhận bỏ qua, ưu tiên bi/crm** ("bỏ qua vnflow đi, không quan trọng bằng bi/crm"), không cần xử lý trong migration này, không hỏi lại. `hermes.fwg.vn`/`fgos.fwg.vn` tiếp tục hoạt động bình thường vì reachable qua Tailscale không phụ thuộc origin chuyển đi đâu.

**Recon phụ (2026-08-04)**: đã xác định `192.168.20.175` (origin vnflow) KHÔNG phải `design-lap` (design-lap chỉ có Tailscale IP `100.66.22.20`, không xuất hiện trong ARP LAN `192.168.20.x`) và KHÔNG phải vantt-mactu (LAN IP thật của vantt-mactu là `192.168.20.49`, cùng subnet nhưng khác host). Thiết bị tại `.175` hiện offline (ARP trả `incomplete`) — không xác định được là máy nào. Không cố gắng SSH vào `design-lap` được (`Permission denied` — key hiện tại chưa được cấp quyền ở đó), không liên quan tới quyết định bỏ qua vnflow nên không chặn tiến độ.

**Kiến trúc**: chạy cloudflared như **service Docker ĐỘC LẬP**, KHÔNG nhúng vào `data-integration/docker-compose.yml` — tránh coupling vòng đời (nếu ai `docker compose down` data-integration sẽ kéo sập luôn route `hermes.fwg.vn`/`fgos.fwg.vn` của project khác, không liên quan gì tới nhau). Đặt tại `~/cloudflared-tunnel/` riêng trên vantt-mactu.

## Bước

### 8.1 — Transfer + dockerize tunnel connector

1. Copy 3 file cấu hình tunnel từ Windows (KHÔNG qua git, KHÔNG qua app_data/backups — đây là secret, `.json` chứa private key):
   ```bash
   ssh vantt-mactu "mkdir -p ~/cloudflared-tunnel/config"
   scp "/c/ProgramData/cloudflared/0cece51f-9721-4a5d-9797-f63ecf8d5d16.json" \
       "/c/ProgramData/cloudflared/cert.pem" \
       "/c/ProgramData/cloudflared/config.yml" \
       vantt-mactu:~/cloudflared-tunnel/config/
   ```
2. Sửa `config.yml` trên vantt-mactu: cập nhật `credentials-file` path cho đúng Linux path, XOÁ dòng `vnflow.fwg.vn` (origin không reachable, tránh cloudflared cố connect rồi log lỗi liên tục) — giữ nguyên `crm.fwg.vn`/`bi.fwg.vn`/`hermes.fwg.vn`/`fgos.fwg.vn`:
   ```yaml
   tunnel: 0cece51f-9721-4a5d-9797-f63ecf8d5d16
   credentials-file: /etc/cloudflared/0cece51f-9721-4a5d-9797-f63ecf8d5d16.json
   ingress:
     - hostname: crm.fwg.vn
       service: http://127.0.0.1:3007
     - hostname: bi.fwg.vn
       service: http://127.0.0.1:3001
     - hostname: hermes.fwg.vn
       service: http://100.66.22.20:9119
     - hostname: fgos.fwg.vn
       service: http://100.66.22.20:8765
     - service: http_status:404
   ```
3. Tạo `docker-compose.yml` độc lập tại `~/cloudflared-tunnel/docker-compose.yml` — dùng `network_mode: host` (Linux native host, không phải Docker Desktop, host networking hoạt động bình thường) để `127.0.0.1:3007`/`127.0.0.1:3001` trong config trỏ đúng port host thật, KHÔNG cần đổi sang service-name Docker (`crm:8090`) hay join `caddy_net`:
   ```yaml
   services:
     cloudflared:
       image: cloudflare/cloudflared:latest
       container_name: cloudflared
       restart: unless-stopped
       network_mode: host
       command: tunnel --config /etc/cloudflared/config.yml run
       volumes:
         - ./config:/etc/cloudflared:ro
   ```
4. Start, verify log kết nối:
   ```bash
   ssh vantt-mactu "cd ~/cloudflared-tunnel && docker compose up -d && docker logs cloudflared --tail 30"
   ```
   Kỳ vọng: log `Registered tunnel connection` cho ≥2 edge location, KHÔNG có lỗi origin cho crm/bi/hermes/fgos.

### 8.2 — Verify song song (KHÔNG cần dừng Windows ngay)

Cloudflare Tunnel hỗ trợ nhiều connector replica cùng 1 tunnel — có thể chạy song song Windows + vantt-mactu một lúc, Cloudflare tự load-balance. Vì origin CRM/Metabase thật vẫn đang ở Windows lúc này (CRM Windows đã stop trong phase 8 gốc — data transfer), request routed sang connector vantt-mactu sẽ hit đúng CRM/Metabase vantt-mactu; request routed sang connector Windows sẽ 502 vì Windows CRM đã stop. Chấp nhận vài request lỗi thoáng qua trong lúc chuyển tiếp, hoặc:
```powershell
# Dừng hẳn Windows connector trước khi test để tránh nhầm lẫn log
Stop-Service Cloudflared
```
Verify từ ngoài:
```bash
curl -sI https://crm.fwg.vn/health
curl -sI https://bi.fwg.vn/api/health
curl -sI https://hermes.fwg.vn
curl -sI https://fgos.fwg.vn
```

### 8.3 — CRM data cutover (giữ nguyên như bản gốc)

(giữ nguyên nội dung bước 1-3 bản trước: transfer delta `crm_data`/`crm_backups` lần cuối, `PRAGMA integrity_check`, start `crm`/`crm_drill_runner` trên vantt-mactu — xem lịch sử file nếu cần chi tiết lệnh.)

## Rủi ro còn lại (không thuộc scope sửa, chỉ ghi nhận)

- `vnflow.fwg.vn` sẽ mất route khi Windows bị wipe — **user đã chấp nhận bỏ qua** (2026-08-04), không xử lý trong migration này.
- `hermes.fwg.vn`/`fgos.fwg.vn` phụ thuộc `100.66.22.20` (design-lap) qua Tailscale — nếu máy đó offline, 2 domain này gãy độc lập với migration này, không phải lỗi mới do ta gây ra.

## Rollback
Trước khi Windows bị wipe: `docker compose stop` trên vantt-mactu (cả `cloudflared-tunnel` lẫn `crm`), `Start-Service Cloudflared` lại trên Windows. Sau khi Windows đã wipe: KHÔNG còn rollback path — đây là lý do phase 7 + 8.2 phải verify kỹ trước khi cho phép wipe Windows (xem phase 9 cập nhật).

## Acceptance
- `cloudflared` container trên vantt-mactu log kết nối thành công, không lỗi origin cho crm/bi/hermes/fgos.
- 4 domain (`crm.fwg.vn`, `bi.fwg.vn`, `hermes.fwg.vn`, `fgos.fwg.vn`) trả response đúng từ bên ngoài.
- `vnflow.fwg.vn` — user đã được thông báo rõ sẽ gãy, xác nhận chấp nhận trước khi wipe Windows.
- CRM data integrity check pass, nhân viên đăng nhập thử CRM public domain thành công.
