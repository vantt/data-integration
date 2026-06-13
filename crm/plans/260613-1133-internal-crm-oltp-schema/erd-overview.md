# ERD Tổng & Giải thích — Internal CRM (SQLite)

> Tài liệu review schema trước khi code. Xem kèm [plan.md](plan.md) + các phase. DDL kiểu Postgres trong phase → map SQLite theo "Quy ước SQLite" ở plan.md (`uuid`→TEXT, `timestamptz`→TEXT UTC, `jsonb`→TEXT+JSON1, prefix `crm_*`/`wh_*`).

## 0. Bản đồ domain & ranh giới 2 file

```mermaid
flowchart TB
  subgraph SRC["Nguồn ngoài"]
    SAPO[(Sapo online)]
    WH[(Warehouse olap.duckdb<br/>insight đã tính)]
    FB[Messenger API<br/>v1; Shopee/Zalo sau]
  end

  subgraph CACHE["cache.db — Python ghi (1 writer) · read-only cho CRM"]
    direction LR
    WHI["Nhóm 2 — Insight<br/>customer_insight · product_insight · action_queue"]
    WHR["Nhóm 3 — Quan hệ gốc<br/>customer_base · product · order_hdr"]
    WHS[wh_party_seed]
  end

  subgraph CRM["crm.db — Go ghi (1 writer) · SQLite WAL"]
    direction LR
    IDENT["Identity<br/>party · identity · dedup · merge_log"]
    C360["Customer 360<br/>profile · custom_field · tag · note"]
    ENG["Engagement<br/>activity · task · conversation · message"]
    GROW["Growth<br/>segment · campaign · ad_*"]
  end

  SAPO -->|dlt hiện có| WH
  WH -->|reverse-ETL Python| CACHE
  FB -->|ingest mới Phase 05| ENG
  CACHE -. ATTACH read-only .-> CRM
  WHS -. Go đọc seed → tạo party .-> IDENT
  WHI -. sinh task + insight .-> ENG
  WHR -. order/customer/product .-> C360
  CRM -->|outbox → Sapo API · Phase 07 hoãn| SAPO
  Users["Sales/CSKH ~10"] -->|Go app hexagonal| CRM
```

**3 nhóm dữ liệu — phân biệt rõ ai sở hữu:**

| Nhóm | Ví dụ | Nguồn sự thật | Ở đâu | CRM ghi? |
|---|---|---|---|---|
| 1. CRM tự tạo | party, enrichment, tag, note, task, conversation, segment, campaign | **CRM** | `crm.db` | ✅ |
| 2. Insight đã tính | RFM, affinity, next_purchase, action_queue, product_health | warehouse | `cache.db` `wh_*_insight` | ❌ |
| 3. Quan hệ gốc | order, customer base, product (catalog) | Sapo→warehouse | `cache.db` `wh_order_hdr`/`customer_base`/`product` | ❌ |

**Nguyên tắc:** mỗi file đúng **1 writer** (Go↔`crm.db`, Python↔`cache.db`) → không tranh chấp. FK **trong cùng file vẫn dùng bình thường** (bật `PRAGMA foreign_keys=ON`); chỉ liên kết **`crm.db`↔`cache.db`** là **value-link** (so giá trị `customer_id`), không FK — vì SQLite **không enforce FK qua file ATTACH**. `crm_party` là **trục trung tâm** — gần như mọi bảng tác nghiệp gắn `party_id`.

---

## 1. Identity & Golden Record (Phase 02) — lõi v1

```mermaid
erDiagram
  crm_party ||--o{ crm_party_identity : "1 người ↔ N danh tính"
  crm_party ||--o| crm_customer_profile : "1-1 enrichment"
  crm_party ||--o{ crm_party_merge_log : "surviving"
  crm_dedup_candidate }o--|| crm_party : "party_a"
  crm_dedup_candidate }o--|| crm_party : "party_b"

  crm_party {
    TEXT party_id PK
    TEXT primary_phone "chuẩn hoá +84"
    TEXT primary_email
    TEXT display_name
    INTEGER is_merged "0/1"
    TEXT merged_into FK "self, nếu bị gộp"
  }
  crm_party_identity {
    TEXT identity_id PK
    TEXT party_id FK
    TEXT source_system "sapo|messenger|zalo|manual"
    TEXT identity_type "sapo_customer|phone|email|psid"
    TEXT identity_value "UNIQUE(type,value)"
    REAL confidence
  }
  crm_dedup_candidate {
    TEXT candidate_id PK
    TEXT party_a FK
    TEXT party_b FK
    TEXT match_rule "exact_phone|fts_name"
    REAL match_score
    TEXT status "pending|merged|rejected"
  }
  crm_party_merge_log {
    TEXT merge_id PK
    TEXT surviving_party_id FK
    TEXT merged_party_id
    TEXT snapshot "JSON, để undo"
  }
```

