# Phase 3 — D1 match-count + matched-user-list preview endpoint

## Context links

- Plan overview: `plans/260623-0852-hug-campaign-matching-and-preview/plan.md`
- Research source: `plans/reports/hug-campaign-match-count-ui-from-d1-260623-0852-report.md` §2–§4
- TS matcher: `webhook_receiver/cloudflareD1/src/hug-handler.ts:148–189` (matchesTargeting — reused verbatim)
- Route table: `webhook_receiver/cloudflareD1/src/index.ts:18–36`
- Admin HMAC: `webhook_receiver/cloudflareD1/src/hug-handler.ts:317–327` (verifyAdminHmac — reused)
- Transport: `crm/src/hug/d1_transport.py:34–71` (post_signed — extend to return body)
- Config gate: `crm/src/hug/config.py:54–56` (push_enabled())
- Current preview call site: `crm/src/adapters/inbound/web/screen_hug_campaign.py:324`
- Preview render: `crm/src/adapters/inbound/web/screen_hug_campaign_html_preview.py:14–136`
- Touchpoint-level warning: `crm/src/adapters/inbound/web/screen_hug_campaign.py:292–307`
- Tests: `crm/src/tests/test_hug_targeting_engine.py` (P01–P03 preview cases)

## Overview

- **Priority:** P1
- **Status:** pending (blocked on Phase 2 Worker deploy — `customer_type` must be in `ScanContext` before preview counts it)
- **Worker deploy required:** YES (new route `POST /hug/campaign/preview`)
- **D1 schema migration:** No
- **CRM container rebuild:** No (`crm/src` is volume-mounted)

## Verified facts

- `matchesTargeting` at `hug-handler.ts:148–189` is a pure function (no I/O, no side effects). It accepts `(targetingJson: string, ctx: ScanContext)` and returns `boolean`. Reusing it directly in the new handler eliminates any logic duplication risk.
- `verifyAdminHmac` at `hug-handler.ts:317–327` uses `HUG_ADMIN_SECRET` + `X-Hug-Signature: sha256=<hex>`. Exactly the same auth pattern as `handleHugTokenUpsert`, `handleHugCustomerUpsert`, `handleHugCampaignUpsert`. No new secrets needed.
- `post_signed` at `d1_transport.py:34–71` discards the response body entirely (line 65: `return {"ok": True, "status": resp.status}`). To get the preview JSON back, a new function must read and parse `resp.read()`.
- `push_enabled()` at `config.py:54–56` returns `bool(worker_url())`. Used in `customer_push.run()` to gate the push. Same gate can gate the D1 preview call.
- `_rerender_with_preview` at `screen_hug_campaign.py:310–344` has a single `preview_result = preview_match_customers(targeting, _cache_db_path())` call at line 324. One swap point.
- `render_preview_panel` at `screen_hug_campaign_html_preview.py:14–136` already renders `matched`, `total`, `sample` list, `upper_bound_warning`, and an error state. It needs extension for: source badge, `data_as_of`, and larger paginated customer list.
- `hug_customer` D1 has NO `name`, `phone`, or `email` columns (confirmed at `schema_hug.sql:35–42`). Preview response contains only `customer_id`, `tier`, `recency_days`, `value_group`, `is_contactable` (and `customer_type` after Phase 2). PII boundary is clean.
- Touchpoint-level attrs (`op_type`, `channel`, `sku`) are in `hug_token`, not `hug_customer`. A `SELECT * FROM hug_customer` preview cannot count them per-customer. Upper-bound warning already exists in `screen_hug_campaign.py:292–307`; the same logic applies to the D1 preview path.
- D1 full-scan of 7.5k `hug_customer` rows with no SQL WHERE filter + TS loop is estimated <10ms at D1 latency. Acceptable for an admin action (not on the hot scan path).
- `_campaignCache` at `hug-handler.ts:96–98` is irrelevant here — the preview endpoint is a new path with no cache.
- Route registration pattern in `index.ts`: import function from `hug-handler.ts`, add `if (request.method === "POST" && url.pathname === "/hug/...") { return handleXxx(...); }` (lines 28–36). Additive; existing routes untouched.

