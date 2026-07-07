# Phase 4 — E2E verification

**Loại:** Checklist verify, không code (kế thừa "Bước 3" của plan cũ).
**Phụ thuộc:** Phase 1, 2, 3 đều xong (hoặc ít nhất Phase 3 xong để verify phần in-app role trước, Phase 1-2 xong để verify phần CF Access edge).

## Context

Verify trên `crm.fwg.vn` (production CF Tunnel domain, xem plan archive `260626-1712-cf-access-crm`). Có thể tách verify Phase 3 (in-app) trước khi Phase 1-2 (CF dashboard) hoàn tất, vì 2 phần độc lập.

## Checklist

### Phần in-app role (Phase 3, verify được ngay không cần chờ Phase 1-2)

- [ ] Admin (email trong `CRM_ADMIN_EMAILS`) login lần đầu → tự động tạo `AppUser` role=`admin`, vào được `/settings`.
- [ ] Non-admin login → `/settings` trả 403 (guard `require_admin` — `crm/src/adapters/inbound/http/auth_dependency.py:57-72`).
- [ ] Header hiển thị đúng tên user đang login (name sync qua `/profile/sync`, xem `cf_access_middleware.py:12-17`).
- [ ] `AppUser` mới được tạo trong SQLite (`crm_app_user` table) với đúng role default (hiện tại: theo `CF_ROLE_MAP` cũ hoặc `CRM_ADMIN_EMAILS`).
- [ ] Admin đổi role user khác qua UI Settings → có hiệu lực **ngay** ở lần request tiếp theo, KHÔNG cần user đó re-login (vì `provision_or_sync` đọc role từ DB, không phải JWT, ở các lần login sau).
- [ ] Admin deactivate user → hành vi theo quyết định ở Phase 3 (hiện tại: không chặn login, chỉ log warning — xác nhận đây là hành vi mong muốn hay cần chặn hẳn).

### Phần CF Access edge (Phase 1-2, cần claim `department` mới + Access Groups)

- [ ] Login bằng Lark admin account → CF Access cho qua (nằm trong `grp-admins`) → vào được app → CRM tạo/sync đúng role.
- [ ] Login bằng account KHÔNG thuộc group nào được cấp quyền → CF Access chặn **ở edge** (màn hình Cloudflare Access Denied), request không tới CRM container (kiểm tra CRM log không có entry cho email đó).
- [ ] JWT payload (`custom.department`, `custom.role`) đúng giá trị đã ghi nhận ở Phase 1.
- [ ] Default role theo department đúng như `CF_ROLE_MAP` đã điền (vd account phòng Sales → role `sales` lúc first-provision).

## Rollback nếu verify fail

- Fail ở phần in-app (Phase 3): rollback code theo Risks & rollback trong `phase-03-crm-role-management.md`.
- Fail ở phần CF edge (Phase 1-2): rollback policy/group trên CF dashboard theo `phase-02-cf-dashboard-config.md`, giữ nguyên policy cũ (email-list) làm fallback cho tới khi group mới verify xong.

## Open question

- Cách verify "CF Access chặn ở edge" chính xác nhất: dùng tab ẩn danh + tài khoản Lark test không thuộc group nào, tránh test bằng cách xóa quyền của chính người đang thao tác (rủi ro tự khóa mình khỏi dashboard).
