# PRD — Internal Retail CRM (OLTP)

| Trường | Giá trị |
|---|---|
| **Tiêu đề** | Internal Retail CRM — OLTP v1 |
| **Phiên bản** | 0.1 (Draft) |
| **Ngày** | 2026-06-13 |
| **Trạng thái** | Draft — chờ review |
| **Owner** | Data & Analytics Team |
| **Tài liệu liên quan** | [`../plans/260613-1133-internal-crm-oltp-schema/plan.md`](../plans/260613-1133-internal-crm-oltp-schema/plan.md) · ERD: `erd-overview.md` |

---

## 1. Executive Summary

Xây dựng một CRM nội bộ nhỏ gọn cho đội ngũ sales/CSKH (~10 người) của doanh nghiệp bán lẻ, chạy trên nền warehouse phân tích đã có (DuckDB/dbt). Hệ thống cho phép nhân viên **làm giàu — chuẩn hóa — khai thác** insight sâu theo từng khách hàng (RFM, hành vi mua, affinity SKU, tín hiệu reactivation) để bán lại hiệu quả hơn, trong khi warehouse và Sapo vẫn giữ nguyên vai trò tính toán và ghi đơn. CRM là lớp tác nghiệp duy nhất biết "làm gì tiếp theo" với từng khách cụ thể.

---

## 2. Vấn đề (Problem Statement)

| Vấn đề | Chi tiết |
|---|---|
| **Sapo cứng nhắc** | Ít custom field; không lưu lịch sử tương tác; không ghi nhận nguồn acquisition thật; không có inbox chat gắn với khách |
| **Không có golden record** | Warehouse không gộp khách trùng qua SĐT/email → cùng 1 người có thể có 2+ Sapo ID; không có SCD2 lịch sử profile |
| **Insight không actionable tại điểm tác nghiệp** | Warehouse tính được RFM, affinity, action_queue — nhưng NV không có công cụ để xem insight đó cùng lúc với hội thoại/task của khách, không thể giao việc theo signal |
| **Không đo được reactivation ROI** | Không có cách nào theo dõi "tôi gọi cho khách X → họ mua đơn Y → chiến dịch này đem lại bao nhiêu doanh thu" |
| **Chat rời rạc** | Messenger không gắn với Sapo customer ID; không thể gán NV xử lý; không theo dõi được |
| **Không có ads attribution** | Warehouse có spend nhưng không có click→order path; không đo được ROI quảng cáo thật |

---

## 3. Goals & Non-goals

### Goals (v1)

| # | Mục tiêu | Đo lường |
|---|---|---|
| G1 | Cung cấp golden record thống nhất (1 người = 1 party) qua dedup SĐT + FTS5 tên | % party có ≥1 identity được link; dedup candidate review rate |
| G2 | Bề mặt insight warehouse (action_queue, RFM, affinity) trực tiếp tại hồ sơ khách | % action_queue được tạo thành task trong CRM |
| G3 | Ghi lại lịch sử tương tác đầy đủ (call log, note, chat, task) gắn với party | # hoạt động/tuần/NV |
| G4 | Tạo segment + chiến dịch reactivation có thể đo ROI (converted_order_code) | Tỷ lệ chuyển đổi chiến dịch; revenue attributed |
| G5 | Ingest Messenger chat v1 + gắn khách + gán NV xử lý | Inbox resolution rate |
| G6 | Theo dõi ads spend + lead + attribution last-touch mà warehouse không có | # lead attributed / ad campaign |

### Non-goals (v1)

- **Không thay thế Sapo** — CRM không ghi đơn, không tính tồn kho, không xử lý thanh toán
- **Không tính lại analytics** — warehouse vẫn là nguồn sự thật cho mọi tính toán (RFM, margin, affinity); CRM chỉ đọc
- **Không có auth/login v1** — tin-cậy-LAN (như `detailView`); RBAC để sau
- **Sapo write-back hoãn** — Phase 07 gated bởi API spike; không chặn v1
- **Shopee/Zalo chat hoãn** — v1 chỉ Messenger; schema tổng quát để thêm adapter sau
- **Enrichment → warehouse hoãn** — luồng ngược (CRM data → re-analysis) để sau (Backlog)
- **Full order line-item** — chỉ order header slim trong cache; full giỏ hàng on-demand nếu cần sau

---

## 4. Personas

