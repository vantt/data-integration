# Plan: CRM Unified FTS Search (S02)

**Branch:** main  
**Status:** Done  
**Goal:** Replace S02's limited name/phone search with a unified FTS5 index covering all identity types + order codes.

---

## Context

Current S02 search (`_search_parties()`) only covers:
- `crm_party_fts` → display_name only (FTS5, trigger-maintained)
- `crm_party.primary_phone` → exact match only

Missing: secondary contacts (phone_secondary, zalo, email added by sales), sapo-id, customer-code, order-id, order-code.

Approach: denormalized `crm_party_search` FTS5 table, rebuilt after every ETL refresh.

---

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | Phone format — strip +84 internally | ✅ done |
| 2 | SQLite migration — unified FTS table | ✅ done |
| 3 | FTS rebuild module | ✅ done |
| 4 | Wire rebuild into admin refresh | ✅ done |
| 5 | Simplify search router (S02 + global) | ✅ done |
| 6 | Tests | ✅ done |
| + | Add warehouse full_name to FTS tokens | ✅ done |

---

## Phase 1 — Phone format: local (no +84)

**Why:** Internal system is VN-only. E.164 `+84901234567` makes prefix search awkward — user types `0901`, FTS prefix `0901*` won't match `+84901234567`. Local format `0901234567` matches naturally.

**Export rule:** when sending phone to external systems, call `phone_to_e164(v)` at the output layer.

### Files to change

| File | Change |
|------|--------|
| `crm/src/application/party_service.py` | Rewrite `normalize_phone()`: `0...` → keep, `+84...` → `0...`, `84...` → `0...` |
| `crm/src/domain/entities/party.py:94` | Update comment: `# normalised local VN format (09...)` |
| `crm/src/application/party_service.py` | Add `phone_to_e164(local: str) -> str` helper for export use |
| `crm/src/tests/test_party_service.py` | Update all `+84...` expected values → `09...` |
| `crm/src/tests/test_domain_entities.py` | Update hardcoded `+84901000001` → `0901000001` |
| `crm/sync/tests/test_reverse_etl_warehouse_to_crm.py` | Update `+84901000001` test fixtures |
| `crm/migrations/0020_phone_local_format.up.sql` | Data migration: strip +84 from existing rows |

### Migration SQL (`0020_phone_local_format.up.sql`)

```sql
-- Strip +84 prefix from crm_party.primary_phone
UPDATE crm_party
SET primary_phone = '0' || substr(primary_phone, 4)
WHERE primary_phone LIKE '+84%';

-- Strip +84 prefix from crm_party_identity phone values
UPDATE crm_party_identity
SET identity_value = '0' || substr(identity_value, 4)
WHERE identity_type IN ('phone', 'phone_secondary')
  AND identity_value LIKE '+84%';
```

**Risk:** UNIQUE(identity_type, identity_value) constraint. If two parties somehow had `+84901234567` and `0901234567` for the same type, the UPDATE would collide. In practice impossible (UNIQUE prevents duplicate phones), but migration should run in a transaction and fail loudly if constraint fires.

---

## Phase 2 — SQLite migration: unified FTS table

**File:** `crm/migrations/0021_unified_party_search.up.sql`

```sql
-- Drop old trigger-maintained FTS (replaced by rebuild-based unified FTS)
DROP TRIGGER IF EXISTS trg_party_fts_insert;
DROP TRIGGER IF EXISTS trg_party_fts_update;
DROP TRIGGER IF EXISTS trg_party_fts_delete;
DROP TABLE IF EXISTS crm_party_fts;

-- Unified search index: one row per party, token blob covers all searchable values
-- Tokenizer: unicode61 with diacritic removal (Vietnamese names) + tokenchars for
-- special chars in emails (+84 stripped so no + needed), order codes (- separator ok)
CREATE VIRTUAL TABLE IF NOT EXISTS crm_party_search USING fts5(
    party_id  UNINDEXED,
    tokens,
    tokenize = "unicode61 remove_diacritics 2 tokenchars '@.'"
);
```

**Tokenizer notes:**
- `remove_diacritics 2` — handles Vietnamese (Nguyễn → nguyen for matching)
- `tokenchars '@.'` — keeps `@` and `.` inside email tokens so `nguyen@gmail.com` is one token
- `-` not in tokenchars: `DH-001` splits into `DH` + `001` (acceptable — prefix on either works)
- Phones stored as `0901234567` (local) — prefix `0901*` matches naturally

---

## Phase 3 — FTS rebuild module

**New file:** `crm/sync/search_index.py`

### Token blob schema per party

```
{display_name} {local_phone_1} {local_phone_2} ... {email_1} {email_2} ... {sapo_id} {customer_code} {zalo_uid} {facebook_psid} {order_code_1} {order_id_1} ...
```

**Phone normalization at build time:**
```python
def _to_local_phone(v: str) -> str:
    """Convert any stored format to local 09... for FTS token."""
    digits = re.sub(r'\D', '', v)
    if digits.startswith('84') and len(digits) == 11:
        return '0' + digits[2:]
    return digits  # already local or unrecognized
```

Applied at rebuild time — handles old `+84...` data that wasn't yet migrated, and future manual inputs that bypass normalize_phone.

### Data sources

