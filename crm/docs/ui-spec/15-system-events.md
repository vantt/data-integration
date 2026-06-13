---
id: SYS
type: screen
name: "System Events"
platforms: [desktop]
hosts: []
status: active
rules: []
regions: []
---

# System Events — Backend / SSE Event Catalogue

Dotted-name events emitted by the Go backend or Python jobs that UI surfaces listen to via
`listens_to:`. These are **exempt from VR-LISTEN-ORPHAN** (dotted namespace = external signal).

| Event | Source | Payload | Surfaces that listen |
|---|---|---|---|
| `cache.refreshed` | Python reverse-ETL | `{ table, refreshed_at }` | S01, S03, P01 |
| `chat.message.received` | Go Messenger ingest | `{ conversation_id, message_id }` | S05, S06 |
| `dedup.candidate.created` | Go dedup job | `{ candidate_id, party_a_id, party_b_id }` | S04 |
| `campaign.target.converted` | Go conversion tracker | `{ campaign_id, party_id, order_code, revenue_vnd }` | S11 |
| `task.due.soon` | Go scheduler | `{ task_id, party_id, due_at }` | S01 |
| `segment.materialized` | Go segment job | `{ segment_id, member_count }` | S08, S09 |
| `party.merged` | Go merge handler | `{ surviving_party_id, merged_party_id }` | S03, S04 |
| `conversation.assigned` | Go assign handler | `{ conversation_id, assignee_user_id }` | S05, S06 |

## Notes

- All timestamps in payload are UTC ISO-8601; UI displays in ICT.
- SSE stream endpoint: `GET /api/sse` — Go server pushes named events.
- Surfaces that react to these events update their local state without full page reload.

```yaml crm-contract
interactions:
  - id: A-SYS-001
    trigger: system_event
    listens_to: cache.refreshed
    action: mutate
    effects: [ui.freshness_badge.update]
  - id: A-SYS-002
    trigger: system_event
    listens_to: chat.message.received
    action: mutate
    effects: [ui.inbox_badge.increment]
  - id: A-SYS-003
    trigger: system_event
    listens_to: dedup.candidate.created
    action: mutate
    effects: [ui.dedup_badge.increment]
  - id: A-SYS-004
    trigger: system_event
    listens_to: campaign.target.converted
    action: mutate
    effects: [ui.campaign_stats.refresh]
  - id: A-SYS-005
    trigger: system_event
    listens_to: segment.materialized
    action: mutate
    effects: [ui.segment_member_count.update]
  - id: A-SYS-006
    trigger: system_event
    listens_to: party.merged
    action: mutate
    effects: [ui.dedup_queue.remove_resolved]
```
