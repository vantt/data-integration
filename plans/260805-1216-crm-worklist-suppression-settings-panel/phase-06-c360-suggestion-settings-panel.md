# Phase 06 — Customer 360 panel P07 "Cài đặt gợi ý"

**Priority:** P2 · **Status:** pending · **Effort:** 3h · **Blocked by:** Phase 02, Phase 04
**File ownership:**
`crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_suggestion_settings.py` (new),
`crm/src/adapters/inbound/web/templates/fragments/c360_suggestion_settings_panel.html` (new),
`crm/src/adapters/inbound/web/screens/customer360/screen_customer_360.py`,
`crm/src/adapters/inbound/web/templates/customer_360.html`,
`crm/src/composition.py`,
`crm/src/adapters/inbound/web/templates/dismissed_actions.html`.

## Context — verified patterns

- **Framework:** FastAPI. Router factory `make_customer_360_router(...)` at
  `screen_customer_360.py:127`, mounted with no prefix at `composition.py:613`.
- **Tab list** is a hardcoded Jinja tuple list at `customer_360.html:63-70`; each button calls
  `dvActivateTab(this, '/customers/{{ party.party_id }}/panels/{{ tab_key }}')` (`:78`).
- **Panel dispatch:** `screen_customer_360_panels.py:162` —
  `@router.get("/customers/{party_id}/panels/{panel}", response_class=HTMLResponse)` with an
  `if panel == "...":` chain at `:167, 169, 185, 197, 211, 224`.
- **Sub-route registration:** `register_panel_routes(router, templates, *, ...)` signature at
  `screen_customer_360_panels.py:32-54`, called from `screen_customer_360.py:284-304`.
- **Acting user:** `getattr(getattr(request.state, "current_user", None), "user_id", "")` —
  pattern at `screen_customer_360_panels.py:119`. Set by `CFAccessMiddleware`.
- **CSRF:** header-based `CSRFGuardMiddleware` (`csrf_guard.py:34,48-60`), log-only unless
  `CRM_CSRF_ENFORCE=true`. No form tokens anywhere. Do not invent one.
- **Closest analog** for "rows + quick actions + a date": tasks panel
  (`screen_customer_360_tasks.py:31-164` + `fragments/c360_tasks_panel.html`) with the postpone
  overlay `fragments/overlay_o03_postpone_task.html:13-59` (`NGÀY`/`GIỜ` fields, `hx-patch`,
  re-renders the panel).
- **i18n:** none. Vietnamese is hardcoded in templates and in Python error strings
  (`screen_customer_360_tasks.py:70,75`). Follow suit.
- **Surface IDs:** `crm/docs/ui-spec/00-overview.md` lists P01-P06 → this is **P07**. Fragment banner
  `{# @surface P07 · ... #}` on line 1 and `data-surface="P07"` on the outermost element
  (`crm/AGENTS.md` §Surface ID convention, Python-port rules 1-3).

## Requirements

**Functional**
1. New tab "Cài đặt gợi ý" appended to the C360 tabbar, `tab_key = "suggestion_settings"`.
2. Panel lists every catalog row grouped by `scenario_group`, group headers in Vietnamese.
3. Each row shows: label (`description_vi`), grain badge ("Theo khách" / "Theo sản phẩm"),
   state (Đang bật / Đã tắt tới `dd/mm/yyyy` / Đã hết hạn), and who set it.
4. Toggle OFF: preset chips 1 tuần / 1 tháng / 3 tháng + a custom `<input type="date">`. Submits
   `POST /customers/{party_id}/suggestion-settings/suppress`.
5. Toggle ON: `POST /customers/{party_id}/suggestion-settings/unsuppress`.
6. Rows created by the old quick-dismiss appear here and their end date is editable — same table, so
   this is automatic; verify with a test rather than special-casing.
7. Globally-disabled types (`enabled = 0`) render greyed + non-interactive with a tooltip
   "Loại gợi ý này đang tắt toàn hệ thống".
8. Empty catalog (Phase 02 not yet synced) → explicit empty state
   "Danh mục gợi ý chưa được đồng bộ từ kho dữ liệu." Never a hardcoded fallback list.
9. A short explainer at the top distinguishing this panel from the per-card "Bỏ qua" and from
   "Đừng gọi nữa" — this is the whole point of the feature.

**Non-functional**
10. Both mutation routes re-render the full panel fragment (`hx-target` the panel root,
    `hx-swap="outerHTML"`), matching the tasks-panel round trip.
