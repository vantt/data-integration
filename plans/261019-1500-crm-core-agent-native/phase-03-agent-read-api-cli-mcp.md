# Phase 3: agent đọc qua REST v1, CLI và MCP code mode (code-mode host dùng chung + Monty)

**Effort:** 5d · **Phụ thuộc:** phase 2; **plan [`261020-1310-agent-codemode-host`](../261020-1310-agent-codemode-host/plan.md) đã phát hành bản đầu (qua cổng quyết định phase 0 của plan đó, có tag phiên bản và image)**; Q2, Q8 đã chốt (che SĐT và tên; LAN + Tailscale qua Caddy); code mode đã chốt 19/10 16:13; Monty + host repo riêng đã chốt 20/10 ~13:10 · **Đụng prod:** có (CRM restart, thêm service `crm_codemode`, route Caddy) · **Cần user duyệt giờ:** có · **Migration:** không

## Bối cảnh

- Đã có khoảng 40 route `/api/*` nhưng không có hợp đồng ổn định (không version, lỗi không thống nhất, nhiều route trả HTML cho HTMX như `screen_customer_360_activity.py:644,707`). FastAPI đã sinh OpenAPI ở `/api/docs` (`crm/src/composition.py:208`).
- **MCP theo code mode** (design §5.9): server chỉ lộ `search_api` và `execute`. Server là **code-mode host** dùng chung (repo riêng, Python, runner Pydantic Monty, agent viết Python tập con), chạy ở container sidecar `crm_codemode`. Mỗi hàm agent gọi là một route REST `/api/v1` có đánh dấu `x-agent-function`; CRM chỉ **khai báo**, mọi policy ở CommandBus/query service.
- Vì host ở sidecar và gọi REST, **image `crm` không phải build lại** ở phase này (không thêm MCP SDK hay runtime nào vào CRM).
- Phase này chỉ có hàm đọc (số 1–9 ở design §5.9.4); hàm ghi và đề xuất ở phase 4.
- Research CEO MCP đã chốt: Claude Desktop và bot Lark; dữ liệu hằng đêm đủ; "lợi nhuận" mặc định CM2. MCP phân tích dùng cùng code-mode host (design §5.10).

## Yêu cầu

1. **Query service** dưới `crm/src/application/queries/` (nhận port, trả DTO Pydantic dùng chung cho REST, CLI và qua đó cho code mode):
   - `PartyQuery.search(q, filters, limit, cursor)`, `PartyQuery.get_360(party_id)`;
   - `TimelineQuery.list(party_id, kinds, limit, cursor)` (tương tác, ghi chú, task, đơn từ cache);
   - `WorklistQuery.list(assignee, date, limit)` (bọc `WorklistQueryService` hiện có, không viết lại xếp hạng);
   - `TaskQuery.list(filters)`; `ApproachScriptQuery.get(party_id)` (giữ cảnh báo R14);
   - `SegmentQuery.members(segment_id, limit, cursor)`; `CampaignQuery.results(campaign_id)` (ROI hiện có; lift ở phase 10);
   - `WhoAmIQuery` (principal, `on_behalf_of`, `agent_kind`, quyền hiệu lực, **danh sách tên hàm agent được phép**, module bật, `data_as_of` từ `wh_sync_run`).
2. **Chính sách hiển thị PII** (`crm/src/domain/policy.py`, `present_party(dto, ctx)`), cưỡng chế ở CRM:
   - Agent: SĐT luôn che dạng `09x****123`; tên luôn che (chữ cái đầu mỗi từ + mã khách); địa chỉ chỉ tỉnh/thành; ngày sinh chỉ năm.
   - Người dùng: như hiện nay.
   - Trường và tag `data_class='sensitive'` (kể cả tag sức khoẻ của khách đã đồng ý riêng): người dùng theo `can_view_sensitive`; **agent không bao giờ nhận**, kể cả số lượng hay trạng thái đồng ý `sensitive_profile`. Tag `product_interest` là tag thường.
