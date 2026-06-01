# Caddy Front Proxy — DNS & Certificate Setup

Tài liệu cấu hình DNS + TLS cho **caddy-global** (front proxy của toàn bộ stack).
Đặt cạnh `caddy-global/docker-compose.yml` vì đây là nơi quản lý cert + routing.

> **Trạng thái triển khai:**
> - [x] Cloudflare token tạo + verify active + lưu `.env.docker`
> - [x] Config front proxy (Dockerfile.caddy, base.Caddyfile, compose) đã soạn
> - [ ] Build image + `up` caddy-global (cấp cert DNS-01)
> - [ ] Đổi label 5 service sang `*.lan.fwg.vn`
> - [ ] DNS nội bộ trỏ `*.lan.fwg.vn` → `192.168.20.33`
> - [ ] Sửa link blueprint + redeploy 12 dashboard

---

## 1. Values

| Khoá | Giá trị | Ghi chú |
|---|---|---|
| Domain (zone Cloudflare) | `fwg.vn` | active, DNS host tại Cloudflare |
| Subdomain | `bi/detailview/etl/rill/files.lan.fwg.vn` | per-host cert qua DNS-01 |
| Server LAN IP | `192.168.20.33` | NIC Wi-Fi — nên đặt DHCP reservation |
| DNS server nội bộ | `<INTERNAL_DNS>` | Pi-hole / AdGuard / router / hosts file |
| Cloudflare API token | *(trong `.env.docker`)* | scope Zone:DNS:Edit + Zone:Read; đã verify active |

> **Cert per-host thay vì wildcard:** với caddy-docker-proxy, để mỗi service tự lấy cert
> theo hostname (qua DNS-01) là đơn giản & bền nhất. Vẫn KHÔNG publish A record (DNS-01 chỉ
> tạo TXT challenge tạm), nên mục tiêu "không lộ IP nội bộ" vẫn đạt. 5 cert << rate-limit
> Let's Encrypt. Wildcard chỉ cần nếu sau này có nhiều subdomain động.

---

## 2. Kiến trúc

```
Client (LAN)                    Server (Docker)
   │  https://bi.lan.<domain>      ┌─────────────────────────────┐
   │ ───────────────────────────► │ caddy-global :80/:443       │
   │  (DNS nội bộ → LAN_IP)        │  - đọc label container       │
   │                               │  - cấp/gia hạn cert (DNS-01) │
   │                               │  - reverse_proxy theo upstream│
   │                               └──────────┬──────────────────┘
   │                                          │ caddy_net (internal)
   │                              metabase:3000 / detail_view:8000 / ...
```

- **caddy-global** = front proxy duy nhất, listen `80/443`, route theo **Docker label**
  (`lucaslorentz/caddy-docker-proxy`). Network dùng chung: `caddy_net` (external).
- **Cert:** Let's Encrypt **wildcard `*.lan.<domain>`** cấp qua **Cloudflare DNS-01 challenge**
  → chỉ cần **outbound** tới Cloudflare API, KHÔNG cần inbound từ internet.
- **Resolve:** DNS-01 chỉ tạo TXT challenge tạm thời rồi xoá → **không publish A record**,
  không lộ IP nội bộ. Việc resolve tên → `LAN_IP` do **DNS nội bộ** đảm nhiệm.

### Service → subdomain → upstream

| Service | Subdomain | Container port |
|---|---|---|
| Metabase | `bi.lan.<domain>` | 3000 |
| detailView | `detailview.lan.<domain>` | 8000 |
| Dagster | `etl.lan.<domain>` | 3001 |
| Rill | `rill.lan.<domain>` | 9009 |
| Fileserver | `files.lan.<domain>` | 8080 |

---

## 3. Tại sao DNS-01 (không phải HTTP-01)

- Server **không nhận inbound** từ internet → HTTP-01 / TLS-ALPN challenge **fail**.
- DNS-01: Caddy tạo record `_acme-challenge.lan.<domain>` TXT qua Cloudflare API (outbound),
  Let's Encrypt verify, Caddy xoá record. **Hoạt động sau NAT/firewall**, hỗ trợ **wildcard**.
- Cert do Let's Encrypt cấp → **mọi trình duyệt/thiết bị tin sẵn**, KHÔNG cần cài root CA.

---

## 4. Các bước triển khai

