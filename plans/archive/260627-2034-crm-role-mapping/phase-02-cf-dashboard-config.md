# Phase 2 — CF Zero Trust dashboard config (thao tác tay, không code)

**Loại:** Thao tác dashboard trên Cloudflare Zero Trust — không có code thay đổi trong repo này.
**Phụ thuộc:** Phase 1 (cần biết giá trị claim thật để test policy đúng).

## Context

- CRM app đã có CF Access Application + Tunnel từ plan `plans/archive/260626-1712-cf-access-crm` (done).
- Middleware hiện tại (`crm/src/adapters/inbound/http/cf_access_middleware.py:8-11`) chỉ verify JWT audience/signature — KHÔNG check quyền vào app; việc chặn "ai được vào" là trách nhiệm của CF Access edge (policy), không phải code CRM.
- Claim đánh giá lúc authenticate/renew session — đổi policy/group không có hiệu lực real-time cho session đang mở, chỉ áp dụng lần login/renew tiếp theo.

## Requirements

**Cập nhật 2026-07-07:** claim thật là `departments`/`functional_roles` (array, plural) — không phải `department`/`role` số ít. Bước #1 (khai báo OIDC Claims) **đã làm xong** — `/debug/me` xác nhận thấy cả 2 field, giá trị thật (xem `phase-01-idp-claims.md` § Test result).

**Quyết định (2026-07-07, user):** KHÔNG gate CRM app hôm nay — mọi nhân viên Lark org vẫn login được vào `crm.fwg.vn` (khớp thiết kế app-layer hiện tại: phòng ban không map trong `CF_ROLE_MAP` chỉ fallback role `sales`, không bị từ chối truy cập). Việc hôm nay chỉ là **tạo sẵn 4 Access Groups tái dùng** cho app sau (Metabase/Dagster/Rill/Evidence) — KHÔNG gắn vào Policy của CRM app, nên **không có rủi ro tự khóa mình** (Group chỉ có hiệu lực khi được reference trong 1 Policy).

Taxonomy thật (từ `/debug/me`, xem `project_crm_lark_claims_departments_functional_roles` memory):
- departments: sales, sales-etc, sales-otc, marketing, kho-van, hr-admin, ky-thuat, design, ecom, tai-chinh-ke-toan, customer-care, sourcing, bod
- functional_roles: administration, finance, hr, it, bod, nv-kho, + pattern `truong-phong-<dept>` (head-of-department, không enumerate hết được)

## Implementation steps (chỉ tạo Groups, KHÔNG đổi Policy CRM)

1. Zero Trust dashboard → Access → Groups → **Add a group**. Với mỗi group dưới đây: đặt tên, Session duration mặc định, phần **Configure rules** → Include → chọn selector **"OIDC Claim"** → nhập claim key + value:

   | Group | Include rules (OR giữa các dòng) |
   |---|---|
   | `grp-admins` | OIDC Claim `departments` = `bod`  **OR**  OIDC Claim `functional_roles` = `bod` |
   | `grp-managers` | OIDC Claim `functional_roles` = `truong-phong-hanh-chinh`  **OR**  `truong-phong-tai-chinh` (thêm dòng mới mỗi khi có `truong-phong-*`/`head-of-*` giá trị mới — CF Access KHÔNG hỗ trợ prefix/wildcard match trên claim value, khác với code `CF_MANAGER_PREFIXES` tự match theo prefix) |
   | `grp-sales` | OIDC Claim `departments` = `sales`  **OR**  `sales-etc`  **OR**  `sales-otc`  **OR**  `ecom` |
   | `grp-care` | OIDC Claim `departments` = `customer-care` |

2. Save từng group. **KHÔNG** vào Access → Applications → CRM → Policies để đổi gì — giữ nguyên policy hiện tại (permissive).
3. (Optional, an toàn) Access → Applications → CRM → Policies → xác nhận Include hiện tại là "Everyone"/"Login Methods: Lark" (không có group nào bị exclude) — chỉ để xác nhận, không sửa.

## Validation

- [ ] Access → Groups → thấy đủ 4 group (`grp-admins`, `grp-managers`, `grp-sales`, `grp-care`) đã save.
- [ ] CRM app policy KHÔNG đổi — vẫn cho toàn bộ Lark org vào (test: 1 tài khoản bất kỳ chưa từng login vẫn vào được `crm.fwg.vn`, tạo `AppUser` role fallback `sales` nếu department không nằm trong `CF_ROLE_MAP`).
- [ ] Không cần test "chặn ở edge" (đã quyết định không gate hôm nay) — checklist tương ứng ở `phase-04-e2e-verification.md` được đánh dấu skip/deferred.

## Risks & rollback

- Rủi ro chính (sai policy khóa hết user) **không áp dụng** cho việc tạo Group đơn thuần — chỉ phát sinh khi sau này thật sự gắn group vào 1 Policy. Khi làm bước đó (tương lai): luôn giữ ít nhất 1 policy fallback bằng email cụ thể của người thao tác trước khi xóa policy cũ permissive.
- Rollback: xóa group vừa tạo (Access → Groups → Delete) — không ảnh hưởng app nào vì chưa được reference.

## Open question

- Khi nào thật sự cần gate CRM/app khác theo group (thay vì permissive + role fallback trong app)? Để dành quyết định này cho lúc có nhu cầu cụ thể (vd thêm app không muốn toàn bộ org vào).
- App nào lên CF Access tiếp theo quyết định có cần thêm group nào ngoài 4 group cơ bản ở trên không.

## Kết quả (2026-07-07)

4 group đã tạo (`grp-admins`, `grp-managers`, `grp-sales`, `grp-care`), KHÔNG gắn vào Policy nào — hiện tại không có tác dụng gì (đúng như thiết kế, group chỉ có hiệu lực khi được reference). Có thảo luận việc này hơi trái YAGNI (tạo trước khi có app thứ 2 thật sự cần) — quyết định: **giữ nguyên**, không hại gì vì chưa gắn policy, dùng khi có app/nhu cầu gate cụ thể. Phase 2 coi như **done**.
