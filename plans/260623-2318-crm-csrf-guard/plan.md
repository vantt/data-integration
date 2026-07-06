# Plan — CRM CSRF guard (deferred from audit M4)

**Status:** NOT DONE — deployed + log-only rollout running (started 2026-07-06 15:03 ICT), waiting on a real-traffic observation window before enforcing (see "Next step") · **Priority:** Medium→High (was Low; CF Access now live, see below) · **Created:** 2026-06-23
(updated 2026-06-24: deferred — naive header guard would break /hug kiosk external POSTs; inventory + classification required)
(updated 2026-07-06: un-deferred. CF Access (`plans/archive/260626-1712-cf-access-crm`) made CRM internet-facing with real per-user auth — the original "LAN-only, no-auth app" deferral reason is void. A malicious page can now trick a logged-in staff browser into a cross-site POST that rides the CF Access cookie through the tunnel. Re-audited routes with real evidence, resolved all 4 open questions below, implementing header-independent Origin/Host guard.)

## Context
- Audit finding M4 (`plans/reports/audit-crm-app-260623-1843-report.md`): no CSRF protection on state-changing CRM endpoints.
- A second-wave agent implemented a naive guard (middleware: 403 any POST/PUT/PATCH/DELETE lacking `HX-Request: true`, exempt `/api/*` + `/hug/claim/bind`). **Reverted before commit** — too risky: it would 403 the external Hug kiosk on `/hug/claim`, `/hug/mint`, `/hug/review/action` and any non-HTMX form post.

