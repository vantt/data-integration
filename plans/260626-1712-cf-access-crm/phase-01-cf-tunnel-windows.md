# Phase 01: CF Tunnel on Windows

**Type:** Manual infra  
**Target:** Windows host (D:\vantt\app\data-integration machine)  
**CRM host port:** 3007 → container 8090

## Bước 1 — Cài cloudflared

```powershell
winget install Cloudflare.cloudflared
# Kiểm tra:
cloudflared --version
```

Hoặc download trực tiếp `.exe` từ https://github.com/cloudflare/cloudflared/releases

## Bước 2 — Login Cloudflare

```powershell
cloudflared tunnel login
# Browser mở → chọn zone fwg.vn → approve
# Cert lưu tại: C:\Users\Vantt\.cloudflared\cert.pem
```

## Bước 3 — Tạo tunnel

```powershell
cloudflared tunnel create crm
# Ghi lại <TUNNEL_ID> từ output
# Credentials tại: C:\Users\Vantt\.cloudflared\<TUNNEL_ID>.json
```

## Bước 4 — Cấu hình tunnel

Tạo file `C:\Users\Vantt\.cloudflared\config.yml`:

```yaml
tunnel: <TUNNEL_ID>
credentials-file: C:\Users\Vantt\.cloudflared\<TUNNEL_ID>.json

ingress:
  - hostname: crm.fwg.vn
    service: http://127.0.0.1:3007
  - service: http_status:404
```

## Bước 5 — Route DNS

```powershell
cloudflared tunnel route dns crm crm.fwg.vn
# Tự động tạo CNAME record trong Cloudflare DNS: crm.fwg.vn → <TUNNEL_ID>.cfargotunnel.com
```

## Bước 6 — Test trước khi install service

```powershell
cloudflared tunnel run crm
# Thử mở https://crm.fwg.vn → phải thấy CRM (chưa có Access guard)
# Ctrl+C để stop
```

## Bước 7 — Install Windows service

> **Lưu ý:** `cloudflared service install` chạy dưới `LocalSystem` không đọc được `C:\Users\Vantt\.cloudflared\`.
> Phải copy config ra `C:\ProgramData\cloudflared\` và sửa registry path thủ công.

```powershell
# Chạy PowerShell với quyền Administrator

# 7a. Copy config + credentials ra chỗ SYSTEM đọc được
New-Item -ItemType Directory -Force "C:\ProgramData\cloudflared"
Copy-Item "C:\Users\Vantt\.cloudflared\config.yml" "C:\ProgramData\cloudflared\config.yml"
Copy-Item "C:\Users\Vantt\.cloudflared\<TUNNEL_ID>.json" "C:\ProgramData\cloudflared\<TUNNEL_ID>.json"
Copy-Item "C:\Users\Vantt\.cloudflared\cert.pem" "C:\ProgramData\cloudflared\cert.pem"

# 7b. Sửa credentials-file trong config.yml trỏ sang ProgramData
notepad C:\ProgramData\cloudflared\config.yml
# credentials-file: C:\ProgramData\cloudflared\<TUNNEL_ID>.json

# 7c. Install service với --config
cloudflared --config "C:\ProgramData\cloudflared\config.yml" service install

# 7d. Fix registry ImagePath — sc.exe trong PowerShell có quoting bug, dùng cmd /c
cmd /c 'sc config Cloudflared binPath= "\"C:\Program Files (x86)\cloudflared\cloudflared.exe\" --config \"C:\ProgramData\cloudflared\config.yml\" tunnel run"'

# 7e. Start + verify
Start-Service Cloudflared
Get-Service Cloudflared

# Optional: tự restart sau 5s nếu crash
sc.exe failure Cloudflared reset= 86400 actions= restart/5000/restart/5000/restart/5000
```

## Bước 8 — CF Access Application (CF Dashboard)

1. Vào **Cloudflare Dashboard → Zero Trust → Access → Applications**
2. **Add an application → Self-hosted**
3. Name: `CRM`
4. Application domain: `crm.fwg.vn`
5. Session duration: 24h (hoặc tuỳ)
6. **Add a policy:**
   - Name: `Lark users`
   - Action: Allow
   - Rule: **Emails ending in** `@<company-domain>` (hoặc Lark group cụ thể)
7. Lưu → copy **Application Audience (aud tag)** → đây là `CF_ACCESS_AUDIENCE`

## Bước 9 — Verify Lark role claim

Để biết Lark bridge Worker đặt role vào JWT claim nào:

```powershell
# Login bằng Lark rồi decode JWT header:
# Cf-Access-Jwt-Assertion header → paste vào jwt.io → xem payload
# Tìm claim chứa role (thường là "custom", "role", "groups", "lark_role", v.v.)
```

→ Ghi lại tên claim → điền vào `CF_ROLE_CLAIM` trong env.

## Output của phase này

Cần note lại để điền vào `.env`:
```
CF_ACCESS_AUDIENCE=<aud từ bước 8>
CF_TEAM_DOMAIN=<team>.cloudflareaccess.com
CF_ROLE_CLAIM=<claim name từ bước 9>
```
