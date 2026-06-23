# Phase 01 Output Contract

**For:** Phase 02 (filter bar) and Phase 03 (banded UI).
**Date:** 2026-06-23. Authoritative — deviations from phase-01 spec are noted inline.

---

## 1. Template context variables

All variables are set by `_load_worklist_data` in `screen_worklist.py` and
available in every template that renders from `/worklist` or `/worklist/fragment`.

| Variable | Type | Description |
|---|---|---|
| `bands` | `list[dict]` | Ordered list of band dicts — always 4 entries (ids 0,1,2,3) even when empty. See §2. |
| `value_total` | `int` | Sum of `value_at_stake_vnd` for all actions after filtering (VND). |
| `counts` | `dict` | `{actions: int, tasks: int, total: int}` — counts after filtering. |
| `task_open` | `int` | Count of open tasks after filtering (all tasks passed to ranking are open). |
| `urgent_count` | `int` | Count of rows in bands 0 + 1 (overdue + today/urgent). Used for progress bar. |
| `party_extras` | `dict[str, dict]` | Keyed by `party_id`. Value: `{preferred_identity: PartyIdentity|None, contact_pref_notes: list[Note]}`. |
| `refreshed_at` | `str` | UTC ISO-8601 string from first action's `refreshed_at`; empty string if no actions. |
| `is_stale` | `bool` | True when `refreshed_at` is older than 24 h. |
| `available_types` | `list[str]` | Sorted distinct `action_type` values from **unfiltered** action data. Use for type-filter chips in Phase 02. |
| `active_filter_count` | `int` | Count of non-default active filters (badge on filter bar toggle). |
| `filters` | `dict` | Current filter state — see §3. |
| `actions` | `list[ActionQueueItem]` | Filtered actions list (post-filter, pre-rank). Available for templates that need direct iteration; prefer `bands` for display. |
| `tasks` | `list[Task]` | Filtered tasks list (post-filter, pre-rank). Same note as `actions`. |

Additionally, top-level filter keys are spread into context for backward compat:
`assignee`, `priority` (both from `filters` dict — same values, direct keys).

---

## 2. Band structure

`bands` is always a list of exactly 4 dicts, ordered `[0, 1, 2, 3]`. Empty bands have `count=0` and `rows=[]`.

```python
{
    "id":          int,        # 0=overdue, 1=today/urgent, 2=on-track, 3=neglected
    "label":       str,        # Vietnamese label (Quá hạn / Hôm nay / Khẩn / Trong hạn / Treo lâu)
    "icon":        str,        # emoji prefix (🔴 / ⏰ / 📋 / 💤)
    "rows":        list[WorklistRow],
    "count":       int,
    "total_value": int,        # sum of value_at_stake_vnd for rows in this band (VND)
}
```

---

## 3. WorklistRow fields

Each element of `band["rows"]` is a `WorklistRow` dataclass
(`crm/src/application/worklist_ranking.py`).

| Field | Type | Description |
|---|---|---|
| `kind` | `str` | `'action'` or `'task'` |
| `band` | `int` | Band id (0–3) |
| `urgency` | `int` | Normalized urgency score 1–9 (higher = more urgent). action: `10 - priority_rank`; task: `7 + priority`. |
| `value` | `int` | `value_at_stake_vnd` for actions; `0` for tasks (VND). |
| `neglect_days` | `int` | Days since `pending_since` (actions) or days overdue (tasks in band 0). Used for "đã chờ N ngày" badge. |
| `ref_id` | `str` | `action_id` (action) or `task_id` (task). |
| `payload` | `ActionQueueItem \| Task` | Original entity — all fields accessible. |

---

## 4. ActionQueueItem payload fields (kind='action')

From `crm/src/domain/entities/cache_insight.py`:

| Field | Type | Notes |
|---|---|---|
| `action_id` | `str` | Unique ID — used in HTMX endpoints `/worklist/actions/{id}/dismiss\|snooze` |
| `customer_key` | `str` | Sapo customer key |
| `action_type` | `str` | e.g. `CALL_NOW`, `REORDER_NUDGE`, `WIN_BACK`, `REORDER_PREEMPT`, `SECOND_ORDER`, `HIGH_CANCEL_RISK` |
| `rationale_vi` | `str` | Vietnamese rationale text for display |
| `value_at_stake_vnd` | `int` | VND monetary opportunity |
| `priority` | `int` | Raw warehouse priority_rank (1=CALL_NOW, 9=ELSE) — lower=more urgent. Use `row.urgency` for display comparisons. |
| `pending_since` | `str` | `YYYY-MM-DD` — first day this action episode appeared |
| `generated_date` | `str` | `YYYY-MM-DD` — last warehouse refresh date |
| `refreshed_at` | `str` | UTC ISO-8601 warehouse sync timestamp |
| `customer_name` | `str` | Display name; empty string when not resolved |
| `party_id` | `str\|None` | CRM party_id; None when customer not yet synced to CRM |
| `status` | `str` | `open` \| `snoozed` (dismissed rows are excluded upstream) |
| `snoozed_until` | `str\|None` | `YYYY-MM-DD`; set when `status='snoozed'` and the row is in band 1 (woke-up) |

---

