# Phase 01 — Schema: ACL Tables + source column

**Context:** [plan.md](plan.md)

## Overview
- **Priority:** P0 — block mọi phase sau
- **Status:** ⬜ TODO
- Tạo 2 bảng ACL mới (`crm_ext_tag`, `crm_ext_tag_map`) và mở rộng `crm_party_tag` với `source` + `ext_ref` để track tag đến từ đâu.

## Key Insights
- `crm_party_external_id` (migration 0009) đã làm đúng pattern này cho identity — tag ACL follow cùng tư duy.
- `source` column quyết định conflict rule: `crm_user` > `*_sync`.
- `crm_ext_tag_map` là N:M: 1 ext_tag có thể map nhiều crm_tag (vd Sapo group WHOLESALE → tag "KH Sỉ" + tag "B2B"); 1 crm_tag có thể nhận từ nhiều ext_tag.

## Architecture

```
crm_ext_tag (registry tag hệ ngoài)
  ext_tag_id   PK
  source_system            -- 'sapo_v2' | 'haravan' | 'shopify'
  ext_key                  -- giá trị gốc (TYPE_WHOLESALE, VIP_CUSTOMER...)
  ext_label                -- nhãn hiển thị gốc
  UNIQUE (source_system, ext_key)

crm_ext_tag_map (ACL mapping)
  map_id       PK
  ext_tag_id   FK → crm_ext_tag
  crm_tag_id   FK → crm_tag
  direction                -- 'inbound' | 'outbound' | 'both'
  priority     INTEGER     -- khi 1 party có nhiều ext_tag → crm_tag cùng category
  is_active    BOOLEAN

crm_party_tag (extend existing)
  + source     TEXT DEFAULT 'crm_user'   -- 'crm_user' | 'sapo_v2_sync' | 'haravan_sync'
  + ext_ref    TEXT                      -- giá trị ext_key gốc để tracing
```

## Related Code Files
- **Tạo:** `crm/migrations/0022_tag_acl_ext_mapping.up.sql`
- **Đọc:** `crm/migrations/0003_customer_profile_custom_fields_tags.up.sql` (crm_tag/crm_party_tag hiện tại)
- **Đọc:** `crm/migrations/0009_party_external_id.up.sql` (pattern ACL tham khảo)

## Implementation Steps

1. Viết `0022_tag_acl_ext_mapping.up.sql`:
   - `CREATE TABLE crm_ext_tag` với UNIQUE (source_system, ext_key)
   - `CREATE TABLE crm_ext_tag_map` với index trên (ext_tag_id, is_active)
   - `ALTER TABLE crm_party_tag ADD COLUMN source TEXT NOT NULL DEFAULT 'crm_user'`
   - `ALTER TABLE crm_party_tag ADD COLUMN ext_ref TEXT`
   - Index `(source, party_id)` trên `crm_party_tag` cho sync query
2. Viết `.down.sql` tương ứng (DROP TABLE + ALTER TABLE DROP COLUMN nếu SQLite version hỗ trợ — hoặc recreate table)
3. Apply migration: `docker exec crm-app python -m crm.sync.apply_migrations` (hoặc cách app đang apply)
4. Verify schema bằng `PRAGMA table_info(crm_party_tag)` và `PRAGMA table_info(crm_ext_tag)`

## Todo
- [ ] `0022_tag_acl_ext_mapping.up.sql`
- [ ] `0022_tag_acl_ext_mapping.down.sql`
- [ ] Apply + verify schema

## Success Criteria
- `crm_ext_tag` + `crm_ext_tag_map` tồn tại trong crm.db
- `crm_party_tag` có thêm `source` (default 'crm_user') và `ext_ref`
- Existing tags không bị ảnh hưởng (default source='crm_user' backfill tự động)

## Risk
- SQLite không hỗ trợ `DROP COLUMN` trước v3.35 → down migration cần recreate table nếu SQLite cũ; check version trước.
- `ALTER TABLE ADD COLUMN` không thể có DEFAULT non-constant → dùng `DEFAULT 'crm_user'` (literal string) là hợp lệ.
