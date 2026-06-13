---
id: C02
type: component
name: "Global Customer Search"
platforms: [desktop]
hosts: [S02, S03]
status: active
design_ref: ""
rules: [R5]
regions: []
---

# C02 — Global Customer Search

## Purpose

Thanh tìm kiếm khách hàng toàn cục (FTS5 + SĐT exact). Hiển thị trong topbar của Customer List
(S02) và có thể mount ở header S03 để tìm nhanh party khác. Debounce 300ms, target < 200ms.
Kết quả dropdown gồm: tên, SĐT, value_group. Chọn kết quả → emit `global_search.submitted`
để host screen xử lý (navigate hoặc filter list).

## Props / API

- `placeholder` (string, optional): placeholder text
- `mode` (string): "navigate" (click → S03) | "filter" (click → emit filter event)
- `autofocus` (bool, optional): focus on mount

## States

- default: Empty input
- searching: FTS query in-flight (spinner in input)
- results: Dropdown list visible
- no_results: "Không tìm thấy" + CTA tạo mới

## Emits

```yaml crm-contract
emits:
  - id: A-C02-001
    element: search_result_item
    trigger: click
    event: global_search.submitted
    payload: { party_id: "$result.id", query: "$input.value" }
  - id: A-C02-002
    element: search_input
    trigger: input
    event: global_search.query_changed
    payload: { query: "$input.value" }
  - id: A-C02-003
    element: btn_create_new
    trigger: click
    event: global_search.create_requested
    payload: { prefill_query: "$input.value" }
