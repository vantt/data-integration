# Phase 02 Implementation Report — S14 Health Collect + Inline Tag Assign

Plan: `plans/260706-0833-crm-health-profile-tag-governance/phase-02-s14-health-collect.md`
Date: 2026-07-07

## Real files touched (doc's guessed paths were stale — actual hexagonal-architecture paths below)

Domain / application:
- `crm/src/domain/entities/profile.py` — `PartyTag.source: str = "crm_user"` field added
- `crm/src/domain/ports/tag_repository.py` — protocol: `list_tags_by_category_ordered_by_usage`, `attach_tag` docstring
- `crm/src/application/tag_service.py` — `attach_tag(..., source="crm_user")`, `list_tags_by_category_ordered_by_usage` delegate
- `crm/src/application/health_domain_collect.py` — **new**, shared gap-detection helper used by both cockpit render paths

Adapters — outbound:
- `crm/src/adapters/outbound/sqlite/tag_note_repository.py` — `_SQL_ATTACH` now writes `source` explicitly; new `_SQL_LIST_BY_CATEGORY_ORDERED_BY_USAGE` (LEFT JOIN + COUNT + `is_archived=0` filter) + repo method

Adapters — inbound web:
- `crm/src/composition.py` — `_ProfileTagCFComposite.attach_tag(source=...)` passthrough + `list_tags_by_category_ordered_by_usage` delegate; `tags=services["tag"]` wired into `make_customer_360_router(...)`
- `crm/src/adapters/inbound/web/screens/modals/screen_modal_shared.py` — `ProfileSvc` protocol: `attach_tag(source=...)`, `get_tag`, `list_tags_by_category_ordered_by_usage`
- `crm/src/adapters/inbound/web/screens/modals/screen_modal_tags.py` — **new endpoint** `POST /customers/{party_id}/tags/inline` (hard whitelist `INLINE_ALLOWED_CATEGORIES = {"health_domain","health_concern"}`, 400 before any lookup/attach if outside)
- `crm/src/adapters/inbound/web/screens/modals/screen_modal_contact.py` — `custom-field-inline` (Phase 06 endpoint, reused not duplicated): whitelist `+ "health_context_raw"`, server-side 200-char cap, per-field `kind` (custom_select vs custom_text)
- `crm/src/adapters/inbound/web/screens/customer360/screen_call_cockpit.py` — `tags=None` param, calls `load_health_domain_collect_context()`, merges into template context
- `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_panels.py` — same, for the embedded S03 `panels/call_cockpit` route
- `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360.py` — `tags=None` param forwarded to both sub-registrations

Templates / static:
- `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` — 2 new gap checks in `collect_rows` builder; `tag_multiselect` include branch; generic text-row `maxlength`; JS `s14CollectSave` extended for `custom_text`; new `s14TagChipToggle` / `s14TagMultiSave` JS
- `crm/src/adapters/inbound/web/templates/fragments/_s14_collect_row.html` — variant B condition broadened to `('custom_select','custom_text')`; new variant C (`tag_multiselect`, unsaved chips vs saved done-row)
- `crm/src/adapters/inbound/web/static/ds-extra.css` — `.chipset` / `.chip-pill` / `.chip-pill--on` (mirrors `.radio-pill`)

Docs:
- `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md` — new "Implementation Notes (Phase 02 — 260706-0833 ...)" section

Tests (new):
- `crm/src/tests/test_health_domain_collect_and_tags_inline.py` — 21 tests: helper unit tests, SQLite repo ordering/archived-filter/explicit-source, cockpit gap rendering (shown/hidden/no-tags-svc/skin_type-unaffected), `/tags/inline` whitelist+attach+no-match-400, `/custom-field-inline` health_context_raw save/maxlength/skin_type-regression/unknown-key-still-400.

## Key design decisions (resolving doc ambiguity)

