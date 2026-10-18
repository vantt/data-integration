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
