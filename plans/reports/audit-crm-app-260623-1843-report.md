# CRM App Health Audit — 2026-06-23

Read-only audit of `crm/src/` (domain/, application/, adapters/inbound/web/, adapters/outbound/sqlite/, hug/).
Scope excludes crm/sync/.

---

## Summary counts

| Severity | Count |
|----------|-------|
| CRITICAL | 3 |
| HIGH | 5 |
| MEDIUM | 6 |
| LOW | 4 |

---

## CRITICAL

### C1 — Campaign screen calls non-existent service methods (AttributeError at runtime)

**File:** `crm/src/adapters/inbound/web/screen_management.py:295,310,311`

`screen_management.py` calls three methods on `CampaignService` that do not exist:

| Call site (screen_management.py) | Missing on CampaignService |
|----------------------------------|----------------------------|
| `campaigns_svc.record_conversion(campaign_id, party_id, ...)` L295 | No such method |
| `campaigns_svc.update_target_status(campaign_id, party_id, status)` L310 | No such method (exists as `update_target()` with `**kwargs`) |
| `campaigns_svc.get_target(campaign_id, party_id)` L311 | No such method (exists on repo, not service) |

In addition, `campaigns_svc.create_campaign(name=..., objective=..., channel=..., ...)` (L203) is called with keyword args but `CampaignService.create_campaign` accepts a single `data: dict` param — TypeError at runtime.

**Risk:** `/campaigns/{id}/targets/{pid}/convert` (POST), `/campaigns/{id}/targets/{pid}/status` (PATCH), and `POST /campaigns` all raise `AttributeError`/`TypeError` on first call. Dead campaign management routes.

**Fix:** Either (a) add `record_conversion`, `update_target_status`, `get_target`, and a keyword-arg overload for `create_campaign` to `CampaignService`; or (b) refactor the screen to call the existing `update_target()` and repo methods through the service.

---

### C2 — Hexagonal boundary violation: `sqlite3` imported in application layer

**Files:**
- `crm/src/application/segment_service.py:12` — `import sqlite3`
- `crm/src/application/campaign_service.py:6` — `import sqlite3`

Both application services accept a bare `sqlite3.Connection` in their constructor and execute raw SQL queries directly (segment_service `_evaluate_rule`, campaign_service `_find_earliest_order`, `_fetch_consent_map`). This is a hard hexagonal-boundary violation: application layer must not touch persistence adapters directly.

**Risk:** Domain purity is broken. Swapping SQLite for another store requires editing application logic. `import sqlite3` in `application/` is the smell declared in AGENTS.md as forbidden.

**Fix:** Extract the raw SQL queries into a `SegmentQueryRepository` and `CampaignQueryRepository` port+adapter pair. Application services should depend on the port interface, not on `sqlite3.Connection` directly.

---

### C3 — Unauthenticated Facebook Messenger webhook ingest

**File:** `crm/src/adapters/inbound/http/conversation_handler.py:99-131`

`POST /api/conversations/messenger/ingest` accepts arbitrary JSON with no `X-Hub-Signature-256` HMAC verification. The code comment explicitly notes: *"Auth/FB signature verification: TODO — deferred until live token is available."*

**Risk (LAN-only but still):** Any internal service or compromised LAN node can POST arbitrary messenger payloads to create conversations and activities. If the CRM is ever exposed beyond LAN, this is a full unauthenticated write endpoint with no rate limit beyond the 1 MiB body cap.

**Fix:** Implement HMAC-SHA256 verification using `X-Hub-Signature-256` header before processing. At minimum add an API key check (`CRM_WEBHOOK_SECRET`) so ingest is restricted to the known sender.

---

## HIGH

### H1 — `| safe` on server-controlled label string (low XSS risk, but pattern is unsafe)

**File:** `crm/src/adapters/inbound/web/templates/fragments/order_financial_tab.html:16`

```jinja
<span class="wf-label">{{ label | safe }}
```

`label` is passed from `wf_row(op, label, ...)` macro calls. Currently labels are hardcoded Python string literals (e.g. `"Doanh thu gộp"`), but the `| safe` filter disables autoescape and would render unescaped HTML/JS if a label ever came from a user-controlled source. This pattern is fragile — future contributors may unknowingly pass untrusted data to `wf_row`.

