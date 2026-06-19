"""screen_hug_mint_html.py — pure HTML rendering helpers for the Hug mint station.

No FastAPI dependency here — only stdlib + hug domain modules.
This split keeps the rendering logic testable without a running HTTP framework,
and keeps screen_hug_mint.py (the router) under the 200-line threshold.

Exported:
  _render_form(error)           -> mint form page
  _render_batches(batches)      -> recent-batch list page (batch IDs are clickable)
  _render_batch_not_found(bid)  -> friendly 404-style page for unknown batch IDs
  _COMMON_CSS                   -> shared dark-card CSS string
  _MAX_COUNT                    -> upper bound on tokens-per-batch (used in form)
"""
from __future__ import annotations

import html
from urllib.parse import quote as _url_quote

from hug.op_types import OP_LABELS

# Reasonable safety cap: 1–2000 tokens per web batch (also validated in router).
_MIN_COUNT = 1
_MAX_COUNT = 2000

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
    for val, label in OP_LABELS.items():
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


def _render_batch_not_found(batch_id: str) -> str:
    """Friendly error page when a batch_id has no tokens in hug.db."""
    escaped = html.escape(str(batch_id))
    return f"""<!doctype html>
<html lang="vi" data-surface="HUG-BATCH-404">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hug · Không tìm thấy batch</title>
<style>{_COMMON_CSS}</style>
</head>
<body>
  <main class="card">
    <h1>Không tìm thấy batch</h1>
    <p class="sub">Batch <code>{escaped}</code> không có trong hệ thống.</p>
    <p style="margin-top:24px">
      <a class="batch-link" href="/hug/batches">&larr; Quay lại danh sách batch</a>
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
            raw_bid = str(b["batch_id"])
            bid_escaped = html.escape(raw_bid)
            # URL-encode only the query-parameter value so batch IDs with spaces
            # or special characters are transmitted safely to the reprint route.
            bid_href = f"/hug/batch/labels?batch_id={_url_quote(raw_bid, safe='')}"
            n = b["n"]
            created = html.escape(str(b["created_at"])[:16])
            rows.append(
                f'<tr>'
                f'<td><a href="{bid_href}"><code>{bid_escaped}</code></a></td>'
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
  td a {{ color: inherit; text-decoration: none; }}
  td a:hover code {{ text-decoration: underline; }}
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
