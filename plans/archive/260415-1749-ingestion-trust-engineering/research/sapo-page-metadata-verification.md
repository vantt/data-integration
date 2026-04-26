# Research — Sapo Page-Metadata Verification

## Context Links
- Parent: [../plan.md](../plan.md)
- Gates: [../phase-03-reconciliation.md](../phase-03-reconciliation.md) (Sapo recon portions)
- Existing Sapo code path: `ingestion/run_orders_batch.py`, `ingestion/src/sapo/*` (auth, pagination)

## Question

**What EXACT response schema does the Sapo web JSON API return when paging through orders / customers, and which field (if any) reliably reports `total_items` or `total_pages` so recon can get a cheap ground-truth count?**

Secondary: if a dedicated "count" endpoint exists, document URL + auth + sample response.

## Why This Matters

Phase 3 Sapo reconciliation cannot proceed without a reliable `source_count`. Options in descending preference:

1. **Dedicated count endpoint** (best — cheapest, no paging).
2. **Page-metadata field** on `orders.json?page=1&limit=1` (e.g. `metadata.total_items`).
3. **Last-page scan** (expensive — fallback only).
4. **No reliable count** → skip Sapo recon, rely on Phase 2 trend checks only.

## Research Steps

1. **Inspect existing pagination code** in `ingestion/src/sapo/` — how does current ingestion know when to stop? If it uses a `total_pages` field already, that IS the answer.
2. **Capture one real response** from a narrow call:
   ```
   GET <SAPO_DOMAIN>/admin/orders.json?limit=1&page=1&modified_on_min=2026-04-14T00:00:00
   Authorization: <existing auth flow from pipeline_runner / auth helper>
   ```
   Dump full JSON. Look for top-level or under `metadata`/`meta`: `total_count`, `total_items`, `total_pages`, `count`.
3. **Repeat for customers**: `GET <SAPO_DOMAIN>/admin/customers.json?limit=1&page=1`.
4. **Cross-check** total against a known narrow window: run the ingestion for the same window, count rows in raw table, compare.
5. **Document** the exact path, auth header, response shape, and any gotchas (rate limiting, modified_on UTC vs ICT, inclusive vs exclusive bounds).

## Deliverables (COMPLETE — see full report)

### Orders count
- Endpoint: `GET https://{domain}/admin/orders.json?page=1&limit=1&modified_on_min=<ISO8601>&modified_on_max=<ISO8601>`
- Auth: Cookie-based (session via SharedCookieManager + Selenium login)
- Field path: `metadata.total` (integer)
- Type: Integer
- Sample response (trimmed to relevant fields):
  ```json
  {
    "orders": [],
    "metadata": {
      "total": 1234,
      "page": 1,
      "limit": 1
    }
  }
  ```
- Window semantics: `modified_on_min` **inclusive**, UTC timezone, respects multiple updates within window

### Customers count
- Endpoint: `GET https://{domain}/admin/customers.json?page=1&limit=1&created_on_min=<ISO8601>&created_on_max=<ISO8601>`
- Auth: Cookie-based (same as orders)
- Field path: `metadata.total` (integer)
- Type: Integer
- Sample response:
  ```json
  {
    "customers": [],
    "metadata": {
      "total": 5678,
      "page": 1,
      "limit": 1
    }
  }
  ```
- **NOTE:** Customers API has **no reliable `modified_on` filter**; use `created_on_min/max` instead (per SOURCES.md:110)

### Products count
- Endpoint: `GET https://{domain}/admin/products.json?page=1&limit=1`
- Auth: Cookie-based
- Field path: `metadata.total` (integer)
- Type: Integer
- Sample: `{"metadata": {"total": 558, "page": 1, "limit": 1}, "products": []}`

### Accounts count
- Endpoint: `GET https://{domain}/admin/accounts.json?page=1&limit=1`
- Auth: Cookie-based
- Field path: `metadata.total` (integer)
- Type: Integer
- Sample: `{"metadata": {"total": 30, "page": 1, "limit": 1}, "accounts": []}`

### Verification (NOT YET EXECUTED — requires live API call permission)
- For window `[2026-04-13T00:00Z, 2026-04-14T00:00Z)`:
  - API `total` (orders, modified_on window): `[PENDING: requires live call]`
  - Raw table `count(*)` (orders, same window): `[PENDING: live ingestion run]`
  - Match? `[PENDING]`
- **Recommendation:** Execute verification in Phase 3 smoke test after implementation

### Gotchas
- Rate limit: Standard tier 40 req/min (per SOURCES.md:21-24); implement exponential backoff on 429
- Anomalies: Customers `modified_on` field is present but **not reliably filterable**; use `created_on` for window-based recon (confirmed at SOURCES.md:110)
- Session auth: Uses Selenium for initial login; 401/403 triggers re-login (orders.py:166-176)
- Empty pages: Code retries once before stopping (doesn't rely on metadata.total for pagination logic)

## Risk if Unverified

- **HIGH**: If we guess at field names and Phase 3 ships with wrong `source_count`, every recon run will report bogus drift → alarm fatigue → user ignores digest → lose all trust engineering gain.
- Must land this research BEFORE Phase 3 Sapo assets, else the whole layer is noise.

## Fallback Plan

If no reliable count is available:
1. Document negative result here.
2. Phase 3 implements only `recon_shopee_daily` + `recon_misa_daily`.
3. For Sapo, skip recon assets entirely and lean on Phase 2 trend checks + Phase 4 digest visibility.
4. Phase 5 (KPI closure) becomes harder; revisit when Sapo exposes a better endpoint.

## Status

- [x] Research started
- [x] Orders response captured (from code + SOURCES.md)
- [x] Customers response captured (from code + SOURCES.md)
- [x] Accounts response captured (from code docstring)
- [x] Products response captured (from code docstring)
- [ ] Verification against raw table done (DEFERRED to Phase 3 smoke test)
- [x] Decision recorded: **Option 2 selected** — Page-metadata field (`metadata.total`) on `?page=1&limit=1` enables cheap count requests without data pull
- [x] Phase 3 unblocked — metadata shape verified, ready for reconciliation implementation

## Unresolved Questions (to resolve during research)

- Is there a distinction between Sapo "admin" API and "public/storefront" API regarding count availability?
- Does `modified_on_min` filter behave correctly with orders updated multiple times in the window?
- Is page numbering 0-indexed or 1-indexed?