**Risk:** If label ever comes from `order.financial.*` (which originates from DuckDB/warehouse), an HTML-injection payload stored there would be rendered.

**Fix:** Remove `| safe`. If bold/italic formatting is needed in labels, use a whitelist Jinja filter instead of blanket safe-marking.

---

### H2 — `worklist.TaskQuerier` protocol mismatch: `party_id` vs `assignee_id`

**File:** `crm/src/adapters/inbound/web/screen_worklist.py:41`

```python
class TaskQuerier(Protocol):
    def list_tasks(self, party_id: str, status: str) -> list[Task]: ...
```

The wired implementation is `task_svc` (`TaskService`), whose actual signature is:
```python
def list_tasks(self, assignee_id: Optional[str] = None, status: Optional[str] = None, limit: int = 100)
```

At L86 the worklist calls `tasks.list_tasks("", "open")`. Positionally `""` maps to `assignee_id` (correct), but the protocol documents the parameter as `party_id`. This is semantically misleading and is the same class of bug that caused L140's empty-render issue: the protocol documentation directs future callers to pass a `party_id` (wrong type of ID) instead of `assignee_id`.

**Risk:** A future worklist variant that correctly follows the Protocol contract and passes `party_id` instead of `assignee_id` will silently get wrong results (tasks for a different filter axis). Reproduces the L140 empty-worklist class of bug.

**Fix:** Rename `party_id` to `assignee_id` in the `TaskQuerier` Protocol definition.

---

### H3 — `scheduled_at` stores local ICT offset instead of UTC

**File:** `crm/src/adapters/inbound/web/screen_management.py:202`

```python
ts = (scheduled_at.strip() + "T00:00:00+07:00") if scheduled_at.strip() else None
```

`scheduled_at` is stored as `"YYYY-MM-DDT00:00:00+07:00"` — a fixed ICT offset appended to a date field from the HTML form. This contradicts the TIMESTAMPTZ convention (store UTC ISO-8601). The `scan_conversions` method in `CampaignService` then parses this with `_date_to_ict_key()` which tries ICT→date_key conversion, but the hardcoded `+07:00` suffix means DST-aware TZ parsing will be inconsistent if ever normalized to UTC.

**Risk:** Violates AGENTS.md TIMESTAMPTZ discipline. If the serving layer is ever changed to normalize timestamps to UTC before storage, `scheduled_at` values break. The `scan_conversions` date comparison may produce off-by-one results across midnight boundaries.

**Fix:** Store as UTC: `datetime.strptime(scheduled_at, "%Y-%m-%d").replace(tzinfo=timezone(timedelta(hours=7))).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")`.

---

### H4 — Tag ACL sync plan entirely unimplemented (in-flight, phases 0/0)

**Directory:** `plans/260619-0830-crm-tag-acl-sync/`

Plan has 4 phases (schema, seed, sync, write-back). **All are ⬜ Todo** — no `crm_ext_tag` or `crm_ext_tag_map` migration exists, no `tag_sync.py`. The tag system currently has no source tracking (`source` column on `crm_party_tag` not yet added).

**Risk:** Without this schema, tags applied by sync would silently overwrite or conflict with manually-set CRM tags. The plan has no partial rollout guard — if a developer adds `crm_party_tag(source='sapo_v2_sync')` rows before Phase 01 migration runs, the DB schema rejects them.

**Status:** Half-planned, zero code. Flag: ensure migration 0022 lands before any sync code writes to `crm_party_tag`.

---

### H5 — i18n JSON locale plan entirely unimplemented (in-flight, phases 0/6)

**Directory:** `plans/260618-1050-crm-i18n-json-locale/`

6-phase plan (infrastructure → templates). All phases are **Todo** — no `i18n.py`, no locale JSON files, no `t()` injection, no middleware. Badge catalog `hint` strings are still raw Python strings.

**Risk:** Work-in-progress without any guard. If a developer starts implementing phase 3 (badge catalog migration) before phase 1 (infrastructure), `t()` calls will raise `NameError` globally. No feature flag or partial-activation path is defined.

---

## MEDIUM

### M1 — `get_sapo_ids_for_parties` uses f-string SQL construction (safe but pattern is risky)