**Vì sao:** Warehouse KHÔNG gộp khách trùng qua SĐT/email → CRM tự sở hữu. `crm_party` = bản ghi vàng (1 người thật). `crm_party_identity` = bảng cầu nối mọi danh tính về party; `UNIQUE(identity_type, identity_value)` đảm bảo 1 SĐT/psid chỉ thuộc 1 party. Dedup: exact SĐT (~90%) tự link; fuzzy tên (FTS5) → `crm_dedup_candidate` cho NV duyệt. Mọi merge ghi `crm_party_merge_log.snapshot` để **hoàn tác**.

---

## 2. Customer 360 — Enrichment (Phase 03)

```mermaid
erDiagram
  crm_party ||--o| crm_customer_profile : ""
  crm_party ||--o{ crm_party_tag : ""
  crm_tag ||--o{ crm_party_tag : ""
  crm_party ||--o{ crm_note : ""
  crm_custom_field_def ||..o{ crm_customer_profile : "validate custom JSONB (logical)"
  crm_app_user ||--o{ crm_customer_profile : "owner phụ trách"

  crm_customer_profile {
    TEXT party_id PK "FK→crm_party 1-1"
    TEXT owner_user_id FK "NV phụ trách"
    TEXT lifecycle_stage "thủ công, bổ trợ wh_*"
    TEXT address "JSON đã chuẩn hoá"
    TEXT custom "JSON: custom field values"
    INTEGER consent_contact "0/1 compliance"
  }
  crm_custom_field_def {
    TEXT field_id PK
    TEXT field_key "khoá trong custom JSON"
    TEXT data_type "text|number|date|select.."
    TEXT options "JSON"
  }
  crm_tag {
    TEXT tag_id PK
    TEXT name
    TEXT category
  }
  crm_party_tag {
    TEXT party_id PK "FK"
    TEXT tag_id PK "FK"
    TEXT tagged_by FK
  }
  crm_note {
    TEXT note_id PK
    TEXT party_id FK
    TEXT body
    TEXT author_user_id FK
  }
```

**Vì sao:** Sapo ít custom field → đây là giá trị cốt lõi. `custom` (JSON1) lưu giá trị field tuỳ biến; `crm_custom_field_def` = registry để app render UI + validate (thêm field mới KHÔNG cần migration). Quy ước: **warehouse = sự thật tính toán, profile = ghi nhận con người** — không ghi đè nhau. `consent_contact=false` sẽ loại khỏi campaign (Phase 06).

---

## 3. Engagement — Activity, Task, Chat (Phase 05)

```mermaid
erDiagram
  crm_party ||--o{ crm_activity : ""
  crm_party ||--o{ crm_task : "nullable"
  crm_party ||--o{ crm_conversation : "nullable tới khi resolve psid"
  crm_conversation ||--o{ crm_message : ""
  crm_app_user ||--o{ crm_task : "assignee"
  crm_app_user ||--o{ crm_conversation : "assignee inbox"

  crm_activity {
    TEXT activity_id PK
    TEXT party_id FK
    TEXT activity_type "call|note|visit|chat"
    TEXT related_order_code "gắn đơn, no FK"
    TEXT staff_user_id FK
    TEXT occurred_at "UTC"
  }
  crm_task {
    TEXT task_id PK
    TEXT party_id FK
    TEXT status "open|doing|done"
    TEXT assignee_user_id FK
    TEXT source "manual|action_queue|campaign"
    TEXT source_ref "action_id/campaign_id"
    TEXT due_at "UTC"
  }
  crm_conversation {
    TEXT conversation_id PK
    TEXT party_id FK "nullable"
    TEXT channel "messenger(v1)|shopee|zalo"
    TEXT external_thread_id "UNIQUE(channel,thread)"
    TEXT status "open|pending|closed"
  }
  crm_message {
    TEXT message_id PK
    TEXT conversation_id FK
    TEXT direction "in|out"
    TEXT external_message_id "idempotent"
    TEXT sent_at "UTC"
  }
```

