# Verification — Priority Scales & Action-State Filtering (S01 worklist)

**Date:** 2026-06-23 · **For:** S01 triage redesign plan · **Scope:** verify OQ#3 + ranking preconditions.

## OQ#3 — does `list_all_action_queue` filter dismissed/snoozed? → YES

`cache_repository.py:121-177`. SQL filters:
- `WHERE COALESCE(s.status,'open') != 'dismissed'` (`:148`) — dismissed excluded.
- `AND (status != 'snoozed' OR s.snoozed_until < date('now','+7 hours'))` (`:149-150`) — snoozed-until-future excluded; `+7h` = ICT offset. **Woke-up snoozed rows reappear** (status still `'snoozed'`, `snoozed_until` in past) → Band 1 "vừa thức" detectable via `status=='snoozed' AND snoozed_until <= today`.
- `LEFT JOIN crm_task t ON t.source='action_queue' AND t.source_ref=a.action_id AND t.status NOT IN ('done','cancelled')` + `t.task_id IS NULL` (`:144-151`) — actions that already spawned an open task are hidden (no double-count).
- `ORDER BY a.priority ASC` (`:152`).

Both `status` + `snoozed_until` are selected (`:135-136`, `:173-174`) → data available for banding.

## CRITICAL — two opposite `priority` scales

| Field | Source | Scale |
|-------|--------|-------|
| `crm_task.priority` | `task.py:33-37` | `0=normal,1=high,2=urgent` → **higher=urgent** |
| `wh_action_queue.priority` | mart `priority_rank`, `mart_customer_action_queue.sql:107-115` | `CALL_NOW=1,REORDER_NUDGE=2,REORDER_PREEMPT=3,WIN_BACK=4,SECOND_ORDER=5,HIGH_CANCEL_RISK=6,ELSE=9` → **lower=urgent**, derived from action_type |

`priority_rank` IS the action-type tier (redundant with a separate tier tie-break).

### Bugs this exposes (current code)
- `screen_worklist.py:84` `a.priority >= 2` for "urgent" actions → excludes CALL_NOW(=1), keeps least-urgent. **Priority filter broken for actions.**
- `cache_repository.py:152` `ORDER BY a.priority ASC` → correct for actions (rank1 first), but any naive "priority DESC" in new code is wrong for actions.

### Required: normalize to one urgency scale (higher=urgent)
- action: `urgency = 10 - priority_rank`  (CALL_NOW=9 … ELSE=1)
- task:   `urgency = 7 + priority`        (normal=7, high=8, urgent=9)
- tie-break: `value_at_stake_vnd` DESC → due/pending.

## action_type drift (affects filter chips)
Mart emits `{CALL_NOW, REORDER_NUDGE, REORDER_PREEMPT, WIN_BACK, SECOND_ORDER, HIGH_CANCEL_RISK}`.
Entity `VALID_ACTION_TYPES` (`cache_insight.py:51-58`) lists `{CALL_NOW, REORDER_NUDGE, WIN_BACK, UPSELL, CROSS_SELL, COLLECT_FEEDBACK}`.
→ Filter chips MUST derive from distinct `action_type` present in data, not the constant. Badge styling (`bdg_cls`) may lack styles for `REORDER_PREEMPT/SECOND_ORDER/HIGH_CANCEL_RISK` — verify in Phase 03.

## Data lifecycle (recap, verified earlier)
`upsert_action_queue` (`sqlite_upsert.py:162-170`) signal-based full replace → no zombie actions. `generated_date` daily, `pending_since` preserved. Staleness only when sync stalls (covered by `is_stale>24h`).

## Open questions
1. `priority_rank` ELSE=9 maps which action_types? (UPSELL/CROSS_SELL/COLLECT_FEEDBACK not in mart CASE → would be ELSE or absent). Verify whether mart actually produces those types.
2. Owner per-customer field existence (for "Của tôi" filter).