3. **REST `/api/v1`** (`crm/src/adapters/inbound/api_v1/`): `GET /api/v1/whoami`, `/parties?q=`, `/parties/{id}`, `/parties/{id}/timeline`, `/worklist`, `/parties/{id}/approach-script`, `/tasks`, `/segments/{id}/members`, `/campaigns/{id}/results`. Phong bì `{data, data_as_of, warnings, request_id}`; lỗi theo design §5.7 (thông điệp không chứa PII); phân trang cursor; mọi lời gọi của agent ghi audit qua `CommandBus.read`, kèm `execution_id` khi đến bằng token con. Route cũ không đổi.
4. **Khai báo danh mục hàm cho agent:** mỗi route ở yêu cầu 3 có `openapi_extra={"x-agent-function": {"name": ..., "group": ..., "kind": "read"}}` và mô tả tiếng Việt (docstring của stub); OpenAPI có `info.x-agent-catalog-version` (bắt đầu `1`). Test: mọi route `x-agent-function` có tên duy nhất, có mô tả, có model input/output; route không đánh dấu thì không thành hàm.
5. **Vòng đời một lần chạy** (design §5.9.2):
   - `POST /api/v1/agent-executions` (chỉ credential `principal_type='agent'`, scope `mcp`): nhận hash SHA-256 và độ dài code, sinh `execution_id` (UUIDv7) và token con ngẫu nhiên (`secrets.token_urlsafe(32)`) **giữ trong bộ nhớ process CRM** (ánh xạ token → credential cha, principal, `on_behalf_of`, `execution_id`, hết hạn 60 giây; không ghi DB); ghi audit `mcp.execute.start`.
   - `POST /api/v1/agent-executions/{id}/finish` (token con): nhận outcome, thời gian, kích thước kết quả; thu hồi token con; ghi audit `mcp.execute` với danh sách lệnh tra theo `execution_id`. Token con hết hạn mà chưa `finish` thì CRM tự đóng với outcome `abandoned`.
   - Middleware REST v1 đếm lời gọi và lệnh ghi theo `execution_id` (200 lời gọi; giới hạn ghi ở phase 4); token con không có quyền nhiều hơn credential cha; token con không gọi được `agent-executions` để tạo lần chạy mới.
6. **Service `crm_codemode`** trong `docker-compose.yml`:
   - Image dựng bằng `Dockerfile.crm_codemode` (ở gốc repo, như các Dockerfile khác): cài code-mode host **theo tag git đã ghim kèm hash** (hoặc kéo image do repo host phát hành theo digest); không có code CRM trong image.
   - Cấu hình bằng biến môi trường: URL OpenAPI và API của CRM (`http://crm:8090/api/v1`), giới hạn (design §5.9.2 bảng giới hạn), cổng MCP; `mem_limit` theo số đo của plan host (đề xuất 384 MiB), `pids_limit`, `read_only: true`, `tmpfs` nhỏ, `cap_drop: [ALL]`, không mount volume dữ liệu nào, cùng mạng docker với `crm`.
   - Credential agent đi kèm từng request MCP (Bearer), host chuyển tiếp cho CRM; host không giữ secret nào của CRM.
   - Healthcheck: host đọc được OpenAPI và `x-agent-catalog-version` nằm trong dải hỗ trợ.
