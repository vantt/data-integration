# Phase 2 — Dynamic Claim-Field Foundation

## Context links
- `crm/src/hug/db.py:22-46` — `_SCHEMA` with `CREATE TABLE IF NOT EXISTS hug_token` + idempotent `executescript` at `:71`
- `crm/src/hug/repository.py:65-68` — `get_token` (SELECT *)
- `crm/src/hug/repository.py:91-134` — `bind_token` — current signature, idempotency guard at `:110-113`
- `crm/src/hug/config.py` — env reader pattern (`os.environ.get` with defaults)
- `crm/src/adapters/inbound/web/screen_hug_claim.py:37-100` — `make_hug_claim_router` — existing endpoints
- `crm/src/adapters/inbound/web/screen_hug_claim.py:45-88` — `POST /hug/claim` (form POST, no-JS fallback — unchanged)
- `crm/src/composition.py:95` — `make_hug_claim_router` wired into FastAPI app
- `docker-compose.yml:164-178` — crm environment block
- `docker-compose.yml:187` — `./crm/src` volume-mount → hot-reload with `CRM_DEV_RELOAD=1` at `:174`
- Sibling plan: `plans/260623-0852-hug-campaign-matching-and-preview/` (targeting catalog)

## Overview
- **Priority:** P1 — prerequisite for Phase 3 (frontend wiring)
- **Status:** pending
- **Scope:** Python backend only. New file `claim_fields.py`. Two new SQLite columns. Generic `check-field` + `check-token` endpoints. Rewritten `bind_token` + new AJAX `bind` endpoint. No frontend changes.

## Requirements

### Functional

#### 1. `claim_fields.py` — field config + validator registry (NEW FILE)

`crm/src/hug/claim_fields.py`:

```python
CLAIM_FIELDS = [
    {
        "key":      "order_code",
        "label":    "Mã đơn hàng",
        "type":     "text",
        "input":    "type",        # staff types or prefills from ?order=
        "required": True,
        "validate": "sapo_order",  # key into VALIDATORS
        "prefill":  "order",       # URL query param name to prefill from
        "edge":     True,          # include in D1 attributes push (Phase 4)
    },
    {
        "key":      "is_gift",
        "label":    "Quà tặng",
        "type":     "bool",
        "input":    "type",
        "required": False,
        "validate": None,          # no live check needed
        "prefill":  None,
        "edge":     False,
    },
]

# Validator registry — key matches CLAIM_FIELDS[*].validate
# Each callable: (value: str, session_id: str | None) -> dict {ok: bool|None, message: str}
# ok=True: valid. ok=False: invalid (show red). ok=None: soft-fail/unknown (show amber, allow proceed).
VALIDATORS: dict[str, callable] = {
    "sapo_order": _validate_sapo_order,   # defined below in same file
}
```

`_validate_sapo_order(value, session_id)` imports and delegates to `sapo_order_proxy.check_order_exists(value)` (the proxy module introduced below). This keeps `claim_fields.py` free of HTTP logic.

Adding a new external field = append one dict to `CLAIM_FIELDS` + add one function to `VALIDATORS` only when the external system is genuinely new. Adding a local-only metadata field = append dict, no validator.

#### 2. `sapo_order_proxy.py` — Sapo HTTP check (NEW FILE, moved from Phase 3 original plan)

`crm/src/hug/sapo_order_proxy.py`: `check_order_exists(order_code: str) -> dict`

- Reads `SAPO_API_URL`, `SAPO_API_KEY` via `hug.config` helpers (added in this phase).
- If either unset → `{"ok": None, "message": "Sapo chưa cấu hình"}` — soft-fail.
- `GET {SAPO_API_URL}/admin/orders.json?code={encoded}&fields=id,code,status` with `Authorization: Bearer {SAPO_API_KEY}` and `User-Agent: crm-hug-claim/1.0` (Cloudflare Bot Fight Mode mitigation — see MEMORY `feedback_cloudflare_botfight_useragent.md`).
- Timeout: 3 s (`urllib.request.urlopen(req, timeout=3)`).
- Any exception, HTTP 5xx → `{"ok": None, "message": "Không kiểm tra được (Sapo không phản hồi)"}`.
- HTTP 4xx → `{"ok": None, "message": "Lỗi xác thực Sapo"}` (soft-fail; never expose status code).
- HTTP 200 + `orders` array non-empty → `{"ok": True, "message": "Đơn hợp lệ"}`.
- HTTP 200 + `orders` empty → `{"ok": False, "message": "Mã đơn không tồn tại"}`.
- Uses stdlib `urllib.request` only (same pattern as `d1_transport.py`). No new dependency.

