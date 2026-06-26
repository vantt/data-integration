# Phase 02: CRM Auth Layer

**Type:** Code implementation  
**Architecture:** Hexagonal (ports & adapters)  
**Branch:** main

## Scope

Thêm CF Access JWT verification và role-based guard vào CRM FastAPI app, không phá vỡ hexagonal boundary hiện tại.

## Hexagonal layers

```
Domain         — AppUser entity (unchanged), ROLE_* constants (unchanged)
Port/outbound  — AppUserRepository (unchanged: get_by_email, create, update)
Application    — NEW: AppUserService.provision_or_sync()
Inbound adapter— NEW: CFAccessMiddleware (Starlette BaseHTTPMiddleware)
               — UPDATE: auth_dependency.py → add require_admin()
Config         — UPDATE: config.py → 4 new env var readers
Composition    — UPDATE: composition.py → wire AppUserService + middleware
Web screen     — UPDATE: screen_management.py → /settings* depend on require_admin
Template       — UPDATE: layout.html → header user button hiển thị tên
docker-compose — UPDATE: crm service → 4 new env vars
requirements   — UPDATE: requirements.txt → add PyJWT + cryptography
```

## Files to create

### `crm/src/application/app_user_service.py`

```python
"""AppUserService — application service for CRM user provisioning.

Sits between the CF Access inbound adapter and the AppUserRepository port.
Does NOT import any HTTP/DB adapter directly.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from domain.entities.app_user import AppUser, VALID_ROLES, ROLE_SALES
from domain.ports.app_user_repository import AppUserRepositoryPort  # Protocol

log = logging.getLogger(__name__)


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


class AppUserService:
    def __init__(self, repo: AppUserRepositoryPort) -> None:
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
```

### `crm/src/adapters/inbound/http/cf_access_middleware.py`

```python
"""cf_access_middleware.py — Starlette middleware: verify Cloudflare Access JWT.

Injects request.state.current_user: Optional[AppUser] on every request.
If CF_ACCESS_AUDIENCE is unset → bypass (dev/LAN mode, current_user = None).

JWT verification:
  - Fetches JWKS once from https://<CF_TEAM_DOMAIN>/cdn-cgi/access/certs
  - Caches keys in memory for the process lifetime (restart refreshes)
  - RS256 only — CF Access always signs with RS256
  - Validates aud claim against CF_ACCESS_AUDIENCE

Role mapping:
  - Reads Lark role from JWT at path CF_ROLE_CLAIM (dot-separated: "custom.role")
  - Maps to CRM role via CF_ROLE_MAP dict
  - Falls back to "sales" if unmapped
"""
from __future__ import annotations

import json
import logging
import urllib.request
from typing import Optional

import jwt  # PyJWT
from jwt.algorithms import RSAAlgorithm
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from application.app_user_service import AppUserService
from config import cf_access_audience, cf_team_domain, cf_role_claim, cf_role_map

log = logging.getLogger(__name__)

# Module-level JWKS cache (populated on first verified request).
_JWKS_CACHE: dict[str, object] = {}


def _fetch_jwks(team_domain: str) -> dict[str, object]:
    global _JWKS_CACHE
    if _JWKS_CACHE:
        return _JWKS_CACHE
    url = f"https://{team_domain}/cdn-cgi/access/certs"
    with urllib.request.urlopen(url, timeout=5) as resp:
        data = json.loads(resp.read())
    # Build kid → public_key mapping
    for key_data in data.get("keys", []):
        kid = key_data.get("kid")
        if kid:
            _JWKS_CACHE[kid] = RSAAlgorithm.from_jwk(json.dumps(key_data))
    log.info("CF Access JWKS loaded: %d key(s)", len(_JWKS_CACHE))
    return _JWKS_CACHE


def _get_claim(payload: dict, path: str) -> str:
    """Read a dot-separated claim path from JWT payload. E.g. 'custom.role'."""
    parts = path.split(".")
    val = payload
    for p in parts:
        if not isinstance(val, dict):
            return ""
        val = val.get(p, "")
    return str(val) if val else ""


class CFAccessMiddleware(BaseHTTPMiddleware):
    """Verify CF Access JWT and inject request.state.current_user."""

    def __init__(self, app, user_svc: AppUserService) -> None:
        super().__init__(app)
        self._user_svc = user_svc
        self._audience = cf_access_audience()
        self._team_domain = cf_team_domain()
        self._role_claim = cf_role_claim()
        self._role_map: dict[str, str] = cf_role_map()

        if not self._audience:
            log.warning(
                "CF_ACCESS_AUDIENCE unset — auth BYPASSED (LAN/dev mode). "
                "Set it to enable Cloudflare Access protection."
            )

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.current_user = None

        if not self._audience:
            # Bypass: dev/LAN mode
            return await call_next(request)

        token = request.headers.get("Cf-Access-Jwt-Assertion", "")
        if not token:
            # No JWT — CF Access should have blocked this; pass through
            # (healthz, static files, etc. don't need a user)
            return await call_next(request)

        try:
            jwks = _fetch_jwks(self._team_domain)
            header = jwt.get_unverified_header(token)
            kid = header.get("kid", "")
            pub_key = jwks.get(kid)
            if pub_key is None:
                log.warning("CF Access JWT: unknown kid=%r", kid)
                return Response("Unauthorized", status_code=401)

            payload = jwt.decode(
                token,
                pub_key,
                algorithms=["RS256"],
                audience=self._audience,
            )
        except jwt.ExpiredSignatureError:
            return Response("Token expired", status_code=401)
        except Exception:
            log.exception("CF Access JWT verification failed")
            return Response("Unauthorized", status_code=401)

        email: str = payload.get("email", "")
        name: str = payload.get("name", "") or email
        lark_role: str = _get_claim(payload, self._role_claim)
        crm_role: str = self._role_map.get(lark_role, "sales")

        try:
            user = self._user_svc.provision_or_sync(email, name, crm_role)
            request.state.current_user = user
        except Exception:
            log.exception("user provisioning failed for %s", email)

        return await call_next(request)
```

