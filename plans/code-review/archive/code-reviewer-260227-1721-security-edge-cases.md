# Code Review: Security & Resource Management Edge Cases
Date: 2026-02-27

---

## 1. SQL Injection via String Interpolation

**Status: PARTIAL**

### `generate_serving_db.py`

- **Evidence (lines 92, 112):**
  ```python
  con.sql(f"DROP VIEW IF EXISTS {table_name}")
  sql = f"""CREATE OR REPLACE VIEW {table_name} AS ..."""
  ```
  `table_name` is derived from `os.listdir(ROLLING_DIR)` — filesystem directory names.

- **Evidence (line 106):**
  ```python
  portable_glob = f"{PORTABLE_ROOT}/export/marts/rolling/{table_name}/*.parquet"
  ```
  `PORTABLE_ROOT` comes from an env var. Path traversal via `table_name` (e.g., a directory named `../../secret`) is possible if the filesystem is writeable by untrusted actors.

- **Impact:** Medium. In practice, directory names are controlled by the dbt pipeline output. Exploitation requires an attacker to create arbitrary directories in the rolling folder, which implies prior filesystem access. Not a remote injection vector, but violates defense-in-depth.

### `sync_seeds.py`

- **Evidence (lines 27-34 and 87-95):**
  ```python
  con.execute(f"""
      ...
      WHERE id NOT IN ({','.join(["'" + str(i) + "'" for i in existing_ids])})
  """)
  ```
  `existing_ids` is read from a CSV file (`ref_order_sources.csv`, `ref_branch_locations.csv`). The IDs are manually quoted with single quotes but not escaped. A value like `'; DROP TABLE order; --` in the CSV would be injected directly.

  `RAW_SCHEMA` is a module-level constant (`sapo_raw`) — not user-input, safe.

- **Impact:** Medium. The CSV seeds are developer-controlled reference files. However, if the CSV is ever auto-updated (which is exactly what `sync_seeds.py` does — it appends rows back), a corrupted upstream value in `json_extract_string(payload, '$.source_id')` could propagate into the CSV and then re-inject on next run. This is a self-reinforcing injection risk.

### `cleanup_and_verify.py`

- **Evidence (line 25-26):**
  ```python
  con.sql(f"DROP VIEW IF EXISTS {t}")
  con.sql(f"DROP TABLE IF EXISTS {t}")
  ```
  `t` is formatted as `f"{schema}.{table}"` where both schema and table come from `information_schema.tables` — i.e., already-stored metadata, not external input. Low risk.

