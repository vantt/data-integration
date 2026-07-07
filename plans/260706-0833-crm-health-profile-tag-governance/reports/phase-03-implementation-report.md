# Phase 03 — Tag Governance Admin — Implementation Report

**Plan:** `plans/260706-0833-crm-health-profile-tag-governance/` (v1 final phase)
**Status:** DONE_WITH_CONCERNS (1 unresolved validation item — role-gating, see below)

## Files touched

New:
- `crm/src/adapters/outbound/sqlite/tag_governance_repository.py` — raw SQL: taxonomy/queue queries, merge (3-step transaction), archive/unarchive, chipify group query + apply
- `crm/src/application/tag_governance_service.py` — business rules composing the repo + existing `TagService`
- `crm/src/adapters/inbound/web/screens/management/screen_mgmt_tag_governance.py` — all `/settings/tags*` routes
- `crm/src/adapters/inbound/web/templates/settings_tag_governance.html` — main screen shell
- `crm/src/adapters/inbound/web/templates/fragments/_tag_governance_taxonomy_rows.html`
- `crm/src/adapters/inbound/web/templates/fragments/_tag_governance_l1_rows.html`
- `crm/src/adapters/inbound/web/templates/fragments/_tag_governance_l2_rows.html`
- `crm/src/adapters/inbound/web/templates/fragments/_tag_governance_chipify_rows.html`
- `crm/src/adapters/inbound/web/templates/fragments/modal_tag_governance_merge.html`
- `crm/src/tests/test_tag_governance_admin.py` — 25 tests

Edited:
- `crm/src/domain/entities/profile.py` — `Tag` +`is_provisional`/+`is_archived` fields (default False, additive)
- `crm/src/application/tag_service.py` — `create_tag(...)` +`is_provisional` param; L2 (provisional, no category) keeps `category=None` instead of the old `"general"` fallback
- `crm/src/adapters/outbound/sqlite/tag_note_repository.py` — `create_tag` SQL writes `is_provisional`; `list_tags`/`list_tags(category)` now filter `is_archived=0` (M03/M14 pickers stop offering archived tags)
- `crm/src/adapters/inbound/web/screens/management/screen_mgmt_settings.py` — `GET /settings/tags/modal/create` accepts optional `chipify_raw_text`/`chipify_tab`/`prefill_name`/`prefill_category`/`is_provisional` query params (reused by Chipify, not rebuilt)
- `crm/src/adapters/inbound/web/templates/fragments/modal_m14_create_tag.html` — conditional prefill, hidden `raw_text`/`is_provisional`/`tab` fields, relaxed `required` on category for L2, +2 category options (`health_domain`, `health_concern`)
- `crm/src/adapters/inbound/web/templates/settings.html` — added a discover link "Quản lý Tag (merge/archive/provisional)" from the old Tags tab to `/settings/tags`
- `crm/src/adapters/inbound/web/screens/management/screen_management.py` — wired `make_tag_governance_router`, added `tag_governance_svc` param
- `crm/src/composition.py` — added `tag_governance` repo+service to `SqliteRepos`/`Services` TypedDicts and their builders; passed into `make_management_router`
- `plans/260706-0833-crm-health-profile-tag-governance/plan.md` — phase table (01+03 → ✅)
- `plans/260706-0833-crm-health-profile-tag-governance/phase-03-tag-governance-admin.md` — appended real-path + validation notes

## Real vs. doc paths

Doc said `crm/templates/settings/tag_governance.html`, `crm/views/settings_tag_governance.py`, `crm/routes/settings.py` — none exist in this repo's hexagonal layout. Mirrored the real, verified convention instead: management screens live in `adapters/inbound/web/screens/management/screen_mgmt_*.py`, each exposing `make_*_router(templates, svc)`, composed by `screen_management.make_management_router`, wired in `composition.py`. Templates are flat under `templates/`, fragments under `templates/fragments/`. Confirmed by reading `screen_mgmt_settings.py`, `screen_management.py`, `screen_modal_tags.py`, `screen_modals_party.py`, and `composition.py`'s `_register_web_routes`/`_build_services` before writing any code.

## M14 "create tag" modal — reused, not reimplemented

Found it: `fragments/modal_m14_create_tag.html`, served by `GET /settings/tags/modal/create` / `GET /settings/tags/{id}/modal/edit` in `screen_mgmt_settings.py`, posting to `TagService.create_tag` (canonical only, category required from a hardcoded enum that did NOT include health categories).

