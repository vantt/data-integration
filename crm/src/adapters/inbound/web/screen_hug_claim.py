"""Web adapter — Hug claim station (kiosk).

Local/LAN claim station for binding pre-printed Hug tokens to a Sapo order.

  GET  /hug/claim?order=SO1234   -> self-contained 2-field kiosk page
  POST /hug/claim                -> bind token (local instant) + best-effort D1 push
  GET  /hug/claim/health         -> token counts by status (ops)

Design notes:
- Self-contained HTML (no AppShell) — the station runs on a tablet/PC with a
  USB 2D scanner (acts as a keyboard). 2 inputs: order_code (pre-filled from the
  Sapo userscript via ?order=) and token (filled by the scanner). The token
  field auto-submits on Enter (scanners emit a trailing CR), giving a tap-free
  scan -> beep -> green flow.
- The D1 push is config-gated in hug.d1_push; with HUG_WORKER_URL unset the bind
  still succeeds and the push is skipped ("pending deploy").

This router owns its own hug.db connection (separate from crm.db), opened once
at wiring time — single writer, matching the CRM SQLite discipline.
"""
from __future__ import annotations

import html
import json as _json
import logging
import sqlite3

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from hug import config as hug_config
from hug import d1_push, repository
from hug.claim_fields import CLAIM_FIELDS, VALIDATORS, get_field
from hug.repository import AlreadyBoundError
from hug.tokens import human_code, is_valid_token, normalize_input

log = logging.getLogger(__name__)

# Promoted columns: fields that have a dedicated column in hug_token (+ bind_token param).
# Any CLAIM_FIELDS key NOT in this set lands in bind_attributes JSON automatically.
# When bind_token gains a new promoted parameter, add its key here too (same PR).
# See: repository.py bind_token for the parameter list this must match.
_PROMOTED_COLS: frozenset[str] = frozenset({"order_code", "is_gift"})


