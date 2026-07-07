# Phase 1 — IdP claims: department + role (external dependency)

**Loại:** External dependency — code nằm ở repo IdP (Lark OIDC provider tự viết), NGOÀI repo `data-integration` này.
**Phụ thuộc:** Không (có thể bắt đầu ngay, song song với Phase 3).

## Context

- CRM đọc role claim qua dot-path config (`CF_ROLE_CLAIM`, default `role`) — xem `crm/src/config.py:69-79` và `cf_access_middleware.py:59-67` (`_get_claim`).
- Hiện tại claim `role` map rỗng (`CF_ROLE_MAP={}`) → mọi user fallback `sales` (`cf_access_middleware.py:132-133`).
- Quyết định thiết kế (xem `plan.md`): dùng **department** làm nguồn default role vì ổn định hơn chức danh (`role`) — chức danh đổi thường xuyên hơn phòng ban.
- CF Access chỉ match được claim đã khai báo trong OIDC Claims config của provider (Phase 2); claim khai báo được CF nhét vào `Cf-Access-Jwt-Assertion` dưới namespace `custom.*`.

## Requirements

IdP (repo ngoài) cần thêm vào id_token trả về cho CF Access:

```json
{
  "email": "...",
  "name": "...",
  "department": "<tên phòng ban Lark, org-level>",
  "role": "<chức danh Lark, org-level>"
}
```

Cả 2 claim đều lấy từ Lark org directory (không phải khái niệm app-specific). CRM sẽ dùng `department` làm primary; `role` là dự phòng/tham khảo, không bắt buộc dùng ngay.

Sau khi CF Access nhét custom claims, phía CRM sẽ thấy tại path:

- `custom.department`
- `custom.role`

(vì middleware đọc `payload.custom.<key>` — xem `_get_claim` dùng dot-path `"custom.department"`).

## Implementation steps (ở repo IdP, ngoài scope code repo này)

1. Xác định field Lark API trả về org department + role (Lark Open API: `department_id` cần resolve tên, hoặc `department_name` nếu API cung cấp sẵn).
2. Thêm 2 field này vào id_token claims khi issue token cho CF Access.
3. Deploy IdP.

## Validation — verify bằng jwt.io

1. Login `crm.fwg.vn` (hoặc domain test) bằng Lark.
2. DevTools → Network → tìm request có header `Cf-Access-Jwt-Assertion` → copy token.
3. Paste vào `jwt.io` → xem payload, tìm:
   ```json
   {
     "email": "...",
     "custom": {
       "department": "???",   ← giá trị thật cần ghi lại
       "role": "???"
     }
   }
   ```
4. Ghi lại giá trị `department` thật cho từng nhóm (Sales, CSKH/Care, Quản lý, Admin) — dùng để điền `CF_ROLE_MAP` ở Phase 3 config.

## Risks & rollback

- Nếu IdP chưa deploy claim mới: CRM vẫn hoạt động bình thường ở role fallback `sales` (không breaking) — Phase 3 (bootstrap admin + UI đổi role) không phụ thuộc claim này nên không bị chặn.
- Rollback: không cần — đây là bổ sung claim, không đổi hành vi hiện tại của IdP.

## Open question

- Tên phòng ban Lark trả về ở dạng gì — tiếng Việt có dấu, tiếng Anh, hay mã nội bộ? Cần xác nhận trước khi điền `CF_ROLE_MAP` (JSON key phải khớp chính xác).
