"""AJAX (JSON) routes for the Hug claim station — the JS-driven happy path.

  GET  /hug/claim/check-token  -> token state relative to the current session
  GET  /hug/claim/check-field  -> per-field live validation via the registry
  POST /hug/claim/bind         -> server-validated bind + best-effort D1 push

All endpoints return HTTP 200 (errors encoded in the JSON body) unless noted.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from hug import d1_push
from hug.claim_fields import CLAIM_FIELDS, VALIDATORS, get_field
from hug.repository import AlreadyBoundError
from hug.tokens import human_code, is_valid_token, normalize_input

from domain.ports.hug_ports import HugTokenPort

log = logging.getLogger(__name__)

# Promoted columns: fields that have a dedicated column in hug_token (+ bind_token param).
# Any CLAIM_FIELDS key NOT in this set lands in bind_attributes JSON automatically.
# When bind_token gains a new promoted parameter, add its key here too (same PR).
# See: repository.py bind_token for the parameter list this must match.
_PROMOTED_COLS: frozenset[str] = frozenset({"order_code", "is_gift"})


def make_claim_ajax_router(token_port: HugTokenPort) -> APIRouter:
    """Return the AJAX router bound to a HugTokenPort."""
    router = APIRouter()

    @router.get("/hug/claim/check-token", response_class=JSONResponse)
    async def check_token(token: str = "", session: str = "") -> JSONResponse:
        """Return the current state of a token relative to the given session.

        States:
          invalid         — token string fails format check (not a valid Hug token)
          unknown         — token not found in local hug.db (not minted here)
          ready           — minted + printed, not yet claimed — safe to bind
          rebind_ok       — already bound, same session → mid-operation correction OK
          blocked         — already bound to a DIFFERENT session → show red warning
        """
        norm = normalize_input(token)
        if not is_valid_token(norm):
            return JSONResponse({"state": "invalid", "message": "Tem không hợp lệ"})

        row = token_port.get_token(norm)
        if row is None:
            return JSONResponse({"state": "unknown", "message": "Tem chưa mint"})

        if row["status"] != "bound":
            return JSONResponse({"state": "ready", "message": "Tem sẵn sàng"})

        # Bound: compare sessions
        stored = row["bind_session_id"]
        if stored and session and stored != session:
            return JSONResponse({
                "state": "blocked",
                "message": "Tem đã được claim bởi phiên khác",
            })
        # Same session (or either side empty) → re-bind allowed
        return JSONResponse({"state": "rebind_ok", "message": "Tem đã claim — cho phép ghi đè"})

    @router.get("/hug/claim/check-field", response_class=JSONResponse)
    async def check_field(key: str = "", value: str = "", session: str = "") -> JSONResponse:
        """Dispatch per-field live validation to the VALIDATORS registry.

        Returns {ok: true|false|null, message: str}.
        ok=true  → green (valid).
        ok=false → red (invalid).
        ok=null  → amber (unknown/soft-fail — frontend should allow proceed).
        """
        field = get_field(key)
        if field is None:
            return JSONResponse({"ok": False, "message": f"Trường không hợp lệ: {key}"}, status_code=400)

        validate_key = field.get("validate")
        if validate_key is None:
            # No validator → always valid (e.g. is_gift boolean toggle)
            return JSONResponse({"ok": True, "message": "OK"})

        validator = VALIDATORS.get(validate_key)
        if validator is None:
            log.warning("check-field: no validator registered for key=%s", validate_key)
            return JSONResponse({"ok": None, "message": "Không có validator"})

        try:
            result = validator(value, session or None)
        except Exception as exc:  # noqa: BLE001
            log.error("check-field: validator %s raised: %s", validate_key, exc)
            result = {"ok": None, "message": "Lỗi kiểm tra"}

        return JSONResponse(result)

    @router.post("/hug/claim/bind", response_class=JSONResponse)
    async def claim_bind(request: Request) -> JSONResponse:
        """AJAX bind endpoint — JSON body {session_id, token, fields:{...}}.

        Server-side re-validates all required fields via the registry before
        binding.  Does NOT trust the frontend's pre-validation.

        Flow:
          1. Parse session_id, token, fields from JSON body.
          2. Check each required CLAIM_FIELDS key is present + non-empty.
          3. Run VALIDATORS for fields that have validate set.
             ok=False → reject (red).  ok=None → log warning, allow proceed.
          4. Split fields into promoted columns vs bind_attributes.
          5. bind_token → D1 push → return {ok, message, edge}.

        HTTP 200 always.  Errors encoded in {ok: false, message}.
        """
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "message": "Body không hợp lệ (JSON expected)"})

        session_id: str = (body.get("session_id") or "").strip()
        raw_token: str = (body.get("token") or "").strip()
        fields: dict = body.get("fields") or {}

        # Validate the token
        token = normalize_input(raw_token)
        if not is_valid_token(token):
            return JSONResponse({
                "ok": False,
                "message": f"Tem không hợp lệ: {raw_token or '(trống)'}",
            })

        # Server-side field validation
        for field_def in CLAIM_FIELDS:
            key = field_def["key"]
            val = fields.get(key)

            if field_def["required"] and not val:
                return JSONResponse({"ok": False, "message": f"Thiếu trường bắt buộc: {field_def['label']}"})

            validate_key = field_def.get("validate")
            if validate_key and val:
                validator = VALIDATORS.get(validate_key)
                if validator:
                    try:
                        result = validator(str(val), session_id or None)
                    except Exception as exc:  # noqa: BLE001
                        log.error("bind: validator %s raised: %s", validate_key, exc)
                        result = {"ok": None, "message": "Lỗi kiểm tra"}

                    if result.get("ok") is False:
                        return JSONResponse({"ok": False, "message": result.get("message", "Giá trị không hợp lệ")})
                    if result.get("ok") is None:
                        log.warning("bind: validator %s returned amber for value=%r — proceeding", validate_key, val)

        # Split into promoted columns vs dynamic bind_attributes
        promoted = {k: v for k, v in fields.items() if k in _PROMOTED_COLS}
        bind_attrs = {k: v for k, v in fields.items() if k not in _PROMOTED_COLS}

        order_code = str(promoted.get("order_code") or "").strip()
        is_gift_raw = promoted.get("is_gift")
        is_gift = is_gift_raw in (True, 1, "1", "true", "on", "yes")

        try:
            row = token_port.bind_token(
                token,
                order_code=order_code,
                is_gift=is_gift,
                bind_session_id=session_id or None,
                bind_attributes=bind_attrs,
            )
        except AlreadyBoundError as exc:
            return JSONResponse({"ok": False, "message": str(exc)})
        except KeyError:
            return JSONResponse({"ok": False, "message": f"Tem chưa mint: {token}"})
        except ValueError as exc:
            return JSONResponse({"ok": False, "message": str(exc)})
        except Exception as exc:  # noqa: BLE001
            log.error("hug claim/bind: bind failed token=%s: %s", token, exc)
            return JSONResponse({"ok": False, "message": f"Lỗi: {exc}"})

        # Best-effort edge publish — never blocks the claim
        push = d1_push.push_bound_token(row)
        if push.get("ok"):
            token_port.mark_pushed(token)
            edge = "Đã đẩy lên edge (D1)."
        elif push.get("skipped"):
            edge = "Edge: pending deploy."
        else:
            edge = f"Edge push lỗi (sẽ thử lại): {push.get('error', '?')}"

        msg = f"{human_code(token)} → {order_code}" + (" · QUÀ" if is_gift else "")
        return JSONResponse({"ok": True, "message": msg, "edge": edge})

    return router
