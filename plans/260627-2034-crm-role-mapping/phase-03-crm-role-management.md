# Phase 3 — CRM code: bootstrap admin + UI quản lý user (repo này)

**Loại:** Code, chạy trong Docker container `crm`.
**Phụ thuộc:** Không phụ thuộc Phase 1-2 (claim `department` mới). Dùng email hiện có từ CF Access JWT (`payload.email`) đã hoạt động qua claim `role` cũ.

## Context — hiện trạng đã đọc trong repo

- `crm/src/application/app_user_service.py:34-79` — `provision_or_sync` đã đúng: tạo user lần đầu với role từ middleware, **không bao giờ ghi đè role** ở các lần login sau (chỉ sync `full_name`, `lark_user_id`, `staff_id`).
- `crm/src/adapters/inbound/http/cf_access_middleware.py:128-139` — tính `crm_role` từ `CF_ROLE_MAP` (fallback `sales`), gọi `provision_or_sync(email, name, crm_role, lark_user_id=...)`. Đây là nơi cần chèn logic `CRM_ADMIN_EMAILS`.
- `crm/src/config.py:59-84` — các hàm đọc env `CF_ACCESS_AUDIENCE`, `CF_TEAM_DOMAIN`, `CF_ROLE_CLAIM`, `CF_ROLE_MAP`. Thêm hàm mới `cf_admin_emails()` theo cùng pattern.
- `crm/src/domain/entities/app_user.py:13-17` — 4 role hợp lệ: `ROLE_SALES="sales"`, `ROLE_CARE="care"`, `ROLE_MANAGER="manager"`, `ROLE_ADMIN="admin"`, list `VALID_ROLES`.
- `crm/src/adapters/outbound/sqlite/app_user_repository.py:84-105` — `update(user_id, **kwargs)` đã tồn tại, whitelist cột `{email, full_name, role, is_active, updated_at, lark_user_id, staff_id}` — **không cần thêm method DB mới**, chỉ cần gọi đúng kwargs.
- `crm/src/domain/ports/app_user_repository.py` — Protocol port hiện chỉ khai `get_by_email`, `list_active`. Cần thêm `update(self, user_id: str, **kwargs) -> None` vào Protocol để khớp interface.
- `crm/src/adapters/inbound/web/screens/management/screen_mgmt_settings.py:42-45` — `AppUsersSvc` Protocol hiện chỉ có `list_active`. Route hiện tại nhận `app_users_svc=sqlite_repos["app_user"]` (raw repo, xem `crm/src/composition.py:657`) — pattern hiện có là truyền thẳng repo, validate ở route handler (giống `_is_valid_hex_color` cho tag color). Giữ pattern này: thêm `update` vào Protocol, validate role tại route handler trước khi gọi `app_users_svc.update(...)`.
- `crm/src/adapters/inbound/web/templates/settings.html:87-110` — tab "Người dùng" **đã render sẵn** bảng user + dropdown role (`<select name="role">`), nhưng **KHÔNG có `hx-patch`/`hx-trigger`** — chỉ hiển thị, không submit. Cũng chưa có control activate/deactivate. Đây là phần UI cần hoàn thiện.
- `crm/src/tests/test_auth_dependency.py` — pattern test hiện có cho `require_admin` (mock `config.cf_access_audience`, `TestClient` với middleware inject `current_user`). Dùng làm mẫu cho test guard mới.
- `.env.compose.example:30-36` — section `[Cloudflare Access — CRM protection]`, thêm dòng `CRM_ADMIN_EMAILS=` vào đây.

## Requirements

1. **`CRM_ADMIN_EMAILS`** (env, comma-separated email, case-insensitive so sánh): email nằm trong list → provision với role `admin` lúc **first-provision**. Nếu user đã tồn tại với role khác `admin` → chỉ log warning, KHÔNG tự elevate (mặc định đề xuất — xem Open question ở `plan.md`; đổi tay qua UI Settings nếu cần elevate).
2. **UI quản lý user** trong Settings (`/settings?tab=users`), guard `require_admin`:
   - Đổi role qua dropdown 4 role (`sales`/`care`/`manager`/`admin`) — submit ngay khi đổi (HTMX `hx-patch` on `change`).
   - Activate/deactivate qua toggle/button.
   - Hiển thị email, tên, role, trạng thái (đã có sẵn), **thêm** cột/hành động cho activate-deactivate.
3. Route API mutation, cùng pattern các route settings khác trong file này (`dependencies=[Depends(require_admin)]`).
4. Tests cho: `CRM_ADMIN_EMAILS` bootstrap logic (middleware hoặc chỗ tính role), `update_role`/`set_active` (nếu thêm vào service) hoặc route handler validate + repo.update, và guard `require_admin` trên route mới.

## Files to modify/create

