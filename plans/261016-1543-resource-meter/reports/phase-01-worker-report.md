# Phase 1: bộ thu mức container và tiến trình — báo cáo worker

**Ngày:** 17/10/2026 (Asia/Saigon) · **Worktree:** `/home/vantt/app/fg-dw-meter` (nhánh `feat/resource-meter`, chưa commit) · **Trạng thái:** xong

## Kết quả

Crate `tools/resource-meter/` có lệnh `resource-meter run`, chạy được trên host. Lệnh này ghi `containers-YYYYMMDD.tsv` (mọi container, mỗi 15 giây, kèm dòng `self` mỗi phút) và `processes-YYYYMMDD.tsv` (một dòng khi tiến trình của run Dagster thoát). File ngày cũ được nén gzip, file quá 90 ngày bị xoá. Lần chạy tay 200 giây trên host bằng user `vantt` đo được RSS 1,4 MB và CPU 0,05% một nhân, file ra không chứa dòng lệnh hay bí mật.

## File (chỉ trong `tools/resource-meter/`)

| File | Dòng | Nội dung |
|---|---|---|
| `Cargo.toml`, `Cargo.lock` | 21, — | 2 dependency: `flate2` (backend Rust thuần, không cần zlib/C) và `serde_json`; release `lto`, `panic=abort`, `strip` |
| `.cargo/config.toml` | 3 | `+crt-static`: glibc liên kết tĩnh, binary ra `static-pie` (đã kiểm bằng `file`), không cần target musl |
| `rustfmt.toml` | 1 | `max_width = 120` |
| `src/main.rs` | 110 | CLI `run` và các tuỳ chọn, kiểm giá trị đầu vào |
| `src/collector.rs` | ~580 | vòng lặp một thread: 15 giây / 1 giây / 250 ms / 60 giây; ghi dòng, xoay ngày; log lỗi chống lặp |
| `src/tracker.rs` | ~700 | theo dõi tiến trình qua `cgroup.procs`, phân vai trong cây Dagster, gắn `run_id`/`file_key`, vòng đệm mẫu, phát hiện thoát và PID dùng lại |
| `src/procfs.rs` | ~500 | parse `status` (kèm `NSpid`), `stat`, `io`, `btime`; phân loại tiến trình thành tên rút gọn |
| `src/cgroup.rs` | ~210 | parse `memory.stat/events`, `cpu.stat`, `io.stat` (cộng mọi thiết bị), PSI `some`/`full` |
| `src/containers.rs` | ~185 | liệt kê `docker-<64 hex>.scope`, đọc một container, tên từ `config.v2.json` |
| `src/tsv.rs` | ~310 | ghi dòng TSV an toàn (ký tự điều khiển bị thay), file theo ngày, gzip qua `.tmp` rồi rename, xoá theo hạn giữ |
| `src/clock.rs` | ~105 | ngày địa phương theo độ lệch UTC cố định, chuyển đổi `YYYYMMDD` |
| `src/test_support.rs` | ~107 | cây thư mục giả cho test |
| `README.md` | ~150 | đo gì, nhịp lấy mẫu, cách nhận diện cây Dagster, cột của từng file, quyền root, chi phí đo được |

Không file nào ngoài `tools/` bị sửa, nên `scripts/checks/run-all.sh` không cần chạy. Thư mục build bị `.gitignore` gốc bỏ qua.

## Yêu cầu của phase và cách đáp ứng

