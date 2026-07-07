# Phase 03 — Tag Governance Admin (S13 extension)

**Depends on:** Phase 01 (is_provisional + is_archived), Phase 02 (health data collected)

## Context

S13 Settings đã host M14 (create tag). Cần thêm tab "Quản lý tags" cho:
- Taxonomy: view/merge/archive tất cả categories
- Provisional queue Level 1: domain đã biết, tag chưa validate
- Provisional queue Level 2: domain chưa biết, chỉ có text
- Chipify: health_context_raw → structured tag

**Route:** `/settings/tags` — tab mới trong S13.

## Files to modify/create

- `crm/templates/settings/tag_governance.html` — main template (mới)
- `crm/templates/settings/fragments/_tag_governance_tag_list.html`
- `crm/templates/settings/fragments/_tag_governance_provisional_row.html`
- `crm/templates/settings/fragments/_tag_governance_chipify_row.html`
- `crm/views/settings_tag_governance.py` (mới)
- `crm/routes/settings.py` — thêm `/settings/tags` + HTMX sub-routes
- `crm/docs/ui-spec/screens/S13-settings.md` — add tab + interactions

## Layout

```
/settings/tags
┌──────────────────────────────────────────────────────────────────────┐
│ [health_domain] [health_concern] [segment] [profile] [...] │ [+ Tag] │
│  ← tabs render động từ DISTINCT category WHERE is_provisional=0      │
│  + tab cố định: [⚠ Chờ duyệt L1] [⚠ Chờ duyệt L2]                  │
├──────────────────────────────────────────────────────────────────────┤
│ Tab: health_domain — 8 tags                   [🔍 tìm...]            │
│ ┌────────────────┬───────┬──────────────┬──────────────────────────┐ │
│ │ Tên            │ Dùng  │ Nguồn        │ Actions                  │ │
│ ├────────────────┼───────┼──────────────┼──────────────────────────┤ │
│ │ tim-mach       │ 34 KH │ seeded       │ [Sửa] [Merge] [Lưu trữ] │ │
│ │ ho-hap         │ 12 KH │ seeded       │ [Sửa] [Merge] [Lưu trữ] │ │
│ └────────────────┴───────┴──────────────┴──────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│ Tab: ⚠ Chờ duyệt L1 — domain đã biết (8 tags)                       │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ "huyet-ap-cao" · health_concern · 8 KH                           │ │
│ │   → [Xác nhận] [Đổi tên] [Merge vào tag có sẵn] [Xoá]           │ │
│ │ "mat-ngu" · health_concern · 5 KH                                │ │
│ │   → [Xác nhận] [Đổi tên] [Merge vào than-kinh-ngu] [Xoá]        │ │
│ └──────────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│ Tab: ⚠ Chờ duyệt L2 — chưa biết domain (5 tags)                     │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ "khach-hay-hoi-combo" · NULL · 3 KH                              │ │
│ │   → Gán domain: [health_concern ▼]  [Xác nhận] [Xoá]            │ │
│ │ "tang-can" · NULL · 2 KH                                         │ │
│ │   → Gán domain: [___________ ▼]     [Xác nhận] [Xoá]            │ │
│ └──────────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│ CHIPIFY — health_context_raw chưa xử lý (23 KH)    [Xử lý tất cả]   │
│ ┌────────────────────────────────────────────────────────────────┐   │
│ │ "huyết áp cao, uống thuốc" · 8 KH                              │   │
│ │   → [Tạo tag L1: health_concern] [Map hiện có ▼] [Bỏ qua]      │   │
│ │ "khach-thich-combo" · 3 KH                                     │   │
│ │   → [Tạo tag L2: chưa rõ domain] [Map hiện có ▼] [Bỏ qua]      │   │
│ └────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

## Features

### A. Taxonomy panel (canonical tags)

Category tabs render động: `SELECT DISTINCT category FROM crm_tag WHERE is_provisional=0 AND is_archived=0 ORDER BY category`. Thêm category mới → tự xuất hiện, không sửa code.

**Merge** `POST /settings/tags/merge`:
```json
{ "canonical_tag_id": "X", "merge_tag_ids": ["Y", "Z"] }
```
Toàn bộ trong 1 transaction — thứ tự bắt buộc (FK: crm_party_tag.tag_id và crm_ext_tag_map.crm_tag_id đều trỏ crm_tag):

```sql
-- 1. Reassign party_tag. PK (party_id, tag_id): party có CẢ tag Y lẫn X → UPDATE thô sẽ collide.
--    INSERT OR IGNORE cặp mới rồi xóa cặp cũ; giữ source/tagged_by/tagged_at của row đến trước (IGNORE giữ row X có sẵn).
INSERT OR IGNORE INTO crm_party_tag (party_id, tag_id, tagged_by, tagged_at, source, ext_ref)
  SELECT party_id, 'X', tagged_by, tagged_at, source, ext_ref
  FROM crm_party_tag WHERE tag_id IN ('Y','Z');
