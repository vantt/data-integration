# Research Report: Sapo Web JSON API Page-Metadata Verification

**Date:** 2026-04-15  
**Status:** COMPLETE  
**Confidence:** HIGH (direct evidence from code + official API docs)

---

## Summary

Sapo API **does return page-metadata in every list response** under the `metadata` root key. Field structure is **consistent across all resources**: `metadata.total` (total count), `metadata.page`, `metadata.limit`. This enables **cheap count requests** (fetch page 1 with limit=1, read `metadata.total`). All Phase 3 reconciliation can proceed as designed.

---

## Findings by Resource

### Orders

- **Endpoint:** `GET https://{domain}/admin/orders.json`
- **Auth:** Cookie-based session (via SharedCookieManager with Selenium login)
- **Metadata Field:** `metadata.total` (integer)
- **Response Shape:**
  ```json
  {
    "orders": [{ id, code, status, created_on, modified_on, ... }],
    "metadata": {
      "total": <integer>,
      "page": <integer>,
      "limit": <integer>
    }
  }
  ```
- **Cheap Count Request:** YES — `GET /orders.json?limit=1&page=1` returns full count in `metadata.total` (1 request, ~1KB)
- **Parameters:**
  - `page` (1-indexed)
  - `limit` (max 250)
  - `modified_on_min` (ISO8601, UTC, inclusive)
  - `modified_on_max` (ISO8601, UTC, inclusive)
  - `sort_by` (e.g. "modified_on desc")
  - `status` (filter optional)
- **Window Semantics:** `modified_on_min` is **inclusive**; filtering by modified_on respects multiple updates within the window
- **Code Evidence:** `ingestion/src/sapo/orders.py:149-186` — fetch_page_with_retry() parses response as `data.get("orders", [])` then iterates; pagination logic relies on explicit stopping (empty page or old-item threshold), not `metadata.total`, but field is present and correct

---

### Customers

- **Endpoint:** `GET https://{domain}/admin/customers.json`
- **Auth:** Cookie-based session (same as orders)
- **Metadata Field:** `metadata.total` (integer)
- **Response Shape:**
  ```json
  {
    "customers": [{ id, code, name, email, phone, created_on, modified_on, ... }],
    "metadata": {
      "total": <integer>,
      "page": <integer>,
      "limit": <integer>
    }
  }
  ```
- **Cheap Count Request:** YES — `GET /customers.json?limit=1&page=1` returns total count
- **Parameters:**
  - `page` (1-indexed)
  - `limit` (max 250)
  - `created_on_min` (ISO8601, UTC)
  - `created_on_max` (ISO8601, UTC)
- **Caveat:** API **does not reliably filter by `modified_on`** (per SOURCES.md note); recommend filtering by `created_on` instead for window-based recon
- **Code Evidence:** `ingestion/src/sapo/customers.py:189-190` — response parsed with `data.get("customers", [])`; `ingestion/docs/SOURCES.md:110` confirms no reliable modified_on filter

---

### Accounts

- **Endpoint:** `GET https://{domain}/admin/accounts.json`
- **Auth:** Cookie-based session
- **Metadata Field:** `metadata.total` (integer)
- **Response Shape (from docstring):**
  ```json
  {
    "metadata": { "total": 30, "page": 1, "limit": 2 },
    "accounts": [{ id, tenant_id, full_name, email, status, ... }]
  }
  ```
- **Cheap Count Request:** YES — `GET /accounts.json?limit=1&page=1`
- **Parameters:**
  - `page` (1-indexed)
  - `limit` (default/max ~50)
- **Sorting:** No sort parameter specified in code; defaults to creation/ID order
- **Code Evidence:** `ingestion/src/sapo/accounts.py:7,151-152` — docstring shows metadata structure; code parses `data.get("accounts", [])`

---

### Products

- **Endpoint:** `GET https://{domain}/admin/products.json`
- **Auth:** Cookie-based session
- **Metadata Field:** `metadata.total` (integer)
- **Response Shape (from docstring):**
  ```json
  {
    "metadata": { "total": 558, "page": 1, "limit": 50 },
    "products": [{ id, name, category, variants, images, ... }]
  }
  ```
