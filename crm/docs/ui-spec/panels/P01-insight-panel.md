---
id: P01
type: panel
name: "Insight Panel"
platforms: [desktop]
hosts: [S03]
status: active
design_ref: ""
rules: [R2, R7]
regions: [action_queue, rfm_block, signals_block, rep_insights_block, freshness_bar]
---

# P01 — Insight Panel

## Purpose

Panel tab "Insight" trong Customer 360 (S03). Hiển thị hai lớp insight song song:
1. **Warehouse insights** (machine-generated): RFM, affinity, action_queue, signals — đọc từ `cache.wh_customer_insight` và `cache.wh_action_queue`. CRM không tính lại.
2. **Rep insights** (human-curated): các nhận định rep đã đúc kết từ `crm_party_insight` — persona, buying pattern, decision style, v.v.

`refreshed_at` hiển thị rõ tại freshness_bar (chỉ áp dụng cho warehouse layer).

## Layout

```
┌ ACTION QUEUE ─────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │ CALL_NOW  "Sắp hết hàng yêu thích — gọi ngay"  💰 2.400.000đ  │   │
│ │           [Đã xử lý ✓] hoặc [→ Tạo task]                      │   │
│ │ REORDER_NUDGE  "Chu kỳ mua ~30 ngày, đã 28 ngày"  💰 900.000đ │   │
│ └─────────────────────────────────────────────────────────────────┘   │
├ RFM BLOCK ────────────────────────────────────────────────────────────┤
│  Nhóm: GOLD  |  Recency: 28 ngày  |  Freq: 8 đơn  |  LTV: 18.400.000 │
├ SIGNALS ──────────────────────────────────────────────────────────────┤
│  Status: active  |  Next purchase: IMMINENT  |  Affinity: Sữa rửa mặt │
│  Discount sensitivity: LOW  |  Margin: 34.2% (has_cogs ✓)            │
├ REP INSIGHTS ──────────────────────────── 👤 Minh (3 insights) [+ Thêm]┤
│  [Persona]       Mua cho shop Q7 — cần báo giá sỉ         [cao] ✓    │
│  [Quyết định]    Hay do dự, cần follow up ≥3 lần          [tb]  ✓    │
│  [Mùa vụ]        Mua mạnh T10–T12                         [cao] ✓    │
├ FRESHNESS ─────────────────────────────────────────────────────────────┤
│  Cache insight: 07:15 ICT hôm nay ✓                                  │
└────────────────────────────────────────────────────────────────────────┘
```

## Action Queue Item States

- Nếu `crm_task.action_queue_id = item.action_id` và `task.outcome IS NOT NULL` → badge "Đã xử lý ✓" + outcome label
- Nếu chưa có task → button "→ Tạo task" (prefill từ action item)

## Rep Insights Block

- Đọc từ `crm_party_insight` WHERE `party_id = $party.id` AND `is_active = true`
- Mỗi insight row: [insight_type badge] body text [confidence badge] [✎ Sửa] [✗ Invalidate]
- [+ Thêm] → M16 (Promote/Create Insight)
- Nếu không có insight nào → placeholder "Rep chưa có nhận định — thêm insight sau khi liên lạc"
- `contact_pref` notes (`crm_note.note_type='contact_pref'`) cũng hiển thị ở đây nếu pinned

## States

- ST-360-NO-INSIGHT: Không có row trong `wh_customer_insight` cho customer_id này
- ST-STALE-CACHE: refreshed_at > 24h → yellow freshness_bar
- ST-LOADING: Insight fetch in-flight

## Interactions

```yaml crm-contract
interactions:
  - id: A-P01-001
    element: action_queue_item
    region: action_queue
    trigger: click
    action: open_overlay
    target: M05
    payload: { source: "action_queue", action_id: "$item.action_id", party_id: "$party.id" }
  - id: A-P01-002
    element: affinity_product_link
    region: signals_block
    trigger: click
    action: mutate
    effects: [ui.tooltip.show_product_insight]
  - id: A-P01-003
    element: btn_add_insight
    region: rep_insights_block
    trigger: click
    action: open_overlay
    target: M16
    payload: { party_id: "$party.id" }
  - id: A-P01-004
    element: insight_edit_btn
    region: rep_insights_block
    trigger: click
    action: open_overlay
    target: M16
    payload: { party_id: "$party.id", insight_id: "$insight.id" }
  - id: A-P01-005
    element: insight_invalidate_btn
    region: rep_insights_block
    trigger: click
    action: mutate
    effects: [insight.is_active.set_false, rep_insights_block.reload]
  - id: A-P01-LSN01
    listens_to: cache.refreshed
    action: mutate
    effects: [insight.reload, freshness_bar.update]
  - id: A-P01-LSN02
    listens_to: freshness_badge.hovered
    action: mutate
    effects: [ui.tooltip.show_refresh_details]
```
