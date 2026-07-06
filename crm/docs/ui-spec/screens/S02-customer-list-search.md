---
id: S02
type: screen
name: "Customer List & Search"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: [R5]
regions: [topbar, sidebar, main, result_list]
---

# S02 — Customer List & Search

## Purpose

Màn hình tra cứu và duyệt danh sách khách hàng (crm_party). Sales Rep và CSKH dùng để tìm khách
theo SĐT, tên (FTS5), email, hoặc customer_code trước khi mở hồ sơ. Manager dùng để duyệt toàn bộ
danh sách và lọc theo tag/owner/status.

Target performance: < 200ms cho FTS search. Kết quả hiển thị ngay khi NV gõ (debounce 300ms).
Mỗi row hiển thị: tên, SĐT, value_group (GOLD/VIP/…), customer_status, owner, ngày mua gần nhất.

## Layout

```yaml ui-layout
columns: [1fr, 4fr]
areas:
  - [sidebar, main]
children:
  main:
    areas:
      - [topbar]
      - [result_list]
samples:
  sidebar: "(C01 global nav)"
  main: "(right content area — topbar · result_list)"
  topbar: "[🔍 SĐT / Tên / Email...]  Filter: [Value Group ▼] [Status ▼] [Owner ▼] [Tag ▼]"
  result_list: "Họ tên · SĐT · Group · Status · Owner  |  Nguyễn Văn A · 0901234567 · GOLD · active  [+ Tạo mới]  Trang 1/10 [< Trước][Sau >]"
elements:
  "Value Group ▼": A-S02-003
  "Status ▼": A-S02-004
  "Owner ▼": A-S02-005
  "Tag ▼": A-S02-006
  "+ Tạo mới": A-S02-002
  "< Trước": A-S02-008
  "Sau >": A-S02-007
```

<!-- ui-layout:ascii:start -->
```
┌───────────────┬────────────────────────────────────────────────────────────┐
│SIDEBAR        │MAIN                                                        │
│· (C01 global …│· (right content area — topbar · result_list)               │
└───────────────┴────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## States

- ST-CUSTOMER-SEARCH-EMPTY: Không tìm thấy → gợi ý tạo party mới
- ST-CUSTOMER-SEARCH-LOADING: FTS in-flight, skeleton rows
- ST-LOADING: Initial page load

## Interactions

```yaml crm-contract
interactions:
  - id: A-S02-001
    element: customer_row
    region: result_list
    trigger: click
    action: navigate
    target: S03
    payload: { party_id: "$party.id" }
  - id: A-S02-002
    element: btn_create_party
    region: main
    trigger: click
    action: open_overlay
    target: M02
  - id: A-S02-003
    element: filter_value_group
    region: topbar
    trigger: change
    action: mutate
    effects: [result_list.reload]
  - id: A-S02-004
    element: filter_status
    region: topbar
    trigger: change
    action: mutate
    effects: [result_list.reload]
  - id: A-S02-005
    element: filter_owner
    region: topbar
    trigger: change
    action: mutate
    effects: [result_list.reload]
  - id: A-S02-006
    element: filter_tag
    region: topbar
    trigger: change
    action: mutate
    effects: [result_list.reload]
  - id: A-S02-007
    element: pagination_next
    region: result_list
    trigger: click
    action: mutate
    effects: [result_list.page_next]
  - id: A-S02-008
    element: pagination_prev
    region: result_list
    trigger: click
    action: mutate
    effects: [result_list.page_prev]
  - id: A-S02-LSN01
    listens_to: global_search.submitted
    action: mutate
    effects: [result_list.reload_with_query]
  - id: A-S02-LSN02
    listens_to: global_search.query_changed
    action: mutate
    effects: [result_list.debounce_reload]
  - id: A-S02-LSN03
    listens_to: global_search.create_requested
    action: open_overlay
    target: M02
    payload: { prefill_name: "$event.prefill_query" }
  - id: A-S02-LSN04
    listens_to: filter_bar.changed
    action: mutate
    effects: [result_list.reload_with_filters]
  - id: A-S02-LSN05
    listens_to: filter_bar.cleared
    action: mutate
    effects: [result_list.reload]
  - id: A-S02-LSN06
    listens_to: tag_chips.chip_clicked
    action: mutate
    effects: [filter_tag.set, result_list.reload]
```