#### 3. `hug/config.py` — two new env readers

```python
def sapo_api_url() -> str:
    return os.environ.get("SAPO_API_URL", "").rstrip("/")

def sapo_api_key() -> str:
    return os.environ.get("SAPO_API_KEY", "")
```

#### 4. SQLite schema — two new nullable columns on `hug_token`

Added to `_SCHEMA` in `crm/src/hug/db.py` as idempotent `ALTER TABLE` statements (same pattern as existing schema):

```sql
ALTER TABLE hug_token ADD COLUMN IF NOT EXISTS bind_session_id TEXT;
ALTER TABLE hug_token ADD COLUMN IF NOT EXISTS bind_attributes TEXT;
```

- `bind_session_id TEXT` — client-generated UUID; session idempotency.
- `bind_attributes TEXT` — JSON blob for all dynamic fields NOT already promoted columns. At current config `order_code` and `is_gift` are promoted; `bind_attributes` starts as `{}` (empty object) for new binds. Future local-only metadata fields go here with no schema change.

Both nullable → zero impact on existing rows. No separate migration file — `executescript(_SCHEMA)` is already idempotent (`:71`).

Trigger: `docker compose restart crm` (one-time; hot-reload does not re-run `db.connect()`).

#### 5. `bind_token` — updated signature and idempotency

`crm/src/hug/repository.py:91`:

New signature:
```python
def bind_token(
    conn,
    token,
    *,
    order_code: str,
    is_gift: bool = False,
    channel: str | None = None,
    campaign_hint: str | None = None,
    bind_session_id: str | None = None,
    bind_attributes: dict | None = None,   # NEW
) -> sqlite3.Row:
```

Idempotency logic (replaces guard at `:110-113`):
```
if row["status"] == "bound":
    if row["order_code"] and row["order_code"] != order_code:
        raise ValueError("token already bound to a different order ({row['order_code']})")
    # Same order — check session
    stored_session = row["bind_session_id"]
    if stored_session and bind_session_id and stored_session != bind_session_id:
        raise ValueError("token already claimed in a different operation")
    # Same session (or either side None) → allow re-bind (fall through to UPDATE)
```

UPDATE statement (`:118-131`) gains `bind_session_id=?` and `bind_attributes=?` in SET clause. `bind_attributes` is serialised as `json.dumps(bind_attributes or {})`.

Callers:
- `screen_hug_claim.py:63` (existing form POST) — passes no new params → both default to `None` → session check skipped, `bind_attributes` stored as `'{}'`. Graceful.
- New AJAX bind endpoint (Step 6 below) — passes both.

#### 6. Generic `GET /hug/claim/check-field` endpoint

Replaces the order-specific `check-order` from the original Phase 3. The Sapo validator is now just one entry in `VALIDATORS`.

```
GET /hug/claim/check-field?key=<field_key>&value=<value>&session=<session_id>
```

- Look up `key` in `CLAIM_FIELDS`; if not found → 400.
- If `field.validate` is None → `{"ok": True, "message": "OK"}` immediately (no external check).
- Call `VALIDATORS[field.validate](value, session)` → return its `{ok, message}` dict.
- Never raises to the client — any unhandled exception in validator → `{"ok": None, "message": "Lỗi kiểm tra"}`.

#### 7. `GET /hug/claim/check-token` endpoint (carried from original Phase 2 — unchanged semantics)

```
GET /hug/claim/check-token?token=<token>&session=<session_id>
```