## Requirements

### Functional
1. `POST /hug/campaign/preview` Worker endpoint, HMAC-secured, accepts `{targeting, limit?, offset?}`, returns `{count, total_customers, data_as_of, customers: [...]}`.
2. Matching logic: reuses `matchesTargeting` exactly — no new implementation.
3. Python: new `post_signed_and_read` function in `d1_transport.py` that returns the parsed JSON body on success.
4. Python: new `preview_match_customers_d1` function (in `targeting_engine.py` or a new `d1_preview.py`) that calls the Worker endpoint; falls back to `preview_match_customers(cache.db)` when `push_enabled()` is False or the call fails.
5. `_rerender_with_preview` in `screen_hug_campaign.py` swaps to `preview_match_customers_d1` when D1 is available.
6. `render_preview_panel` in `screen_hug_campaign_html_preview.py` shows: source badge (D1 vs cache.db), `data_as_of`, matched customer list (up to 50 rows flat for v1 — no pagination), exact count (no `~` tilde) when source is D1.
7. Upper-bound warning retained for touchpoint-level attrs — unchanged behavior.

### Non-functional
- Fallback to `cache.db` when `HUG_WORKER_URL` unset preserves dev-mode usability.
- Graceful degradation: if Worker call fails (timeout, 5xx), fall back to `cache.db` preview with a notice; never crash the admin UI.
- Timeout on Worker call: 8s (reuse `_TIMEOUT_S` from `d1_transport.py:23`).
- `limit` default 50, max 200. `offset` default 0. Admin-only endpoint; D1 scan of 7.5k rows is single-query.
- No new secrets; `HUG_ADMIN_SECRET` is sufficient.

## Architecture

```
CRM admin UI (POST action=preview)
  ↓ screen_hug_campaign.py:_rerender_with_preview()
  ↓ if push_enabled():
      preview_match_customers_d1(targeting, limit=50) [new]
        ↓ post_signed_and_read(url, secret, body) [new in d1_transport.py]
          ↓ POST /hug/campaign/preview (Worker)
            ↓ verifyAdminHmac (existing)
            ↓ SELECT * FROM hug_customer (all rows, no filter)
            ↓ for each row: build ctx dict → matchesTargeting(targeting, ctx)
            ↓ collect count + page
            ↓ → {count, total_customers, data_as_of, customers:[...]}
        ← JSON body parsed → preview dict with "source":"d1"
      ← fallback on error: preview_match_customers(cache.db) + "source":"cache"
  else:
      preview_match_customers(targeting, cache_db_path()) [existing]
  ↓ render_campaign_form(..., preview=preview_result)
  ↓ render_preview_panel(preview, overlaps, priority) [extended]
```

## Data flow

```
Request body (Worker):
  {"targeting": {"tier": ["VIP"], "customer_type": {"not_in": ["WHOLESALE"]}},
   "limit": 50, "offset": 0}

Worker processing:
  1. verifyAdminHmac(request, body, env) → bool
  2. JSON.parse(body) → {targeting, limit, offset}
  3. db.prepare("SELECT customer_id, tier, recency_days, value_group,
                          is_contactable, customer_type, updated_at
                 FROM hug_customer ORDER BY customer_id")
     .all<HugCustomer>()
  4. for row of results:
       ctx = {tier, recency_days, value_group, is_contactable, customer_type,
              op_type: null, channel: null, sku: null,   // touchpoint attrs absent → no constraint
              customer_id: row.customer_id,
              order_code: null, ship_date: null}         // not in hug_customer
       if matchesTargeting(JSON.stringify(targeting), ctx): push to matched[]
  5. count = matched.length
  6. total_customers = results.length
  7. data_as_of = max(updated_at) across all results (or null if empty)
  8. page = matched.slice(offset, offset + limit)

Response body:
  {"count": 312, "total_customers": 7543,
   "data_as_of": "2026-06-22T23:15:00Z",
   "customers": [{"customer_id":"1234","tier":"VIP","recency_days":12,
                  "value_group":"HIGH","is_contactable":1,"customer_type":"RETAIL"}, ...]}

Python post_signed_and_read return:
  Success: {"ok": True, "status": 200, "data": {count, total_customers, data_as_of, customers}}
  Failure: {"ok": False, "error": "<str>"}

preview_match_customers_d1 return (same shape as preview_match_customers):
  {"matched": 312, "total": 7543, "sample": [...up to 50 rows...],
   "source": "d1", "data_as_of": "2026-06-22T23:15:00Z"}
  or on fallback:
  {"matched": N, "total": M, "sample": [...5 rows...], "source": "cache",
   "fallback_reason": "<str>"}
```

