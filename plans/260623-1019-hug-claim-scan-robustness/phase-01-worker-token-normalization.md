# Phase 1 — Worker `/h/:token` normalization

## Context links
- `webhook_receiver/cloudflareD1/src/index.ts:18-20` — raw capture
- `webhook_receiver/cloudflareD1/src/hug-handler.ts:217-275` — `handleHugScan`, D1 lookup at :229
- `webhook_receiver/cloudflareD1/src/utils.ts` — existing TS utilities (add `normalizeToken` here)
- `webhook_receiver/cloudflareD1/src/utils.test.ts` — existing Vitest suite (add parity tests here)
- `crm/src/hug/tokens.py:53-95` — Python `normalize_input` (canonical reference)
- `crm/src/adapters/inbound/web/screen_hug_claim.py:238-250` — client-JS `normalizeToken` (copy 2)

## Overview
- **Priority:** P1 — silent scan failures from typed human codes are invisible to operators
- **Status:** ✅ DONE — merged `afd271d`, deployed version `02c2165e` to `hug.fjp.vn`, live e2e PASS (bare/dashed/HUG-/lowercase/underscore/dot/%20 all → campaign; unknown/short → fallback)
- **Scope:** Worker TS only. No D1 schema change. No Python/JS changes (those are called out separately below as a recommendation).

## The bug (verified)

`index.ts:18` captures `hugScanMatch[1]` — the raw URL path segment — and passes it as-is to `handleHugScan` (`index.ts:20`). `handleHugScan` binds it directly to the D1 `WHERE t.token = ?` query (`hug-handler.ts:229`). The stored token is always a bare 12-char string (e.g. `7K2NQ9XRWAB4`). Staff typing the printed sticker code `/h/7K2N-Q9XR-WAB4` or `/h/HUG-7K2N-Q9XR-WAB4` produce a dashed string that will never match → silent 302 to `HUG_FALLBACK_URL`.

## Requirements

### Functional
1. `normalizeToken(raw: string): string` in TS mirrors `tokens.py:normalize_input` exactly, **plus** broadened separator set.
2. Normalization steps (in order):
   a. `decodeURIComponent` (typed spaces arrive as `%20`; scanner may encode the full URL)
   b. `.trim().toUpperCase()`
   c. If the string contains `://`, extract the last path segment (strip query string + fragment first)
   d. Strip all of: `-`, `_`, `.`, and any whitespace character (`\s`)  ← broadened beyond Python's `-`/space
   e. If `len == 15` and starts with `HUG`, strip the first 3 chars (15 = `HUG` + 12-char token)
3. Call `normalizeToken` in `handleHugScan` on the incoming `token` argument, **before** the D1 lookup.
4. After normalization, if the result is not exactly 12 chars → redirect to fallback immediately (avoid wasted D1 read).

### Non-functional
- No runtime dependencies added.
- `normalizeToken` exported from `utils.ts` (same file as `verifySignature`).
- Tests added to `utils.test.ts` (Vitest — already configured).

### Drift management (cross-copy parity)
There are now THREE copies: Python `tokens.py:normalize_input`, client-JS `screen_hug_claim.py:238-250`, Worker-TS (new). **Recommendation (must be called out in PR):** also widen the Python and client-JS copies to strip `_` and `.` so all three accept the same separator set. This is not required for Phase 1 to ship, but deferring creates silent divergence. The plan treats it as a same-PR companion change.

## Architecture

```
GET /h/<raw_segment>
  index.ts:18 → hugScanMatch[1]
  ↓
  normalizeToken(raw)          ← NEW in utils.ts
  ↓
  if len != 12 → 302 fallback  ← NEW guard
  ↓
  handleHugScan(req, env, ctx, normalizedToken)
  ↓
  D1: WHERE t.token = normalizedToken AND t.status = 'bound'
```

## Files to modify

| File | Change |
|------|--------|
| `webhook_receiver/cloudflareD1/src/utils.ts` | Add `export function normalizeToken(raw: string): string` |
| `webhook_receiver/cloudflareD1/src/hug-handler.ts` | Import `normalizeToken`; call it at start of `handleHugScan`; add early-exit guard |
| `webhook_receiver/cloudflareD1/src/utils.test.ts` | Add `describe('normalizeToken', ...)` parity tests |
| `crm/src/hug/tokens.py` | Widen `normalize_input` separator strip (add `_` and `.`) — recommended companion |
| `crm/src/adapters/inbound/web/screen_hug_claim.py` | Widen client-JS `normalizeToken` separator strip — recommended companion |

## Implementation steps

