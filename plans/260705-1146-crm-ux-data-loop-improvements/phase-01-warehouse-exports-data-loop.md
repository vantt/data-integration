# Phase 01 — Warehouse Exports: Đóng vòng lặp dữ liệu CRM (D1)

**Status:** DONE  **Priority:** P0  **Depends on:** —

## Context Links

- Design + quyết định: `crm/docs/ui-spec/notes/ux-action-queue-task-cockpit-data-loop-design.md` §5, §6-D1, §8
- Master plan: `plans/260705-1146-crm-ux-data-loop-improvements/plan.md`
- Export assets hiện tại: `orchestration/assets/crm_writeback_assets.py`
- Source registry: `transformation/models/sources.yml` (block `crm_export`, dòng 176–199)
- Staging pattern: `transformation/models/staging/stg_crm__activity_log.sql` (incremental)
- Staging pattern: `transformation/models/staging/stg_crm__last_contact.sql` (snapshot)
- Schema tests: `transformation/models/staging/schema.yml`
- SQLite schemas: `crm/migrations/0003_*.up.sql`, `0010_note_type_pin_visibility.up.sql`,
  `0011_party_insight.up.sql`, `0014_custom_field_section_tag_category.up.sql`, `0017_tag_display_label.up.sql`

---

## Requirements

1. Export `crm_note` incremental_append trên `created_at`; loại `visibility='private'` khỏi query (xem §Decision bên dưới); cột `deleted_at` vẫn xuất để staging filter.
2. Export `crm_tag` snapshot: `tag_id, name, category, color, display_label`.
3. Export `crm_party_tag` snapshot: `party_id, tag_id, tagged_by, tagged_at`. (2 file riêng, staging JOIN — xem §Justification.)
4. Export `crm_party_insight` incremental_append trên `created_at`; `WHERE deleted_at IS NULL` trong query.
5. Export `crm_customer_profile_custom` snapshot: `party_id, custom (raw JSON), updated_at`.
6. 5 source entries bổ sung vào `sources.yml` block `crm_export`.
7. `stg_crm__note` view: cast timestamps TIMESTAMPTZ, `WHERE deleted_at IS NULL`.
8. `stg_crm__party_tag` view: JOIN crm_tag + crm_party_tag, expose tag taxonomy fields.
9. `stg_crm__party_insight` view: cast timestamps, `WHERE deleted_at IS NULL`.
10. `stg_crm__customer_profile_custom` view: `custom_json` (raw), `updated_at`, plus `json_extract_string` theo 4 field_key seed (`skin_type`, `loyal_tier`, `preferred_contact`, `note_internal`).
11. schema.yml: `unique` + `not_null` cho PK của 4 staging models.
12. Row count staging ≈ SQLite sau khi lọc visibility/deleted (validated bằng count query).

### §Decision — `crm_note` visibility='private'

**Recommendation: loại trừ hoàn toàn** (`AND visibility != 'private'` trong export query). Private notes do NV viết riêng; ship lên warehouse shared là data exposure không chủ đích.

**Alternative:** export nhưng mask `body → NULL` (giữ metadata note_type/author/timestamps). Phức tạp hơn, ít value hơn.

**IMPLEMENTER: confirm với user trước khi chạy production lần đầu.** Default trong plan này: exclusion filter.

### §Justification — crm_tag + crm_party_tag tách 2 file

Nhất quán với pattern 1 table = 1 export. crm_tag (taxonomy, ít thay đổi) và crm_party_tag (assignment, thay đổi thường xuyên) có cadence khác nhau. Staging model `stg_crm__party_tag` JOIN cả hai → enriched view. Nếu merge 1 file, snapshot crm_tag chạy thừa mỗi lần có tag assignment mới.

---

## Files to Modify / Create

### Modify

| File | Thay đổi |
|------|---------|
| `orchestration/assets/crm_writeback_assets.py` | Thêm 5 tên bảng vào `_CRM_TABLE_NAMES`; thêm 5 `CrmWritebackTable`; thêm 5 module-level asset objects |
| `transformation/models/sources.yml` | Thêm 5 entries vào block `crm_export` |
| `transformation/models/staging/schema.yml` | Thêm 4 model blocks với PK tests |

