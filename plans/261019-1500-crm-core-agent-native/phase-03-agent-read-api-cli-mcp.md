# Phase 3: agent đọc qua REST v1, CLI và MCP code mode

**Effort:** 6.5d · **Phụ thuộc:** phase 2; phase 0 (kiểm Deno, RAM, MCP SDK); Q2 và Q8 đã chốt 19/10 (che SĐT và tên; LAN + Tailscale qua Caddy); code mode đã chốt 19/10 16:13 · **Đụng prod:** có (CRM, build lại image) · **Cần user duyệt giờ:** có · **Migration:** không

## Bối cảnh

- Đã có khoảng 40 route `/api/*` nhưng không có hợp đồng ổn định (không version, lỗi không thống nhất, nhiều route trả HTML cho HTMX như `screen_customer_360_activity.py:644,707`).
- FastAPI đã sinh OpenAPI ở `/api/docs` (`crm/src/composition.py:208`).
- Thư viện nằm trong image (`crm/src/requirements.txt`), nên thêm MCP SDK và Deno phải build lại image; image hiện build ngày 10/08 từ `python:3.12-slim` không ghim digest (`Dockerfile.crm:4`).
- **MCP theo code mode** (design §5.9): server chỉ lộ `search_api` và `execute`; code TypeScript của agent chạy trong sandbox Deno, gọi SDK có kiểu sinh từ OpenAPI `/api/v1`; SDK chỉ gọi được REST nội bộ bằng token con của principal agent. Mọi policy nằm ở CommandBus/query service, không ở sandbox. Phase này chỉ có hàm SDK đọc; hàm ghi và đề xuất ở phase 4.
- MCP server chạy trong cùng process CRM (SQLite một writer); sandbox là subprocess không mở DB.
- Research CEO MCP đã chốt: Claude Desktop và bot Lark; dữ liệu hằng đêm đủ; "lợi nhuận" mặc định CM2 và luôn nêu bậc. MCP phân tích được đề xuất dùng cùng code mode (design §5.10).

## Yêu cầu

1. **Query service** dưới `crm/src/application/queries/` (nhận port, trả DTO Pydantic dùng chung cho REST, CLI, SDK):
   - `PartyQuery.search(q, filters, limit, cursor)`, `PartyQuery.get_360(party_id)`;
   - `TimelineQuery.list(party_id, kinds, limit, cursor)` (tương tác, ghi chú, task, đơn từ cache);
   - `WorklistQuery.list(assignee, date, limit)` (bọc `WorklistQueryService` hiện có, không viết lại xếp hạng);
   - `TaskQuery.list(filters)`; `ApproachScriptQuery.get(party_id)` (giữ cảnh báo R14);
   - `SegmentQuery.members(segment_id, limit, cursor)`; `CampaignQuery.results(campaign_id)` (ROI hiện có; lift ở phase 10);
   - `WhoAmIQuery` (principal, `on_behalf_of`, quyền hiệu lực, module bật, `data_as_of` từ `wh_sync_run`).
2. **Chính sách hiển thị PII** (`crm/src/domain/policy.py`, `present_party(dto, ctx)`), cưỡng chế ở server:
   - Agent: SĐT luôn che dạng `09x****123`; tên luôn che (chữ cái đầu mỗi từ + mã khách; `CRM_AGENT_PII_MODE` chỉ nhận `masked` ở v1); địa chỉ chỉ tỉnh/thành; ngày sinh chỉ năm.
   - Người dùng: như hiện nay.
   - Trường và tag `data_class='sensitive'` (kể cả tag sức khoẻ của khách đã đồng ý riêng): người dùng theo `can_view_sensitive`; **agent không bao giờ nhận**, kể cả số lượng hay trạng thái đồng ý `sensitive_profile`. Tag `product_interest` là tag thường, agent nhận được.
