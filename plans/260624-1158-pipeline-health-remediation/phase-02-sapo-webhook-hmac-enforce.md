# Phase 02 — Worker security: queue bearer-token + Sapo webhook HMAC

**Priority:** HIGH (security) | **Status:** 🟡 Part A done+enforced; Part B OBSERVE deployed (awaiting real-traffic confirmation before enforce)
**Context:** [plan](plan.md) · audit findings "queue endpoints unauth" + "CHECK_HMAC off by default" · Sapo OAuth doc https://support.sapo.vn/oauth + webhook doc https://support.sapo.vn/sapo-webhook

---

## Part A — Queue endpoint bearer-token (CODE DONE 2026-06-24, deploy pending)

`/poll` `/ack` `/ack-batch` `/release` are server-to-server (Dagster consumer → Worker), NOT Sapo-signed → bearer token is the right control (not HMAC). Docker net is private, so this is defense-in-depth.

**Implemented:**
- Worker `src/index.ts`: `requireQueueToken()` guards the 4 queue routes. Backward-compatible — if `POLL_TOKEN` unset, check is skipped (no break window).
- Consumer `ingestion/src/sapo/webhook_consumer.py`: sends `Authorization: Bearer <WORKER_POLL_TOKEN>` if that env var is set.

**Deploy steps (to enforce):**
1. Pick a strong token. Set on Worker: `wrangler secret put POLL_TOKEN`.
2. Set same value as `WORKER_POLL_TOKEN` env on the Dagster `data_platform` container (`.env.docker`).
3. Restart consumer / redeploy Worker. Verify `/poll` returns 200 with header, 401 without.
4. Order matters: set consumer env FIRST (or simultaneously) so polling doesn't 401 the moment `POLL_TOKEN` lands.

---

## Part B — Sapo webhook HMAC (observe → confirm → enforce)

### Progress (2026-06-24)
- ✅ Observe-mode logging deployed (Worker v8b2c35e5): when a secret is set but `CHECK_HMAC` off, each `/webhook/*` logs `HMAC_OBSERVE` to D1 `webhook_errors` with the request's header names + which header/encoding the HMAC matches — WITHOUT rejecting. Code in `src/index.ts` `handleWebhook` (marked temporary, remove after enforce).
- ✅ Secrets set: `SAPO_SECRET` + `WEBHOOK_SECRET` (same value) via wrangler.
- ✅ Self-test validated logic: a request signed with the secret over the raw body → `match=MATCH header=x-sapo-hmac-sha256 enc=base64` (matches `SOURCE_CONFIGS['sapo']`). Bogus test message was deleted from the queue (status was NEW).

### NEXT (you / monitoring) — confirm on REAL Sapo traffic, then enforce
1. Wait for genuine Sapo webhook events, then read the observe log:
   ```
   cd webhook_receiver/cloudflareD1 && npx wrangler d1 execute fgcare-webhook-db --remote \
     --command "SELECT created_at, error_message FROM webhook_errors WHERE error_type='HMAC_OBSERVE' ORDER BY id DESC LIMIT 20"
   ```
   Confirm REAL requests show `match=MATCH` (note the actual `path=` and `header=` Sapo uses — if path is `/webhook/sapo_v2/...` it falls to DEFAULT_CONFIG/WEBHOOK_SECRET, which is also set).
2. If real events MATCH consistently → enforce: `npx wrangler secret put CHECK_HMAC` (value `true`) OR add `CHECK_HMAC = "true"` to `wrangler.toml [vars]` + `wrangler deploy`. Also set `HMAC_HEADER_NAME=x-sapo-hmac-sha256` if Sapo uses the DEFAULT_CONFIG path.
3. After enforcing + confirming ingestion unaffected: REMOVE the temporary observe block from `index.ts` and redeploy.
4. Rollback: unset/false `CHECK_HMAC` → instant revert to accept-all.
- If real events show `no-match` → the secret or scheme differs; do NOT enforce. Inspect the logged header list + adjust secret/header/encoding.