### P1 — Sales Rep (Nhân viên kinh doanh)
**Số lượng:** ~5–7 người  
**Trách nhiệm:** Gọi điện tư vấn, bán lại cho khách cũ, chăm sóc khách VIP/GOLD  
**Cần từ CRM:**
- Worklist buổi sáng: "hôm nay tôi cần gọi cho ai, tại sao, và giá trị tiềm năng là bao nhiêu"
- Hồ sơ 360 khách: lịch sử mua, insight RFM, affinity SKU, ghi chú cũ trước khi gọi
- Ghi lại kết quả cuộc gọi (outcome note) và tạo follow-up task
- Xem hội thoại Messenger liên quan tới khách

**Màn hình chính:** Worklist screen, Customer 360 screen, Activity/Call Log

---

### P2 — Customer Care Agent (CSKH)
**Số lượng:** ~2–3 người  
**Trách nhiệm:** Xử lý inbox chat, resolve khiếu nại, link hội thoại với khách  
**Cần từ CRM:**
- Inbox Messenger với hội thoại chưa xử lý; gán NV
- Tra cứu nhanh khách theo SĐT/tên khi chat đến
- Hợp nhất psid → party; xử lý khách chưa có hồ sơ
- Ghi note sau xử lý; đóng hội thoại

**Màn hình chính:** Inbox screen, Customer Search/Dedup Review, Conversation Detail

---

### P3 — Manager / Admin
**Số lượng:** ~1–2 người  
**Trách nhiệm:** Tạo chiến dịch, phân tích hiệu quả, quản lý dữ liệu  
**Cần từ CRM:**
- Tạo/quản lý segment động theo signal warehouse
- Tạo chiến dịch reactivation + gán NV thực hiện
- Theo dõi ROI chiến dịch (converted_revenue vs cost)
- Duyệt dedup candidate; merge/từ chối
- Quản lý custom field def + tag category

**Màn hình chính:** Segments screen, Campaigns screen, Dedup Review screen, Ads Tracking screen

---

## 5. Key User Journeys

### J1 — Buổi sáng: Worklist → Gọi điện bán lại

> Sales Rep A mở CRM lúc 8h. Worklist hiển thị 12 khách ưu tiên hôm nay — lấy từ `wh_action_queue` (CALL_NOW, REORDER_NUDGE, WIN_BACK). Mỗi dòng có tên, SĐT, lý do (rationale_vi), và giá trị tiềm năng (`value_at_stake_vnd`). Rep A nhấn vào khách đầu tiên → Customer 360 screen: thấy lịch sử mua 18 tháng, sản phẩm yêu thích, lần mua gần nhất, ghi chú cũ. Rep A gọi điện → ghi log activity (outcome: "sẽ mua tuần sau") → tạo follow-up task due 7 ngày. Task xuất hiện trong worklist ngày đó.

**Liên quan:** M3 (action_queue), M4 (task/activity), M1 (party lookup), M2 (customer 360)

---

### J2 — Win-back khách at-risk / churned

> Manager tạo chiến dịch "Win-back Q3" cho segment "GOLD + churned >90 ngày". Segment rule tự động lấy từ `wh_customer_insight.value_group='GOLD'` AND `customer_status='churned'`. CRM materialize 87 party. Manager gán cho 2 Sales Rep. Mỗi Rep thấy danh sách khách được giao → gọi lần lượt → ghi outcome. Khi khách đặt đơn (order_code mới trên warehouse > ngày touch), CRM match → set `converted_order_code`, tính `converted_revenue_vnd`.

**Liên quan:** M6 (segment + campaign + conversion tracker), M3 (insight), M4 (task)

---

### J3 — Xử lý chat Messenger inbound + link khách

> CSKH B mở Inbox: hội thoại mới từ PSID `PSID_abc`. Hệ thống đã upsert vào `crm_conversation` nhưng `party_id` null (PSID chưa khớp). CSKH B đọc tin nhắn → khách hỏi về đơn hàng → CSKH tra SĐT khách nhắn → search party → tìm thấy → link psid vào `crm_party_identity`. Hồ sơ khách gắn vào conversation. CSKH ghi note + đóng hội thoại.

**Liên quan:** M5 (inbox, psid resolve), M1 (party search/identity), M2 (customer 360)

---

### J4 — Làm giàu hồ sơ + dedup merge

