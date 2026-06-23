# Phase 3 — Claim Station Frontend: Config-Driven Form + Per-Field Live Validation

## Context links
- `crm/src/adapters/inbound/web/screen_hug_claim.py` — all rendering + embedded JS
- `crm/src/adapters/inbound/web/screen_hug_claim.py:37-100` — `make_hug_claim_router` (existing endpoints)
- `crm/src/adapters/inbound/web/screen_hug_claim.py:45-88` — `POST /hug/claim` (form POST, no-JS fallback — unchanged)
- `crm/src/adapters/inbound/web/screen_hug_claim.py:211-257` — existing JS block (`beep`, `normalizeToken`, auto-submit, auto-clear) — to be replaced
- `crm/src/adapters/inbound/web/screen_hug_claim.py:238-250` — client-JS `normalizeToken` — keep logic, keep in new block
- `crm/src/adapters/inbound/web/screen_hug_claim.py:212-223` — `beep(ok)` WebAudio — keep unchanged
- `crm/src/adapters/inbound/web/screen_hug_claim.py:251-254` — auto-submit-on-12-chars — REPLACED by check-token flow
- Phase 2 endpoints (prerequisites):
  - `GET /hug/claim/check-field?key=&value=&session=`
  - `GET /hug/claim/check-token?token=&session=`
  - `POST /hug/claim/bind` (JSON body `{session_id, fields:{...}}`)
- `crm/src/hug/claim_fields.py` — `CLAIM_FIELDS` list (Phase 2 new file)
- `docker-compose.yml:187` — `./crm/src` volume-mounted → hot-reload on save

## Overview
- **Priority:** P1
- **Status:** pending
- **Blocked by:** Phase 2 (needs `check-field`, `check-token`, `bind` endpoints + `CLAIM_FIELDS` config)
- **Scope:** `screen_hug_claim.py` only — two changes:
  1. `_render_page`: render form fields from `CLAIM_FIELDS` config (replacing hard-coded `order_code` + `is_gift` fields).
  2. `<script>` block: replace auto-submit logic with per-field live check + AJAX bind. Keep `beep()`, `normalizeToken`, autofocus.
- No new Python files. No new endpoints. No new dependencies.

## Requirements

### Functional

#### A. Config-driven field rendering (`_render_page`)

`_render_page` currently hard-codes the `order_code` text input and `is_gift` checkbox. Replace with a loop over `CLAIM_FIELDS`:

```python
from hug.claim_fields import CLAIM_FIELDS
import json as _json

# In _render_page, replace hard-coded field HTML with:
fields_html = ""
for f in CLAIM_FIELDS:
    if f["type"] == "bool":
        fields_html += f'<label><input type="checkbox" name="{f["key"]}" value="1" id="f_{f["key"]}"> {f["label"]}</label>'
    else:  # text
        placeholder = f["label"]
        required_attr = 'required' if f["required"] else ''
        fields_html += (
            f'<input type="text" name="{f["key"]}" id="f_{f["key"]}" '
            f'placeholder="{placeholder}" autocomplete="off" {required_attr}>'
            f'<small id="lbl_{f["key"]}"></small>'  # sub-label for live check state
        )

# Pass CLAIM_FIELDS as JSON to the JS block:
claim_fields_json = _json.dumps(CLAIM_FIELDS)
```

`prefill` handling: for fields with `prefill` set, the URL query param is read in `claim_form` (`GET /hug/claim`) and passed to `_render_page`. For `order_code` this is already `order: str = ""` at `:42`. The rendered HTML sets `value="{prefill_value}"` on the matching field. For future prefill fields, the router extracts them as additional query params.

The existing `<form id="claim" method="post" action="/hug/claim">` stays in the DOM — the no-JS fallback. All dynamically-rendered fields have `name="{key}"` so the form POST still sends them. The fallback `POST /hug/claim` handler must also be updated to read all `CLAIM_FIELDS` keys from form data (see Files to Modify).

#### B. `<script>` block replacement

Replace the existing JS block (`screen_hug_claim.py:211-257`) with the following structure. Embed `CLAIM_FIELDS_JSON` from Python (`{{ claim_fields_json }}`).

