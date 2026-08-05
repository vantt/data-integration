# Phase 04 — Suppression repository, ports, entities

**Priority:** P2 · **Status:** pending · **Effort:** 2h · **Blocked by:** Phase 03
**File ownership:** `crm/src/adapters/outbound/sqlite/action_state_repository.py`,
`crm/src/domain/ports/action_state_port.py`, `crm/src/domain/entities/action_dismissal.py`,
new `crm/src/adapters/outbound/sqlite/action_catalog_repository.py`,
new `crm/src/domain/ports/action_catalog_port.py`,
new `crm/src/application/suggestion_settings_service.py`,
`crm/src/tests/test_action_dismissal_ttl.py`.
**Does NOT touch** `cache_repository.py` (Phase 05) or any web/composition file (Phase 06).

## Context — verified current state

- `SQLiteActionStateRepository` — `action_state_repository.py`:
  - `_DISMISSAL_TTL_DAYS = 30` (`:26`)
  - `dismiss()` (`:40-52`) writes `crm_action_state` then calls `_dismiss_by_party_and_type()`
  - `_dismiss_by_party_and_type()` (`:56-79`) — `ON CONFLICT(party_id, action_type)`, TTL f-stringed
    into the SQL at `:72`
  - `_resolve_party_and_action_type()` (`:81-118`) — two branch queries, customer branch first
    (`cache.wh_action_queue`), then SKU branch (`cache.wh_sku_action_queue`); returns
    `(party_id, action_type)` or `None`; swallows missing-table errors via `_is_missing_table_or_column()` (`:29-31`)
  - `list_active_dismissals()` (`:120-156`) — GLOBAL (all parties), enriched, newest first
  - `resolve_party_id()` (`:182-190`) — returns `resolved[0]`
- Port `ActionStatePort` — `domain/ports/action_state_port.py:7-27`: `dismiss`, `snooze`, `reopen`,
  `resolve_party_id`. **`list_active_dismissals` is NOT on the port** — the tasks-board screen declares
  its own `DismissalReader` Protocol at `screen_tasks_board.py:43-45`.
- Entity `ActionDismissal` — `domain/entities/action_dismissal.py:14-27`: 7 fields, incl.
  `party_display`, `dismissed_by_display`.
- Consumers of `list_active_dismissals()` — exhaustive: `screen_tasks_board.py:115` (rendering
  `dismissed_actions.html:47-60`) and tests at `test_action_dismissal_ttl.py:422,455,498`. No others.

## Key insight — the mart is already known at resolve time

`_resolve_party_and_action_type()` iterates the two branches in a fixed order. Whichever branch
returns a row tells you the originating mart. So the quick-dismiss fast path can record the precise
`source_mart` with no extra query — change the return to a 3-tuple.

`resolve_party_id()` uses `resolved[0]`, so widening the tuple leaves it correct with zero edits.
Blast radius: 3 internal call sites (`:63`, `:189`), no external caller.

## Requirements

**Functional**
1. `_resolve_party_and_action_type()` returns `(party_id, action_type, source_mart)`.
2. `_dismiss_by_party_and_type()` writes `source_mart` and conflicts on the new 3-column PK.
   Default duration stays `_DISMISSAL_TTL_DAYS = 30` (locked decision D6).
