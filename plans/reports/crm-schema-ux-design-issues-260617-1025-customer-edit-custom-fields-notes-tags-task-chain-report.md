# CRM Schema & UX Design Issues — Retail Activation Edition

**Date:** 2026-06-17  
**Context:** Review of `crm/docs/ui-spec` trước khi implement edit/customize surfaces.  
**Framing:** Retail activation workflow — cần reach direct contact với khách, track toàn bộ interaction chain từ warehouse recommendation đến outcome.

---

## Quyết định đã align

| # | Vấn đề | Quyết định |
|---|--------|-----------|
| A | Custom field entity_type | `customer` \| `order` — bắt buộc |
| B | Custom field section | Free-text (không enum) — linh hoạt hơn |
| C | Facebook / Zalo | `crm_party_identity` với identity_type mới |
| D | Address | Column riêng trên `crm_party` (có `address_source` + editable) |
| E | Phone 2 | `crm_party_identity` type=phone_secondary |
| F | Note types | Có — enum: general \| preference \| contact_pref \| warning \| outcome \| internal |
| G | Note pinned + pinned_until + visibility | Có implement |
| H | Tag category | Enum chuẩn (6 loại) — không free-text |
| I | `crm_party_tag` audit trail | Có — thêm tagged_at + tagged_by_user_id |
| J | `crm_task.action_queue_id` FK | Có implement |
| K | `crm_task.outcome` | Có — NULL(pending) \| success \| no_response \| escalated \| skipped |
| L | `crm_activity.task_id` FK | Có implement |
| M | CRM ownership | CRM owns customer relationship; warehouse owns transaction analytics |
| N | Platform independence | Thêm `crm_party_external_id` tách identity khỏi Sapo |
| O | Distilled insights | `crm_party_insight` entity riêng, surface trong P01 |

---

## Issue 1 — Custom Fields: entity scope + section grouping

**Schema bổ sung vào `crm_custom_field_def`:**
```sql
entity_type  TEXT NOT NULL DEFAULT 'customer'  -- 'customer' | 'order'
section      TEXT                               -- free-text, VD: "Thông tin bổ sung", "Nội bộ"
sort_order   INTEGER DEFAULT 0
```

**Lưu order custom fields:** `crm_order_profile.custom` JSON1 (tương tự customer profile).

---

## Issue 2 — Contact Channels: identity ≠ contact channel

`crm_party_identity` dùng cho dedup/search. Activation cần thêm contact-specific metadata.

**Bổ sung vào `crm_party_identity`:**
```sql
display_label   TEXT        -- "Số chính", "Zalo", "Facebook shop"
contact_status  TEXT DEFAULT 'active'  -- active | invalid | dnc (do_not_contact)
is_preferred    BOOLEAN DEFAULT FALSE  -- kênh ưu tiên liên lạc
```

**Thêm identity_type mới:** `zalo`, `facebook`, `phone_secondary`

**Vì sao không tạo bảng riêng:** cùng phone number vừa là identity (dedup) vừa là contact channel — tách ra phải sync.

---

## Issue 3 — Address: sync Sapo nhưng editable

Sapo có address trong đơn hàng nhưng marketplace orders thường bị mask.  
Address không phải identity (không dùng dedup), không phải custom field → column riêng.

**Bổ sung vào `crm_party`:**
```sql
address_line        TEXT
ward                TEXT
district            TEXT
province            TEXT
address_source      TEXT DEFAULT 'manual'  -- 'sapo_sync' | 'manual'
address_note        TEXT   -- "Địa chỉ sàn bị mask, đã xác nhận qua điện thoại"
address_updated_at  TIMESTAMPTZ
address_updated_by  INTEGER REFERENCES crm_app_user(id)
```

**Sync rule:** Nếu `address_source='manual'` → sync không ghi đè. Nếu `sapo_sync` → cập nhật bình thường.

---

## Issue 4 — Notes: redesign với typed + pinned + visibility

**Vấn đề hiện tại:** `crm_note` là text blob, không phân loại, không surface đúng chỗ.