11. Screen module declares its own narrow `typing.Protocol` for the injected service
    (`crm/AGENTS.md` §Screen boundaries) — no `Any`.
12. Screen module stays under 200 lines; template may exceed (Markdown/HTML exempt from the
    200-line rule, but keep it tidy).
13. No new modal ⇒ no new M-id. Date input is inline in the row.

## Architecture / data flow

```
GET  /customers/{pid}/panels/suggestion_settings
   → screen_customer_360_panels.py dispatch  → render_suggestion_settings_panel()
   → SuggestionSettingsService.get_settings(pid)
       → catalog (cache.wh_action_scenario_registry) × dismissals (crm_action_dismissal)
   → fragments/c360_suggestion_settings_panel.html   [data-surface="P07"]

POST /customers/{pid}/suggestion-settings/suppress
   Form: action_type, source_mart, until_date (YYYY-MM-DD)
   → user_id from request.state.current_user
   → service.suppress(...)  [validates against catalog, converts ICT EOD → UTC]
   → re-render panel

POST /customers/{pid}/suggestion-settings/unsuppress
   Form: action_type, source_mart
   → service.unsuppress(...) → re-render panel
```

## Related code files

**Create**
- `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_suggestion_settings.py`
- `crm/src/adapters/inbound/web/templates/fragments/c360_suggestion_settings_panel.html`
- `crm/docs/ui-spec/panels/P07-suggestion-settings-panel.md`

**Modify**
- `crm/src/adapters/inbound/web/templates/customer_360.html` — add the tab tuple at `:63-70`.
- `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360.py` — call the new
  `register_suggestion_settings_routes(...)` next to the existing `register_panel_routes(...)` at
  `:284-304`, and thread the new service param through `make_customer_360_router`.
- `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_panels.py` — add the
  `if panel == "suggestion_settings":` branch delegating to the new module's render helper.
  Alternative: register a dedicated `GET .../panels/suggestion_settings` route in the new module —
  FastAPI matches the literal path before the `{panel}` catch-all only if registered first, which is
  fragile. **Use the dispatch branch.**
- `crm/src/composition.py` — instantiate `SQLiteActionCatalogRepository(conn)` in `sqlite_repos`
  (near `:245`), build `SuggestionSettingsService`, pass to `make_customer_360_router` (`:613-635`).
- `crm/src/adapters/inbound/web/templates/dismissed_actions.html:31` — copy currently reads
  "Mọi dismiss đã hết hạn 30 ngày…"; now the end date is staff-chosen. Reword and add a
  `source_mart` column to the table (`:47-60`).
- `crm/docs/ui-spec/00-overview.md` — add P07 to the panel index.

**Delete** — none.

## Implementation steps

1. New screen module:
   ```python
   class SuggestionSettingsSvc(Protocol):
       def get_settings(self, party_id: str) -> list: ...
       def suppress(self, party_id: str, action_type: str, source_mart: str,
                    until_date_ict: str, user_id: str) -> None: ...
       def unsuppress(self, party_id: str, action_type: str, source_mart: str) -> None: ...

   def register_suggestion_settings_routes(router, templates, *, settings_svc: SuggestionSettingsSvc):
       async def render_panel(request, party_id) -> Response: ...
       @router.post("/customers/{party_id}/suggestion-settings/suppress", response_class=HTMLResponse)
       async def suppress(...): ...
       @router.post("/customers/{party_id}/suggestion-settings/unsuppress", response_class=HTMLResponse)
       async def unsuppress(...): ...
       return render_panel   # handed to the panel dispatcher
   ```
   Catch `ValueError` from the service → `HTMLResponse(status_code=400)` with a Vietnamese message,
   mirroring `screen_customer_360_tasks.py:70,75`.
2. Template: banner line 1 `{# @surface P07 · Cài đặt gợi ý · plans/260805-1216-... #}`, root
   `<section class="panel" data-surface="P07" id="p07-suggestion-settings">`. Reuse the existing
   panel/table/chip CSS classes from `c360_tasks_panel.html` — do not add new CSS unless
   `crm/docs/ui-conventions.md` has no suitable class.
3. Tab tuple to add at `customer_360.html:63-70`:
   `("suggestion_settings", "Cài đặt gợi ý", "P07"),` — place last, after `call_cockpit`.