> Manager C thấy trong Dedup Review screen có 2 party cùng SĐT: `Nguyen Van A` (Sapo ID 1234) và `NVA` (Sapo ID 5678 — nhập bằng tay). Match rule = `exact_phone`. Manager kiểm tra → xác nhận cùng người → bấm Merge: CRM chuyển tất cả identity về surviving party, set party bị gộp `is_merged=true`, ghi `party_merge_log.snapshot` để undo. Manager sau đó thêm custom field "Da nhạy cảm" = true, gán tag "VIP-repeat", điền địa chỉ đã chuẩn hóa.

**Liên quan:** M1 (dedup + merge), M2 (enrichment + custom field + tag)

---

### J5 — Tạo segment + chiến dịch + đo conversion

> Manager tạo segment động "Reactivation tháng 7": rule `{customer_status: 'at_risk', value_group: ['VIP','GOLD'], next_purchase_signal: 'OVERDUE'}`. Segment materialize 34 party (loại trừ `consent_contact=false`). Manager tạo campaign "React-Jul-2026" gắn segment này, channel=messenger, gán Sales Rep D. Rep D thấy 34 target trong campaign → liên hệ lần lượt → ghi converted_order_code khi thành công. Sau 30 ngày: dashboard hiển thị conversion rate + revenue.

**Liên quan:** M6 (segment + campaign), M3 (insight signal), M4 (task/activity)

---

### J6 — Ads → Lead → Attribution

> FB Ads chạy campaign "Summer-2026". Python ingest job đọc FB Ads API → ghi spend/ngày vào `crm_ad_spend`. Khi khách click quảng cáo và nhắn Messenger, PSID + `ad_ref` (messenger ad-referral) → ghi `crm_ad_lead`. Sau khi CSKH resolve psid → party + khách đặt đơn (order_code) → ghi `crm_ad_attribution` model=`last_touch`. Report: CPC, CPL, và revenue/đơn quy cho quảng cáo.

**Liên quan:** M6 (ad_campaign, ad_spend, ad_lead, ad_attribution), M1 (party resolve), M5 (chat ingest)

---

## 6. Phạm vi (Scope)

### v1 IN — 6 module

| Module | Mô tả ngắn |
|---|---|
| M1 Identity & Golden Record | Dedup, merge, party identity |
| M2 Customer 360 | Enrichment, custom field, tag, note, owner |
| M3 Insight Surfacing | Đọc insight từ cache.db; action_queue; relational (order/product) |
| M4 Activity & Tasks | Timeline, follow-up task, auto-generate từ action_queue |
| M5 Conversation / Chat | Messenger v1 inbox, ingest, psid→party resolve, assign |
| M6 Segments, Campaigns & Ads | Segment dynamic, reactivation campaign, ads tracking + attribution |

### DEFERRED — sau v1

| Hạng mục | Lý do hoãn |
|---|---|
| Sapo write-back (Phase 07) | Cần API spike xác nhận field writable; không chặn v1 |
| Shopee Chat / Zalo OA | Schema tổng quát rồi; chỉ cần thêm adapter; cần API creds |
| Enrichment → warehouse pipeline | Ngược chiều; cần design riêng (Backlog) |
| Auth / login / RBAC enforce | LAN-trust v1 như `detailView`; `app_user.role` để sẵn |
| Order line-item detail trong cache | Full `fact_sales` lớn; v1 dùng order header slim |
| AR/debt real-time | `fact_payments` empty; cần MISA integration |

### OUT — không nằm trong scope

| Hạng mục |
|---|
| Ghi đơn / chỉnh đơn Sapo |
| Tính lại analytics / re-derive RFM |
| Inventory management |
| Multi-tenant / multi-branch phân quyền phức tạp |

---

## 7. Functional Requirements — Theo Module

### M1 — Identity & Golden Record

**Mục đích:** Gộp nhiều danh tính (Sapo ID, SĐT, email, FB PSID) về 1 `crm_party` duy nhất — lớp dedup mà warehouse không có.

**Bảng owned:** `crm_party`, `crm_party_identity`, `crm_dedup_candidate`, `crm_party_merge_log`  
**Đọc từ:** `cache.wh_customer_base` (seed), `cache.wh_party_seed`  
**Màn hình:** Party Search, Dedup Review screen