1. **Gap detection lives in Jinja, not a Python `_build_collect_gaps()`** — the existing `skin_type` precedent computes `collect_rows` inline in `c360_call_cockpit_panel.html` from context vars (`party_custom`, identities, etc). I followed suit: `load_health_domain_collect_context()` (Python) supplies `has_health_domain_tag` / `health_domain_options`; the Jinja template still owns the `collect_rows.append(...)` gap logic, same as skin_type.
2. **`tags_svc=None` degrades to "row hidden"** (not "row shown with empty options") — avoids rendering a non-functional chip picker if a future composition root forgets to wire the tag service.
3. **`tag_names` transport**: FastAPI `List[str] = Form(default=[])` (same convention already used by M03's `POST /customers/{id}/tags`), submitted from JS via `htmx.ajax(..., {values: {tag_names: [...], category}})` — htmx's object→FormData converter appends one entry per array item (verified in bundled `htmx.min.js`), so no JSON body / no new client-side serialization needed.
4. **`health_context_raw` reuses variant B** (`custom_select`/`custom_text` share the same "if row.current → done pill" markup) rather than inventing a 3rd fragment variant — its *unsaved* state is the pre-existing generic text-input row in `c360_call_cockpit_panel.html` (same markup used by `zalo`/`email`/`core`), not `_s14_collect_row.html` at all.
5. **`source='crm_user'` written explicitly** in `_SQL_ATTACH` (not relying on the `DEFAULT 'crm_user'` on `crm_party_tag.source`) per task instructions — `PartyTag.source` field added, `TagService.attach_tag` and composite `attach_tag` both thread it through.

## Verification (live, against running `crm` container + real `/data/crm.db`)

1. `docker compose restart crm` → healthy, no import/template errors (`docker logs crm --tail 30` clean, `/healthz` 200).
2. `GET /customers/{party_id}/call` for a party with 0 health_domain tags + empty `health_context_raw`: both rows render (`s14-cr-health_domain` present, all 8 chips incl. "Tim mạch"/"Da"; `s14-crow-health_context_raw` present).
3. `POST /customers/{id}/tags/inline` `{tag_names: [tim-mach, ho-hap], category: health_domain}` → `200`, fragment shows `✓ Hô hấp, Tim mạch`; DB: `crm_party_tag` now has 2 rows for that party, `source='crm_user'` on both. Re-fetch `/call` → `health_domain` row gone (gap cleared).
4. `POST /tags/inline` `{tag_names:[vip], category: risk}` → `400 "Category không được phép qua inline: 'risk'"`; DB: 0 rows for that party (confirmed via query).
5. `POST /customers/{id}/custom-field-inline` `{field_key: health_context_raw, value: "huyết áp cao, hay mệt"}` → `200`, pill shown, toast; DB `crm_customer_profile.custom` = `{"health_context_raw": "huyết áp cao, hay mệt"}`; re-fetch `/call` → row gone. 201-char value → `400`.
6. `skin_type` regression: `POST /custom-field-inline {field_key: skin_type, value: "khô"}` → `200`, same pill+toast markup as before, byte-identical handler path (only the whitelist set and the `_FIELD_META` tuple shape changed structurally, `skin_type`'s own entry is unchanged in content).
7. `docker compose exec crm python3 -m pytest crm/src/tests -k "call_cockpit or s14 or collect or skin_type or tag or health" -q --ignore=crm/src/tests/test_approach_script_handler.py` → **27 passed**.
8. Full suite: `docker compose exec crm python3 -m pytest crm/src/tests -q --ignore=crm/src/tests/test_approach_script_handler.py` → **817 passed, 1 failed** (`test_approach_script_file_repository.py::test_list_customer_ids_reflects_new_file_without_reinit` — file-mtime caching bug in an unrelated repository, pre-existing per git status showing that file already modified before this session; confirmed **not** touched by any Phase 02 edit). `test_approach_script_handler.py` also pre-existing collection error (`ImportError: wire_approach_script_router` — unrelated module, not touched). **0 new failures introduced.**

## Scope discipline

- Did not build Tag Governance Admin screen (Phase 03).
- Did not touch `skin_type`'s own whitelist entry content, its `_FIELD_META` values, or its Jinja branch semantics — only broadened the *condition* that routes into the shared branch (`'custom_select'` → `('custom_select','custom_text')`), which is a superset, not a behavior change for existing `custom_select` rows.
- No commits made (per instructions) — working tree left for review.

## Unresolved questions

- None blocking. Minor note: the embedded S03 panel path (`screen_customer_360_panels.py`'s `call_cockpit` branch) never parsed `party_custom` even before this phase (pre-existing gap from Phase 06 — `skin_type`/`preferred_contact` rows always show there regardless of saved value). I left this untouched/consistent — `health_context_raw` inherits the identical pre-existing quirk in that one code path, verified via the full-screen `/customers/{id}/call` route instead (which does parse `party_custom` correctly and is what the existing `skin_type` tests + my new tests exercise).
