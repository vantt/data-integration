---
title: "Thư viện code mode dùng chung trong monorepo (packages/agent-codemode, sandbox Pydantic Monty)"
description: "Dựng thư viện Python độc lập packages/agent-codemode trong repo này: interface Runner (Monty mặc định), giới hạn, danh mục hàm và stub từ OpenAPI có x-agent-function, khối dựng MCP code mode (search_api + execute), audit hook, preset assistant/chat; mỗi gói sản phẩm tự cài thư viện và tự viết MCP server riêng."
status: pending
priority: P1
effort: 11d
branch: feat/agent-codemode-library
tags: [mcp, code-mode, sandbox, monty, agent, library, monorepo, security]
blockedBy: []
blocks: [261019-1500-crm-core-agent-native]
created: 2026-10-20
---

# Thư viện code mode dùng chung trong monorepo

## Tổng quan

Quyết định của user:

- **20/10 ~13:10:** MCP chạy theo code mode, sandbox là **Pydantic Monty** (`pydantic-monty` 1.2.0, MIT; worker là binary Rust `monty` trong `pydantic-monty-runtime`, client Python mỏng); agent viết **Python** (tập con Monty). Không Deno, không tự viết sandbox Rust/QuickJS. Dự phòng: `quickjs-rs` (QuickJS trong wasmtime) sau cùng interface; user đã chấp nhận agent viết JS nếu cổng thí nghiệm chọn nó. Chưa có người ngoài dùng, nhưng sau này có thể nối "chat agent": cần preset `chat` chặt hơn và đường nâng cấp sang micro-VM qua interface `Runner`.
- **20/10 16:07:** code mode **không** làm repo riêng. Nó là **một thư viện Python độc lập nằm trong repo này nhưng tự đứng được**, ở `packages/agent-codemode/`, có `pyproject.toml`, gói `agent_codemode`, phiên bản semver riêng bắt đầu `0.1.0`, README và test riêng. Mỗi gói sản phẩm (CRM; sau này report/kho cho MCP phân tích) tự cài thư viện và **tự viết MCP server riêng** với danh mục hàm riêng.
- **Vị trí tạm, bố cục chưa chốt (20/10):** bố cục thư mục của repo và cách đóng gói theo bộ chức năng (kho dữ liệu, report, CRM, mỗi bộ một gói) quyết trong thiết kế Đợt 2 ([roadmap 261013-1751](../261013-1751-modularize-data-platform-suite/roadmap.md), đoạn "Bố cục thư mục"). Thư viện code mode dùng chung cho nhiều bộ nên **nằm ngoài mọi bộ**; tạm đặt ở `packages/agent-codemode/`, vị trí có thể đổi theo Đợt 2. Chỉ hai chỗ phụ thuộc đường dẫn: cấu hình luật ranh giới (`scripts/checks/libraries.yaml`) và đường cài trong image. MCP server của CRM thuộc bộ CRM; MCP phân tích thuộc bộ report (hoặc kho, chờ Đợt 2). Không dời app hiện có.

Căn cứ: [`plans/reports/research-261019-1905-agent-code-sandbox-options.md`](../reports/research-261019-1905-agent-code-sandbox-options.md). Thiết kế phía CRM: [`plans/261019-1500-crm-core-agent-native/design.md`](../261019-1500-crm-core-agent-native/design.md) §5.9–5.10. Phase 3 của plan CRM chờ thư viện xong phase 5 của plan này.

## Kiến trúc tóm tắt

```text
packages/agent-codemode/            (thư viện, không biết gì về CRM)
   ├── Runner (interface): MontyRunner (mặc định) | QuickJsRunner (dự phòng) | runner micro-VM (sau này)
   ├── Limits: thời gian tổng, timeout từng hàm host, số lời gọi, kích thước kết quả, cắt/che log
   ├── Catalog: đọc OpenAPI của backend, lấy operation có `x-agent-function` → hàm host HTTP + stub + chỉ mục
   ├── Backend: gọi HTTP, lifecycle lần chạy (start → token con → finish), idempotency mặc định
   ├── MCP: build_mcp_app(...) tạo `search_api` và `execute`; preset assistant/chat
   └── Audit hook (AuditSink cắm được)

Gói sản phẩm (ví dụ CRM) tự viết server riêng, vài chục dòng:
   server = build_mcp_app(catalog=from_openapi(CRM_URL), runner_factory=MontyRunner, limits=..., instructions=..., ...)
   chạy trong container riêng có mem_limit (CRM: sidecar `crm_codemode`), gọi REST của backend; mọi policy ở backend
```