3. **REST `/api/v1`** (`crm/src/adapters/inbound/api_v1/`): `GET /api/v1/whoami`, `/parties?q=`, `/parties/{id}`, `/parties/{id}/timeline`, `/worklist`, `/parties/{id}/approach-script`, `/tasks`, `/segments/{id}/members`, `/campaigns/{id}/results`. Phong bì `{data, data_as_of, warnings, request_id}`; lỗi theo design §5.7 (thông điệp không chứa PII); phân trang cursor; mọi lời gọi của agent ghi audit qua `CommandBus.read`, kèm `execution_id` khi đến từ sandbox. Mỗi operation có `operationId` ổn định và mô tả tiếng Việt (nguồn của JSDoc trong SDK). Route cũ không đổi.
4. **SDK TypeScript** `crm/src/adapters/inbound/mcp/sdk/crm_sdk.ts`:
   - Sinh từ OpenAPI `/api/v1` bằng script `crm/ops/generate_mcp_sdk.py` (đọc `app.openapi()`, sinh kiểu và hàm theo nhóm `crm.parties`, `crm.worklist`, `crm.tasks`, `crm.segments`, `crm.campaigns`, `crm.approachScripts`, `crm.whoami`); client `fetch` mỏng tự viết, **không phụ thuộc gói ngoài**; đọc base URL và token con từ tham số khởi tạo (không đọc env).
   - Thêm header `Authorization: Bearer <token con>` và `X-CRM-Execution-Id`; ném lỗi có kiểu (`CrmApiError{code, message, status, request_id}`).
   - File sinh ra được commit; test sinh lại và so (lệch là fail).
   - Danh mục hàm và ngữ nghĩa: design §5.9.3 (số 1–9 ở phase này).
5. **Chỉ mục `search_api`**: sinh từ cùng file SDK (mỗi hàm: tên, chữ ký, kiểu liên quan, JSDoc tiếng Việt, quyền cần); tìm theo từ khoá tiếng Việt có/không dấu và tiếng Anh, điểm theo tên và mô tả; trả tối đa 5 mục, khoảng 2.000 token; **lọc theo quyền hiệu lực của principal**.
6. **Sandbox runner** `crm/src/adapters/inbound/mcp/sandbox.py` (runtime theo kết luận phase 0; đề xuất Deno, design §5.9.2):
   - Mỗi `execute`: sinh `execution_id` (UUIDv7); tạo token con ngẫu nhiên (`secrets.token_urlsafe(32)`) giữ **trong bộ nhớ process** (không ghi DB, vì REST v1 do chính process này kiểm): ánh xạ token → (credential cha, principal, `on_behalf_of`, `execution_id`, hết hạn 60 giây); chạy `deno run --no-prompt --no-config --no-remote --allow-net=127.0.0.1:<cổng CRM> --v8-flags=--max-old-space-size=64` trong thư mục tạm rỗng, không cấp `--allow-read/--allow-write/--allow-env/--allow-run/--allow-ffi/--allow-sys`; code của agent được bọc trong một module nạp SDK đã đóng gói sẵn; truyền token và URL qua stdin.
   - Giới hạn: timeout 10 giây (kill nhóm process), `prlimit` CPU 10 giây và bộ nhớ ảo, kết quả ≤ 32 KB JSON, `console.log` ≤ 4 KB, tối đa 2 lần chạy đồng thời và hàng đợi 4.
   - Giới hạn số lời gọi (200) và số lệnh ghi (20) mỗi `execution_id` cưỡng chế ở **server** (middleware REST v1 đếm theo `execution_id` của token con).
   - Handler `execute` là async, không giữ transaction hay khoá DB trong khi chờ subprocess; uvicorn vẫn phục vụ lời gọi ngược của sandbox.
   - Sau khi chạy: thu hồi token con; ghi audit `mcp.execute` (hash SHA-256 code, độ dài, danh sách lệnh tra theo `execution_id`, thời gian, kích thước kết quả, outcome); che PII trong `console.log` và thông điệp lỗi như lớp phòng thủ thứ hai.
