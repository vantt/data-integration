# Caddy Front Proxy — DNS & Certificate Setup

Tài liệu cấu hình DNS + TLS cho **caddy-global** (front proxy của toàn bộ stack).
Đặt cạnh `caddy-global/docker-compose.yml` vì đây là nơi quản lý cert + routing.

> **Trạng thái: ĐÃ TRIỂN KHAI** (cert Let's Encrypt thật qua Cloudflare DNS-01).
> - [x] Cloudflare token tạo + verify active + lưu `.env.docker`
> - [x] Config front proxy: `Dockerfile.caddy`, `base.Caddyfile`, `docker-compose.yml`
> - [x] Build image custom + `up` caddy-global → cấp cert DNS-01
> - [x] Label 5 service → `*.lan.fwg.vn`
> - [x] Resolve `*.lan.fwg.vn` → `192.168.20.33` (Cloudflare public wildcard A)
> - [x] Sửa link blueprint + redeploy 12 dashboard (link → `detailview.lan.fwg.vn`)

---

## 1. Values (as-built)

| Khoá | Giá trị | Ghi chú |
|---|---|---|
| Domain (zone Cloudflare) | `fwg.vn` | active, DNS host tại Cloudflare |
| Subdomain | `bi / detailview / etl / rill / files` `.lan.fwg.vn` | mỗi host 1 cert qua DNS-01 |
| Server LAN IP | `192.168.20.33` | NIC Wi-Fi — nên đặt DHCP reservation |
| Resolve `*.lan.fwg.vn` | **Cloudflare public wildcard A → 192.168.20.33** | resolve mọi nơi, không cần DNS nội bộ |
| Cloudflare API token | *(trong `.env.docker`)* | scope Zone:DNS:Edit + Zone:Read; verified active |

> **Cert per-host (không wildcard cert):** caddy-docker-proxy để mỗi service tự lấy cert theo
> hostname qua DNS-01 — đơn giản & bền. 5 cert << rate-limit Let's Encrypt.
>
> **Đánh đổi resolve:** dùng **public wildcard A record** `*.lan.fwg.vn → 192.168.20.33` nên
> resolve được từ mọi máy/resolver mà KHÔNG cần dựng DNS nội bộ. Nhược: private IP lộ trên
> public DNS — rủi ro thấp (IP RFC1918 không route từ internet, không mở inbound). Muốn giấu
> hẳn IP → bỏ A record public, chuyển sang DNS nội bộ (xem §6).

---

## 2. Kiến trúc

```
Client (LAN)                       Server 192.168.20.33 (Docker)
   │  https://bi.lan.fwg.vn           ┌─────────────────────────────┐
   │ ───────────────────────────────►│ caddy-global :80/:443       │
   │  (DNS → 192.168.20.33)           │  - đọc label container       │
   │                                  │  - cấp/gia hạn cert (DNS-01) │
   │                                  │  - reverse_proxy theo upstream│
   │                                  └──────────┬──────────────────┘
   │                                             │ caddy_net (internal)
   │                         metabase:3000 / detail_view:8000 / dagster:3001 / ...
```

- **caddy-global** = front proxy duy nhất, listen `80/443`, route theo **Docker label**
  (caddy-docker-proxy). Network dùng chung: `caddy_net` (external).
- **Cert:** Let's Encrypt cấp **per-host** qua **Cloudflare DNS-01 challenge** → chỉ cần
  **outbound** tới Cloudflare API, KHÔNG cần inbound từ internet. Cert được mọi trình
  duyệt/thiết bị tin sẵn → KHÔNG cần cài root CA.

### Service → subdomain → upstream

| Service | Subdomain | Container port |
|---|---|---|
| Metabase | `bi.lan.fwg.vn` | 3000 |
| detailView | `detailview.lan.fwg.vn` | 8000 |
| Dagster | `etl.lan.fwg.vn` | 3001 |
| Rill | `rill.lan.fwg.vn` | 9009 |
| Fileserver | `files.lan.fwg.vn` | 8080 |

---

## 3. Tại sao DNS-01 (không phải HTTP-01)

- Server **không nhận inbound** từ internet → HTTP-01 / TLS-ALPN challenge **fail**.
- DNS-01: Caddy tạo record `_acme-challenge.<host>` TXT qua Cloudflare API (outbound),
  Let's Encrypt verify, Caddy xoá record. **Hoạt động sau NAT/firewall**.
- Cert do Let's Encrypt cấp → mọi thiết bị tin sẵn, KHÔNG cần cài root CA.

---

## 4. Thành phần cấu hình (đã tạo)

| File | Vai trò |
|---|---|
| `caddy-global/Dockerfile.caddy` | Build Caddy custom = `caddy-docker-proxy` + `caddy-dns/cloudflare` (image stock thiếu DNS plugin) |
| `caddy-global/base.Caddyfile` | Global option `acme_dns cloudflare {env.CLOUDFLARE_API_TOKEN}` |
| `caddy-global/docker-compose.yml` | `build: Dockerfile.caddy`, mount base.Caddyfile, truyền `CLOUDFLARE_API_TOKEN` |
| `.env.docker` | Chứa `CLOUDFLARE_API_TOKEN` (gitignored) |
| `docker-compose.yml` (chính) | Label `caddy: <host>.lan.fwg.vn` + `caddy.reverse_proxy` cho 5 service |

Token KHÔNG nạp bằng `env_file` (tránh đổ mọi secret DB vào container proxy) mà interpolate
qua `--env-file .env.docker` lúc chạy compose; chỉ đúng 1 biến token vào container.

---

## 5. Lệnh triển khai / cập nhật

```bash
# Build + chạy front proxy (chạy từ thư mục gốc dự án; --env-file nạp token)
docker compose --env-file .env.docker -f caddy-global/docker-compose.yml up -d --build

# Áp label cho các service (recreate service nào đổi label)
docker compose up -d

# Verify cert thật (issuer phải là acme-v02.api.letsencrypt.org, KHÔNG phải "local")
docker logs caddy-global --tail 80 | grep -Ei "certificate obtained|acme|cloudflare"

# Chứng minh cert được tin sẵn (KHÔNG dùng -k; lỗi TLS = cert chưa hợp lệ)
curl -sSI https://bi.lan.fwg.vn
```

> Kết quả as-built: 5/5 host cấp cert LE trong ~35s; `curl` không `-k` đều OK.

---

## 6. (Tuỳ chọn) Giấu IP — split-horizon DNS qua router

Hiện resolve qua **public wildcard A** → private IP lộ trên public DNS. Muốn giấu hẳn dùng
**split-horizon**: router trả lời `*.lan.fwg.vn` **tại chỗ**, forward các tên khác lên upstream.

```
Client ──► Router (DNS chính, set qua DHCP)
              ├─ *.lan.fwg.vn  → TRẢ LỜI NỘI BỘ → 192.168.20.33  (KHÔNG ra internet)
              └─ tên khác       → FORWARD upstream (1.1.1.1 / 8.8.8.8 / ISP)
```

> Mấu chốt: `*.lan.fwg.vn` phải được router **trả lời nội bộ**, KHÔNG forward. Cert KHÔNG ảnh
> hưởng — DNS-01 chỉ tạo TXT `_acme-challenge` qua Cloudflare API, không liên quan A record.

**Thứ tự làm (đúng — tránh mất truy cập):**
1. Cấu hình resolver nội bộ override `*.lan.fwg.vn → 192.168.20.33`:
   - **Router (đang dùng):** Local/Static DNS, wildcard `*.lan.fwg.vn` → `192.168.20.33`
     (OpenWrt/dnsmasq, MikroTik, pfSense hỗ trợ wildcard; router gia dụng không wildcard → khai 5 host).
   - **Pi-hole:** `/etc/dnsmasq.d/02-lan-fwg.conf` → `address=/lan.fwg.vn/192.168.20.33` → `pihole restartdns`.
   - **AdGuard Home:** DNS rewrites → `*.lan.fwg.vn` → `192.168.20.33`.
   - **hosts file** (từng máy, không wildcard): 5 dòng `192.168.20.33  <host>.lan.fwg.vn`.
2. DHCP router → DNS = resolver nội bộ, để mọi client dùng.
3. **Verify** từ client: `nslookup bi.lan.fwg.vn` → Address `192.168.20.33` **và** Server = IP router
   (KHÔNG phải 8.8.8.8). Trỏ DNS của chính server về router cho nhất quán.
4. **CHỈ KHI** bước 3 OK → **xoá** A record `*.lan.fwg.vn` trên Cloudflare (hết lộ IP). Xoá trước
   bước 3 sẽ làm mất truy cập.

---

## 7. Vận hành & xử lý sự cố

| Vấn đề | Nguyên nhân / xử lý |
|---|---|
| Cert `issuer=local` | Thiếu `acme_dns` hoặc label dạng `.local`. Kiểm tra base.Caddyfile + `CADDY_DOCKER_CADDYFILE_PATH`. |
| `dns: unauthorized` | Token sai scope/zone hoặc còn dấu nháy trong `.env.docker`. Token cần Zone:DNS:Edit + Zone:Read. |
| Trình duyệt cảnh báo | Đang truy cập tên cũ, hoặc DNS chưa trỏ. `nslookup <host>.lan.fwg.vn` phải ra `192.168.20.33`. |
| Subdomain 2 cấp không resolve | Wildcard `*.lan.fwg.vn` chỉ match 1 cấp. Dùng host 1 cấp (vd `files.lan.fwg.vn`, KHÔNG `files.etl.lan.fwg.vn`). |
| Gia hạn cert | **Tự động** (Caddy renew ~30 ngày trước hạn qua DNS-01). Không cần thao tác. |
| Rate limit Let's Encrypt | Khi test nhiều, dùng global `acme_ca https://acme-staging-v02.api.letsencrypt.org/directory`. |

### Đổi/rotate token
Cập nhật `CLOUDFLARE_API_TOKEN` trong `.env.docker` →
`docker compose --env-file .env.docker -f caddy-global/docker-compose.yml up -d` (recreate nạp env mới).
> ⚠️ Token hiện tại từng dán trong chat → nên rotate (tạo mới, revoke cũ) cho an toàn.

### Không xoá volume `caddy_data`
Chứa account ACME + cert đã cấp. `docker compose down -v` sẽ buộc cấp lại cert (rủi ro rate limit).

---

## 8. Fallback — domain nội bộ `.local` (CA nội bộ Caddy)

Nếu cần service chỉ chạy LAN bằng `.local` (không qua Let's Encrypt):
- Label `caddy: <ten>.local` + `caddy.tls: internal` (TLD công khai phải ép `internal`).
- Client phải **tin root CA** của Caddy:
  ```bash
  docker cp caddy-global:/data/caddy/pki/authorities/local/root.crt .
  # Windows (Admin): Import-Certificate -FilePath .\root.crt -CertStoreLocation Cert:\LocalMachine\Root
  # Firefox: about:config → security.enterprise_roots.enabled = true
  ```

---

## 9. Tham chiếu
- caddy-docker-proxy: https://github.com/lucaslorentz/caddy-docker-proxy
- caddy-dns/cloudflare: https://github.com/caddy-dns/cloudflare
- Caddy DNS challenge: https://caddyserver.com/docs/automatic-https#dns-challenge