**Vì sao:** Warehouse chat là stub disabled, không link customer → CRM tự ingest (v1 Messenger) + tự dựng `psid→party` qua `crm_party_identity`. `crm_task.source='action_queue'` → việc sinh tự động từ `wh_action_queue` (CALL_NOW/WIN_BACK…), `source_ref` chống tạo trùng. `related_order_code` gắn đơn nhưng **không FK** (đơn nằm ở warehouse).

---

## 4. Growth — Segment, Campaign, Ads (Phase 06)

```mermaid
erDiagram
  crm_segment ||--o{ crm_segment_member : ""
  crm_party ||--o{ crm_segment_member : ""
  crm_segment ||--o{ crm_campaign : ""
  crm_campaign ||--o{ crm_campaign_target : ""
  crm_party ||--o{ crm_campaign_target : ""
  crm_ad_campaign ||--o{ crm_ad_spend : ""
  crm_ad_campaign ||--o{ crm_ad_lead : ""
  crm_party ||--o{ crm_ad_lead : "nullable"
  crm_ad_campaign ||--o{ crm_ad_attribution : ""
  crm_party ||--o{ crm_ad_attribution : ""

  crm_segment {
    TEXT segment_id PK
    TEXT name
    INTEGER is_dynamic "0/1"
    TEXT definition "JSON rule trên party+wh_*"
  }
  crm_segment_member {
    TEXT segment_id PK "FK"
    TEXT party_id PK "FK"
    TEXT source "rule|manual"
  }
  crm_campaign {
    TEXT campaign_id PK
    TEXT objective "reactivation|winback|upsell"
    TEXT segment_id FK
    TEXT status "draft|running|done"
  }
  crm_campaign_target {
    TEXT campaign_id PK "FK"
    TEXT party_id PK "FK"
    TEXT status "queued|sent|converted"
    TEXT converted_order_code
    INTEGER converted_revenue_vnd
  }
  crm_ad_campaign {
    TEXT ad_campaign_id PK
    TEXT platform "facebook|google|tiktok"
    TEXT external_campaign_id
  }
  crm_ad_spend {
    TEXT spend_date PK
    TEXT ad_campaign_id PK "FK"
    INTEGER spend_vnd
    INTEGER clicks
  }
  crm_ad_lead {
    TEXT lead_id PK
    TEXT ad_campaign_id FK
    TEXT party_id FK "nullable"
    TEXT psid
  }
  crm_ad_attribution {
    TEXT attribution_id PK
    TEXT party_id FK
    TEXT ad_campaign_id FK
    TEXT order_code "đơn quy cho ad"
    TEXT model "last_touch"
  }
```

**Vì sao:** Segment dựng trên signal `wh_*` (value_group, customer_status, affinity) — KHÔNG re-derive. Campaign → `crm_campaign_target` theo dõi từng khách (queued→converted) + đo `converted_order_code` để tính ROI reactivation. Ads: warehouse không có ad→order → CRM tự ghi `crm_ad_lead` (click/messenger ad-referral) → resolve party → `crm_ad_attribution` (v1 last-touch đơn giản).

---

## 5. cache.db — Warehouse Read-Cache (Phase 04, Python ghi)

> `cache.db` = **mọi dữ liệu gốc-warehouse CRM cần ĐỌC**, 2 nhóm: **(2) insight đã tính** + **(3) quan hệ gốc** (order/customer/product). CRM không tính lại, không ghi. Quan hệ trong cache dùng cột index (`customer_id`/`sku`), **không bật FK** (bulk-load).

```mermaid
erDiagram
  wh_customer_base ||..o{ wh_order_hdr : "customer_id (index, no FK)"
  wh_customer_insight {
    TEXT customer_key PK
    INTEGER customer_id "value-link party"
    TEXT value_group "VIP|GOLD|.."
    TEXT customer_status "active|at_risk|churned"
    TEXT next_purchase_signal "OVERDUE|DUE_SOON"
    TEXT top_affinity_product
    TEXT refreshed_at
  }
  wh_action_queue {
    TEXT action_id PK
    TEXT customer_key
    TEXT action_type "CALL_NOW|WIN_BACK.."
    INTEGER value_at_stake_vnd
    TEXT rationale_vi
  }
  wh_product_insight {
    TEXT product_key PK
    TEXT sku
    TEXT health_class "STAR|DOG.."
    TEXT oos_risk
    REAL realized_margin_pct
  }
  wh_customer_base {
    TEXT customer_key PK
    INTEGER customer_id "value-link party"
    TEXT customer_code
    TEXT display_name
    TEXT phone
    TEXT customer_group
  }
  wh_product {
    TEXT product_key PK
    TEXT sku
    TEXT product_name
    TEXT brand
    INTEGER unit_price
  }
  wh_order_hdr {
    TEXT order_id PK
    TEXT order_code
    INTEGER customer_id "value-link party"
    INTEGER date_key "ICT YYYYMMDD"
    INTEGER net_revenue
    TEXT status
  }
  wh_party_seed {
    INTEGER customer_id PK
    TEXT customer_key
    TEXT seen_at "Go đọc → tạo party"
  }
  wh_sync_run {
    TEXT run_id PK
    TEXT source_table
    INTEGER row_count
    TEXT status
  }
```