7. **Kênh mạng (đã chốt Q8):** route Caddy LAN + Tailscale `/mcp` tới `crm_codemode`, `/api/v1` tới `crm:8090` (theo mẫu report site Evidence), không qua Cloudflare Tunnel; CSRF không ảnh hưởng vì client không gửi Origin. Tài liệu kết nối Claude Desktop (`mcp-remote`) ở `crm/docs/agent-access.md`.
8. **CLI** `crm/ops/crmctl.py`: nhóm lệnh đọc tương ứng (design §5.8), gọi `/api/v1`, `--json`; đọc `CRM_URL`, `CRM_TOKEN` từ môi trường.
9. **Credential đầu tiên:** `agent:claude_desktop_ceo` (`agent_kind='assistant'`, bound user = CEO, scope `mcp,read`), và `agent:claude_desktop_<người thực thi>` để thử.
10. **Bộ 25 tác vụ CRM** tiếng Việt (ví dụ "Hôm nay tôi nên gọi ai?", "5 khách đáng giá nhất trong worklist chưa liên hệ 30 ngày, kèm sản phẩm gần nhất", "Chiến dịch X ra sao?") lưu ở `crm/src/tests/agent_scenarios/`: mỗi tác vụ có câu hỏi, đoạn code Python mẫu (tập con Monty) và kết quả mong đợi trên fixture giả. Hai cách dùng: (a) test tự động chạy code mẫu qua host (image đã ghim) trên CRM fixture, quét kết quả: không SĐT, không tên đầy đủ, không tag/trường nhạy cảm (fixture có khách đã đồng ý riêng và có tag sức khoẻ), có `data_as_of`; (b) đo **tỷ lệ code chạy đúng lần đầu** khi model đang dùng tự viết code từ câu hỏi (chạy bằng harness của plan host, ghi số lần thử lại).
11. **Đo token** (tiêu chí chấp nhận của plan): (a) định nghĩa tool + `instructions` của server so với ước lượng 21 tool riêng (sinh tạm JSON schema của 21 thao tác từ OpenAPI chỉ để đếm); (b) với 10 tác vụ, tổng byte REST mà host nhận so với byte kết quả trả về model. Ghi số vào `crm/docs/agent-access.md`.
12. ADR-020 cập nhật: code mode, host dùng chung + Monty, sidecar gọi REST, ranh giới cưỡng chế, cách ghim phiên bản.

## File

- Tạo: `crm/src/application/queries/*.py`, `crm/src/adapters/inbound/api_v1/*.py` (gồm `agent_executions.py`), `crm/ops/crmctl.py`, `crm/docs/agent-access.md`, `Dockerfile.crm_codemode`, test (`test_api_v1_read.py`, `test_agent_function_catalog.py`, `test_agent_executions.py`, `test_pii_presentation.py`, `agent_scenarios/`).
- Sửa: `crm/src/domain/policy.py`, `crm/src/composition.py` (đăng ký router), `docker-compose.yml` (service `crm_codemode`), cấu hình Caddy, `crm/AGENTS.md` (nơi đặt query service; route agent phải có `x-agent-function`; đổi chữ ký route agent là đổi hợp đồng, tăng `x-agent-catalog-version` khi phá tương thích), `crm/README.md`, ADR-020.

## Các bước

1. Worktree `feat/crm-agent-read`.
2. Query service + test trên fixture (so với đường đọc hiện có của UI để không lệch).
3. Chính sách PII + test.
4. REST v1 + `x-agent-function` + OpenAPI; CLI.
5. Vòng đời lần chạy (`agent-executions`, token con, đếm lời gọi) + test.
6. `Dockerfile.crm_codemode` ghim phiên bản host; service compose; chạy host với CRM trên bản sao trong scratch.
7. Bộ 25 tác vụ: chạy code mẫu (a); đo tỷ lệ đúng lần đầu (b); đo token.
8. Thử thật trên bản sao: Claude Desktop của người thực thi nối qua `mcp-remote`, 10 tác vụ.
9. Deploy giờ user duyệt: merge, `docker restart crm` (code bind-mount, không build lại `crm`), `docker compose up -d crm_codemode` (build image sidecar trước), route Caddy.
10. Chạy song song có người theo dõi 1 tuần: đọc audit `mcp.execute` hằng ngày (hash code, lệnh đã gọi); CEO dùng thử.

## Test