**Retained from existing block:**
- `beep(ok)` WebAudio function (`:212-223`) — copy verbatim.
- `normalizeToken(v)` (`:238-250`) — copy verbatim (or extend separator set if Phase 1 companion widening is applied here).
- `if (lastResult === "ok") { tokenEl.value = ""; tokenEl.focus(); }` — post-form-POST clear (still fires after a full-page re-render on the fallback path).

**New additions:**

```javascript
// --- Config ---
const FIELDS = /* {{ claim_fields_json }} */;
const SESSION_ID = crypto.randomUUID();  // one UUID per page-load

// --- Helpers ---
function getFieldEl(key)    { return document.getElementById('f_' + key); }
function getLabelEl(key)    { return document.getElementById('lbl_' + key); }

function showSubLabel(key, text, state) {
    // state: 'ok' | 'err' | 'warn'
    const el = getLabelEl(key);
    if (!el) return;
    el.textContent = text;
    el.className = 'sublabel sublabel-' + state;
}

function clearSubLabel(key) {
    const el = getLabelEl(key);
    if (el) { el.textContent = ''; el.className = ''; }
}

// --- Order field: debounced live check-field ---
const orderField = FIELDS.find(f => f.key === 'order_code');
const orderEl = getFieldEl('order_code');
let orderTimer = null;

function checkField(key, value) {
    return fetch('/hug/claim/check-field?key=' + encodeURIComponent(key)
                 + '&value=' + encodeURIComponent(value)
                 + '&session=' + encodeURIComponent(SESSION_ID))
        .then(r => r.json())
        .catch(() => ({ ok: null, message: 'Lỗi kết nối' }));
}

if (orderEl) {
    orderEl.addEventListener('input', () => {
        clearTimeout(orderTimer);
        orderTimer = setTimeout(async () => {
            const v = orderEl.value.trim();
            if (!v) { clearSubLabel('order_code'); return; }
            const res = await checkField('order_code', v);
            if (res.ok === true)  showSubLabel('order_code', res.message, 'ok');
            else if (res.ok === false) { showSubLabel('order_code', res.message, 'err'); beep(false); }
            else                  showSubLabel('order_code', res.message || 'Không thể kiểm tra', 'warn');
        }, 600);
    });
    // Pre-fill from ?order=: fire check immediately if field already has value
    if (orderEl.value.trim()) {
        setTimeout(() => orderEl.dispatchEvent(new Event('input')), 0);
    }
}

// --- Token field: normalize → check-token → bind ---
const tokenEl = getFieldEl('token');  // id="f_token" or legacy id — see note below
const RE = /^[A-Z0-9]{12}$/;

async function checkToken(value) {
    const res = await fetch('/hug/claim/check-token?token=' + encodeURIComponent(value)
                            + '&session=' + encodeURIComponent(SESSION_ID))
        .then(r => r.json())
        .catch(() => ({ state: 'error', message: 'Lỗi kết nối' }));

    if (res.state === 'ready' || res.state === 'rebind_ok') {
        const isAmber = res.state === 'rebind_ok';
        showSubLabel('token', res.message, isAmber ? 'warn' : 'ok');
        beep(true);
        await doBind(value);
    } else {
        showSubLabel('token', res.message, 'err');
        beep(false);
    }
}

async function doBind(token) {
    // Collect all FIELDS values from the form
    const fields = {};
    for (const f of FIELDS) {
        const el = getFieldEl(f.key);
        if (!el) continue;
        fields[f.key] = f.type === 'bool' ? el.checked : el.value.trim();
    }
    // order_code guard: if empty, show amber and wait
    if (!fields['order_code']) {
        showSubLabel('token', 'Nhập mã đơn trước', 'warn');
        return;
    }

    let res;
    try {
        res = await fetch('/hug/claim/bind', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: SESSION_ID, fields })
        }).then(r => r.json());
    } catch {
        res = { ok: false, message: 'Lỗi kết nối khi gắn tem' };
    }

    const resultEl = document.getElementById('result');
    if (res.ok) {
        if (resultEl) {
            resultEl.className = 'result ok';
            resultEl.innerHTML = '<strong>' + res.message + '</strong>'
                + (res.edge ? '<small> ' + res.edge + '</small>' : '');
        }
        beep(true);
        // Clear token field + sub-label; keep order field (next sticker same order)
        const tEl = getFieldEl('token');
        if (tEl) { tEl.value = ''; tEl.focus(); }
        clearSubLabel('token');
    } else {
        if (resultEl) {
            resultEl.className = 'result err';
            resultEl.innerHTML = '<strong>' + res.message + '</strong>';
        }
        beep(false);
    }
}

// Token input listener — replace old auto-submit logic
if (tokenEl) {
    tokenEl.addEventListener('input', async () => {
        let v = normalizeToken(tokenEl.value);
        tokenEl.value = v;
        clearSubLabel('token');
        if (RE.test(v)) {
            await checkToken(v);
        }
    });
}
```

