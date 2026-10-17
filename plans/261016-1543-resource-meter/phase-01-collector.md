# Phase 1: bộ thu mức container và tiến trình

**Effort:** 1d · **Phụ thuộc:** phase 0 · **Đụng prod:** không (chạy thử tay ngắn trên host, chỉ đọc)

## File

- Tạo `tools/resource-meter/` (Cargo.toml, `src/`, `README.md`). Tên file Rust theo snake_case.

## Yêu cầu

1. Vòng lặp hai nhịp:
   - Mỗi 15 giây: mọi container (`memory.current`, `memory.stat` → anon/file/kernel, `memory.events` → max/oom/oom_kill, `cpu.stat` → usage_usec/throttled_usec, `io.stat` → rbytes/wbytes, PSI `some avg10`).
   - Mỗi 1 giây: chỉ các tiến trình được theo dõi (tiến trình bước Dagster và con cháu của nó, tiến trình dbt). Đọc `/proc/<pid>/status` (VmRSS, VmHWM), `stat` (utime, stime), `io` (read_bytes, write_bytes).
2. Phát hiện tiến trình mới bằng quét `/proc` mỗi 5 giây, lọc theo cgroup của `data_platform` (và về sau container khác nếu cấu hình). Không quét `/proc` mỗi giây.
3. Khi tiến trình thoát, ghi một dòng tổng kết (thời gian sống, RSS đỉnh, CPU-giây, đĩa) vào `processes-YYYYMMDD.tsv`. Mẫu theo giây chỉ giữ trong bộ nhớ (vòng đệm có giới hạn) cho phase 2, không ghi ra đĩa.
4. Ghi `containers-YYYYMMDD.tsv` mỗi nhịp 15 giây; mỗi phút ghi thêm một dòng `self` (RSS, CPU của chính công cụ).
5. Qua ngày: nén file ngày cũ thành `.gz`, xoá file cũ hơn 90 ngày.
6. Ghi theo kiểu thêm dòng, flush mỗi nhịp; mất điện chỉ mất tối đa một nhịp.
7. Không dùng thread pool hay async runtime; một thread, ngủ giữa các nhịp.

## Test

- Unit: parse `memory.stat`, `cpu.stat`, `io.stat`, `/proc/<pid>/status` từ fixture văn bản (số giả).
- Chạy tay trên host 10 phút (`sudo`, ngoài 02:30–04:00): so số container với đọc tay cùng lúc; đo RSS/CPU của chính công cụ.