Nguyên tắc: thư viện **không giữ quyền hay dữ liệu**; nó chuyển tiếp danh tính của principal, cưỡng chế giới hạn tài nguyên và là lớp phòng thủ thêm, không thay policy của backend.

## Yêu cầu bắt buộc

1. **Tự đứng được:** `packages/agent-codemode/` không import gì từ các thư mục khác của repo (`crm`, `orchestration`, `ingestion`, `transformation`, `analytics`, `detailView`, `evidence`, `scripts`, `webhook_*`, và nội bộ của thư viện dùng chung khác). Chỉ phụ thuộc thư viện chuẩn, `pydantic-monty`/`pydantic-monty-runtime`, MCP Python SDK, `httpx` (và `quickjs-rs` nếu cổng chọn). Có thể chép nguyên thư mục ra repo riêng mà không sửa code.
2. **API công khai:** code ngoài thư viện chỉ dùng `import agent_codemode` / `from agent_codemode import ...` (các tên trong `__all__`); không import module con (`agent_codemode.runner.monty`, …).
3. Hai quy tắc trên được kiểm bằng luật mới trong `scripts/checks/check_boundaries.py`, viết **tổng quát cho mọi thư viện dùng chung** khai báo trong một tệp cấu hình (`scripts/checks/libraries.yaml`: đường dẫn thư mục và tên module gốc), không viết cứng `packages/` (phase 4), chạy trong `scripts/checks/run-all.sh`. Đổi vị trí thư viện chỉ sửa tệp này.
4. Interface `Runner` là ranh giới duy nhất với sandbox; MCP, catalog, limits, audit không import `pydantic_monty` trực tiếp.
5. RAM thật được chặn bằng cgroup (`mem_limit` của container chạy server sản phẩm), vì `max_memory` của Monty không chặn RSS. Timeout riêng cho từng hàm host, vì thời gian chờ hàm host không tính vào giới hạn của Monty.
6. Không nới bảo mật container để chạy bubblewrap (không `privileged`, không `seccomp=unconfined`, không thêm `CAP_SYS_ADMIN`). Nếu bubblewrap không chạy được thì lớp OS là cgroup + container hạn chế.
7. Phiên bản semver trong `pyproject.toml` và `CHANGELOG.md` của thư viện; thay đổi phá tương thích với hợp đồng backend (`x-agent-function`, `x-agent-catalog-version`, lifecycle) hoặc với API công khai chỉ ở bản major (trước `1.0.0`: ở bản minor, ghi rõ trong changelog).
8. Không đọc `.env*`, không dữ liệu khách trong test/ví dụ; không ghi plan ID, số phase vào code, tên test, commit message; commit theo conventional commit.

## Phases