**Schema mới:**
```sql
crm_note (
  id, party_id, body TEXT NOT NULL,
  note_type      TEXT DEFAULT 'general',
  -- general | preference | contact_pref | warning | outcome | internal
  pinned         BOOLEAN DEFAULT FALSE,
  pinned_until   DATE,             -- tự unpinned sau ngày này
  visibility     TEXT DEFAULT 'team',  -- team | manager_only | private
  task_id        INTEGER REFERENCES crm_task(id),    -- nullable
  campaign_id    INTEGER REFERENCES crm_campaign(id), -- nullable
  created_at, created_by_user_id,
  updated_at, updated_by_user_id,
  deleted_at     -- soft delete
)
```

**note_type → surface behavior:**

| Type | Surface ở đâu | Behavior đặc biệt |
|------|--------------|-------------------|
| `contact_pref` | S01 worklist row + contact section S03 | "Chỉ Zalo sau 8pm" |
| `preference` | P01 insight panel khi chuẩn bị gọi | "Thích màu hồng, size M" |
| `warning` | Badge đỏ ngay khi mở S03, top of P05 | Chỉ manager xóa được |
| `outcome` | P05, linked task_id + campaign_id | Nhận định rep sau activation |
| `internal` | Ẩn với junior staff | Phối hợp nội bộ |
| `general` | P05 | Default, không behavior đặc biệt |

**Ranh giới P03 vs P05 (làm rõ):**
- P03 Activity Timeline: event log immutable (gọi lúc 10:05, 3 phút, không bắt máy)
- P05 Notes: context sống rep muốn nhớ, có thể sửa (nhận định, sở thích, cảnh báo)

---

## Issue 5 — Tags: category enum + audit trail

**Tag category enum chuẩn:**
```
behavioral   -- hành vi mua (hay mua cuối tuần, thích flash sale)
demographic  -- đặc điểm khách (doanh nghiệp, cá nhân)
preference   -- sở thích sản phẩm
vip_tier     -- phân tầng (Gold, Silver)
risk         -- cảnh báo (nợ xấu, hay hoàn)
source       -- nguồn (ads, referral, walk-in)
```

**Bổ sung vào `crm_party_tag`:**
```sql
tagged_at         TIMESTAMPTZ DEFAULT now()
tagged_by_user_id INTEGER REFERENCES crm_app_user(id)
```

---

## Issue 6 — action_queue → task → activity/note: review chain

**Schema changes:**
```sql
-- crm_task
action_queue_id  TEXT         -- FK về wh_action_queue.action_id (nullable)
outcome          TEXT         -- NULL | success | no_response | escalated | skipped
completed_at     TIMESTAMPTZ

-- crm_activity (extend)
task_id             INTEGER REFERENCES crm_task(id)   -- nullable
channel_used        TEXT   -- phone | zalo | facebook | visit | email
contact_outcome     TEXT   -- reached | no_answer | callback_requested | refused | converted
callback_at         TIMESTAMPTZ
contact_duration_s  INTEGER

-- crm_note
task_id     INTEGER REFERENCES crm_task(id)    -- nullable
campaign_id INTEGER REFERENCES crm_campaign(id) -- nullable
```

**Chain đầy đủ:**
```
wh_action_queue.action_id
  → crm_task.action_queue_id
    → crm_activity.task_id (event log: gọi lúc mấy, kết quả gì)
    → crm_note.task_id     (nhận định: rep viết gì sau đó)
```

**UX implication:** P01 hiển thị badge "Đã xử lý" khi task.outcome IS NOT NULL.

---

## Issue 7 — Distilled Insights: human insight layer

Notes không đủ cho thông tin được đúc kết từ nhiều lần tương tác. Cần entity riêng.

**New table `crm_party_insight`:**
```sql
crm_party_insight (
  id, party_id,
  insight_type  TEXT,
  -- buying_pattern | persona | relationship | life_event | decision_style | advocate_signal
  body          TEXT NOT NULL,
  confidence    TEXT DEFAULT 'medium',  -- low | medium | high
  source_note_id  INTEGER REFERENCES crm_note(id),   -- promoted từ note
  source_task_id  INTEGER REFERENCES crm_task(id),
  created_by, created_at,
  updated_by, updated_at,
  is_active     BOOLEAN DEFAULT TRUE   -- invalidate nếu sai
)
```

**UX "Promote to insight":** Sau khi viết outcome note → button "★ Đúc kết thành insight" → mini-form chọn insight_type + tóm tắt + confidence.