1. **Add `normalizeToken` to `utils.ts`** (after `verifySignature`):
   - `decodeURIComponent` on `raw` (wrapped in try/catch — malformed % encoding falls back to `raw`)
   - `.trim().toUpperCase()`
   - URL detection: `if (s.includes('://'))` → split on `?` then `#`, strip trailing `/`, take last `/`-segment
   - Strip `[-_.\s]` globally (single regex replace)
   - HUG prefix: `if (s.length === 15 && s.startsWith('HUG')) s = s.slice(3)`
   - Return `s`

2. **Update `hug-handler.ts` `handleHugScan`** (`hug-handler.ts:217`):
   - Import `normalizeToken` from `'./utils'`
   - First line of function body: `token = normalizeToken(token);`
   - After normalization: `if (token.length !== 12) return Response.redirect(getFallbackUrl(env), 302);`
   - All subsequent logic unchanged

3. **Add tests in `utils.test.ts`** — new `describe` block alongside existing `verifySignature` suite:

   | Test case | Input | Expected output |
   |-----------|-------|-----------------|
   | Bare token | `7K2NQ9XRWAB4` | `7K2NQ9XRWAB4` |
   | Lowercase bare | `7k2nq9xrwab4` | `7K2NQ9XRWAB4` |
   | Grouped code (dashes) | `7K2N-Q9XR-WAB4` | `7K2NQ9XRWAB4` |
   | Human code (HUG- prefix) | `HUG-7K2N-Q9XR-WAB4` | `7K2NQ9XRWAB4` |
   | HUG- lowercase | `hug-7k2n-q9xr-wab4` | `7K2NQ9XRWAB4` |
   | Full scan URL | `https://hug.fjp.vn/h/7K2NQ9XRWAB4` | `7K2NQ9XRWAB4` |
   | Full URL with query | `https://hug.fjp.vn/h/7K2NQ9XRWAB4?foo=1#bar` | `7K2NQ9XRWAB4` |
   | URL-encoded space (`%20`) | `HUG%207K2N%20Q9XR%20WAB4` | `7K2NQ9XRWAB4` |
   | Underscores | `7K2N_Q9XR_WAB4` | `7K2NQ9XRWAB4` |
   | Dots | `7K2N.Q9XR.WAB4` | `7K2NQ9XRWAB4` |
   | Token starting with HUG (not prefix) | `HUG234567892A` | `HUG234567892A` (length=12, no strip) |
   | Garbage input | `XXXX` | `XXXX` (len≠12 caught by caller guard) |

4. **Widen Python `normalize_input`** (`tokens.py:87`): change `.replace("-", "").replace(" ", "")` to also replace `_` and `.`; update the docstring separator list. Verify `is_valid_token` still passes after — the alphabet contains no `_`/`.` so stripped chars are always non-token and safe to remove.

5. **Widen client-JS `normalizeToken`** (`screen_hug_claim.py:245`): change `v.replace(/-/g, "").replace(/\s+/g, "")` to `v.replace(/[-_.\s]/g, "")`.

6. **Deploy:** `wrangler deploy` from `webhook_receiver/cloudflareD1/`.

## Test matrix

| Layer | What | How |
|-------|------|-----|
| Unit | `normalizeToken` all 12 cases above | `vitest run` in `webhook_receiver/cloudflareD1/` |
| Unit | Python `normalize_input` with `_` and `.` inputs | Add to existing `crm/src/tests/test_hug_*.py` (or new file) |
| Manual smoke | GET `/h/7K2N-Q9XR-WAB4` against deployed Worker with a bound token | Confirm 302 to campaign URL (not fallback) |
| Manual smoke | GET `/h/HUG-7K2N-Q9XR-WAB4` | Same confirm |
| Regression | GET `/h/7K2NQ9XRWAB4` (bare token, existing happy path) | Unchanged behavior |

## Success criteria
- `vitest run` passes with all new normalizeToken cases green.
- Manual GET of a dashed human code against a bound token → 302 to campaign URL (not fallback).
- GET of bare token still works.
- No existing `verifySignature` tests regressed.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Parity drift: Python/JS copies not widened | Medium | Medium (staff confusion when claim JS accepts `_` but Worker also does — no actual user harm, just inconsistency) | Treat as required companion PR changes, not optional |
| `decodeURIComponent` throws on malformed `%` | Low | Low (scanner inputs are well-formed) | Wrap in `try/catch`, fall back to raw string |
| Token starting with `HUG` + exactly 12 chars gets corrupted | — | — | The 15-char length guard prevents this (verified via `tokens.py:92` logic; test case 11 above covers it) |
| Wrangler deploy breaks existing webhook routes | Low | High | Routes are separate path prefixes; normalization is additive only |

## Rollback
Redeploy prior Worker commit (`git revert` + `wrangler deploy`). Python/JS companion changes are non-breaking (separator set widening only adds flexibility) — no rollback needed for those.

## Unresolved questions
- None for this phase. Python/JS widening is recommended but can be deferred to a follow-up PR if preferred — flag in PR description.