| # | Phase | File | Effort | Phụ thuộc | Cổng / đầu ra |
|---|---|---|---|---|---|
| 0 | Bài kiểm thực nghiệm và cổng quyết định runner | [phase-00](phase-00-experiments-and-runner-gate.md) | 2.5d | — | **Cổng quyết định**: Monty / quickjs-rs / dừng; số RAM để đặt `mem_limit` |
| 1 | Khung thư viện, interface `Runner`, `MontyRunner`, pool, giới hạn | [phase-01](phase-01-runner-core-and-limits.md) | 3d | 0 | Bộ kiểm phá xanh |
| 2 | Danh mục hàm từ OpenAPI, stub, chỉ mục tìm kiếm, hàm host HTTP, lifecycle, idempotency mặc định | [phase-02](phase-02-catalog-stubs-and-backend-adapter.md) | 2.5d | 1 | Backend giả chạy trọn vòng |
| 3 | Khối dựng MCP (`search_api`, `execute`), chuyển tiếp danh tính, audit hook, preset `assistant`/`chat`, server mẫu | [phase-03](phase-03-mcp-server-and-audit.md) | 1.5d | 2 | Claude Desktop gọi được server mẫu + backend giả |
| 4 | Đóng gói trong monorepo: wheel, khoá phụ thuộc, luật ranh giới cho thư viện dùng chung, test trong `run-all.sh`, cách cài vào image | [phase-04](phase-04-packaging-versioning-ci.md) | 1d | 3 | `agent-codemode` 0.1.0 dựng được wheel; luật ranh giới và test xanh trong `run-all.sh` |
| 5 | Tài liệu và tích hợp mẫu | [phase-05](phase-05-docs-and-sample-integration.md) | 0.5d | 4 | CRM phase 3 dùng được |

Tổng: 11 ngày công. Phase 0 bắt đầu được ngay, song song với phase 0–2 của plan CRM.

## Cách gói sản phẩm dùng và ghim phiên bản

- **Hiện trạng quản lý phụ thuộc của repo (đã kiểm 20/10):** không có `pyproject.toml` hay `uv.lock` nào; mỗi thành phần có `requirements.txt` riêng (`ingestion/`, `scripts/`, `detailView/`, `crm/src/`, `crm/sync/`) và Dockerfile theo thành phần cài bằng `pip install -r` (`Dockerfile.crm:10-11`, `Dockerfile.dataplatform:27-31`). Thư viện không đổi cách này.
- **Khoá phụ thuộc của thư viện:** `pyproject.toml` khai báo phụ thuộc có cận; `requirements.lock` có hash sinh bằng `uv pip compile --generate-hashes`. Image dùng thư viện cài theo đúng kiểu pip hiện có: `pip install --require-hashes -r <thư viện>/requirements.lock` rồi `pip install --no-deps <wheel hoặc thư mục thư viện>`. Không đụng `requirements.txt` của thành phần khác.
- **Khi có từ hai `pyproject.toml` trở lên** (thư viện thứ hai, hoặc Đợt 2 chuyển thành phần sang `pyproject.toml`): dùng **uv workspace** (một `pyproject.toml` gốc khai báo `[tool.uv.workspace] members`) với **một `uv.lock` chung**, để các image không lệch phiên bản; mỗi Dockerfile vẫn cài bằng pip từ tệp xuất ra `uv export --package <gói> --frozen --no-emit-workspace` (có hash), nên không phải đổi sang uv trong image. Việc này làm khi điều kiện xảy ra, không làm trước.
- **Bây giờ (một repo, chưa tách image theo gói):** image của server sản phẩm cài thư viện từ chính thư mục trong repo, cùng commit: dựng wheel bằng `uv build packages/agent-codemode` (hoặc `pip wheel`) rồi `pip install --require-hashes -r packages/agent-codemode/requirements.lock` và cài wheel vừa dựng. Với CRM: `Dockerfile.crm_codemode` làm việc này cho sidecar `crm_codemode`. Phiên bản dùng là phiên bản của commit đang deploy; `agent_codemode.__version__` ghi vào log khởi động.
- **Sau khi tách image theo gói (Đợt 2):** mỗi image ghim `agent-codemode==x.y.z` (wheel dựng từ tag hoặc từ commit đã ghi phiên bản), nâng phiên bản là một commit riêng có chạy lại bộ tác vụ của gói đó.
- **Khi có dự án ngoài repo cần dùng:** chuyển nguyên thư mục `packages/agent-codemode/` ra repo riêng (giữ lịch sử bằng `git subtree split` hoặc `git filter-repo`), không viết lại; các gói trong repo này chuyển sang ghim phiên bản phát hành.
- **Hợp đồng với backend:** OpenAPI có `info.x-agent-catalog-version`; mỗi phiên bản thư viện khai báo dải hỗ trợ; ngoài dải thì server sản phẩm từ chối khởi động (healthcheck đỏ).