## Re-audit findings (2026-07-06)
Answers to the 4 open questions, verified by reading code (not assumed):
1. **`/hug/*` is NOT an external unauthenticated kiosk.** `docker-compose.yml:233` comment: "crm.lan.fwg.vn now routed via Cloudflare Tunnel" — the LAN hostname the Hug claim/mint stations use is now also behind CF Access, same as the rest of CRM. There is no bypass path left.
2. **Yes — `/hug/*` screens use plain `<form method="post">`, no `hx-post` at all** (`screen_hug_claim_template.py:63`, `screen_hug_mint_html.py:79`, `screen_hug_review_html.py:174/183`, `screen_hug_campaign_html_list.py:111/120`, `screen_hug_campaign_html_history.py:88`). A header-only (`HX-Request`) guard would 403 100% of Hug screens — confirms the original revert was correct.
   - Everywhere else (`web/screens/*`, `management_modals.html`, `campaigns.html`, `modals.html`, `dedup_review.html`, `settings.html`, `segments.html`, fragments/*), every mutating form has `hx-post`/`hx-patch`/`hx-put`. `task_detail.html` has plain `method="post"` forms too, but each also carries `hx-post` as progressive enhancement — HTMX intercepts them in normal operation.
   - The only bare non-HTMX `<form>`s without hx-* are `layout.html` search, `customer_list.html` toolbar search, `_wl_filter_bar.html` — all `hx-get` (search/filter), not mutations. Not in scope.
3. **`crm/userscripts/sapo-hug-claim-button.user.js` does not POST anywhere.** It only opens `https://crm.lan.fwg.vn/hug/claim?order=...` as a normal browser navigation (staff clicking a button on a Sapo order page) — same browser, same CF Access session as any other CRM screen. Not a cross-origin actor.
4. **No new session/token needed.** Chose Origin/Referer-vs-Host self-check instead (see Mechanism) — doesn't depend on CF's `CF_Authorization` cookie SameSite behavior (undetermined, Cloudflare-controlled) and needs no allowlist config to maintain.

## Mechanism (decided)
Since at least one legitimate group (`/hug/*`) uses plain forms, per the plan's original decision tree we skip the header-allowlist trick and use an **Origin/Referer vs Host** check instead — uniform across HTMX and plain-form routes, no per-route exemption needed beyond `/api/*`:
- For POST/PUT/PATCH/DELETE outside `/api/*`: read `Origin` header (fallback `Referer`); extract its host; compare to the request's own `Host` header.
- Match → allow. Mismatch → block (or log, during rollout). Neither header present → allow + log (ambiguous; OWASP guidance is to not block on absence alone).
- `/api/*` stays exempt — already has its own auth (`CRM_API_TOKEN` / webhook HMAC per `auth_dependency.py`), called server-to-server, legitimately has no browser Origin.
- No hardcoded domain allowlist: self-referential check works automatically whether reached via `crm.fwg.vn`, `crm.lan.fwg.vn`, or local dev.

## Rollout
`CRM_CSRF_ENFORCE` env var, default `false` (log-only — matches Step 5 of the original plan). Flip to `true` after a log-review cycle confirms no legitimate caller is flagged.

## Files
- `crm/src/adapters/inbound/http/csrf_guard.py` (new — guard middleware; placed next to `cf_access_middleware.py`/`auth_dependency.py`, not `web/csrf.py` as originally guessed, to match the existing auth-middleware location convention)
- `crm/src/composition.py` (middleware wiring)
- `crm/src/tests/test_csrf_guard.py` (new)

## Implementation (2026-07-06)
- `crm/src/adapters/inbound/http/csrf_guard.py` — `CSRFGuardMiddleware`, Origin/Referer-vs-Host check, `CRM_CSRF_ENFORCE` env toggle (default log-only).
- Wired in `composition.py::_configure_middleware` after `CFAccessMiddleware` (outermost — rejects before spending a JWT verification).
- 7 new tests in `crm/src/tests/test_csrf_guard.py`, all pass. Full suite run: 749 passed, 9 pre-existing failures unrelated (jinja template/worklist-filter/cache-repo issues already present before this change, not touching composition.py or the new middleware).
- No new env var required in `.env` yet — `CRM_CSRF_ENFORCE` unset defaults to log-only (safe).

## Deployment (2026-07-06 15:03 ICT)
- Added `CRM_CSRF_ENFORCE=${CRM_CSRF_ENFORCE:-false}` to `docker-compose.yml` crm service env, documented (commented, defaults false) in `.env`.
- `docker compose up -d crm` (recreate, not just restart, to pick up the new compose env var) — container healthy.
- Verified live: same-origin POST passes through untouched; cross-origin POST (`Origin: https://evil.example`) returns 200 (log-only, not blocked) and logs `csrf_guard: cross-origin POST ... — would block (CRM_CSRF_ENFORCE=false, log-only)`.

## Test-infra fix (2026-07-06 15:18 ICT)
While re-testing, found `crm/src/tests/test_csrf_guard.py` originally used `fastapi.testclient.TestClient` (needs `httpx`) + `pytest.mark.asyncio` (needs `pytest-asyncio`) — neither package was in `requirements.txt` nor baked into the image; they only worked because someone had `pip install`-ed them ad-hoc into the previously long-running container, which my `docker compose up -d crm` recreate wiped. Fixed two ways:
1. Rewrote the test to call `CSRFGuardMiddleware.dispatch()` directly (bare Starlette `Request` from a minimal ASGI scope, `asyncio.run(...)`) — matches the existing project convention in `test_hug_mint_reprint.py` / `test_bulk_resolve_endpoint.py` for avoiding the TestClient/httpx dependency. No new package needed for this test.
2. Also found `test_hug_claim_dynamic_fields.py` and `test_task_detail_and_cockpit.py` DO use `TestClient`/httpx and were silently relying on the same ad-hoc install — a latent gap unrelated to CSRF guard. Added `pytest==8.3.4` + `httpx==0.28.1` to `crm/src/requirements.txt` (matches the existing convention in `crm/sync/requirements.txt`, which already ships `pytest` in its main requirements file — no dev/prod split exists anywhere in this repo). Rebuilt image (`docker compose up -d --build crm`) — verified both packages now baked in, full suite reruns clean with zero manual pip installs, same 749 passed / 9 pre-existing failures.

## Clean-code review (2026-07-06 15:24 ICT)
Re-tested + audited against project conventions and personal dev rules. 2 real findings, both fixed:
1. Test docstring claimed httpx "NOT in requirements.txt" — went stale the moment httpx was added in the prior step. Fixed wording to explain the direct-dispatch choice as a unit-test design decision, not a dependency workaround.
2. Comments in `docker-compose.yml`, `.env`, and `csrf_guard.py` embedded this plan's ID (`260623-2318-crm-csrf-guard`) — violates the personal rule "don't put plan IDs in code comments, explain the invariant directly" (stable-code-artifacts rule). Removed all 3; comments now describe behavior only (`plan.md` itself is the only place the plan ID belongs).
No other clean-code issues found: SRP/naming/DRY/YAGNI all check out (see prior review pass). Full suite reruns clean after both fixes: 749 passed, 9 pre-existing failures unchanged.

## Next step (not yet done)
Let it run log-only for one real-traffic cycle (few days of normal Hug/staff usage), then:
```
docker compose logs crm --since 72h | grep "csrf_guard:.*would block"
```
If zero hits from legitimate traffic (Hug claim/mint/review, staff HTMX screens) → set `CRM_CSRF_ENFORCE=true` in `.env`, `docker compose up -d crm` to enforce. Any unexpected hit → investigate that route before enforcing (may reveal a caller path not covered by the re-audit above).

## Open questions
None remaining — all 4 resolved above by reading code, not asked to the user.
