# Phase 02 — Tag Signal → Action Queue Consumer (AI-9 core)

**Status:** TODO  **Priority:** P1  **Depends on:** phase-01 (customer_id resolution — chặn cứng, không compile được nếu thiếu)

## Context Links

- Master plan: `plans/260706-1738-crm-tag-signal-action-queue-consumer/plan.md`
- Mart cần sửa: `transformation/models/marts/customer/mart_customer_action_queue.sql`
- Staging nguồn: `transformation/models/staging/stg_crm__party_tag.sql` (sau phase-01, có `customer_id`)
- Badge convention (phase-09): `crm/src/adapters/inbound/web/badge_catalog.py` (`_CATALOG["action_type"]`, `_ACTION_TYPE_SHORT_LABEL`), `crm/src/application/task_service.py` (`_ACTION_TYPE_SHORT_LABEL` bản duplicate ở application layer)
- Design gốc: `crm/docs/ui-spec/notes/ux-action-queue-task-cockpit-data-loop-design.md` §5 consumption plan

## Quyết định áp dụng (đã chốt ở master plan, nhắc lại cho implementer)

1. Tag `vip_tier` → OR vào điều kiện VIP trong CASE logic hiện có (không tạo action_type mới, chỉ mở rộng điều kiện trigger).
2. Tag `risk` → action_type mới `MANUAL_RISK_REVIEW`, priority_rank đề xuất = 2 (ngay sau CALL_NOW=1), KHÔNG chặn các action_type khác.
3. 1 party có thể có nhiều tag cùng category → aggregate bằng `bool_or`/`MAX`, không nhân dòng.

## Requirements

1. Intermediate model mới `int_crm_party_tag_flags.sql` — 1 dòng/customer_id, cột: `customer_id, has_vip_tag BOOLEAN, vip_tag_labels VARCHAR (concat), has_risk_tag BOOLEAN, risk_tag_labels VARCHAR (concat), tags_updated_at`.
2. `mart_customer_action_queue.sql`:
   - Thêm CTE `tag_flags AS (SELECT * FROM {{ ref('int_crm_party_tag_flags') }})`.
   - JOIN vào `customers` CTE (LEFT JOIN theo `customer_id`, không phải `customer_key` — staging CRM dùng `customer_id` INTEGER, khớp `dim_customers.customer_id`).
   - Sửa CASE `action_type` (trong `classified` CTE): mọi điều kiện `value_group IN ('VALUE_VIP', 'VALUE_GOLD', 'VALUE_SILVER')` → `(value_group IN ('VALUE_VIP', 'VALUE_GOLD', 'VALUE_SILVER') OR has_vip_tag)`.
   - Thêm nhánh mới TRƯỚC `ELSE NULL`: `WHEN has_risk_tag THEN 'MANUAL_RISK_REVIEW'` — đặt sau các nhánh VIP/reorder hiện có nhưng trước `HIGH_CANCEL_RISK` nếu muốn risk-tag ưu tiên hơn cancel_rate tự động (quyết định thứ tự CASE = thứ tự ưu tiên khi 1 khách khớp nhiều điều kiện; đề xuất đặt NGAY SAU nhóm VIP, TRƯỚC `SECOND_ORDER`/`HIGH_CANCEL_RISK` — risk là tín hiệu người, đáng tin hơn heuristic).
   - Thêm `priority_rank` case: `WHEN 'MANUAL_RISK_REVIEW' THEN 2` (dịch các rank hiện tại 2-6 xuống nếu cần — QUYẾT ĐỊNH: giữ nguyên rank 1-6 cũ, `MANUAL_RISK_REVIEW` chèn = 2, các rank cũ 2-6 KHÔNG đổi số nhưng giờ đứng sau nó về thứ tự thực thi `ORDER BY priority_rank` — chấp nhận trùng rank tạm thời nếu đơn giản hơn, hoặc renumber 1-7 sạch. Implementer chọn renumber sạch (rõ ràng hơn): CALL_NOW=1, MANUAL_RISK_REVIEW=2, REORDER_NUDGE=3, REORDER_PREEMPT=4, WIN_BACK=5, SECOND_ORDER=6, HIGH_CANCEL_RISK=7, ELSE=9).
   - Thêm `action_rationale`: `WHEN 'MANUAL_RISK_REVIEW' THEN 'NV đánh giá rủi ro: ' || risk_tag_labels || ' — cần xác minh trước khi tiếp cận'`.
   - `value_at_stake`: `WHEN 'MANUAL_RISK_REVIEW' THEN ROUND(COALESCE(lifetime_value, 0))::BIGINT` (dùng lifetime_value thay avg_order_spend — rủi ro liên quan tổng giá trị khách, không phải 1 đơn).
3. `badge_catalog.py` — thêm entry `_CATALOG["action_type"]["manual_risk_review"] = BadgeDef("bad", "Cần xác minh rủi ro — NV đã tự đánh giá, không phải hệ thống tự động")`.
4. `_ACTION_TYPE_SHORT_LABEL` (badge_catalog.py, phase-09) — thêm `"manual_risk_review": "Cần xác minh"`.
5. `task_service.py` — bản duplicate `_ACTION_TYPE_SHORT_LABEL` ở application layer (phase-09 R5) — thêm cùng entry để task title fallback nhất quán.
6. `schema.yml` — thêm test cho `int_crm_party_tag_flags`: `customer_id` unique+not_null.

## Files to Modify / Create

