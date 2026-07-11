"""Centralized authorization/ownership decisions — single source of truth for
"can actor X act on resource Y" checks. v1 scope: pure identity comparison,
no role/permission logic (AppUser.role is informational-only, auth deferred
per domain/entities/app_user.py). Designed as the seed for future RBAC: when
role-based rules are needed, they extend the methods here — callers don't
change, they just get stricter answers back."""
from __future__ import annotations

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