## Problem
`webhook_receiver/cloudflareD1/src/index.ts:98` gates HMAC on `env.CHECK_HMAC === 'true'`. CHECK_HMAC is NOT set in `wrangler.toml` → defaults false → `/webhook/*` currently accepts **unauthenticated** payloads into the D1 queue. Cannot blindly flip to true: a wrong secret/header would 401 all real Sapo webhooks and silently stop ingestion.

## Key findings (verified 2026-06-24)
- Sapo signs with **HMAC-SHA256, Base64-encoded, using the app "Secret Key"** (per OAuth doc; Sapo mirrors the Shopify API — topics `orders/create`, `products/update`, etc.).
- The Worker **already supports** this: `verifySignature(secret, sig, body, 'base64')`, `encoding:'auto'` falls back to base64 when no `sha256=` prefix (`index.ts:124-138`).
- **Unknowns blocking enforcement:** (1) Sapo's exact signature **header name** (default config uses `x-hub-signature-256`; Sapo likely `X-Sapo-Hmac-SHA256` — must confirm from real traffic); (2) which secret value Sapo uses and that our computed HMAC matches byte-for-byte.
- Webhooks registered via `POST /admin/webhooks.json` (topic + address).

## Strategy: observe-before-enforce (never break live ingestion)
1. **Observe mode (no rejection):** add temporary logging in `handleWebhook` that, for each inbound `/webhook/*`, records: all request header names, the candidate signature header value, and the result of computing HMAC-SHA256/base64 over the raw body with the configured secret (match / mismatch) — but DO NOT 401. Keep `CHECK_HMAC` false. Deploy.
2. **Set secret:** `wrangler secret put WEBHOOK_SECRET` (or sapo-specific key per `SOURCE_CONFIGS`) = Sapo app Secret Key.
3. **Confirm from real traffic (a few hours/day):** read Cloudflare logs / D1 error log → confirm (a) the real header name Sapo sends, (b) computed base64 HMAC == received signature for genuine events. Adjust `HMAC_HEADER_NAME` env / `SOURCE_CONFIGS['sapo_v2'].headerNames` to the confirmed header.
4. **Enforce:** once match rate is 100% on real events, set `CHECK_HMAC=true` (wrangler var/secret). Remove the temporary observe logging (or downgrade to error-only). Add a startup log line printing HMAC posture so it's visible in CF logs.
5. **Rollback:** if legit events start 401-ing, set `CHECK_HMAC=false` immediately (single env flip) → ingestion resumes.

## Related files
- `webhook_receiver/cloudflareD1/src/index.ts` (handleWebhook, verifySignature, SOURCE_CONFIGS)
- `webhook_receiver/cloudflareD1/wrangler.toml` (vars/secrets — CHECK_HMAC, HMAC_HEADER_NAME, secret)
- `webhook_receiver/docs/SECURITY.md` (update once header/secret confirmed)

## Todo
- [ ] Add observe-mode logging (no reject) + deploy
- [ ] `wrangler secret put` the Sapo Secret Key
- [ ] Confirm real header name + HMAC match from CF logs
- [ ] Pin confirmed header in config
- [ ] Set CHECK_HMAC=true, remove observe logging, add posture log
- [ ] Update SECURITY.md

## Success criteria
- 100% of genuine Sapo webhook events pass HMAC; forged/altered bodies get 401.
- Ingestion row counts unchanged across the cutover (no drop after enforce).

## Risks
- Wrong header/secret → mass 401 → ingestion stops. Mitigated by observe-first + instant `CHECK_HMAC=false` rollback.
- Sapo may not send a signature at all on some topics → observe phase reveals this before enforcing.

## Open questions
- Does Sapo actually send an HMAC header for store-registered webhooks (vs only OAuth-app webhooks)? Observe phase answers this. If not, protection must shift to a secret path token in the webhook address URL instead.