DELETE FROM crm_party_tag WHERE tag_id IN ('Y','Z');

-- 2. Repoint ACL mapping (từ 260619 phase 01 — nếu Y/Z đang là target của inbound sync,
--    không repoint thì DELETE crm_tag gãy FK, hoặc mapping mồ côi → sync chết).
--    UNIQUE (ext_tag_id, crm_tag_id) trên map: dedupe trước khi repoint.
DELETE FROM crm_ext_tag_map WHERE crm_tag_id IN ('Y','Z')
  AND EXISTS (SELECT 1 FROM crm_ext_tag_map m2
              WHERE m2.ext_tag_id = crm_ext_tag_map.ext_tag_id AND m2.crm_tag_id = 'X');
UPDATE crm_ext_tag_map SET crm_tag_id='X' WHERE crm_tag_id IN ('Y','Z');

-- 3. Xóa tag đã merge
DELETE FROM crm_tag WHERE tag_id IN ('Y','Z');
```
Confirm dialog trước (không reversible). Dialog hiện thêm cảnh báo nếu Y/Z có mapping active: "Tag này đang nhận sync từ Sapo — mapping sẽ chuyển sang tag đích."

**Archive** `POST /settings/tags/{id}/archive`:
```sql
-- Tag đang là target của inbound mapping active mà chỉ ẩn UI → sync tiếp tục bơm
-- party_tag vào tag vô hình (zombie data). Deactivate mapping cùng lúc.
UPDATE crm_ext_tag_map SET is_active=0
  WHERE crm_tag_id=? AND is_active=1 AND direction IN ('inbound','both');
UPDATE crm_tag SET is_archived=1 WHERE tag_id=?;
```
Party_tag rows giữ nguyên — nhưng lưu ý: rows `source='sapo_v2_sync'` của tag này sẽ bị mirror-reconcile (260619 phase 03) xóa ở lần sync kế tiếp vì mapping đã inactive (đúng ngữ nghĩa: archive = ngừng nhận từ nguồn). Rows `crm_user` giữ nguyên. Unarchive available — nhưng KHÔNG tự bật lại mapping (admin bật tay qua seed/SQL nếu muốn, tránh bất ngờ).

### B. Provisional queue Level 1 (domain đã biết)

**Query:** `SELECT * FROM crm_tag WHERE is_provisional=1 AND category IS NOT NULL AND is_archived=0`

Per row actions:
- **[Xác nhận]** → `UPDATE crm_tag SET is_provisional=0 WHERE tag_id=?` — promote to canonical
- **[Đổi tên]** → inline edit `name` field → save
- **[Merge vào tag có sẵn]** → dropdown canonical tags cùng category → merge workflow
- **[Xoá]** → DELETE crm_tag + crm_party_tag rows (confirm trước)

### C. Provisional queue Level 2 (domain chưa biết)

**Query:** `SELECT * FROM crm_tag WHERE is_provisional=1 AND category IS NULL AND is_archived=0`

Per row: phải gán domain trước mới promote được:
1. Chọn category từ dropdown
2. **[Xác nhận]** → `UPDATE crm_tag SET category=?, is_provisional=0`
3. Optional: rename + merge

### D. Chipify panel (health_context_raw)

**Query:**
```sql
SELECT
  json_extract(cp.custom, '$.health_context_raw') AS raw_text,
  COUNT(*) AS n
FROM crm_customer_profile cp
WHERE
  json_extract(cp.custom, '$.health_context_raw') IS NOT NULL
  AND (json_extract(cp.custom, '$.health_context_raw_reviewed') IS NULL
       OR json_extract(cp.custom, '$.health_context_raw_reviewed') = 'false')