7. **MCP server** (`crm/src/adapters/inbound/mcp/server.py`): `fg-crm`, transport streamable HTTP mount ở `/mcp`, xác thực Bearer bằng dependency của phase 2, chỉ credential có scope `mcp`; hai tool `search_api`, `execute` (design §5.9); `instructions` tiếng Việt.
8. **CLI** `crm/ops/crmctl.py`: nhóm lệnh đọc tương ứng (design §5.8), gọi `/api/v1`, `--json`; đọc `CRM_URL`, `CRM_TOKEN` từ môi trường.
9. **Image:** thêm MCP Python SDK đã ghim và binary Deno đã ghim phiên bản (tải trong bước build, kiểm checksum); ghim digest `python:3.12-slim` bằng digest đang chạy (lấy từ `docker image inspect` image hiện tại); kiểm `sqlite3.sqlite_version`, `python`, `duckdb`, `fastapi` giống image cũ. Tag image cũ là `crm:pre-agent` trước khi build để rollback.
10. **Kênh mạng (đã chốt Q8):** route Caddy LAN + Tailscale chỉ cho `/mcp` và `/api/v1` tới `crm:8090` (theo mẫu report site Evidence), không qua Cloudflare Tunnel; CSRF không ảnh hưởng vì client không gửi Origin. Tài liệu kết nối Claude Desktop (`mcp-remote`) ở `crm/docs/agent-access.md`.
11. **Credential đầu tiên:** `agent:claude_desktop_ceo` (bound user = CEO, scope `mcp,read`), và `agent:claude_desktop_<người thực thi>` để thử.
12. **Bộ kịch bản 30 câu** tiếng Việt (ví dụ "Hôm nay tôi nên gọi ai?", "5 khách đáng giá nhất trong worklist chưa liên hệ 30 ngày, kèm sản phẩm gần nhất", "Chiến dịch X ra sao?") lưu ở `crm/src/tests/agent_scenarios/`: mỗi câu có đoạn code TS mẫu chạy qua `execute` trên fixture giả và kết quả mong đợi; test quét kết quả: không SĐT, không tên đầy đủ, không tag/trường nhạy cảm (fixture có khách đã đồng ý riêng và có tag sức khoẻ), có `data_as_of`.
13. **Đo token** (tiêu chí chấp nhận của plan): (a) kích thước định nghĩa tool + `instructions` của server (đếm bằng tokenizer, chấp nhận ước lượng 4 ký tự/token nếu không có tokenizer) so với ước lượng 21 tool riêng (sinh tạm JSON schema của 21 thao tác từ OpenAPI chỉ để đếm, không triển khai); (b) với 10 câu kịch bản, tổng byte REST mà sandbox nhận so với byte kết quả trả về model. Ghi số vào `crm/docs/agent-access.md`.
14. ADR-020 cập nhật: code mode, runtime sandbox, ranh giới cưỡng chế.

## File

- Tạo: `crm/src/application/queries/*.py`, `crm/src/adapters/inbound/api_v1/*.py`, `crm/src/adapters/inbound/mcp/{server.py,sandbox.py,search_index.py}`, `crm/src/adapters/inbound/mcp/sdk/crm_sdk.ts` (sinh ra), `crm/ops/generate_mcp_sdk.py`, `crm/ops/crmctl.py`, `crm/docs/agent-access.md`, test (`test_api_v1_read.py`, `test_mcp_code_mode.py`, `test_sandbox_isolation.py`, `test_sdk_generated_up_to_date.py`, `test_pii_presentation.py`, `agent_scenarios/`).
- Sửa: `crm/src/domain/policy.py`, `crm/src/composition.py` (đăng ký router, mount MCP), `crm/src/requirements.txt`, `Dockerfile.crm`, cấu hình Caddy, `crm/AGENTS.md` (nơi đặt query service; adapter mỏng; quy tắc sinh lại SDK khi đổi route v1), `crm/README.md`, ADR-020.

## Các bước

1. Worktree `feat/crm-agent-read`.
2. Query service + test trên fixture (so với đường đọc hiện có của UI để không lệch).
3. Chính sách PII + test.
4. REST v1 + OpenAPI; CLI.
5. Bộ sinh SDK + chỉ mục `search_api` + test sinh lại.
6. Sandbox runner + giới hạn phía server + test cô lập.
7. MCP server hai tool; bộ 30 kịch bản; đo token.
8. Build image trong scratch (tag riêng, không đè tag đang chạy); chạy toàn bộ test trong image mới; đo RAM đỉnh của `execute` khi chạy song song 2 lần.
9. Thử thật trên bản sao: container scratch từ image mới với bản sao DB, Claude Desktop của người thực thi nối qua `mcp-remote`, chạy 10 câu kịch bản.
10. Deploy giờ user duyệt: `docker compose build crm`, `docker compose up -d crm` (lưu log trước); route Caddy.
11. Chạy song song có người theo dõi 1 tuần: đọc audit `mcp.execute` hằng ngày (hash code, lệnh đã gọi); CEO dùng thử.

## Test

