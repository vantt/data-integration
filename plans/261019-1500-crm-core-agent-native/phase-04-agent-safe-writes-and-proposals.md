# Phase 4: agent ghi an toàn và mô hình đề xuất → người duyệt

**Effort:** 5.5d · **Phụ thuộc:** phase 3; Q4 đã chốt 19/10 (manager và admin duyệt, hết hạn 7 ngày) · **Đụng prod:** có (CRM) · **Cần user duyệt giờ:** có · **Migration:** 0055–0059

## Bối cảnh

- Đường ghi kết quả tiếp xúc đã có một executor side-effects duy nhất (`crm/src/application/activity_side_effects.py`, `activity_service.py`): giữ nguyên, agent phải đi qua đúng đường này.
- Task đã idempotent theo `source_ref` (R8, `0037_task_source_ref_active_only_uniqueness.up.sql`); action state theo `action_id` và dismiss TTL (R15, `0038`, `0046`).
- Merge đã có snapshot undo (`merge_service.py:52-115`); dedup candidate có trạng thái `pending/merged/rejected`.
- Web UI ghi trực tiếp qua service, chưa qua bus, nên chưa có audit cho người dùng web (phase 2 chỉ nối route API và admin).

## Yêu cầu

1. **Migration `0055_proposal`:** bảng `crm_proposal` theo design §5.5; index (`status`, `proposed_at`), (`party_id`).
2. **Lệnh ghi an toàn** (`crm/src/application/commands/`), mỗi lệnh có tên ổn định và quyền: `interaction.log`, `task.create`, `task.update`, `note.add`, `party_tags.set`, `action_state.update`. Handler gọi service hiện có; không viết lại logic.
3. **Lệnh đề xuất:** `proposal.create` cho các loại `identity_link`, `merge`, `consent_change`, `bulk_operation`. Mỗi loại có:
   - `validate(payload)`, `preview(payload) -> preview_json` (chạy thử trong transaction rồi rollback, hoặc tính diff không ghi);
   - `apply(payload, ctx_người_duyệt)` gọi lệnh thật qua bus.
   - Executor tạm: `identity_link` ghi vào `crm_party_identity` qua repository hiện có (phase 6 đổi sang bảng mới, không đổi giao diện); `consent_change` ghi `consent_enum` cũ và bắt buộc bằng chứng nằm trong proposal và audit (phase 7 đổi sang sổ cái); `merge` gọi `MergeService.merge`; `bulk_operation` hỗ trợ gắn/bỏ tag không nhạy cảm, tạo task, chuyển `owner_user_id`, tối đa 2.000 party.
   - `proposal.approve` / `proposal.reject` / `proposal.cancel` (người đề xuất huỷ); hết hạn sau 7 ngày (đánh dấu ở cuối `/admin/refresh`). Duyệt kiểm lại preview: nếu khác preview lúc đề xuất thì trả `preview_changed` và yêu cầu duyệt lại.
