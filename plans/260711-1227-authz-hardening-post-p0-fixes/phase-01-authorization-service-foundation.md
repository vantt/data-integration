---
phase: 1
title: "Authorization Service Foundation"
status: completed
priority: P1
dependencies: []
---

# Phase 1: Authorization Service Foundation

## Overview

Both Phase 2 (unclaim ownership) and Phase 3 (resolve-actions IDOR) need the same kind of decision: "does actor X have the right relationship to resource Y?" Rather than writing 2 near-identical inline `==` comparisons in 2 unrelated files (`task_service.py`, `activity_side_effects.py`), this phase extracts a small, real, hexagonal-architecture service — `AuthorizationService` — as the single place that decision logic lives.

**Explicitly NOT in scope** (discussed with user): a full RBAC system. `AppUser.role` exists (`app_user.py:13-39`) but is documented as "informational in v1 — auth deferred (LAN-trust model)" — there is no permission-check middleware, no role-based rule engine, and building one now would be speculative (no second consumer exists yet beyond "is this person the owner"). This phase builds the minimum CORRECT seam — a proper service class with clear single responsibility, in the right architectural layer, unit-testable in isolation — sized for today's 2 ownership checks, structured so that when real RBAC work happens later, it extends this service's methods rather than requiring every call site to be found and rewired individually.

**Interface vs. internals (explicit split, per user direction)**: the PUBLIC INTERFACE — class name, method names, parameter/return types (`is_owner(resource_assignee_id, actor_id) -> bool`, `is_same_party(resource_party_id, expected_party_id) -> bool`) — must be properly designed and stable, because Phase 2/3's call sites are written against it and a future RBAC upgrade should not need to touch those call sites. The INTERNAL implementation of each method is deliberately ad-hoc/minimal for v1 (literally a null-check + `==`) — when real role-based rules exist, the method BODIES get richer (e.g. check a role table, consult a policy), the SIGNATURES do not change. Do not conflate this with "make the interface generic/abstract too" — e.g. do not collapse both methods into one stringly-typed `authorize(actor_id, action: str, **kwargs)` dispatcher to look more "enterprise"; that trades clean typed call sites for premature genericity and is a worse interface, not a more standard one. 2 distinctly-named typed methods for 2 distinct authorization concerns (identity-ownership vs. scope-containment) IS the standard shape here, not a compromise.

## Requirements

- One new `application/authorization_service.py` — pure logic, no IO, no adapter imports (matches this codebase's existing "pure domain + ports only" convention already documented in `activity_side_effects.py`'s own docstring).
- Two methods covering today's 2 needs: `is_owner(resource_assignee_id, actor_id) -> bool` (Phase 2) and `is_same_party(resource_party_id, expected_party_id) -> bool` (Phase 3) — both are trivial comparisons TODAY, but living behind named, testable methods on a single class means a future role-check extension touches one file, not N call sites scattered across the codebase.
- **Wired once in `composition.py`, ONE shared instance, threaded explicitly everywhere it's needed — no exceptions, no inline re-construction anywhere else.** (Revised after red-team review — the original "fallback to inline construction if threading proves awkward" language was correctly flagged by 3 independent reviewers as a design smell: a service claiming to be "the single source of truth" that sometimes gets bypassed by ad-hoc re-construction isn't actually centralized. The fix isn't a different class shape, it's discipline: constructor injection for classes (`TaskService`), explicit parameter passing for plain functions (`resolve_actions_and_tasks`, `bulk_resolve`, and every function in between them and `composition.py` in the call chain) — this is not identical mechanics between the two call shapes, but it IS the correct hexagonal pattern for each, and "explicit parameter passing down a call chain" is standard practice for plain-function DI, not a workaround. Phase 3's Implementation Steps must show the FULL threaded chain, not stop at "the immediate caller.")
- Zero behavior change on its own — this phase alone does nothing user-visible; it's pure foundation for phases 2 and 3.

## Architecture

