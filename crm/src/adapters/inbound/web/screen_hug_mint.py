"""Web adapter — Hug mint station (warehouse admin).

Simple warehouse UI to pre-generate a batch of Hug tokens and render the
print-ready QR label sheet directly in the browser.

  GET  /hug/mint          -> batch configuration form (count, batch id, op_type)
  POST /hug/mint          -> mint batch + return QR labels page (ready to Ctrl-P)
  GET  /hug/batches       -> recent batch list with token counts by status

Design notes:
- Self-contained HTML (no AppShell / template engine), dark-card kiosk styling
  that mirrors screen_hug_claim.py.
- QR labels HTML is produced by hug_qr_print.render_labels_html() — the same
  function the CLI calls — so token generation and QR rendering are never
  duplicated (DRY).
- Minting delegates to hug.repository.mint_batch() — same function the CLI uses.
- The labels page embeds an "← Sinh batch khác" back-link and a print button so
  warehouse staff never need the CLI.
"""
from __future__ import annotations

import html
import logging
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, JSONResponse

from hug import config as hug_config
from hug import repository
from hug.tokens import human_code

# Shared QR renderer — same function used by the hug_qr_print.py CLI.
from hug_qr_print import render_labels_html

log = logging.getLogger(__name__)

# Reasonable safety cap: 1–2000 tokens per web batch.
_MIN_COUNT = 1
_MAX_COUNT = 2000

_OP_LABELS = {
    "package_insert": "Trong kiện hàng (mặc định)",
    "loyalty_card":   "Thẻ thành viên",
    "winback_flyer":  "Tờ rơi mời mua lại",
    "receipt":        "Hóa đơn",
    "acquire":        "Phát lẻ / chưa gắn khách",
}


def _default_batch_id() -> str:
    return "LOT-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")


def make_hug_mint_router(conn: sqlite3.Connection) -> APIRouter:
    """Return the mint-station router bound to an open hug.db connection."""
    router = APIRouter()

    @router.get("/hug/mint", response_class=HTMLResponse)
    async def mint_form() -> HTMLResponse:
        return HTMLResponse(_render_form())

    @router.post("/hug/mint", response_class=HTMLResponse)
    async def mint_submit(
        count: str = Form(default=""),
        batch_id: str = Form(default=""),
        op_type: str = Form(default="package_insert"),
    ) -> HTMLResponse:
        # Validate count
        count_str = count.strip()
        try:
            n = int(count_str)
        except ValueError:
            return HTMLResponse(_render_form(error=f"Số lượng không hợp lệ: '{html.escape(count_str)}'"))
        if not (_MIN_COUNT <= n <= _MAX_COUNT):
            return HTMLResponse(
                _render_form(error=f"Số lượng phải từ {_MIN_COUNT} đến {_MAX_COUNT}.")
            )

        # Normalise batch id
        bid = batch_id.strip() or _default_batch_id()
        op = op_type.strip() or "package_insert"

        try:
            tokens = repository.mint_batch(conn, n, batch_id=bid, op_type=op)
        except Exception as exc:  # noqa: BLE001
            log.error("hug mint: failed batch=%s count=%d: %s", bid, n, exc)
            return HTMLResponse(_render_form(error=f"Lỗi khi sinh token: {html.escape(str(exc))}"))

        log.info("hug mint: batch=%s count=%d op_type=%s", bid, n, op)

        # Return the print-ready QR labels page (shared renderer, DRY).
        labels_html = render_labels_html(tokens, bid)
        return HTMLResponse(labels_html)

    @router.get("/hug/batches", response_class=HTMLResponse)
    async def batch_list() -> HTMLResponse:
        batches = repository.list_recent_batches(conn, limit=50)
        return HTMLResponse(_render_batches(list(batches)))

    return router


# ── Rendering helpers (self-contained HTML; no template engine) ──────────────