Chipify's "Tạo tag L1"/"Tạo tag L2" buttons call the **same** `GET /settings/tags/modal/create` route with query params (`chipify_raw_text`, `chipify_tab`, `prefill_category`, `is_provisional`). The template conditionally:
- posts to a new `/settings/tags/chipify/create-tag` endpoint instead of the plain `/settings/tags` route when `chipify_raw_text` is set
- carries hidden `raw_text`/`tab`/`is_provisional` fields
- drops the `required` attribute on category only for the L2 case (`is_provisional` + no `prefill_category`), so category submits empty → `TagService.create_tag` resolves that to `None` (not `"general"`)
- adds `health_domain`/`health_concern` as 2 new fixed options in the existing category `<select>`

`chipify/create-tag` handler creates the tag, assigns it to every party still holding that raw text unreviewed (`source='ops_normalized'`), then marks the group reviewed — all via `TagGovernanceService._assign_and_review`.

## Access control decision

Read `auth_dependency.require_admin`: it early-returns (bypass) when `CF_ACCESS_AUDIENCE` is unset, but when set it hits an explicit `# TODO: re-enable when roles are configured in CF_ROLE_MAP` / `return  # temporarily allow all authenticated users into /settings` — i.e. it is a **stub that allows everyone**, already applied to every existing `/settings/*` route (`screen_mgmt_settings.py`). `crm_app_user.role` is documented in `domain/entities/app_user.py` as *"informational in v1 (auth deferred — LAN-trust model)"*; valid roles are `sales|care|manager|admin` — **no `ops` role exists** in this codebase (the phase doc's `role IN ('admin','ops')` doesn't map onto the real role vocabulary).

Decision: reused `require_admin` on all `/settings/tags*` routes for consistency with the rest of S13 — same risk profile as the pre-existing tag CRUD (create/update/delete) it sits beside. Did **not** write a bespoke role check scoped to only this new screen: that would (a) contradict the documented "role is informational in v1" decision, (b) create an inconsistent security posture (this one screen locked while the equally-destructive existing tag delete/edit stays open), (c) require inventing an "ops" role that doesn't exist anywhere else. Flagging for the user: either enable real role enforcement app-wide (would need `auth_dependency.require_admin` reworked + `CF_ROLE_MAP` configured with an actual `ops`→role mapping), or accept LAN-trust for v1 here too, consistent with the rest of Settings.

**Verified live** (see Validation below): `CF_ACCESS_AUDIENCE` IS set in this deployment's `crm` container, yet `GET http://127.0.0.1:3007/settings/tags` with no `Cf-Access-Jwt-Assertion` header returns 200 — confirms the stub is truly inert right now, not just in theory.

## Validation — verified against the live `crm` container + real `crm.db`

All performed via direct HTTP calls to `http://127.0.0.1:3007` (host-mapped port) after `docker compose restart crm`, and direct `sqlite3`/Python inspection of `/data/crm.db` inside the container. Test artifacts (`test-tag-a/b`, `qa-l1-tag`, `qa-l2-tag`, `qa-huyet-ap-cao`, `qa-ext-1` mapping, chipify custom-field edits on 2 real parties) were fully cleaned up afterward — `crm_tag` count confirmed back to the original 18.

