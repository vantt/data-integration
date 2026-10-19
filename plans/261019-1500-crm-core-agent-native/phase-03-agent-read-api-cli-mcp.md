# Phase 3: agent đọc qua REST v1, CLI và MCP

**Effort:** 4.5d · **Phụ thuộc:** phase 2; câu trả lời Q2 (PII cho agent) và Q8 (kênh mạng) · **Đụng prod:** có (CRM, build lại image) · **Cần user duyệt giờ:** có · **Migration:** không

## Bối cảnh

- Đã có khoảng 40 route `/api/*` nhưng không có hợp đồng ổn định (không version, lỗi không thống nhất, nhiều route trả HTML cho HTMX như `screen_customer_360_activity.py:644,707`).
- FastAPI đã sinh OpenAPI ở `/api/docs` (`crm/src/composition.py:208`).
- Thư viện nằm trong image (`crm/src/requirements.txt`), nên thêm MCP SDK phải build lại image; image hiện build ngày 10/08 từ `python:3.12-slim` không ghim digest (`Dockerfile.crm:4`).
- MCP phải chạy trong cùng process vì SQLite một writer (design §5.1). Phase này chỉ có tool đọc; tool ghi ở phase 4.
- Research CEO MCP đã chốt: Claude Desktop và bot Lark; dữ liệu hằng đêm đủ; "lợi nhuận" mặc định CM2 và luôn nêu bậc.

## Yêu cầu

1. **Query service** dưới `crm/src/application/queries/` (mỗi cái nhận port, trả DTO Pydantic dùng chung cho REST và MCP):
   - `PartyQuery.search(q, filters, limit, cursor)`, `PartyQuery.get_360(party_id)`;
   - `TimelineQuery.list(party_id, kinds, limit, cursor)` (tương tác, ghi chú, task, đơn từ cache);
   - `WorklistQuery.list(assignee, date, limit)` (bọc `WorklistQueryService` hiện có, không viết lại xếp hạng);
   - `TaskQuery.list(filters)`; `ApproachScriptQuery.get(party_id)` (giữ cảnh báo R14);
   - `SegmentQuery.members(segment_id, limit, cursor)`; `CampaignQuery.results(campaign_id)` (dùng ROI hiện có; lift ở phase 10);
   - `WhoAmIQuery` (principal, `on_behalf_of`, quyền hiệu lực, module bật, `data_as_of` từ `wh_sync_run`).
2. **Chính sách hiển thị PII** (`crm/src/domain/policy.py`): `present_party(dto, ctx)`:
   - Agent: SĐT luôn che dạng `09x****123`; tên theo `CRM_AGENT_PII_MODE` (`masked`: chữ cái đầu mỗi từ + mã khách; `full`: đủ tên); địa chỉ chỉ tỉnh/thành; ngày sinh chỉ năm.
   - Người dùng: như hiện nay.
   - Trường `data_class='sensitive'`: chỉ khi có `data.sensitive.read` (agent không bao giờ có).
3. **REST `/api/v1`** (`crm/src/adapters/inbound/api_v1/`): `GET /api/v1/whoami`, `/parties?q=`, `/parties/{id}`, `/parties/{id}/timeline`, `/worklist`, `/parties/{id}/approach-script`, `/tasks`, `/segments/{id}/members`, `/campaigns/{id}/results`. Phong bì `{data, data_as_of, warnings, request_id}`; lỗi theo design §5.7; phân trang cursor; mọi lời gọi của agent ghi audit qua `CommandBus.read`. Route cũ không đổi.
4. **MCP** (`crm/src/adapters/inbound/mcp/`): server `fg-crm`, transport streamable HTTP mount ở `/mcp`; xác thực Bearer bằng cùng dependency phase 2; chỉ credential có scope `mcp` vào được. 9 tool đọc: `whoami`, `search_parties`, `get_party_360`, `list_party_timeline`, `list_worklist`, `get_approach_script`, `list_tasks`, `list_segment_members`, `get_campaign_results` (design §5.9 số 1–9). Schema input/output sinh từ DTO Pydantic (một định nghĩa). Annotation `readOnlyHint=true`. Server `instructions` tiếng Việt: múi giờ Asia/Ho_Chi_Minh, CRM không tính số mà lấy từ kho, luôn nêu "dữ liệu tới", không suy diễn nhân quả, không đề nghị gửi tin cho khách.
5. **CLI** `crm/ops/crmctl.py`: nhóm lệnh đọc tương ứng (design §5.8), gọi `/api/v1`, `--json`; đọc `CRM_URL`, `CRM_TOKEN` từ môi trường.
6. **Image:** thêm MCP SDK đã ghim (phiên bản phase 0 xác nhận); ghim digest `python:3.12-slim` trong `Dockerfile.crm` bằng digest đang chạy (lấy từ `docker image inspect` của image hiện tại) để không kéo base mới; kiểm `sqlite3.sqlite_version` trong image mới bằng phiên bản cũ.
7. **Kênh mạng** theo Q8: nếu chọn LAN + Tailscale, thêm route Caddy chỉ cho `/mcp` và `/api/v1` tới `crm:8090` (theo mẫu report site Evidence), không qua Cloudflare Tunnel; CSRF không ảnh hưởng vì client không gửi Origin. Tài liệu kết nối Claude Desktop (`mcp-remote`) đặt ở `crm/docs/agent-access.md`.
8. **Credential đầu tiên:** `agent:claude_desktop_ceo` (bound user = CEO, scope `mcp,read`), và một credential `agent:claude_desktop_<người thực thi>` để thử.
9. **Bộ kịch bản kiểm 30 câu** tiếng Việt (ví dụ "Hôm nay tôi nên gọi ai?", "Khách này mua gì gần nhất?", "Chiến dịch X ra sao?") lưu ở `crm/src/tests/agent_scenarios/` dưới dạng chuỗi lời gọi tool mong đợi trên fixture giả; test tự động chạy tool qua MCP client trong process và quét phản hồi: không SĐT đầy đủ, không trường nhạy cảm, có `data_as_of`.

