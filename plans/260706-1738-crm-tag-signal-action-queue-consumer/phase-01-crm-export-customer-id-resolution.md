# Phase 01 — CRM Export customer_id Resolution (prerequisite)

**Status:** TODO  **Priority:** P0  **Depends on:** — (chặn cứng phase 02)

## Context Links

- Master plan: `plans/260706-1738-crm-tag-signal-action-queue-consumer/plan.md`
- Pattern tham chiếu (đã có, đúng): `crm_last_contact`, `crm_activity_log` export queries — `orchestration/assets/crm_writeback_assets.py:37-70`
- Export cần sửa: cùng file, block `crm_note` (L120-127), `crm_party_tag` (L133-134), `crm_party_insight` (L135-141), `crm_customer_profile_custom` (L142-144)
- Staging cần sửa: `transformation/models/staging/stg_crm__party_tag.sql`, `stg_crm__note.sql`, `stg_crm__party_insight.sql`, `stg_crm__customer_profile_custom.sql`
- Schema tests: `transformation/models/staging/schema.yml`

## Vấn đề

`crm_party_identity` (bảng SQLite nội bộ CRM, map `party_id → identity_value` theo `identity_type`) không được export thành dbt source riêng — chỉ dùng làm JOIN helper NGAY LÚC EXPORT (Python/DuckDB, trong `crm_writeback_assets.py`) cho các export cần `customer_id`. 4 export phase-01 (`crm_party_tag`, `crm_note`, `crm_party_insight`, `crm_customer_profile_custom`) thiếu bước này — chỉ có `party_id`, không thể JOIN vào bất kỳ mart Sapo nào (`mart_customer_action_queue`, `dim_customers`, ...) ở tầng dbt.

## Requirements

1. Sửa 4 export query trong `CRM_WRITEBACK_TABLES` — thêm `LEFT JOIN crm_party_identity pi ON pi.party_id = X.party_id AND pi.identity_type = 'sapo_customer'` + `pi.identity_value AS customer_id` vào SELECT, đúng pattern `crm_last_contact` (L37-45).
2. Sửa 4 staging model — thêm `customer_id::INTEGER AS customer_id` vào SELECT, pass-through (không filter NULL — party chưa link Sapo vẫn giữ trong staging, filter NULL ở mart layer nếu cần).
3. `schema.yml`: KHÔNG thêm `not_null` cho `customer_id` (nullable hợp lệ — party có thể chưa link Sapo, vd khách mới tạo qua Lark chưa từng mua hàng).
4. `crm_note`/`crm_party_insight` là `incremental_append` — dữ liệu batch cũ (trước fix) không có `customer_id`. Xóa cursor file tương ứng (`{DATA_LAKE}/crm_export/crm_note_cursor.json`, `crm_party_insight_cursor.json`) để re-export từ `_DEFAULT_CURSOR` (epoch) — volume nhỏ (feature mới ~1 ngày), an toàn re-export toàn bộ.
5. `crm_party_tag`/`crm_customer_profile_custom` là `snapshot` — re-run asset tự ghi đè file, không cần thao tác gì thêm.

## Implementation Steps

### 1. `crm_writeback_assets.py` — sửa 4 export query

```python
CrmWritebackTable(
    name="crm_note", mode="incremental_append", watermark_column="created_at",
    export_query="""
        SELECT n.note_id, n.party_id, pi.identity_value AS customer_id,
               n.note_type, n.body, n.author_user_id,
               n.pinned, n.pinned_until, n.visibility, n.task_id, n.campaign_id,
               n.source_activity_id, n.updated_at, n.updated_by_user_id, n.deleted_at, n.created_at
        FROM crm_note n
        LEFT JOIN crm_party_identity pi
               ON pi.party_id = n.party_id AND pi.identity_type = 'sapo_customer'
        WHERE n.created_at > '{cursor}' AND n.visibility != 'private'
    """),
CrmWritebackTable(
    name="crm_party_tag", mode="snapshot",
    export_query="""
        SELECT pt.party_id, pi.identity_value AS customer_id, pt.tag_id, pt.tagged_by, pt.tagged_at
        FROM crm_party_tag pt
        LEFT JOIN crm_party_identity pi
               ON pi.party_id = pt.party_id AND pi.identity_type = 'sapo_customer'
    """),
CrmWritebackTable(
    name="crm_party_insight", mode="incremental_append", watermark_column="created_at",
    export_query="""
        SELECT i.insight_id, i.party_id, pi.identity_value AS customer_id,
               i.insight_type, i.body, i.confidence,
               i.source_note_id, i.created_by, i.updated_at, i.deleted_at, i.created_at
        FROM crm_party_insight i
        LEFT JOIN crm_party_identity pi
               ON pi.party_id = i.party_id AND pi.identity_type = 'sapo_customer'
        WHERE i.created_at > '{cursor}' AND i.deleted_at IS NULL
    """),
CrmWritebackTable(
    name="crm_customer_profile_custom", mode="snapshot",
    export_query="""
        SELECT cp.party_id, pi.identity_value AS customer_id, cp.custom, cp.updated_at
        FROM crm_customer_profile cp
        LEFT JOIN crm_party_identity pi
               ON pi.party_id = cp.party_id AND pi.identity_type = 'sapo_customer'
    """),
```

