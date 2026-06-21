# Phase 01 — Warehouse Scoring Foundation

> Status: ⛔ BLOCKED (chờ chốt objective ladder — discussion §14.2)
> Phụ thuộc: — · Chặng ① trong pipeline
> Context: [`discussion.md`](./discussion.md) §3, §6, §7, §10, §12

## Mục tiêu

Warehouse làm **tối đa năng lực**: sản xuất điểm nền (population-relative) + candidate objectives đã chấm điểm, để CRM chỉ cần phủ lớp mỏng lên trên. Đổi vai `mart_customer_action_queue` từ "quyết định cuối" → "ứng viên đã chấm điểm".

## Key insights

- Warehouse là **vua điểm tương đối toàn dân** (percentile, rank, cohort) — CRM không làm được.
- `predicted_next_purchase_date` + `avg_days_between_orders` đã có → khai thác cho "đón đầu" tái bán.
- Giữ scoring inputs + `value_at_stake`; chỉ chuyển *quyết định action cuối* ra khỏi SQL.

## Phạm vi (locked)

**Thêm cột vào `dim_customers` (hoặc mart scoring riêng):**
- `value_percentile` (rank toàn tập theo lifetime_value)
- `churn_score` (heuristic vs cohort — KHÔNG ML)
- `overdue_severity` (số σ recency vượt `avg_days_between_orders`)
- `base_priority_score` (tổng hợp các điểm trên, 0–100)

**Đổi `mart_customer_action_queue`:**
- Output **candidate objectives** mỗi khách (có thể >1) kèm `base_score`, `value_at_stake`, `reason_fragments[]` (cấu trúc, KHÔNG string template)
- Giữ `priority_rank` nhưng đổi nghĩa = **base ordering mặc định** (dùng khi khách chưa có state CRM)

**Reason fragments có cấu trúc** thay `rationale_vi` string.

## Related code files

- Sửa: `transformation/models/marts/core/dim_customers.sql`
- Sửa: `transformation/models/marts/customer/mart_customer_action_queue.sql`
- Sửa (đồng bộ cột mới): `crm/sync/reverse_etl_warehouse_to_crm.py`, reader serving views (xem memory: bootstrap_serving_views sau rename cột)
- Kiểm: dbt manifest reload (restart data_platform sau khi thêm node)

## Todo (draft)

- [ ] Chốt objective taxonomy + ladder (§14.2) ← gate
- [ ] Thêm scoring cột vào dim_customers + test
- [ ] Reframe action_queue → candidate objectives + reason fragments
- [ ] Sync cột mới sang cache.db
- [ ] dim_customers incremental: thêm cột mới cần `--full-refresh` (xem memory)

## Success criteria

- Mỗi khách (RETAIL, có đơn) có `base_priority_score` + ≥1 candidate objective với reason fragments.
- Không phá KPI/recon hiện có; serving views rebuild sạch.

## Rủi ro

- Thêm cột vào incremental mart chỉ backfill row đổi → cần full-refresh thủ công trong container.
- Đừng dùng `fact_payments` (rỗng) hay `customer_type` (dở) làm input scoring.

## Open

- Objective taxonomy cuối + thứ tự ưu tiên cứng (§14.2).
- Công thức `base_priority_score` (trọng số các thành phần).
