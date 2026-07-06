---
id: DR
type: screen
name: "Domain Rules"
platforms: [desktop]
hosted_by: []
status: active
rules: []
regions: []
---

# 20 — Domain Rules

Business rules từ PRD áp dụng xuyên suốt nhiều surfaces. Mỗi rule có `surfaces[]` listing —
validator kiểm tra bidirectional với frontmatter `rules:` của từng surface.

---

## R1 — Consent Gating (consent_contact)

`consent_contact` là enum 3 giá trị: `null`/`na` (default — chưa từng thu thập) / `allowed` / `denied`.
Party có `consent_contact='denied'` **phải bị loại** khỏi campaign target và không được gửi liên lạc chủ động.
Party có `consent_contact=null`/`na` không bị hard-block nhưng không được outreach chủ động cho đến khi xác nhận.
Áp dụng tại: segment materialization (server), campaign target creation, và hiển thị cảnh báo trong UI.

## R2 — No-Recompute Insight

CRM **không tính lại** bất kỳ insight nào (RFM, affinity, margin, action_queue).
Chỉ đọc từ `cache.db` (`wh_customer_insight`, `wh_action_queue`, `wh_product_insight`).
`refreshed_at` phải hiển thị rõ tại mọi surface hiển thị insight.

## R3 — Value-Link No-FK

Không có FK qua ranh giới `crm.db ↔ cache.db`.
Link bằng value `customer_id` (TEXT). App tự resolve; không enforce referential integrity cross-file.

## R4 — Merge Reversibility

Mọi merge party đều ghi `party_merge_log` với JSON snapshot đầy đủ trước khi thực hiện.
UI phải cung cấp đường dẫn undo merge từ snapshot.

## R5 — Phone E.164 Normalization

SĐT VN phải chuẩn hóa về E.164 (`+84xxx`) trước khi insert vào `crm_party_identity`.
`0xxx` và `+84xxx` của cùng số → cùng `identity_value`. UNIQUE(identity_type, identity_value).

## R6 — ICT Display Convention

Mọi timestamp lưu UTC ISO-8601 'Z' trong SQLite. UI **luôn hiển thị** theo ICT (Asia/Ho_Chi_Minh).
`date_key` ICT YYYYMMDD dùng cho date range filter, không dùng UTC date.

## R7 — realized_margin_pct Only

UI **không hiển thị** `gross_margin_pct`. Chỉ dùng `realized_margin_pct` với gate `has_cogs=true`.
Lý do: bug H010 làm `gross_margin_pct` sai cho ~5 SKU.

## R8 — Idempotent Task Generation

Mỗi `action_id` từ `wh_action_queue` → tối đa 1 task CRM (`source='action_queue'`, `source_ref=action_id`).
Chạy lại task generator không tạo duplicate.

## R9 — Dedup Fuzzy → Candidate Queue

Chỉ exact SĐT match → auto-link identity (không tạo duplicate party).
Fuzzy match (FTS5 tên + prefix SĐT) → tạo `crm_dedup_candidate` status=pending, chờ NV review thủ công.

## R10 — Segment Dynamic Consent Re-evaluation

Mỗi lần segment materialize, parties với `consent_contact='denied'` bị loại khỏi `crm_segment_member`.
UI hiển thị count bị loại do consent.

## R11 — Conversion Attribution Window

Converted order: `order_code` mới trong `wh_order_hdr` với `date_key >= campaign.scheduled_at` ICT
và party_id match. Ghi `converted_order_code`, `converted_revenue_vnd`, `converted_at`.

## R12 — Messenger Read-Only v1

v1: CRM chỉ ingest + hiển thị Messenger. Không gửi tin nhắn ra. Gửi 2 chiều để Phase 2.

## R13 — Address Source Priority (manual overrides sync)

`crm_party.address_source` quyết định ai được ghi đè địa chỉ:
- `sapo_sync`: địa chỉ lấy từ shipping address đơn hàng Sapo. Sync job ghi đè bình thường.
- `manual`: rep đã xác nhận địa chỉ thực (thường qua điện thoại vì marketplace mask địa chỉ). Sync job **không được ghi đè**.

