# Phase 02 — Backend Interpreter Endpoint

**Status:** pending  
**Effort:** 1.5h  
**Blockers:** Phase 01 (schema approved + PoC file ready)  
**File ownership (new):** `crm/src/adapters/inbound/http/script_nav_handler.py`  
**File ownership (modify):** `crm/src/composition.py`

---

## Purpose

Add a single POST endpoint that is a **near-pure function**:

```
input:  script (from repo) + current_node_id + outcome
output: next Node object (or terminal signal)
```

No session table. No LLM call. No mutable state on the server beyond what's already in the script file.

---

## Data Flow

```
Client (S14 JS)
  │  POST /api/parties/{party_id}/script-nav
  │  Body: { current_node_id: "reached_interest_check", outcome: "interested" }
  ▼
script_nav_handler.py
  │  1. Resolve party_id → customer_id  (reuse pattern from approach_script_handler.py:67-77)
  │  2. approach_repo.get_by_customer_id(customer_id)  → ApproachScript
  │  3. Guard: script is None → 404
  │  4. Guard: approach.recommended = false → 403 {"error": "stop_state"}
  │  5. Guard: script.data.get("nodes") is None → 404 {"error": "no_branching_script"}
  │  6. Look up node = nodes[current_node_id]
  │     - node not found → fallback: return entry_node node
  │  7. Find matching option: option where option["outcome"] == outcome
  │     - no match → return current node unchanged (idempotent, no crash)
  │  8. next_id = option["next"]
  │     - next_id is None → return {"terminal": true, "node": null}
  │     - next_id in nodes → return {"terminal": false, "node": nodes[next_id]}
  │     - next_id not in nodes → return entry_node (defensive fallback)
  ▼
JSON response  →  HTMX swaps #s14-node-area
```

---

## Endpoint Spec

```
POST /api/parties/{party_id}/script-nav
Content-Type: application/json

Request body:
{
  "current_node_id": "reached_interest_check",
  "outcome": "interested"
}

Response 200 — advance to next node:
{
  "terminal": false,
  "node": {
    "id": "pitch_reorder",
    "kind": "pitch",
    "say": "...",
    "hint": "...",
    "options": [
      { "label": "Đồng ý mua", "outcome": "purchased", "next": null },
      ...
    ]
  }
}

Response 200 — terminal (call complete, no next guidance):
{
  "terminal": true,
  "node": null
}

Response 403 — script is in STOP state:
{ "error": "stop_state" }

Response 404 — party/script/nodes not found:
{ "error": "not_found" | "no_branching_script" }
```

### Why POST not GET

The nav step will also trigger activity logging (Phase 04). A GET that has side effects is wrong. POST is correct even though the interpreter itself is stateless.

---

## Implementation Notes

### New file: `crm/src/adapters/inbound/http/script_nav_handler.py`

Structure mirrors `approach_script_handler.py` exactly:
- Module-level `_party_repo`, `_approach_repo` holders
- `wire_script_nav_router(party_repo, approach_repo)` factory called at startup
- Single `@router.post("/parties/{party_id}/script-nav")` handler
- Pure function `_resolve_next_node(nodes: dict, current_node_id: str, outcome: str) -> tuple[bool, dict | None]` — the interpreter core. Extracting it as a named function makes it trivially unit-testable without HTTP.

### Interpreter core logic (no framework deps)

```python
def _resolve_next_node(
    nodes: dict,
    current_node_id: str,
    outcome: str,
    entry_node_id: str,
) -> tuple[bool, dict | None]:
    """
    Returns (is_terminal, next_node_dict).
    Pure function — no I/O, no side effects.
    """
    node = nodes.get(current_node_id) or nodes.get(entry_node_id)
    if node is None:
        return True, None  # no usable node — treat as terminal

    for option in node.get("options", []):
        if option.get("outcome") == outcome:
            next_id = option.get("next")
            if next_id is None:
                return True, None  # explicit terminal
            next_node = nodes.get(next_id) or nodes.get(entry_node_id)
            return False, next_node

    # No matching option — return current node unchanged (idempotent)
    return False, node
```

This function has zero external deps. Unit tests: pass a dict literal, assert output. No mocking needed.

### Wiring: `crm/src/composition.py`

Add after the existing `wire_approach_script_router(...)` call:

```python
from adapters.inbound.http.script_nav_handler import wire_script_nav_router, router as script_nav_router
wire_script_nav_router(party_repo, approach_repo)
app.include_router(script_nav_router)
```

Verify the existing `wire_approach_script_router` call in `composition.py` to confirm the pattern (it's in `approach_script_handler.py:30-33`).

---

## Activity Logging Hook (Phase 04 preview)

The POST handler calls `activity_log.log_activity(...)` after resolving the next node. Phase 04 fills this in. For Phase 02, leave a `# TODO(phase-04): log nav step activity` comment at the logging point so the hook location is clear.

`activity_log` is already wired in `composition.py` for `screen_customer_360`. The same `ActivityService` instance can be passed to `wire_script_nav_router`.

---

## Tests

| Test | Type | What to assert |
|------|------|----------------|
| `_resolve_next_node` happy path | unit | `(False, nodes["pitch_reorder"])` |
| `_resolve_next_node` terminal | unit | `(True, None)` when `next=null` |
| `_resolve_next_node` unknown outcome | unit | returns current node unchanged |
| `_resolve_next_node` unknown node_id | unit | falls back to entry_node |
| `_resolve_next_node` entry_node missing entirely | unit | returns `(True, None)` |
| POST endpoint stop_state | integration | mock `recommended=False` → 403 |
| POST endpoint no_branching_script | integration | script without `nodes` → 404 |

Unit tests live in `crm/tests/` (check existing test structure before placing). No new test infra needed — the pure function needs no fixtures.

---

## Rollback

Remove `script_nav_router` from `composition.py` include list. Delete `script_nav_handler.py`. No DB change, no migration.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `composition.py` wiring order matters (repo not yet initialized) | Low | High | Mirror existing `wire_approach_script_router` call order exactly |
| Script file malformed — `nodes` is present but not a dict | Low | Low | `nodes.get(...)` on a non-dict raises TypeError → catch at handler level, return 404 |
| Concurrent reads of `FileApproachScriptRepository` while script file is being written | Very Low | Low | File repo is read-only per call; Python GIL + os-level read atomicity sufficient for file sizes in play |