## Tiêu chí chấp nhận (đo được)

1. Cổng phase 0 có kết quả bằng số (bảng ở phase 0), user duyệt lựa chọn runner.
2. Bộ kiểm phá (vòng lặp vô hạn, ăn RAM, đệ quy sâu, chuỗi/list khổng lồ, kết quả khổng lồ, log khổng lồ, gọi hàm host vượt trần, hàm host chậm, thử đọc file, thử mạng, thử import module cấm, worker bị giết giữa chừng): 100% bị chặn hoặc kết thúc có kiểm soát; process host sống, lần chạy kế tiếp đúng; chạy trong `scripts/checks/run-all.sh`.
3. 1.000 lần `execute` liên tiếp (pool 2 worker): 0 lỗi host; RSS container sau 1.000 lần tăng ≤ 10% so với sau 100 lần.
4. `search_api` trả ≤ 5 stub, ≤ 2.000 token, không trả hàm principal không có quyền.
5. Định nghĩa tool + `instructions` mặc định ≤ 1.500 token.
6. Độ trễ thêm của thư viện (không tính model và backend) cho một `execute` 10 lời gọi hàm: p95 ≤ 300 ms khi pool ấm.
7. `check_boundaries.py` báo 0 vi phạm luật thư viện dùng chung trên code thật, và bắt được import ngược và import module con trong fixture test.
8. Chép riêng thư mục `packages/agent-codemode/` ra một thư mục tạm ngoài repo, cài và chạy toàn bộ test của thư viện ở đó thành công (chứng minh tự đứng được).

## Rủi ro chính

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Monty v1 còn mới (1.0.0 ngày 25/09/2026, 1.2.0 ngày 18/10), phát hành dày | Trung bình × Trung bình | Ghim trong `requirements.lock`; mọi chỗ dùng Monty sau `Runner`; nâng có kiểm |
| Model viết Python tập con sai | Trung bình × Thấp | Stub có kiểu, type-check trước khi chạy; đo tỷ lệ đúng lần đầu ở phase 0 |
| Lỗ hổng thoát interpreter Monty | Thấp × Cao | Container sản phẩm `read_only`, `cap_drop ALL`, không mount dữ liệu, không secret ngoài token theo request; backend không tin server code mode; runner micro-VM khi có người ngoài |
| bubblewrap không chạy được trong Docker | Cao × Thấp | Đã chấp nhận trước (yêu cầu 6) |
| Thư viện bị kéo dính vào code của repo, khó tách sau này | Trung bình × Trung bình | Luật ranh giới thư viện trong `run-all.sh`; tiêu chí 8 (chạy test ngoài repo) |
| Đợt 2 đổi bố cục làm đổi vị trí thư viện | Trung bình × Thấp | Chỉ sửa `libraries.yaml` và dòng cài trong Dockerfile của server sản phẩm; tên gói và API không đổi |
| Môi trường chạy test offline (shadow, `--network none`) chưa có wheel Monty | Trung bình × Thấp | Phase 4 thêm wheel vào bộ phụ thuộc offline (`scripts/shadow/prepare-deps.sh`) |
| Prompt injection qua chat agent sau này | Trung bình × Cao | Preset `chat`; backend phạm vi hẹp; runner micro-VM qua interface |

## Rollback

Thư viện mới, chưa có prod nào dùng cho tới plan CRM phase 3. Rollback ở plan này là `git revert`. Phía CRM rollback bằng dừng sidecar `crm_codemode` (plan CRM phase 3).

## Câu hỏi mở cho user (kèm đề xuất)

1. **Q1. License cho thư viện nội bộ:** **Đề xuất:** nội bộ, chưa cần license; ghi "Proprietary, internal use" trong `pyproject.toml`. Khi tách ra repo riêng hoặc công khai thì chọn (gợi ý MIT, cùng Monty).
2. **Q2. Ngân sách RAM cho container server code mode của CRM:** **Đề xuất:** 384 MiB (pool 2 worker), chốt lại theo số đo phase 0.
