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
import logging
import sqlite3

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, JSONResponse

from hug import config as hug_config
from hug import d1_push, repository
from hug.tokens import human_code, is_valid_token, normalize_input

log = logging.getLogger(__name__)


def make_hug_claim_router(conn: sqlite3.Connection) -> APIRouter:
    """Return the claim-station router bound to an open hug.db connection."""
    router = APIRouter()

    @router.get("/hug/claim", response_class=HTMLResponse)
    async def claim_form(order: str = "") -> HTMLResponse:
        return HTMLResponse(_render_page(order_code=order))

    @router.post("/hug/claim", response_class=HTMLResponse)
    async def claim_submit(
        token: str = Form(default=""),
        order_code: str = Form(default=""),
        is_gift: str = Form(default=""),
    ) -> HTMLResponse:
        token = normalize_input(token)
        order_code = order_code.strip()
        gift = is_gift in ("1", "true", "on", "yes")

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
  input#token {{ font-size: 26px; letter-spacing: 3px; text-align: center;
          font-variant-numeric: tabular-nums; }}
  input:focus {{ border-color: #38bdf8; box-shadow: 0 0 0 3px rgba(56,189,248,.25); }}
  .row {{ display: flex; gap: 16px; align-items: center; margin-top: 16px; flex-wrap: wrap; }}
  .row .grp {{ flex: 1; min-width: 160px; }}
  select {{ width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #334155;
          background: #0f172a; color: #f1f5f9; font-size: 15px; }}
  .toggle {{ display: flex; align-items: center; gap: 8px; font-size: 15px; }}
  .toggle input {{ width: 22px; height: 22px; }}
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
      <label for="order_code">Mã đơn (Sapo)</label>
      <input type="text" id="order_code" name="order_code" value="{oc}"
             placeholder="SO1234" inputmode="text">
      <label for="token">Tem (quét mã 2D)</label>
      <input type="text" id="token" name="token" value="{tk}"
             placeholder="quét tem…" autofocus autocapitalize="characters" spellcheck="false">
      <div class="row">
        <div class="grp toggle">
          <label style="margin:0">Đơn là quà tặng?</label>
          <input type="checkbox" id="is_gift" name="is_gift" value="1">
          <span>Tick nếu người NHẬN hàng khác người ĐẶT mua</span>
        </div>
      </div>
      <button type="submit">Gắn tem vào đơn</button>
    </form>
    {result_html}
    <p class="hint">Tem = 12 ký tự. Máy quét tự xuống dòng → tự gửi.</p>
  </main>
<script>
  // Audio cues via WebAudio — no asset files needed.
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
  const lastResult = {play};
  if (lastResult) beep(lastResult === "ok");

  const tokenEl = document.getElementById("token");
  const orderEl = document.getElementById("order_code");
  // Focus the right field: token if order already filled, else the order field.
  if (orderEl.value.trim()) {{ tokenEl.focus(); tokenEl.select(); }}
  else {{ orderEl.focus(); }}

  // Auto-submit when a full token has been scanned/typed (scanner sends Enter,
  // but also auto-fire once 12 valid chars are present for robustness).
  // Normalization mirrors the server-side normalize_input() logic so that
  // printed human codes (HUG-XXXX-XXXX-XXXX) and scanned full URLs auto-submit.
  const RE = /^[2-9A-HJKMNP-Z]{{12}}$/;
  function normalizeToken(v) {{
    v = v.trim().toUpperCase();
    // If a scanner emits the full QR URL, extract the token from the last path segment.
    if (v.includes("://")) {{
      v = v.split("?")[0].split("#")[0].replace(/\\/+$/, "").split("/").pop();
    }}
    // Remove dashes and spaces (handles HUG-XXXX-XXXX-XXXX and stray whitespace).
    v = v.replace(/-/g, "").replace(/\\s+/g, "");
    // Strip a "HUG" prefix only when the result is exactly 15 chars (= "HUG" + 12-char token).
    // A genuine 12-char token starting with HUG stays intact — length 12 never triggers this.
    if (v.length === 15 && v.startsWith("HUG")) v = v.slice(3);
    return v;
  }}
  tokenEl.addEventListener("input", () => {{
    tokenEl.value = normalizeToken(tokenEl.value);
    if (RE.test(tokenEl.value)) document.getElementById("claim").submit();
  }});
  // After a successful claim, clear the token field for the next scan.
  if (lastResult === "ok") {{ tokenEl.value = ""; tokenEl.focus(); }}
</script>
</body>
</html>"""