## File

- Tạo: `crm/src/application/queries/*.py`, `crm/src/adapters/inbound/api_v1/*.py`, `crm/src/adapters/inbound/mcp/*.py`, `crm/ops/crmctl.py`, `crm/docs/agent-access.md`, test (`test_api_v1_read.py`, `test_mcp_read_tools.py`, `test_pii_presentation.py`, `agent_scenarios/`).
- Sửa: `crm/src/domain/policy.py`, `crm/src/composition.py` (đăng ký router và mount MCP), `crm/src/requirements.txt`, `Dockerfile.crm`, cấu hình Caddy (nếu Q8 chọn LAN), `crm/AGENTS.md` (nơi đặt query service, quy tắc adapter mỏng), `crm/README.md`.

## Các bước

1. Worktree `feat/crm-agent-read`.
2. Query service + test trên fixture (so kết quả với service/screen hiện có để không lệch).
3. Chính sách PII + test.
4. REST v1 + OpenAPI; CLI.
5. MCP + test tool qua client trong process; bộ 30 kịch bản.
6. Build image trong scratch (tag riêng, không đè tag đang chạy); chạy toàn bộ test trong image mới.
7. Thử thật trên bản sao: container scratch từ image mới với bản sao DB, Claude Desktop của người thực thi nối vào qua `mcp-remote`, chạy 10 câu kịch bản.
8. Deploy giờ user duyệt: `docker compose build crm` (đã ghim base), `docker compose up -d crm` (lưu log trước); route Caddy nếu có.
9. Chạy song song có người theo dõi 1 tuần: người thực thi đọc audit `channel='mcp'` hằng ngày; CEO dùng thử.

## Test

| Mức | Nội dung |
|---|---|
| Unit | Mỗi query trả cùng nội dung với đường đọc hiện có của UI trên fixture (360, worklist, timeline) |
| Unit | PII: agent không bao giờ nhận SĐT đầy đủ, ngày sinh đủ, địa chỉ chi tiết, trường nhạy cảm; người dùng nhận như cũ |
| Unit | MCP: credential thiếu scope `mcp` bị từ chối; tool không tồn tại cho lệnh ghi; mỗi lời gọi có một audit `channel='mcp'` |
| Tích hợp | 30 kịch bản xanh; `pytest` toàn bộ trong image mới |
| Thủ công | Claude Desktop trả lời được 10 câu mẫu, mỗi câu có "dữ liệu tới" |

## Kiểm "CRM như cũ"

- Phase chỉ thêm route, thêm thư viện và đổi cách build image. `parity_snapshot diff`: chỉ khác số dòng `crm_audit_event` (nếu chạy thử tool trên bản sao); mọi hash khác giữ nguyên.
- Image mới: `python --version`, `sqlite3.sqlite_version`, `duckdb.__version__`, `fastapi.__version__` giống image cũ (in ra so trước khi deploy).
- Sau deploy: UI, `/admin/refresh`, nightly export như phase trước; route cũ `/api/*` trả như cũ (gọi thử `GET /api/parties/{id}/360` bằng token cũ).

## Đụng prod và duyệt

Có: build lại image, tạo lại container, có thể thêm route Caddy. Cần user duyệt giờ.

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| MCP SDK kéo theo phiên bản starlette/pydantic xung đột với FastAPI đang ghim | Trung bình × Trung bình | Phase 0 đã thử; nếu xung đột thì nâng FastAPI trong phase riêng trước, không gộp |
| Dữ liệu cá nhân khách tới nhà cung cấp mô hình | Chắc chắn khi dùng × Cao | Mặc định `masked`; chỉ đổi sau Q2 |
| Agent đọc quá nhiều (quét toàn bộ khách) | Thấp × Trung bình | Giới hạn `limit`, rate limit 60 lời gọi/phút/credential, audit |
| Mở `/mcp` ra ngoài ý muốn | Thấp × Cao | Chỉ qua LAN/Tailscale; Cloudflare Tunnel không route `/mcp` |

## Rollback

`git revert` phạm vi đã deploy, `docker compose build crm` với `requirements.txt` cũ (hoặc dùng lại image cũ đã tag `crm:pre-agent` trước khi build), `docker compose up -d crm`; gỡ route Caddy; thu hồi credential (`credential_admin revoke`). Không có thay đổi dữ liệu cần dọn.