| ID | Acceptance Criteria |
|---|---|
| FR-M1-1 | - [ ] Mỗi `crm_party_identity` có `UNIQUE(identity_type, identity_value)` — 1 SĐT chuẩn hóa chỉ thuộc 1 party |
| FR-M1-2 | - [ ] SĐT VN chuẩn hóa về E.164 (`+84xxx`) trước khi insert — `0xxx` và `+84xxx` match về cùng 1 identity_value |
| FR-M1-3 | - [ ] Party tạo tự động từ `wh_party_seed` khi Go app xử lý seed mới từ cache |
| FR-M1-4 | - [ ] Exact SĐT match → tự động link identity (không tạo duplicate party); FTS5 tên + cùng prefix SĐT → tạo `dedup_candidate` status=pending |
| FR-M1-5 | - [ ] UI Dedup Review hiển thị candidate pending; NV merge/reject từng cặp |
| FR-M1-6 | - [ ] Merge transaction: tất cả identity/activity/task/conversation của party B chuyển sang A; B set `is_merged=true`, `merged_into=A`; ghi `party_merge_log` với JSON snapshot để undo |
| FR-M1-7 | - [ ] Undo merge: khôi phục từ snapshot trong `party_merge_log` — đảo ngược toàn bộ reassign |
| FR-M1-8 | - [ ] Search party theo SĐT, tên (FTS5), email, customer_code trả kết quả < 200ms |

---

### M2 — Customer 360

**Mục đích:** Lớp làm giàu thông tin khách mà Sapo không có — profile mở rộng, custom field tuỳ biến, tag, note, gán phụ trách, consent.

**Bảng owned:** `crm_customer_profile`, `crm_custom_field_def`, `crm_tag`, `crm_party_tag`, `crm_note`  
**Đọc từ:** `cache.wh_customer_insight` (insight), `cache.wh_order_hdr` (đơn), `cache.wh_customer_base` (base attrs)  
**View:** `crm_party_360` = join party + profile + insight + tags + latest action  
**Màn hình:** Customer 360 screen

| ID | Acceptance Criteria |
|---|---|
| FR-M2-1 | - [ ] Mỗi party có 0..1 `crm_customer_profile`; profile tạo on-demand khi NV mở hồ sơ lần đầu |
| FR-M2-2 | - [ ] Custom field def registry (text/number/date/bool/select/multiselect); thêm field mới **không cần migration** |
| FR-M2-3 | - [ ] App validate `custom` JSON theo registry trước khi save (data_type, required, options) |
| FR-M2-4 | - [ ] Tag có category; gán/bỏ tag atomically; party_360 trả tags-agg trong 1 query |
| FR-M2-5 | - [ ] `consent_contact=0` bị loại tự động khỏi campaign target (enforce tại M6) |
| FR-M2-6 | - [ ] Owner assignment (`owner_user_id`) để lọc worklist theo NV |
| FR-M2-7 | - [ ] Customer 360 screen hiển thị: thông tin cơ bản + enrichment + insight từ cache + 10 đơn gần nhất + tags + ghi chú + task mở + activity timeline; `refreshed_at` insight hiển thị rõ |
| FR-M2-8 | - [ ] View `crm_party_360` trả đủ dữ liệu cho màn hình trong ≤ 200ms (point-lookup) |

---

### M3 — Insight & Relational Surfacing

**Mục đích:** Đọc và bề mặt hóa insight đã tính từ warehouse — CRM **không tính lại**, chỉ hiển thị. Bao gồm cả dữ liệu quan hệ gốc (đơn hàng, sản phẩm).

**Đọc từ cache.db (read-only):**
- **Nhóm insight:** `wh_customer_insight` (value_group, customer_status, RFM, affinity, next_purchase_signal, discount_sensitivity, lifetime_contribution_margin), `wh_action_queue` (6 action_type + value_at_stake_vnd + rationale_vi), `wh_product_insight` (health_class, oos_risk, realized_margin_pct)
- **Nhóm quan hệ gốc:** `wh_order_hdr` (lịch sử đơn hàng khách), `wh_customer_base` (base attrs Sapo), `wh_product` (catalog SKU)

**Convention bắt buộc khi đọc:**
- `realized_margin_pct` (KHÔNG `gross_margin_pct` — bug H010)
- `net_revenue` (VAT-inclusive); `date_key` ICT
- Gate margin với `has_cogs=true`
- `customer_type` B2B không đáng tin cho lịch sử trước 2026; `fact_payments` không dùng

