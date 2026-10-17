# Phase 3: lệnh xem kết quả, cài systemd, tài liệu

**Effort:** 0.5d · **Phụ thuộc:** phase 2 · **Đụng prod:** có (cài unit trên host, không đụng container) · **Cần user:** duyệt giờ cài, chạy `sudo`

## Yêu cầu

1. `report`, `compare`, `status` như mô tả trong `plan.md`, đọc thẳng TSV và `.gz`, in bảng văn bản. `compare` đánh dấu bước hoặc model tăng > 10% về thời gian, RSS đỉnh hoặc CPU-giây.
2. Unit `tools/resource-meter/resource-meter.service`: `ExecStart=/usr/local/bin/resource-meter run`, `Restart=always`, `MemoryMax=32M`, `CPUQuota=2%`, `Nice=19`, `IOSchedulingClass=idle`, `ProtectSystem=strict`, `ReadWritePaths=/var/lib/resource-meter`, `ProtectHome=read-only`, `NoNewPrivileges=yes`. Chạy root vì cần `/proc/<pid>/io` và `environ` của tiến trình root.
3. Script cài `tools/resource-meter/install.sh` (build release, chép file chạy, chép unit, `systemctl enable --now`) và gỡ (`--uninstall`). User tự chạy bằng `sudo`.
4. Tài liệu: `tools/resource-meter/README.md` (đo gì, đọc file thế nào, ví dụ `report`/`compare`), và một mục ngắn trong `docs/operations/` (vị trí theo mục lục hiện có; `deployment.md` đã > 800 dòng nên không thêm vào đó) trỏ tới README.

## Cài

Ngoài 02:30–04:00, vào giờ user duyệt. Sau khi cài: `status` báo chạy; 15 phút sau `report` có dữ liệu container; không container nào khởi động lại.
