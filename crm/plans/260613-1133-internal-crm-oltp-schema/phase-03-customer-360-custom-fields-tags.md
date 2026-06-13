# Phase 03 — Customer 360 + Custom Fields + Tags

**Context:** [plan.md](plan.md) · Reports: customer-identity, orders-sales-products

## Overview
- **Priority:** P1
- **Status:** ✅ DONE — migration 0003 (profile/custom_field_def/tag/note), domain custom-field validator (type/required/options, date via time.Parse), ProfileService (merge custom JSON + validate merged map), tags/notes, `crm_party_360` view (crm-only — cache join hoãn Phase 04), 7 endpoint, 32 test PASS, code-review fixed (H1 PUT data-loss, H2 required-field). Auth hoãn.
- Lớp **làm giàu & chuẩn hoá** thông tin khách mà Sapo không có: profile mở rộng, custom fields tuỳ biến, tags, notes. Kết hợp với insight cache (Phase 04) thành view `party_360`.

## Key Insights
- Sapo ít custom field → đây là giá trị cốt lõi của CRM.
- Gaps từ scan: không lịch sử liên hệ, không nguồn acquisition thật, không SCD2 profile. CRM bù các field này.
- SQLite JSON1 (`TEXT`+`json_extract`) cho custom field (ít user, schema linh hoạt); kèm registry `custom_field_def` để app render UI + validate.

## Requirements
- **FR:** mỗi party có 1 profile enrichment; custom field định nghĩa động (text/number/date/select/multiselect); gắn nhiều tag có category; ghi chú tự do có tác giả; gán owner (NV phụ trách).
- **NFR:** truy vấn party_360 1 round-trip; custom field thêm mới không cần migration.

## Architecture
> DDL Postgres-style — map **SQLite** theo Quy ước [plan.md](plan.md): `crm_*` prefix, `uuid`→`TEXT`, `timestamptz`→`TEXT` UTC, `jsonb`→`TEXT`+JSON1, ở `crm.db`.

### Core DDL
```sql
CREATE TABLE crm.customer_profile (
  party_id        uuid PRIMARY KEY REFERENCES crm.party(party_id),
  owner_user_id   uuid REFERENCES crm.app_user(user_id),  -- NV phụ trách
  lifecycle_stage text,           -- lead|new|active|at_risk|churned (thủ công, bổ trợ wh_cache)
  acquisition_source text,        -- nguồn thật do NV xác nhận
  birthday        date,
  address         jsonb,          -- {province,district,ward,street} đã chuẩn hoá
  preferences     jsonb,          -- sở thích/ghi nhận hành vi thủ công
  custom          jsonb NOT NULL DEFAULT '{}',  -- giá trị custom field (key ↔ custom_field_def.field_key)
  consent_contact boolean DEFAULT true,          -- đồng ý liên hệ (compliance)
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE crm.custom_field_def (
  field_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type text NOT NULL DEFAULT 'party',  -- party|order (mở rộng sau)
  field_key  text NOT NULL,                    -- khoá trong jsonb
  label      text NOT NULL,
  data_type  text NOT NULL,                    -- text|number|date|bool|select|multiselect
  options    jsonb,                            -- cho select/multiselect
  is_required boolean DEFAULT false,
  is_active  boolean DEFAULT true,
  sort_order int DEFAULT 0,
  UNIQUE (entity_type, field_key)
);

CREATE TABLE crm.tag (
  tag_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL, category text, color text,
  UNIQUE (category, name)
);
CREATE TABLE crm.party_tag (
  party_id uuid REFERENCES crm.party(party_id),
  tag_id   uuid REFERENCES crm.tag(tag_id),
  tagged_by uuid REFERENCES crm.app_user(user_id),
  tagged_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (party_id, tag_id)
);
CREATE TABLE crm.note (
  note_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  party_id uuid NOT NULL REFERENCES crm.party(party_id),
  body text NOT NULL,
  author_user_id uuid REFERENCES crm.app_user(user_id),
  created_at timestamptz NOT NULL DEFAULT now()
);
-- SQLite: index biểu thức trên field custom hay lọc (thay GIN); thêm theo nhu cầu
CREATE INDEX idx_profile_owner ON crm_customer_profile (owner_user_id);
-- vd cần lọc theo 1 custom field: CREATE INDEX ... ON crm_customer_profile(json_extract(custom,'$.skin_type'));
```
### View party_360 (đọc cho app)
`crm.party_360` = `party` ⋈ `customer_profile` ⋈ `wh_cache.customer_insight` (Phase 04) ⋈ tags-agg ⋈ latest action. App dùng view này cho màn hồ sơ khách.

## Related Code Files
- **Tạo:** `crm/migrations/0004_customer_profile_custom_fields_tags.up.sql`, `0005_view_party_360.up.sql`, Go CRUD profile/tag/note + custom-field registry handler.
- **Đọc:** `dim_customers.sql` (field nào warehouse đã có → tránh trùng lặp ở profile).

## Implementation Steps
1. Migration 0004: profile + custom_field_def + tag/party_tag + note.
2. Validate `custom` JSONB theo `custom_field_def` ở tầng app (data_type, required, options).
3. Seed vài custom field + tag category khởi điểm.
4. View `party_360` (0005) — join wh_cache để app 1 query.
5. CRUD + audit (touch_updated_at).

## Todo
- [ ] Migration 0004 + 0005
- [ ] Validate custom JSONB theo def
- [ ] CRUD profile/tag/note
- [ ] Seed field/tag mẫu
- [ ] party_360 view

## Success Criteria
- Thêm custom field mới (vd "Da nhạy cảm") không cần migration; gắn/bỏ tag; party_360 trả profile + insight + tags trong 1 query.

## Risk Assessment
- **JSONB không validate** → enforce ở app theo registry; cân nhắc CHECK/constraint cho field quan trọng.
- Trùng field giữa profile thủ công và warehouse → quy ước: warehouse = sự thật tính toán, profile = ghi nhận con người; không ghi đè nhau.

## Security
- PII (birthday, address, consent) — role-gated; `consent_contact=false` phải chặn ở Phase 06 (campaign).

## Next Steps
→ Phase 04 cung cấp insight cho party_360. → Phase 07 chọn field nào trong `custom`/`tag` để ghi ngược Sapo.
