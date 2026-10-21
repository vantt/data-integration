# Phase 4 — quan sát sau cài đặt

## Cài đặt (18/10/2026 00:32)

User duyệt và tự cài sau khi `main` fast-forward lên `84b83cdf` (18/10 00:20). Unit
`resource-meter.service` active từ 00:32:00, `NRestarts` 0.

## Kiểm lần đầu (00:32–00:38, chỉ đọc)

- `resource-meter status` lúc 00:38: running, RSS 3 MB, CPU 0,050% một nhân, MemoryMax 0 lần,
  OOM 0. "NOT RUNNING" lúc 00:32 chỉ vì dòng self đầu tiên ghi sau 60 giây.
- Đã gắn số đo cho một run realtime (`pipeline_sapo_v2_realtime_job` `53d6ff83`): 28 dòng step,
  51 dòng model.
- Cột `read_bytes` có số (6/39 dòng process khác 0), nên giới hạn capability
  (`CAP_SYS_PTRACE CAP_DAC_READ_SEARCH`) đủ; không cần bỏ dòng `CapabilityBoundingSet`.
- Throttle: `status` báo tỉ lệ chu kỳ bị throttle (93,75% lúc khởi động, 43% lúc 00:38). Số này đo
  sai thứ: `nr_periods` chỉ đếm chu kỳ 100 ms mà công cụ có việc, nên một lần quét cần hơn 2 ms CPU
  là bị tính throttle dù trung bình chỉ dùng 0,05%. Tiêu chí 1 tính theo thời gian. Đo 5 phút ổn định
  (00:33:29–00:38:29, có một run realtime): CPU 161 ms / 300 s = 0,054%; `throttled_usec` tăng
  3,2 s / 300 s = 1,07% thời gian, sát ngưỡng 1%. Throttle chỉ làm trễ mẫu của chính công cụ (tối đa
  một chu kỳ 100 ms), không lấy CPU của container.

## Đề xuất (chờ user duyệt, chưa sửa unit trên host)

1. Thêm `CPUQuotaPeriodSec=1s` vào unit, giữ `CPUQuota=2%`: trần trung bình không đổi, nhưng mỗi
   giây có 20 ms thay vì 2 ms mỗi 100 ms, đủ cho một lần quét nên hết throttle.
2. Sửa `status` báo throttle theo `throttled_usec` / thời gian chạy của unit, đúng cách tính của
   tiêu chí 1, thay cho tỉ lệ chu kỳ.

## Đêm 1: nightly 18/10 03:01 (kiểm 09:5x, chỉ đọc)

- `status`: running, RSS 4 MB, unit peak 13 MB, MemoryMax 0 lần, OOM 0, CPU 0,055% một nhân.
  Throttle theo thời gian từ 00:32 (khoảng 9,4 giờ): `throttled_usec` 295 s, tức 0,87%, dưới ngưỡng
  1%; `status` vẫn báo 15,65% (tỉ lệ chu kỳ, như đã ghi ở trên).
- Dữ liệu ngày: 46.899 dòng container, 4.415 dòng process, 3.038 dòng step, 5.750 dòng model, 8 MB
  chưa nén.
- `read_bytes`: 932/4.415 dòng process khác 0.
- `report --job pipeline_batch_nightly_job` (nightly `d0b09efb`, 13,9 phút):
  - Bước dài nhất: `sapo__ingest_sapo_v2_orders_batch_asset` 604 s (RSS 535 MB, 14 CPU-s, tức là chờ
    API: phía Sapo sửa hàng loạt 2.606 đơn đúng lúc nightly chạy, xem ghi chú 18/10 trong
    `plans/261014-2225-taxonomy-engine/phase-06-prod-parallel-run.md`); `approach_script_autogen`
    182 s (codex lỗi cả 10 lần).
  - RSS cao nhất: `sapo_dbt_assets` 2,04 GB (36 s); model nặng nhất `src_sapo_v2_orders` 2,1 s,
    1,70 GB.
  - Container `data_platform` trong ngày: anon đỉnh 5,92 GB, kể cả cache 8,00 GB, chạm `memory.max`
    31.473 lần, OOM kill 0, PSI bộ nhớ tối đa 16,5. Lúc khởi động bước (03:02) CPU bị throttle
    mạnh (trần 4 nhân), sau đó container gần như rảnh trong lúc chờ Sapo (CPU khoảng 14%).