### Create

- `transformation/models/staging/stg_crm__note.sql`
- `transformation/models/staging/stg_crm__party_tag.sql`
- `transformation/models/staging/stg_crm__party_insight.sql`
- `transformation/models/staging/stg_crm__customer_profile_custom.sql`

---

## Implementation Steps

### 1. `crm_writeback_assets.py`

**`_CRM_TABLE_NAMES`** — thêm: `"crm_note", "crm_tag", "crm_party_tag", "crm_party_insight", "crm_customer_profile"`

**`CRM_WRITEBACK_TABLES`** — append 5 entries:

```python
CrmWritebackTable(
    name="crm_note", mode="incremental_append", watermark_column="created_at",
    export_query="""
        SELECT note_id, party_id, note_type, body, author_user_id,
               pinned, pinned_until, visibility, task_id, campaign_id,
               source_activity_id, updated_at, updated_by_user_id, deleted_at, created_at
        FROM crm_note
        WHERE created_at > '{cursor}' AND visibility != 'private'
    """),
CrmWritebackTable(
    name="crm_tag", mode="snapshot",
    export_query="SELECT tag_id, name, category, color, display_label FROM crm_tag"),
CrmWritebackTable(
    name="crm_party_tag", mode="snapshot",
    export_query="SELECT party_id, tag_id, tagged_by, tagged_at FROM crm_party_tag"),
CrmWritebackTable(
    name="crm_party_insight", mode="incremental_append", watermark_column="created_at",
    export_query="""
        SELECT insight_id, party_id, insight_type, body, confidence,
               source_note_id, created_by, updated_at, deleted_at, created_at
        FROM crm_party_insight
        WHERE created_at > '{cursor}' AND deleted_at IS NULL
    """),
CrmWritebackTable(
    name="crm_customer_profile_custom", mode="snapshot",
    export_query="SELECT party_id, custom, updated_at FROM crm_customer_profile"),
```

> Note: export name là `crm_customer_profile_custom` nhưng table SQLite là `crm_customer_profile` — chỉ `crm_customer_profile` cần vào `_CRM_TABLE_NAMES`.

**Module-level assets** (cuối file, theo pattern hiện tại):

```python
crm_note_export = _make_incremental_asset(next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_note"))
crm_tag_export = _make_snapshot_asset(next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_tag"))
crm_party_tag_export = _make_snapshot_asset(next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_party_tag"))
crm_party_insight_export = _make_incremental_asset(next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_party_insight"))
crm_customer_profile_custom_export = _make_snapshot_asset(next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_customer_profile_custom"))
```

### 2. `sources.yml` — append vào `crm_export` source

```yaml
      - name: crm_note
        description: "CRM notes incremental (private excluded). Grain: 1 note × batch."
        meta:
          external_location: "read_parquet('{{ env_var('DBT_DATA_LAKE_PATH') }}/crm_export/crm_note/**/*.parquet', hive_partitioning=1, union_by_name=true)"
      - name: crm_tag
        description: "Tag taxonomy snapshot."
        meta:
          external_location: "read_parquet('{{ env_var('DBT_DATA_LAKE_PATH') }}/crm_export/crm_tag.parquet')"
      - name: crm_party_tag
        description: "Party-tag assignments snapshot."
        meta:
          external_location: "read_parquet('{{ env_var('DBT_DATA_LAKE_PATH') }}/crm_export/crm_party_tag.parquet')"
      - name: crm_party_insight
        description: "Rep-curated insights incremental (active rows only)."
        meta:
          external_location: "read_parquet('{{ env_var('DBT_DATA_LAKE_PATH') }}/crm_export/crm_party_insight/**/*.parquet', hive_partitioning=1, union_by_name=true)"
      - name: crm_customer_profile_custom
        description: "Customer profile custom JSON blob snapshot. Pivot in staging."
        meta:
          external_location: "read_parquet('{{ env_var('DBT_DATA_LAKE_PATH') }}/crm_export/crm_customer_profile_custom.parquet')"
```

### 3. Staging models

