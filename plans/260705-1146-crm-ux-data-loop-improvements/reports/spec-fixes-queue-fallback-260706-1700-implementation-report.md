# AI-5 / AI-6 — Queue fallback hide + M08 stale spec fix

**Status:** DONE
**Scope:** docs + 1 template (`call_cockpit.html`), no `crm/src` Python changes, no `c360_call_cockpit_panel.html` changes.

## AI-5 — hide "Khách kế →" fallback when no queue context

File: `crm/src/adapters/inbound/web/templates/call_cockpit.html:70` (topbar, S14 full-page cockpit).

Before: `{% if not pinned_task_id %}` wrapped both the real-next-party link and the `/customers`
fallback link — so the fallback rendered any time `pinned_task_id` was unset, including
`queue_total == 0` (no queue context at all, e.g. direct URL entry).

After: condition changed to `{% if not pinned_task_id and queue_total and queue_total > 0 %}`
(`call_cockpit.html:70`). This distinguishes two cases per the task brief:
- **No queue at all** (`queue_total == 0`): the whole "Khách kế" control — including the
  `/customers` fallback — no longer renders. Showing a "next customer" link when there was never
  a queue would be misleading.
- **End of a real queue** (`queue_total > 0`, `queue_next_party_id` is `None`): the fallback link
  to `/customers` still renders — this is legitimately "queue finished, browse customers" and is
  a meaningful, non-misleading affordance. Updated its `title` to "Hết hàng đợi hôm nay — quay lại
  danh sách khách hàng" for clarity (was previously the same tooltip as the real-next-party link).

Verified with cockpit test subset (`pytest src/tests -k cockpit`, excluding the pre-existing
broken `test_approach_script_handler.py` collection error unrelated to this change — see AI-2(c)
in progress in a parallel workstream): **35 passed**.

## AI-6 — M08 stale spec paragraph

File: `crm/docs/ui-spec/modals/M08-log-activity-modal.md:265` ("Item 2 — Promote insight" note).

Verified actual behavior before editing:
- `crm/src/composition.py:599` passes `party_insights=sqlite_repos["party"]` into
  `register_activity_routes(...)` — i.e. `party_insights` IS wired (not `None`).
- `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py:235-255`:
  when `promote_insight == "1"` and both `insight_type` / `insight_body` are non-empty, calls
  `party_insights.add_insight(PartyInsight(...))`. The `party_insights is None` branch (log
  warning + skip) is now unreachable in the actual composition root — only a defensive fallback.
- `crm/src/adapters/outbound/sqlite/party_repository.py:214-217` (`SQLitePartyRepository.add_insight`)
  does `INSERT INTO crm_party_insight ...` — a real row is created.

Rewrote the spec paragraph to state: POST handler wires `party_insights`
(`SQLitePartyRepository`, injected via `composition.py`); on promote it inserts a
`crm_party_insight` row (party_id, insight_type, insight_body, insight_confidence, created_at);
wired as of commit `5dce0c37`, no longer a no-op; the "not wired" log-and-skip path is now only a
defensive fallback, not the current runtime path.

## S14 spec update (AI-5 second half)

File: `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md`.

1. Extended the existing A2 implementation note (`:165`) with the hide/fallback distinction above.
2. Added a new note ("A2 scope — full-page cockpit only") clarifying that the `#n/N` queue
   counter and "Khách kế →" control live in `call_cockpit.html` topbar chrome, only rendered on
   the S01 → full-page cockpit entry path (`GET /customers/{id}/call`). The embedded S03 "Gọi" tab
   renders `fragments/c360_call_cockpit_panel.html` directly — no topbar, no queue context, by
   design (a C360 tab visit is not a queue session). Previously undocumented.

## Validation

- `docker compose exec -T crm sh -c "cd /app/crm && python -m pytest src/tests -k cockpit -q"` →
  collection error in `test_approach_script_handler.py` (pre-existing, unrelated
  `wire_approach_script_router` import — belongs to the concurrent approach-script refactor
  workstream, not touched here). Re-ran with `--ignore=src/tests/test_approach_script_handler.py`:
  **35 passed, 0 failed**.
- `docker compose restart crm` — done, container restarted successfully.

## Files touched

- `crm/src/adapters/inbound/web/templates/call_cockpit.html` (topbar queue-nav condition + tooltip)
- `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md` (A2 note + new scope note)
- `crm/docs/ui-spec/modals/M08-log-activity-modal.md` (Item 2 paragraph rewritten)

## Unresolved questions

None.