### Create
- `transformation/models/marts/customer/int_crm_party_tag_flags.sql` (hoặc `transformation/models/intermediate/` nếu repo có layer riêng — kiểm tra convention hiện có trước khi đặt, mart hiện tại không có thư mục `intermediate/` riêng nên đặt cùng `marts/customer/` với tag `intermediate` để phân biệt)

### Modify
- `transformation/models/marts/customer/mart_customer_action_queue.sql`
- `crm/src/adapters/inbound/web/badge_catalog.py`
- `crm/src/application/task_service.py`
- `transformation/models/staging/schema.yml` (hoặc file schema.yml tương ứng thư mục marts nếu khác)

## Implementation Steps

### 1. `int_crm_party_tag_flags.sql`

```sql
{{ config(tags=['intermediate', 'crm'], materialized='view') }}

-- Gộp tag risk/vip_tier theo customer_id (1 dòng/customer, aggregate qua bool_or).
-- Party chưa link Sapo (customer_id NULL) bị loại — vô hình với action queue by design.
SELECT
    customer_id,
    bool_or(tag_category = 'vip_tier')                                   AS has_vip_tag,
    string_agg(DISTINCT CASE WHEN tag_category = 'vip_tier'
               THEN tag_display_label END, ', ')                          AS vip_tag_labels,
    bool_or(tag_category = 'risk')                                        AS has_risk_tag,
    string_agg(DISTINCT CASE WHEN tag_category = 'risk'
               THEN tag_display_label END, ', ')                          AS risk_tag_labels,
    max(tagged_at)                                                        AS tags_updated_at
FROM {{ ref('stg_crm__party_tag') }}
WHERE customer_id IS NOT NULL
  AND tag_category IN ('risk', 'vip_tier')
GROUP BY customer_id
```

### 2. `mart_customer_action_queue.sql` — điểm sửa cụ thể

Trong CTE `customers` (đầu file): thêm JOIN `int_crm_party_tag_flags` để đưa `has_vip_tag`, `has_risk_tag`, `risk_tag_labels` vào scope trước khi tới `classified` CTE (cần các cột này trong CASE logic của `classified`).

Trong `classified` CTE, sửa toàn bộ 4 điều kiện `value_group IN (...)` thành `(value_group IN (...) OR has_vip_tag)`, và thêm nhánh `MANUAL_RISK_REVIEW` theo thứ tự ưu tiên đã mô tả ở Requirements §2.

### 3. Badge + label

Theo đúng convention phase-09 đã thiết lập — xem `badge_catalog.py:74-87` (`_CATALOG["action_type"]`) và phần `_ACTION_TYPE_SHORT_LABEL` để thêm entry cùng cấu trúc.

## Tests & Validation

1. `docker compose restart data_platform`; `dbt build --select int_crm_party_tag_flags mart_customer_action_queue`.
2. Sanity: tạo/xác nhận ≥1 party test có tag `vip_tier` và `value_group` KHÔNG phải VIP/GOLD/SILVER → verify xuất hiện trong action queue với action_type hợp lệ (không NULL).
3. Sanity: ≥1 party có tag `risk` → verify action_type = `MANUAL_RISK_REVIEW`, VÀ party đó vẫn xuất hiện ở action_type khác nếu đủ điều kiện khác (KHÔNG bị lọc mất).
4. `docker compose exec crm python -m pytest src/tests -k badge` — xác nhận badge mới không phá test hiện có.
5. Bootstrap serving view (`bootstrap_serving_views.py`, dừng Metabase trước) để CRM đọc được `mart_customer_action_queue` mới → `docker compose restart crm` (KHÔNG cần `--build` trừ khi badge_catalog.py/task_service.py là code CRM bind-mounted — xác nhận: CÓ bind-mounted theo `feedback_crm_restart_not_rebuild` → chỉ cần restart, không rebuild).
6. Worklist S01: verify badge "Cần xác minh" hiện đúng, tooltip đúng, không lộ mã `manual_risk_review` thô.

## Risks & Rollback

| Risk | Mitigation |
|------|-----------|
| Renumber priority_rank 1-7 làm lệch thứ tự hiển thị hiện tại NV đã quen | Thông báo NV trước khi deploy; rank chỉ ảnh hưởng THỨ TỰ trong queue, không ẩn/hiện gì |
| `has_vip_tag`/`has_risk_tag` NULL (LEFT JOIN không match) thay vì FALSE → `OR NULL` không hoạt động như mong đợi trong SQL 3-value logic | Dùng `COALESCE(has_vip_tag, false)` khi tham chiếu, hoặc đảm bảo `int_crm_party_tag_flags` luôn trả `false` thay `NULL` (bool_or trên tập rỗng → NULL trong DuckDB, cần `COALESCE` ở mart) |
| 1 party có tag risk VÀ vip_tier cùng lúc → thứ tự CASE quyết định action_type nào thắng | Theo thiết kế: VIP nhánh đứng trước risk nhánh trong CASE hiện có → VIP thắng nếu đồng thời đủ điều kiện reorder/churn; risk chỉ thắng khi KHÔNG khớp nhánh VIP nào — chấp nhận, ghi rõ trong code comment |
| Rollback | Revert 2 file mart + badge_catalog + task_service; xóa `int_crm_party_tag_flags.sql`; dbt build lại |

## Unresolved Questions

- Không có quyết định treo — mọi lựa chọn thiết kế đã chốt ở master plan hoặc quyết định ngay trong phase này (vd renumber priority_rank sạch). Nếu implementer thấy renumber gây xáo trộn quá lớn, có thể quay lại hỏi user trước khi deploy production.
