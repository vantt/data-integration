---
title: "Code-mode host dùng chung cho MCP (repo riêng, sandbox Pydantic Monty)"
description: "Dựng một repo Python dùng chung cung cấp MCP code mode (search_api + execute) trên sandbox Pydantic Monty, sinh danh mục hàm và stub từ OpenAPI có x-agent-function, có giới hạn, audit hook và interface Runner thay được; CRM và MCP phân tích ghim phiên bản để dùng."
status: pending
priority: P1
effort: 12d
branch: main (repo mới, tên dự kiến agent-codemode)
tags: [mcp, code-mode, sandbox, monty, agent, shared-library, security]
blockedBy: []
blocks: [261019-1500-crm-core-agent-native]
created: 2026-10-20
---

# Code-mode host dùng chung cho MCP

## Tổng quan

User chốt ngày 20/10/2026 ~13:10:

- MCP của CRM chạy theo code mode, sandbox dùng **Pydantic Monty** (`pydantic-monty` 1.2.0, MIT; worker là binary Rust `monty` trong `pydantic-monty-runtime`, client Python mỏng). Agent viết **Python** (tập con Monty). Không dùng Deno, không tự viết sandbox Rust/QuickJS. Dự phòng nếu Monty trượt bài kiểm: `quickjs-rs` (LangChain, QuickJS trong wasmtime) sau cùng interface.
- Lớp "code-mode host" là **repo git riêng dùng chung**: MCP CRM, MCP phân tích cho CEO, dự án khác. CRM chỉ khai báo danh mục hàm; mọi policy, che PII, audit, đề xuất → duyệt vẫn ở CommandBus của CRM.
- Chưa có người ngoài dùng, nhưng sẽ có thể nối "chat agent": host phải có principal loại `chat` với giới hạn chặt hơn và đường nâng cấp sang cô lập mạnh hơn (micro-VM) qua interface `Runner`.

Căn cứ: [`plans/reports/research-261019-1905-agent-code-sandbox-options.md`](../reports/research-261019-1905-agent-code-sandbox-options.md) (so 11 ứng viên, đề xuất Monty + lớp bọc mỏng, các bài kiểm phải làm trước khi chốt). Thiết kế phía CRM: [`plans/261019-1500-crm-core-agent-native/design.md`](../261019-1500-crm-core-agent-native/design.md) §5.9–5.10.

Plan này làm phần host. Phase 3 của plan CRM chờ bản phát hành đầu tiên của host.

## Kiến trúc tóm tắt

```text
Client MCP (Claude Desktop qua mcp-remote, bot Lark)
   │ Bearer token của principal agent
   ▼
code-mode host (container riêng mỗi backend, mem_limit = trần RAM qua cgroup)
   ├── MCP server: search_api(query) , execute(code)
   ├── Catalog: đọc OpenAPI của backend, lấy các operation có `x-agent-function`
   │            → hàm host (HTTP tới backend) + stub Python có kiểu + chỉ mục tìm kiếm
   ├── Runner (interface): MontyRunner (mặc định) | QuickJsRunner (dự phòng) | MicroVmRunner (sau này)
   ├── Limits: thời gian tổng, timeout từng hàm host, số lời gọi, kích thước kết quả, cắt/che log
   ├── Execution lifecycle (tuỳ chọn, do backend khai báo): start → token con → finish
   └── Audit hook: hash code, danh sách lời gọi, thời gian, outcome (gửi về backend hoặc log)
   │ HTTP (token con hoặc token agent)
   ▼
Backend (CRM REST /api/v1, API nội bộ của MCP phân tích): mọi policy và audit chính
```

Nguyên tắc: **host không giữ quyền hay dữ liệu của riêng nó**. Host chỉ chuyển tiếp danh tính của principal; mọi quyết định cho/không cho nằm ở backend. Host cưỡng chế giới hạn tài nguyên và là lớp phòng thủ thêm, không thay backend.

## Yêu cầu bắt buộc

