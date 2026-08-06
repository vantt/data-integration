# Phase 05 — Worklist read path: match suppression per mart

**Priority:** P2 · **Status:** pending · **Effort:** 1h · **Blocked by:** Phase 03
**File ownership:** `crm/src/adapters/outbound/sqlite/cache_repository.py` +
`crm/src/tests/test_worklist_suppression_per_mart.py` (new).
**Does NOT touch** `action_state_repository.py` (Phase 04).

## Context — verified current predicates

`cache_repository.py` — customer branch (`:179-185`):
```sql
LEFT JOIN crm_action_dismissal ad
       ON ad.party_id = pi.party_id
      AND ad.action_type = a.action_type
...
AND (ad.party_id IS NULL OR ad.dismissed_until <= strftime('%Y-%m-%dT%H:%M:%fZ','now'))
```
SKU branch (`:227-233`) — identical except `sa.action_type`.

Both branches are string-concatenated into `full_sql` (`:249-251`,
`"SELECT * FROM (" + _customer_branch + " UNION ALL " + _sku_branch + ") ORDER BY priority ASC"`)
with a customer-only `fallback_sql` (`:254`) used when `wh_sku_action_queue` is missing
(`:256-259` catches `OperationalError`).

**There is no source discriminator column in the result set.** Consumers infer the grain from
`supply_stream` being NULL (customer, `:169`) vs non-NULL (SKU, `:217`).

`_fetch_actions()` (`:397`) — the C360 reason rail — **deliberately does not** join
`crm_action_dismissal`; documented at `cache_repository.py:9-15`. **Do not change this** (locked
decision D5); it is an existing verified decision, not an oversight.

## Requirements

**Functional**
1. Customer branch matches only `ad.source_mart = 'mart_customer_action_queue'`.
2. SKU branch matches only `ad.source_mart = 'mart_customer_sku_action_queue'`.
3. Expiry semantics unchanged (`dismissed_until <= now` ⇒ row reappears).
4. `fallback_sql` path keeps working when `wh_sku_action_queue` is absent.
5. `_fetch_actions()` untouched.

**Non-functional**
6. Predicate stays a plain equality (no `OR`/`IN`) — Phase 03's row-expansion backfill guarantees
   there is no `'ANY'` sentinel to accommodate.
7. Add the mart literal as a **named constant** at module level so the two branches and Phase 04
   cannot drift apart. Suggested: import nothing new — define
   `_MART_CUSTOMER = 'mart_customer_action_queue'` / `_MART_SKU = 'mart_customer_sku_action_queue'`
   in a small shared module both adapters import, e.g. `crm/src/domain/entities/action_scenario.py`
   (created in Phase 04). Coordinate: Phase 04 owns that file, Phase 05 only imports from it.

## Related code files

**Modify**
- `crm/src/adapters/outbound/sqlite/cache_repository.py` — 2 JOIN clauses + module docstring
  (`:9-15`) to mention the mart-scoped match.

**Create**
- `crm/src/tests/test_worklist_suppression_per_mart.py`

**Delete** — none.

## Implementation steps

1. Customer branch, replace `:179-181` with:
   ```sql
   LEFT JOIN crm_action_dismissal ad
          ON ad.party_id = pi.party_id
         AND ad.action_type = a.action_type
         AND ad.source_mart = 'mart_customer_action_queue'
   ```
2. SKU branch, replace `:227-229` with the same shape using `sa.action_type` and
   `'mart_customer_sku_action_queue'`.
3. Leave both `WHERE` clauses (`:185`, `:233`) exactly as they are — the LEFT JOIN + `IS NULL`
   pattern still works, it just now fails to match rows belonging to the other mart.
4. Update the module docstring (`:11-13`) to state that `list_all_action_queue()` matches
   `crm_action_dismissal` on `(party_id, action_type, source_mart)` and that `_fetch_actions()` still
   deliberately does not filter it at all.
5. Write `test_worklist_suppression_per_mart.py` reusing the fixture helpers from
   `test_action_dismissal_ttl.py:39-129` (`_setup_cache_tables`, `_insert_action`, `_link_party`,
   `_make_repos`) — extract them to a shared helper module if copying would exceed ~40 lines, else
   import directly.

## Test matrix (this phase)

| # | Setup | Assert |
|---|---|---|
| W1 | Customer-level + SKU-level `REORDER_NUDGE` both active for party P. Suppress `('REORDER_NUDGE','mart_customer_action_queue')`. | queue contains the SKU row, not the customer row |
| W2 | Mirror of W1, suppress the SKU mart instead. | queue contains the customer row, not the SKU row |
| W3 | Suppress both marts. | neither row in queue |
| W4 | Suppression with `dismissed_until` in the past. | row present (expired ⇒ reappears) |
| W5 | Suppression for a different `party_id`. | row present |
| W6 | `wh_sku_action_queue` table dropped. | `fallback_sql` path returns customer rows, customer-mart suppression still applies |
| W7 | Legacy expanded rows (both marts, from the 0046 backfill). | both grains hidden — legacy semantics preserved |
| W8 | `_fetch_actions()` for a party whose action_type is suppressed. | action still returned (D5 pinned) |

Also re-run `pytest crm/src/tests/test_worklist_suppression_do_not_contact.py` — must stay green,
proving mechanism #3 is untouched.

## Todo list

- [x] Customer branch JOIN + mart literal (via shared `MART_CUSTOMER`/`MART_SKU` constants in `action_scenario.py`)
- [x] SKU branch JOIN + mart literal
- [x] Module docstring updated
- [x] W1-W8 green (8/8, new file `test_worklist_suppression_per_mart.py`)
- [x] `test_worklist_suppression_do_not_contact.py` green
- [x] `test_action_dismissal_ttl.py` green
- [x] Full suite: 1176 passed, 1 skipped, zero regressions

## Success criteria

- W1/W2 demonstrate independent per-grain suppression — the core promise of the feature.
- Zero change in `list_all_action_queue()` row counts on a DB with no dismissals at all.
- `grep -n "crm_action_dismissal" crm/src/adapters/outbound/sqlite/cache_repository.py` shows the
  discriminator in both JOINs and nowhere else.

## Risk assessment

| Risk | L×I | Mitigation |
|---|---|---|
| Deploying Phase 05 before Phase 03's migration → `no such column: source_mart` | Med×High | Runner applies migrations at app start (`connection.py:112-115`) before routes serve; ship 03+04+05 in one deploy. `_is_missing_column()` (`:38`) would swallow this into an empty queue — **worse than a crash**. Add an assertion in the deploy smoke test that the queue is non-empty |
| Mart literal typo diverges from what Phase 04 writes → suppression silently never matches | Med×High | Shared constants (requirement 7) + integration test W1 catches it |
| Someone "fixes" `_fetch_actions()` to also filter | Low×Med | Docstring states the intent explicitly; W8 pins it |
| Legacy expanded rows behave differently from before | Low×Med | W7 |

## Rollback

Revert the two JOIN clauses to the mart-agnostic form. Works against the 0046 schema too (it simply
matches either mart row), so Phase 05 can be reverted independently of Phase 03 in an emergency.

## Security considerations

None new — read path only, same tables, same ATTACH boundary.

## Next steps

Feeds Phase 07's end-to-end test. Parallel with Phase 04.
