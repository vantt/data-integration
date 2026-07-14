---
id: P02
type: panel
name: "Order History Panel"
platforms: [desktop]
hosted_by: [S03]
status: active
design_ref: ""
rules: [R2, R3, R6]
regions: [toolbar, order_list]
---

# P02 — Order History Panel

## Purpose

Panel tab "Đơn hàng" trong Customer 360 (S03). Hiển thị 10 đơn gần nhất từ `cache.wh_order_hdr`
join qua `customer_id` (value-link, no FK — R3). Mỗi row: order_code, date_key ICT, net_revenue VND,
status. `refreshed_at` của `wh_order_hdr` hiển thị ở toolbar. Không hiển thị gross_margin_pct (R7).

NV có thể ghi `related_order_code` khi log activity từ panel này.

## Layout

```yaml ui-layout
areas:
  - [toolbar]
  - [order_list]
content:
  toolbar:
    - row:
        - { h: "10 đơn gần nhất" }
        - { badge: "Cache: hôm nay 08:00 ICT ✓" }
        - { btn: "Xem thêm →", action: A-P02-003 }
  order_list:
    - table: { cols: ["Mã đơn", "Ngày", "Giá trị", "Trạng thái"], rows: 4 }
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│TOOLBAR                                                                     │
│· 10 đơn gần nhất [Cache: hôm nay 08:00 ICT v] [Xem thêm →]                 │
├────────────────────────────────────────────────────────────────────────────┤
│ORDER_LIST                                                                  │
│· tbl(Mã đơn | Ngày | Giá trị | Trạng thái) ×4                              │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## States

- ST-LOADING: Orders fetch in-flight
- ST-EMPTY: Không có đơn hàng nào → "Khách chưa có đơn hàng"
- ST-STALE-CACHE: wh_order_hdr refreshed_at > 24h

## Interactions

```yaml crm-contract
interactions:
  - id: A-P02-001
    element: order_row
    region: order_list
    trigger: click
    action: mutate
    effects: [ui.tooltip.show_order_detail]
  - id: A-P02-002
    element: btn_log_activity_with_order
    region: toolbar
    trigger: click
    action: open_overlay
    target: M08
    payload: { party_id: "$party.id", prefill_order_code: "$order.order_code" }
  - id: A-P02-003
    element: btn_load_more
    region: toolbar
    trigger: click
    action: mutate
    effects: [order_list.load_next_page, order_list.append_rows]
```