**File:** `crm/src/adapters/outbound/sqlite/party_repository.py:92-100`

```python
placeholders = ",".join("?" * len(party_ids))
sql = (
    f"SELECT party_id, MIN(CAST(identity_value AS INTEGER)) AS customer_id"
    f" FROM crm_party_identity"
    f" WHERE identity_type = 'sapo_customer'"
    f" AND party_id IN ({placeholders})"
    ...
)
```

The `IN ({placeholders})` is built from `"?" * len(party_ids)` — values are parameterized. The f-string only interpolates a count of `?` placeholders, not user data. **Not a SQL injection vector currently**, but the pattern is fragile: future edits that change `placeholders` to include actual values would introduce injection.

**Risk:** Low-risk today. The pattern should be documented or wrapped in a helper to make it clear only `?` count is interpolated.

---

### M2 — `screen_management._build_dedup_party_names` late-binding lambda (benign today but brittle)

**File:** `crm/src/adapters/inbound/web/screen_management.py:514`

```python
p = _safe(lambda: parties_svc.get_by_id(pid), None, "")
```

Lambda captures `pid` by reference from the enclosing for-loop. Because `_safe()` calls the lambda immediately, `pid` holds the current loop value — **not a bug today**. However, if this pattern were ever refactored to collect lambdas and call them later (e.g., for async fan-out), all lambdas would resolve to the last `pid` value. Same pattern appears at L500 with `t.party_id`.

**Fix:** Use `lambda pid=pid:` default-capture pattern to make intent explicit and future-safe.

---

### M3 — `consent_contact` column alias inconsistency in profile UPDATE vs SELECT

**File:** `crm/src/adapters/outbound/sqlite/profile_repository.py:132,170`

`_SQL_GET` reads `consent_enum AS consent_contact`. The `_SQL_UPSERT` writes to `consent_enum`. But `_SQL_UPDATE_PROFILE` (L159-170) joins `SET ... consent_contact, ...` — referencing the view alias `consent_contact` not the underlying column `consent_enum`. This works only if `crm_party_360` is a view that exposes `consent_contact` as an alias. If someone queries `crm_customer_profile` directly they need to use `consent_enum`. The dual-name pattern creates confusion.

**Risk:** Future migrations that add a real `consent_contact` column to `crm_customer_profile` would silently shadow the alias and break reads that rely on the `AS consent_contact` alias in `_SQL_GET`.

---

### M4 — No CSRF protection on state-changing POSTs/PATCHes/DELETEs

**Scope:** All web routes in `screen_management.py`, `screen_modals.py`, `screen_inbox.py`, `screen_tasks_board.py`, `screen_worklist.py`

FastAPI + HTMX setup has no CSRF middleware. HTMX does not set `X-Requested-With` or a CSRF token by default. All mutating form submissions (`POST /parties`, `POST /dedup/{id}/merge`, `DELETE /settings/tags/{id}`, etc.) are unprotected.

**Risk:** LAN-only mitigates practical exposure, but if any LAN host is compromised (phishing, SSRF from another LAN service), CSRF attacks become trivial. Merge two parties, delete tags, reassign owner — all via crafted HTML.

**Fix:** Add a `SameSite=Strict` cookie to the session or use `starlette-csrf`; or at minimum add `HX-Request: true` header check on mutating endpoints (HTMX sends it; direct form submit does not).

---

### M5 — `SegmentService.create_segment` accepts both `dict` and keyword API inconsistently

**File:** `crm/src/adapters/inbound/web/screen_management.py:105`

```python
seg = segments_svc.create_segment(
    name=name.strip(),
    description=description.strip(),
    is_dynamic=(is_dynamic == "true"),
    definition=definition,
)
```

But `SegmentService.create_segment(self, data: dict)` at L46 takes a single `data: dict`. The screen calls it with kwargs. This raises `TypeError` at runtime when a segment is created from the web UI.

**Risk:** `POST /segments` raises `TypeError: create_segment() got unexpected keyword argument 'name'`.

**Fix:** Either change the service signature to accept kwargs, or change the screen call to pass a dict.

---

### M6 — N+1 queries in segments list, campaigns list, dedup review