GROUP BY raw_text
ORDER BY n DESC
```

Per pattern:
- **[Tạo tag L1]** → M14 prefilled `category='health_concern', is_provisional=0` → sau tạo: assign tất cả matching parties + mark `health_context_raw_reviewed=true`
- **[Tạo tag L2]** → M14 với `category=NULL, is_provisional=1` → assign + mark reviewed
- **[Map hiện có]** → dropdown existing tags → assign + mark reviewed
- **[Bỏ qua]** → chỉ mark `health_context_raw_reviewed=true`

**[Xử lý tất cả]** → bulk skip tất cả unreviewed (clear queue không tạo tag).

### E. Rep tạo provisional tag inline (from S14/M03)

Khi rep gõ text không tìm thấy chip:

**Level 1** (biết domain, e.g., đang trong health_concern context):
```json
POST /customers/{id}/tags/inline
{ "name": "huyet-ap-cao", "category": "health_concern", "is_provisional": true, "source": "crm_user" }
```
→ tạo `crm_tag(is_provisional=1, category='health_concern')` + assign

**Level 2** (không rõ domain, từ M03 generic):
```json
POST /customers/{id}/tags/inline
{ "name": "thich-combo", "category": null, "is_provisional": true, "source": "crm_user" }
```
→ tạo `crm_tag(is_provisional=1, category=NULL)` + assign

Cả 2 trường hợp vào queue tương ứng trong Governance Admin.

## Access control

Route `/settings/tags` chỉ accessible `role IN ('admin', 'ops')`.

## Validation

- Category tabs render đúng tất cả canonical categories
- Tab "Chờ duyệt L1" chỉ hiện tags có `category IS NOT NULL AND is_provisional=1`
- Tab "Chờ duyệt L2" chỉ hiện tags có `category IS NULL AND is_provisional=1`
- Promote L1 → tag xuất hiện trong canonical tab đúng category, ẩn khỏi L1 queue
- Promote L2 (sau khi gán domain) → tag xuất hiện trong canonical tab, ẩn khỏi L2 queue
- Merge: party_tag reassigned (party có cả 2 tag → không duplicate, không crash PK); crm_ext_tag_map repointed sang tag đích, không còn row trỏ tag đã xóa
- Merge tag đang có mapping active → dialog hiện cảnh báo sync
- Archive: tag ẩn khỏi M03/M14/S14 chip list; mapping inbound của tag bị set is_active=0
- Unarchive: tag hiện lại, mapping KHÔNG tự bật
- Chipify: sau apply → parties nhận crm_party_tag + raw_text marked reviewed
- role=rep → 403 khi access route

---

## Implementation Notes (2026-07-07) — DONE

Doc paths above are approximate (per plan convention); real hexagonal-layout paths used:

- `crm/src/adapters/outbound/sqlite/tag_governance_repository.py` — raw SQL (merge/archive/queues/chipify)
- `crm/src/application/tag_governance_service.py` — business rules on top of the repo + TagService
- `crm/src/adapters/inbound/web/screens/management/screen_mgmt_tag_governance.py` — routes
- `crm/src/adapters/inbound/web/screens/management/screen_management.py` — wired new router
- `crm/src/composition.py` — added `tag_governance` repo/service to SqliteRepos/Services
- `crm/src/adapters/inbound/web/templates/settings_tag_governance.html` + 4 fragments (taxonomy/l1/l2/chipify rows) + `fragments/modal_tag_governance_merge.html`
- Reused the real M14 modal (`fragments/modal_m14_create_tag.html`, GET `/settings/tags/modal/create` in `screen_mgmt_settings.py`) for Chipify's "Tạo tag L1/L2" — extended with optional prefill/chipify-post-url params + 2 new category options (health_domain/health_concern), NOT rebuilt
- `crm/src/domain/entities/profile.py` (Tag: +is_provisional/+is_archived), `application/tag_service.py` (create_tag: +is_provisional), `adapters/outbound/sqlite/tag_note_repository.py` (create_tag SQL + is_archived filter on list_tags so M03/M14 pickers hide archived tags)
- Tests: `crm/src/tests/test_tag_governance_admin.py` (25 tests — merge PK-collision, ext_tag_map dedupe/repoint, archive/unarchive, L1/L2 filtering, chipify, router wiring)

**Access control:** reused `require_admin` (existing `/settings/*` convention). It is currently a **no-op stub** (`adapters/inbound/http/auth_dependency.py:67-68`, explicit TODO "temporarily allow all authenticated users into /settings") — confirmed live: `CF_ACCESS_AUDIENCE` IS set in this deployment, yet `GET /settings/tags` with no CF-Access-JWT header returned 200. This is a pre-existing, documented v1 gap across ALL `/settings/*` routes (not introduced by this phase) — did not add a bespoke role check for just this screen (would create an inconsistent security surface vs. the rest of Settings). **role=rep → 403 validation item: not achievable in current environment** (would need a real CF Access JWT or reworking auth_dependency.py app-wide) — flagged for user decision.

All other validation bullets verified live against the running `crm` container + real `crm.db` (merge PK-collision, ext_tag_map dedupe+repoint, archive deactivates mapping + hides from S14/M03, unarchive doesn't reactivate mapping, L1/L2 queue filtering, promote L1/L2, chipify create+assign+mark-reviewed). Test data cleaned up afterward.
