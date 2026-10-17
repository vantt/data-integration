# Phase 0: kiểm thực địa

**Effort:** 0.25d · **Phụ thuộc:** — · **Đụng prod:** chỉ đọc · **Cần user:** không

## Mục tiêu

Xác nhận bằng quan sát thật những gì phase 1–2 dựa vào, trước khi viết code.

## Các bước

1. **Cgroup:** liệt kê `/sys/fs/cgroup/system.slice/docker-*.scope`, xác nhận có đủ `memory.stat`, `memory.events`, `memory.current`, `memory.peak`, `cpu.stat`, `io.stat`, `memory.pressure`, `cpu.pressure`, `io.pressure`, và đọc được bằng user thường. Ghi cách map id cgroup → tên container mà không gọi Docker API (ví dụ `/var/lib/docker/containers/<id>/config.v2.json`, cần root).
2. **Tiến trình bước Dagster:** trong một nightly (hoặc một job nhỏ chạy tay ngoài 02:30–04:00 nếu c8 đang chạy một job như vậy vì lý do khác; không tự kích hoạt job chỉ để đo), chụp `ps -eo pid,ppid,args` và đọc bằng root `/proc/<pid>/environ` của tiến trình con của `dagster api execute_step` (hoặc tương đương). Ghi lại: biến hay đối số nào cho run id và step key; tiến trình dbt là tiến trình con nào.
3. **Job `in_process_executor`:** xác nhận các job này chạy trong tiến trình nào (`orchestration/definitions.py:249`, `:258`, `:306`) để gắn ở mức job.
4. **`run_results.json`:** xác định nơi dagster-dbt ghi thư mục kết quả của mỗi lần chạy, và thời gian thư mục tồn tại trước khi `scripts/maintenance/cleanup_dbt_target_dirs_standalone.py` xoá (vòng 3600 giây). Nếu bị xoá trước khi công cụ kịp đọc, công cụ phải đọc ngay khi tiến trình dbt thoát.
5. **Số nền thời gian nightly:** lấy trung vị 7 nightly gần nhất để dùng cho tiêu chí 1.

## Kết quả

Báo cáo ngắn `reports/phase-00-field-check.md`: đường dẫn và khoá nhận diện thật, có ví dụ đã che giá trị. Nếu bước 2 không nhận diện được, chọn phương án dự phòng trong `plan.md` (Rủi ro) và báo điều phối trước khi sang phase 1.
