---
phase: 8
title: "Xoá đường SQL cũ, monitor đối chiếu và biến chuyển đổi"
status: pending
priority: P2
effort: "0.75d"
dependencies: [7]
---

# Phase 8: Xoá đường SQL cũ

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `transformation/docs/TAXONOMY.md` (mục `customer_type`: không còn khối SQL, luật ở seed tenant, bảng "Vị trí và hash" thay bằng đường dẫn seed và `rule_id`; mục `is_us_gift_recipient`: còn khối ở `int_us_shipment_line_prices.sql`, bỏ hai khối của `dim_customers`; Known divergences #6 ghi lại hai domain bộ máy; §3 bảng tổng quan; §6 literal `CTN00014`, `KY_GUI`, `'US'` giờ ở seed tenant; §10 bỏ mục "hai khối customer_type là ứng viên đầu tiên"); `scripts/checks/taxonomy_inventory.yaml`; `docs/architecture/taxonomy-engine.md` (pilot hoàn tất, bài học, chỗ cần làm khi thêm domain); `docs/architecture/modules.md` §9 (bộ máy là thành phần đang chạy) và §10 (bỏ logic hook CROSSBORDER khỏi danh sách hook của tenant: luật nằm ở seed tenant, đặc trưng `channels_ordered_on` là đặc trưng chung).

## Mục tiêu

Sau 30 ngày ổn định, xoá các khối `CASE` cũ, biến `taxonomy_engine_customer_type`, bản sao trong monitor và bảng log đối chiếu, để `customer_type` chỉ còn là luật dạng dữ liệu. Giữ `monitor_taxonomy_unmapped` và `entity_labels`.

## Điều kiện vào phase

- Phase 7 đủ 30 ngày, nhật ký sự cố không quá một sự cố quy cho bộ máy, log đối chiếu 0 khác biệt mọi ngày.

## Files

- Modify: `transformation/models/core/marts/dim_customers.sql` — bỏ nhánh `else` (khối `CASE` L215–230 cũ, biểu thức `is_us_gift_recipient` cũ) và CTE `us_channel_customers`; join `lbl_customer_type` không còn bọc `if`.
- Modify: `transformation/models/core/marts/sales/fact_orders.sql` — CTE `customer_type_info` chỉ còn `SELECT ... FROM lbl_customer_type__group_blob`; giữ nguyên comment về lý do dùng bản blob (tránh vòng) với nội dung cập nhật.
- Modify: `transformation/models/core/marts/intermediate/int_customer_benchmarks.sql` — bỏ khối `CASE` cũ và comment sai "mirrors dim_customers.sql exactly" (`TAXONOMY.md` §10 đã ghi việc sửa comment này đi cùng lần gộp).
- Modify: `transformation/dbt_project.yml` — xoá biến `taxonomy_engine_customer_type`.
- Delete: `transformation/models/monitoring/monitor_taxonomy_parity.sql`, `monitor_taxonomy_parity_log.sql` và mục của chúng trong `monitoring/schema.yml`, `model_buckets.yaml`.
- Modify: `scripts/checks/taxonomy_inventory.yaml` — bỏ các khối `customer_type` (ba khối gốc, hai bản sao), hai khối `is_us_gift_recipient` của `dim_customers` và bản sao; giữ khối `int_us_shipment_line_prices.sql`; giữ `customer_type` trong `columns` để `WARN new` vẫn bắt ai viết lại khối `CASE` gán `customer_type`.
- Modify: tài liệu ở đầu file.

## Các bước

1. Rebase lên `main`; sửa ba model và xoá biến, monitor.
2. Chạy `check_taxonomy_inventory.py`: sau khi cập nhật inventory, không còn `WARN`; `grep` không còn `CASE` nào gán `customer_type` trong `transformation/models/`.
3. Gate: `gate.sh S --allow-code-change` (compiled SQL đổi; hai model monitor biến mất là node bị xoá, kiểm cách `dbt_inventory.py` báo node bị xoá và ghi lại).
4. Deploy theo runbook, ngoài 02:30–04:00; kiểm như phase 7. Sau deploy, `DROP TABLE` bảng `monitor_taxonomy_parity_log` còn sót ở lần dừng container kế tiếp (không ai đọc).
5. Dọn môi trường: `scripts/shadow/cleanup.sh`, xoá worktree của plan (PII của bản sao shadow không giữ lâu hơn cần thiết).
6. Cập nhật `status` của plan theo CLI plan của repo.

## Verification

- Gate S: golden 83/83 0 khác biệt; full-refresh, lake trống pass.
- `check_boundaries.py`, `check_taxonomy_rules.py`, `check_taxonomy_inventory.py` (không `WARN`), pytest pass.
- Sau deploy: nightly xanh, `row_trend_checks` trong ngưỡng, phân bố `customer_type` bằng số nền.
- Tiêu chí nghiệm thu 5 của `plan.md`: không còn khối `CASE` gán `customer_type` trong `transformation/models/`.

## Đổi số?

**Không.** Đường bộ máy đã chạy 30 ngày; gate chứng minh lại.

## Rollback

`git revert` commit của phase này theo runbook: đường SQL cũ và biến quay lại (biến về `true` như cuối phase 7), monitor đối chiếu được tạo lại; bảng log tạo lại rỗng.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Mất khả năng quay lại nhanh bằng biến | Chỉ làm sau 30 ngày sạch; revert commit vẫn là đường lui |
| `dbt_inventory.py` coi node bị xoá là `DIFF` | Bước 3 kiểm; nếu harness chưa có cờ cho node bị xoá, ghi rõ trong commit message và xác nhận bằng golden |

## Effort

0.75 ngày (0.25 sửa và xoá, 0.25 inventory và tài liệu, 0.25 gate, deploy, dọn shadow).