## Files to modify

### `crm/src/config.py` — append 4 new readers

```python
import json as _json

def cf_access_audience() -> str:
    """CF Access application audience tag. Empty = bypass (dev mode)."""
    return os.environ.get("CF_ACCESS_AUDIENCE", "")


def cf_team_domain() -> str:
    """Cloudflare team domain, e.g. 'myteam.cloudflareaccess.com'."""
    return os.environ.get("CF_TEAM_DOMAIN", "")


def cf_role_claim() -> str:
    """Dot-separated JWT claim path for Lark role. E.g. 'custom.role' or 'role'."""
    return os.environ.get("CF_ROLE_CLAIM", "role")


def cf_role_map() -> dict:
    """JSON mapping: Lark role value → CRM role string.
    
    Example env: CF_ROLE_MAP={"Admin":"admin","Manager":"manager","Sales":"sales"}
    """
    raw = os.environ.get("CF_ROLE_MAP", "{}")
    try:
        return _json.loads(raw)
    except Exception:
        return {}
```

### `crm/src/requirements.txt` — add JWT deps

```
PyJWT==2.9.0
cryptography==43.0.3
```

### `crm/src/adapters/inbound/http/auth_dependency.py` — add require_admin

Append after existing `require_api_token`:

```python
from fastapi import Request

def require_admin(request: Request) -> None:
    """FastAPI dependency: enforce admin role for CF-Access-authenticated users.

    No-op when CF_ACCESS_AUDIENCE is unset (dev bypass).
    Raises 403 if current_user is None or role != admin.
    """
    from config import cf_access_audience
    if not cf_access_audience():
        return  # bypass in dev mode

    user = getattr(request.state, "current_user", None)
    if user is None or user.role != "admin":
        from domain.entities.app_user import ROLE_ADMIN
        raise HTTPException(status_code=403, detail={"status": "forbidden"})
```

### `crm/src/adapters/inbound/web/screen_management.py` — guard /settings*

In `make_management_router()`, add dependency to all `/settings*` routes:

```python
from fastapi import Depends
from adapters.inbound.http.auth_dependency import require_admin

# Change all @router.get/post/patch/delete("/settings*"...) to include:
#   dependencies=[Depends(require_admin)]
# Example:
@router.get("/settings", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def settings(request: Request, tab: str = Query(default="custom_fields")):
    ...
```

### `crm/src/composition.py` — wire middleware + service

```python
# Add imports
from application.app_user_service import AppUserService
from adapters.inbound.http.cf_access_middleware import CFAccessMiddleware

# In create_app(), after line: app = FastAPI(...)
app_user_svc = AppUserService(app_user_repo)
app.add_middleware(CFAccessMiddleware, user_svc=app_user_svc)
```

### `crm/src/adapters/inbound/web/templates/layout.html` — header user chip

Replace static user button (lines ~100-108):

```html
<button class="icon-btn" type="button" aria-label="Tài khoản"
        title="{{ request.state.current_user.full_name if request.state.current_user else 'Guest' }}">
  <!-- icon: user -->
  <svg class="ico" width="15" height="15" viewBox="0 0 16 16" fill="none"
       stroke="currentColor" stroke-width="1.3" stroke-linecap="round"
       stroke-linejoin="round" aria-hidden="true">
    <circle cx="8" cy="5.5" r="2.6"></circle>
    <path d="M3.2 13.2c.5-2.6 2.4-4 4.8-4s4.3 1.4 4.8 4"></path>
  </svg>
  {% if request.state.current_user %}
  <span class="crm-nav__label" style="font-size:11px;max-width:80px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
    {{ request.state.current_user.full_name }}</span>
  {% endif %}
</button>
```

### `docker-compose.yml` — crm service env block

Thêm vào environment của service `crm`:

```yaml
- CF_ACCESS_AUDIENCE=${CF_ACCESS_AUDIENCE:-}
- CF_TEAM_DOMAIN=${CF_TEAM_DOMAIN:-}
- CF_ROLE_CLAIM=${CF_ROLE_CLAIM:-role}
- CF_ROLE_MAP=${CF_ROLE_MAP:-{}}
```

## Validation

```bash
# 1. Build và restart CRM
docker compose build crm && docker compose up -d crm

# 2. LAN mode (CF_ACCESS_AUDIENCE unset) — tất cả routes vẫn accessible
curl http://localhost:3007/healthz  # 200

# 3. /settings trả 403 khi có AUDIENCE nhưng không có JWT
curl -H "CF_ACCESS_AUDIENCE=test" http://localhost:3007/settings  # 403

# 4. Sau phase 01: login bằng Lark → /settings chỉ vào được nếu role=admin
```

## Risks / rollback

- `PyJWT` + `cryptography` thêm ~2MB vào image — acceptable
- JWKS fetch on startup: nếu CF unreachable → container vẫn start nhưng first request fail → có retry mechanism trong middleware
- Middleware order: `app.add_middleware()` LIFO → CF middleware chạy sau các middleware khác của FastAPI; đây là đúng vì ta cần request đã parsed