Khi rep lưu địa chỉ qua M15 → `address_source` tự động set `manual`. Chỉ reset về `sapo_sync` nếu rep xóa địa chỉ manual.

## R14 — AI Approach-Script Gate (recommended=false)

Kịch bản tiếp cận do AI sinh (`cache.wh_approach_script`) có cờ `recommended`. Khi `recommended=false`
(tài khoản nghi B2B gán nhầm RETAIL, dữ liệu margin mâu thuẫn `is_margin_negative=false` nhưng
`avg_order_contribution_margin_pct<0`, hoặc khách chết-sâu kèm margin âm) → surface vào
**WARN state** (Phase 05): banner cảnh báo sticky đỏ + nội dung che mờ (`opacity:0.35`, `pointer-events:none`);
nút "Tôi đã xác minh — vẫn tiếp tục" mở khoá + ghi audit activity `r14_ack` (POST 204, pure JS unlock, không re-render panel).
Hiển thị `reason_if_not_recommended` + CTA tạo task xác minh tài khoản trong banner.

Hard-block CHỈ khi tương lai có `consent='denied'` thật. Hiện tại default=contactable (không có consent data) — R14 warn-with-ack là đủ.

## R15 — Dismiss TTL by (party_id, action_type)

Dismiss action queue item (`PATCH /worklist/actions/{action_id}/dismiss` và các đường dismiss
khác dùng chung `ActionStatePort.dismiss()`) ghi nhớ theo cặp **(party_id, action_type)**,
KHÔNG chỉ theo `action_id` — vì warehouse sinh `action_id` mới mỗi tuần cho cùng một action
ngữ nghĩa (cùng khách + cùng loại việc), dismiss theo `action_id` cũ sẽ mất hiệu lực và việc
tái xuất hiện, làm NV mất niềm tin vào nút dismiss.

Ghi vào `crm_action_dismissal` (PK `party_id, action_type`) với `dismissed_until = dismissed_at + 30 ngày`.
Sau khi hết hạn, action **tự hiện lại bình thường** — không có badge đặc biệt (khác snooze-wake B2).
`SQLiteCacheRepository.list_all_action_queue()` lọc bỏ action có dismissal còn hiệu lực
(`dismissed_until > now`) song song với filter `crm_action_state.status != 'dismissed'` hiện có
(giữ nguyên cho C360 reason rail per-episode, không đổi).

Manager có view đọc-only liệt kê dismissal đang hiệu lực (khách, loại việc, ai bỏ qua, khi nào,
ẩn đến ngày nào) — minh bạch, chống dismiss né việc.

---

```yaml crm-contract
rules:
  - id: R1
    name: Consent Gating
    surfaces: [S09, S10, S11, M07, S14]
  - id: R2
    name: No-Recompute Insight
    surfaces: [S01, S03, P01, P02, S12, S14]
  - id: R3
    name: Value-Link No-FK
    surfaces: [S03, P02, S11]
  - id: R4
    name: Merge Reversibility
    surfaces: [S04, M01]
  - id: R5
    name: Phone E.164 Normalization
    surfaces: [S02, S04, M01, M02]
  - id: R6
    name: ICT Display Convention
    surfaces: [S01, S03, S05, S06, S11, S12, S14, S15]
  - id: R7
    name: realized_margin_pct Only
    surfaces: [P01, S03]
  - id: R8
    name: Idempotent Task Generation
    surfaces: [S01, S07]
  - id: R9
    name: Dedup Fuzzy Candidate Queue
    surfaces: [S04, M01]
  - id: R10
    name: Segment Dynamic Consent Re-evaluation
    surfaces: [S09, S10]
  - id: R11
    name: Conversion Attribution Window
    surfaces: [S11, S07]
  - id: R12
    name: Messenger Read-Only v1
    surfaces: [S05, S06]
  - id: R13
    name: Address Source Priority
    surfaces: [M15, S03]
  - id: R14
    name: AI Approach-Script Gate
    surfaces: [S14]
  - id: R15
    name: Dismiss TTL by (party_id, action_type)
    surfaces: [S01, S07]
```
