# Security Edge Cases — Re-evaluation & Action Plan
Date: 2026-04-03 | Based on: `code-reviewer-260227-1721-security-edge-cases.md`

---

## Re-evaluation Summary

| # | Issue | Original Status | Current Status | Action Needed |
|---|-------|----------------|----------------|---------------|
| 1 | SQL injection via f-strings | PARTIAL | **OPEN** | Yes |
| 2 | Credential exposure (.env) | HANDLED (gap) | **FIXED** | No — `.env` added to root `.gitignore` line 4 |
| 3 | Cookie files plaintext | PARTIAL | **OPEN** | Yes (4 sub-issues) |
| 4 | Stale lock / race conditions | PARTIAL | **OPEN** | Yes (temp file race) |
| 5 | Resource leaks (DB connections) | PARTIAL | **PARTIALLY FIXED** | Yes (3 of 5 files) |
| 6 | HMAC timing attack | HANDLED | **HANDLED** | No |

**Items already resolved since report:**
- `.gitignore` now has bare `.env` entry (line 4) → Issue #2 closed.
- `generate_serving_db.py` uses `try/finally` with `con.close()` at line 145 → Issue #5a closed.

---

## Action Items (Priority Order)

### P1: Resource Leaks — DB Connections (3 files)

**Why:** DuckDB holds exclusive write lock while open. Leaked connection = blocked serving DB until process exits. `KeyboardInterrupt` or unhandled exception causes leak.

**Fix:** Wrap `duckdb.connect()` in `try/finally` with `con.close()` in `finally`.

#### 1a. `scripts/maintenance/sync_seeds.py`
- **Current (line 16, 106):** `con = duckdb.connect(DB_PATH)` ... `con.close()` — no `try/finally`
- **Fix:** Wrap entire `sync_seeds()` body in `try/finally`
```python
def sync_seeds():
    con = duckdb.connect(DB_PATH)
    try:
        # ... existing body ...
    finally:
        con.close()
```

#### 1b. `scripts/maintenance/cleanup_and_verify.py`
- **Current (line 3, 51):** Module-level `con = duckdb.connect(...)` ... `con.close()` — no `try/finally`
- **Fix:** Wrap in function with `try/finally`
```python
def main():
    con = duckdb.connect('data_lake/sapo_warehouse.duckdb')
    try:
        # ... existing body ...
    finally:
        con.close()

if __name__ == "__main__":
    main()
```

#### 1c. `scripts/testing/verify_hops_readonly.py`
- **Current (line 20, 52):** `con.close()` outside try/except. If exception on lines 28-50, close skipped before exit.
- **Fix:** Add `finally` block
```python
try:
    con = duckdb.connect(db_path, read_only=True)
    # ... checks ...
finally:
    if con:
        con.close()
```
- **Severity:** Low (read-only connection, no write lock held). Still good hygiene.

#### 1d. `ingestion/query_lake.py`
- **Current (line 12-38):** `con = duckdb.connect()` inside try, never closed.
- **Fix:** Add `finally: con.close()` or use context manager.
- **Severity:** Low (in-memory connection, no file lock). Hygiene fix.

---

### P2: SQL Identifier Sanitization (2 files)

**Why:** `table_name` from `os.listdir()` and `information_schema` used directly in f-string SQL. Defense-in-depth: a malicious directory name like `'; DROP TABLE x; --` would execute arbitrary SQL.

#### 2a. `scripts/provisioning/generate_serving_db.py` (lines 103, 117, 123)
- **Current:** `table_name` from `os.listdir(ROLLING_DIR)` used in `DROP VIEW IF EXISTS {table_name}` and `CREATE OR REPLACE VIEW {table_name} AS`.
- **Fix:** Add allowlist regex validation before the loop:
```python
TABLE_NAME_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
# Inside loop:
if not TABLE_NAME_RE.match(table_name):
    print(f"  [!] Skipping invalid table name: {table_name}")
    continue
```
- `re` already imported (line 3). Zero new dependencies.

#### 2b. `scripts/maintenance/sync_seeds.py` (lines 32, 93)
- **Current:** CSV-sourced IDs joined with string concatenation into `NOT IN (...)`.
- **Self-reinforcing risk:** `sync_seeds.py` writes IDs back to CSV → corrupted upstream value re-injects on next run.
- **Fix options:**
  - **(A) Safest:** Use DuckDB parameterized query with array unnest:
    ```python
    con.execute("""
        SELECT DISTINCT ...
        FROM sapo_raw.order
        WHERE id NOT IN (SELECT unnest(?::VARCHAR[]))
        AND id IS NOT NULL
    """, [list(existing_ids)])
    ```
  - **(B) Simpler:** Validate IDs against allowlist regex before building SQL:
    ```python
    ID_RE = re.compile(r'^[a-zA-Z0-9_-]+$')
    safe_ids = [i for i in existing_ids if ID_RE.match(str(i))]
    ```