1. **Hai nhịp:** mọi container mỗi 15 giây (`memory.current`, anon/file/kernel/shmem, `memory.max`, max/oom/oom_kill, `usage_usec`/`throttled_usec`/`nr_throttled`, rbytes/wbytes, PSI avg10). Tiến trình của run mỗi 1 giây; tiến trình dbt mỗi 250 ms trong lúc còn chạy (theo quyết định của user). Tiến trình dịch vụ lâu dài lấy mẫu mỗi 15 giây.
2. **Phát hiện tiến trình:** đọc `cgroup.procs` của container được theo dõi mỗi 1 giây, đúng đề xuất của phase 0, thay cho quét `/proc` mỗi 5 giây. Không bao giờ quét `/proc`.
3. **Dòng tổng kết khi thoát:** gồm thời gian sống (start lấy từ `btime` + `starttime`), `VmHWM`, RSS mẫu lớn nhất, CPU-giây, đĩa. Mẫu chỉ giữ trong bộ nhớ: tối đa 4.096 mẫu mỗi tiến trình, tối đa 2.000 tiến trình; phase 2 sẽ dùng.
4. **`containers-*.tsv`** mỗi 15 giây, kèm dòng `self` mỗi 60 giây và khi dừng.
5. **Qua ngày:** đóng file, gzip mọi `.tsv` của ngày trước (ghi đè `.gz` dở nếu có), xoá file cũ hơn `--retention-days`. Việc này cũng chạy khi khởi động, nên bù được những ngày công cụ không chạy.
6. **Ghi thêm dòng và flush mỗi nhịp:** mất điện chỉ mất tối đa một nhịp.
7. **Một thread**, không async, không thread pool; ngủ tới mốc gần nhất.

Theo phase 0 và các quyết định của user:

- `NSpid` được lưu thành `ns_pid` và `ns_ppid`, khớp với pid Dagster ghi trong sự kiện.
- **Không đọc `environ`** ở bất cứ đâu.
- Không lưu dòng lệnh. Tên rút gọn không chứa đường dẫn, ví dụ `dbt build`, `mp-spawn`, `refresh_rolling.py`. Danh sách `--select` của dbt bị bỏ; có test riêng kiểm điều này.
- `run_id` và `file_key` lấy từ đường dẫn của `tail` compute-log, rồi truyền cho run worker và mọi tiến trình con cháu.
- Tên container chỉ lấy trường `Name` của `config.v2.json` (có kiểm ký tự hợp lệ). Không có root thì dùng `cid12`.

## Test

- `cargo test`: **36/36 pass**, dùng cây `/proc` và cgroup giả mô phỏng đúng cây thật thấy ở phase 0 (grpc → run worker → step → tail/dbt). Các trường hợp được phủ:
  - phân vai khi `cgroup.procs` không theo thứ tự;
  - gắn `run_id`/`file_key` cho step, run worker và dbt;
  - executor in-process (`file_key` thuộc run worker);
  - vòng đệm giữ đúng N mẫu mới nhất;
  - tổng kết lúc thoát (RSS max, HWM, CPU, io, `last_seen`);
  - PID bị dùng lại, tiến trình biến mất giữa hai nhịp;
  - tiến trình `exec` sau khi đã được phát hiện (phân loại lại);
  - giới hạn số tiến trình; container biến mất làm kết thúc tiến trình của nó;
  - ghi file thật: tiêu đề, số cột, ô trống, dòng `self`, và kiểm không lọt `--select` hay `PASSWORD`;
  - gzip, xoá theo hạn, ghi đè `.gz` dở, file lạ không bị đụng;
  - parser của từng file, chuyển ngày, kiểm tham số khởi động.
- `cargo clippy --all-targets -- -D warnings`: sạch. `cargo fmt --check`: sạch.
- `cargo build --release`: binary `static-pie linked, stripped`.

## Chạy tay trên host

Chạy 21:40:01–21:43:21 ngày 17/10, user `vantt`, `nice -n 19`, `--duration 200`, ra `scratchpad/meter`. Có job realtime của Dagster chạy thật trong lúc đo, không kích hoạt job nào.