**`stg_crm__note.sql`**
```sql
{{ config(materialized='view', tags=['staging', 'crm']) }}
SELECT note_id, party_id, note_type, body, author_user_id,
       pinned::INTEGER AS pinned, pinned_until::TIMESTAMPTZ AS pinned_until,
       visibility, task_id, campaign_id, source_activity_id,
       updated_at::TIMESTAMPTZ AS updated_at, updated_by_user_id,
       created_at::TIMESTAMPTZ AS created_at
FROM {{ source('crm_export', 'crm_note') }}
WHERE deleted_at IS NULL
```

**`stg_crm__party_tag.sql`**
```sql
{{ config(materialized='view', tags=['staging', 'crm']) }}
SELECT pt.party_id, pt.tag_id,
       t.name AS tag_name, t.category AS tag_category,
       t.display_label AS tag_display_label, t.color AS tag_color,
       pt.tagged_by, pt.tagged_at::TIMESTAMPTZ AS tagged_at
FROM {{ source('crm_export', 'crm_party_tag') }} pt
LEFT JOIN {{ source('crm_export', 'crm_tag') }} t USING (tag_id)
```

**`stg_crm__party_insight.sql`**
```sql
{{ config(materialized='view', tags=['staging', 'crm']) }}
SELECT insight_id, party_id, insight_type, body, confidence,
       source_note_id, created_by,
       updated_at::TIMESTAMPTZ AS updated_at,
       created_at::TIMESTAMPTZ AS created_at
FROM {{ source('crm_export', 'crm_party_insight') }}
WHERE deleted_at IS NULL
```

**`stg_crm__customer_profile_custom.sql`**
```sql
{{ config(materialized='view', tags=['staging', 'crm']) }}
-- Raw JSON + static extract từ 4 field_key seed (crm_custom_field_def).
-- Khi thêm field_key mới vào crm_custom_field_def, thêm json_extract_string tương ứng ở đây.
SELECT
    party_id,
    custom                                              AS custom_json,
    updated_at::TIMESTAMPTZ                             AS updated_at,
    json_extract_string(custom, '$.skin_type')          AS skin_type,
    json_extract_string(custom, '$.loyal_tier')         AS loyal_tier,
    json_extract_string(custom, '$.preferred_contact')  AS preferred_contact,
    json_extract_string(custom, '$.note_internal')      AS note_internal
FROM {{ source('crm_export', 'crm_customer_profile_custom') }}
```

### 4. `schema.yml` additions

```yaml
  - name: stg_crm__note
    description: "CRM notes (team-visible, non-deleted)."
    columns:
      - name: note_id
        tests: [unique, not_null]
      - name: party_id
        tests: [not_null]
  - name: stg_crm__party_tag
    description: "Party-tag assignments enriched with tag taxonomy."
    columns:
      - name: party_id
        tests: [not_null]
      - name: tag_id
        tests: [not_null]
  - name: stg_crm__party_insight
    description: "Rep-curated insights (active rows)."
    columns:
      - name: insight_id
        tests: [unique, not_null]
      - name: party_id
        tests: [not_null]
  - name: stg_crm__customer_profile_custom
    description: "Custom profile fields (1 row per party)."
    columns:
      - name: party_id
        tests: [unique, not_null]
```

---

## Consumption Plan (follow-up — KHÔNG trong phase này, YAGNI)

- **Segmentation:** `stg_crm__party_tag` filter `tag_category IN ('risk','vip_tier')` → customer tier/risk segment mart.
- **Recommender:** `skin_type` + `preferred_contact` từ `stg_crm__customer_profile_custom`; `insight_type IN ('preference','buying_pattern')` từ `stg_crm__party_insight` → cải thiện affinity score và approach script.
- Mart models cụ thể sẽ được plan trong phase/task riêng khi staging data quality đã xác minh.

---

## Tests & Validation

