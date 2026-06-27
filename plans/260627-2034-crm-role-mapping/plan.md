# Plan: CRM Role Mapping & Permission Verification

**Date:** 2026-06-27  
**Status:** pending  
**Branch:** main  
**Depends on:** plans/archive/260626-1712-cf-access-crm (CF Tunnel + Auth Layer — done)

## Mục tiêu

Xác định giá trị Lark role từ JWT claim, điền `CF_ROLE_MAP` đúng, và verify phân quyền hoạt động end-to-end trên `crm.fwg.vn`.

## Context

CF Tunnel + middleware + `require_admin` guard đã hoàn thiện.  
`CF_ROLE_CLAIM=role` đã set trong `.env`.  
`CF_ROLE_MAP={}` — **đang rỗng** → mọi user hiện tại đều fallback về `sales`.

## Việc cần làm

### Bước 1 — Xác định giá trị Lark role trong JWT

Login `crm.fwg.vn` bằng Lark, mở DevTools → Network → tìm request có header `Cf-Access-Jwt-Assertion` → copy token → paste vào `jwt.io` → xem payload:

```json
{
  "email": "...",
  "name": "...",
  "role": "???",   ← đây là giá trị cần biết
  ...
}
```

Ghi lại các giá trị Lark trả về cho từng nhóm user (admin, manager, sales).

### Bước 2 — Điền CF_ROLE_MAP vào .env

```env
CF_ROLE_MAP={"<giá trị Lark admin>":"admin","<giá trị Lark manager>":"manager","<giá trị Lark sales>":"sales"}
```

Restart CRM container sau khi cập nhật:

```bash
docker compose up -d crm
```

### Bước 3 — Verify end-to-end

- [ ] Login bằng Lark admin account → vào được `/settings`
- [ ] Login bằng Lark non-admin account → `/settings` trả 403
- [ ] Header hiển thị đúng tên user đang login
- [ ] AppUser mới được tạo trong SQLite với đúng role

## Open questions

- Lark JWT claim `role` trả giá trị gì cho từng nhóm? (cần check jwt.io)
- Có bao nhiêu nhóm role cần map? (admin / manager / sales hay khác?)
