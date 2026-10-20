# Phase 1: khung repo, interface Runner, MontyRunner, pool, giới hạn

**Effort:** 3d · **Phụ thuộc:** phase 0 (cổng đã duyệt) · **Đụng prod:** không · **Cần user duyệt:** không

## Bối cảnh

Phase 0 chọn runner và cho số RAM. Phase này dựng lõi của repo: ranh giới `Runner` và các giới hạn mà host cưỡng chế. Nếu cổng chọn `quickjs-rs`, thay `MontyRunner` bằng `QuickJsRunner` trong phase này, mọi phần khác giữ nguyên.

## Yêu cầu

1. **Khung repo** (`agent-codemode`, tên theo Q1): `pyproject.toml` (uv), gói `agent_codemode/`, `tests/`, `README.md`, `CHANGELOG.md`, `LICENSE`; lint và type-check (ruff, mypy hoặc pyright) trong CI.
2. **Interface** `agent_codemode.runner`:
   ```python
   class Runner(Protocol):
       async def run(self, code: str, functions: Mapping[str, HostFunction],
                     stubs: str, limits: Limits) -> RunResult: ...
       async def close(self) -> None: ...
   ```
   `HostFunction`: async callable có tên, chữ ký, timeout riêng. `Limits`: thời gian tổng, timeout mặc định mỗi hàm, số lời gọi tối đa, `max_memory`, độ sâu đệ quy, kích thước kết quả, kích thước log. `RunResult`: `value` (JSON được), `calls` (tên hàm, trạng thái, thời gian), `log` (đã cắt), `error` (loại, thông điệp, dòng trong code), `outcome` (`ok`/`error`/`timeout`/`limit`/`crashed`).
3. **`MontyRunner`:** `AsyncMonty` với pool riêng mỗi instance host, `max_processes` = cấu hình (mặc định 2), `max_checkouts_per_worker` để tái chế worker, `request_timeout` giết worker; type-check bằng stub trước khi chạy (lỗi kiểu trả về như lỗi code, không chạy); huỷ session sau mỗi lần chạm giới hạn RAM/thời gian (tài liệu Monty yêu cầu vì heap có thể hỏng). Hàm host đăng ký qua cơ chế hàm ngoài của Monty; hình dạng tên (module hay tên phẳng) chốt theo API thực tế đã thử ở phase 0.
4. **Giới hạn phía host** (không tin runner):
   - Mỗi hàm host bọc `asyncio.wait_for` với timeout riêng (thời gian chờ hàm host không tính vào giới hạn của Monty);
   - đếm lời gọi, vượt trần thì lỗi `call_limit` cho mọi lời gọi sau;
   - thời gian tổng bằng đồng hồ của host; hết giờ thì huỷ session và giết worker;
   - giá trị trả về chuẩn hoá JSON, cắt ở kích thước tối đa kèm cảnh báo;
   - log cắt, và đi qua bộ che (`Redactor` cắm được: mặc định che chuỗi giống SĐT Việt Nam, email).
5. **Hàng đợi đồng thời:** semaphore theo `max_processes`, hàng đợi có trần; quá trần thì `busy`.
6. **Vòng đời worker:** pool tự thay worker chết; health check của runner (`await runner.check()`).
7. **Runner dự phòng** `QuickJsRunner`: chỉ khung và test hợp đồng (chạy `run` cơ bản), đánh dấu thử nghiệm; bật đầy đủ chỉ khi cổng phase 0 chọn.
8. **Bộ kiểm phá** của phase 0 thành test CI (`tests/attack/`), chạy với runner đang bật.

## File

Trong repo mới: `agent_codemode/runner/{__init__,base,monty,quickjs}.py`, `agent_codemode/limits.py`, `agent_codemode/redact.py`, `tests/runner/`, `tests/attack/`.

## Các bước

1. Tạo repo (Q1, Q2), khung, CI tối thiểu.
2. Interface + `MontyRunner` + giới hạn.
3. Chuyển bộ kiểm phá thành test; chạy trong container có `mem_limit` (CI dùng job container hoặc `docker run` trong job).
4. Đo lại RAM và 1.000 lần chạy trên code thật, so với phase 0.

## Test

| Mức | Nội dung |
|---|---|
| Unit | Hợp đồng `Runner` (một bộ test dùng chung cho mọi runner): trả giá trị, lỗi cú pháp, lỗi kiểu, gọi hàm host sync/async, timeout hàm host, trần lời gọi, trần kết quả, trần log, che log |
| Tấn công | Toàn bộ danh sách phase 0; host sống, lần sau đúng |
| Tải | 1.000 lần chạy, RSS ổn định (tiêu chí 3 của plan) |

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| API Monty đổi giữa các bản | Trung bình × Trung bình | Ghim `pydantic-monty` và `pydantic-monty-runtime`; test hợp đồng bắt lỗi khi nâng |
| CI không có cgroup giống prod | Trung bình × Thấp | Chạy job tấn công trong container có `--memory` |

## Rollback

Repo mới, chưa phát hành; không ảnh hưởng ai.
