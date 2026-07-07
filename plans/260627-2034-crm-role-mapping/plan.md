# Plan: CRM Role Mapping — Kiến trúc 2 tầng (CF Access + In-app Role)

**Date:** 2026-06-27 (rewrite 2026-07-07)
**Status:** pending
**Branch:** main
**Depends on:** plans/archive/260626-1712-cf-access-crm (CF Tunnel + Auth Layer — done)

## Mục tiêu

Chốt kiến trúc phân quyền 2 tầng cho toàn bộ app dùng chung Cloudflare Access + Lark OIDC (CRM là app đầu tiên, các app sau — Metabase, Dagster, Rill, Evidence — tái dùng tầng 1):

1. **Tầng 1 — CF Access (edge):** ai được VÀO app nào. Dùng claim `department`/`role` (Lark org-level) qua Access Groups + policy trên CF Zero Trust dashboard.
2. **Tầng 2 — In-app role (CRM):** làm gì TRONG app. JWT claim chỉ set default role lúc first-login; role sau đó do app tự sở hữu, đổi qua UI.

## Quyết định thiết kế

| Sự thật | Nơi sở hữu | Kênh truyền |
|---|---|---|
| Danh tính (email, open_id, tên) | Lark | JWT claim |
| Phòng ban, chức vụ org | Lark | JWT claim (mới, chưa load) |
| Vào được app nào | CF Access | Access Groups + policy |
| Role trong app | Từng app (CRM: SQLite `crm_app_user`) | JWT chỉ là default first-login |

**Phương án đã loại:**
- *Per-app `CF_ROLE_MAP` đầy đủ, tự tay điền cho N app*: map claim → role rải rác N env file, dễ stale, không audit trail khi đổi role.
- *Per-app role claim riêng từ IdP (vd `crm_role`)*: buộc IdP (repo ngoài) phải biết khái niệm từng app con; đổi quyền cần user re-login mới lấy claim mới.
- *Lark groups kiểu `app-crm-admin`*: làm bẩn org directory (Lark) bằng khái niệm chỉ 1 app cần.

Nguyên tắc giữ lại: IdP xác thực danh tính, app tự sở hữu role. `provision_or_sync` hiện tại đã đúng nửa sau (không bao giờ ghi đè role sau khi tạo — xem `crm/src/application/app_user_service.py:34-79`); phần thiếu là bootstrap admin đầu tiên + UI đổi role.

## Kiến trúc

```
Lark (danh tính + org role/dept)
   │ id_token claim: email, custom.department, custom.role (MỚI — Phase 1)
   ▼
CF Access (edge) ── Access Groups + Policy (Phase 2, thao tác dashboard)
   │ Cf-Access-Jwt-Assertion header
   ▼
CF Access Middleware (crm/src/adapters/inbound/http/cf_access_middleware.py)
   │ CF_ROLE_CLAIM=custom.department + CF_ROLE_MAP={...} → default role lúc first-login
   ▼
AppUserService.provision_or_sync (KHÔNG ghi đè role sau lần đầu)
   │
   ▼
CRM in-app role (crm_app_user.role) ── đổi qua Settings UI (Phase 3, admin-only)
```

## Phases

| Phase | Nội dung | Loại | Phụ thuộc |
|---|---|---|---|
| [Phase 1](phase-01-idp-claims.md) | Spec claim `department`/`role` cần IdP (repo ngoài) thêm vào id_token | External dependency | Không |
| [Phase 2](phase-02-cf-dashboard-config.md) | Khai báo OIDC claims + tạo Access Groups + gắn policy trên CF Zero Trust dashboard | Thao tác tay (dashboard) | Phase 1 (cần claim thật để test) |
| [Phase 3](phase-03-crm-role-management.md) | `CRM_ADMIN_EMAILS` bootstrap admin + UI quản lý user (đổi role/active) trong Settings + tests | Code (repo này) | **Không phụ thuộc Phase 1-2** — có thể làm song song |
| [Phase 4](phase-04-e2e-verification.md) | Verify end-to-end toàn bộ luồng | Checklist | Phase 1, 2, 3 |

Phase 3 độc lập vì `CRM_ADMIN_EMAILS` và UI đổi role không cần claim `department` mới — chỉ cần email đã login qua CF Access hiện tại (claim `role` cũ, map rỗng, mọi user fallback `sales`).

## Acceptance Criteria

- [ ] Phase 1: claim path xác nhận (`custom.department`, `custom.role`), verify được bằng jwt.io.
- [ ] Phase 2: CF Access Groups + policy áp cho CRM app, chặn user ngoài groups (403 ở edge, trước khi vào app).
- [ ] Phase 3: `CRM_ADMIN_EMAILS` bootstrap admin lần đầu; Settings → tab "Người dùng" đổi role/activate-deactivate có hiệu lực ngay, guard `require_admin`; tests pass.
- [ ] Phase 4: toàn bộ checklist verify pass trên `crm.fwg.vn`.

## Open questions

- Tên department thực tế Lark trả về là gì (tiếng Việt có dấu?) — cần Phase 1 xong mới điền `CF_ROLE_MAP` thật (xem phase-01).
- Elevate-to-admin cho user đã tồn tại nằm trong `CRM_ADMIN_EMAILS`: auto hay chỉ warning? Đề xuất mặc định: chỉ warning + đổi tay qua UI (xem phase-03, có thể đổi khi implement).
- App nào lên CF Access tiếp theo (Metabase/Dagster/Rill/Evidence?) — quyết định số lượng/thiết kế Access Groups cần tạo trước ở Phase 2 (nên tạo groups tái dùng được ngay từ đầu, không chỉ scope cho CRM).