| Mức | Nội dung |
|---|---|
| Unit | Mỗi query trả cùng nội dung với đường đọc hiện có của UI trên fixture (360, worklist, timeline) |
| Unit | PII: agent không bao giờ nhận SĐT, tên đầy đủ, ngày sinh đủ, địa chỉ chi tiết, trường/tag nhạy cảm; người dùng nhận như cũ |
| Unit (sandbox) | Code đọc file, đọc env, chạy subprocess, gọi host ngoài (`https://example.com`), gọi `127.0.0.1` cổng khác, theo redirect ra ngoài → đều bị Deno chặn; vòng lặp vô hạn → bị kill ở 10 giây; cấp phát vượt bộ nhớ → lỗi, process CRM không ảnh hưởng; kết quả > 32 KB → cắt kèm cảnh báo |
| Unit (server) | Token con hết hạn sau 60 giây và bị thu hồi khi chạy xong; dùng token con ngoài sandbox sau khi xong → 401; 201 lời gọi trong một `execution_id` → lỗi `execution_call_limit`; token con không có quyền nhiều hơn credential cha |
| Unit | `search_api` không trả hàm principal không có quyền; trả ≤ 5 mục; tìm không dấu được |
| Unit | Mỗi `execute` có đúng một audit `mcp.execute` với hash code và danh sách lệnh; mỗi lời gọi REST trong sandbox có audit riêng kèm `execution_id` |
| Unit | Lỗi trả về model không chứa stack server, body request hay chuỗi giống SĐT |
| Tích hợp | 30 kịch bản xanh; `pytest` toàn bộ trong image mới; SDK đã commit khớp OpenAPI |
| Thủ công | Claude Desktop trả lời được 10 câu mẫu, mỗi câu có "dữ liệu tới" |

## Kiểm "CRM như cũ"

- Phase chỉ thêm route, thêm thư viện, thêm runtime Deno và đổi cách build image. `parity_snapshot diff`: chỉ khác số dòng `crm_audit_event` (nếu chạy thử trên bản sao); mọi hash khác giữ nguyên.
- Image mới: `python --version`, `sqlite3.sqlite_version`, `duckdb.__version__`, `fastapi.__version__` giống image cũ (in ra so trước khi deploy). RAM nghỉ của container `crm` sau khởi động tăng không quá 30 MB (Deno không chạy thường trực).
- Sau deploy: UI, `/admin/refresh`, nightly export như phase trước; route cũ `/api/*` trả như cũ (gọi thử `GET /api/parties/{id}/360` bằng token cũ).

## Đụng prod và duyệt

Có: build lại image, tạo lại container, thêm route Caddy. Cần user duyệt giờ.

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Code độc hoặc vòng lặp từ agent (do prompt injection trong dữ liệu khách, ví dụ ghi chú) | Trung bình × Trung bình | Sandbox deny-by-default, timeout, giới hạn RAM/CPU, giới hạn số lời gọi theo `execution_id` ở server; sandbox chỉ có quyền của principal agent; audit hash code |
| Thoát sandbox Deno | Thấp × Cao | Ghim phiên bản, theo dõi advisory; không cấp quyền nào ngoài net loopback; process chạy bằng user không đặc quyền trong container; container CRM không có secret ngoài token của chính nó |
| Lộ dữ liệu qua lỗi hoặc `console.log` | Thấp × Trung bình | Thông điệp lỗi REST không chứa PII; che PII ở đầu ra; cắt kích thước |
| `execute` gọi ngược về chính process gây nghẽn | Trung bình × Trung bình | Handler async, không giữ transaction; tối đa 2 lần chạy đồng thời; timeout |
| RAM máy chủ không đủ khi chạy song song với data_platform | Trung bình × Trung bình | Phase 0 đo; đồng thời 2; nếu vượt, dùng phương án V8 isolate dự phòng (design §5.9.2) |
| MCP Python SDK kéo starlette/pydantic xung đột với FastAPI đang ghim | Trung bình × Trung bình | Phase 0 đã thử; nếu xung đột thì nâng FastAPI trong phase riêng trước |
| Model viết code sai SDK | Trung bình × Thấp | Kiểu TypeScript và JSDoc qua `search_api`; lỗi có kiểu để model tự sửa; kịch bản mẫu |
| Mở `/mcp` ra ngoài ý muốn | Thấp × Cao | Chỉ qua LAN/Tailscale; Cloudflare Tunnel không route `/mcp` |

## Rollback

`git revert` phạm vi đã deploy, dùng lại image `crm:pre-agent` (hoặc build với `requirements.txt` và `Dockerfile.crm` cũ), `docker compose up -d crm`; gỡ route Caddy; thu hồi credential (`credential_admin revoke`). Không có thay đổi dữ liệu cần dọn.