Returns `{state, message}` where `state` ∈ `{invalid, unknown, ready, rebind_ok, blocked}`.

Logic:
- `normalize_input(token)` → `is_valid_token` guard.
- `get_token` → None → `{state: "unknown"}`.
- `row["status"] == "printed"` → `{state: "ready"}`.
- `row["status"] == "bound"`: compare `row["bind_session_id"]` vs request `session`.
  - Same session (both non-empty, equal) → `{state: "rebind_ok"}`.
  - Different session → `{state: "blocked"}`.
  - Either side None → `{state: "rebind_ok"}` (no session semantics; fallback path).

#### 8. `POST /hug/claim/bind` AJAX endpoint

JSON body: `{session_id, fields: {order_code: "SON123", is_gift: false, ...}}`.

Server-side re-validates all required fields via the registry before binding. Does NOT trust the frontend's pre-validation.

Flow:
1. Extract `session_id` and `fields` dict from body.
2. For each field in `CLAIM_FIELDS` where `required=True`: check `fields[key]` non-empty — 200 `{ok:false}` if missing.
3. For each field where `validate` is not None: call `VALIDATORS[field.validate](fields[key], session_id)`. If `ok=False` → return `{ok:false, message}`. If `ok=None` (soft-fail) → log warning, allow proceed.
4. Split fields into promoted columns + `bind_attributes`:
   - Promoted: `order_code`, `is_gift` (known schema columns).
   - `bind_attributes`: remaining dynamic fields (currently empty; future fields land here automatically).
5. Call `bind_token(conn, token, order_code=..., is_gift=..., bind_session_id=session_id, bind_attributes=bind_attrs)`.
6. D1 push (best-effort). Return `{ok: True, message: str, edge: str}`.

HTTP 200 always. Errors encoded in `{ok: False, message}`.

The split between promoted columns and `bind_attributes` is determined by checking which keys are promoted schema columns. A simple constant `_PROMOTED_COLS = {"order_code", "is_gift"}` in `screen_hug_claim.py` handles this. Adding a future field that is local-only = it goes into `bind_attributes` automatically (not in `_PROMOTED_COLS`). Adding a field that also needs a dedicated column = add to `_PROMOTED_COLS` + schema + `bind_token` signature (rare; only for indexed lookups).

#### 9. Existing `POST /hug/claim` (no-JS fallback) — unchanged

`screen_hug_claim.py:45-88`. Calls `bind_token(..., bind_session_id=None, bind_attributes=None)`. Session check skipped (graceful). `bind_attributes` stored as `{}`.

## Data flows

```
claim_fields.py CLAIM_FIELDS
      │
      ├─ check-field endpoint
      │     → VALIDATORS[key](value, session)
      │           → sapo_order_proxy.check_order_exists()
      │                 → urllib GET Sapo REST API (3s timeout)
      │                 → {ok: True|False|None, message}
      │
      ├─ bind endpoint
      │     → re-validate all required fields via VALIDATORS
      │     → split into promoted cols + bind_attributes dict
      │     → repository.bind_token(... bind_session_id, bind_attributes)
      │           → UPDATE hug_token SET ... bind_session_id=?, bind_attributes=?
      │     → d1_push.push_bound_token(row)   [best-effort, Phase 4 adds attributes]
      │
      └─ check-token endpoint
            → repository.get_token()
            → session id comparison
            → {state, message}
```

## Files to create

| File | Purpose |
|------|---------|
| `crm/src/hug/claim_fields.py` | `CLAIM_FIELDS` list + `VALIDATORS` dict + `_validate_sapo_order` wrapper |
| `crm/src/hug/sapo_order_proxy.py` | `check_order_exists()` — Sapo HTTP, stdlib only |

## Files to modify

| File | Change |
|------|--------|
| `crm/src/hug/db.py` | Add two `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` to `_SCHEMA` |
| `crm/src/hug/repository.py` | Add `bind_session_id`, `bind_attributes` params to `bind_token`; update UPDATE SET; expand idempotency guard |
| `crm/src/hug/config.py` | Add `sapo_api_url()` and `sapo_api_key()` readers |
| `crm/src/adapters/inbound/web/screen_hug_claim.py` | Add `check-field`, `check-token`, `bind` endpoints inside `make_hug_claim_router`; add `_PROMOTED_COLS` constant |
| `docker-compose.yml` | Add `SAPO_API_URL` and `SAPO_API_KEY` under `crm:` → `environment:` |