```python
# crm/src/application/authorization_service.py
"""Centralized authorization/ownership decisions — single source of truth for
"can actor X act on resource Y" checks. v1 scope: pure identity comparison,
no role/permission logic (AppUser.role is informational-only, auth deferred
per domain/entities/app_user.py). Designed as the seed for future RBAC: when
role-based rules are needed, they extend the methods here — callers don't
change, they just get stricter answers back."""
from typing import Optional


class AuthorizationService:
    def is_owner(self, resource_assignee_id: Optional[str], actor_id: Optional[str]) -> bool:
        """True if actor_id is the resource's assignee. Requires both to be
        non-empty — an unassigned resource (assignee_id=None) is not "owned"
        by anyone under this check; callers needing different semantics for
        the unassigned case handle that separately (e.g. "not_found" vs
        "forbidden" branching stays in the calling service, not here)."""
        if not actor_id or not resource_assignee_id:
            return False
        return resource_assignee_id == actor_id

    def is_same_party(self, resource_party_id: Optional[str], expected_party_id: str) -> bool:
        """True if a resource (action/task) genuinely resolves to the
        expected party_id — used to prevent cross-party IDOR on bulk-resolve
        operations. Unresolvable resources (resource_party_id=None) fail
        closed (return False), not open."""
        if not resource_party_id:
            return False
        return resource_party_id == expected_party_id
```

No new domain entity, no new port/Protocol needed — this is a plain application-layer class (matches the shape of other application services in this codebase, e.g. `NoteService`, `TaskService` themselves), stateless, safe to instantiate once and share, or construct fresh per call (cheap either way — no IO in the constructor).

## Related Code Files

- Create: `crm/src/application/authorization_service.py`
- Create: `crm/src/tests/test_authorization_service.py` (pure unit tests, no DB/fixtures needed — this class has zero IO)
- Modify: `crm/src/composition.py` (instantiate `AuthorizationService()` once, make available for Phase 2/3's wiring — exact injection point depends on how those phases end up threading it through; if straightforward, wire it as a shared singleton-style instance passed into both `TaskService(...)` and wherever `resolve_actions_and_tasks`'s caller chain needs it)

## Implementation Steps

1. Create `authorization_service.py` with the `AuthorizationService` class and its 2 methods exactly as specified above (or with equivalent behavior — keep names `is_owner`/`is_same_party` since Phase 2/3 reference them by these names).
2. Create `test_authorization_service.py`: unit tests for both methods — `is_owner`: matching ids → True; mismatched ids → False; either side empty/None → False. `is_same_party`: matching → True; mismatched → False; `resource_party_id=None` → False (fail closed).
3. Instantiate once in `composition.py` (e.g. `authz_service = AuthorizationService()` near where other application services are constructed) — do NOT wire it into `TaskService`/`resolve_actions_and_tasks` yet, that's Phase 2/3's job; this phase just makes the instance available.
4. Run the new unit tests + full suite to confirm zero regressions (this phase adds a new unused-until-Phase-2/3 class, should be inert).

## Success Criteria

- [x] `AuthorizationService.is_owner()` — 4 test cases (match/mismatch/empty-actor/empty-resource), all pass.
- [x] `AuthorizationService.is_same_party()` — 3 test cases (match/mismatch/None-resource), all pass.
- [x] Zero adapter imports in `authorization_service.py` (pure logic, verified by reading the file — no `sqlite3`, no `fastapi`, no adapter-layer imports).
- [x] `composition.py` instantiates the service; full suite green (this phase is inert on its own, no user-visible behavior change).

## Risk Assessment

- **Risk**: over-building this "for RBAC later" — mitigated by keeping it to exactly 2 methods matching today's 2 concrete needs, no speculative role/permission parameters, no premature `Resource`/`Actor` domain entities. If Phase 2/3's actual implementation reveals a 3rd shape of check is needed, add it then — don't guess additional methods now.
- **Risk (resolved, was a Critical-adjacent finding across 3 reviewers)**: Phase 3's call chain (`execute_side_effects` → `resolve_actions_and_tasks`, and separately `register_activity_routes` → `bulk_resolve`/`handle_resolve_async` → `resolve_actions_and_tasks`) has multiple intermediate functions between `composition.py` and the actual check. Phase 3 must thread `authz` through EVERY one of them explicitly — enumerate the full chain in Phase 3's Related Code Files, don't just list the 2 endpoints. This is mechanical (1 new param per function in the chain) but must be complete, not partial.
- **Rollback**: entirely new, unused-until-consumed file — zero risk to existing code, trivial to delete if the design doesn't pan out in Phase 2/3.