**Token field id note:** the existing form has `<input name="token" ...>`. Its `id` attribute must be `f_token` to match `getFieldEl('token')`. If current HTML uses a different id (e.g. bare `id="token"`), update the rendered HTML in `_render_page` to use `id="f_token"` for the token field too, or adjust `getFieldEl` to also try the legacy id.

**`#result` update mechanism:** set `resultEl.className` + `resultEl.innerHTML` on the existing `id="result"` element (verified present in `_result_block` at `:108`). No `outerHTML` swap needed — avoids re-querying.

#### C. Happy path (zero taps)

1. Page loads with `?order=SON1234` → `order_code` prefilled → debounce fires → `check-field` → green sub-label (Sapo confirms).
2. Staff scans QR → scanner emits 12-char string → `normalizeToken` → `RE.test` passes → `check-token` → `state: ready` → `beep(true)` → `doBind` fires automatically.
3. `bind` → `{ok: true}` → `#result` green + `beep(true)` → token field clears + refocuses.
4. Staff scans next sticker. Order field stays. Zero taps.

#### D. No-JS fallback

The existing `<form id="claim" method="post" action="/hug/claim">` remains. All config-driven fields have `name="{key}"` — the form POST sends them all. The `POST /hug/claim` handler must be updated to read additional CLAIM_FIELDS keys generically (not just hard-coded `order_code` + `is_gift`):

```python
# In claim_submit — replace hard-coded Form params with a Request body read:
@router.post("/hug/claim", response_class=HTMLResponse)
async def claim_submit(request: Request) -> HTMLResponse:
    form = await request.form()
    fields = {}
    for f in CLAIM_FIELDS:
        raw = form.get(f["key"], "")
        if f["type"] == "bool":
            fields[f["key"]] = raw in ("1", "true", "on", "yes")
        else:
            fields[f["key"]] = str(raw).strip()
    order_code = fields.get("order_code", "")
    is_gift = fields.get("is_gift", False)
    token = normalize_input(form.get("token", ""))
    # ... rest of existing logic unchanged
```

This keeps the fallback path fully functional while also future-proofing it for new CLAIM_FIELDS entries.

## Architecture

```
Page load (GET /hug/claim?order=SON1234)
  _render_page:
    - loop CLAIM_FIELDS → render text/bool inputs (id="f_{key}", name="{key}")
    - embed CLAIM_FIELDS_JSON in <script>
    - order_code field prefilled with order="SON1234"
  <script> on DOMContentLoaded:
    - SESSION_ID = crypto.randomUUID()
    - order_code has value → setTimeout → 'input' event → debounce → checkField()
      → GET /hug/claim/check-field?key=order_code&value=SON1234&...
      → {ok:true} → green sub-label under order field

  Staff scans token QR:
    tokenEl 'input' → normalizeToken → RE.test(12 chars) → checkToken()
      → GET /hug/claim/check-token?token=...&session=SESSION_ID
      ├─ state=ready → beep(true) + sub-label green → doBind()
      │     → POST /hug/claim/bind {session_id, fields:{order_code, is_gift, ...}}
      │     ├─ {ok:true} → #result green + beep(true) + clear+focus token field
      │     └─ {ok:false} → #result red + beep(false)
      ├─ state=rebind_ok → beep(true) + sub-label amber → doBind()
      ├─ state=blocked → beep(false) + sub-label red → NO bind
      └─ state=unknown → beep(false) + sub-label red → NO bind

  No-JS fallback:
    <form method="post" action="/hug/claim"> submits all name="{key}" fields
    POST /hug/claim → bind_token(bind_session_id=None) → full-page re-render
```