- Chưa có `compare` vì đây là ngày đầu có số đo.

## Đêm 2: nightly 19/10 03:00 (kiểm 09:5x, chỉ đọc)

- `status`: running, RSS 4 MB, unit peak 27 MB (dưới `MemoryMax` 32 MB), MemoryMax 0 lần, OOM 0,
  CPU 0,054% một nhân. Từ lúc cài (18/10 00:32, khoảng 33 giờ): CPU 65 s (0,055%), `throttled_usec`
  1.031 s, tức 0,86% thời gian, dưới ngưỡng 1%.
- `read_bytes`: 1.098/4.775 dòng process khác 0.
- `report --job pipeline_batch_nightly_job` (nightly `7928f479`, 5,2 phút): RSS cao nhất
  `sapo_dbt_assets` 1,65 GB (52,9 s tính cả khởi động tiến trình; Dagster ghi 32,8 s thực thi);
  dài nhất `approach_script_autogen` 179 s (codex vẫn chưa đăng nhập); model dài nhất
  `fact_fulfillments` 0,9 s.
- `compare --base 2026-10-18`: 25 bước nặng hơn quá 10%, đều là bước check asset và `sapo_dbt_assets`
  chậm hơn 30–780% về thời gian, RSS gần như không đổi. Đêm 18/10 các bước check của
  `orders_batch` chạy muộn và một mình (sau 9 phút chờ Sapo); đêm nay chúng khởi động cùng lúc nên
  tranh CPU lúc khởi động (trần 4 nhân). Tổng nightly 5,2 phút, bằng số nền. Hai model chỉ có ở đêm
  nay (`dim_sku_alias`, `int_sapo_inventories`) là do đêm trước chạy dưới 0,1 s nên không ghi.

## Đêm 3: nightly 20/10 03:00 (kiểm 09:5x, chỉ đọc)

- Unit chưa được cài lại bản `aa3a5cfb`: `status` vẫn báo theo chu kỳ (15,12%), unit peak 30 MB
  (dưới 32 MB), MemoryMax 0 lần, OOM 0, CPU 0,055% một nhân. `read_bytes`: 910/4.802 dòng process
  khác 0.
- `report --job pipeline_batch_nightly_job` (nightly `c633a631`, 2,4 phút, lần đầu có lịch sử
  giá/tồn và `approach_script_autogen` tắt): RSS cao nhất `sapo_dbt_assets` 1,72 GB (50,5 s tính
  cả khởi động; Dagster 36,5 s); model mới nặng nhất `fact_variant_price_changes` 1,1 s, 1,27 GB.
- `compare --base 2026-10-19`: 16 bước nặng hơn quá 10%, đều là bước check và bước file-drop chậm
  hơn khi khởi động cùng lúc (RSS không đổi); `approach_script_autogen` không còn tốn 3 phút. Mới:
  3 model lịch sử và check `capture_coverage` của snapshot sản phẩm.

## Đêm 4: nightly 21/10 03:00 (kiểm 09:4x, chỉ đọc)

- Unit vẫn là bản cũ (chưa cài lại `aa3a5cfb`). RSS 4 MB, CPU 0,054% một nhân, MemoryMax 0 lần,
  OOM 0. **Unit peak 32 MB, bằng `MemoryMax`** (13 → 27 → 30 → 32 MB qua 4 ngày) trong khi RSS chỉ
  4 MB: phần tăng là page cache của các file TSV đang ghi, tính vào cgroup. Chưa có sự kiện `max`;
  khi chạm, kernel thu hồi cache trước, không giết tiến trình (anon nhỏ). Theo dõi `max` trong
  `memory.events`; nếu tăng đều thì cân nhắc nâng `MemoryMax` hoặc dùng `MemoryHigh`.
- `read_bytes`: 927/4.756 dòng process khác 0.
- `report` (nightly `77e59cce`, 2,4 phút): `sapo_dbt_assets` 1,72 GB, 54,2 s tính cả khởi động
  (Dagster 37,0 s); model nặng nhất `fact_variant_price_changes` 1,2 s, 1,26 GB.
- `compare --base 2026-10-20`: 20 bước nặng hơn quá 10% về thời gian, toàn bước check ngắn (vài
  giây, dao động khởi động), RSS không đổi; không bước hay model nào nặng hơn đáng kể.