| File | Thay đổi |
|---|---|
| `crm/src/config.py` | Thêm `cf_admin_emails() -> set[str]` đọc `CRM_ADMIN_EMAILS`, parse comma-separated, lowercase, strip. |
| `crm/src/adapters/inbound/http/cf_access_middleware.py` | Trong `dispatch()` (khoảng dòng 128-139): sau khi tính `crm_role`, kiểm tra `email.lower() in self._admin_emails`. Nếu user chưa tồn tại (`self._user_svc._repo.get_by_email(email) is None` — hoặc thêm helper `exists_before` bằng cách check trước khi gọi `provision_or_sync`) → set `crm_role = ROLE_ADMIN` trước khi gọi `provision_or_sync`. Sau khi có `user` trả về, nếu `email.lower() in self._admin_emails and user.role != ROLE_ADMIN` → `log.warning(...)`. Thêm `self._admin_emails = cf_admin_emails()` trong `__init__`. |
| `crm/src/domain/ports/app_user_repository.py` | Thêm `def update(self, user_id: str, **kwargs: object) -> None: ...` vào Protocol `AppUserRepository`. |
| `crm/src/adapters/inbound/web/screens/management/screen_mgmt_settings.py` | Mở rộng `AppUsersSvc` Protocol thêm `update(self, user_id: str, **kwargs: object) -> None: ...`. Thêm 2 route: `PATCH /settings/users/{user_id}/role` (Form `role: str`, validate `role in VALID_ROLES` trước khi gọi `app_users_svc.update(user_id, role=role)`, trả `HX-Redirect` hoặc render lại row fragment) và `PATCH /settings/users/{user_id}/active` (Form `is_active: str` "true"/"false" → bool, gọi `app_users_svc.update(user_id, is_active=...)`). Cả 2 `dependencies=[Depends(require_admin)]`. Import `VALID_ROLES` từ `domain.entities.app_user`. |
| `crm/src/adapters/inbound/web/templates/settings.html` (dòng 96-108) | Thêm `hx-patch="/settings/users/{{ u.user_id }}/role"` + `hx-trigger="change"` + `hx-target` phù hợp (row hoặc toast) vào `<select name="role">`. Thêm cột hành động activate/deactivate (button `hx-patch=".../active"` toggle theo `u.is_active`, theo pattern nút hiện có trong file cho tag delete — `hx-confirm` nếu deactivate chính mình cần cân nhắc, xem Risks). |
| `crm/src/composition.py:657` | Không đổi nếu `sqlite_repos["app_user"]` (raw repo) đã có `update()` — repo `SQLiteAppUserRepository.update()` đã tồn tại (`crm/src/adapters/outbound/sqlite/app_user_repository.py:84`), chỉ cần Protocol khớp. |
| `.env.compose.example` (dòng 30-36) | Thêm `# CRM_ADMIN_EMAILS=` (comment, optional — unset = không có bootstrap admin nào ngoài role map). |
| `crm/src/tests/test_app_user_role_management.py` (mới) | Test route mutation: role hợp lệ → 200 + DB updated; role không hợp lệ → 400; guard `require_admin` chặn non-admin (dùng pattern `test_auth_dependency.py`); activate/deactivate cập nhật đúng cột. |
| `crm/src/tests/test_cf_access_middleware_admin_bootstrap.py` (mới, hoặc thêm vào file middleware test nếu đã có — kiểm tra trước) | Test: email trong `CRM_ADMIN_EMAILS` + user chưa tồn tại → provision role=admin; email trong list + user đã tồn tại role=sales → không đổi role, có log warning (dùng `caplog`). |

## Implementation steps

1. `config.py`: thêm `cf_admin_emails()`.
2. `cf_access_middleware.py`: đọc `self._admin_emails` trong `__init__`; sửa logic tính `crm_role` trước khi gọi `provision_or_sync`; thêm warning sau khi có `user`.
3. `domain/ports/app_user_repository.py`: thêm `update` vào Protocol.
4. `screen_mgmt_settings.py`: mở rộng `AppUsersSvc` Protocol, thêm 2 route mutation, import `VALID_ROLES`.
5. `settings.html`: wire `hx-patch` cho role select + thêm control activate/deactivate.
6. `.env.compose.example`: thêm dòng `CRM_ADMIN_EMAILS`.
7. Viết tests (mục Files to modify/create).
8. Chạy tests trong container (xem Validation).

## Validation

CRM code bind-mounted, KHÔNG rebuild — chỉ cần restart:

```bash
docker compose restart crm
```

Chạy tests trong container `crm` (theo memory: CRM tests chạy trong Docker container, không dùng venv host):

```bash
docker compose exec crm python -m pytest src/tests/test_app_user_role_management.py src/tests/test_auth_dependency.py -v
```

(Điền đúng tên file test middleware bootstrap sau khi tạo.)

Kiểm tra thủ công sau restart:
- [ ] Set `CRM_ADMIN_EMAILS=<email test>` trong `.env`, restart, login bằng email đó lần đầu → user tạo với role `admin`.
- [ ] Vào `/settings?tab=users`, đổi role user khác → DB cập nhật ngay, không cần re-login.
- [ ] Deactivate user → `is_active=0`, user đó login lại vẫn được tạo session nhưng nên xem xét có cần chặn login khi inactive (hiện `provision_or_sync` chỉ log warning cho inactive, không chặn — giữ hành vi hiện tại, không mở rộng scope).

## Risks & rollback

- **Risk:** admin tự đổi role của chính mình xuống non-admin hoặc tự deactivate → mất quyền vào `/settings`, không ai sửa lại qua UI. Cân nhắc chặn self-demote/self-deactivate ở route handler (so `user_id` với `request.state.current_user.user_id`) — quyết định cụ thể để lúc implement, không phải blocker cho việc viết plan.
- **Risk:** `CRM_ADMIN_EMAILS` sai chính tả email → không ai bootstrap được admin → phải sửa DB SQLite trực tiếp (`sqlite3 crm.db "UPDATE crm_app_user SET role='admin' WHERE email='...'"`) như phương án dự phòng.
- **Rollback:** revert các file trên qua git; không có migration DB mới (dùng cột `role`/`is_active` đã có sẵn) nên rollback code là đủ, không cần rollback schema.