**Surface trong P01:** Hai lớp insight cùng chỗ:
- 🤖 Warehouse: RFM, churn risk, action queue
- 👤 Rep insights: persona, buying pattern, decision style

**Future:** Warehouse đọc `crm_party_insight` để tinh chỉnh recommendation (persona='shop_buyer' → gợi ý giá sỉ). V1 one-way, V2 reverse-ETL.

---

## Issue 8 — CRM Ownership + Platform Independence

**Quyết định:** CRM owns customer relationship data; warehouse owns transaction analytics.

| Data | Owner | Lý do |
|------|-------|-------|
| Order history, RFM, LTV | Warehouse (DuckDB) | Analytical, volume lớn |
| Customer identity + contacts | CRM (SQLite) | Rep edit, multi-source |
| Interaction history | CRM | Không có trong Sapo |
| Human insights | CRM | Không thể auto-generate |

**Platform independence:** Anti-corruption layer đã có ở dbt (`fact_orders`, `dim_customers` → platform-agnostic). Khi đổi Sapo → system X: chỉ thay ingestion adapter + điều chỉnh dbt models; CRM không đổi nếu warehouse schema giữ nguyên.

**New table `crm_party_external_id`:**
```sql
crm_party_external_id (
  party_id    INTEGER REFERENCES crm_party(id),
  system      TEXT,   -- 'sapo' | 'shopify' | 'kiotviet' | ...
  external_id TEXT,
  UNIQUE(system, external_id)
)
```
`crm_party` là master identity. Sapo customer_id là external reference — không phải PK của CRM.

---

## Issue 9 — Activation UX Redesign

### S03 Left Column (tái cấu trúc)
```
Cảnh báo (warnings pinned — luôn visible nếu có)
Liên lạc [+]          ← tất cả crm_party_identity channels
  📞 0912 xxx   Số chính  ✓ active
  💬 zalo_id    Zalo      ✓ active
  📘 fb_handle  Facebook
Địa chỉ [✎]
  Hồ Chí Minh / confirmed manual
Thông tin [✎]          ← crm_party core fields
Tags [✎]
Custom Fields (by section) [✎]
```

### S01 Worklist Row
Hiển thị `contact_pref` note inline + quick-action buttons:
```
Nguyễn Văn A  ·  💡 Mua lại SPF  ·  ~850k
💬 Chỉ Zalo sau 8pm    [Zalo] [Xem 360]
```

### M08 Extension — Contact Attempt Mode
Thêm mode `contact_attempt`:
- Kênh: phone | zalo | facebook | visit
- Kết quả: reached | no_answer | callback | refused
- Hẹn gọi lại: datetime (nếu callback)
- Auto-tạo follow-up task nếu có callback_at

### New M15 — Edit Contact & Core Info Modal
Modal mới để edit: display_name, contacts (add/remove/update identity), address.  
Tách khỏi M06 (custom fields) vì đây là core structured data, không phải custom.

### New M16 — Promote to Insight Modal
Mini-modal từ note: chọn insight_type, confirm/edit body, set confidence.

---

## Các spec files cần update

| File | Thay đổi |
|------|---------|
| `S03` | Tái cấu trúc left col, thêm interactions M15, M16 |
| `S01` | Thêm contact_pref inline, quick-action buttons |
| `P01` | Thêm human insight section (crm_party_insight) |
| `P05` | Note types, tabs filter, pinned section, promote action |
| `M06` | Dùng entity_type + section grouping |
| `M08` | Thêm mode contact_attempt |
| `M13` | Thêm entity_type, section, sort_order |
| `M14` | Category từ free-text → enum dropdown |
| `M15` | New — Edit Contact & Core Info |
| `M16` | New — Promote Note to Insight |
| `20-domain-rules` | Thêm R13 (address_source sync rule) |

---

## Unresolved questions

1. **Zalo tích hợp:** V1 log thủ công hay tích hợp Zalo OA API sau?
2. **Callback task auto-create:** Tự tạo hay rep tự chọn?
3. **Warehouse feedback loop (V2):** Timeline để warehouse đọc crm_party_insight?
4. **Order custom fields:** Render ở đâu trong UX đơn hàng?
