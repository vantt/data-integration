---
id: C06
type: component
name: "Freshness Badge"
platforms: [desktop]
hosts: [S01, S03, S12, P01, P02]
status: active
design_ref: ""
rules: [R2]
regions: []
---

# C06 — Freshness Badge

## Purpose

Badge hiển thị `refreshed_at` của một bảng cache (wh_customer_insight, wh_order_hdr, v.v.).
Màu xanh nếu < 24h, vàng nếu 24–48h, đỏ nếu > 48h (ST-STALE-CACHE). Tooltip hiển thị
timestamp đầy đủ ICT. Bắt buộc hiển thị tại mọi surface có insight (R2).

## Props / API

- `table_name` (string, required): tên bảng cache (cho tooltip label)
- `refreshed_at` (string, required): UTC ISO-8601 timestamp
- `display_tz` (string, optional, default "Asia/Ho_Chi_Minh"): timezone for display

## States

- fresh: refreshed_at < 24h → green badge "✓ cập nhật HH:mm ICT"
- stale: 24–48h → yellow badge "⚠ HH:mm ICT (hôm qua)"
- very_stale: > 48h → red badge "✗ quá 48h — liên hệ admin"

## Emits

```yaml crm-contract
emits:
  - id: A-C06-001
    element: badge
    trigger: hover
    event: freshness_badge.hovered
    payload: { table_name: "$table_name", refreshed_at: "$refreshed_at" }
