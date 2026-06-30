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


def _is_derived_name(name: str, email: str) -> bool:
    """True if name was mechanically derived from email prefix (not a real IDP name)."""
    prefix = email.split("@")[0]
    parts = prefix.replace(".", " ").replace("_", " ").replace("-", " ").split()
    derived = " ".join(p.capitalize() for p in parts) if parts else email
    return name == derived or name == email


class AppUserService:
    def __init__(self, repo, staff_resolver=None) -> None:
        self._repo = repo
        self._staff_resolver = staff_resolver  # StaffIdResolver | None

    def provision_or_sync(self, email: str, full_name: str, crm_role: str, lark_user_id: str = "") -> AppUser:
        """Return existing AppUser or create one on first login.

        Syncs full_name (protected from derived-name overwrites) and lark_user_id.
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
                lark_user_id=lark_user_id or None,
            )
            self._repo.create(user)
            log.info("auto-provisioned AppUser %s role=%s lark_user_id=%s", email, crm_role, lark_user_id)
            # Resolve Sapo staff_id once on first provision; non-blocking on failure.
            self._try_sync_staff_id(user.user_id, email)
            return self._repo.get_by_email(email) or user

        # Sync name and lark_user_id; never override role.
        # Never overwrite a real IDP name with an email-derived fallback.
        updates: dict = {"updated_at": now}
        if full_name and user.full_name != full_name:
            if not _is_derived_name(full_name, email) or _is_derived_name(user.full_name, email):
                updates["full_name"] = full_name
        if lark_user_id and user.lark_user_id != lark_user_id:
            updates["lark_user_id"] = lark_user_id
        if not user.is_active:
            log.warning("inactive user %s attempted login", email)
        self._repo.update(user.user_id, **updates)
        # Backfill staff_id on subsequent logins if still unset (e.g. dim_staff was unavailable on provision).
        if user.staff_id is None:
            self._try_sync_staff_id(user.user_id, email)
        # Re-fetch so caller sees the updated values (update() mutates DB, not the object).
        return self._repo.get_by_email(email) or user

    def _try_sync_staff_id(self, user_id: str, email: str) -> None:
        """Resolve and persist staff_id from dim_staff; no-op when resolver absent or lookup fails."""
        if self._staff_resolver is None:
            return
        try:
            sid = self._staff_resolver.resolve(email)
            if sid is not None:
                self._repo.update(user_id, staff_id=sid)
                log.info("synced staff_id=%s for user %s", sid, email)
        except Exception as exc:
            log.debug("staff_id sync failed for %s: %s", email, exc)