**Vì sao:**
- **Nhóm 2 (insight)** — bản sao read-only của thứ ĐÃ TÍNH ở warehouse, CRM không tính lại.
- **Nhóm 3 (quan hệ)** — `wh_customer_base`/`wh_product`/`wh_order_hdr` để CRM "xem đơn của khách / chọn SP gợi ý / segment theo lịch sử mua". `order_hdr` **slim 1 dòng/đơn** (KHÔNG dòng đơn); full giỏ hàng để **on-demand** từ `olap.duckdb` khi cần.
- `wh_party_seed` = kênh 1 chiều để Go tạo `crm_party` (giữ 1-writer). Mọi link sang CRM bằng **giá trị `customer_id`**, không FK qua file.

**Truy vấn điển hình** (Go ATTACH cache.db): "đơn của party này" = `crm_party_identity` → `customer_id` → `cache.wh_order_hdr`.

> ⚠️ Convention khi đọc: tiền = VND `INTEGER`; margin dùng `realized_margin_pct` (KHÔNG gross — bug H010); `net_revenue` (VAT-inclusive); `date_key` ICT; `customer_type` B2B & `fact_payments` warehouse KHÔNG tin cậy.

---

## 6. Phase 07 — Sapo Write-back (HOÃN sau v1)

```mermaid
erDiagram
  crm_sync_outbox ||--o{ crm_sync_log : "mỗi lần gọi API"
  crm_sapo_writeback_map ||..o{ crm_sync_outbox : "field nào được ghi (logical)"

  crm_sync_outbox {
    TEXT outbox_id PK
    TEXT entity_id "party_id"
    TEXT operation "update_customer"
    TEXT payload "JSON"
    TEXT status "pending|sent|failed"
    TEXT idempotency_key "UNIQUE"
  }
  crm_sapo_writeback_map {
    TEXT field_key PK
    TEXT sapo_field
    INTEGER enabled "0/1 theo spike"
  }
  crm_sync_log {
    TEXT log_id PK
    TEXT outbox_id FK
    INTEGER status_code
  }
```

**Vì sao:** Transactional outbox — thay đổi enrichment được duyệt → `crm_sync_outbox` → worker (hexagonal `SapoWriter` adapter) gọi Sapo API. API order+customer đã xác nhận tồn tại; field writable cần spike nhẹ. `enabled` bật từng field theo kết quả spike. **Hoãn sau khi v1 ổn.**

---

## 7. Quy ước chung mọi bảng `crm_*`

- `*_id` PK = **TEXT (UUID app sinh)**. Mọi `*_user_id` → `crm_app_user`.
- `created_at`/`updated_at` = **TEXT UTC ISO-8601 'Z'**, hiển thị ICT ở app (kỷ luật TIMESTAMPTZ).
- Tiền VND = **INTEGER**; tỉ lệ/pct = **REAL**; bool = **0/1**; JSON = **TEXT + JSON1**.
- `crm_app_user` còn được tham chiếu bởi `note.author`, `activity.staff`, `campaign.created_by`, `segment.owner`, `dedup_candidate.reviewed_by`… (lược khỏi sơ đồ cho gọn).
- **FK trong cùng file**: dùng đầy đủ, nhớ bật `PRAGMA foreign_keys=ON` mỗi connection (mặc định SQLite TẮT → quên thì không enforce).
- **Không enforce FK qua file ATTACH**: `crm.db` ⇄ `cache.db` chỉ value-link `customer_id` (app tự đảm bảo toàn vẹn).

## Legend
- `||--o{` 1 ↔ 0..N (FK cứng, cùng file) · `||--o|` 1 ↔ 0..1 · `}o--||` N ↔ 1
- `..` (đường đứt) = liên kết **logic/value-link**, KHÔNG FK (qua file, hoặc registry validate).

## Câu hỏi mở
- Không còn — chờ bạn duyệt ERD để bắt đầu Phase 01.