## Implementation steps

1. **`claim_fields.py`** — write `CLAIM_FIELDS` list with `order_code` (validate=`sapo_order`, edge=True) and `is_gift` (validate=None, edge=False). Write `_validate_sapo_order(value, session_id)` wrapper (imports `sapo_order_proxy`). Write `VALIDATORS` dict.

2. **`sapo_order_proxy.py`** — implement `check_order_exists`. Import `sapo_api_url`, `sapo_api_key` from `hug.config`. Use `urllib.request` with 3 s timeout. Set `User-Agent: crm-hug-claim/1.0`. Soft-fail on all error paths (exception, 4xx, 5xx, unset env). Return `{ok: True|False|None, message: str}`.

3. **`hug/config.py`** — add `sapo_api_url()` and `sapo_api_key()` after existing functions.

4. **`crm/src/hug/db.py`** — in `_SCHEMA` string (`:22`), add after the `CREATE UNIQUE INDEX` / index block (before closing `"""`):
   ```sql
   ALTER TABLE hug_token ADD COLUMN IF NOT EXISTS bind_session_id TEXT;
   ALTER TABLE hug_token ADD COLUMN IF NOT EXISTS bind_attributes TEXT;
   ```
   These run every `connect()` call via `executescript`; `ADD COLUMN IF NOT EXISTS` is a no-op when column already exists.

5. **`crm/src/hug/repository.py:91`** — update `bind_token` signature (add `bind_session_id: str | None = None`, `bind_attributes: dict | None = None`). Expand idempotency guard. Add `import json` at top. In UPDATE statement, append `bind_session_id=?, bind_attributes=?`; pass `(bind_session_id, json.dumps(bind_attributes or {}))`.

6. **`crm/src/adapters/inbound/web/screen_hug_claim.py`** — add three new endpoints inside `make_hug_claim_router`:
   - `GET /hug/claim/check-field` — dispatches to `VALIDATORS` via `CLAIM_FIELDS` lookup.
   - `GET /hug/claim/check-token` — session-aware token state.
   - `POST /hug/claim/bind` — server-side re-validate → `bind_token` → D1 push → JSON.
   Add `_PROMOTED_COLS = {"order_code", "is_gift"}` constant at module level. Add `from hug.claim_fields import CLAIM_FIELDS, VALIDATORS` import.

7. **`docker-compose.yml`** — under `crm:` → `environment:` (`:164`), add:
   ```yaml
   - SAPO_API_URL=${SAPO_API_URL:-}
   - SAPO_API_KEY=${SAPO_API_KEY:-}
   ```
   Values in `.env` (gitignored). Empty defaults → proxy soft-fails when unset.

8. **Deploy** — `docker compose restart crm` (one-time: re-runs schema bootstrap → adds two columns). Subsequent code edits hot-reload without restart.

## Test matrix