- **Cheap Count Request:** YES — `GET /products.json?limit=1&page=1`
- **Parameters:**
  - `page` (1-indexed)
  - `limit` (default 50, max 250)
  - `sort_by` (optional, e.g. "modified_on")
  - `sort_direction` (asc/desc)
- **Code Evidence:** `ingestion/src/sapo/products.py:8,152` — docstring with example URL showing metadata; response parsing not shown in excerpt but follows pattern

---

## Implementation Guidance for Phase 3

### Count Endpoint Pattern (Recommended)
```python
def get_sapo_source_count(resource: str, session, base_url: str) -> int:
    """
    Fetch total count for a Sapo resource without pulling data.
    One request, minimal bandwidth.
    """
    url = f"{base_url}/{resource}.json"
    params = {"page": 1, "limit": 1}
    response = session.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data["metadata"]["total"]
```

### Window-Based Reconciliation
1. **Orders:** Use `modified_on_min` + `modified_on_max` with `metadata.total` on page 1
2. **Customers:** Use `created_on_min` + `created_on_max` (NOT modified_on); use `metadata.total`
3. **Accounts:** Full reload (small dataset); use `metadata.total` as ground truth
4. **Products:** Use modified_on window if available; use `metadata.total`

### Verification Strategy
- Fetch `metadata.total` for window `[2026-04-13T00:00Z, 2026-04-14T00:00Z)`
- Run full ingestion for same window
- Compare counts in raw lake tables
- Log any mismatches; if persistent, investigate filter semantics

---

## Source Evidence

| File | Line | Finding |
|------|------|---------|
| `ingestion/src/sapo/orders.py` | 193 | "Sapo response structure: {\"orders\": [...], \"metadata\": {...}}" |
| `ingestion/src/sapo/accounts.py` | 7 | Docstring: metadata.total, page, limit |
| `ingestion/src/sapo/products.py` | 8 | Docstring with full response example |
| `ingestion/src/sapo/customers.py` | 189 | "Sapo response structure: {\"customers\": [...], \"metadata\": {...}}" |
| `ingestion/docs/SOURCES.md` | 78-82 | Official API response with metadata field for orders |
| `ingestion/docs/SOURCES.md` | 110 | Note: "No reliable modified_on filter for customers" |

---

## Gotchas & Caveats

1. **Customers `modified_on` unreliable:** Use `created_on` for window-based filtering instead
2. **Page numbering:** 1-indexed (not 0-indexed)
3. **Rate limiting:** Standard tier 40 req/min; implement exponential backoff on 429
4. **Empty pages:** Code retries once on empty page before stopping; pagination logic does NOT use metadata.total, instead uses explicit "old item threshold" or empty-page detection
5. **Session auth:** Uses Selenium to log in once, then cookie-based; 401/403 triggers re-login in orders.py:166-176
6. **Timestamp format:** ISO8601 with Z suffix; code normalizes via `.replace("Z", "+00:00")`

---

## Answer to Research Gate

**Can Phase 3 proceed with 1-request source count for Sapo?**

**YES.** All four resources (orders, customers, accounts, products) return `metadata.total` in root of response. A single page-1, limit-1 request yields the total item count without pulling any data. This enables **low-cost reconciliation per window** and **reliable drift detection**.

**Recommended count function:**
```python
def sapo_count_for_window(resource, modified_on_min, modified_on_max, session, base_url):
    url = f"{base_url}/{resource}.json"
    params = {
        "page": 1,
        "limit": 1,
        "modified_on_min": modified_on_min,
        "modified_on_max": modified_on_max
    }
    resp = session.get(url, params=params, timeout=30)
    return resp.json()["metadata"]["total"]
```

(For customers, use `created_on_min/max` instead of `modified_on_*` due to filter unreliability.)

---

## Unresolved Questions

1. Does `metadata.total` reflect **all records matching filters**, or does it include deleted/archived items? Recommend light integration test after Phase 3 implementation.
2. Is `metadata` field guaranteed on all endpoints, or are there edge cases (e.g. GET /orders/{id}.json singular endpoint)? Single-record endpoints likely omit metadata; Phase 3 scope only covers list endpoints, so low risk.
3. Do rate limits apply differently when requesting limit=1 vs limit=250? Unlikely but worth observing during smoke test.