1. Chạy 5 Dagster assets thủ công (`crm_note_export`, `crm_tag_export`, `crm_party_tag_export`, `crm_party_insight_export`, `crm_customer_profile_custom_export`). Kiểm tra log row count > 0 (trừ note/insight nếu CRM mới).
2. Xác minh cột parquet khớp export query:
   ```bash
   # DuckDB CLI hoặc trong data_platform container
   SELECT * FROM read_parquet('/app/var/data_lake/crm_export/crm_tag.parquet') LIMIT 3;
   SELECT * FROM read_parquet('/app/var/data_lake/crm_export/crm_note/**/*.parquet', hive_partitioning=1) LIMIT 3;
   ```
3. `dbt build --select stg_crm__note stg_crm__party_tag stg_crm__party_insight stg_crm__customer_profile_custom` — all green.
4. Row-count sanity vs SQLite (attach crm.db qua DuckDB):
   ```sql
   SELECT COUNT(*) FROM crm_note WHERE visibility != 'private' AND deleted_at IS NULL;      -- ≈ stg_crm__note
   SELECT COUNT(*) FROM crm_party_insight WHERE deleted_at IS NULL;                         -- ≈ stg_crm__party_insight
   SELECT COUNT(*) FROM crm_customer_profile;                                               -- = stg_crm__customer_profile_custom
   SELECT COUNT(*) FROM crm_tag;                                                            -- = stg_crm__party_tag (unique tag_id)
   SELECT COUNT(*) FROM crm_party_tag;                                                      -- = stg_crm__party_tag (total rows)
   ```
5. Kiểm tra không có private note trong parquet: query `WHERE visibility = 'private'` → 0 rows.

---

## Ops Notes

- **dbt manifest stale:** 4 model mới → **restart `data_platform` container** trước khi `dbt build`, nếu không sẽ KeyError.
  ```bash
  docker compose restart data_platform
  ```
- **Mart mới cho CRM sau này:** nếu một mart downstream cần CRM đọc, phải thực hiện 2 bước thủ công: (1) dừng Metabase, chạy `bootstrap_serving_views.py`; (2) `docker compose up -d --build crm`. Không áp dụng trong phase này.
- **Serving DuckDB luôn read_only:** mọi query ad-hoc trên `olap.duckdb` / `sapo_export_latest` phải dùng `duckdb.connect(path, read_only=True)`.
- **File-drop same-second collision:** `_incremental_export` đặt tên `batch_{HH}{MM}{SS}.parquet`. Hai incremental export (`crm_note`, `crm_party_insight`) ghi vào subdirectory khác nhau → không collision dù chạy cùng giây trong 1 Dagster job. Snapshot exports dùng fixed filename (overwrite) → không liên quan. **An toàn.**
- **Phase này không đụng `crm/`:** không cần `docker compose restart crm`.

---

## Risks & Rollback

| Risk | Mitigation |
|------|-----------|
| Private note body lọt vào warehouse | `AND visibility != 'private'` trong query; validate step 5 |
| Watermark reset crm_note | Xóa `{DATA_LAKE}/crm_export/crm_note_cursor.json` → re-export từ epoch |
| Watermark reset crm_party_insight | Xóa `{DATA_LAKE}/crm_export/crm_party_insight_cursor.json` |
| stg_crm__party_tag fail vì crm_tag chưa export | Chạy `crm_tag_export` trước khi `dbt build` staging |
| crm_customer_profile không có row cho mọi party | `json_extract` trả NULL cho party thiếu profile — safe, filter downstream nếu cần |
| Manifest stale sau thêm model | Restart `data_platform` (xem Ops Notes) |

---

## Unresolved Questions

1. **`visibility='private'` final call:** Recommendation là loại trừ hoàn toàn. Nếu business cần note metadata (type, author, timestamps) không có body, chuyển sang mask `body = NULL`. **Confirm với user trước production run đầu tiên.**
2. **`crm_custom_field_def` export:** Hiện dùng static extraction 4 field_key seed. Nếu custom field mới được thêm thường xuyên, cân nhắc 5th export `crm_custom_field_def` + dynamic pivot ở mart layer (YAGNI cho đến khi có nhu cầu thực tế).
3. **Soft-deleted insights trong production:** Insights bị xóa trước phase này không xuất hiện trong parquet (export filter `deleted_at IS NULL`). Nếu audit trail cần thiết, phải plan export riêng.