### Bước 1 — Tạo Cloudflare API token
1. Cloudflare Dashboard → My Profile → **API Tokens** → Create Token → *Custom token*.
2. Permissions: **Zone → DNS → Edit** và **Zone → Zone → Read**.
3. Zone Resources: chỉ zone `<domain>`.
4. Copy token, thêm vào `.env.docker` (KHÔNG có dấu nháy bao quanh):
   ```
   CLOUDFLARE_API_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   > `.env.docker` đã nằm trong `.gitignore` — không commit token.

### Bước 2 — Build Caddy image custom (kèm DNS plugin)
Image mặc định `lucaslorentz/caddy-docker-proxy:ci-alpine` **không có** `caddy-dns/cloudflare`.
Tạo `caddy-global/Dockerfile.caddy`:
```dockerfile
FROM caddy:2-builder AS builder
RUN xcaddy build \
    --with github.com/lucaslorentz/caddy-docker-proxy/v2 \
    --with github.com/caddy-dns/cloudflare

FROM caddy:2-alpine
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
CMD ["caddy", "docker-proxy"]
```

### Bước 3 — Base Caddyfile (global options)
Tạo `caddy-global/base.Caddyfile` để cấu hình DNS challenge toàn cục:
```caddyfile
{
    # ACME DNS-01 qua Cloudflare cho mọi cert (trừ .local → vẫn internal CA)
    acme_dns cloudflare {env.CLOUDFLARE_API_TOKEN}
    # email nhận cảnh báo hết hạn (tuỳ chọn)
    # email ban@<domain>
}
```

### Bước 4 — `caddy-global/docker-compose.yml` (ĐÃ áp dụng)
Đã đổi `image:` → `build: Dockerfile.caddy`, thêm mount `base.Caddyfile` + 2 env
(`CADDY_DOCKER_CADDYFILE_PATH`, `CLOUDFLARE_API_TOKEN`). Token KHÔNG nạp bằng `env_file`
(tránh đổ mọi secret DB vào container proxy) mà interpolate qua `--env-file .env.docker`
lúc chạy compose (xem Bước 7). Chỉ đúng 1 biến token được truyền vào container.

### Bước 5 — Đổi label service (`docker-compose.yml` chính)
Mỗi service thêm site block subdomain thật. Giữ luôn `.local` (ordinal block) trong giai đoạn
chuyển tiếp để không gián đoạn nếu DNS nội bộ chưa sẵn sàng. Ví dụ Metabase:
```yaml
    labels:
      caddy_0: bi.lan.fwg.vn              # nội bộ cũ (CA nội bộ) — bỏ sau khi .lan.fwg.vn chạy ổn
      caddy_0.reverse_proxy: "{{upstreams 3000}}"
      caddy_1: bi.lan.fwg.vn         # cert thật qua DNS-01
      caddy_1.reverse_proxy: "{{upstreams 3000}}"
```
Áp tương tự: `detailview.lan.fwg.vn` (8000), `etl.lan.fwg.vn` (3001), `rill.lan.fwg.vn` (9009),
`files.lan.fwg.vn` (8080). Cert mỗi host Caddy tự lấy qua DNS-01.

### Bước 6 — DNS nội bộ (resolve `*.lan.fwg.vn` → `192.168.20.33`)

Mục tiêu: client trong LAN gõ `https://bi.lan.fwg.vn` phải resolve về `192.168.20.33`.
Chọn **một** cách:

**Cách 1 — Pi-hole (khuyến nghị, tập trung, hỗ trợ wildcard):**
- Settings → Local DNS → *hoặc* tạo file `/etc/dnsmasq.d/02-lan-fwg.conf`:
  ```
  address=/lan.fwg.vn/192.168.20.33
  ```
  (1 dòng = wildcard, mọi `*.lan.fwg.vn` → IP). Restart DNS: `pihole restartdns`.
- Trỏ DHCP của router → DNS = IP Pi-hole, để mọi client dùng.

**Cách 2 — AdGuard Home (tập trung, wildcard):**
- Filters → DNS rewrites → thêm: Domain `*.lan.fwg.vn` → Answer `192.168.20.33`.
- Router DHCP → DNS = IP AdGuard.

**Cách 3 — DNS trên router:** nhiều router (OpenWrt, MikroTik, pfSense) có "Local DNS /
Static DNS". Thêm wildcard `*.lan.fwg.vn` → `192.168.20.33` (OpenWrt dùng dnsmasq giống Pi-hole).
Router gia dụng phổ thông thường KHÔNG hỗ trợ wildcard → liệt kê 5 host.