| ID | Acceptance Criteria |
|---|---|
| FR-M3-1 | - [ ] Customer 360 hiển thị `value_group`, `customer_status`, `next_purchase_signal`, `top_affinity_product`, `discount_sensitivity` từ `wh_customer_insight` |
| FR-M3-2 | - [ ] Action queue của khách hiển thị action_type + rationale_vi + value_at_stake_vnd; `refreshed_at` hiển thị kèm |
| FR-M3-3 | - [ ] Lịch sử đơn: 10 đơn gần nhất từ `wh_order_hdr` join qua `customer_id`; show order_code, date_key (ICT), net_revenue, status |
| FR-M3-4 | - [ ] Product catalog lookup từ `wh_product` (khi tạo segment theo SKU affinity hoặc chọn SP upsell) |
| FR-M3-5 | - [ ] Product insight (`wh_product_insight`) hiển thị health_class + oos_risk khi NV xem gợi ý upsell |
| FR-M3-6 | - [ ] CRM **không hiển thị** `gross_margin_pct`; chỉ dùng `realized_margin_pct` (gate `has_cogs`) |
| FR-M3-7 | - [ ] `refreshed_at` của từng bảng cache hiển thị rõ trong UI (NV biết data mới hay cũ) |

---

### M4 — Activity & Tasks

**Mục đích:** Nhật ký tương tác + giao việc follow-up. Task có thể sinh tự động từ `wh_action_queue` hoặc tạo thủ công/từ campaign.

**Bảng owned:** `crm_activity`, `crm_task`  
**Màn hình:** Worklist screen (tasks by assignee), Customer 360 timeline, Task Detail

| ID | Acceptance Criteria |
|---|---|
| FR-M4-1 | - [ ] Activity types: call/note/visit/email/chat/other; gắn `party_id` + `staff_user_id` + `occurred_at`; tùy chọn `related_order_code` (soft ref) |
| FR-M4-2 | - [ ] Task có title, due_at, priority, assignee, status (open/doing/done/cancelled) |
| FR-M4-3 | - [ ] Task generator idempotent: mỗi `action_id` từ `wh_action_queue` → tối đa 1 task (`source='action_queue'`, `source_ref=action_id`); chạy lại không tạo duplicate |
| FR-M4-4 | - [ ] Worklist screen: NV thấy task open/doing được giao cho mình, sắp xếp theo due_at + priority; filter theo party/assignee |
| FR-M4-5 | - [ ] Timeline khách: tất cả activity (call log, note, chat event) + task completed gắn party, sort `occurred_at` DESC |
| FR-M4-6 | - [ ] Hoàn thành task: set `status=done`, `completed_at`; task từ campaign → trigger check conversion |

---

### M5 — Conversation / Chat (Messenger v1)

**Mục đích:** Ingest Messenger chat (v1); resolve psid → party; gán NV xử lý. Warehouse chat là disabled stubs — CRM tự ingest.

**Bảng owned:** `crm_conversation`, `crm_message`  
**Ingest:** Python `sync/ingest_messenger.py` đọc FB Graph API → upsert idempotent  
**Màn hình:** Inbox screen, Conversation Detail

| ID | Acceptance Criteria |
|---|---|
| FR-M5-1 | - [ ] Conversation ingest idempotent theo `UNIQUE(channel, external_thread_id)`; message idempotent theo `UNIQUE(conversation_id, external_message_id)` |
| FR-M5-2 | - [ ] PSID khớp `crm_party_identity(identity_type='psid')` → `party_id` gắn tự động vào conversation |
| FR-M5-3 | - [ ] PSID không khớp → `party_id=null`; UI gợi ý link thủ công (search party theo SĐT từ nội dung chat); NV confirm → thêm identity |
| FR-M5-4 | - [ ] Inbox screen: list conversation theo assignee/status; badge unread_count; filter open/pending/closed |
| FR-M5-5 | - [ ] Gán NV xử lý (assignee_user_id) cho conversation; reassign được |
| FR-M5-6 | - [ ] Conversation detail: hiển thị messages (direction in/out, sent_at ICT); bên cạnh hoặc drawer: Customer 360 tóm tắt nếu party đã link |
| FR-M5-7 | - [ ] Đóng conversation: set `status=closed`; tạo activity `type=chat` gắn party (nếu resolved) |

---

### M6 — Segments, Reactivation Campaigns & Ads