| Layer | What | How |
|-------|------|-----|
| Unit | `check_order_exists` — orders found | Mock `urllib.request.urlopen` |
| Unit | `check_order_exists` — empty orders | Mock returns `{"orders":[]}` |
| Unit | `check_order_exists` — timeout → `ok=None` | Mock raises `TimeoutError` |
| Unit | `check_order_exists` — unset env → `ok=None` | Clear env vars in test |
| Unit | `check_order_exists` — HTTP 401 → `ok=None` | Mock HTTP 401 response |
| Unit | `bind_token` + same-session rebind → allowed | In-memory SQLite, pytest |
| Unit | `bind_token` + cross-session block → `ValueError` | Same |
| Unit | `bind_token` + `bind_session_id=None` (fallback) → binds | Same |
| Unit | `bind_token` stores `bind_attributes` as JSON in column | Read back column, `json.loads` |
| Unit | `CLAIM_FIELDS` — `order_code` entry has `edge=True`, `validate="sapo_order"` | Direct assertion |
| Unit | `VALIDATORS["sapo_order"]` soft-fails when Sapo down | Mock proxy |
| Integration | `GET /hug/claim/check-field?key=order_code&value=SON1` | `TestClient` — mock proxy at module level |
| Integration | `GET /hug/claim/check-field?key=unknown_key` → 400 | Same |
| Integration | `GET /hug/claim/check-field?key=is_gift&value=1` → `ok=True` (no validator) | Same |
| Integration | `GET /hug/claim/check-token` — all 5 states | `TestClient` |
| Integration | `POST /hug/claim/bind` — valid → `{ok:true}` | `TestClient` |
| Integration | `POST /hug/claim/bind` — cross-session → `{ok:false}` | Same |
| Integration | `POST /hug/claim/bind` — missing required field → `{ok:false}` | Same |
| Integration | Existing `POST /hug/claim` (form POST) still works after signature change | Same |
| Manual | `docker compose restart crm` → `sqlite3 hug.db ".schema hug_token"` shows two new columns | Inside container |

## Success criteria
- `hug_token` table has `bind_session_id` and `bind_attributes` columns after restart.
- `GET /hug/claim/check-field?key=order_code&value=SON123` → `{ok:true|false|null}` (Sapo creds configured or not).
- `GET /hug/claim/check-field?key=is_gift&value=1` → `{ok:true}` (no validator → immediate pass).
- `GET /hug/claim/check-token?token=<printed>&session=<uuid>` → `{state:"ready"}`.
- `POST /hug/claim/bind` with `{session_id, fields:{order_code:"SON1", is_gift:false}}` → `{ok:true}`.
- Same `POST /hug/claim/bind` with different session → `{ok:false, message:"...different operation..."}`.
- Existing form `POST /hug/claim` still renders HTML success page.
- All unit + integration tests pass.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Sapo REST API only supports cookie auth (no key) | Medium | Medium | Proxy always soft-fails → `ok=None` → amber → station fully usable; verify in Sapo admin before Step 2 |
| `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` not on old SQLite | Low | Medium | Python 3.12 ships SQLite ≥ 3.39; confirm with `import sqlite3; sqlite3.sqlite_version` in healthcheck |
| `_PROMOTED_COLS` constant diverges from actual `bind_token` promoted params | Medium | Medium | Single source of truth: define `_PROMOTED_COLS` in `screen_hug_claim.py` and add a unit test that asserts `_PROMOTED_COLS ⊆ {param names of bind_token excluding token/conn}` |
| Validator soft-fail masking real Sapo errors (always amber) | Low | Low | Log warning with status code on every 4xx/5xx for ops visibility; never surface to kiosk JS |
| `bind_session_id=None` fallback: `check-token` returns `rebind_ok` when stored session is None | Intentional | — | Documented: when stored is None, rebind_ok is correct (form POST path set no session; no session to block against) |
| JSON column `bind_attributes` grows unbounded with many future fields | Very Low | Very Low | All dynamic field values are short strings/bools; for MVP, no size limit needed (YAGNI) |

## Rollback
Remove the two `ALTER TABLE` lines from `_SCHEMA` → `docker compose restart crm`. The two columns remain in the SQLite file (unused, harmless). Remove `claim_fields.py` + `sapo_order_proxy.py` + three new endpoints → hot-reload. No data loss.

## Unresolved questions
1. **Sapo API key format:** does `fwg.mysapogo.com` support `Authorization: Bearer <key>` or only cookie sessions? Verify in Sapo admin console before implementing `sapo_order_proxy.py`. If only cookie auth, validator always returns `ok=None` (soft-fail) and the check-field result is always amber — acceptable degradation.
2. **`_PROMOTED_COLS` maintenance:** if `bind_token` gains a new promoted parameter in the future, `_PROMOTED_COLS` must be updated in the same PR. Add a comment to `_PROMOTED_COLS` referencing `repository.py:bind_token` to make this discoverable.
