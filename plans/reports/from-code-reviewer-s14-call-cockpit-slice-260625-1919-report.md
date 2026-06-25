# Code Review Report — S14 Call Cockpit Vertical Slice

**Commit:** e45cb45  
**Date:** 2026-06-25  
**Reviewer:** code-reviewer agent

---

## Scope

| Area | Files |
|---|---|
| Domain | `crm/src/domain/entities/approach_script.py`, `crm/src/domain/ports/approach_script_repository.py` |
| Outbound adapter | `crm/src/adapters/outbound/file/approach_script_file_repository.py` |
| Inbound HTTP | `crm/src/adapters/inbound/http/approach_script_handler.py` |
| Composition | `crm/src/composition.py` (approach-script wiring block) |
| Loader script | `scripts/load_approach_scripts.py` |
| Tests | `crm/src/tests/test_approach_script_file_repository.py`, `crm/src/tests/test_approach_script_handler.py` |
| UI glue | `crm/src/adapters/inbound/web/screen_customer_360.py` (`call_cockpit` branch) |
| Templates | `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` |
| CSS | `crm/src/adapters/inbound/web/static/ds-extra.css` |
| Shell integration | `crm/src/adapters/inbound/web/templates/customer_360.html` |

---

## Overall Assessment

Backend is solid — hexagonal layering, graceful-empty, and error handling are all correct. The integration seam between backend entity and UI dict is tight. The critical issues are concentrated in the `screen_customer_360.py` glue layer written by the third (glue) author: a wrong `../` count that silently breaks the STOP-gate demo fixture in all environments, and a template crash path on malformed-but-valid JSON (missing `approach` key). No XSS risk, no real path traversal into user-controlled paths. Auth is deferred at LAN-trust, consistent with all sibling endpoints.

---

## Findings Table

| # | Severity | File : Line | Issue | Recommended Fix |
|---|---|---|---|---|
| F1 | HIGH | `screen_customer_360.py:364-367` | `?fixture=stop` path uses 7x `..` from `dirname(__file__)` but needs only 5x. Resolves to `D:\Vantt\plans\...` on host and `/plans/...` in container — both wrong. `plans/` is also NOT mounted in the CRM container. Exception is caught silently; STOP-gate demo always renders ST-CALL-NO-SCRIPT empty state instead. | Use 5x `..` (counted: `web → inbound → adapters → src → crm → data-integration`). Alternatively, seed via env var pointing to a pre-loaded fixture file in `/data/`, which is mounted. |
| F2 | HIGH | `c360_call_cockpit_panel.html:40-41` | If `script` is a truthy dict but has no `approach` key (valid JSON, structurally partial), Jinja2 raises `UndefinedError` → 500. `FileApproachScriptRepository.from_json` handles missing `approach` gracefully at entity level (defaults `recommended=True`), but `script_dict = scr.data` (the raw dict) is passed to the template unguarded. Any LLM-generated file that omits the `approach` block crashes the panel. | Add a guard before the template renders: in screen_customer_360.py, after `scr.data`, check `if "approach" not in scr.data: treat as no-script`. OR add `{% if ap is defined and ap is not none %}` in the template before line 41. Simplest: validate in the repo/entity layer that `approach` key exists before allowing `data` to propagate. |
| F3 | MEDIUM | `c360_call_cockpit_panel.html:19-23` | Stale TODO comment says "replace fixture load with real repository call". The real repository is already wired in screen_customer_360.py (lines 378-388); the fixture only applies to `?fixture=stop`. Comment is misleading and will confuse the next developer. | Remove or rewrite: "NOTE: `?fixture=stop` forces STOP-state demo via plans/ baseline; normal path already uses real FileApproachScriptRepository." |
| F4 | MEDIUM | `screen_customer_360.py:389-392` | `party=party360` is passed to the template context, but the template never uses `party.*` — it only uses `party_id`. This is a dead variable; `party360` can be `None` if `_load_base` returns `(None, [])` for an invalid `party_id`, but this causes no crash because the template never dereferences it. Still misleading and wastes a DB round-trip on stale party_ids. | Remove `party360, ids = _load_base(party_id)` call and replace with `_, ids = _load_base(party_id)` (same as the `orders` panel pattern). Drop `party=party360` from template context. |
| F5 | MEDIUM | `scripts/load_approach_scripts.py:49` | Loader's `_default_dest()` reads `CRM_DB_PATH` env var but `docker-compose.yml` sets `CRM_DATA_DIR` (not `CRM_DB_PATH`). In container, `CRM_DB_PATH` is unset, so the loader falls through to the `/data/approach_scripts` Docker fallback — which happens to match. But this is accidental alignment; a future rename of env vars will silently send files to the wrong directory with no error. | Change line 49 to read `CRM_DATA_DIR` instead of `CRM_DB_PATH`, matching `config.py`'s `_data_dir()`. |
| F6 | LOW | `c360_call_cockpit_panel.html:329-330` | `ap.opening_message` and `ap.fallback_message` are baked into inline JS as `| tojson`. Jinja2's `tojson` filter correctly escapes `<>/&` to `\uXXXX` sequences, so XSS is not achievable via these fields. Confirmed safe. | No action needed. Document as intentional in a comment (comment on line 328 already says "safe, no eval"). |
| F7 | LOW | `test_approach_script_handler.py:77-78` | Tests manually reset module-level `_party_repo`/`_approach_repo` globals to `None` before each test. This is fragile — test isolation depends on side-effect reset. If a test in another file imports and wires the handler, state bleeds. | Use `importlib.reload(approach_script_handler)` before each test, or refactor handler to use FastAPI `Depends()` injection (factory pattern like `make_dedup_router` siblings). |
| F8 | LOW | `test_approach_script_handler.py` | No test for `recommended=False` script (STOP meta path via API). No test for `list_identities` exception (500). No test for all-non-numeric sapo_customer values (falls through to 404). | Add 3 test cases: STOP meta returned correctly in 200 body; identity lookup 500; all-invalid identity values → 404. |
| F9 | LOW | `approach_script_handler.py:49` | `party_id` route parameter is typed `str` (not `int`), consistent with other handlers. This is correct — party IDs are UUIDs. No issue. | Confirmed correct. No action. |