3. NEW `suppress(party_id, action_type, source_mart, until_date, user_id)` — direct write, **no
   `action_id` required** (locked decision #5). Upsert semantics; overwrites end date and owner.
4. NEW `unsuppress(party_id, action_type, source_mart)` — deletes the row (turning a suggestion back on).
5. NEW `list_dismissals_for_party(party_id)` — per-party, returns ALL rows including expired ones,
   so the panel can show "đã hết hạn" instead of a misleading "đang bật".
6. `list_active_dismissals()` keeps its current global semantics and gains `source_mart` on the entity.
7. NEW `SQLiteActionCatalogRepository.list_catalog()` reading `cache.wh_action_scenario_registry`,
   graceful-empty when the table is absent (matches `cache_repository` house rule, `cache_repository.py:4`).
8. NEW `SuggestionSettingsService` composing catalog × per-party dismissals into a
   `scenario_group`-grouped view model, and validating writes against the catalog.

**Non-functional**
9. Ports are `typing.Protocol` in `domain/ports/` per `crm/AGENTS.md` §Hexagonal.
10. Service returns domain entities; no SQL, no HTTP, no template imports.
11. Dates: `dismissed_until` is stored as the existing UTC ISO-8601 `%Y-%m-%dT%H:%M:%fZ` text so the
    existing comparison at `cache_repository.py:185,233` keeps working. The panel supplies a **date**;
    convert to end-of-day ICT → UTC instant. Do not store a bare `YYYY-MM-DD` — it would sort before
    every timestamp and silently expire immediately.

## Architecture / data flow

```
P07 panel (Phase 06)
  └─ SuggestionSettingsService
       ├─ ActionCatalogPort.list_catalog()          → cache.wh_action_scenario_registry  (read)
       ├─ ActionSuppressionPort.list_for_party(pid) → crm_action_dismissal               (read)
       ├─ ActionSuppressionPort.suppress(...)       → crm_action_dismissal               (write)
       └─ ActionSuppressionPort.unsuppress(...)     → crm_action_dismissal               (delete)

quick-dismiss card (unchanged UX)
  └─ ActionStatePort.dismiss(action_id)
       ├─ crm_action_state (per-episode)
       └─ _dismiss_by_party_and_type → crm_action_dismissal with the resolved source_mart, +30d
```

## Related code files

**Create**
- `crm/src/domain/ports/action_catalog_port.py` — `ActionCatalogPort` Protocol.
- `crm/src/domain/entities/action_scenario.py` — `ActionScenario` dataclass
  (`action_type, mart, enabled, scenario_group, description_vi`).
- `crm/src/adapters/outbound/sqlite/action_catalog_repository.py` — `SQLiteActionCatalogRepository`.
- `crm/src/application/suggestion_settings_service.py` — `SuggestionSettingsService` + the
  `SuggestionSettingRow` / `SuggestionSettingGroup` view-model dataclasses.

**Modify**
- `crm/src/adapters/outbound/sqlite/action_state_repository.py` — items 1-6 above.
- `crm/src/domain/ports/action_state_port.py` — add `ActionSuppressionPort` Protocol (separate,
  narrow port; do NOT fatten `ActionStatePort`, per `crm/AGENTS.md` §"Split read/write when access
  patterns differ").
- `crm/src/domain/entities/action_dismissal.py` — add `source_mart: str`.
- `crm/src/tests/test_action_dismissal_ttl.py` — update fixtures for the new column, add the new cases.

**Delete** — none.

## Implementation steps

1. `action_dismissal.py` — add `source_mart: str` to the dataclass. Place it after `action_type`.
   Grep confirms only `action_state_repository.py:146-154` constructs it and only
   `dismissed_actions.html` renders it, so field order is safe.
2. `action_state_repository.py`:
   - Change `_resolve_party_and_action_type` to carry a mart label per branch. Keep the existing
     two-branch tuple but make it `((sql, 'mart_customer_action_queue'), (sql, 'mart_customer_sku_action_queue'))`
     and return the 3-tuple. Update the docstring.
   - `_dismiss_by_party_and_type`: unpack 3 values, add `source_mart` to the column list, VALUES, and
     `ON CONFLICT(party_id, action_type, source_mart)`.
   - Add `suppress()`: same INSERT ... ON CONFLICT shape but takes `until_utc: str` as a bound
     parameter (no f-string interpolation).
   - Add `unsuppress()`: `DELETE FROM crm_action_dismissal WHERE party_id=? AND action_type=? AND source_mart=?`.
   - Add `list_dismissals_for_party()`: same enrichment SELECT as `list_active_dismissals()` but
     `WHERE d.party_id = ?` and **no** `dismissed_until >` filter; order by `action_type, source_mart`.
     Wrap in the same `_is_missing_table_or_column` graceful-empty guard.
   - Add `source_mart=row["source_mart"]` to both entity constructions.
3. `action_state_port.py` — append:
   ```python
   class ActionSuppressionPort(Protocol):
       """Outbound port for explicit per-(party, action_type, mart) suppression."""
       def suppress(self, party_id: str, action_type: str, source_mart: str,
                    until_utc: str, user_id: Optional[str] = None) -> None: ...
       def unsuppress(self, party_id: str, action_type: str, source_mart: str) -> None: ...
       def list_dismissals_for_party(self, party_id: str) -> list[ActionDismissal]: ...
   ```
4. `action_catalog_port.py` + `action_catalog_repository.py` — single method
   `list_catalog() -> list[ActionScenario]`, `SELECT action_type, mart, enabled, scenario_group,
   description_vi FROM cache.wh_action_scenario_registry ORDER BY scenario_group, mart, action_type`,
   returning `[]` on missing table.
5. `suggestion_settings_service.py`:
   - `get_settings(party_id)` → groups catalog rows by `scenario_group`, joins each
     `(action_type, mart)` to at most one dismissal row, and computes per row:
     `is_globally_disabled` (catalog `enabled == 0`), `is_suppressed` (row exists AND
     `dismissed_until > now`), `is_expired` (row exists AND expired), `until_date_ict`,
     `set_by_display`.
   - `suppress(party_id, action_type, source_mart, until_date_ict, user_id)`:
     **validate** `(action_type, source_mart)` exists in the catalog and is not globally disabled →
     raise `ValueError` otherwise (prevents orphan rows and pointless toggles); convert
     `until_date_ict` (a `YYYY-MM-DD` from the date input) to `23:59:59.999` ICT → UTC ISO-8601;
     reject dates in the past and beyond a 1-year ceiling; delegate to the port.
   - `unsuppress(...)` → straight delegation.
   - Keep this file under 200 lines per the global modularisation rule; move the date helper to
     an existing datetime util module if one exists (`grep -rn "format_datetime_ict" crm/src/` first).
6. Update `test_action_dismissal_ttl.py`: existing `_setup_cache_tables`/`_insert_action` helpers stay;
   assertions that read `crm_action_dismissal` gain `source_mart`.

## Test matrix (unit — this phase)

| # | Case | Assert |
|---|---|---|
| U1 | `dismiss()` on a customer-level action | row has `source_mart='mart_customer_action_queue'`, `+30d` |
| U2 | `dismiss()` on a SKU-level action | row has `source_mart='mart_customer_sku_action_queue'` |
| U3 | `dismiss()` on SKU `REORDER_NUDGE` | NO row exists for `('mart_customer_action_queue','REORDER_NUDGE')` — the behaviour change (D4) |
| U4 | `suppress()` with no matching action anywhere in cache | row written; no exception (pre-emptive suppression) |
| U5 | `suppress()` twice, different dates | 1 row, latest date + latest user wins |
| U6 | `unsuppress()` | row gone |
| U7 | `list_dismissals_for_party` | returns expired rows too; other parties excluded |
| U8 | `list_active_dismissals` | unchanged global behaviour; `source_mart` populated |
| U9 | catalog repo when `wh_action_scenario_registry` absent | returns `[]`, no raise |
| U10 | service `suppress` with an unknown `(action_type, mart)` pair | raises `ValueError`, nothing written |
| U11 | service `suppress` on `GIFT_TO_PURCHASE` (globally disabled) | raises `ValueError` |
| U12 | date conversion | `2026-08-31` → an instant that is still `> now` at 23:00 ICT on 2026-08-31 |

Run: `pytest crm/src/tests/test_action_dismissal_ttl.py -q` plus the new service test file.
Tests run locally on temp SQLite (`crm/src/tests/conftest.py:30-74`); no Docker needed.

## Todo list

- [x] `ActionScenario` entity + `ActionCatalogPort` + `SQLiteActionCatalogRepository`
- [x] `source_mart` on `ActionDismissal`
- [x] 3-tuple resolve + mart-aware `_dismiss_by_party_and_type`
- [x] `suppress` / `unsuppress` / `list_dismissals_for_party`
- [x] `ActionSuppressionPort` Protocol
- [x] `SuggestionSettingsService` with catalog validation + ICT→UTC date conversion
- [x] U1-U12 green (13 new tests); existing `test_action_dismissal_ttl.py` green (16/16, zero edits needed)
- [x] Files under 200 lines each (new files); `action_state_repository.py` grew 191→~290 lines (existing file, 3 closely-related methods added to the same cohesive class — not split, see rollback note)

## Success criteria

- All 12 unit cases pass.
- `grep -n "ON CONFLICT(party_id, action_type)" crm/src/` returns nothing (all upgraded to 3 columns).
- No concrete adapter imported outside `composition.py` (Phase 06 wires them).
- `resolve_party_id()` still returns the right value with zero edits (3-tuple `[0]`).

## Risk assessment

| Risk | L×I | Mitigation |
|---|---|---|
| **D4 behaviour change**: quick-dismiss on SKU `REORDER_NUDGE` no longer hides the customer-level one | High×Med | Intended per locked decision. Test U3 pins it. Call it out in the release note to CS — the panel is the surface for "tắt cả hai" |
| Date stored as bare `YYYY-MM-DD` sorts before every `...T..Z` timestamp → suppression expires instantly | Med×High | Requirement 11 + test U12 |
| Panel writes an `(action_type, mart)` pair absent from the catalog → invisible orphan row | Med×Med | Service-level validation (step 5) + U10 |
| `list_dismissals_for_party` returning expired rows confuses the panel | Low×Low | View model computes explicit `is_suppressed` / `is_expired`; template never re-derives |
| Fattening `ActionStatePort` breaks unrelated screens | Low×Med | Separate `ActionSuppressionPort`; existing port untouched |
| Timezone: `dismissed_until` compared against `strftime(...,'now')` = UTC | Med×Med | Convert ICT end-of-day → UTC in the service, never in SQL |

## Rollback

Revert the 7 files. Phase 03's schema tolerates the old code only if 03 is also reverted — revert
04 and 03 together.

## Security considerations

- **Confirmed: no role/ownership restriction — any authenticated staff may toggle any party's
  suppressions** (not owner-only, not manager-only). The only guard needed is the same IDOR check
  `screen_customer_360_tasks.py:70,75` (`authz.is_same_party`) already applies to tasks: confirm the
  action/action_type genuinely belongs to the `party_id` in the URL before mutating, rejecting a
  tampered URL — not a permission check on the acting user.
- `user_id` recorded for audit ("bởi ai"), FK-enforced to `crm_app_user`.
- All SQL uses bound parameters — no f-string interpolation of caller input (the existing TTL
  f-string at `:72` stays a module constant, never user input).

## Next steps

Unblocks Phase 06. Runs in parallel with Phase 05 (disjoint files).