## 5. Task payload fields (kind='task')

From `crm/src/domain/entities/task.py`:

| Field | Type | Notes |
|---|---|---|
| `task_id` | `str` | UUID — used in HTMX endpoint `/tasks/{id}/done` |
| `title` | `str` | Task title |
| `priority` | `int` | `0=normal, 1=high, 2=urgent` (higher = more urgent) |
| `status` | `str` | `open\|doing` (done/cancelled excluded upstream) |
| `source` | `str` | `manual\|action_queue\|campaign` |
| `created_at` | `str` | UTC ISO-8601 |
| `updated_at` | `str` | UTC ISO-8601 |
| `party_id` | `str\|None` | CRM party_id; None for party-less tasks |
| `description` | `str\|None` | Optional body text |
| `due_at` | `str\|None` | UTC ISO-8601 datetime — drives band 0/1 assignment |
| `assignee_user_id` | `str\|None` | FK to crm_app_user; None when unassigned |
| `source_ref` | `str\|None` | action_id or campaign_id when source != manual |
| `created_by` | `str\|None` | FK to crm_app_user |
| `completed_at` | `str\|None` | UTC ISO-8601; set when done |

---

## 6. Filter state (`filters` dict)

```python
{
    "assignee":  str,        # 'me' | 'all' (default: 'me')
    "priority":  str,        # 'all' | 'high' | 'urgent' (default: 'all')
    "types":     list[str],  # action_type strings to include; [] = all types
    "q":         str,        # free-text search query; '' = no filter
    "min_value": int,        # minimum value_at_stake_vnd; 0 = no filter
}
```

### Query-parameter names (for HTMX hx-get URLs)

| Param | Maps to | Notes |
|---|---|---|
| `assignee` | `filters.assignee` | |
| `priority` | `filters.priority` | |
| `type` | `filters.types` | Comma-separated list, e.g. `type=CALL_NOW,WIN_BACK` |
| `q` | `filters.q` | URL-encoded free text |
| `min_value` | `filters.min_value` | Integer VND threshold |

---

## 7. File ownership by downstream phase

| File | Owner | Notes |
|---|---|---|
| `fragments/_wl_filter_bar.html` | **Phase 02** | Replace stub with full filter bar (type chips, search, min_value). Must keep `hx-get="/worklist/fragment?..."` pattern; preserve all query params when partially changing filters. |
| `fragments/_wl_bands.html` | **Phase 03** | Replace stub with full collapsible band UI + `_wl_row.html` macro. Must use `bands` list, not raw `actions`/`tasks`. Cap logic (N per band) lives here. |
| `fragments/worklist_fragment.html` | **Phase 01 (done)** | Skeleton — do not rewrite; add includes only if needed for new Phase 02/03 features outside the two stubs. |
| `src/application/worklist_ranking.py` | **Phase 01 (done)** | Pure module. Phase 04 (tests) reads it; no other phase modifies it. |
| `src/adapters/inbound/web/screen_worklist.py` | **Phase 01 (done)** | Thin adapter. Phase 02 may need to add a `min_value` range helper if UX requires it; coordinate with Phase 01 author. |

---

## 8. Preserved HTMX behaviours (must not regress)

| Behaviour | Endpoint / mechanism |
|---|---|
| Row click → customer 360 | `hx-get="/customers/{party_id}"` on `.wl-row` for actions |
| Task title link → customer 360 | `href="/customers/{party_id}"` on `.wl-row__name` for tasks |
| Quick-contact → M08 modal | `hx-get="/modals/m08?party_id=...&mode=contact_attempt[&channel=...]"` |
| Dismiss action | `hx-patch="/worklist/actions/{action_id}/dismiss"` + `hx-swap="delete"` |
| Snooze action | `hx-patch="/worklist/actions/{action_id}/snooze?days=N"` + `hx-swap="delete"` |
| Mark task done | `hx-patch="/tasks/{task_id}/done"` swaps row with task_done_row fragment |
| Fragment refresh | `hx-get="/worklist/fragment?..."` targeting `#worklist-container` with `outerHTML` |
| Freshness footer | `is_stale` + `refreshed_at` — always rendered at bottom of `worklist_fragment.html` |
| Empty state | When `counts.total == 0` render empty-state div (in `_wl_bands.html`) |

---

## 9. Deviations from phase-01 spec

| Spec text | Implemented as | Reason |
|---|---|---|
| `urgency_score(item) -> int` (single-arg) | `urgency_score(kind, priority_or_rank) -> int` (two-arg) | Avoids importing domain entities into the pure module; caller extracts the scalar before passing. |
| `rank_worklist` returns `list[WorklistRow]` | Returns `dict` with `bands`, `counts`, `value_total`, `task_open`, `urgent_count` | The spec note says "returns ordered rows + band metadata + counts" — the dict form is the full shape; a flat list would require the template to re-group. |
| `WorklistRow.urgency_score` field | Named `urgency` | Shorter; avoids redundancy since the type is already called WorklistRow (not ambiguous). |
| `assign_band` takes `row_like` object | Takes explicit scalar args: `kind, urgency, due_date, pending_date, snoozed_until, status, today` | Pure function — no object dependencies, easier to unit-test each band rule in isolation. |