---

## Security Checklist Results

| Check | Verdict |
|---|---|
| Path traversal via `customer_id` in `FileApproachScriptRepository` | SAFE — `customer_id` is cast to `int` before use; `f"{customer_id}.json"` produces only digits, no path separators |
| Path traversal via `?fixture=stop` | NOT a user-controllable path — fixture path is hardcoded, only `fixture=stop` string is checked from user; no user-supplied path segment. Risk: fixture silently fails (F1 above), not a traversal attack |
| XSS: `opening_message`, `talking_points`, `objection_handling`, `do_not` rendered in HTML | SAFE — `autoescape=True` in Jinja2 environment (confirmed in `templating.py:34`); no `|safe` filter in template; `| tojson` uses unicode escapes for `<>/&` |
| XSS: `data-obj-q`/`data-obj-a` HTML attributes | SAFE — autoescape encodes these; JS reads via `getAttribute()` → plain text |
| Auth on `GET /api/parties/{id}/approach-script` | Deferred (LAN-trust) — consistent with all `GET /api/parties/*` siblings (`insight_handler` same comment). `auth_dependency.py` explicitly covers mutation routes only. No regression. |
| PII in `script.data` response body | Script exposes LLM-derived customer behavioral analysis; no raw PII (phone/email) in the `data` dict per observed JSON shape. LAN-only currently adequate. |

---

## Integration Seam Verification

**party_id → customer_id resolution**

`screen_customer_360.py` uses `_sapo_customer_id(ids)` (line 359-361) which mirrors the same helper used by `insight` and `orders` panels (lines 291-295, 315-321). Pattern is consistent.

**`app.state.approach_repo` access**

`composition.py` line 212: `app.state.approach_repo = approach_repo` is always set (not conditional, not Optional). `screen_customer_360.py` line 378 uses `getattr(request.app.state, "approach_repo", None)` with None-check guard. If somehow unset, renders ST-CALL-NO-SCRIPT. Correct.

**Backend entity → template dict contract**