def make_hug_claim_router(conn: sqlite3.Connection) -> APIRouter:
    """Return the claim-station router bound to an open hug.db connection."""
    router = APIRouter()

    @router.get("/hug/claim", response_class=HTMLResponse)
    async def claim_form(order: str = "") -> HTMLResponse:
        return HTMLResponse(_render_page(order_code=order))

    @router.post("/hug/claim", response_class=HTMLResponse)
    async def claim_submit(request: Request) -> HTMLResponse:
        # Read all form fields generically so adding a new CLAIM_FIELDS entry
        # requires no change here — the loop below picks it up automatically.
        form = await request.form()
        fields: dict = {}
        for f in CLAIM_FIELDS:
            raw = form.get(f["key"], "")
            if f["type"] == "bool":
                fields[f["key"]] = raw in ("1", "true", "on", "yes")
            else:
                fields[f["key"]] = str(raw).strip()

        token = normalize_input(str(form.get("token", "")))
        order_code = fields.get("order_code", "")
        gift = fields.get("is_gift", False)

        if not order_code:
            return _render_result(False, "Thiếu mã đơn", order_code, token)
        if not is_valid_token(token):
            return _render_result(
                False, f"Tem không hợp lệ: {token or '(trống)'}", order_code, token
            )

        try:
            row = repository.bind_token(
                conn,
                token,
                order_code=order_code,
                is_gift=gift,
            )
        except KeyError:
            return _render_result(False, f"Tem chưa mint: {token}", order_code, token)
        except ValueError as exc:
            return _render_result(False, str(exc), order_code, token)
        except Exception as exc:  # noqa: BLE001
            log.error("hug claim: bind failed token=%s: %s", token, exc)
            return _render_result(False, f"Lỗi: {exc}", order_code, token)

        # Best-effort edge publish — never blocks/fails the claim.
        push = d1_push.push_bound_token(row)
        if push.get("ok"):
            repository.mark_pushed(conn, token)
            edge = "Đã đẩy lên edge (D1)."
        elif push.get("skipped"):
            edge = "Edge: pending deploy (chưa cấu hình Worker)."
        else:
            edge = f"Edge push lỗi (sẽ thử lại): {push.get('error', '?')}"

        msg = f"{human_code(token)} → {order_code}" + (" · QUÀ" if gift else "")
        return _render_result(True, msg, order_code, "", edge=edge)

    @router.get("/hug/claim/health", response_class=JSONResponse)
    async def claim_health() -> JSONResponse:
        return JSONResponse(
            {
                "counts": repository.counts_by_status(conn),
                "push_enabled": hug_config.push_enabled(),
                "hug_domain": hug_config.hug_domain(),
            }
        )

    # ── Phase 2: AJAX endpoints ──────────────────────────────────────────────

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

        row = repository.get_token(conn, norm)
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
            row = repository.bind_token(
                conn,
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
            repository.mark_pushed(conn, token)
            edge = "Đã đẩy lên edge (D1)."
        elif push.get("skipped"):
            edge = "Edge: pending deploy."
        else:
            edge = f"Edge push lỗi (sẽ thử lại): {push.get('error', '?')}"

        msg = f"{human_code(token)} → {order_code}" + (" · QUÀ" if is_gift else "")
        return JSONResponse({"ok": True, "message": msg, "edge": edge})

    return router


# ── Rendering (self-contained kiosk HTML; no template engine dependency) ──────

def _result_block(success: bool | None, message: str, edge: str = "") -> str:
    """Render the live-region result banner (empty when success is None)."""
    if success is None:
        return '<div id="result" class="result" aria-live="polite"></div>'
    cls = "ok" if success else "err"
    icon = "✓" if success else "✕"
    edge_html = f'<div class="edge">{html.escape(edge)}</div>' if edge else ""
    return (
        f'<div id="result" class="result {cls}" aria-live="polite">'
        f'<div class="big">{icon}</div>'
        f'<div class="msg">{html.escape(message)}</div>'
        f"{edge_html}"
        f'<div data-sound="{"ok" if success else "err"}"></div>'
        f"</div>"
    )


def _render_result(
    success: bool, message: str, order_code: str, token: str, edge: str = ""
) -> HTMLResponse:
    """POST response — full page re-render so the kiosk resets after each scan."""
    return HTMLResponse(
        _render_page(order_code=order_code, token=token, result=(success, message, edge))
    )


def _render_page(
    order_code: str = "",
    token: str = "",
    result: tuple[bool, str, str] | None = None,
) -> str:
    oc = html.escape(order_code)
    tk = html.escape(token)
    if result is None:
        result_html = _result_block(None, "")
        play = "null"
    else:
        success, message, edge = result
        result_html = _result_block(success, message, edge)
        play = '"ok"' if success else '"err"'

    # Build config-driven field HTML from CLAIM_FIELDS.
    # Adding a new field to CLAIM_FIELDS automatically renders it here — no edit needed.
    # Note: when a 2nd prefill field is added, refactor _render_page to accept a
    # generic prefill dict instead of named order_code param.
    fields_html = ""
    for f in CLAIM_FIELDS:
        key = html.escape(f["key"])
        label = html.escape(f["label"])
        if f["type"] == "bool":
            fields_html += (
                f'<div class="row"><div class="grp toggle">'
                f'<label style="margin:0" for="f_{key}">{label}</label>'
                f'<input type="checkbox" id="f_{key}" name="{key}" value="1">'
                f'</div></div>'
            )
        else:  # text
            required_attr = "required" if f["required"] else ""
            # Prefill: order_code uses the order_code param; extend to dict when 2nd prefill field arrives
            prefill_val = html.escape(order_code) if f["key"] == "order_code" else ""
            fields_html += (
                f'<label for="f_{key}">{label}</label>'
                f'<input type="text" id="f_{key}" name="{key}" value="{prefill_val}"'
                f' placeholder="{label}" autocomplete="off" inputmode="text" {required_attr}>'
                f'<small id="lbl_{key}" class="sublabel"></small>'
            )

    # Serialise CLAIM_FIELDS for the JS block (validate key stripped by claim_fields_json).
    # _json.dumps always escapes < > & so embedding in <script> is XSS-safe.
    claim_fields_json = _json.dumps(
        [{k: v for k, v in f.items() if k != "validate"} for f in CLAIM_FIELDS]
    )

    return f"""<!doctype html>
<html lang="vi" data-surface="HUG-CLAIM">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hug · Claim station</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
         margin: 0; background: #0f172a; color: #e2e8f0;
         display: flex; min-height: 100vh; align-items: center; justify-content: center; }}
  .card {{ width: min(560px, 92vw); background: #1e293b; border-radius: 16px;
          padding: 28px 28px 32px; box-shadow: 0 12px 40px rgba(0,0,0,.4); }}
  h1 {{ font-size: 20px; margin: 0 0 4px; letter-spacing: .5px; }}
  .sub {{ color: #94a3b8; font-size: 13px; margin: 0 0 20px; }}
  label {{ display: block; font-size: 12px; text-transform: uppercase;
          letter-spacing: .6px; color: #94a3b8; margin: 14px 0 6px; }}
  input[type=text] {{ width: 100%; padding: 14px 16px; font-size: 20px;
          border-radius: 10px; border: 1px solid #334155; background: #0f172a;
          color: #f1f5f9; outline: none; }}
  input#f_token {{ font-size: 26px; letter-spacing: 3px; text-align: center;
          font-variant-numeric: tabular-nums; }}
  input:focus {{ border-color: #38bdf8; box-shadow: 0 0 0 3px rgba(56,189,248,.25); }}
  .row {{ display: flex; gap: 16px; align-items: center; margin-top: 16px; flex-wrap: wrap; }}
  .row .grp {{ flex: 1; min-width: 160px; }}
  .toggle {{ display: flex; align-items: center; gap: 8px; font-size: 15px; }}
  .toggle input {{ width: 22px; height: 22px; }}
  .sublabel {{ display: block; font-size: 12px; margin-top: 3px; min-height: 16px; }}
  .sublabel-ok  {{ color: #4ade80; }}
  .sublabel-err {{ color: #f87171; }}
  .sublabel-warn {{ color: #fbbf24; }}
  .result {{ margin-top: 22px; text-align: center; border-radius: 12px; padding: 0; }}
  .result.ok {{ background: #064e3b; padding: 20px; }}
  .result.err {{ background: #7f1d1d; padding: 20px; }}
  .result .big {{ font-size: 48px; line-height: 1; }}
  .result .msg {{ font-size: 18px; margin-top: 8px; font-weight: 600; }}
  .result .edge {{ font-size: 12px; color: #cbd5e1; margin-top: 8px; }}
  .hint {{ margin-top: 18px; font-size: 12px; color: #64748b; text-align: center; }}
  button {{ width: 100%; margin-top: 18px; padding: 16px; font-size: 18px; font-weight: 700;
          border: none; border-radius: 10px; background: #38bdf8; color: #0f172a; cursor: pointer; }}
  button:hover {{ background: #0ea5e9; }}
</style>
</head>
<body>
  <main class="card">
    <h1>Hug · Claim station</h1>
    <p class="sub">Quét tem → tự bind vào đơn → bíp + xanh → dán.</p>
    <form id="claim" method="post" action="/hug/claim" autocomplete="off">
      {fields_html}
      <label for="f_token">Tem (quét mã 2D)</label>
      <input type="text" id="f_token" name="token" value="{tk}"
             placeholder="quét tem…" autofocus autocapitalize="characters" spellcheck="false">
      <small id="lbl_token" class="sublabel"></small>
      <button type="submit">Gắn tem vào đơn</button>
    </form>
    {result_html}
    <p class="hint">Tem = 12 ký tự. Máy quét tự xuống dòng → tự gửi.</p>
  </main>
<script>
  // ── Config injected from Python CLAIM_FIELDS (validate key stripped) ──────
  const FIELDS = {claim_fields_json};
  // One UUID per page-load; persists across re-scans within the same session.
  // Reset only on full page reload or fresh navigation.
  const SESSION_ID = crypto.randomUUID();

  // ── Audio cues via WebAudio — no asset files needed ───────────────────────
  function beep(ok) {{
    try {{
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator(), gain = ctx.createGain();
      osc.connect(gain); gain.connect(ctx.destination);
      osc.frequency.value = ok ? 880 : 220;
      gain.gain.setValueAtTime(0.15, ctx.currentTime);
      osc.start();
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + (ok ? 0.18 : 0.45));
      osc.stop(ctx.currentTime + (ok ? 0.2 : 0.5));
    }} catch (e) {{}}
  }}

  // Play sound on full-page re-render (no-JS fallback POST path result).
  const lastResult = {play};
  if (lastResult) beep(lastResult === "ok");

  // ── DOM helpers ───────────────────────────────────────────────────────────
  function getFieldEl(key)  {{ return document.getElementById('f_' + key); }}
  function getLabelEl(key)  {{ return document.getElementById('lbl_' + key); }}

  function showSubLabel(key, text, state) {{
    // state: 'ok' | 'err' | 'warn'
    const el = getLabelEl(key);
    if (!el) return;
    el.textContent = text;
    el.className = 'sublabel sublabel-' + state;
  }}

  function clearSubLabel(key) {{
    const el = getLabelEl(key);
    if (el) {{ el.textContent = ''; el.className = 'sublabel'; }}
  }}

  // ── Token normalisation — mirrors server-side normalize_input() logic ─────
  // Printed human codes (HUG-XXXX-XXXX-XXXX) and scanned full QR URLs are
  // both reduced to the raw 12-char token so they auto-check correctly.
  const RE = /^[2-9A-HJKMNP-Z]{{12}}$/;
  function normalizeToken(v) {{
    v = v.trim().toUpperCase();
    // Full QR URL emitted by scanner → extract last path segment.
    if (v.includes("://")) {{
      v = v.split("?")[0].split("#")[0].replace(/\\/+$/, "").split("/").pop();
    }}
    // Remove separator characters: dashes, underscores, dots, whitespace.
    // Matches the Worker normalizeToken separator set so all three copies accept the same inputs.
    v = v.replace(/[-_.\\s]/g, "");
    // Strip a "HUG" prefix only when the result is exactly 15 chars (= "HUG" + 12-char token).
    // A genuine 12-char token starting with HUG stays intact — length 12 never triggers this.
    if (v.length === 15 && v.startsWith("HUG")) v = v.slice(3);
    return v;
  }}

  // ── Per-field live validation (text fields with validate set) ─────────────
  async function checkField(key, value) {{
    try {{
      const r = await fetch('/hug/claim/check-field?key=' + encodeURIComponent(key)
                            + '&value=' + encodeURIComponent(value)
                            + '&session=' + encodeURIComponent(SESSION_ID));
      return await r.json();
    }} catch (_) {{
      return {{ ok: null, message: 'Lỗi kết nối' }};
    }}
  }}

  // Wire debounced check-field to every text FIELD that has a validate key.
  // This loop makes adding a new validated text field require zero frontend edits.
  const fieldTimers = {{}};
  for (const f of FIELDS) {{
    if (f.type !== 'text') continue;
    const el = getFieldEl(f.key);
    if (!el) continue;
    el.addEventListener('input', () => {{
      clearTimeout(fieldTimers[f.key]);
      fieldTimers[f.key] = setTimeout(async () => {{
        const v = el.value.trim();
        if (!v) {{ clearSubLabel(f.key); return; }}
        const res = await checkField(f.key, v);
        if (res.ok === true)       showSubLabel(f.key, res.message, 'ok');
        else if (res.ok === false) {{ showSubLabel(f.key, res.message, 'err'); beep(false); }}
        else                       showSubLabel(f.key, res.message || 'Không thể kiểm tra', 'warn');
      }}, 600);
    }});
    // Pre-fill from query param: if field already has a value on page load,
    // trigger the check immediately so the sub-label shows state without user interaction.
    if (el.value.trim()) {{
      setTimeout(() => el.dispatchEvent(new Event('input')), 0);
    }}
  }}

  // ── Token field: normalise → check-token → doBind ────────────────────────
  const tokenEl = getFieldEl('token');

  async function checkToken(value) {{
    let res;
    try {{
      const r = await fetch('/hug/claim/check-token?token=' + encodeURIComponent(value)
                            + '&session=' + encodeURIComponent(SESSION_ID));
      res = await r.json();
    }} catch (_) {{
      res = {{ state: 'error', message: 'Lỗi kết nối' }};
    }}

    if (res.state === 'ready' || res.state === 'rebind_ok') {{
      const isAmber = res.state === 'rebind_ok';
      showSubLabel('token', res.message, isAmber ? 'warn' : 'ok');
      beep(true);
      await doBind(value);
    }} else {{
      showSubLabel('token', res.message, 'err');
      beep(false);
    }}
  }}

  async function doBind(token) {{
    // Collect current values from all CLAIM_FIELDS inputs.
    const fields = {{}};
    for (const f of FIELDS) {{
      const el = getFieldEl(f.key);
      if (!el) continue;
      fields[f.key] = f.type === 'bool' ? el.checked : el.value.trim();
    }}

    // Guard: order_code must be present before binding — show amber hint and wait.
    if (!fields['order_code']) {{
      showSubLabel('token', 'Nhập mã đơn trước', 'warn');
      return;
    }}

    let res;
    try {{
      const r = await fetch('/hug/claim/bind', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ session_id: SESSION_ID, token, fields }}),
      }});
      res = await r.json();
    }} catch (_) {{
      res = {{ ok: false, message: 'Lỗi kết nối khi gắn tem' }};
    }}

    const resultEl = document.getElementById('result');
    if (res.ok) {{
      if (resultEl) {{
        resultEl.className = 'result ok';
        resultEl.innerHTML = '<div class="big">✓</div>'
          + '<div class="msg"><strong>' + res.message + '</strong></div>'
          + (res.edge ? '<div class="edge">' + res.edge + '</div>' : '');
      }}
      beep(true);
      // Clear token field + sub-label; keep order field so next sticker binds to same order.
      if (tokenEl) {{ tokenEl.value = ''; tokenEl.focus(); }}
      clearSubLabel('token');
    }} else {{
      if (resultEl) {{
        resultEl.className = 'result err';
        resultEl.innerHTML = '<div class="big">✕</div>'
          + '<div class="msg"><strong>' + res.message + '</strong></div>';
      }}
      beep(false);
    }}
  }}

  // Token field input: normalise → check against RE → trigger async check+bind.
  // Last scan always wins (no debounce; 12-char RE is the gate).
  if (tokenEl) {{
    tokenEl.addEventListener('input', async () => {{
      const v = normalizeToken(tokenEl.value);
      tokenEl.value = v;
      clearSubLabel('token');
      if (RE.test(v)) {{
        await checkToken(v);
      }}
    }});
  }}

  // ── Initial focus ─────────────────────────────────────────────────────────
  const orderEl = getFieldEl('order_code');
  // If order_code already pre-filled (e.g. from ?order=), focus token for scanning.
  if (orderEl && orderEl.value.trim()) {{
    if (tokenEl) {{ tokenEl.focus(); tokenEl.select(); }}
  }} else if (orderEl) {{
    orderEl.focus();
  }}

  // Post-form-POST clear: after a full-page re-render on the no-JS fallback path,
  // clear the token field and refocus so the kiosk is ready for the next scan.
  if (lastResult === "ok") {{
    if (tokenEl) {{ tokenEl.value = ""; tokenEl.focus(); }}
  }}
</script>
</body>
</html>"""