1. Repo mới, Python ≥ 3.12, quản lý bằng `uv`, license MIT (khớp Monty) trừ khi user chọn khác. Không có code hay dữ liệu của Fine Japan trong repo; ví dụ dùng backend giả.
2. Interface `Runner` là ranh giới duy nhất với sandbox; MCP, catalog, limits, audit không import `pydantic_monty` trực tiếp.
3. Giới hạn RAM thật bằng cgroup (container `mem_limit`), vì `max_memory` của Monty không chặn RSS của worker. Timeout riêng cho từng hàm host, vì thời gian chờ hàm host không tính vào giới hạn thời gian của Monty.
4. Không nới bảo mật container để chạy bubblewrap (không `privileged`, không `seccomp=unconfined`, không thêm `CAP_SYS_ADMIN`). Nếu bubblewrap không chạy được dưới cấu hình mặc định thì ghi rõ lớp OS là cgroup + container hạn chế.
5. Không đọc `.env*`, không đưa dữ liệu khách vào test hay ví dụ.
6. Không ghi plan ID, số phase vào code, tên test, commit message của repo mới.
7. Phát hành theo semver; mỗi bản có tag git, changelog, image có digest. Thay đổi phá tương thích với hợp đồng backend (`x-agent-function`, `x-agent-catalog-version`, lifecycle endpoint) chỉ ở bản major.

## Phases

| # | Phase | File | Effort | Phụ thuộc | Cổng / đầu ra |
|---|---|---|---|---|---|
| 0 | Bài kiểm thực nghiệm và cổng quyết định runner | [phase-00](phase-00-experiments-and-runner-gate.md) | 2.5d | — | **Cổng quyết định**: Monty / quickjs-rs / dừng; số RAM để đặt `mem_limit` |
| 1 | Khung repo, interface `Runner`, `MontyRunner`, pool, giới hạn | [phase-01](phase-01-runner-core-and-limits.md) | 3d | 0 | Bộ kiểm phá chạy xanh trong CI |
| 2 | Danh mục hàm từ OpenAPI, stub, chỉ mục tìm kiếm, hàm host HTTP, lifecycle, idempotency mặc định | [phase-02](phase-02-catalog-stubs-and-backend-adapter.md) | 2.5d | 1 | Backend giả chạy trọn vòng |
| 3 | MCP server (`search_api`, `execute`), chuyển tiếp danh tính, audit hook, che log, preset `assistant`/`chat` | [phase-03](phase-03-mcp-server-and-audit.md) | 1.5d | 2 | Claude Desktop gọi được host + backend giả |
| 4 | Đóng gói, phiên bản, CI, image | [phase-04](phase-04-packaging-versioning-ci.md) | 1.5d | 3 | Tag `v0.1.0` (hoặc `v1.0.0` theo Q4), image có digest |
| 5 | Tài liệu và tích hợp mẫu (backend giả, hướng dẫn CRM, hướng dẫn MCP phân tích) | [phase-05](phase-05-docs-and-sample-integration.md) | 1d | 4 | CRM phase 3 dùng được |

Tổng: 12 ngày công. Phase 0 có thể bắt đầu ngay, song song với phase 0–2 của plan CRM.

## Cách CRM (và dự án khác) ghim phiên bản

- Repo host CI dựng image `agent-codemode:<semver>` và đẩy lên registry đã chọn (Q2); CRM ghim **theo digest** trong `Dockerfile.crm_codemode` (`FROM <registry>/agent-codemode:<semver>@sha256:...`) hoặc trong `docker-compose.yml`.
- Nếu không dùng registry: `Dockerfile.crm_codemode` cài wheel phát hành kèm release của tag (`pip install --require-hashes -r requirements-codemode.txt`, file khoá có hash của wheel host, `pydantic-monty`, `pydantic-monty-runtime`).
- Hợp đồng với backend: OpenAPI có `info.x-agent-catalog-version`; mỗi bản host khai báo dải hỗ trợ (ví dụ `1.x`); ngoài dải thì host từ chối khởi động (healthcheck đỏ), không chạy với danh mục lệch.
- Nâng phiên bản host: đọc changelog của host và của Monty, chạy lại bộ 25 tác vụ và bộ kiểm phá trên image mới, rồi mới đổi digest (một commit riêng ở repo dùng).

## Tiêu chí chấp nhận (đo được)