- **Recommendation:** Option A if DuckDB supports array unnest in this context; Option B as fallback.

#### 2c. `scripts/maintenance/cleanup_and_verify.py` (lines 25-26)
- **Current:** `t` from `information_schema.tables` (format `schema.table`) used in `DROP VIEW/TABLE`.
- **Risk:** Low — source is DB metadata, not external input.
- **Fix (optional):** Validate with regex `^[a-zA-Z_][a-zA-Z0-9_.]*$` before DROP.
- **Recommendation:** Low priority. Fix if touching the file for P1 anyway.

---

### P3: Cookie File Security (4 sub-items)

File: `ingestion/src/utils/shared_cookie_manager.py`

**Why:** Session tokens + username in plaintext. Multi-user or shared-environment risk.

#### 3a. Restrict file permissions on Linux
- Add `os.chmod(cookie_path, 0o600)` after writing in `_write_cookie_file`.
- On Windows this is a no-op (ACL-based), but in Docker (Linux container) it prevents world-readable tokens.
- Also set directory: `os.chmod(self.cookie_dir, 0o700)` on creation.

#### 3b. Remove `username` from persisted cookie JSON
- Line ~390: `'username': self.username  # For debugging`
- Remove this field. Cookies are already sensitive; co-locating credential adds exposure for zero value.

#### 3c. Use random temp filename
- Line ~220: `temp_file = self.cookie_file.with_suffix('.tmp')` — shared suffix, race condition.
- **Fix:** Use `tempfile.NamedTemporaryFile(dir=self.cookie_dir, delete=False, suffix='.tmp')` to get unique name.
- Eliminates concurrent-write collision where multiple processes overwrite same `.tmp`.

#### 3d. Windows rename race condition (lines 237-250)
- Current: `unlink()` then `replace()` — gap where file doesn't exist.
- **Fix:** Use `os.replace()` directly (atomic on modern Windows NTFS, no pre-delete needed).
- If pre-delete is needed for legacy reasons, catch `FileNotFoundError` in reader gracefully.
- **Note:** This pairs with 3c — random temp filename makes the race less impactful regardless.

---

## Out of Scope (Acknowledged, No Action)

| Item | Why No Action |
|------|---------------|
| `query_lake.py` raw SQL from argv | Developer tool, not exposed via API. Documented risk. |
| `cleanup_and_verify.py` SQL from `information_schema` | Internal metadata source. Validated risk = low. |
| `_read_cookie_file` no locking | By design — relies on atomic rename. Acceptable with 3c/3d fixes. |
| HMAC timing attack | Already correctly using `crypto.subtle.verify()`. |
| `.env` credential exposure | Fixed — bare `.env` in root `.gitignore`. |

---

## Implementation Order

```
Phase 1 (P1): Resource leaks          ~30 min   [4 files, mechanical fix]
Phase 2 (P2): SQL sanitization         ~30 min   [2 files, regex + test]
Phase 3 (P3): Cookie security          ~45 min   [1 file, 4 changes]
```

All changes are backward-compatible. No API/schema changes. No new dependencies.

---

## Checklist

- [ ] P1a: `sync_seeds.py` — try/finally around `con`
- [ ] P1b: `cleanup_and_verify.py` — wrap in function + try/finally
- [ ] P1c: `verify_hops_readonly.py` — add finally block
- [ ] P1d: `query_lake.py` — add con.close() in finally
- [ ] P2a: `generate_serving_db.py` — regex validate table_name
- [ ] P2b: `sync_seeds.py` — parameterize NOT IN clause or validate IDs
- [ ] P2c: `cleanup_and_verify.py` — validate table names (optional, do if touching file)
- [ ] P3a: Cookie file permissions (os.chmod 0o600)
- [ ] P3b: Remove username from cookie JSON
- [ ] P3c: Random temp filename in _write_cookie_file
- [ ] P3d: Fix Windows rename race (use os.replace directly)

---

## Unresolved Questions

1. Does DuckDB support `?::VARCHAR[]` array parameter in `execute()`? Need to test before committing to P2b Option A.
2. Cookie `username` field — is it used anywhere downstream for display/logging? Grep before removing.
3. `os.replace()` on Windows with DuckDB-locked files — any edge case where the cookie file could be locked by another reader?