Handler returns `{"script": script.data, "meta": {...}}`. Web glue (screen_customer_360.py line 382-386) uses the same shape: `script_dict = scr.data`, `meta_dict = {"recommended": scr.recommended, ...}`. Template comment on lines 3-8 documents the contract. The only mismatch: template expects `meta.refreshed_at` as a UTC ISO-8601 Z-string and passes it to `format_datetime_ict` which converts to ICT display ("25/06/2026 19:00 ICT"). The `refreshed_at` field in the entity is already UTC Z (line 46 of file repo). R6 ICT display requirement is met.

**R14 STOP gate**

`{% set is_stop = (ap.recommended == false) %}` — when `ap.recommended` is Python `False`, this correctly evaluates to `True`. When missing: Jinja2 returns `Undefined`, `Undefined == false` is `False` → safe (no false STOP). Tested manually. The `{% if is_stop %}` block hides talk-track, talking-points, objections, and outcome bar. `reason_if_not_recommended` and `data_gaps` shown only in STOP state. Gate logic is correct as implemented.

---

## Must-Fix Before Production

1. **F1 (HIGH)** — `?fixture=stop` traversal count wrong and plans/ not mounted: fix `..` count from 7 to 5, or move STOP-gate fixture to `/data/` which IS mounted. Without this the STOP-gate demo is silently broken in all environments.

2. **F2 (HIGH)** — Template 500 on valid JSON missing `approach` key. Add one guard in the web glue (after `scr = approach_repo.get_by_customer_id(customer_id)`, before assigning `script_dict`) to treat `approach`-less dicts as no-script, or validate in entity `from_json`.

3. **F5 (MEDIUM)** — Loader reads wrong env var (`CRM_DB_PATH` vs `CRM_DATA_DIR`). Currently works by accident via Docker fallback. Fix before adding a second environment that sets only one of them.

---

## Positive Observations

- Hexagonal layering clean: domain entity, port protocol, file adapter, HTTP handler, composition root are all separate and have no circular imports.
- `FileApproachScriptRepository` handles all filesystem error paths (missing file, stat failure, JSON parse failure) returning `None` with structured warning logs. No exception propagates to caller.
- `from_json` default-True for missing `recommended` is safe and logged at DEBUG.
- `refreshed_at` derives from file `mtime` with correct UTC-Z format; `format_datetime_ict` converts it to ICT on display — R6 compliant.
- Test location convention matches repo (`crm/src/tests/`). `recommended=False` path is covered in file-repo tests (F8 gap is handler test only).
- CSS uses only `s14-*` prefixed classes or existing DS tokens (`var(--*)`). No invented classes from unknown design vocabulary.
- Stale-badge JS (>24h) reads the baked `refreshed_at` timestamp client-side — no extra request needed.
- `load_approach_scripts.py` is idempotent and handles filename-vs-JSON fallback cleanly.
- `autoescape=True` is centralized in `make_templates` — not a per-template opt-in — so there is no accidental escape bypass path.

---

## Metrics

| Metric | Value |
|---|---|
| New lines | ~1,100 (excluding plans/) |
| Test cases | 8 (5 file-repo + 3 handler) |
| Confirmed STOP gate | Works when script reaches template correctly |
| Confirmed XSS paths | 0 (autoescape + tojson cover all LLM output fields) |
| Confirmed path traversal | 0 (customer_id is int-gated) |
| Fixture path bug | 7x `..` used, 5x `..` needed |

---

## Unresolved Questions

1. Is `?fixture=stop` still needed after the real per-customer scripts are loaded? If pilot data will soon include `recommended=false` rows, the fixture branch can be deleted entirely rather than fixed.
2. Should `GET /api/parties/{id}/approach-script` adopt `auth_dependency.py` now that the file is merged? It exposes AI behavioral analysis per customer — worth a low-cost token guard once `CRM_API_TOKEN` is configured.
3. The template comment says `party` is required in context (line 7) but the template body never uses `party.*`. Is `party` reserved for a future expansion (e.g., showing customer name in the cockpit header), or is it dead from the beginning?

---

**Status:** DONE_WITH_CONCERNS  
**Summary:** Backend and UI are structurally sound; two HIGH issues in the glue layer (wrong `..` count breaking STOP demo, template crash on approach-less JSON) should be fixed before the call cockpit is used with non-pilot data.  
**Evidence:** All findings grep-verified against actual file lines; path traversal count confirmed by running `os.path.normpath` against actual directory structure; Jinja2 behavior tested in Python REPL.