4. Wire `composition.py`. Follow §"No duplicate wiring": one `SuggestionSettingsService` instance.
5. Write P07 ui-spec doc following the shape of `crm/docs/ui-spec/panels/P04-tasks-panel.md`.
6. Manual pass: open a customer with an active `REORDER_NUDGE` at both grains, turn off the
   customer-level one for 1 tháng, reload the worklist, confirm only the SKU row remains.

## Test matrix (route-level — this phase)

| # | Case | Assert |
|---|---|---|
| R1 | GET panel, catalog synced, no dismissals | 200, all 13 rows, all "Đang bật", groups present |
| R2 | GET panel, catalog empty | 200, empty-state text, no crash |
| R3 | POST suppress, valid | 200, panel shows "Đã tắt tới", DB row with the right `source_mart` |
| R4 | POST suppress, unknown action_type | 400, Vietnamese error, no DB row |
| R5 | POST suppress, globally-disabled type | 400 |
| R6 | POST suppress, past date | 400 |
| R7 | POST unsuppress | 200, row deleted |
| R8 | Row pre-created by quick-dismiss | appears in the panel; POST suppress overwrites its end date |
| R9 | Unauthenticated / no `current_user` | `user_id` falls back to `""`; row still written with NULL owner and "Hệ thống" display — matches `list_active_dismissals` fallback (`action_state_repository.py:153`) |

## Todo list

- [x] Screen module + Protocol
- [x] Panel fragment with `data-surface="P07"` + banner
- [x] Tab tuple in `customer_360.html`
- [x] Dispatch branch in `screen_customer_360_panels.py`
- [x] `composition.py` wiring (single instance)
- [x] `dismissed_actions.html` copy fix + `source_mart` column
- [x] `P07-suggestion-settings-panel.md` + `00-overview.md` index — `ui-spec validate` 0 warnings
- [x] R1-R9 green (9/9, `test_c360_suggestion_settings_routes.py`)
- [x] End-to-end verified against real prod-like data via TestClient (GET panel, suppress, invalid-type 400, unsuppress)
- [ ] Manual verification of the two-grain scenario

## Success criteria

- Tab renders, all 13 catalog rows grouped by `scenario_group`.
- Turning off customer-level `REORDER_NUDGE` leaves the SKU-level one firing (manual + Phase 07 test).
- Quick-dismiss rows are visible and editable here.
- `GIFT_TO_PURCHASE` greyed, cannot be toggled.
- Panel module < 200 lines; no `Any`-typed service params.

## Risk assessment

| Risk | L×I | Mitigation |
|---|---|---|
| Staff read the panel as "customer will never be contacted" and stop using "Đừng gọi nữa" | Med×High | Requirement 9's explainer; do NOT show a "tắt tất cả" master switch — that is what `do_not_contact` is for |
| Panel implies the C360 reason rail will also hide the suggestion — it will not (D5) | Med×Med | Explainer wording scopes the effect to "danh sách việc cần làm" (worklist), not the customer's insight panel. Flagged as an open question |
| `{panel}` catch-all route ordering | Med×Med | Use the dispatch branch, not a competing literal route |
| Date input timezone drift (browser local vs ICT) | Med×Med | `<input type="date">` submits a bare date string; the service does the ICT→UTC conversion (Phase 04 req 11). Never send a datetime from the browser |
| Adding a 8th tab crowds the tabbar | Low×Low | Accepted; desktop-first, ~10 users |
| `composition.py` double-wiring the service | Low×Med | `crm/AGENTS.md` §No duplicate wiring; one instance in `services` dict |

## Rollback

Remove the tab tuple (feature invisible), then revert the rest. The repository/schema layers stay —
no data loss, quick-dismiss keeps working.

## Security considerations

- Authorisation: verify the acting user may modify this party before mutating. Check what the tasks
  panel enforces (`screen_customer_360_tasks.py:70,75`) and apply the same rule; if it enforces
  nothing, match the existing posture rather than inventing a new one in this phase — but record it
  as an open question.
- IDOR: `party_id` comes from the path. The service writes only rows keyed on that `party_id`; there
  is no `action_id` to cross-check (that was the point). Ensure `party_id` is validated to exist
  before writing, so a typo cannot create rows for a nonexistent party (the FK to `crm_party` already
  enforces this — confirm the error surfaces as 400, not 500).
- CSRF: header-based middleware already covers POST. No token needed.

## Next steps

Feeds Phase 07 (integration + docs).
