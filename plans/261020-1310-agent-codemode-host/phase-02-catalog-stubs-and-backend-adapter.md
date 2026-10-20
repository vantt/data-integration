# Phase 2: danh mục hàm từ OpenAPI, stub, chỉ mục tìm kiếm, hàm host HTTP, lifecycle, idempotency

**Effort:** 2.5d · **Phụ thuộc:** phase 1 · **Đụng prod:** không · **Cần user duyệt:** không

## Bối cảnh

Backend (CRM, MCP phân tích) chỉ **khai báo** hàm cho agent bằng đánh dấu `x-agent-function` trên operation OpenAPI (design CRM §5.9.1, §5.9.4). Host sinh mọi thứ còn lại, nên backend không phải viết code riêng cho agent, và mỗi hàm agent đi qua đúng route REST có sẵn policy.

## Yêu cầu

1. **Hợp đồng backend v1** (viết thành tài liệu `docs/backend-contract.md` của repo):
   - `info.x-agent-catalog-version`: số nguyên; host khai báo dải hỗ trợ.
   - Mỗi operation dành cho agent có `x-agent-function: {name, group, kind: read|write|propose, idempotent: bool, timeout_s?: int}` và `description` (tiếng Việt được) làm docstring.
   - Tuỳ chọn lifecycle: `info.x-agent-executions: {start: "<path>", finish: "<path>"}`. Nếu có, host gọi `start` (bằng token agent, gửi hash SHA-256 và độ dài code) để nhận `execution_id` và token con, dùng token con cho mọi lời gọi hàm, rồi gọi `finish` (outcome, thời gian, kích thước kết quả). Nếu không có, host dùng token agent trực tiếp và tự sinh `execution_id`.
   - Tuỳ chọn danh sách hàm được phép: `info.x-agent-whoami: "<path>"` trả `allowed_functions`; nếu không có thì mọi hàm trong danh mục đều hiện.
2. **Catalog:** đọc OpenAPI lúc khởi động và khi nhận tín hiệu tải lại; kiểm `x-agent-catalog-version` nằm trong dải (ngoài dải → healthcheck đỏ, không phục vụ `execute`); dựng `FunctionSpec` (tên, nhóm, loại, tham số path/query/body với kiểu, kiểu trả về, mô tả, timeout).
3. **Stub Python** sinh từ `FunctionSpec`: `TypedDict` cho input/output (từ JSON Schema của OpenAPI), chữ ký hàm có kiểu, docstring; tham số `idempotency_key: str | None = None` cho hàm `write`/`propose`. Dùng cho type-check của Monty và cho `search_api`. (Nếu runner là quickjs-rs: sinh khai báo kiểu tương đương cho JS từ cùng `FunctionSpec`.)
4. **Chỉ mục tìm kiếm:** từ khoá trên tên, nhóm, mô tả; không phân biệt hoa thường và dấu tiếng Việt; trả tối đa N stub, giới hạn token; lọc theo `allowed_functions` của principal.
5. **Hàm host HTTP:** mỗi `FunctionSpec` thành một `HostFunction` gọi đúng method/path của backend bằng `httpx` (client dùng chung, timeout theo spec hoặc mặc định), gửi token (con hoặc agent), header `X-Request-Id` (UUIDv7), `X-Agent-Execution-Id`, `Idempotency-Key`. Lỗi backend chuyển thành lỗi có kiểu `BackendError{code, message, status, request_id}`, **không** kèm body request hay header.
6. **Idempotency mặc định:** hàm `write`/`propose` không được truyền khoá thì host điền `hash(idempotency_scope hoặc hash code, thứ tự lời gọi, hash tham số chuẩn hoá)`, để chạy lại cùng đoạn code không tạo bản ghi trùng.
7. **Không có đường ra khác:** host chỉ đăng ký vào runner các hàm sinh từ catalog; không có hàm tiện ích nào chạm mạng, file, thời gian hệ thống ngoài những gì runner tự có.
8. **Backend giả** (`examples/fake_backend/`, FastAPI): vài hàm đọc/ghi/đề xuất, có lifecycle, có `whoami`, có policy giả (403 khi không có quyền), dùng cho test và tài liệu.

## File

Trong repo mới: `agent_codemode/catalog/{openapi,spec,stubs,search}.py`, `agent_codemode/backend/{http,lifecycle,idempotency}.py`, `docs/backend-contract.md`, `examples/fake_backend/`, `tests/catalog/`, `tests/backend/`.

## Các bước

1. Viết hợp đồng backend.
2. Catalog + stub + chỉ mục; test với OpenAPI mẫu (gồm OpenAPI dạng của FastAPI có `$ref`).
3. Hàm host HTTP, lifecycle, idempotency; backend giả.
4. Test trọn vòng: code Python gọi hàm host → backend giả → kết quả.

## Test

| Mức | Nội dung |
|---|---|
| Unit | OpenAPI không có `x-agent-function` → danh mục rỗng; tên trùng → lỗi khởi động; phiên bản ngoài dải → healthcheck đỏ |
| Unit | Stub sinh ra qua được type-check của runner; code gọi sai kiểu bị chặn trước khi chạy |
| Unit | Tìm không dấu ("lien he" khớp "liên hệ"); lọc theo `allowed_functions` |
| Unit | Lỗi backend 403/409/429/500 thành `BackendError` không chứa body/header; timeout từng hàm |
| Unit | Chạy lại cùng code → cùng khoá idempotency; khác tham số → khác khoá |
| Tích hợp | Backend giả với lifecycle: token con dùng cho mọi lời gọi; `finish` luôn được gọi kể cả khi code lỗi hoặc timeout |

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| JSON Schema của OpenAPI phức tạp (oneOf, $ref lồng) sinh stub sai | Trung bình × Thấp | Hỗ trợ tập con cần thiết; kiểu không hỗ trợ thành `Any` kèm cảnh báo khởi động |
| Backend đổi route làm hàm agent đổi theo âm thầm | Thấp × Trung bình | Backend tăng `x-agent-catalog-version` khi phá tương thích; host ghi danh sách hàm vào log khởi động |

## Rollback

Repo mới, chưa phát hành.