4. **Quy tắc theo kênh** (design §5.5 bảng): agent chỉ được `proposal.create` cho merge, identity, consent, hàng loạt; người có quyền làm trực tiếp như hôm nay; thao tác hàng loạt > 200 party từ người cũng phải qua đề xuất (người dùng hiện không có thao tác hàng loạt nào trên UI ngoài bulk-resolve outcome; xác nhận ở phase 0, nếu có thì giữ nguyên hành vi).
5. **REST v1 ghi:** `POST /api/v1/parties/{id}/interactions`, `POST/PATCH /api/v1/tasks`, `POST /api/v1/parties/{id}/notes`, `PUT /api/v1/parties/{id}/tags`, `POST /api/v1/actions/{action_id}/state`, `POST /api/v1/proposals`, `GET /api/v1/proposals`, `GET /api/v1/proposals/{id}`, `POST /api/v1/proposals/{id}/approve|reject|cancel`. Header `Idempotency-Key` bắt buộc với POST/PUT/PATCH của agent.
6. **MCP code mode:** đánh dấu `x-agent-function` (loại `write` hoặc `propose`) trên các route ở yêu cầu 5 để có hàm số 10–19 và 21 của design §5.9.4 (`proposals_get`, `proposals_list_mine`, 6 hàm ghi, `proposals_identity_link`, `proposals_merge`, `proposals_consent_change`, `proposals_bulk_operation`); số 20 (`proposals_party_relationship`) thêm ở phase 8. Không phải sửa thư viện hay MCP server của CRM: server đọc lại OpenAPI khi khởi động lại (`docker restart crm_codemode`). **Không thêm tool MCP**: hàm ghi chạy trong `execute` và đi qua đúng route REST v1, đúng lệnh CommandBus, đúng đề xuất như khi gọi REST trực tiếp. Hàm ghi nhận `idempotency_key`; nếu code không truyền, thư viện điền khoá tất định, CRM vẫn bắt buộc header `Idempotency-Key` với lệnh ghi của agent. CRM cưỡng chế tối đa 20 lệnh ghi mỗi `execution_id` (vượt → `use_bulk_proposal`) và giới hạn thấp hơn cho `agent_kind='chat'` (design §5.9.3). Không có hàm duyệt; `whoami` và `search_api` không liệt kê hàm principal không có quyền.
7. **CLI:** lệnh ghi và `proposals list|show|approve|reject` (chỉ credential `principal_type='human'` có quyền `proposal.approve` mới duyệt được; credential người dùng tạo bằng `credential_admin` với `--type human`).
8. **Màn hình "Hàng chờ duyệt"** (surface ID mới theo `crm/docs/ui-spec/00-overview.md`): danh sách đề xuất `pending`, xem lý do, bằng chứng, preview diff, nút duyệt/từ chối có ghi chú; badge số đề xuất chờ trên menu cho manager/admin.
9. **Web UI ghi qua bus:** mọi handler web có lệnh ghi (danh sách phase 0) lấy ctx từ `request.state.ctx` và gọi qua `CommandBus.run`, để người dùng web cũng có audit. Không đổi giao diện, mã trả về, fragment HTMX.
10. Rate limit: 30 lệnh ghi/phút và 20 đề xuất/giờ mỗi credential agent (cấu hình).

## File

- Tạo: migration `0055_proposal.{up,down}.sql`; `crm/src/application/commands/*.py`, `crm/src/application/proposal_service.py`, `crm/src/domain/entities/proposal.py`, `crm/src/domain/ports/proposal_repository.py`, `crm/src/adapters/outbound/sqlite/proposal_repository.py`; route v1 ghi có `x-agent-function`; screen review queue + template; test.
- Sửa: các handler web có lệnh ghi (khoảng 30 route; danh sách đủ từ phase 0), `crm/ops/crmctl.py`, `crm/src/composition.py`, `crm/docs/ui-spec/00-overview.md` (đăng ký surface mới), `crm/docs/agent-access.md`.

## Các bước

1. Worktree `feat/crm-agent-writes-proposals`.
2. Migration + repository + `ProposalService` + test vòng đời.
3. Lệnh ghi an toàn + REST v1 + `x-agent-function` + giới hạn ghi theo `execution_id` + test idempotency.
4. Bốn loại đề xuất, preview và apply + test.
5. Chuyển handler web sang bus theo từng nhóm màn hình; sau mỗi nhóm chạy test màn hình tương ứng.
6. Screen review queue.
7. Parity + toàn bộ test; thử thật với Claude Desktop trên bản sao: ghi một kết quả cuộc gọi, đề xuất một merge, duyệt bằng UI.
8. Deploy (backup vì có migration), giờ user duyệt.

## Test

