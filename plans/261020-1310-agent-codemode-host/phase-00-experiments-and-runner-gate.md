# Phase 0: bài kiểm thực nghiệm và cổng quyết định runner

**Effort:** 2.5d · **Phụ thuộc:** — · **Đụng prod:** chỉ đọc (đọc RAM trống, `docker stats --no-stream`); mọi thử nghiệm chạy trong container scratch, không trên container prod · **Cần user duyệt:** có, duyệt kết quả cổng (không cần giờ deploy)

## Bối cảnh

Research 19/10 chọn Monty nhưng mọi số đo là số tự công bố của dự án, trên Apple Silicon. Chưa có số RSS mỗi worker, chưa biết bubblewrap chạy được trong Docker không, chưa so tỷ lệ code đúng lần đầu giữa Python (Monty) và JS (quickjs-rs) với model đang dùng. Phase này đo trước khi viết code thật.

## Yêu cầu

1. **Prototype tối thiểu** trong thư mục thử (chưa phải repo chính): hai runner sau cùng chữ ký `run(code, functions, limits)`:
   - `MontyRunner` dùng `pydantic_monty` (`AsyncMonty`, pool worker, `max_memory`, `max_feed_duration_secs`, `request_timeout`, `max_suspensions`, `max_recursion_depth`).
   - `QuickJsRunner` dùng `quickjs-rs` (`memory_limit`, timeout mỗi eval), chạy trong subprocess riêng để cô lập crash.
   - Backend giả: 9 hàm đọc và 6 hàm ghi theo danh mục CRM (design CRM §5.9.4), dữ liệu giả, độ trễ giả 5–30 ms.
2. **Đo RAM** trong container giới hạn như prod dự kiến (`mem_limit` 384 MiB, 1 CPU), pool 2 và 4 worker:
   - RSS mỗi worker khi rảnh và khi chạy tác vụ điển hình (10 lời gọi hàm, xử lý 200 bản ghi);
   - RSS container sau 100 và sau 1.000 lần `execute` liên tiếp (rò rỉ);
   - thời gian checkout lạnh và ấm.
   Đọc RAM trống thực tế của máy prod (`free -m`, `docker stats --no-stream`, chỉ đọc) để đặt ngân sách.
3. **Trần RAM qua cgroup:** chạy code ăn RAM vượt `max_memory`; xác nhận cgroup chặn RSS, worker bị giết (không phải process host), pool tự thay worker, lần chạy kế tiếp đúng; ghi thời gian hồi phục.
4. **bubblewrap trong Docker:** thử `binary_path` (hoặc cơ chế tương đương) của Monty trỏ tới wrapper `bwrap --unshare-all --die-with-parent ...` dưới cấu hình container mặc định (seccomp/AppArmor mặc định, không thêm capability). Ghi kết quả: chạy được hay bị chặn, lý do. Không nới cấu hình container để ép chạy (yêu cầu bắt buộc 4 của plan).
5. **Bộ kiểm phá** (mỗi bài chạy với cả hai runner): vòng lặp vô hạn; `'x' * 10**12`; list tăng dần tới khi hết RAM; đệ quy sâu; kết quả trả về 100 MB; in log 100 MB; gọi hàm host 10.000 lần; hàm host chậm 60 giây; thử mở file, thử socket/HTTP, thử import `os`/`subprocess`; giết worker giữa chừng. Kết quả mong đợi: chặn hoặc kết thúc có kiểm soát, host sống.
6. **Tỷ lệ code đúng lần đầu:** 25 tác vụ CRM (dùng lại câu hỏi của bộ tác vụ plan CRM phase 3, chạy trên backend giả), model đang dùng (Claude qua API, cùng model mà Claude Desktop của user dùng), mỗi tác vụ 3 lần cho mỗi runner: (a) Monty, agent viết Python với stub `TypedDict` và type-check; (b) quickjs-rs, agent viết JS với khai báo kiểu dạng JSDoc/TS. Ghi tỷ lệ đúng lần đầu, số lần thử lại, loại lỗi (cú pháp không hỗ trợ, gọi sai hàm, sai kiểu, sai logic).
7. **Độ trễ end-to-end** của host (không tính model): `execute` với 5, 10, 20 lời gọi hàm; p50/p95.
8. **Báo cáo** `plans/261020-1310-agent-codemode-host/reports/phase-00-experiments.md` (chỉ số đo, không dữ liệu khách) và trình user cổng quyết định.

## Cổng quyết định

| Tiêu chí | Ngưỡng để chọn Monty |
|---|---|
| RSS mỗi worker rảnh | ≤ 50 MB |
| RSS đỉnh mỗi worker ở tác vụ điển hình | ≤ 150 MB |
| Trần cgroup | Worker bị giết, host sống, hồi phục ≤ 2 giây, lần sau đúng |
| 1.000 lần chạy | 0 lỗi host; RSS container tăng ≤ 10% từ lần 100 tới lần 1.000 |
| Bộ kiểm phá | 100% chặn hoặc kết thúc có kiểm soát |
| Tỷ lệ đúng lần đầu (25 tác vụ × 3) | ≥ 80%; ≥ 95% sau một lần thử lại |
| p95 độ trễ host, 10 lời gọi | ≤ 300 ms |

Quy tắc:
- Monty đạt mọi ngưỡng → chọn Monty (mặc định đã chốt).
- Monty trượt **chỉ** ở tỷ lệ đúng lần đầu, quickjs-rs vượt Monty ≥ 10 điểm và đạt ngưỡng → đề xuất user đổi sang quickjs-rs (agent viết JS); CRM không phải đổi gì.
- Monty trượt RAM/cô lập mà quickjs-rs đạt → đề xuất quickjs-rs.
- Cả hai trượt tiêu chí cô lập → dừng, báo user, xem lại (ví dụ hyperlight-sandbox có KVM).
- bubblewrap: không phải tiêu chí cổng; chỉ quyết định có thêm lớp OS hay không.

## File

- Tạo (ngoài repo này, trong thư mục thử nghiệm của repo host tương lai hoặc scratch): prototype hai runner, backend giả, bộ kiểm phá, harness 25 tác vụ.
- Tạo (trong repo này): `plans/261020-1310-agent-codemode-host/reports/phase-00-experiments.md`.

## Các bước

1. Dựng container thử từ `python:3.12-slim` với `mem_limit` 384 MiB, cài `pydantic-monty==1.2.0`, `quickjs-rs` (bản mới nhất), ghi phiên bản.
2. Prototype hai runner + backend giả.
3. Đo RAM, cgroup, bubblewrap, độ trễ.
4. Bộ kiểm phá.
5. Harness 25 tác vụ × 3 lần × 2 runner.
6. Báo cáo, trình user.

## Test

Chính phase này là bài kiểm; mọi bài kiểm phá được giữ lại để chuyển thành test CI ở phase 1.

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Đo trên container thử khác prod | Trung bình × Thấp | Cùng base image, cùng `mem_limit`, cùng nhân Linux của máy prod |
| Tỷ lệ đúng lần đầu dao động theo model và prompt | Trung bình × Trung bình | 3 lần mỗi tác vụ; cùng `instructions`; ghi phiên bản model |
| Chi phí gọi model cho harness | Chắc chắn × Thấp | 25 × 3 × 2 = 150 lượt, ước lượng nhỏ |

## Rollback

Không có thay đổi prod.
