"""AppUserService — application service for CRM user provisioning.

Sits between the CF Access inbound adapter and the AppUserRepository port.
Does NOT import any HTTP/DB adapter directly.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from domain.entities.app_user import AppUser, VALID_ROLES, ROLE_SALES

log = logging.getLogger(__name__)


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


class AppUserService:
    def __init__(self, repo) -> None:
        self._repo = repo

    def provision_or_sync(self, email: str, full_name: str, crm_role: str) -> AppUser:
        """Return existing AppUser or create one on first login.

        Updates full_name if it changed (Lark profile update).
        Role is NOT overwritten after initial creation (admin can change it manually).
        """
        if crm_role not in VALID_ROLES:
            log.warning("unknown crm_role %r → fallback to %r", crm_role, ROLE_SALES)
            crm_role = ROLE_SALES

        user = self._repo.get_by_email(email)
        now = _utcnow()

        if user is None:
            user = AppUser(
                user_id=str(uuid.uuid4()),
                email=email,
                full_name=full_name or email,
                role=crm_role,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            self._repo.create(user)
            log.info("auto-provisioned AppUser %s role=%s", email, crm_role)
            return user

        # Sync name if changed; never override role.
        updates: dict = {"updated_at": now}
        if full_name and user.full_name != full_name:
            updates["full_name"] = full_name
        if not user.is_active:
            log.warning("inactive user %s attempted login", email)
        self._repo.update(user.user_id, **updates)
        return user