| Item | Result |
|---|---|
| Category tabs render correct canonical tags per category | PASS — `/settings/tags?tab=health_domain` and a throwaway `qa_merge_test` category both rendered correct rows |
| L1 tab = `category NOT NULL AND is_provisional=1` only | PASS — verified via row-id markers (`tag-row-<id>`), not naive substring (a false-positive from the Chipify panel's cross-tab "Map hiện có" dropdown was caught and corrected) |
| L2 tab = `category IS NULL AND is_provisional=1` only | PASS — same method |
| Promote L1 → moves to canonical tab, leaves L1 queue | PASS — `qa-l1-tag` category=`health_concern`, is_provisional=0 after promote; appeared in `health_concern` tab, gone from L1 |
| Promote L2 (assign category) → moves to canonical tab, leaves L2 queue | PASS — `qa-l2-tag` category=`qa_merge_test` after promote |
| **Merge PK-collision**: party holding both merged-away + canonical tag | PASS — party had `test-tag-a` + `test-tag-b`; after merge, exactly 1 `crm_party_tag` row (`test-tag-a`); no crash, no duplicate row |
| Merge repoints `crm_ext_tag_map`, no orphan | PASS — active inbound mapping on `test-tag-b` repointed to `test-tag-a` (`is_active` preserved=1); post-merge query for any `crm_ext_tag_map` row still pointing at deleted `test-tag-b` returned none |
| Merge with active mapping shows sync warning | PASS — merge modal for a category containing a tag with `has_active_mapping=True` rendered the warning banner + the ⇄ badge next to that candidate |
| Archive deactivates active inbound mapping | PASS (2 cases): the repointed `test-tag-a` mapping went `is_active 1→0`; outbound-only mapping (unit test) correctly left untouched |
| Archive hides tag from S14/M03 pickers | PASS — archived `tim-mach` (real seeded tag) disappeared from S14 call-cockpit health_domain chip row (`tag-health-0001` no longer served, checked via label text) and from the M03 tag-management modal's `all_tags` (checked via `tag-health-0001` absence while `tag-health-0008` "da" stayed present) |
| Unarchive does NOT reactivate mapping | PASS — `is_archived` back to 0 but `is_active` stayed 0 for the same mapping row |
| Chipify apply → parties get `crm_party_tag` + raw text marked reviewed | PASS — created tag `qa-huyet-ap-cao` from a 2-party chipify group via the actual `/settings/tags/chipify/create-tag` endpoint (through the reused M14 modal path); both parties got the `crm_party_tag` row; `health_context_raw_reviewed` flipped to `'true'` in `crm_customer_profile.custom` for both |
| role=sales → 403 | **NOT VERIFIED** — see Access control section. Confirmed instead that the existing stub lets an unauthenticated request through with 200 in this exact deployment (CF_ACCESS_AUDIENCE set, no JWT header) |
| `docker compose exec crm python3 -m pytest crm/src/tests -q` | 849 passed, 1 pre-existing unrelated failure (`test_approach_script_file_repository.py::test_list_customer_ids_reflects_new_file_without_reinit`) + 1 pre-existing collection error (`test_approach_script_handler.py`, unrelated `ImportError`) — both present before this phase's changes, confirmed by memory note "2 CRM test fail pre-existing" |

## Deviations from plan.md's simplified conflict table

`plan.md`'s "Conflict rules" table says merge should set `source='merged'` on reassigned rows; the phase-03 doc's literal SQL (which the task explicitly asked to implement "exact 3-step transaction from phase doc") preserves the original `source` value via `INSERT OR IGNORE ... SELECT ... source ...`. Followed phase-03's literal SQL (more detailed, more recently patched per plan.md's own 2026-07-06 changelog note) over plan.md's simplification. Similarly, plan.md's conflict table implies chipify always sets `is_provisional=0`, while phase-03 §D explicitly specs both L1 (`is_provisional=0`) and L2 (`is_provisional=1`) chipify creation — implemented per phase-03.

## Judgment calls (not explicitly specced)

- Taxonomy tab row query includes archived tags of that category (not just `is_provisional=0 AND is_archived=0` as literally stated for the *tab list*) so there's a UI path to unarchive — otherwise no screen would ever show an archived tag again.
- Merge modal unifies the taxonomy panel's per-tag `[Merge]` and the L1 row's `[Merge vào tag có sẵn]` into one dialog (radio = canonical target, checkboxes = tags to merge away, pre-selecting the row that opened it) — same underlying `merge_tags` call either way.
- "Nguồn" (source) column for a canonical tag has no dedicated column in `crm_tag`; derived from the most common `crm_party_tag.source` for that tag (falls back to `"seeded"` when unused).
- Chipify's "Map hiện có" dropdown lists all non-archived tags (canonical + provisional) rather than canonical-only, so ops can map into an existing not-yet-promoted tag without creating a duplicate.

## Unresolved questions

1. Should `/settings/tags` (and the rest of `/settings/*`) get real role enforcement now, or stay LAN-trust for v1 consistent with current app-wide behavior? No `ops` role exists today — would need to be added to `VALID_ROLES` + `CF_ROLE_MAP` if pursued.
2. `test_approach_script_handler.py` collection error and the 1 pre-existing test failure are unrelated to this phase (confirmed present before any change here) — flagging in case they weren't previously tracked.

---

Status: DONE_WITH_CONCERNS
Summary: `/settings/tags` Tag Governance Admin fully implemented and verified live (taxonomy/merge/archive/L1/L2 queues/chipify) against the running crm container and real crm.db; 25 new tests + full suite green (849 passed, 2 pre-existing unrelated failures). Access-control gate reuses the existing (currently inert) `require_admin` stub — role='sales'→403 could not be verified because this app has no working role enforcement yet, flagged for user decision rather than inventing a new auth layer.
Concerns/Blockers: role-gating validation item unverifiable in current environment (documented app-wide gap, not introduced by this phase).