**ScanContext shape in preview handler (TS):** The preview builds a ctx object from `hug_customer` columns only. Touchpoint attrs (`op_type`, `channel`, `sku`, `order_code`, `ship_date`) are absent from `hug_customer` and must be set to `null` in the ctx. `matchesTargeting` treats a constrained attr with `null` ctx as no-match — meaning a campaign targeting `{"op_type": ["package_insert"]}` will match ZERO customers in the D1 preview (since all `op_type` values are null). This is expected and must be surfaced in the upper-bound warning — when `op_type`/`channel`/`sku` are in targeting, the D1 count is 0 (not upper-bound). The warning must be updated: for D1 source, touchpoint-level attrs produce a 0-count, not an upper bound.

**Decision:** For D1 preview, if targeting contains touchpoint-level attrs, skip those keys when building the ctx (treat as "no constraint") — the same behavior as the cache.db preview path. This avoids a confusing "0 matches" when the real count is much higher. Set a flag `upper_bound` in the response to communicate this to the UI.

Revised Worker logic: before matching, parse targeting and remove touchpoint-level attr keys (`op_type`, `channel`, `sku`). Use the stripped targeting for the D1 loop. Return `{"upper_bound": true}` alongside count when stripping occurred.

The touchpoint-level attr list must be hardcoded in the Worker (it cannot import Python's `TARGETING_CATALOG`). Use a constant: `const TOUCHPOINT_ATTRS = new Set(["op_type", "channel", "sku"])`. When Phase 1 adds `sku` to the catalog with `touchpoint_level: true`, this set is already correct.

## Files to modify

| File | Change |
|------|--------|
| `webhook_receiver/cloudflareD1/src/hug-handler.ts` | Add `handleHugCampaignPreview(request, env)` function + export (after `handleHugCampaignUpsert`, around line 807) |
| `webhook_receiver/cloudflareD1/src/index.ts` | Import `handleHugCampaignPreview` (line 9); add route `POST /hug/campaign/preview` (after line 35) |
| `crm/src/hug/d1_transport.py` | Add `post_signed_and_read(url, secret, payload) -> dict` function (after `post_signed`, around line 72) |
| `crm/src/hug/targeting_engine.py` | Add `preview_match_customers_d1(targeting, limit, offset) -> dict` function (after `preview_match_customers`, around line 181); update module docstring |
| `crm/src/adapters/inbound/web/screen_hug_campaign.py` | In `_rerender_with_preview` (line 324): replace direct `preview_match_customers(...)` call with conditional D1/cache dispatch; import `preview_match_customers_d1` |
| `crm/src/adapters/inbound/web/screen_hug_campaign_html_preview.py` | Extend `render_preview_panel` signature to accept `source` and `data_as_of` from preview dict; add source badge, data_as_of, show up to 50 rows (was 5); update count display (remove `~` when source=d1) |

## Files to create

None. All changes are extensions to existing files.

## Implementation steps

### Step 1 — Add `handleHugCampaignPreview` to `hug-handler.ts`

Add after `handleHugCampaignUpsert` (end of file, around line 807). Key implementation notes:

```typescript
export async function handleHugCampaignPreview(
    request: Request,
    env: Env,
): Promise<Response> {
    const body = await request.text();
    if (!(await verifyAdminHmac(request, body, env))) {
        return new Response('Unauthorized', { status: 401 });
    }

    let parsed: { targeting: Record<string, unknown>; limit?: number; offset?: number };
    try { parsed = JSON.parse(body); } catch {
        return new Response('Invalid JSON', { status: 400 });
    }

    const limit  = Math.min(parsed.limit  ?? 50, 200);
    const offset = Math.max(parsed.offset ?? 0,  0);

    // Touchpoint-level attrs are not in hug_customer — strip them before matching
    // so they are treated as "no constraint" rather than "no match" (null ctx value
    // always fails a constrained key; stripping avoids a misleading zero count).
    const TOUCHPOINT_ATTRS = new Set(['op_type', 'channel', 'sku']);
    const rawTargeting = parsed.targeting ?? {};
    const upperBound = Object.keys(rawTargeting).some((k) => TOUCHPOINT_ATTRS.has(k));
    const targeting: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(rawTargeting)) {
        if (!TOUCHPOINT_ATTRS.has(k)) targeting[k] = v;
    }
    const targetingJson = JSON.stringify(targeting);

    // Fetch all hug_customer rows (no SQL filter — matchesTargeting applied in TS loop)
    const { results } = await env.DB.prepare(
        `SELECT customer_id, tier, recency_days, value_group,
                is_contactable, customer_type, updated_at
         FROM hug_customer
         ORDER BY customer_id`
    ).all<HugCustomer>();

    const allRows = results ?? [];
    const totalCustomers = allRows.length;

    // Compute data_as_of: max(updated_at) — lexicographic max works for ISO strings
    let dataAsOf: string | null = null;
    for (const r of allRows) {
        if (r.updated_at && (dataAsOf === null || r.updated_at > dataAsOf)) {
            dataAsOf = r.updated_at;
        }
    }

    // Apply matchesTargeting over customer rows
    // Touchpoint attrs absent from hug_customer → set null → treated as no constraint
    // (already stripped from targeting above, so no-constraint = always-pass for those keys)
    const matched: HugCustomer[] = [];
    for (const row of allRows) {
        // Build a ScanContext-compatible object from customer fields only.
        // Touchpoint fields (op_type, channel, sku, order_code, ship_date) not available
        // → null; stripped from targeting above so they never cause a false-false match.
        const ctx = {
            tier:           row.tier,
            recency_days:   row.recency_days,
            value_group:    row.value_group,
            is_contactable: row.is_contactable,
            customer_type:  row.customer_type ?? null,
            customer_id:    row.customer_id,
            op_type:        null,
            channel:        null,
            sku:            null,
            order_code:     null,
            ship_date:      null,
        } as unknown as ScanContext;

        if (matchesTargeting(targetingJson, ctx)) {
            matched.push(row);
        }
    }

    const page = matched.slice(offset, offset + limit);

    return Response.json({
        count:           matched.length,
        total_customers: totalCustomers,
        data_as_of:      dataAsOf,
        upper_bound:     upperBound,
        customers:       page,
    });
}
```

### Step 2 — Register route in `index.ts`

Add import (line 9):
```typescript
import {
    handleHugScan,
    handleHugOptinLanding,
    handleHugTokenUpsert,
    handleHugCustomerUpsert,
    handleHugCampaignUpsert,
    handleHugCampaignPreview,   // new
} from './hug-handler';
```

Add route after the campaign upsert route (after line 35):
```typescript
if (request.method === "POST" && url.pathname === "/hug/campaign/preview") {
    return handleHugCampaignPreview(request, env);
}
```

### Step 3 — Worker deploy

```bash
cd webhook_receiver/cloudflareD1 && wrangler deploy
```

Additive route — no existing handler touched. Roll forward only; no migration needed.

### Step 4 — Add `post_signed_and_read` to `d1_transport.py`

Insert after `post_signed` (around line 72):

```python
def post_signed_and_read(
    url: str,
    secret: str,
    payload: dict[str, Any],
    *,
    timeout_s: int = _TIMEOUT_S,
) -> dict[str, Any]:
    """POST *payload* as JSON to *url* with HMAC signature, returns parsed response body.

    Extends post_signed() by reading and JSON-parsing the response body on success.
    Used for admin endpoints that return structured data (e.g. campaign preview).

    Returns:
      {"ok": True,  "status": <int>, "data": <parsed JSON>}   — success
      {"ok": False, "error": <str>}                           — HTTP or network failure
      {"ok": False, "error": "invalid json: ..."}             — response not JSON

    Never raises.
    """
    raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=raw_body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Hug-Signature": sign(secret, raw_body),
            "User-Agent": _USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                log.error("hug preview: response not JSON at %s — %s", url, exc)
                return {"ok": False, "error": f"invalid json: {exc}"}
            return {"ok": True, "status": resp.status, "data": data}
    except urllib.error.HTTPError as exc:
        body_snippet = ""
        try:
            body_snippet = exc.read(200).decode("utf-8", errors="replace")
        except Exception:
            pass
        log.error("hug preview: HTTP %d at %s — %s %s", exc.code, url, exc.reason, body_snippet)
        return {"ok": False, "error": f"http {exc.code}"}
    except Exception as exc:
        log.error("hug preview: failed at %s — %s", url, exc)
        return {"ok": False, "error": str(exc)}
```

### Step 5 — Add `preview_match_customers_d1` to `targeting_engine.py`

Add after `preview_match_customers` (after line 180). Place in same file (DRY — keeps preview logic in one module; the function is small):

```python
def preview_match_customers_d1(
    targeting: dict,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Preview campaign match count using the live D1 hug_customer replica.

    Calls POST /hug/campaign/preview on the Worker (verifyAdminHmac-secured).
    Returns a dict compatible with preview_match_customers():
      {"matched": int, "total": int, "sample": list[dict],
       "source": "d1", "data_as_of": str|None, "upper_bound": bool}

    Falls back to preview_match_customers(cache.db) when Worker is not configured
    or the call fails. Fallback result includes "source": "cache" and
    "fallback_reason": str so the UI can show a notice.

    Never raises.
    """
    from hug.config import admin_secret, push_enabled, worker_url
    from hug.d1_transport import post_signed_and_read
    import os

    if not push_enabled():
        result = preview_match_customers(targeting, _default_cache_db_path())
        result["source"] = "cache"
        result["fallback_reason"] = "D1 preview not configured (HUG_WORKER_URL unset)"
        return result

    secret = admin_secret()
    if not secret:
        result = preview_match_customers(targeting, _default_cache_db_path())
        result["source"] = "cache"
        result["fallback_reason"] = "HUG_ADMIN_SECRET not set"
        return result

    url = worker_url() + "/hug/campaign/preview"
    payload = {"targeting": targeting, "limit": limit, "offset": offset}
    resp = post_signed_and_read(url, secret, payload)

    if not resp["ok"]:
        log.warning("preview_match_customers_d1: Worker call failed (%s), falling back to cache.db",
                    resp.get("error"))
        result = preview_match_customers(targeting, _default_cache_db_path())
        result["source"] = "cache"
        result["fallback_reason"] = f"D1 preview failed: {resp.get('error')}"
        return result

    data = resp["data"]
    customers = data.get("customers", [])
    return {
        "matched":       data.get("count", 0),
        "total":         data.get("total_customers", 0),
        "sample":        customers,   # up to `limit` rows (not capped at 5)
        "source":        "d1",
        "data_as_of":    data.get("data_as_of"),
        "upper_bound":   data.get("upper_bound", False),
    }


def _default_cache_db_path() -> str:
    """Resolve cache.db path from env (mirrors screen_hug_campaign.py._cache_db_path)."""
    import os
    default_dir = os.environ.get("CRM_DATA_DIR", "./data")
    return os.environ.get("CRM_CACHE_DB", os.path.join(default_dir, "cache.db"))
```

Update module docstring (line 8) to add `preview_match_customers_d1` to exported surface.

### Step 6 — Swap preview call site in `screen_hug_campaign.py`

In `_rerender_with_preview` (line 323–324), replace:

```python
preview_result = preview_match_customers(targeting, _cache_db_path())
```

with:

```python
from hug.targeting_engine import preview_match_customers_d1
preview_result = preview_match_customers_d1(targeting)
```

The import at the top of the file still imports `preview_match_customers` (used by fallback internally) — but the direct call in `_rerender_with_preview` is replaced. Remove the direct `from hug.targeting_engine import preview_match_customers` import from the top of `screen_hug_campaign.py` (line 40) if it is only used here; otherwise keep it.

The `_cache_db_path()` helper in `screen_hug_campaign.py` (line 285–289) becomes unused after this swap. Remove it to keep the file clean (or leave if referenced elsewhere — verify with grep before removing).

### Step 7 — Extend `render_preview_panel` in `screen_hug_campaign_html_preview.py`

Changes to `render_preview_panel(preview, overlaps, new_priority)` (line 14):

1. **Source badge:** read `preview.get("source", "cache")`. Display a small pill after the count:
   - `"d1"` → green pill `D1 · chính xác` (exact count)
   - `"cache"` → amber pill `cache.db · hôm qua` (yesterday's snapshot)
   - If `"fallback_reason"` present → add a small italic note below the badge.

2. **Count display:** when `source == "d1"`, remove the `~` tilde from the count header (the count is exact for customer-level attrs). When `upper_bound` is True (touchpoint-level attrs were stripped), keep `~` and retain the upper-bound warning.

3. **`data_as_of`:** when `source == "d1"` and `data_as_of` is present, add a subscript line below the count header: `Dữ liệu tính đến: {data_as_of}` (formatted as ICT date).

4. **Customer list table:** currently capped at 5 rows (`targeting_engine.py:171`). D1 response returns up to 50. Show all returned rows (no cap in the render function; the cap is set by `limit` in the request). Keep 5-row cap for `source == "cache"` path (unchanged behavior).

5. **Column additions for D1 path:** add `customer_type` column to the sample table when the preview dict rows include it (Phase 2 populates it). Guard with `.get("customer_type", "")` to be safe against cache.db rows that lack it.

6. **PII note:** add a comment in the template: `customer_id chỉ là mã Sapo (không có tên/SĐT)`.

Existing overlap warning section (lines 99–135) is unchanged.

### Step 8 — Update `index.test.ts` and add Python tests

**TS (`index.test.ts`):**
- Add a describe block `POST /hug/campaign/preview`:
  - auth: missing sig → 401; wrong sig → 401
  - empty targeting `{}` → 200, count == total (all customers)
  - tier filter → count subset
  - touchpoint attr in targeting (op_type) → count same as empty (stripped); `upper_bound: true`
  - offset/limit pagination: offset=1 → `customers` starts from index 1 of matched

**Python (`test_hug_targeting_engine.py`):**
- New preview D1 cases (PD-series):
  - `test_preview_d1_falls_back_when_push_disabled` — no `HUG_WORKER_URL` → source=cache
  - `test_preview_d1_falls_back_on_worker_error` — mock `post_signed_and_read` returns `{"ok": False, ...}` → source=cache + fallback_reason
  - `test_preview_d1_returns_d1_data_on_success` — mock returns valid response → matched count, source=d1, data_as_of present
  - `test_preview_d1_upper_bound_flag_set_for_touchpoint_attrs` — targeting with `op_type` key → `upper_bound: True` in Worker response propagated

**Python (`crm/src/tests/test_hug_d1_transport.py` — new file):**
- `test_post_signed_and_read_parses_json_response`
- `test_post_signed_and_read_returns_error_on_http_error`
- `test_post_signed_and_read_returns_error_on_invalid_json_response`
- `test_post_signed_and_read_never_raises`

## Test matrix

| Layer | Tool | Scope |
|-------|------|-------|
| TS preview handler | vitest (index.test.ts) | auth, count, filter, touchpoint strip, pagination |
| Python transport | pytest (test_hug_d1_transport.py) | post_signed_and_read success/error/invalid-json |
| Python D1 preview | pytest (test_hug_targeting_engine.py) | fallback paths, D1 success, upper_bound flag |
| UI render | manual / screenshot | source badge, data_as_of, 50-row list, ~ removal |

## Success criteria

- `POST /hug/campaign/preview` returns 401 without valid HMAC; 200 with correct `{count, total_customers, data_as_of, customers}` structure.
- `count + total_customers` agree with a direct `SELECT COUNT(*) FROM hug_customer` in D1 (for `{}` targeting).
- CRM admin preview panel shows "D1 · chính xác" badge and a list of matched customers (customer_id + tier) for a campaign with customer-level targeting.
- When `HUG_WORKER_URL` is unset in dev: preview falls back to cache.db silently, badge shows "cache.db · hôm qua".
- Campaign with `op_type` targeting: D1 preview shows upper-bound warning, count matches empty-targeting count (all customers), badge shows `~`.
- All existing P01–P03 preview tests in `test_hug_targeting_engine.py` pass unchanged.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Worker deploy blocked by pending unrelated changes | Low | Medium — Phase 3 cannot ship until deploy clears | Phase 3 Python side (transport, engine, screen) is deployable independently; only the new Worker route is blocked. CRM falls back to cache.db until deploy. |
| D1 full-scan latency spike on cold start (>1s) | Low | Low — admin action, not hot path | 8s timeout on transport; D1 cold-start typically <500ms on first request; subsequent requests within the same V8 isolate instance are warm |
| Touchpoint-attr stripping diverges between Worker and Python preview | Low | Medium — inconsistent counts between D1 and cache.db paths | Both paths strip touchpoint attrs and set `upper_bound=True`; assert this in tests. `TOUCHPOINT_ATTRS` set in TS must match `touchpoint_level=True` keys in Python catalog |
| `data_as_of` is null if `hug_customer` is empty (no rows) | Low | Low — UI must handle null gracefully | Guard in render: `if data_as_of: render timestamp else: omit` |
| `post_signed_and_read` timeout leaves admin UI frozen | Medium (first deploy, cold start) | Low | Show spinner in CRM UI during preview POST; 8s timeout is reasonable; fallback kicks in on timeout |
| `render_preview_panel` signature change breaks other callers | — | — | Grep confirms `render_preview_panel` is called only from `render_campaign_form` (in `screen_hug_campaign_html_form.py`) which passes the preview dict through. The dict gains new keys (`source`, `data_as_of`) — additive, no caller breakage. |

## Rollback

- **Worker:** redeploy previous build. The `/hug/campaign/preview` route disappears; CRM Python falls back to cache.db (the `push_enabled()` gate still returns True, but `post_signed_and_read` will get a 404, triggering fallback). Seamless.
- **Python:** revert `screen_hug_campaign.py` call site to `preview_match_customers(...)` (2-line change). No rebuild needed (volume-mounted).
- **D1:** no migration to revert.
- **Overall:** Phase 3 rollback has zero user-facing breakage — cache.db preview is always available as fallback.

## Permanent UI caveats (document in `render_preview_panel`)

Always shown regardless of source:
- Touchpoint-level attrs (`op_type`, `channel`, `sku`) → count is upper bound (D1 preview strips them; cache.db preview skips them). Display: `~N / M` with warning.
- D1 data is from the last nightly push; `data_as_of` shows staleness.
- New customers since the last push are absent from D1 (same gap as cache.db).
- `customer_id` is an opaque Sapo integer — no name/phone in this panel (PII boundary).

## Unresolved questions

1. **Pagination v1 scope:** plan specifies flat 50-row list (no paginated navigation). Confirm sufficient for v1, or add a `Tải thêm` button (adds ~1h). The Worker already supports `limit`/`offset`; only the UI work is deferred.
2. **`post_signed_and_read` placement:** kept in `d1_transport.py` (DRY — single signing implementation). Alternative: new `d1_preview.py`. Current choice is simpler; flag if the transport module grows beyond its current 72 lines.
3. **Spinner / loading state in CRM UI:** the preview POST takes up to 800ms on cold start. The existing form submit shows no loading state. Is a spinner acceptable to add, or out of scope for this plan?
4. **`data_as_of` timezone display:** the Worker stores `updated_at` as UTC ISO string (`strftime('%Y-%m-%dT%H:%M:%SZ', 'now')`). Display should convert to ICT (UTC+7) for the admin. Format: `strftime` in Python or a JS approach in the template? Simplest: format server-side in Python using `datetime.fromisoformat` + `astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))`.
5. **CSV export of matched customer list:** out of scope for v1. Note for Phase 4 if requested.