Table alias cần thiết vì `crm_note`/`crm_customer_profile` giờ JOIN — kiểm tra `_qualify_for_attach()` (string-replace theo tên bảng) vẫn hoạt động đúng với alias (không đổi tên bảng gốc, chỉ thêm alias — an toàn).

### 2. Staging models — thêm `customer_id`

Mỗi file thêm 1 dòng `customer_id::INTEGER AS customer_id,` ngay sau `party_id`. Ví dụ `stg_crm__party_tag.sql`:

```sql
SELECT
    pt.party_id,
    pt.customer_id::INTEGER               AS customer_id,
    pt.tag_id,
    t.name                                AS tag_name,
    t.category                            AS tag_category,
    t.display_label                       AS tag_display_label,
    t.color                               AS tag_color,
    pt.tagged_by,
    pt.tagged_at::TIMESTAMPTZ             AS tagged_at
FROM {{ source('crm_export', 'crm_party_tag') }} pt
LEFT JOIN {{ source('crm_export', 'crm_tag') }} t USING (tag_id)
```

Áp dụng tương tự cho 3 file còn lại.

## Tests & Validation

1. `docker compose restart data_platform` (manifest pre-parsed, cột mới cần restart).
2. Chạy lại 4 export asset thủ công qua Dagster (hoặc đợi schedule). Với `crm_note`/`crm_party_insight`: xóa cursor trước khi chạy.
3. `dbt build --select stg_crm__party_tag stg_crm__note stg_crm__party_insight stg_crm__customer_profile_custom` — xanh.
4. Sanity query trong `data_platform` container:
   ```sql
   SELECT COUNT(*), COUNT(customer_id) FROM stg_crm__party_tag;
   -- customer_id NULL count hợp lý (= số party chưa link Sapo), không phải 100% NULL (bug resolution)
   ```
5. Xác nhận KHÔNG có row nào có `customer_id` sai kiểu (cast lỗi) — DuckDB sẽ raise nếu `identity_value` không phải numeric string.

## Ops Notes

- Restart `data_platform` TRƯỚC khi chạy export asset mới (không phải sau) — asset code cũng cần Dagster reload nếu chạy trong cùng container? Kiểm tra: `crm_writeback_assets.py` là orchestration code (Dagster), không phải dbt — Dagster có tự reload code hay cần restart riêng? Xác nhận khi triển khai (khác biệt với dbt manifest issue).
- Serving DuckDB luôn `read_only=True` khi query ad-hoc.

## Risks & Rollback

| Risk | Mitigation |
|------|-----------|
| `crm_party_identity` không có index tốt trên `(party_id, identity_type)` → export chậm hơn | Volume nhỏ (vài nghìn party), chấp nhận; thêm index sau nếu đo thấy chậm |
| Xóa cursor `crm_note`/`crm_party_insight` re-export nhầm phải dữ liệu production lớn | Đã xác nhận volume nhỏ (~1 ngày dữ liệu); kiểm tra row count trước khi xóa cursor |
| Rollback | Revert export query + staging model; xóa cursor lại nếu cần quay về trạng thái cũ (mất `customer_id`, không mất data khác) |

## Unresolved Questions

- Không có — toàn bộ quyết định đã chốt ở master plan.
