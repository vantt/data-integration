# Phase 01 — Schema: ACL Tables + source column

**Context:** [plan.md](plan.md) · Requires: Phase 00 done (data contract `customer_group_id`)

## Overview
- **Priority:** P0 — block phase 02/03
- **Status:** ✅ DONE (2026-07-07) — migration 0039 applied, see `reports/phase-01-implementation-report.md`
- Tạo 2 bảng ACL mới (`crm_ext_tag`, `crm_ext_tag_map`) và mở rộng `crm_party_tag` với `source` + `ext_ref` để track tag đến từ đâu.

## Key Insights
- `crm_party_external_id` (migration 0009) đã làm đúng pattern này cho identity — tag ACL follow cùng tư duy.
- `source` column quyết định conflict rule: `crm_user` > `*_sync`.
- `crm_ext_tag_map` là N:M: 1 ext_tag có thể map nhiều crm_tag (vd Sapo group WHOLESALE → tag "KH Sỉ" + tag "B2B"); 1 crm_tag có thể nhận từ nhiều ext_tag.
- **`ext_key` = khóa ổn định của hệ ngoài** — với Sapo là customer_group **id** (`'1812239'`), KHÔNG phải `code` (Sapo rename code trên cùng id — verified phase 00). `ext_label` lưu name/code để đọc.
- **UNIQUE (ext_tag_id, crm_tag_id)** trên map — bắt buộc để governance merge (plan 260706-0833) repoint mapping idempotent, không tạo duplicate rows.
- Migration đánh số **theo migration mới nhất lúc implement** — plan gốc ghi 0022 đã stale, repo hiện ở 0038 → dùng 0039.

## Architecture

```
crm_ext_tag (registry tag hệ ngoài)
  ext_tag_id   PK
  source_system            -- 'sapo_v2' | 'haravan' | 'shopify'
  ext_key                  -- khóa ổn định hệ ngoài (Sapo: group id '1812239')
  ext_label                -- nhãn hiển thị (name/code gốc, vd 'WHOLESALE (BANBUON)')
  UNIQUE (source_system, ext_key)

crm_ext_tag_map (ACL mapping)
  map_id       PK
  ext_tag_id   FK → crm_ext_tag
  crm_tag_id   FK → crm_tag
  direction                -- 'inbound' | 'outbound' | 'both'
  priority     INTEGER     -- khi 1 party có nhiều ext_tag → crm_tag cùng category
  is_active    BOOLEAN
  UNIQUE (ext_tag_id, crm_tag_id)   -- merge governance repoint idempotent

crm_party_tag (extend existing)
  + source     TEXT DEFAULT 'crm_user'   -- 'crm_user' | 'sapo_v2_sync' | 'haravan_sync'
  + ext_ref    TEXT                      -- ext_key gốc (group id) để tracing/audit
```

## Related Code Files
- **Tạo:** `crm/migrations/0039_tag_acl_ext_mapping.up.sql` (số 0039 = kế tiếp 0038 hiện tại; re-check lúc implement)
- **Đọc:** `crm/migrations/0003_customer_profile_custom_fields_tags.up.sql` (crm_tag/crm_party_tag hiện tại)
- **Đọc:** `crm/migrations/0009_party_external_id.up.sql` (pattern ACL tham khảo)

## Implementation Steps

1. Viết `0039_tag_acl_ext_mapping.up.sql`:
   - `CREATE TABLE crm_ext_tag` với UNIQUE (source_system, ext_key)
   - `CREATE TABLE crm_ext_tag_map` với UNIQUE (ext_tag_id, crm_tag_id) + index (ext_tag_id, is_active)
   - `ALTER TABLE crm_party_tag ADD COLUMN source TEXT NOT NULL DEFAULT 'crm_user'`
   - `ALTER TABLE crm_party_tag ADD COLUMN ext_ref TEXT`
   - Index `(source, party_id)` trên `crm_party_tag` cho reconcile query
2. Viết `.down.sql` tương ứng (DROP TABLE + ALTER TABLE DROP COLUMN nếu SQLite version hỗ trợ — hoặc recreate table)
3. Apply migration theo cơ chế hiện hành của app (xem cách các migration 003x được apply)
4. Verify schema bằng `PRAGMA table_info(crm_party_tag)` và `PRAGMA table_info(crm_ext_tag)`

## Todo
- [x] `0039_tag_acl_ext_mapping.up.sql`
- [x] `0039_tag_acl_ext_mapping.down.sql`
- [x] Apply + verify schema

## Success Criteria
- `crm_ext_tag` + `crm_ext_tag_map` tồn tại trong crm.db
- `crm_party_tag` có thêm `source` (default 'crm_user') và `ext_ref`
- Existing tags không bị ảnh hưởng (default source='crm_user' backfill tự động)

## Risk
- SQLite không hỗ trợ `DROP COLUMN` trước v3.35 → down migration cần recreate table nếu SQLite cũ; check version trước.
- `ALTER TABLE ADD COLUMN` không thể có DEFAULT non-constant → dùng `DEFAULT 'crm_user'` (literal string) là hợp lệ.
