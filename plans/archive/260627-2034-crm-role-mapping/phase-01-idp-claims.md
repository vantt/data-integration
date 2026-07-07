# Phase 1 — IdP claims: departments + functional_roles (external dependency)

**Loại:** External dependency — code nằm ở repo IdP (Lark OIDC provider tự viết), NGOÀI repo `data-integration` này.
**Phụ thuộc:** Không (có thể bắt đầu ngay, song song với Phase 3).

**Cập nhật 2026-07-07:** claim thật do IdP trả về là **plural/array** — `departments` và `functional_roles` (KHÔNG phải `department`/`role` số ít như spec ban đầu bên dưới; giữ nguyên phần dưới để tham khảo lịch sử quyết định, nhưng field name đã đổi). Repo này (`data-integration`) đã cập nhật code để đọc 2 claim array này — xem `crm/src/config.py` (`cf_dept_claim()` default `custom.departments`, `cf_func_role_claim()` default `custom.functional_roles`) và `cf_access_middleware.py` (`_get_claim_values`, `_resolve_crm_role` — mỗi user có thể có nhiều department/functional_role, role CRM = giá trị ưu tiên cao nhất trong các giá trị khớp `CF_ROLE_MAP`, thứ tự admin > manager > care > sales).

## Context

- CRM đọc 2 claim (departments, functional_roles) qua dot-path config (`CF_DEPT_CLAIM` default `custom.departments`, `CF_FUNC_ROLE_CLAIM` default `custom.functional_roles`) — xem `crm/src/config.py` và `cf_access_middleware.py` (`_get_claim_values`).
- Hiện tại `CF_ROLE_MAP={}` (chưa điền) → mọi user fallback `sales`.
- CF Access chỉ match được claim đã khai báo trong OIDC Claims config của provider (Phase 2); claim khai báo được CF nhét vào `Cf-Access-Jwt-Assertion` dưới namespace `custom.*`.

## Requirements

IdP (repo ngoài) cần thêm vào id_token trả về cho CF Access:

```json
{
  "email": "...",
  "name": "...",
  "departments": ["<tên phòng ban Lark, org-level>", "..."],
  "functional_roles": ["<chức danh/vai trò chức năng Lark, org-level>", "..."]
}
```

Cả 2 claim đều là **array** (user có thể thuộc nhiều phòng ban/chức năng) và lấy từ Lark org directory. CRM dùng `departments` + `functional_roles` như nhau — mọi giá trị của cả 2 array được tra `CF_ROLE_MAP`, giá trị ưu tiên cao nhất (admin > manager > care > sales) thắng.

Sau khi CF Access nhét custom claims, phía CRM sẽ thấy tại path:

- `custom.departments` (array)
- `custom.functional_roles` (array)

(vì middleware đọc `payload.custom.<key>` — xem `_get_claim_values`, dot-path `"custom.departments"` / `"custom.functional_roles"`).

## Test result (2026-07-07)

**Lần 1** (trước khi làm Phase 2): `custom` claim chỉ có `{name, sub, picture}` — CHƯA thấy `departments`/`functional_roles`.

**Lần 2** (sau khi khai báo OIDC Claims ở Phase 2) — **PASS**: `/debug/me` cho `van.tran@fgorg.vn` trả về

```json
"custom": {
  "departments": ["bod", "ky-thuat", "marketing", "ecom", "customer-care"],
  "functional_roles": ["test-1", "bod", "it"]
}
```

Xác nhận: (1) claim là slug kebab-case, không dấu; (2) 1 user có thể có nhiều department VÀ nhiều functional_role cùng lúc (tài khoản test này có 5 department + 3 functional_role); (3) pipeline đọc array claim → `_resolve_crm_role` hoạt động đúng (`role: "sales"` vì `CF_ROLE_MAP` còn rỗng `{}` → fallback đúng theo thiết kế). Phase 1 + Phase 2 coi như xong về mặt kỹ thuật; còn lại là điền `CF_ROLE_MAP` thật (xem `phase-03-crm-role-management.md`) và xác nhận toàn bộ tập giá trị department/functional_role trong org (mới thấy 1 tài khoản, có thể chưa đại diện hết).

## Implementation steps (ở repo IdP, ngoài scope code repo này)

1. Xác định field Lark API trả về org department + role (Lark Open API: `department_id` cần resolve tên, hoặc `department_name` nếu API cung cấp sẵn).
2. Thêm 2 field này vào id_token claims khi issue token cho CF Access.
3. Deploy IdP.

## Validation — verify bằng jwt.io

1. Login `crm.fwg.vn` (hoặc domain test) bằng Lark.
2. DevTools → Network → tìm request có header `Cf-Access-Jwt-Assertion` → copy token.
3. Paste vào `jwt.io` (hoặc gọi `/debug/me` — xem test result ở trên) → xem payload, tìm:
   ```json
   {
     "email": "...",
     "custom": {
       "departments": ["???"],   ← giá trị thật cần ghi lại
       "functional_roles": ["???"]
     }
   }
   ```
4. Ghi lại giá trị `departments`/`functional_roles` thật cho từng nhóm (Sales, CSKH/Care, Quản lý, Admin) — dùng để điền `CF_ROLE_MAP` ở Phase 3 config.

## Risks & rollback

- Nếu IdP chưa deploy claim mới: CRM vẫn hoạt động bình thường ở role fallback `sales` (không breaking) — Phase 3 (bootstrap admin + UI đổi role) không phụ thuộc claim này nên không bị chặn.
- Rollback: không cần — đây là bổ sung claim, không đổi hành vi hiện tại của IdP.

## Open question

- Tên phòng ban Lark trả về ở dạng gì — tiếng Việt có dấu, tiếng Anh, hay mã nội bộ? Cần xác nhận trước khi điền `CF_ROLE_MAP` (JSON key phải khớp chính xác).
