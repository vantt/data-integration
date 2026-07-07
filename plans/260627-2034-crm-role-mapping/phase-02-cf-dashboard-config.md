# Phase 2 — CF Zero Trust dashboard config (thao tác tay, không code)

**Loại:** Thao tác dashboard trên Cloudflare Zero Trust — không có code thay đổi trong repo này.
**Phụ thuộc:** Phase 1 (cần biết giá trị claim thật để test policy đúng).

## Context

- CRM app đã có CF Access Application + Tunnel từ plan `plans/archive/260626-1712-cf-access-crm` (done).
- Middleware hiện tại (`crm/src/adapters/inbound/http/cf_access_middleware.py:8-11`) chỉ verify JWT audience/signature — KHÔNG check quyền vào app; việc chặn "ai được vào" là trách nhiệm của CF Access edge (policy), không phải code CRM.
- Claim đánh giá lúc authenticate/renew session — đổi policy/group không có hiệu lực real-time cho session đang mở, chỉ áp dụng lần login/renew tiếp theo.

## Requirements

1. Khai báo 2 OIDC claim `department`, `role` trong provider config (Zero Trust → Settings → Authentication → chọn Lark OIDC provider → OIDC Claims) — CF chỉ match được claim đã khai báo ở đây.
2. Tạo **Access Groups** tái dùng cho nhiều app (không chỉ CRM):
   - `grp-admins` — rule: Email trong danh sách cụ thể (hoặc claim `role` = giá trị admin nếu đã xác nhận ở Phase 1).
   - `grp-managers` — rule: claim `role` hoặc email list.
   - `grp-sales` — rule: claim `department` ∈ {tên phòng Sales theo Phase 1}.
   - (Thêm group khác nếu cần — CSKH/Care, v.v.)
3. Gắn Policy cho CRM Access Application: reference các group trên (Allow policy), KHÔNG duplicate rule trực tiếp trong policy (để group tái dùng được khi thêm app khác — Metabase/Dagster/Rill/Evidence).

## Implementation steps

1. Zero Trust dashboard → Settings → Authentication → Login methods → chọn Lark OIDC provider → Edit → OIDC Claims → thêm `department`, `role`.
2. Access → Groups → New group → tạo từng group theo mục Requirements #2.
3. Access → Applications → chọn CRM app → Policies → Edit policy → Include → Groups → chọn groups vừa tạo.
4. Save, chờ propagate (thường vài phút).

## Validation

- [ ] Login bằng account nằm trong `grp-admins` → vào được CRM.
- [ ] Login bằng account KHÔNG nằm trong bất kỳ group nào → CF Access chặn ở edge (màn hình "Access Denied" của Cloudflare, KHÔNG phải app trả 403) — verify request không tới được CRM container (check log app không có entry tương ứng).
- [ ] Kiểm tra `Cf-Access-Jwt-Assertion` payload có `custom.department`/`custom.role` đúng giá trị Phase 1 đã ghi nhận.

## Risks & rollback

- Sai policy có thể khóa tất cả user ngoài dashboard admin CF — luôn giữ ít nhất 1 policy fallback bằng email cụ thể của người thao tác trước khi xóa policy cũ.
- Rollback: xóa policy mới, khôi phục policy cũ (CF giữ lịch sử audit log, có thể revert qua UI).

## Open question

- App nào lên CF Access tiếp theo quyết định có cần thêm group nào ngoài 3 group cơ bản ở trên không (vd `grp-care` riêng nếu CSKH cần policy khác Sales).