- **Chi phí của chính công cụ:** RSS 1.456 kB (HWM giống hệt), CPU tổng 10 tick = 0,10 giây trong 199 giây, tức 0,05% một nhân. Mục tiêu là RSS < 10 MB và CPU < 0,2%.
- **Ra đĩa:** `containers` 43.657 byte (294 dòng = 14 nhịp × 21 container, cộng 4 dòng `self`); `processes` 5.599 byte (38 dòng). Ước một ngày khoảng 18 MB thô cho `containers` và 2,4 MB thô cho `processes`; theo tỉ lệ nén của mẫu (khoảng 6,8× và 4×), tổng khoảng 3 MB/ngày sau gzip, dưới mục tiêu 5 MB.
- **So với đọc tay** (`cat` cùng lúc, mỗi giây): ở mốc `1792248016`, `file` công cụ đọc là 4.345.905.152, khớp từng byte với đọc tay ở giây :15. `memory.current`, `anon` và `cpu_usage_usec` nằm giữa hai lần đọc tay :15 và :16. RAM `data_platform` lúc đó dao động hàng trăm MB mỗi giây vì có run đang chạy, nên không thể so cùng một khoảnh khắc. `ev_max` 62.150 khớp. Phase 4 sẽ kiểm tiêu chí < 1% lúc container yên.
- **Tiến trình:** 4 `run_worker`, 24 `step`, 6 `dbt` (`version`, `parse`, `build`, mỗi loại 2), 4 `step_child`. **Mọi dòng đều có `run_id`.** Có `file_key` cho step dài (dbt, ingest); các step asset check khoảng 2 giây kết thúc trước khi `tail` của chúng được thấy, nên `file_key` trống. Phase 2 vẫn ghép được qua `(run_id, ns_pid)` với `LogsCapturedEvent.pid`. Không có root nên cột `read_bytes`/`write_bytes` trống và tên container hiện là `cid12`, đúng như thiết kế.
- **Rò rỉ:** `grep -ciE -- "--select|password|secret|/app/|/usr/|instance_ref|spawn_main"` trên các file ra cho 0 dòng.
- Sau khi refactor nhỏ, chạy lại 30 giây (21:44:48–21:45:18): bình thường. Không còn tiến trình nào của công cụ chạy.

## Lệch so với plan

- **Dòng `self`** dùng lại cột của `containers`: `mem_current` là RSS, `mem_max` là VmHWM, `cpu_usage_usec` là CPU của chính công cụ, `io_*` là đĩa của nó. README đã ghi rõ.
- Ước tính trong plan là khoảng 10 MB thô mỗi ngày; thực tế khoảng 18 MB thô cho `containers`, vì mỗi dòng có 21 cột. Sau nén vẫn khoảng 3 MB/ngày, dưới mục tiêu 5 MB.
- Đã thêm `rustfmt.toml` (độ rộng 120) và `.cargo/config.toml` (liên kết tĩnh).

## Việc cho phase sau

- **Phase 2:**
  - Truyền tiến trình đã thoát kèm `samples` sang phần gắn bước và model. Hiện collector bỏ `samples` sau khi ghi dòng tổng kết.
  - Thêm GraphQL qua `std::net::TcpStream`.
  - Tìm `transformation/target/sapo_dbt_assets-<run7>-*`.
- **Phase 3:** `report`/`compare`/`status` đọc cả `.tsv` lẫn `.tsv.gz`, và bỏ qua dòng cuối dở nếu có (sau mất điện). `status` lấy chi phí của công cụ từ dòng `self`.

Status: DONE
Summary: Collector Rust (`tools/resource-meter/`, std + `serde_json` + `flate2`, binary static-pie) ghi `containers`/`processes` theo ngày, nén gzip và xoá theo hạn. 36 test pass, clippy sạch; chạy tay 200 giây trên host đo được RSS 1,4 MB và CPU 0,05%, không lọt dòng lệnh hay bí mật.
Concerns/Blockers: Kiểm sai lệch < 1% so với đọc tay mới làm được gần đúng, vì RAM container đổi rất nhanh khi có run; phase 4 sẽ kiểm lại lúc container yên.
