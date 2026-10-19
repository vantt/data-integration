# Đồng hồ đo tài nguyên (resource-meter)

> Một file chạy Rust nằm trên host, ngoài mọi container. Nó đo RAM, CPU và đĩa theo từng container, từng bước Dagster và từng model dbt, rồi ghi file TSV theo ngày vào `/var/lib/resource-meter/`. Công cụ chỉ đọc: số của kernel (cgroup v2, `/proc`), sự kiện của Dagster (GraphQL qua loopback) và `run_results.json` của dbt. Nó không đụng container hay dữ liệu, và bị giới hạn cứng để không lấy tài nguyên của nền tảng.
>
> Code và tài liệu đầy đủ (từng cột của từng file, cách gắn số với bước và model): [tools/resource-meter/README.md](../../tools/resource-meter/README.md).

## Khi nào dùng

- **Xem RAM thật của container.** `memory.peak` tính cả page cache nên luôn sát trần. Hãy xem cột `RAM` (`anon`) và `HIT LIMIT` trong `report` thay cho `memory.peak`.
- **Tìm phần nặng.** Bước Dagster hay model dbt nào nặng nhất trong ngày.
- **So hai ngày** sau khi thêm luật, thêm khách hay thêm model: phần nào nặng lên quá 10%.

## Cài, nâng cấp, gỡ

Không cài trong khung nightly 02:30–04:00; script tự từ chối trong khung này, trừ khi thêm `--force`. Việc cài không đụng container và không khởi động lại gì ngoài unit của chính công cụ.

```bash
cd /home/vantt/app/fg-dataware-house/tools/resource-meter
cargo build --release                      # bằng user thường (root không có Rust)
sudo ./install.sh                          # cài hoặc nâng cấp: chép binary và unit, enable, restart
resource-meter status                      # sau 1 phút: "running"
resource-meter report                      # sau 15 phút: có bảng container
```

Gỡ:

```bash
sudo ./install.sh --uninstall              # giữ dữ liệu trong /var/lib/resource-meter
sudo ./install.sh --uninstall --purge      # xoá cả dữ liệu
```

Unit `resource-meter.service` chạy bằng root. Giới hạn và quyền:

- Tài nguyên: `MemoryMax=32M`, `CPUQuota=2%` với `CPUQuotaPeriodSec=1s` (20 ms mỗi giây, đủ cho một lần quét), `Nice=19`, `IOSchedulingClass=idle`.
- Hệ thống file chỉ đọc, trừ `/var/lib/resource-meter`. Cgroup cũng chỉ đọc.
- Chỉ giữ hai capability: `CAP_SYS_PTRACE` và `CAP_DAC_READ_SEARCH`.
- Mạng chỉ loopback.

Log: `journalctl -u resource-meter`.

## Đọc báo cáo

Không cần sudo. Mỗi lệnh chạy khoảng 0,1 giây cho một ngày.

```bash
resource-meter status                                   # có chạy không, tự tốn bao nhiêu, có chạm MemoryMax không
resource-meter report --date 2026-10-18 --top 10        # container, bước nặng nhất, model nặng nhất
resource-meter report --job pipeline_batch_nightly_job  # chỉ nightly
resource-meter compare --base 2026-10-18 --date 2026-10-25
```

- **Containers.** Đọc cột `RAM PEAK` / `RAM P50` (RAM thật). `+CACHE PEAK` là `memory.current`, có tính page cache. `HIT LIMIT` là số lần chạm `memory.max` trong ngày; `OOM KILL` khác 0 mới là sự cố thật.
- **Steps.** `RSS PEAK` là đỉnh RAM của cả cây tiến trình của bước, kể cả dbt. `(run_worker)` là chi phí của chính tiến trình điều phối một run. `*` là cả một job chạy `in_process_executor`.
- **Models.** Chỉ có các model chạy từ 0,1 giây. RAM chỉ có với model chạy từ 1 giây trở lên.
- **compare.** So trung vị mỗi run giữa hai ngày. Cột `HEAVIER` cho biết số nào tăng quá ngưỡng: `time`, `rss` hoặc `cpu`.

## Khi có vấn đề

- **`status` báo `NOT RUNNING`.** Xem `systemctl status resource-meter` và `journalctl -u resource-meter`. Unit tự khởi động lại sau 10 giây.
- **`MemoryMax reached` khác 0.** Công cụ đã chạm 32 MB, bị giết riêng rồi được khởi động lại; nền tảng không bị ảnh hưởng. Ghi lại để xem xét.
- **Cột `read_bytes` trống trong `processes-*.tsv`.** Xem mục "Install and uninstall" trong README của công cụ.
- **Bước thiếu `job`/`step_key`.** Dagster GraphQL (127.0.0.1:3000) không trả lời. Công cụ thử lại mỗi 5 phút trong 12 giờ, rồi mới ghi dòng không có khoá.
