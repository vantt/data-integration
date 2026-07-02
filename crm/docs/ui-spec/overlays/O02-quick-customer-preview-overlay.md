---
id: O02
type: overlay
name: "Quick Customer Preview Overlay"
platforms: [desktop]
hosted_by: [S01, S07]
status: active
design_ref: ""
rules: [R2]
regions: [content, actions]
---

# O02 — Quick Customer Preview Overlay

## Purpose

Popover hiển thị tóm tắt nhanh Customer 360 khi hover/click vào tên khách trong Worklist (S01)
hoặc Tasks Board (S07) — mà không rời khỏi màn hình hiện tại. Hiển thị: tên, SĐT, value_group,
customer_status, top_affinity_product, action_queue count, ngày mua gần nhất. CTA để mở hồ sơ đầy đủ.

## Layout

```
     ┌ OVERLAY — Quick Preview ───────────────────┐
     │  Nguyễn Văn A                    [✕]       │
     │  +84901234567  •  GOLD  •  active          │
     │  ──────────────────────────────────────    │
     │  Mua gần nhất: 12/06/2026                 │
     │  Affinity: Sữa rửa mặt gentle             │
     │  Action queue: 2 items (CALL_NOW, REORDER) │
     │  ──────────────────────────────────────    │
     │  [Mở hồ sơ đầy đủ →]                      │
     └────────────────────────────────────────────┘
```

## Trigger

Hover (300ms delay) hoặc click vào customer name chip trong task rows.

## States

- default: Data loaded (từ crm_party_360 cache)
- loading: Fetch in-flight (skeleton)
- ST-360-NO-INSIGHT: Insight không có → ẩn insight rows

## Interactions

```yaml crm-contract
interactions:
  - id: A-O02-001
    element: overlay_backdrop
    region: content
    trigger: click
    action: close_overlay
  - id: A-O02-002
    element: btn_close
    region: content
    trigger: click
    action: close_overlay
  - id: A-O02-003
    element: btn_open_full_profile
    region: actions
    trigger: click
    action: navigate
    target: S03
    payload: { party_id: "$party.id" }
