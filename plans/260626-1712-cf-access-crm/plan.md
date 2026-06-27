# Plan: CF Access + CRM Auth Layer

**Date:** 2026-06-26  
**Status:** in-progress  
**Branch:** main

## Mục tiêu

1. Expose CRM ra internet an toàn qua Cloudflare Tunnel (Windows service)
2. Bảo vệ toàn bộ CRM bằng Cloudflare Access (Lark identity provider)
3. Map Lark role → CRM role qua config, enforce `/settings*` chỉ `admin`
4. Auto-provision `AppUser` khi email lần đầu login

## Kiến trúc

```
Internet
  └── Cloudflare Access (Lark auth → CF JWT)
        └── CF Tunnel (cloudflared Windows service)
              └── http://127.0.0.1:3007 (CRM container)
                    └── CF Access Middleware (verify JWT, inject request.state.current_user)
                          ├── All routes: current_user available in templates
                          └── /settings*: require_admin dependency → 403 if role != admin
```

## Phases

| # | Phase | Type | Status |
|---|-------|------|--------|
| 01 | [CF Tunnel on Windows](phase-01-cf-tunnel-windows.md) | Manual infra | **done** |
| 02 | [CRM auth layer](phase-02-crm-auth-layer.md) | Code | pending |

## Env vars mới (thêm vào `.env` + docker-compose.yml crm service)

```env
CF_ACCESS_AUDIENCE=<aud từ CF Dashboard sau phase 01>
CF_TEAM_DOMAIN=<team>.cloudflareaccess.com
CF_ROLE_CLAIM=<claim name từ Lark bridge Worker — cần verify>
CF_ROLE_MAP={"<LarkGroup>":"admin","<LarkGroup2>":"manager","<LarkGroup3>":"sales"}
```

## Acceptance criteria

- [ ] `crm.fwg.vn` yêu cầu Lark login trước khi vào app
- [ ] Email lần đầu → `AppUser` tự tạo trong SQLite với role từ `CF_ROLE_MAP`
- [ ] `GET /settings` trả 403 với user không phải `admin`
- [ ] Header layout hiển thị tên user đang login
- [ ] `CF_ACCESS_AUDIENCE` unset → bypass (dev LAN mode)

## Open questions

- Lark bridge Worker đặt role vào JWT claim nào? (`role`? `custom.role`? `groups`?)
- Public domain: `crm.fwg.vn` hay tên khác?