## Files to modify

| File | Change |
|------|--------|
| `crm/src/adapters/inbound/web/screen_hug_claim.py` | (1) Import `CLAIM_FIELDS` + `json`; (2) rewrite `_render_page` field section to loop CLAIM_FIELDS; (3) replace `<script>` block `:211-257`; (4) update `claim_submit` (form POST) to read fields generically via `Request.form()` |

## Files to create
None.

## Implementation steps

1. **Import block** — at top of `screen_hug_claim.py`, add:
   ```python
   import json as _json
   from hug.claim_fields import CLAIM_FIELDS
   ```

2. **`_render_page` — field HTML generation** — replace the hard-coded `order_code` + `is_gift` HTML with a loop over `CLAIM_FIELDS`. Build `fields_html` string. Handle `prefill`: for each field with `prefill` set, check whether a matching value was passed to `_render_page` and inject `value="{val}"` on the input. Pass `claim_fields_json = _json.dumps(CLAIM_FIELDS)` into the template string so it is embedded in the `<script>` tag.

3. **`_render_page` — token input id** — ensure the token `<input>` has `id="f_token"` (or adjust `getFieldEl` to handle the existing id — confirm by reading the full `_render_page` body before editing).

4. **`_render_page` — `<script>` block replacement** — replace lines `:211-257` with the new JS structure above. Key structural elements:
   - `const FIELDS = <inject claim_fields_json>;` at top.
   - `const SESSION_ID = crypto.randomUUID();`
   - `beep(ok)` — copy verbatim from `:212-223`.
   - `normalizeToken(v)` — copy verbatim from `:238-250` (or widen separators if Phase 1 companion change applied).
   - `checkField(key, value)` → `fetch('/hug/claim/check-field?...')`.
   - Order field `input` listener with 600 ms debounce + pre-fill fire.
   - Token field `input` listener → `normalizeToken` → `RE.test` → `checkToken`.
   - `checkToken(value)` → `fetch('/hug/claim/check-token?...')` → dispatch to `doBind` or sub-label.
   - `doBind(token)` → collect all FIELDS → `fetch('/hug/claim/bind', {method:'POST',...})` → update `#result` + beep + clear/focus.
   - Post-form-POST clear: `if (lastResult === "ok") { tokenEl.value = ""; tokenEl.focus(); }` — retain for fallback path compatibility.

5. **`claim_submit` update** — replace the three hard-coded `Form(default=...)` parameters with `request: Request` and `await request.form()`. Loop `CLAIM_FIELDS` to extract all field values generically. Pass `order_code` and `is_gift` to `bind_token` as before (promoted columns). Pass remaining fields as `bind_attributes` dict if any (currently none). Add `Request` to the existing `from fastapi import APIRouter, Form, Request` import.