**Mục đích:** Biến insight thành hành động bán lại theo tệp. Đo ROI thật (converted_order_code). Theo dõi ads + attribution mà warehouse không có.

**Bảng owned:** `crm_segment`, `crm_segment_member`, `crm_campaign`, `crm_campaign_target`, `crm_ad_campaign`, `crm_ad_spend`, `crm_ad_lead`, `crm_ad_attribution`  
**Đọc từ:** `cache.wh_customer_insight`, `cache.wh_order_hdr` (check conversion)  
**Màn hình:** Segments screen, Campaigns screen, Campaign Target list, Ads Tracking screen

| ID | Acceptance Criteria |
|---|---|
| FR-M6-1 | - [ ] Segment động: rule JSON (value_group, customer_status, next_purchase_signal, affinity, tag, v.v.) → evaluate trên `crm_party` JOIN `cache.wh_customer_insight` → upsert `crm_segment_member` |
| FR-M6-2 | - [ ] Segment member tự động **loại khỏi** nếu `consent_contact=0` (compliance) |
| FR-M6-3 | - [ ] Segment tĩnh: add/remove party thủ công (`source='manual'`) |
| FR-M6-4 | - [ ] Campaign: objective (reactivation/winback/upsell/crosssell), channel, gắn segment → sinh `campaign_target` cho mỗi party trong segment |
| FR-M6-5 | - [ ] Campaign target: status lifecycle `queued → sent → responded → converted/skipped`; assign NV thực hiện |
| FR-M6-6 | - [ ] Conversion tracker: khách trong campaign đặt đơn (order_code mới trong `wh_order_hdr` sau `campaign.scheduled_at`) → set `converted_order_code`, `converted_revenue_vnd`, `converted_at`; tính conversion rate |
| FR-M6-7 | - [ ] Ads: ghi `crm_ad_campaign` + `crm_ad_spend` (Python FB Ads API ingest); `crm_ad_lead` từ messenger ad-referral + resolve party |
| FR-M6-8 | - [ ] Attribution: `crm_ad_attribution` model=`last_touch`; `order_code` quy cho ad campaign gần nhất trước đơn; idempotent |

---

## 8. Data & Integration Requirements

### 8.1 Mô hình 2-file SQLite

| File | Writer | Reader | Prefix bảng |
|---|---|---|---|
| `crm.db` | Go app (duy nhất) | Go app | `crm_*` |
| `cache.db` | Python reverse-ETL (duy nhất) | Go app (ATTACH RO) | `wh_*` |

Không dùng FK qua ATTACH boundary — link bằng value `customer_id`. FK trong cùng file: bật `PRAGMA foreign_keys=ON` mỗi connection.

### 8.2 3 bucket dữ liệu

| Bucket | Ví dụ | Nguồn sự thật | CRM ghi? |
|---|---|---|---|
| **CRM tự tạo** | party, profile, tag, note, task, activity, conversation, segment, campaign, ads | CRM | ✅ |
| **Insight đã tính** | RFM, affinity, next_purchase, action_queue, product_health | warehouse | ❌ |
| **Quan hệ gốc** | order_hdr, customer_base, product catalog | Sapo→warehouse | ❌ |

### 8.3 Reverse-ETL (Python → cache.db)

```
olap.duckdb (read_only=True, main_marts.*)
  → wh_customer_insight  (từ dim_customers + int_customer_metrics)
  → wh_action_queue      (từ mart_customer_action_queue)
  → wh_product_insight   (từ mart_product_health)
  → wh_customer_base     (từ dim_customers base attrs)
  → wh_product           (từ dim_products catalog)
  → wh_order_hdr         (từ fact_orders, slim 1 dòng/đơn, incremental theo date_key)
  → wh_party_seed        (customer_id mới → Go tạo crm_party)
  → wh_sync_run          (log rows, status, started_at, finished_at)
```

- Idempotent upsert (`INSERT ... ON CONFLICT DO UPDATE`)
- `order_hdr` incremental theo `date_key` — không full-reload
- Python **không đụng** `crm.db` (tránh 2 writer)
- Go đọc `wh_party_seed` → tạo `crm_party/crm_party_identity` (giữ 1 writer)

### 8.4 Convention bắt buộc (warehouse)

