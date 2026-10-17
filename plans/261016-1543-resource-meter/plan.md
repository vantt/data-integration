---
title: "Đồng hồ đo tài nguyên siêu nhẹ cho nền tảng dữ liệu"
description: "Một file chạy Rust nằm ngoài mọi container, đọc số kernel đã tính sẵn (cgroup v2, /proc) để đo RAM, CPU và đĩa theo container, theo bước Dagster và theo model dbt; chạy liên tục, ghi file nén theo ngày, tự in tóm tắt; không cài thêm gì và bị khoá cứng để không lấy tài nguyên của phần chạy chính."
status: in-progress
priority: P3
effort: 3d + 7 đêm quan sát
branch: feat/resource-meter
tags: [observability, tooling, rust, performance, ops]
blockedBy: []
blocks: []
created: 2026-10-16
---

# Đồng hồ đo tài nguyên siêu nhẹ

## Overview

Ngày 16/10/2026, khi xét điều kiện dừng 4 của bộ máy phân loại, số `memory.peak` 8,01 GiB gây báo động nhầm: số này cộng dồn từ lúc container khởi động và tính cả page cache, trong khi RAM thật của tiến trình chỉ 0,87 GiB. Cách c8 kiểm lại (đọc `memory.stat`, `memory.events` của cgroup) cho số đúng và gần như không tốn gì. User muốn biến cách đo này thành một công cụ dùng lại được, đo tới từng bộ phận để biết mỗi phần tốn bao nhiêu, với yêu cầu **không lấy tài nguyên của phần hoạt động chính**.

Công cụ `resource-meter` đo ba mức:

| Mức | Số đo | Nguồn |
|---|---|---|
| Container (mọi container trên máy) | RAM (anon, file cache, kernel), số lần chạm trần, `oom_kill`, CPU, đọc/ghi đĩa, áp lực tài nguyên (PSI) | `/sys/fs/cgroup/system.slice/docker-<id>.scope/{memory.stat,memory.current,memory.events,cpu.stat,io.stat,*.pressure}` |
| Tiến trình, gắn với job và bước Dagster | RAM đỉnh (`VmHWM`), RSS theo thời gian, CPU, đọc/ghi đĩa, thời gian sống | `/proc/<pid>/{status,stat,io,cmdline,environ,cgroup}` |
| Model dbt | Thời gian từng model (chính xác), RAM đỉnh và CPU trong khoảng chạy model (ước lượng tốt vì dbt chạy `threads: 1`) | Ghép chuỗi mẫu của tiến trình dbt với `run_results.json` |

## Đã chốt (user, 16/10/2026)

1. Phạm vi lần đầu gồm cả mức model dbt.
2. Chạy nền liên tục.
3. Lưu nhẹ, không phải cài thêm gì để xem: file văn bản nén theo ngày, xem bằng chính lệnh `resource-meter report`.
4. Tự viết bằng Rust, không dùng cAdvisor/Prometheus (vài trăm MB RAM) hay `below` (không biết job Dagster và model dbt).
5. User duyệt plan 17/10/2026, làm **song song** với các plan đang chạy (worktree riêng).

## Yêu cầu bắt buộc

1. **Không lấy tài nguyên của phần chính.** Chạy trên host, ngoài mọi container, unit systemd riêng có `MemoryMax=32M`, `CPUQuota=2%`, `Nice=19`, `IOSchedulingClass=idle`. Mục tiêu đo được: RSS < 10 MB, CPU trung bình < 0,2% một nhân, ghi đĩa < 5 MB/ngày sau nén. Công cụ ghi chính số đo của nó (dòng `self`).
2. **Chỉ đọc.** Không ghi vào cgroup, không gửi tín hiệu, không gọi Docker API, không mở DuckDB, không ghi vào lake, `app_data` hay repo. Lỗi đọc một file (tiến trình vừa thoát, container vừa tạo lại) chỉ bỏ qua mẫu đó.
3. **Không cài thêm gì.** Một file chạy tĩnh; dependency Rust tối thiểu (ưu tiên chỉ `std` + một crate nén gzip). Không cần Python, DuckDB hay dịch vụ nào để xem kết quả.
4. Không đụng container, không cần khởi động lại gì. Cài và gỡ chỉ là bật/tắt một unit systemd (user chạy `sudo`, vì `/proc/<pid>/io` và `environ` của tiến trình root cần quyền root).
5. Không ghi nội dung `environ` ra file; chỉ trích đúng các biến nhận diện (`DAGSTER_RUN_ID` và tương tự nếu có). Không lưu dòng lệnh đầy đủ (có thể chứa instance-ref dài, đường dẫn): chỉ lưu tên rút gọn và khoá nhận diện.
6. Code ở `tools/resource-meter/` trong repo (crate Rust riêng, không đụng build Docker). Làm trên worktree nhánh `feat/resource-meter`, không trên checkout prod.
7. Tài liệu cập nhật cùng commit: `tools/resource-meter/README.md` và một mục trong `docs/operations/` (cách cài, gỡ, đọc báo cáo).
8. Không ghi plan ID, số phase vào code, test hay commit message.

## Lưu trữ