```
crm.db:
  crm_party          → party_id, display_name
  crm_party_identity → all identity_values per party_id
                        (phone, phone_secondary, email, sapo_customer,
                         customer_code, zalo_uid, facebook, psid)
                        skip: contact_status = 'invalid'

cache.db:
  wh_order_hdr       → order_code, order_id, customer_id (str)
  wh_customer_base   → customer_id → customer_key (for join to party_id)
```

**Cross-DB join (Python dict, not SQL ATTACH):**
1. From `crm.db`: build `{customer_id_str: party_id}` via `crm_party_identity WHERE identity_type='sapo_customer'`
2. From `cache.db`: build `{customer_id_str: [order_code, order_id]}` from `wh_order_hdr` (customer_id already resolved by reverse ETL)
3. Join in Python dicts → append order tokens to each party's blob
4. `NULL` customer_id rows in wh_order_hdr → skip (guest orders, no party link)

### Rebuild logic

```python
def rebuild_search_index(crm_db_path: str, cache_db_path: str) -> int:
    """Full rebuild: DELETE all + INSERT. Returns row count."""
    # 1. Load party data from crm.db
    # 2. Load order data from cache.db
    # 3. Build token blob per party
    # 4. DELETE FROM crm_party_search
    # 5. INSERT batch into crm_party_search
    # Returns count of indexed parties
```

Full rebuild (not incremental) — simpler, correct, fast enough (<1s for ~50k parties).

---

## Phase 4 — Wire into admin_handler

**File:** `crm/src/adapters/inbound/http/admin_handler.py`

Add `_rebuild_search_index_run()` and Step 3 in `_run_refresh()`:

```python
async def _run_refresh(started_at):
    # Step 1 (existing): reverse ETL
    await loop.run_in_executor(None, _reverse_etl_run)
    # Step 2 (existing): sync parties
    await loop.run_in_executor(None, _sync_parties_run)
    # Step 3 (new): rebuild unified FTS
    await loop.run_in_executor(None, _rebuild_search_index_run)
```

`_rebuild_search_index_run()` reads `CRM_DATA_DIR` from env (same as `_sync_parties_run`). Failure → log error, does NOT abort the refresh (non-critical).

---

## Phase 5 — Simplify search router

### S02 `screen_customer_list.py`

**Protocol change** — `PartyLister` gains one new method:

```python
class PartyLister(Protocol):
    ...
    def search_unified(self, q: str) -> list[str]: ...  # returns party_ids
```

**`_search_parties()` replaces 2-branch logic with 1 FTS call:**

```python
def _search_parties(q: str) -> list[Party]:
    try:
        ids = parties.search_unified(_fts_query(q))
    except Exception as exc:
        log.error("customer search: %r: %s", q, exc)
        ids = []
    out = []
    for pid in ids:
        p = parties.get_by_id(pid)
        if p and not p.is_merged:
            out.append(p)
    return out
```

**FTS query sanitization** (`_fts_query(q: str) -> str`):
```python
def _fts_query(q: str) -> str:
    """Wrap user input as FTS5 quoted string + prefix wildcard.

    Quoted strings in FTS5 treat all chars as literals except '"'.
    Stripping '"' from user input prevents syntax errors.
    Trailing '*' enables prefix matching (0901* matches 0901234567).
    """
    clean = q.replace('"', ' ').strip()
    return f'"{clean}"*'
```

This fixes the existing injection bug AND adds prefix matching for all token types.

### Global search `screen_search.py`

Simplify `_resolve_customer()`:
- Remove branches 1-5 (UUID, digit, email, phone, customer-code)
- All collapse into unified FTS search
- Keep UUID branch only (UUID → party_id direct, bypass FTS)
- Return first result as redirect if exactly 1 hit, else disambiguation list

### New SQL + method in repository

**`party_repository_queries.py`:**
```python
SQL_UNIFIED_SEARCH = (
    "SELECT party_id FROM crm_party_search"
    " WHERE crm_party_search MATCH ?"
    " ORDER BY rank LIMIT 50"
)
```

**`party_repository.py`:**
```python
def search_unified(self, fts_query: str) -> list[str]:
    cur = self._conn.execute(SQL_UNIFIED_SEARCH, (fts_query,))
    return [row[0] for row in cur.fetchall()]
```

---

## Phase 6 — Tests

| Test file | What to update/add |
|-----------|-------------------|
| `test_party_service.py` | Update `+84...` → `09...` expected; add `phone_to_e164()` test |
| `test_domain_entities.py` | Update `+84901000001` fixture |
| `test_reverse_etl_warehouse_to_crm.py` | Update `+84...` test data |
| `crm/sync/tests/test_search_index.py` | **NEW**: test rebuild with fixture crm.db + cache.db; assert tokens; assert order_code indexed; assert NULL customer_id skipped |
| `crm/src/tests/test_screen_customer_list.py` | Update mock to use `search_unified`; test `_fts_query()` sanitization |

---

## Key constraints

- `cache.db` opened read-only in rebuild (1-writer rule: Python writes cache.db only via reverse ETL)
- `crm.db` opened by rebuild with write access — same as `_sync_parties_run`, sequential so no concurrent write conflict
- FTS rebuild is Step 3 after Step 2 (sync_parties) so party identities are already up-to-date
- Old `crm_party_fts` table and triggers dropped in migration 0021 — no orphaned triggers

## Unresolved questions

- None. All decision points confirmed in conversation.