**Cách 4 — hosts file (nhanh nhất, KHÔNG cần DNS server, KHÔNG wildcard — phải làm từng máy):**
- Windows: `C:\Windows\System32\drivers\etc\hosts` (mở bằng Notepad Admin)
- macOS/Linux: `/etc/hosts`
  ```
  192.168.20.33  bi.lan.fwg.vn
  192.168.20.33  detailview.lan.fwg.vn
  192.168.20.33  etl.lan.fwg.vn
  192.168.20.33  rill.lan.fwg.vn
  192.168.20.33  files.lan.fwg.vn
  ```
- Hợp khi ít máy. Mỗi máy mới phải thêm lại → nhiều máy thì dùng Cách 1/2.

> Lưu ý: việc resolve nội bộ **độc lập** với việc cấp cert. Cert vẫn cấp được qua DNS-01 dù
> chưa cấu hình resolve. Nhưng client chỉ truy cập được sau khi resolve đúng IP.

### Bước 7 — Áp dụng & verify
```bash
# 1. Build + chạy front proxy (chạy từ thư mục gốc dự án; --env-file nạp token)
docker compose --env-file .env.docker -f caddy-global/docker-compose.yml up -d --build

# 2. Áp label mới cho các service
docker compose up -d

# 3. Xem cert đã cấp (issuer phải là Let's Encrypt / acme, KHÔNG phải "local")
docker logs caddy-global --tail 60 | grep -Ei "certificate obtained|acme|dns|cloudflare"

# 4. Test resolve nội bộ (từ máy client)
nslookup bi.lan.fwg.vn          # → phải ra 192.168.20.33
# Mở https://bi.lan.fwg.vn → xanh, không cảnh báo, không cần cài root CA
```

---

## 5. Vận hành & xử lý sự cố

| Vấn đề | Nguyên nhân / xử lý |
|---|---|
| Cert vẫn `issuer=local` | Domain dạng `.local` hoặc thiếu `acme_dns`. Kiểm tra base.Caddyfile + label đã đổi sang `<domain>`. |
| Lỗi `dns: unauthorized` | Token sai scope/zone hoặc còn dấu nháy trong `.env.docker`. Token cần Zone:DNS:Edit. |
| Trình duyệt vẫn cảnh báo | Đang truy cập tên `.local` cũ, hoặc DNS nội bộ chưa trỏ. `nslookup` kiểm tra. |
| `nslookup` không ra IP | Client chưa dùng `<INTERNAL_DNS>` làm resolver, hoặc thiếu record wildcard. |
| Gia hạn cert | **Tự động** (Caddy renew ~30 ngày trước hạn qua DNS-01). Không cần thao tác. |
| Rate limit Let's Encrypt | Wildcard = 1 cert cho mọi sub → ít chạm limit. Khi test nhiều, dùng `acme_ca` staging. |

### Đổi/rotate token
Cập nhật `CLOUDFLARE_API_TOKEN` trong `.env.docker` → `docker compose -f caddy-global/docker-compose.yml up -d` (recreate để nạp env mới).

### Không xoá volume `caddy_data`
Chứa account ACME + cert đã cấp. `docker compose down -v` sẽ buộc cấp lại cert (rủi ro rate limit).

---

## 6. Fallback — domain nội bộ `.local` (CA nội bộ Caddy)

Nếu cần thêm service chỉ chạy LAN bằng `.local` (không qua Let's Encrypt):
- Label `caddy: <ten>.local` + `caddy.tls: internal` (với TLD công khai phải ép `internal`).
- Client phải **tin root CA** của Caddy:
  ```bash
  docker cp caddy-global:/data/caddy/pki/authorities/local/root.crt .
  # Windows (Admin): Import-Certificate -FilePath .\root.crt -CertStoreLocation Cert:\LocalMachine\Root
  # Firefox: about:config → security.enterprise_roots.enabled = true
  ```

---

## 7. Tham chiếu
- caddy-docker-proxy: https://github.com/lucaslorentz/caddy-docker-proxy
- caddy-dns/cloudflare: https://github.com/caddy-dns/cloudflare
- Caddy DNS challenge / wildcard: https://caddyserver.com/docs/automatic-https#dns-challenge