1. Cổng phase 0 có kết quả ghi bằng số (bảng ở phase 0), user duyệt lựa chọn runner.
2. Bộ kiểm phá (vòng lặp vô hạn, ăn RAM, đệ quy sâu, chuỗi/list khổng lồ, kết quả khổng lồ, log khổng lồ, gọi hàm host vượt trần, hàm host chậm, thử đọc file, thử mạng, thử import module cấm, worker bị giết giữa chừng): 100% bị chặn hoặc kết thúc có kiểm soát; process host sống, lần chạy kế tiếp đúng; chạy trong CI mỗi commit.
3. 1.000 lần `execute` liên tiếp (pool 2 worker): 0 lỗi host; RSS container sau 1.000 lần không tăng quá 10% so với sau 100 lần.
4. `search_api` trả ≤ 5 stub, ≤ 2.000 token; không trả hàm principal không có quyền (theo danh sách backend trả về).
5. Định nghĩa tool + `instructions` mặc định ≤ 1.500 token.
6. Độ trễ thêm của host (không tính model và backend) cho một `execute` có 10 lời gọi hàm: p95 ≤ 300 ms khi pool ấm.
7. Image có digest, tag, changelog; CRM dựng được `crm_codemode` từ đó và qua bộ 25 tác vụ của plan CRM phase 3.

## Rủi ro chính

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Monty v1 còn mới (1.0.0 ngày 25/09/2026, 1.2.0 ngày 18/10), phát hành dày, có thể đổi API | Trung bình × Trung bình | Ghim phiên bản; mọi chỗ dùng Monty nằm sau `Runner`; nâng có kiểm |
| Model viết Python tập con sai (kế thừa class, generator, thư viện ngoài) | Trung bình × Thấp | Stub có kiểu và type-check của Monty trước khi chạy; `instructions` nêu giới hạn; đo tỷ lệ đúng lần đầu ở phase 0 |
| Lỗ hổng thoát interpreter Monty | Thấp × Cao | Container `read_only`, `cap_drop ALL`, không mount dữ liệu, không giữ secret ngoài token theo request; backend không tin host; theo dõi advisory; runner micro-VM khi có người ngoài |
| bubblewrap không chạy được trong Docker mặc định | Cao × Thấp | Đã chấp nhận trước: lớp OS là cgroup + container hạn chế (yêu cầu 4) |
| Worker vượt RAM làm OOM cả container host | Trung bình × Thấp | Một container host mỗi backend; backend không bị ảnh hưởng; pool tái chế worker; restart policy |
| Repo dùng chung trở thành gánh bảo trì thêm | Trung bình × Trung bình | Phạm vi hẹp (vài trăm dòng quanh Monty); không tự viết sandbox; CI đủ để nâng phiên bản an toàn |
| Prompt injection qua chat agent sau này | Trung bình × Cao | Preset `chat` giới hạn chặt; backend phạm vi hẹp; runner micro-VM qua interface |

## Rollback

Repo mới không đụng prod. Phía dùng (CRM) rollback bằng dừng service `crm_codemode` hoặc trả digest về bản trước (plan CRM phase 3). Một bản phát hành lỗi thì phát hành bản vá; không xoá tag đã phát hành.

## Câu hỏi mở cho user (kèm đề xuất)

1. **Q1. Tên repo:** dự kiến `agent-codemode`. **Đề xuất:** giữ tên này (gói Python `agent_codemode`).
2. **Q2. Repo và image để ở đâu, công khai hay riêng?** **Đề xuất:** repo riêng tư trên GitHub của công ty, image trên GitHub Container Registry riêng tư; máy prod kéo bằng token chỉ-đọc. Nếu không muốn máy prod truy cập registry thì dùng cách wheel kèm hash.
3. **Q3. License:** **Đề xuất:** MIT (cùng Monty), kể cả khi để riêng tư, để sau này mở được.
4. **Q4. Đánh số bản đầu:** `v0.1.0` (cho phép đổi hợp đồng trước khi ổn định) hay `v1.0.0`? **Đề xuất:** `v0.1.0`, lên `v1.0.0` sau khi CRM và MCP phân tích cùng chạy 2 tuần.
5. **Q5. Ngân sách RAM cho mỗi container host trên máy chủ hiện tại:** **Đề xuất:** 384 MiB cho `crm_codemode` (pool 2 worker), chốt lại theo số đo phase 0.
