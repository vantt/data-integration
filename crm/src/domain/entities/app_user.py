"""CRM AppUser domain entity — staff accounts mapped to Sapo staff records.

Pure dataclasses; no HTTP/DB adapter imports.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Role constants
# ---------------------------------------------------------------------------
ROLE_SALES = "sales"
ROLE_CARE = "care"
ROLE_MANAGER = "manager"
ROLE_ADMIN = "admin"
VALID_ROLES = [ROLE_SALES, ROLE_CARE, ROLE_MANAGER, ROLE_ADMIN]


# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------

@dataclass
class AppUser:
    """CRM staff account mapped to a Sapo staff record.

    Role is informational in v1 (auth deferred — LAN-trust model).
    """
    user_id: str        # UUID (TEXT in SQLite)
    email: str
    full_name: str
    role: str           # sales|care|manager|admin
    is_active: bool
    created_at: str     # UTC ISO-8601 with 'Z'
    updated_at: str     # UTC ISO-8601 with 'Z'
    lark_user_id: Optional[str] = None  # Lark open_id (ou_...) from CF Access JWT custom.sub
