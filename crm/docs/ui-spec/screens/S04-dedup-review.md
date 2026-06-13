---
id: S04
type: screen
name: "Dedup Review"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: [R4, R5, R9]
regions: [topbar, sidebar, candidate_list, detail_pane]
---

# S04 — Dedup Review

## Purpose

Manager duyệt hàng đợi `crm_dedup_candidate` status=pending. Mỗi candidate là một cặp party
có khả năng trùng nhau (fuzzy FTS5 tên + prefix SĐT). Manager xem thông tin 2 party song song,
quyết định merge hoặc reject. Chỉ exact SĐT auto-link; mọi fuzzy match đều qua màn hình này.

SSE badge trên sidebar cập nhật khi có candidate mới từ dedup job. Manager có thể undo merge đã
thực hiện nếu còn trong `party_merge_log`.

## Layout

```
┌─ C01 SIDEBAR ─┬──────────────────────────────────────────────────────────────┐
│               │  TOPBAR: Dedup Review   Pending: 12  [Filter: match_rule ▼]  │
│               ├───────────────────────┬──────────────────────────────────────┤
│               │  CANDIDATE LIST (35%) │  DETAIL PANE (65%)                   │
│               │  ┌─────────────────┐  │  ┌──────────────┬───────────────┐    │
│               │  │ ● Nguyễn V. A   │  │  │  Party A     │  Party B      │    │
│               │  │   vs NVA        │  │  │  Sapo: 1234  │  Sapo: 5678   │    │
│               │  │   exact_phone   │  │  │  SĐT: +849.. │  SĐT: +849..  │    │
│               │  ├─────────────────┤  │  │  Email: —    │  Email: a@x   │    │
│               │  │ ● Trần T. B     │  │  │  Đơn: 15     │  Đơn: 3       │    │
│               │  │   vs Tran B     │  │  └──────────────┴───────────────┘    │
│               │  │   fuzzy_name    │  │  Match rule: exact_phone             │
│               │  └─────────────────┘  │  [Merge A←B]  [Reject]  [Bỏ qua]    │
└───────────────┴───────────────────────┴──────────────────────────────────────┘
```

## States

- ST-DEDUP-NO-PENDING: Không có candidate pending → empty state
- ST-DEDUP-CONFLICT: Merge bị lỗi constraint ERR-MERGE-CONSTRAINT
- ST-LOADING: Candidate list loading

## Interactions

```yaml crm-contract
interactions:
  - id: A-S04-001
    element: candidate_row
    region: candidate_list
    trigger: click
    action: mutate
    effects: [detail_pane.load_candidate]
  - id: A-S04-002
    element: btn_merge
    region: detail_pane
    trigger: click
    action: open_overlay
    target: M01
    payload: { candidate_id: "$candidate.id" }
  - id: A-S04-003
    element: btn_reject
    region: detail_pane
    trigger: click
    action: mutate
    effects: [candidate.status.set_rejected, candidate_list.remove_row]
  - id: A-S04-004
    element: btn_skip
    region: detail_pane
    trigger: click
    action: mutate
    effects: [candidate_list.select_next]
  - id: A-S04-005
    element: btn_view_party_a
    region: detail_pane
    trigger: click
    action: navigate
    target: S03
    payload: { party_id: "$candidate.party_a_id" }
  - id: A-S04-006
    element: btn_view_party_b
    region: detail_pane
    trigger: click
    action: navigate
    target: S03
    payload: { party_id: "$candidate.party_b_id" }
  - id: A-S04-007
    element: filter_match_rule
    region: topbar
    trigger: change
    action: mutate
    effects: [candidate_list.reload]
  - id: A-S04-LSN01
    listens_to: dedup.candidate.created
    action: mutate
    effects: [topbar.pending_count.increment, candidate_list.prepend_row]
  - id: A-S04-LSN02
    listens_to: party.merged
    action: mutate
    effects: [candidate_list.remove_resolved]
```
