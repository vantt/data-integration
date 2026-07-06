# Verify — overhead allocation method (gỡ chặn P1)

> Verified 2026-06-11 by reading models + querying `sapo_export_latest.duckdb`.
> Source: `transformation/models/intermediate/overhead/int_order_overhead_allocation.sql`,
> `int_overhead_pool_monthly.sql`.

## Phương pháp
Overhead pool (chi phí chung MISA, theo tháng) chia xuống đơn theo `base_metric`:
- **net_revenue: 3 pools, 1,184M (98%)** — chia ∝ doanh thu đơn (revenue-weighted).
- order_count: 1 pool, 22M (2%) — chia đều.
- ACTUAL cho tháng đóng; ESTIMATED (trailing 3 tháng) cho tháng hiện tại.

## Distortion (verified, retail × has_cogs)

| Tier | net_rev TB | gross profit TB | overhead TB | gross margin | FL margin |
|---|---|---|---|---|---|
| VIP | 12.7tr | 7.2tr | **11.1tr** | **57%** | ~0% |
| GOLD | 7.3tr | 3.9tr | 1.7tr | 50% | −0.1% |
| SILVER | 3.4tr | 1.6tr | 0.9tr | 50% | +0.1% |
| BRONZE | 1.1tr | 0.24tr | 0.48tr | 30% | −0.3% |

Đơn VIP gánh overhead 11.1tr > gross profit 7.2tr — chỉ vì đơn TO + chia theo doanh thu. Gross margin VIP CAO NHẤT.

## Kết luận
- **"VIP/GOLD lỗ sau overhead" = ARTIFACT** của revenue-weighted allocation, không phải khách kém lãi.
- **"Shopee lỗ" = THẬT** — phí sàn là chi phí *trực tiếp*, không phải overhead chia.
- → **P1 mart customer dùng `contribution margin` (gross profit − phí trực tiếp), KHÔNG fully-loaded.** Fully-loaded giữ cho finance channel/company P&L.

## Sticky decision
Locked. Audit phản biện chỉ revise nếu: (a) phát hiện pool order_count thực ra chiếm tỷ trọng lớn hơn ở 1 segment cụ thể, hoặc (b) định nghĩa contribution cần trừ thêm chi phí trực tiếp khác (ship per-order) chưa surface.