| Convention | Rule |
|---|---|
| Timestamp | Store UTC ISO-8601 'Z' (TEXT SQLite); display ICT `Asia/Ho_Chi_Minh` ở app |
| date_key | ICT YYYYMMDD — dùng cho date range filter, không dùng UTC |
| Tiền VND | INTEGER (không có thập phân) |
| Revenue | `net_revenue` (VAT-exclusive theo warehouse); `total_collected` (VAT-inclusive) |
| Margin | Chỉ `realized_margin_pct`, gate `has_cogs=true`; KHÔNG `gross_margin_pct` |
| customer_type | B2B không đáng tin lịch sử; `fact_payments` empty → không dùng |
| Link qua file | value-link `customer_id`; không FK qua ATTACH |

---

## 9. Non-functional Requirements

| NFR | Target |
|---|---|
| **Người dùng đồng thời** | ~10; write concurrency thấp → SQLite WAL đủ |
| **Deploy** | Single Go binary + Python venv; không cần container DB; `make build` → 1 binary chạy ngay |
| **Môi trường** | Local/LAN; Windows-native hoặc Docker Desktop (Linux container on Windows host) |
| **Performance** | Point-lookup Customer 360 (party + insight + 10 đơn) ≤ 200ms; Worklist query ≤ 300ms |
| **Security** | LAN-trust v1 (như `detailView`); `crm_app_user.role` (sales/care/manager/admin) reserved cho RBAC sau; secrets qua `.env` (gitignore); file `crm.db`/`cache.db` trên local disk (KHÔNG network share) |
| **Timezone** | Store UTC ISO-8601; display ICT mọi nơi trong UI |
| **Tiền tệ** | VND INTEGER; không dùng REAL cho tiền |
| **Freshness** | `refreshed_at` hiển thị rõ tại mọi bề mặt insight; NV biết data mới nhất lúc nào |
| **Backup** | `crm.db` backup định kỳ; `cache.db` rebuildable hoàn toàn từ warehouse → không cần backup |
| **PRAGMA bắt buộc** | Mỗi connection: `journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`, `synchronous=NORMAL` |
| **Ngôn ngữ UI** | Tiếng Việt |
| **Kiến trúc** | Hexagonal (domain ⟂ ports ⟂ adapters); domain/ports không import sqlite/http/sapo |

---

## 10. Success Metrics / KPIs

| Metric | Mục tiêu tháng đầu | Cách đo |
|---|---|---|
| **Reactivation conversion rate** | ≥ 15% campaign_target chuyển sang `converted` | `converted / total_targets` per campaign |
| **Action-queue task actioned/tuần** | ≥ 60% action_queue tasks có activity ghi nhận trong 3 ngày | `tasks với activity linked / tasks generated` |
| **Golden record dedup coverage** | ≥ 80% party có ≥1 sapo_customer identity linked | `parties with identity / total parties` |
| **Customer 360 load time** | p95 ≤ 200ms | App instrumentation |
| **Staff adoption** | ≥ 7/10 user active (ghi activity) trong tuần đầu | `COUNT(DISTINCT staff_user_id)` trong `crm_activity` |
| **Inbox resolved** | ≥ 70% conversation closed trong 24h | `closed_conversations / opened` by date |
| **Dedup candidate review** | Backlog < 50 pending candidates bất kỳ lúc nào | `COUNT(*) FROM crm_dedup_candidate WHERE status='pending'` |

---

## 11. Constraints & Assumptions

- **Warehouse đã ổn định:** `olap.duckdb` + `main_marts.*` chạy ổn định, daily refresh 07:00 ICT; CRM reverse-ETL chạy sau đó
- **~10 user, write ít:** Không cần Postgres; SQLite WAL đủ; nếu scale lên > 50 user thì re-evaluate
- **LAN-trust v1:** Không có auth; toàn bộ nhân viên trong LAN đều truy cập được; acceptable cho nội bộ
- **Messenger v1 chỉ đọc (ingest + hiển thị):** Gửi tin nhắn 2 chiều từ CRM để Phase 2
- **Sapo API tồn tại:** Xác nhận có API order + customer; field writable cần spike (Phase 07)
- **Python + Go trên cùng máy:** Không cần network call giữa 2 process; file SQLite trên local disk
- **Warehouse không có chat/ads data:** Tất cả `fb_messenger` và `fb_ads` models là `enabled=false`; CRM tự ingest hoàn toàn

---

## 12. Risks & Mitigations

