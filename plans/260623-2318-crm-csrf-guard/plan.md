# Plan — CRM CSRF guard (deferred from audit M4)

**Status:** Deferred / Not started · **Priority:** Low (LAN-only, no-auth app — low CSRF threat) · **Created:** 2026-06-23
(updated 2026-06-24: deferred — user chose to defer; naive header guard would break /hug kiosk external POSTs; inventory + classification required before safe implementation)

## Context
- Audit finding M4 (`plans/reports/audit-crm-app-260623-1843-report.md`): no CSRF protection on state-changing CRM endpoints.
- A second-wave agent implemented a naive guard (middleware: 403 any POST/PUT/PATCH/DELETE lacking `HX-Request: true`, exempt `/api/*` + `/hug/claim/bind`). **Reverted before commit** — too risky: it would 403 the external Hug kiosk on `/hug/claim`, `/hug/mint`, `/hug/review/action` and any non-HTMX form post.

## Problem with header-only guard
`HX-Request` header check assumes EVERY legitimate browser mutation goes through HTMX and every non-browser caller is exempt. Unverified here:
- External Hug kiosk posts to `/hug/*` (not just `/hug/claim/bind`).
- Any plain `<form method=post>` (non-HTMX) in web screens (login? search? full-page submits).
- Userscripts (`crm/userscripts/`) — what do they POST to.

## Requirements
- Protect browser-driven state changes from cross-site forgery.
- MUST NOT break: external Hug kiosk, `/api/*` server-to-server (sync), userscripts.
- App is LAN-only, no auth/session today — so the guard can't rely on a session-bound token unless one is introduced.

## Steps
1. **Inventory mutation routes** (done partially): groups = `/api/*` (REST, prefix set per handler), `/hug/*` (kiosk external + staff HTMX admin), `web/screen_*` (HTMX UI). Enumerate POST/PUT/PATCH/DELETE in each.
2. **Classify each route's real caller**: browser-HTMX (sends `HX-Request`) / external kiosk / server-to-server. Verify by reading kiosk client + `crm/userscripts/` + confirming templates use `hx-*` (not bare forms).
3. **Pick mechanism**:
   - If 100% of browser mutations are HTMX → header-allowlist guard is acceptable: exempt `/api/*` + ALL `/hug/*`, enforce on the rest.
   - If any browser mutation is a plain form → use double-submit cookie token (or SameSite=Strict cookie + origin check) instead of the header trick.
4. **Implement** as one middleware with an explicit, documented allowlist + per-route-group tests (POST with and without the guard token/header).
5. **Roll out log-only first** (warn, don't block) for one cycle to catch any missed caller in real logs, then flip to enforce.

## Files
- `crm/src/composition.py` (middleware wiring)
- New: a small `adapters/inbound/web/csrf.py` (guard + allowlist)
- Tests under `crm/src/tests/`

## Open questions
1. Which `/hug/*` endpoints are external kiosk vs staff HTMX admin?
2. Any non-HTMX `<form>` POST in the web UI (login, search, full-page)?
3. Do `crm/userscripts/` POST to web routes or only `/api`/`/hug`?
4. Worth introducing a session/token at all for a LAN-only app, or is SameSite cookie + origin check enough?