6. **`_render_page` signature** — if it currently takes `order_code: str = ""` as a dedicated param, add a generic `prefill: dict[str, str] | None = None` param and thread it through `claim_form`. For now, `order_code` can stay as a named param (it's the only prefill field in current config). Note in code that when a second `prefill` field is added, this should be refactored to a dict.

7. **Deploy** — code edits to `screen_hug_claim.py` hot-reload via `CRM_DEV_RELOAD=1`. No restart needed (schema already migrated in Phase 2 restart). Test in browser with a printed token.

## Test matrix

| Layer | What | How |
|-------|------|-----|
| Unit | `_render_page` output contains `id="f_order_code"` and `id="f_is_gift"` | `pytest` — parse HTML string |
| Unit | `_render_page` output embeds `CLAIM_FIELDS` as valid JSON in `<script>` | Same — `json.loads` the extracted snippet |
| Unit | `_render_page` prefills `order_code` input when `order_code` param given | Same |
| Unit | `claim_submit` form POST reads `order_code` + `is_gift` correctly from form data | `TestClient` with form POST |
| Unit | `claim_submit` ignores unknown form keys not in `CLAIM_FIELDS` | Same |
| Integration | `GET /hug/claim?order=SON1` → HTML with `value="SON1"` in order_code input | `TestClient` |
| Integration | JS `checkField` call chain: order sub-label green after Sapo mock returns ok | Manual (browser) |
| Integration | Token scan → `check-token` ready → `bind` → result block green | Manual |
| Manual | `?order=SO1234` pre-fill → green sub-label on page load (Sapo creds set) | Browser |
| Manual | `?order=SO1234` pre-fill → amber sub-label on page load (Sapo creds unset) | Browser |
| Manual | Scan valid token with order filled → result block green + beep + token clears. Zero taps | Browser with printed token |
| Manual | Scan already-bound token (different session) → result block red + beep. No bind | Same |
| Manual | Scan token with empty order field → amber "Nhập mã đơn trước" sub-label, no bind | Same |
| Manual | Disable JS → form submit button → full-page POST succeeds | Browser devtools |
| Manual | Sapo API unreachable (wrong URL) → amber sub-label, bind still proceeds | Test env with bad URL |

## Success criteria
- `GET /hug/claim` HTML: contains `id="f_order_code"`, `id="f_is_gift"`, `CLAIM_FIELDS` JSON in script.
- `?order=SON123` → `value="SON123"` pre-filled in `order_code` input.
- Scanning a token (12 valid chars) with order filled → result block green + beep + token clears. Zero taps.
- Scanning an already-bound token (different session) → result block red + beep, no bind.
- Scanning token before order is typed → amber "Nhập mã đơn trước", no bind.
- Disabling JS → "Gắn tem vào đơn" submit button → full-page POST succeeds.
- Sapo unset → amber sub-label under order field; bind still proceeds when token scanned.
- All unit + integration tests pass.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Token input id mismatch (`id="token"` vs `id="f_token"`) | Medium | Medium | Read `_render_page` body fully before editing; add unit test asserting `id="f_token"` in rendered HTML |
| `normalizeToken` drift — JS copy vs TS Worker after Phase 1 separator widening | Medium | Low (kiosk is controlled; inconsistency not user-visible) | Phase 1 companion change widens JS copy in same PR; document in PR |
| `crypto.randomUUID()` unavailable on very old browser | Very Low | Low (kiosk is controlled device) | YAGNI — do not polyfill preemptively; add to risk log |
| `fetch` failure during `doBind` → result block not updated | Low | Medium | `doBind` has try/catch; on exception updates result block to red + `beep(false)` |
| `#result` element id changes (server renders different id) | Very Low | Medium | Verified `id="result"` in `_result_block` at `:108`; add assertion in unit test |
| New `CLAIM_FIELDS` entry with `type="select"` or other input types | Low | Low | Current loop handles `bool` + `text` only; document that new input types need a renderer branch in `_render_page` |
| `claim_submit` fallback ignores `bind_attributes` for non-promoted fields | Intentional | None for current config | When first non-promoted field is added, update `claim_submit` to pass `bind_attributes` — note in code |
| JS `FIELDS` embed injection — XSS if field labels contain `<`, `>`, `"` | Low | Low | `_json.dumps` escapes these; Python's json module always produces safe ASCII for embedding in `<script>` (no `</script>` injection if labels don't contain that exact string — confirm labels don't) |

## Rollback
Revert `_render_page` and `<script>` block to previous version → hot-reload. No schema or endpoint changes in this phase — rollback is a code revert only.

## Unresolved questions
1. **Token input id:** what is the current `id` attribute of the token `<input>` in `_render_page`? Must be read before Step 3 to avoid a mismatch. (Likely `id="token"` based on `:251-254` reference `tokenEl`; if so, standardise to `id="f_token"` or adjust `getFieldEl('token')` to check both.)
2. **`_render_page` current signature:** does it already take `order_code` as a named param, or via a dict? Confirm before Step 6 to avoid breaking the `claim_form` GET handler.
3. **`lastResult` variable:** `:202` references `if (lastResult === "ok")` in the existing script block — this is a server-injected Python value. Confirm it is still present in the new script block context (post-form-POST path), or replace with a DOM class check on `#result`.