| Rủi ro | Mức | Mitigation |
|---|---|---|
| **Sapo write-back không khả thi** — field không ghi được, rate-limit, conflict | Cao | Phase 07 mở đầu bằng API spike; fallback = enrichment ở lại CRM, không chặn v1 |
| **Chat self-ingest lớn hơn dự kiến** — FB Graph API quota, message volume, webhook setup | Trung bình | v1 chỉ ingest (read + display), không gửi; batch pull thay realtime webhook nếu cần |
| **Dedup fuzzy gộp nhầm** — FTS5 + tên VN dễ nhầm | Cao | Chỉ exact SĐT auto-link; fuzzy → `dedup_candidate` chờ review thủ công; mọi merge có snapshot undo |
| **Warehouse data caveats** — `customer_type` B2B unreliable, `fact_payments` empty, H010 bug | Trung bình | Gate margin `has_cogs`; dùng `realized_margin_pct`; không dùng `fact_payments`; document trong UI (tooltip) |
| **Freshness lag** — action_queue daily, order_hdr near-realtime | Thấp | Hiển thị `refreshed_at` rõ; NV biết data không realtime |
| **DuckDB write lock** — reverse-ETL cần `olap.duckdb` | Thấp | Luôn `read_only=True`; fallback `sapo_export_latest.duckdb` nếu file bận |
| **Shopee/Zalo API creds** — chưa có khi build | Thấp (v1) | Schema tổng quát rồi; chỉ cần adapter mới; không block v1 Messenger |

---

## 13. Release Phasing

| Phase | Module | Output chính | Outcome cho team |
|---|---|---|---|
| **01** — Foundation | — | crm.db (WAL) + cache.db (ATTACH RO), Go binary `/healthz`, `crm_app_user`, Makefile | Nền sẵn sàng; deploy 1 binary được |
| **02** — Identity | M1 | `crm_party`, `crm_party_identity`, `crm_dedup_candidate`, `crm_party_merge_log`; chuẩn hóa SĐT; Dedup Review screen | Golden record + dedup workflow |
| **03** — Customer 360 | M2 | `crm_customer_profile`, `crm_custom_field_def`, `crm_tag`, `crm_note`; view `crm_party_360`; Customer 360 screen | Nhân viên làm giàu hồ sơ được |
| **04** — Reverse-ETL | M3 | `cache.db` schema + Python sync (insight + order/customer/product); `wh_party_seed` → party | Insight warehouse xuất hiện trong CRM |
| **05** — Activity & Chat | M4 + M5 | `crm_activity`, `crm_task`; Worklist screen; `crm_conversation`, `crm_message`; Messenger ingest; Inbox screen | Nhân viên có worklist + log call + inbox |
| **06** — Growth | M6 | `crm_segment`, `crm_campaign`, `crm_campaign_target`, ads tables; Segments/Campaigns/Ads screens | Chiến dịch reactivation + đo ROI |
| **07** *(deferred)* | Sapo write-back | `crm_sync_outbox`, `crm_sapo_writeback_map`; Sapo API adapter | Enrichment đẩy ngược Sapo (gated bởi spike) |

---

## 14. Open Questions

| # | Câu hỏi | Ảnh hưởng |
|---|---|---|
| OQ-1 | **Sapo writable fields** — field nào trên `PUT /admin/customers/{id}.json` nhận write (tags, notes, customer_group)? Cần spike trước Phase 07 | Scope Phase 07 |
| OQ-2 | **Shopee Chat API creds** — Shopee Chat API endpoint + credential format; Zalo OA creds tương tự | Unblocks Phase 05 expansion |
| OQ-3 | **Enrichment → warehouse pipeline** — Khi CRM có golden record + custom tags, có feed ngược vào warehouse để re-analysis không? Design ingestion pipeline mới ra sao? | Backlog scoping |
| OQ-4 | **Party count estimate** — ước lượng tổng số khách (Sapo customer_id unique)? SQLite + FTS5 ổn ở mọi mức nhưng ảnh hưởng batch size reverse-ETL | Performance tuning |
| OQ-5 | **Loyalty points freshness** — CRM có cần loyalty balance realtime (từ Sapo API direct) hay daily cache từ warehouse đủ? | Nếu realtime: cần Go adapter gọi Sapo API trực tiếp |
| OQ-6 | **FB Graph API mode** — Ingest Messenger qua webhook (realtime) hay polling (batch)? Webhook cần public endpoint (LAN có thể không expose được) | Phase 05 architecture |