**Files:** `screen_management.py:77-79` (segments list), `screen_management.py:175-181` (campaigns list), `screen_management.py:329` (dedup review)

Each segment issues `list_members(s.segment_id)` per segment row. Each campaign issues `get_segment(c.segment_id)`. Dedup review issues `get_by_id(pid)` per candidate. All wrapped in `_safe()` which silently swallows errors and returns defaults — making N+1 problems invisible in logs.

**Risk:** With 50 segments, 50 separate SQLite queries fire synchronously. Acceptable now but will degrade noticeably at scale.

---

## LOW

### L1 — `worklist` protocol `get_task` defined but unused in fetch path

**File:** `crm/src/adapters/inbound/web/screen_worklist.py:42`

```python
class TaskQuerier(Protocol):
    def list_tasks(self, party_id: str, status: str) -> list[Task]: ...
    def get_task(self, task_id: str) -> Optional[Task]: ...
```

`get_task` is in the protocol and used in `handle_mark_task_done` (L170) — correct. Not a bug. But the protocol's `list_tasks` argument name (`party_id`) is wrong as noted in H2.

---

### L2 — `app_user_repository.py` f-string SQL construction

**File:** `crm/src/adapters/outbound/sqlite/app_user_repository.py:98-100`

```python
set_clause = ", ".join(f"{col} = ?" for col in fields)
sql = f"UPDATE crm_app_user SET {set_clause} WHERE user_id = ?"
```

`col` comes from `_ALLOWED = {"email", "full_name", "role", ...}` — a hardcoded whitelist. User input is never interpolated into the column name. **Not an injection vector today** but the whitelist filtering should be made explicit via a comment.

---

### L3 — `screen_resolver.py` imports from bare `domain.entities.party` (missing `crm.src.` prefix)

**File:** `crm/src/adapters/inbound/web/screen_resolver.py:20`

```python
from domain.entities.party import Party
```

vs other files using `from crm.src.domain.entities.party import Party`. This works only if `crm/src/` is on `sys.path`. Inconsistency may cause import failures if the module is loaded from a different working directory or test runner.

---

### L4 — Dead code: `screen_modals.py` defines `WebDeps` but it is also defined in `routes.py`

**Files:** `crm/src/adapters/inbound/web/screen_modals.py:42-48`, `crm/src/adapters/inbound/web/routes.py:16-19`

Both files define a `WebDeps` class. The one in `routes.py` is different (fewer fields). The one in `screen_modals.py` is the one used at runtime (via `init_modals`). The `routes.py` version appears to be dead code or stale.

---

## Unresolved Questions

1. **C1 detail**: Are `record_conversion`, `update_target_status`, `get_target`, `get_campaign` meant to be added to `CampaignService`, or should the screen call the repository directly? The former is architecturally correct (service as facade).
2. **C2 scope**: Should `_evaluate_rule` + `_find_earliest_order` go to a new `SegmentQueryRepository`/`CampaignQueryRepository` port, or is a "domain query object" pattern preferred?
3. **M3 risk**: Is `crm_party_360` a VIEW that exposes `consent_contact` as an alias? If so, does `UPDATE crm_customer_profile SET consent_contact = ?` (L170) work or does it fail because the underlying column is `consent_enum`?
4. **Tag ACL / i18n plans**: Both are ⬜ Todo with no ETA. Are they blocked on capacity, or is there a sequencing dependency that must be resolved first?
5. **M5 confirmation**: Is `SegmentService.create_segment` actually called with kwargs anywhere in the running app (web layer)? If so, has it been tested? The mismatch would cause an immediate 500.

---

## FIXES APPLIED 260623

