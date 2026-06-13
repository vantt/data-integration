---
id: P01
type: panel
name: "Insight Panel"
platforms: [desktop]
hosts: [S03]
status: active
design_ref: ""
rules: [R2, R7]
regions: [action_queue, rfm_block, signals_block, freshness_bar]
---

# P01 — Insight Panel

## Purpose

Panel tab "Insight" trong Customer 360 (S03). Hiển thị toàn bộ insight đã tính từ warehouse
cho party hiện tại — CRM không tính lại, chỉ đọc từ `cache.wh_customer_insight` và
`cache.wh_action_queue`. `refreshed_at` hiển thị rõ tại freshness_bar.

Các khối: Action Queue (danh sách action_type + rationale_vi + value_at_stake_vnd), RFM block
(value_group, recency_days, frequency, monetary_vnd), Signals block (customer_status,
next_purchase_signal, discount_sensitivity, top_affinity_product), margin chỉ hiện khi has_cogs=true
dùng realized_margin_pct (R7).

## Layout

```
┌ ACTION QUEUE ─────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │ CALL_NOW  "Sắp hết hàng yêu thích — gọi ngay"  💰 2.400.000đ  │   │
│ │ REORDER_NUDGE  "Chu kỳ mua ~30 ngày, đã 28 ngày"  💰 900.000đ │   │
│ └─────────────────────────────────────────────────────────────────┘   │
├ RFM BLOCK ────────────────────────────────────────────────────────────┤
│  Nhóm: GOLD  |  Recency: 28 ngày  |  Freq: 8 đơn  |  LTV: 18.400.000 │
├ SIGNALS ──────────────────────────────────────────────────────────────┤
│  Status: active  |  Next purchase: IMMINENT  |  Affinity: Sữa rửa mặt │
│  Discount sensitivity: LOW  |  Margin: 34.2% (has_cogs ✓)            │
├ FRESHNESS ─────────────────────────────────────────────────────────────┤
│  Cache insight: 07:15 ICT hôm nay ✓                                  │
└────────────────────────────────────────────────────────────────────────┘
```

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
  - id: A-P01-LSN01
    listens_to: cache.refreshed
    action: mutate
    effects: [insight.reload, freshness_bar.update]
  - id: A-P01-LSN02
    listens_to: freshness_badge.hovered
    action: mutate
    effects: [ui.tooltip.show_refresh_details]