- Thư mục `/var/lib/resource-meter/` (ngoài repo, ngoài backup: số đo dùng xong bỏ được).
- Mỗi ngày một file TSV cho mỗi loại: `containers-YYYYMMDD.tsv`, `processes-YYYYMMDD.tsv`, `steps-YYYYMMDD.tsv`, `models-YYYYMMDD.tsv`. Ngày đã đóng được nén `.gz`. Giữ 90 ngày, tự xoá cũ hơn.
- TSV có dòng tiêu đề: đọc bằng `zcat`, `less`, hoặc DuckDB có sẵn trong container `data_platform` nếu muốn truy vấn, nhưng không bắt buộc.
- Ước lượng dung lượng: khoảng 20 container × mỗi 15 giây ≈ 115 nghìn dòng/ngày (≈ 10 MB thô, ≈ 1–2 MB nén); tiến trình chỉ ghi khi đang chạy bước Dagster hoặc vượt ngưỡng RSS.

## Lệnh

- `resource-meter run` (unit systemd gọi): vòng lấy mẫu.
- `resource-meter report [--date YYYY-MM-DD] [--container NAME] [--job NAME] [--top N]`: in bảng tóm tắt (đỉnh và trung bình RAM thật, CPU-giây, đĩa theo container; bước Dagster nặng nhất; model dbt nặng nhất).
- `resource-meter compare --base DATE --date DATE`: so hai ngày theo bước và model, đánh dấu phần tăng > 10%. Đây là câu "thêm luật/thêm khách thì phần nào nặng lên".
- `resource-meter status`: công cụ đang chạy không, tự nó tốn bao nhiêu.

## Phases

| # | Phase | File | Effort | Phụ thuộc | Đụng prod | Cần user |
|---|---|---|---|---|---|---|
| 0 | Kiểm thực địa: nhận diện bước Dagster và vị trí `run_results.json`, chốt định dạng | [phase-00](phase-00-field-check.md) | 0.25d | — | Chỉ đọc | — |
| 1 | Bộ thu mức container và tiến trình, ghi file, xoay vòng | [phase-01](phase-01-collector.md) | 1d | 0 | Không (chạy thử tay ngắn trên host) | — |
| 2 | Gắn số với job, bước Dagster và model dbt | [phase-02](phase-02-attribution.md) | 0.75d | 1 | Không | — |
| 3 | Lệnh `report`, `compare`, `status`; unit systemd; tài liệu | [phase-03](phase-03-report-and-install.md) | 0.5d | 2 | Có (cài unit) | **Duyệt giờ cài, chạy `sudo`** |
| 4 | Quan sát 7 đêm, kiểm chi phí của chính công cụ, đóng | [phase-04](phase-04-observe-and-close.md) | 0.25d + 7 đêm | 3 | Chỉ đọc | — |

Thứ tự ưu tiên: làm song song (user 17/10/2026); không đụng file của các plan khác.

## Tiêu chí chấp nhận

1. Sau 7 đêm chạy liên tục: RSS của công cụ < 10 MB, CPU trung bình < 0,2% một nhân, không lần nào chạm `MemoryMax` hay bị throttle quá 1% thời gian; thời gian nightly không đổi quá dao động bình thường (so trung vị 7 đêm trước khi cài).
2. Số mức container khớp đọc tay `memory.stat`/`memory.events` cùng thời điểm (sai lệch < 1%).
3. Mọi bước của `pipeline_batch_nightly_job` trong 7 đêm đều có dòng trong `steps-*.tsv` với run id và step key đúng như Dagster UI; job chạy `in_process_executor` có dòng ở mức job.
4. Mỗi model dbt chạy trong nightly có dòng trong `models-*.tsv`; thời gian khớp `run_results.json`; với các model chạy > 3 giây có RAM đỉnh khác 0.
5. `resource-meter report` và `compare` chạy trên host không cần cài thêm gì, trả kết quả < 2 giây cho một ngày.
6. Không file kết quả nào chứa nội dung `environ`, mật khẩu hay dòng lệnh đầy đủ (`grep` theo mẫu cho 0 dòng).
7. Gỡ được bằng `systemctl disable --now` + xoá thư mục, không để lại gì.

## Rủi ro chính

| Rủi ro | Khả năng × Ảnh hưởng | Cách giảm |
|---|---|---|
| Không nhận diện được bước Dagster từ dòng lệnh hoặc biến môi trường | Trung bình × Trung bình | Phase 0 kiểm thật trong một nightly; phương án dự phòng: ghép theo thời gian với nhật ký sự kiện của Dagster (đọc qua `dagster` CLI hoặc API, chỉ sau nightly) |
| Model dbt ngắn hơn khoảng lấy mẫu | Chắc chắn × Thấp | Tiến trình dbt được lấy mẫu mỗi 1 giây; model < 1 giây chỉ có thời gian, RAM để trống |
| Container tạo lại làm đổi id cgroup | Chắc chắn × Thấp | Quét lại danh sách `docker-*.scope` mỗi vòng, map id → tên qua `/proc/<pid>/cgroup` và tên trong file config của Docker (chỉ đọc); không gọi Docker API |
| Hai Dagster trên cùng máy (FG và `nu-*`) | Chắc chắn × Thấp | Gắn tiến trình với container qua `/proc/<pid>/cgroup` trước khi gắn với job |
| Công cụ lỗi rò bộ nhớ | Thấp × Thấp | `MemoryMax=32M` giết riêng công cụ, systemd khởi động lại; tiêu chí 1 |

## Rollback

`sudo systemctl disable --now resource-meter`, xoá `/var/lib/resource-meter/` và file unit. Không có gì trong container hay dữ liệu cần hoàn tác.

## Câu hỏi mở

1. Có muốn sau này đưa bảng tóm tắt lên một trang Evidence không? Ngoài phạm vi plan này; TSV đã đủ để làm sau.
