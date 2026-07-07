# Phase 01 — Schema: is_provisional + is_archived + Health Tag Seed

**Depends on:** `260619-0830-crm-tag-acl-sync` Phase 01 (adds `crm_party_tag.source` + `ext_ref`)

## Context

`crm_tag.category` là free-form TEXT — không có CHECK constraint, không cần ALTER. Cần thêm 2 flags + seed health tags.

Existing seed categories trong DB thực tế: `segment`, `profile`, `action` (khác với M14 spec — DB là source of truth).

## Files to modify

- `crm/migrations/00XX_tag_provisional_archived.up.sql` (mới, số sau migration cuối 260619)
- `crm/migrations/00XX_tag_provisional_archived.down.sql`
- `crm/models.py` hoặc tương đương — update TagCategory constants nếu hardcoded

## Requirements

### 1. ALTER crm_tag — thêm 2 flags

```sql
ALTER TABLE crm_tag ADD COLUMN is_provisional INTEGER NOT NULL DEFAULT 0;
-- 0=canonical, 1=provisional (chưa admin validate)
-- Level 1 provisional: category set + is_provisional=1
-- Level 2 provisional: category IS NULL + is_provisional=1

ALTER TABLE crm_tag ADD COLUMN is_archived INTEGER NOT NULL DEFAULT 0;
-- 0=active, 1=archived (ẩn khỏi pickers, giữ lịch sử party_tag)
```

> SQLite dùng INTEGER cho boolean (0/1). `ADD COLUMN ... DEFAULT 0` hợp lệ trong SQLite.

### 2. Seed 8 health domain tags (canonical)

```sql
INSERT OR IGNORE INTO crm_tag (tag_id, name, category, color, is_provisional, is_archived) VALUES
  ('tag-health-0001', 'tim-mach',      'health_domain', '#E53E3E', 0, 0),
  ('tag-health-0002', 'ho-hap',        'health_domain', '#3182CE', 0, 0),
  ('tag-health-0003', 'mien-dich',     'health_domain', '#38A169', 0, 0),
  ('tag-health-0004', 'xuong-khop',    'health_domain', '#DD6B20', 0, 0),
  ('tag-health-0005', 'tieu-hoa',      'health_domain', '#D69E2E', 0, 0),
  ('tag-health-0006', 'than-kinh-ngu', 'health_domain', '#805AD5', 0, 0),
  ('tag-health-0007', 'nang-luong',    'health_domain', '#319795', 0, 0),
  ('tag-health-0008', 'da',            'health_domain', '#D53F8C', 0, 0);
```

### 3. crm_customer_profile.custom — thêm 2 keys (no migration)

Document trong code/comments — không cần migration vì là JSON:

| Key | Type | Mô tả |
|-----|------|-------|
| `health_context_raw` | string ≤200 chars | Free text rep nhập trong call |
| `health_context_raw_reviewed` | bool | Ops đã xử lý pattern này trong chipify queue |

### 4. Update app code — category constants

Nếu app hardcode category list (e.g., Python enum, JS object), thêm:
```python
class TagCategory:
    SEGMENT       = 'segment'       # existing
    PROFILE       = 'profile'       # existing
    ACTION        = 'action'        # existing
    HEALTH_DOMAIN = 'health_domain' # new
    HEALTH_CONCERN= 'health_concern'# new
    # NULL / không set = Level 2 provisional (chưa biết domain)
```

## Full data structure sau Phase 01 + 260619 Phase 01

```
crm_tag
  tag_id          TEXT PK
  name            TEXT NOT NULL          -- slug (unique per category)
  category        TEXT                   -- nullable: NULL = Level 2 provisional
  color           TEXT
  is_provisional  INTEGER DEFAULT 0      -- 0=canonical, 1=awaiting admin review  ← NEW
  is_archived     INTEGER DEFAULT 0      -- 0=active, 1=retired                   ← NEW
  UNIQUE (category, name)

crm_party_tag
  party_id    TEXT NOT NULL → crm_party
  tag_id      TEXT NOT NULL → crm_tag
  tagged_by   TEXT → crm_app_user
  tagged_at   TEXT DEFAULT now
  source      TEXT DEFAULT 'crm_user'   -- 'crm_user'|'ops_normalized'|'sapo_v2_sync'  ← from 260619
  ext_ref     TEXT                      -- ext_key gốc khi source=*_sync              ← from 260619
  PRIMARY KEY (party_id, tag_id)

crm_ext_tag                              -- from 260619
  ext_tag_id    TEXT PK
  source_system TEXT                    -- 'sapo_v2' | 'haravan'
  ext_key       TEXT                    -- giá trị gốc ('TYPE_WHOLESALE')
  ext_label     TEXT
  UNIQUE (source_system, ext_key)

crm_ext_tag_map                          -- from 260619
  map_id      TEXT PK
  ext_tag_id  TEXT → crm_ext_tag
  crm_tag_id  TEXT → crm_tag
  direction   TEXT                      -- 'inbound'|'outbound'|'both'
  priority    INTEGER
  is_active   INTEGER DEFAULT 1
```

## Provisional tag matrix

| category | is_provisional | Ý nghĩa | Admin action |
|----------|---------------|---------|-------------|
| `health_domain` | 0 | Canonical — hiện trong chips S14 | — |
| `health_concern` | 0 | Canonical — hiện trong chips S14 | — |
| `health_concern` | 1 | **Level 1**: domain đã biết, tag chưa validate | Rename/merge trong tab health_concern |
| NULL | 1 | **Level 2**: domain chưa biết | Gán category → rồi rename/merge |
| any | 1 | Provisional từ bất kỳ category nào | Tương tự Level 1 |

## Validation

- `crm_tag` có cột `is_provisional` và `is_archived` sau migration
- 8 health domain tags seeded với `is_provisional=0, is_archived=0`
- INSERT tag mới với `is_provisional=1, category=NULL` không bị constraint reject
- `crm_customer_profile.custom` với key `health_context_raw` lưu/đọc được
