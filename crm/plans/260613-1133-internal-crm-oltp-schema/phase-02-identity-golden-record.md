# Phase 02 — Identity Resolution & Golden Record (Dedup)

**Context:** [plan.md](plan.md) · Report: `../reports/schema-scan-260613-1133-customer-identity-domain-report.md`

## Overview
- **Priority:** P0 (lõi v1; chặn 03/05/06 vì mọi thứ gắn `party_id`)
- **Status:** ⬜
- Xây **golden record**: gộp nhiều danh tính (Sapo customer_id, SĐT, email, FB PSID, Zalo UID) về 1 `party` duy nhất. Warehouse KHÔNG có lớp này — CRM tự sở hữu.

## Key Insights
- Warehouse chỉ dedup trong cùng `sapo_customer_id` (DEDUPLICATION.md). **Không** gộp người trùng qua phone/email → cùng 1 người có thể có nhiều Sapo ID.
- Canonical: lưu cả `customer_id` (natural, gọi Sapo API) + `customer_key` (MD5 surrogate, join `wh_cache`).
- SĐT là field liên hệ chính; cần chuẩn hoá số VN (0xxx ↔ +84) trước khi match.
- Merge phải **reversible** (audit) — sai sót gộp khách là rủi ro cao.

## Requirements
- **FR:** 1 party ↔ N identity; tạo party tự động khi reverse-ETL nạp khách Sapo (Phase 04); hàng đợi `dedup_candidate` cho match nghi ngờ; merge thủ công có log; chuẩn hoá SĐT/email.
- **NFR:** Match phone/trgm name < vài trăm ms ở quy mô khách hiện tại; merge atomic (transaction).

## Architecture
> DDL viết Postgres-style — map sang **SQLite** theo Quy ước ở [plan.md](plan.md): `crm_*` prefix, `uuid`→`TEXT` (app sinh), `timestamptz`→`TEXT` UTC ISO-8601, ở file `crm.db`.

### Core DDL
```sql
CREATE TABLE crm.party (
  party_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  party_type    text NOT NULL DEFAULT 'person',   -- person|org
  display_name  text,
  primary_phone text,            -- chuẩn hoá E.164-ish (+84...)
  primary_email text,
  status        text NOT NULL DEFAULT 'active',
  is_merged     boolean NOT NULL DEFAULT false,    -- true nếu đã bị gộp vào party khác
  merged_into   uuid REFERENCES crm.party(party_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- bản đồ danh tính → party (CƠ CHẾ DEDUP)
CREATE TABLE crm.party_identity (
  identity_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  party_id      uuid NOT NULL REFERENCES crm.party(party_id),
  source_system text NOT NULL,    -- sapo|messenger|zalo|manual
  identity_type text NOT NULL,    -- sapo_customer|phone|email|psid|zalo_uid|customer_code
  identity_value text NOT NULL,   -- giá trị đã chuẩn hoá
  confidence    numeric(4,3) NOT NULL DEFAULT 1.0,
  is_primary    boolean NOT NULL DEFAULT false,
  verified_at   timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (identity_type, identity_value)            -- 1 SĐT/email/psid chỉ thuộc 1 party
);

-- hàng đợi match nghi ngờ (review thủ công)
CREATE TABLE crm.dedup_candidate (
  candidate_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  party_a   uuid NOT NULL REFERENCES crm.party(party_id),
  party_b   uuid NOT NULL REFERENCES crm.party(party_id),
  match_rule text NOT NULL,        -- exact_phone|trgm_name_phone|email
  match_score numeric(4,3) NOT NULL,
  status text NOT NULL DEFAULT 'pending',  -- pending|merged|rejected
  reviewed_by uuid REFERENCES crm.app_user(user_id),
  reviewed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- log gộp (reversible)
CREATE TABLE crm.party_merge_log (
  merge_id  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  surviving_party_id uuid NOT NULL REFERENCES crm.party(party_id),
  merged_party_id    uuid NOT NULL,
  reason text, merged_by uuid REFERENCES crm.app_user(user_id),
  snapshot jsonb,                  -- trạng thái trước gộp để khôi phục
  merged_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_party_phone ON crm_party (primary_phone);
CREATE INDEX idx_identity_value ON crm_party_identity (identity_type, identity_value);
-- fuzzy tên (thay pg_trgm) = FTS5 ngoại bảng:
CREATE VIRTUAL TABLE crm_party_fts USING fts5(
  party_id UNINDEXED, name_norm, tokenize='unicode61 remove_diacritics 2'
);
-- giữ đồng bộ qua trigger AFTER INSERT/UPDATE/DELETE trên crm_party (name đã chuẩn hoá bỏ dấu)
```
### Match flow (SQLite — không pg_trgm)
1. Nạp identity (Sapo/phone/email) → `UNIQUE(identity_type,identity_value)` chặn trùng cứng.
2. Job match: **exact SĐT chuẩn hoá** (chiếm ~90% dedup retail) + email exact → tự link; **fuzzy tên qua FTS5 MATCH** (cùng prefix SĐT) → đẩy vào `dedup_candidate`. Khoảng-cách tên (Levenshtein) tính **app-side trên candidate set nhỏ**, không quét toàn bảng.
3. Nhân viên review → merge: chuyển identity của B sang A, set B `is_merged`, ghi `party_merge_log` (snapshot để undo).

## Related Code Files
- **Tạo:** `crm/migrations/0003_party_identity_golden_record.up.sql`, `crm/app/internal/dedup/*.go` (chuẩn hoá phone/email, match), Go endpoint review/merge.
- **Đọc:** `transformation/docs/DEDUPLICATION.md`, `dim_customers_base.sql` (cách sinh customer_key).

## Implementation Steps
1. Migration 0003: 4 bảng + index trgm/phone.
2. Hàm chuẩn hoá SĐT VN + email (Go + tùy chọn SQL function).
3. Upsert-party-from-sapo (gọi bởi Phase 04): tìm party qua identity sapo_customer; nếu chưa có → tạo + gán identity.
4. Match job (exact + fuzzy) → `dedup_candidate`.
5. Merge transaction + log + khả năng undo.
6. API/UI review hàng đợi dedup.

## Todo
- [ ] Migration 0003 up/down
- [ ] Chuẩn hoá phone/email
- [ ] Upsert party từ Sapo identity
- [ ] Match exact + trgm → candidate
- [ ] Merge + log (reversible)
- [ ] UI review dedup

## Success Criteria
- 2 Sapo ID cùng SĐT → phát hiện candidate; sau merge chỉ còn 1 party giữ đủ identity; `UNIQUE` chặn 1 phone thuộc 2 party; undo khôi phục đúng.

## Risk Assessment
- **Gộp nhầm** (cao) → mặc định fuzzy KHÔNG auto-merge, chỉ exact phone+email auto; còn lại review tay; mọi merge có snapshot undo.
- SĐT bẩn/format lẫn lộn → chuẩn hoá tập trung, test bộ mẫu thật.

## Security
- Merge/PII chỉ role `care`/`manager`+. Log đầy đủ ai gộp gì.

## Next Steps
→ Phase 03 (profile/tags gắn party). → Phase 04 tạo party khi nạp khách.
