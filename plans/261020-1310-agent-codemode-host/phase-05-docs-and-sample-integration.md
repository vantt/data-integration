# Phase 5: tài liệu và tích hợp mẫu

**Effort:** 1d · **Phụ thuộc:** phase 4 · **Đụng prod:** không (tích hợp CRM thật nằm ở plan CRM phase 3) · **Cần user duyệt:** không

## Bối cảnh

Bên dùng đầu tiên là CRM (plan `261019-1500-crm-core-agent-native` phase 3), sau đó là MCP phân tích cho CEO. Tài liệu phải đủ để bên dùng tích hợp chỉ bằng khai báo, không đọc code host.

## Yêu cầu

1. **README:** host làm gì, không làm gì (không thay policy của backend), kiến trúc, cách chạy với backend giả trong 5 phút.
2. **`docs/backend-contract.md`** (từ phase 2) hoàn thiện, kèm ví dụ FastAPI: thêm `openapi_extra={"x-agent-function": ...}` cho route, khai báo lifecycle, `whoami`, `x-agent-catalog-version`.
3. **`docs/security.md`:** mô hình mối đe doạ (code do model viết, prompt injection từ dữ liệu, host bị chiếm, backend là nơi kiểm quyền), các lớp phòng thủ (Monty deny-by-default, giới hạn host, cgroup, container hạn chế, backend không tin host), kết quả bubblewrap ở phase 0, đường nâng cấp micro-VM qua `Runner` (hyperlight-sandbox, microsandbox) cho principal `chat` hoặc người ngoài.
4. **`docs/operations.md`:** đặt `mem_limit` theo số đo, kích thước pool, đọc log audit, nâng phiên bản (đọc changelog, chạy bộ tác vụ của bên dùng, đổi digest).
5. **`docs/integration-crm.md`:** ánh xạ đúng với design CRM §5.9 (danh mục 21 hàm, lifecycle `agent-executions`, giới hạn, `crm_codemode`), làm checklist cho plan CRM phase 3.
6. **`docs/integration-analytics.md`:** bản phác cho MCP phân tích (hàm `metrics_*`, compiler chèn bộ lọc bắt buộc phía server, "lợi nhuận" mặc định CM2 nằm ở registry chỉ tiêu, không tính toán nặng trong sandbox).
7. **Ví dụ chạy được** `examples/fake_backend/` + `examples/compose.yml` (host + backend giả) dùng trong CI.

## File

Trong repo mới: `README.md`, `docs/{backend-contract,security,operations,integration-crm,integration-analytics}.md`, `examples/`.

## Các bước

1. Viết tài liệu theo thứ tự: README, hợp đồng backend, bảo mật, vận hành, hai tài liệu tích hợp.
2. Một người chưa đọc code (hoặc agent mới) làm theo README chạy được ví dụ; sửa chỗ vướng.
3. Bàn giao cho plan CRM phase 3 (đánh dấu plan này hoàn thành sau khi CRM dựng được `crm_codemode` từ bản phát hành).

## Test

| Mức | Nội dung |
|---|---|
| Tài liệu | Mọi lệnh trong README chạy được trên máy sạch (CI chạy `examples/compose.yml`) |
| Tích hợp | Checklist `integration-crm.md` khớp design CRM §5.9 (rà chéo) |

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Tài liệu lệch code | Trung bình × Thấp | Ví dụ chạy trong CI; hợp đồng backend có test |

## Rollback

Không áp dụng.