- **Impact:** Low. No parameterized queries exist anywhere in these scripts (DuckDB's `execute()` with `?` params is not used), but the data sources are mostly internal.

---

## 2. Credential Exposure in .env Files

**Status: HANDLED**

- **Evidence — .gitignore (lines 4-7):**
  ```
  .env
  .env.local
  .env.docker
  ```
  Root `.gitignore` covers `.env.local` and `.env.docker` (confirmed tracked: `.env.example` only).

- **Evidence — ingestion/.gitignore (lines 6-7):**
  ```
  .env
  .env.local
  ```
  Ingestion-level `.env.local` also ignored.

- **Evidence — .env.example:** Contains only placeholder values (`your_username_here`, `your_password_here`, `mb_your_api_key_here`). No real credentials present.

- **Note:** `ingestion/.dlt/secrets.toml` is explicitly gitignored in `ingestion/.gitignore` line 1. `.cookies` directory is also gitignored.

- **One gap:** The root `.gitignore` does not have a generic `.env` entry (only named variants). If someone creates `.env` at the root, it would NOT be ignored. The `ingestion/.gitignore` does cover `.env`. Low risk in current state.

---

## 3. Cookie Files Stored in Plaintext

**Status: PARTIAL**

- **Evidence — storage location (`shared_cookie_manager.py` lines 118-139):**
  Cookies stored at `ingestion/.cookies/{source}_cookies.json` (or with domain suffix). Directory confirmed to exist with live files:
  - `sapo_cookies.json`
  - `sapo_fwg.mysapogo.com_cookies.json`

- **Evidence — no encryption:** `_write_cookie_file` (line 209) writes `json.dump(data, f, indent=2)` — plaintext JSON. No encryption, no obfuscation.

- **Evidence — content includes username (line 390):**
  ```python
  cookie_data = {
      ...
      'username': self.username  # For debugging
  }
  ```
  Username is written into the cookie file alongside session tokens.

- **Evidence — file permissions:** No `os.chmod` or `stat` calls exist anywhere in the file. On Linux/macOS with a shared system, the file is created with the process umask (typically 0644 — world-readable). On Windows, inherits parent directory ACL.

- **Impact:** Medium. Session tokens + username in plaintext on disk. If the machine is multi-user or the `.cookies` dir is accessible to other processes/users, full session hijacking is possible. The directory IS gitignored (safe from VCS leakage), but local filesystem exposure is unmitigated.

---

## 4. Stale Lock Files Blocking All Pipelines

**Status: PARTIAL**

- **Evidence — lock mechanism:** The code uses `msvcrt.locking` (Windows) / `fcntl.flock` (Linux) — these are **OS-managed advisory locks tied to the file handle/process lifetime**. When a process dies, the OS automatically releases these locks. There are **no persistent lock files** (e.g., no `.lock` sentinel file written to disk).

- **Evidence — timeout in `_acquire_lock` (lines 144-163):**
  ```python
  def _acquire_lock(self, file_handle, timeout: int = 10):
      start_time = time.time()
      while True:
          try:
              lock_file(file_handle)
              return True
          except (IOError, OSError):
              if time.time() - start_time >= timeout:
                  raise TimeoutError(...)
              time.sleep(0.1)
  ```
  Timeout is 10 seconds. `TimeoutError` is raised and propagates up — callers in `_write_cookie_file` have a `try/finally` that releases the lock.

- **Gap — Linux `lock_file` does not retry (lines 38-41):**
  ```python
  def lock_file(f):
      fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
  ```
  `LOCK_NB` raises immediately if the lock is held. The `_acquire_lock` wrapper loops and retries correctly. However, `_read_cookie_file` (line 187) opens with `'r'` and **does not call `_acquire_lock` at all** — reads are unprotected. The code comment (line 192) acknowledges this and relies on atomic rename, which is correct for reads, but not for the Windows rename path (lines 239-243) where there is a race between `unlink()` and `replace()`.

- **Gap — shared `.tmp` file (lines 220-235):**
  Multiple processes writing at the same time will overwrite each other's `.tmp` file before the rename, causing silent data loss (last writer wins). A random temp filename would be safer.

- **Impact:** Low-Medium. No permanent lock file stale condition possible (OS handles it). The race in the Windows rename path is a data corruption risk, not a deadlock risk. A pipeline won't block forever, but cookie data may be silently corrupted under concurrent logins.

---

## 5. Resource Leaks (File Handles, DB Connections)

**Status: PARTIAL**

### `generate_serving_db.py`

- **Evidence (lines 65-134):**
  ```python
  con = None
  try:
      con = duckdb.connect(SERVING_DB_PATH)
  except Exception as e:
      ...
  # ... lots of code ...
  if con:
      con.close()
  ```
  `con.close()` is called at the end, but NOT in a `finally` block or context manager. If any unhandled exception occurs in the loop body (lines 83-131), `con` leaks. DuckDB holds an exclusive write lock while open — a leaked connection on the serving DB would block all readers until the process terminates.

- **Impact:** Medium. The loop has individual `try/except` blocks, so most exceptions are caught, but a `KeyboardInterrupt` or `SystemExit` during the loop would leak the connection and lock the DB file.

### `sync_seeds.py`

- **Evidence (lines 16, 106):**
  ```python
  con = duckdb.connect(DB_PATH)
  # ... code without try/finally ...
  con.close()
  ```
  Same pattern: `con.close()` at the bottom, no `finally`. An exception between line 16 and 106 leaks the connection.

- **Impact:** Medium. Same risk as above.

### `cleanup_and_verify.py`

- **Evidence (line 51):**
  ```python
  con.close()
  ```
  No `try/finally`. Same pattern. Note this script is a one-shot run and process exit releases the connection anyway.

- **Impact:** Low. One-shot script; OS reclaims on exit.

### `verify_hops_readonly.py`

- **Evidence (line 52):**
  ```python
  con.close()
  ```
  Connected `read_only=True` (line 20). Read-only connections don't hold write locks. Leak impact minimal.

- **Impact:** Low.

### `query_lake.py`

- **Evidence (lines 12-35):**
  ```python
  con = duckdb.connect()  # in-memory connection
  # ... no con.close() anywhere ...
  ```
  The connection is **never closed** — neither in the success path nor in the `except` block (line 38). However, this is an in-memory connection (`duckdb.connect()` with no path), so no file lock is held.

- **Impact:** Low. In-memory only; no file resource held. Minor hygiene issue.

### Summary of Resource Leak Pattern

All Python scripts follow the same anti-pattern: `con = duckdb.connect()` / `con.close()` without `try/finally` or `with` statement. None use the DuckDB context manager (`with duckdb.connect(...) as con:`).

---

## 6. HMAC Timing Attack Vulnerability

**Status: HANDLED**

- **Evidence (`utils.ts` lines 10-46):**
  ```typescript
  const key = await crypto.subtle.importKey(
      "raw", encoder.encode(secret),
      { name: "HMAC", hash: "SHA-256" },
      false, ["verify"]
  );
  // ...
  return crypto.subtle.verify("HMAC", key, signatureBytes, encoder.encode(body));
  ```
  `crypto.subtle.verify()` is the Web Crypto API's constant-time comparison function. This is the correct approach — it does not use JavaScript string equality (`===`) and is not vulnerable to timing attacks.

- **Evidence — D1 parameterized queries (lines 51-54):**
  ```typescript
  await env.DB.prepare(
      "INSERT INTO webhook_errors (...) VALUES (?, ?, ?, ?, ?)"
  ).bind(...).run();
  ```
  No string interpolation in SQL. Correct parameterized binding used throughout.

- **Impact:** None. Implementation is correct.

---

## Summary Table

| # | Edge Case | Status | Severity |
|---|-----------|--------|----------|
| 1 | SQL injection via f-strings | PARTIAL | Medium |
| 2 | Credential exposure in .env files | HANDLED | — |
| 3 | Cookie files in plaintext | PARTIAL | Medium |
| 4 | Stale lock files blocking pipelines | PARTIAL | Low-Medium |
| 5 | Resource leaks (DB connections) | PARTIAL | Medium |
| 6 | HMAC timing attack | HANDLED | — |

---

## Recommended Actions (Priority Order)

1. **[High] Fix resource leaks in all scripts** — wrap `duckdb.connect()` in `try/finally` with `con.close()` in the `finally` block, or use `with duckdb.connect(...) as con:`. Affects `generate_serving_db.py`, `sync_seeds.py`, `cleanup_and_verify.py`. The locked serving DB scenario is a real operational risk.

2. **[Medium] Sanitize/validate table names before SQL interpolation in `generate_serving_db.py`** — add a regex allowlist (e.g., `re.match(r'^[a-zA-Z0-9_]+$', table_name)`) before using `table_name` in `CREATE VIEW` and `DROP VIEW` statements.

3. **[Medium] Use DuckDB parameterized queries in `sync_seeds.py`** — the `NOT IN (...)` clause built by string joining of CSV-sourced IDs is the most realistic injection vector given the self-reinforcing write path. Convert to `execute("... WHERE id NOT IN (SELECT unnest(?::VARCHAR[]))", [list(existing_ids)])` or equivalent.

4. **[Low-Medium] Restrict cookie file permissions on Linux** — add `os.chmod(self.cookie_file, 0o600)` after writing. On Windows this is a no-op, but on Linux/Docker it prevents world-readable session tokens.

5. **[Low] Add random temp filename in `_write_cookie_file`** — replace `.tmp` suffix with `tempfile.NamedTemporaryFile(dir=self.cookie_dir, delete=False)` to eliminate the concurrent-write race condition.

6. **[Low] Add root-level `.env` to root `.gitignore`** — currently only named variants are listed. A bare `.env` file at root would not be caught.

7. **[Low] Remove `username` field from persisted cookie JSON** — `login_and_save_cookies` (line 390) writes `'username': self.username` to disk. Cookies are already sensitive; no need to co-locate the credential.

---

## Unresolved Questions

- The `.cookies` directory is gitignored at `ingestion/.gitignore` level. Is there a root-level entry needed if the cookie manager is ever invoked from the project root (e.g., in Docker)? The cookie dir defaults to `.cookies` relative to the `ingestion` package root, so currently scoped correctly — but worth verifying for Docker invocation paths.
- `query_lake.py` accepts a raw SQL query from `sys.argv[1]` (line 44-45) with no sanitization and executes it directly. This is a developer tool, but if ever exposed via a web interface or API wrapper, it is a full SQL injection surface. Flagging for awareness.
