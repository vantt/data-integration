---
id: P01
type: panel
name: "Value & Behavior Panel"
platforms: [desktop]
hosted_by: [S03]
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

```yaml ui-layout
areas:
  - [action_queue]
  - [rfm_segments_block]
  - [value_metrics_block]
  - [signals_block]
  - [rep_insights_block]
  - [freshness_bar]
samples:
  action_queue: "[2 việc] ☑ CALL_NOW 💰2.400.000đ · [📞 Gọi ngay] [Hoàn tất (2) ✓]"
  rfm_segments_block: "R: 28 ngày | F: 8 đơn | M: 2.350.000đ · [GOLD] [active] [ON_TRACK]"
  value_metrics_block: "LTV 18.400.000₫ (hero×2) | 8 đơn | 2.300.000₫ · GM 34.2% | Cancel 5% | 32d | POS"
  signals_block: "active · ON_TRACK 2025-07-15 · Discount: LOW · Top affinity: Sữa rửa mặt"
  rep_insights_block: "[Persona] Mua cho shop Q7 — cần báo giá sỉ [cao] · [+ Thêm insight]"
  freshness_bar: "Cache insight: 07:15 ICT hôm nay · R2 · CRM không tính lại insight"
elements:
  "📞 Gọi ngay": A-P01-005
  "Hoàn tất (2) ✓": A-P01-008
  "+ Thêm insight": A-P01-002
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│ACTION_QUEUE                                                                │
│· [2 việc] [x] CALL_NOW ?2.400.000đ · [> Gọi ngay] [Hoàn tất (2) v]         │
├────────────────────────────────────────────────────────────────────────────┤
│RFM_SEGMENTS_BLOCK                                                          │
│· R: 28 ngày | F: 8 đơn | M: 2.350.000đ · [GOLD] [active] [ON_TRACK]        │
├────────────────────────────────────────────────────────────────────────────┤
│VALUE_METRICS_BLOCK                                                         │
│· LTV 18.400.000₫ (hero×2) | 8 đơn | 2.300.000₫ · GM 34.2% | Cancel 5% | 32…│
├────────────────────────────────────────────────────────────────────────────┤
│SIGNALS_BLOCK                                                               │
│· active · ON_TRACK 2025-07-15 · Discount: LOW · Top affinity: Sữa rửa mặt  │
├────────────────────────────────────────────────────────────────────────────┤
│REP_INSIGHTS_BLOCK                                                          │
│· [Persona] Mua cho shop Q7 — cần báo giá sỉ [cao] · [+ Thêm insight]       │
├────────────────────────────────────────────────────────────────────────────┤
│FRESHNESS_BAR                                                               │
│· Cache insight: 07:15 ICT hôm nay · R2 · CRM không tính lại insight        │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## Action Queue Modes

Action queue merges `wh_action_queue` UNION `wh_sku_action_queue` (SKU branch: grain customer × SKU).
Display mode is determined by `unresolved_count` = items where `status != 'dismissed'` AND `action_id not in resolved_action_ids`.

**Mode A — Session Checklist** (`unresolved_count >= 2`):
- Card `aq-session-card` with count pill + hint.
- Each unresolved action = checkbox row, checked by default.
- Resolved actions shown below as muted ✓ rows.
- CTA row: "Gọi ngay" + "Hoàn tất (N) ✓" submit.
- Submit POSTs to `/customers/{party_id}/actions/dismiss-session`; hx-swaps `#aq-section`.

**Mode B — Individual Card** (`unresolved_count == 1` or 0):
- One `aq-card` per non-dismissed action.
- Resolved: "Đã xử lý ✓" badge.
- Unresolved: "Gọi ngay" button + "Đặt Lịch" ghost-link.

**Purchase Context Chips** (both modes, shown when `last_purchase_date` is set — SKU-level actions only):
- `last_purchase_date` chip — date of last SKU purchase.
- `last_order_code` link chip → navigates to `/orders/{code}` (external).
- `last_sku_discount_rate` chip — formatted as `−N%`.

**"Gọi ngay" behavior** (both modes):
JS first tries to click the "Gọi" tab on S03 via DOM query (`[role=tab]` with text "Gọi").
If tab not found (standalone context), falls back to open M08 with `mode=log&hinh_thuc=call`.

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
  - id: A-P01-005
    element: btn_call_now
    region: action_queue
    trigger: click
    guard: "tab_goi.not_found_in_dom"
    action: open_overlay
    target: M08
    payload: { party_id: "$party.id", mode: "log", hinh_thuc: "call" }
  - id: A-P01-006
    element: action_card_order_link
    region: action_queue
    trigger: click
    action: navigate
    target: "external:/orders/$act.last_order_code"
  - id: A-P01-007
    element: btn_schedule_task
    region: action_queue
    trigger: click
    action: open_overlay
    target: M05
    payload: { party_id: "$party.id", source: "action_queue", source_ref: "$act.action_id", prefill_priority: "$act.priority" }
  - id: A-P01-008
    element: session_checklist_form
    region: action_queue
    trigger: submit
    action: mutate
    effects: [checked_actions.dismiss, aq_section.reload]
  - id: A-P01-LSN01
    listens_to: cache.refreshed
    action: mutate
    effects: [insight.reload, freshness_bar.update]
  - id: A-P01-LSN02
    listens_to: freshness_badge.hovered
    action: mutate
    effects: [ui.tooltip.show_refresh_details]
```