| Mức | Nội dung |
|---|---|
| Unit | Mỗi query trả cùng nội dung với đường đọc hiện có của UI trên fixture (360, worklist, timeline) |
| Unit | PII: agent không bao giờ nhận SĐT, tên đầy đủ, ngày sinh đủ, địa chỉ chi tiết, trường/tag nhạy cảm; người dùng nhận như cũ |
| Unit | Danh mục: tên hàm duy nhất, có mô tả; `whoami` của agent chỉ liệt kê hàm được phép |
| Unit | Token con: hết hạn sau 60 giây; bị thu hồi khi `finish`; dùng lại sau `finish` → 401; không gọi được `agent-executions`; quyền không vượt credential cha; 201 lời gọi trong một `execution_id` → `execution_call_limit`; mỗi lời gọi có audit kèm `execution_id`; mỗi lần chạy có đúng một `mcp.execute` |
| Tích hợp | Host (image ghim) + CRM fixture: 25 tác vụ code mẫu chạy đúng; kết quả không có PII hay dữ liệu nhạy cảm; lỗi trả về không chứa stack hay body request |
| Tích hợp | Host không gọi được gì ngoài CRM: hàm host duy nhất là route có `x-agent-function` (kiểm danh sách hàm host đăng ký bằng `/whoami` và stub) |
| Thủ công | Claude Desktop trả lời được 10 tác vụ, mỗi câu có "dữ liệu tới" |

Bài kiểm sandbox (vòng lặp, ăn RAM, đệ quy, thoát file/mạng, kết quả khổng lồ) thuộc plan host; phase này chỉ chạy lại bộ kiểm "khói" của host trên image đã ghim.

## Kiểm "CRM như cũ"

- Phase chỉ thêm route, thêm service sidecar, thêm route Caddy; image `crm` không đổi. `parity_snapshot diff`: chỉ khác số dòng `crm_audit_event` (nếu chạy thử trên bản sao); mọi hash khác giữ nguyên.
- RAM: `docker stats` của `crm` không đổi đáng kể; `crm_codemode` nằm trong `mem_limit` của nó.
- Sau deploy: UI, `/admin/refresh`, nightly export như phase trước; route cũ `/api/*` trả như cũ (gọi thử `GET /api/parties/{id}/360` bằng token cũ). Dừng `crm_codemode` thì CRM vẫn chạy bình thường (chỉ mất MCP).

## Đụng prod và duyệt

Có: restart CRM, thêm service `crm_codemode`, route Caddy. Cần user duyệt giờ.

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Plan host trễ hoặc Monty trượt cổng quyết định | Trung bình × Trung bình | REST v1, `x-agent-function`, vòng đời lần chạy làm trước được; host dùng runner dự phòng `quickjs-rs` sau cùng interface (agent viết JS thay Python, CRM không đổi) |
| Code độc hoặc vòng lặp (kể cả do prompt injection trong dữ liệu khách) | Trung bình × Trung bình | Sandbox Monty không có file/mạng; giới hạn ở host và đếm theo `execution_id` ở CRM; sidecar có `mem_limit`; mọi policy ở CRM |
| Host bị chiếm quyền | Thấp × Trung bình | Host chỉ có token agent của từng request (quyền hẹp), không mount dữ liệu, `cap_drop ALL`, `read_only`; CRM không tin host (giới hạn cưỡng chế lại) |
| Lộ dữ liệu qua lỗi hoặc log | Thấp × Trung bình | Thông điệp lỗi REST không chứa PII; host che PII ở đầu ra; cắt kích thước |
| Danh mục hàm lệch giữa CRM và host | Thấp × Trung bình | Host sinh từ OpenAPI lúc khởi động; `x-agent-catalog-version` kiểm dải |
| Model viết Python tập con sai (kế thừa class, generator) | Trung bình × Thấp | Stub có kiểu và type-check của Monty trước khi chạy; `instructions` nêu giới hạn; đo tỷ lệ đúng lần đầu |
| Mở `/mcp` ra ngoài ý muốn | Thấp × Cao | Chỉ qua LAN/Tailscale; Cloudflare Tunnel không route `/mcp`, `/api/v1` |

## Rollback

`docker compose stop crm_codemode` (MCP tắt ngay, CRM không ảnh hưởng); `git revert` phạm vi đã deploy, `docker restart crm`; gỡ service khỏi compose và route Caddy; thu hồi credential (`credential_admin revoke`). Không có thay đổi dữ liệu cần dọn.