| Mức | Nội dung |
|---|---|
| Unit | Gửi cùng `idempotency_key` 3 lần → 1 activity, 1 task; cùng key khác body → 409 |
| Unit | Agent gọi merge trực tiếp (qua REST v1 ghi) → 403; `proposals_merge()` trong `execute` (hoặc `POST /api/v1/proposals`) → proposal `pending`, 0 thay đổi bảng party/identity; duyệt bởi manager → merge xảy ra, audit có `proposal_id` và actor là manager |
| Unit | Preview thay đổi giữa lúc đề xuất và lúc duyệt → `preview_changed` |
| Unit | Đề xuất hàng loạt: chạy thử trả đúng số party, mẫu ≤ 20, không ghi; vượt 2.000 → từ chối |
| Unit | Consent qua đề xuất thiếu bằng chứng → từ chối |
| Unit | Tag nhạy cảm qua `parties_set_tags` → từ chối kể cả khi khách đã đồng ý riêng; tag `product_interest` → được; đề xuất hàng loạt gắn tag nhạy cảm → từ chối ngay khi tạo |
| Tích hợp | Mọi test màn hình web hiện có xanh (fragment HTMX, mã trả về); mỗi lệnh ghi web có đúng một audit `channel='web'` |
| Tích hợp | Bộ kịch bản agent thêm 10 câu ghi/đề xuất chạy qua `execute` |
| Tích hợp (code mode, sidecar của CRM) | Code gọi `interactions_log` 21 lần trong một lần chạy → 20 bản ghi rồi lỗi `use_bulk_proposal`; chạy lại cùng đoạn code → 0 bản ghi mới (khoá tất định); không có hàm merge thực thi để gọi, gọi REST merge bằng token con → 403; mọi lệnh ghi qua code có audit kèm `execution_id` và `mcp.execute` liệt kê chúng; credential `chat` bị chặn ở lệnh ghi thứ 6 |
| Tích hợp | Bộ 25 tác vụ của phase 3 mở rộng thêm 10 tác vụ ghi/đề xuất; đo tỷ lệ code đúng lần đầu cho cả bộ |

## Kiểm "CRM như cũ"

- `parity_snapshot diff` sau khi **chạy cùng một chuỗi thao tác web giả lập** (script trong test tích hợp: ghi hoạt động, tạo task, gắn tag, claim, snooze) trên hai bản sao (code cũ và code mới): trạng thái các bảng nghiệp vụ giống hệt, chỉ khác bảng `crm_audit_event`, `crm_idempotency_record`.
- `crm_export_parity.py`: 11 bảng giống hệt.
- Sau deploy: một người dùng thật ghi một cuộc gọi trên call cockpit, gắn một tag; kiểm thấy audit `channel='web'` tương ứng; nightly export xanh.

## Đụng prod và duyệt

Có (migration, khởi động lại CRM, thêm màn hình mới cho manager/admin). Cần user duyệt giờ.

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Chuyển 30 handler web sang bus làm vỡ một màn hình | Trung bình × Trung bình | Chuyển theo nhóm, test màn hình hiện có; chuỗi thao tác giả lập so trạng thái |
| Agent tạo nhiều đề xuất rác | Trung bình × Thấp | Rate limit; hết hạn 7 ngày; người đề xuất huỷ được |
| Agent dùng vòng lặp trong code để làm việc hàng loạt, né đề xuất | Trung bình × Cao | Giới hạn 20 lệnh ghi mỗi lần chạy và 30 lệnh ghi/phút mỗi credential ở server; việc lớn hơn chỉ qua `bulkOperation` |
| Người duyệt bấm duyệt không đọc | Trung bình × Trung bình | Preview diff rõ, bằng chứng hiển thị bắt buộc; merge vẫn undo được |

## Rollback

`docker stop crm`, `git revert`, `migration_down.py` 0055 (đề xuất đang chờ mất; báo người dùng), `docker start crm`. Thu hồi credential agent nếu cần dừng ngay mà không rollback code.