_COMMON_CSS = """
  * { box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
         margin: 0; background: #0f172a; color: #e2e8f0;
         display: flex; min-height: 100vh; align-items: center; justify-content: center; }
  .card { width: min(560px, 92vw); background: #1e293b; border-radius: 16px;
          padding: 28px 28px 32px; box-shadow: 0 12px 40px rgba(0,0,0,.4); }
  h1 { font-size: 20px; margin: 0 0 4px; letter-spacing: .5px; }
  .sub { color: #94a3b8; font-size: 13px; margin: 0 0 20px; }
  label { display: block; font-size: 12px; text-transform: uppercase;
          letter-spacing: .6px; color: #94a3b8; margin: 14px 0 6px; }
  input[type=text], input[type=number] {
    width: 100%; padding: 14px 16px; font-size: 18px;
    border-radius: 10px; border: 1px solid #334155; background: #0f172a;
    color: #f1f5f9; outline: none; }
  input:focus { border-color: #38bdf8; box-shadow: 0 0 0 3px rgba(56,189,248,.25); }
  select { width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #334155;
          background: #0f172a; color: #f1f5f9; font-size: 15px; }
  select:focus { outline: none; border-color: #38bdf8; }
  button { width: 100%; margin-top: 18px; padding: 16px; font-size: 18px; font-weight: 700;
          border: none; border-radius: 10px; background: #38bdf8; color: #0f172a; cursor: pointer; }
  button:hover { background: #0ea5e9; }
  .err-banner { margin-top: 16px; background: #7f1d1d; border-radius: 10px;
                padding: 14px 18px; font-size: 15px; color: #fca5a5; }
  .hint { margin-top: 18px; font-size: 12px; color: #64748b; text-align: center; }
  a.batch-link { color: #38bdf8; font-size: 13px; text-decoration: none; }
  a.batch-link:hover { text-decoration: underline; }
"""


def _op_options(selected: str = "package_insert") -> str:
    opts = []
    for val, label in _OP_LABELS.items():
        sel = ' selected' if val == selected else ''
        opts.append(f'<option value="{val}"{sel}>{html.escape(label)}</option>')
    return "\n".join(opts)


def _render_form(error: str = "") -> str:
    error_html = (
        f'<div class="err-banner">&#9888; {error}</div>' if error else ""
    )
    return f"""<!doctype html>
<html lang="vi" data-surface="HUG-MINT">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hug · Sinh tem mới</title>
<style>{_COMMON_CSS}</style>
</head>
<body>
  <main class="card">
    <h1>Hug · Sinh tem mới</h1>
    <p class="sub">Sinh batch token &rarr; in trang QR &rarr; dán tem.</p>
    <form method="post" action="/hug/mint" autocomplete="off">
      <label for="count">Số lượng (1–{_MAX_COUNT})</label>
      <input type="number" id="count" name="count" min="1" max="{_MAX_COUNT}"
             value="50" required autofocus>
      <label for="batch_id">Batch ID (để trống &rarr; tự tạo)</label>
      <input type="text" id="batch_id" name="batch_id"
             placeholder="LOT-YYYYMMDD-HHMM">
      <label for="op_type">Tem dán ở đâu?</label>
      <select id="op_type" name="op_type">
        {_op_options()}
      </select>
      <button type="submit">&#128229; Sinh &amp; xem tem</button>
    </form>
    {error_html}
    <p class="hint">
      <a class="batch-link" href="/hug/batches">Xem batch đã sinh &rarr;</a>
    </p>
  </main>
</body>
</html>"""


def _render_batches(batches: list) -> str:
    if not batches:
        rows_html = '<tr><td colspan="3" style="text-align:center;color:#64748b">Chưa có batch nào.</td></tr>'
    else:
        rows = []
        for b in batches:
            bid = html.escape(str(b["batch_id"]))
            n = b["n"]
            created = html.escape(str(b["created_at"])[:16])
            rows.append(
                f'<tr>'
                f'<td><code>{bid}</code></td>'
                f'<td style="text-align:center">{n}</td>'
                f'<td style="color:#94a3b8;font-size:13px">{created}</td>'
                f'</tr>'
            )
        rows_html = "\n".join(rows)

    return f"""<!doctype html>
<html lang="vi" data-surface="HUG-BATCHES">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hug · Batches</title>
<style>
  {_COMMON_CSS}
  body {{ align-items: flex-start; padding: 32px 16px; }}
  .card {{ width: min(720px, 96vw); }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px; }}
  th {{ text-align: left; padding: 8px 12px; font-size: 12px; text-transform: uppercase;
       letter-spacing: .6px; color: #94a3b8; border-bottom: 1px solid #334155; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #1e293b; }}
  code {{ font-family: ui-monospace, monospace; font-size: 13px; color: #38bdf8; }}
</style>
</head>
<body>
  <main class="card">
    <h1>Hug · Danh sách batch</h1>
    <p class="sub">50 batch gần nhất.</p>
    <table>
      <thead>
        <tr>
          <th>Batch ID</th>
          <th style="text-align:center">Số tem</th>
          <th>Thời gian tạo (UTC)</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
    <p class="hint">
      <a class="batch-link" href="/hug/mint">&larr; Sinh batch mới</a>
    </p>
  </main>
</body>
</html>"""
