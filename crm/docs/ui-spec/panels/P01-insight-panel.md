---
id: P01
type: panel
name: "Value & Behavior Panel"
platforms: [desktop]
hosts: [S03]
status: active
design_ref: ""
rules: [R2, R7]
regions: [action_queue, rfm_segments_block, value_metrics_block, signals_block, rep_insights_block, freshness_bar]
---

# P01 — Value & Behavior Panel

## Purpose

Panel tab "Value & Behavior" trong Customer 360 (S03). Hiển thị hai lớp insight song song:
1. **Warehouse insights** (machine-generated): RFM & Segments, Value Metrics, Signals, action_queue — đọc từ `cache.wh_customer_insight` và `cache.wh_action_queue`. CRM không tính lại.
2. **Rep insights** (human-curated): các nhận định rep đã đúc kết từ `crm_party_insight` — persona, buying pattern, decision style, v.v.

`refreshed_at` hiển thị rõ tại freshness_bar (chỉ áp dụng cho warehouse layer).

## Layout

```
┌ ACTION QUEUE ──────────────────────────────────────────────────────────┐
│ CALL_NOW  "Sắp hết hàng yêu thích — gọi ngay"  💰 2.400.000đ         │
│           [Đã xử lý ✓] hoặc [→ Tạo task]                             │
├ RFM & SEGMENTS ────────────────────────────────────────────────────────┤
│  R: Recency 28 ngày  |  F: Frequency 8 đơn  |  M: Monetary 2.350.000đ │
│  [GOLD] [active] [ON_TRACK] [CHANNEL_XYZ] [discount sensitive]        │
├ VALUE METRICS ─────────────────────────────────────────────────────────┤
│  ┌──────────────────────────┬─────────────┬─────────────┐             │
│  │ Lifetime value (hero×2)  │ Total orders│ Avg order   │             │
│  │ 18.400.000 ₫             │ 8           │ 2.300.000 ₫ │             │
│  ├───────────┬──────────────┬─────────────┬─────────────┤             │
│  │ Gross marg│ Cancel rate  │ Avg cycle   │ Channel     │             │
│  │ 34.2%     │ 5%           │ 32d         │ POS         │             │
│  └───────────┴──────────────┴─────────────┴─────────────┘             │
├ SIGNALS ───────────────────────────────────────────────────────────────┤
│  Customer status: active  |  Next purchase: ON_TRACK (2025-07-15)     │
│  Discount sensitivity: LOW  |  Top affinity: Sữa rửa mặt             │
├ REP INSIGHTS ────────────────────────────── 👤 [+ Thêm insight]       │
│  [Persona]    Mua cho shop Q7 — cần báo giá sỉ       [cao]           │
│  [Quyết định] Hay do dự, cần follow up ≥3 lần        [tb]            │
├ FRESHNESS ──────────────────────────────────────────────────────────────┤
│  Cache insight: 07:15 ICT hôm nay  ·  R2 · CRM không tính lại insight │
└────────────────────────────────────────────────────────────────────────┘
```

## Action Queue Item States

- Nếu `crm_task.action_queue_id = item.action_id` và `task.outcome IS NOT NULL` → badge "Đã xử lý ✓" + outcome label
- Nếu chưa có task → button "→ Tạo task" (prefill từ action item)

## RFM & Segments Block

3 cells ngang: **R** (Recency = `avg_days_between_orders`), **F** (Frequency = tổng số đơn `recent_orders.length`), **M** (Monetary = `avg_order_spend`).

Bên dưới RFM grid: flat horizontal segment badges —
- `value_group` (VIP/GOLD/SILVER/BRONZE) — màu tier riêng
- `customer_status` (active/at_risk/churned)
- `next_purchase_signal` (OVERDUE/DUE_SOON/ON_TRACK)
- `channel_preference` (nếu có)
- "discount sensitive" (nếu `discount_sensitivity == HIGH`)
- "high cancel" (nếu `cancel_rate > 0.1`)

## Value Metrics Block

Grid 4 cột, 2 hàng:
- **Hàng 1**: Lifetime value (hero, span 2 cột, `lifetime_contribution_margin`) | Total orders (`recent_orders.length`) | Avg order value (`avg_order_spend`)
- **Hàng 2**: Gross margin (R7: `lifetime_contribution_margin / avg_order_spend * 100`, gated `not is_margin_negative`) | Cancel rate (`cancel_rate %`) | Avg cycle (`avg_days_between_orders d`) | Channel (`channel_preference`)

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
    element: affinity_product_link
    region: signals_block
    trigger: click
    action: mutate
    effects: [ui.tooltip.show_product_insight]
  - id: A-P01-002
    element: btn_add_insight
    region: rep_insights_block
    trigger: click
    action: open_overlay
    target: M16
    payload: { party_id: "$party.id" }
  - id: A-P01-003
    element: insight_edit_btn
    region: rep_insights_block
    trigger: click
    action: open_overlay
    target: M16
    payload: { party_id: "$party.id", insight_id: "$insight.id" }
  - id: A-P01-004
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
  - id: A-P01-LSN03
    listens_to: action_queue.call_mode_requested
    action: navigate
    target: S14
    payload: { party_id: "$event.party_id" }
  - id: A-P01-LSN04
    listens_to: action_queue.task_requested
    action: open_overlay
    target: M05
    payload: { source: "action_queue", action_id: "$event.action_id", party_id: "$event.party_id" }
```
