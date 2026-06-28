"""FastAPI router — debug and profile-sync endpoints.

GET /debug/me       — inspect CF Access JWT claims and current user.
POST /profile/sync  — manual/client-side name sync until CF custom claims are wired.
"""
from __future__ import annotations

from typing import Optional

import jwt
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from application.app_user_service import AppUserService


class ProfileSyncBody(BaseModel):
    full_name: str
    lark_id: Optional[str] = None


def make_debug_router(app_user_svc: AppUserService) -> APIRouter:
    """Return a configured APIRouter with debug and profile-sync endpoints."""
    router = APIRouter()

    @router.get("/debug/me")
    def debug_me(request: Request):
        token = request.headers.get("Cf-Access-Jwt-Assertion", "")
        raw = jwt.decode(token, options={"verify_signature": False}) if token else {}
        user = request.state.current_user
        return JSONResponse({
            "current_user": {
                "user_id": user.user_id, "email": user.email,
                "full_name": user.full_name, "role": user.role,
            } if user else None,
            "jwt_payload": raw,
            "headers": {
                k: v for k, v in request.headers.items()
                if k.lower().startswith("cf-")
            },
        })

    @router.post("/profile/sync")
    def profile_sync(body: ProfileSyncBody, request: Request):
        """Manual or client-side name sync (used once CF custom claims are wired)."""
        user = request.state.current_user
        if not user:
            return JSONResponse({"ok": False}, status_code=401)
        name = body.full_name.strip()
        if name:
            app_user_svc.provision_or_sync(user.email, name, user.role)
        return JSONResponse({"ok": True})

    return router