| # | Finding | Status | File:line | Notes |
|---|---------|--------|-----------|-------|
| C1a | `create_campaign` kwargs → dict | APPLIED | `screen_management.py:203` | Changed to pass dict |
| C1b | `record_conversion` missing on service | APPLIED | `campaign_service.py:171` | Added method |
| C1c | `update_target_status` missing on service | APPLIED | `campaign_service.py:185` | Added method (delegates to `update_target`) |
| C1d | `get_target` missing on service | APPLIED | `campaign_service.py:168` | Added method |
| C1e | `get_campaign` missing on service | APPLIED | `campaign_service.py:130` | Added method |
| C1f | SQLiteCampaignRepository.update() signature mismatch | APPLIED | `campaign_repository.py:60` | Aligned to port: `update(campaign: Campaign)` |
| C1g | SQLiteCampaignRepository.update_target() signature mismatch | APPLIED | `campaign_repository.py:82` | Aligned to port: `update_target(target: CampaignTarget)` |
| C1h | SQLiteCampaignRepository.list() missing | APPLIED | `campaign_repository.py:101` | Added `list()` alias calling `list_campaigns()` |
| C1i | SQLiteSegmentRepository.upsert_member() signature mismatch | APPLIED | `segment_repository.py:100` | Aligned to port: `upsert_member(member: SegmentMember)` |
| C1j | SQLiteSegmentRepository.list() missing | APPLIED | `segment_repository.py:86` | Added `list()` alias calling `list_segments()` |
| C2 | Hexagonal breach: `sqlite3` in application layer | APPLIED | `campaign_service.py`, `segment_service.py` | Removed `sqlite3` import + `conn` param; SQL moved to adapters: `campaign_repository.fetch_consent_map()`, `campaign_repository.find_earliest_order()`, `segment_repository.evaluate_rule()`. Port updated. Composition wiring updated. |
| C3 | Unauthenticated Messenger webhook | PLANNED | `plans/260623-2257-crm-messenger-webhook-hmac/plan.md` | Deferred — no live FB traffic; plan written |
| H1 | `\| safe` on label in macro | APPLIED | `order_financial_tab.html:16` | Removed `\| safe`; COGS badge HTML replaced with `caption` param |
| H2 | `TaskQuerier.list_tasks` param `party_id` → `assignee_id` | APPLIED | `screen_worklist.py:41` | Renamed to `assignee_id` |
| H3 | `scheduled_at` stores ICT offset, not UTC | APPLIED | `screen_management.py:202` | Converts to UTC ISO-8601 before storing |
| H4 | Tag ACL sync unimplemented | DEFERRED | plans/260619-0830-crm-tag-acl-sync/ | Capacity/sequencing decision for owner |
| H5 | i18n JSON locale unimplemented | DEFERRED | plans/260618-1050-crm-i18n-json-locale/ | Capacity/sequencing decision for owner |
| M1 | f-string placeholders in `party_repository.py` | DEFERRED | Already safe (only `?` count interpolated); L2 comment fix approach applied to analogous L2 case |
| M2 | Late-binding lambdas | APPLIED | `screen_management.py:78,178,500,514` | Added default-capture `pid=pid` pattern to all four lambda sites |
| M3 | `consent_contact` alias inconsistency | DEFERRED | `profile_repository.py:132,170` | Requires schema investigation (Q3 above); no code change without confirming view structure |
| M4 | No CSRF on state-changing routes | DEFERRED | All screen files | LAN-only; fix requires framework-level middleware decision; flag for owner |
| M5 | `create_segment` kwargs mismatch | APPLIED | `screen_management.py:105` | Changed to pass dict |
| M6 | N+1 queries | DEFERRED | `screen_management.py:77,175,329` | Acceptable at current scale; document for future optimisation |
| L1 | Protocol `get_task` unused in fetch path | NOT A BUG | `screen_worklist.py:42` | Used in `handle_mark_task_done`; note left |
| L2 | `app_user_repository` f-string SQL | APPLIED | `app_user_repository.py:89` | Added whitelist comment clarifying only column name count is interpolated |
| L3 | `screen_resolver.py` bare import | DEFERRED | `screen_resolver.py:20` | Pre-existing; no import failure in current test run; leave for import cleanup pass |
| L4 | Dead `WebDeps` in `routes.py` | DEFERRED | `routes.py:15` | Dead code; low risk; leave for cleanup pass |

**Test result:** 514 passed, 42 skipped (pre-existing skips for Docker-env tests). `test_web_templating.py` excluded — `ModuleNotFoundError: fastapi` is a pre-existing host-env issue, confirmed failing before this patch.

**Unresolved questions (inherited):**
- Q3: Is `crm_party_360` a VIEW exposing `consent_contact` alias? Needed before fixing M3.
- Q4: ETA/sequencing for Tag ACL (H4) and i18n (H5) plans.
