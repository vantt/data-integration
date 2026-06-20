"""screen_hug_review_html.py — pure HTML rendering for the Hug CS review queue.

No FastAPI dependency — only stdlib. Split from screen_hug_review.py so
rendering helpers can be unit-tested without the HTTP framework (same pattern
as screen_hug_mint_html.py).

Exported:
  render_review_queue(rows)     -> full page HTML for GET /hug/review
  render_action_result(msg, ok) -> inline result banner HTML (POST response)
  COMMON_CSS                    -> shared dark-card CSS string (re-exported)
"""
from __future__ import annotations

import html

# Reuse the shared dark-card CSS from the mint screen.
from adapters.inbound.web.screen_hug_mint_html import _COMMON_CSS

# Re-export so callers only need one import.
COMMON_CSS = _COMMON_CSS


# ── Page rendering ─────────────────────────────────────────────────────────────

def render_review_queue(rows: list[dict]) -> str:
    """Render the full /hug/review page.

    Args:
        rows: dicts with keys: token, buyer_customer_id, scanner_phone,
              scanner_zalo_uid, resolved_customer_id, confidence, status, ts,
              and optional enrichment keys: buyer_name, scanner_name.
    """
    body = _render_queue_body(rows)
    return f"""<!doctype html>
<html lang="vi" data-surface="HUG-REVIEW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hug · Hàng chờ xem xét</title>
<style>
{COMMON_CSS}
  body {{ align-items: flex-start; padding: 24px 16px; }}
  .card {{ width: min(860px, 98vw); }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px; }}
  th {{ text-align: left; padding: 8px 12px; font-size: 12px; text-transform: uppercase;
       letter-spacing: .6px; color: #94a3b8; border-bottom: 1px solid #334155; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #1e293b; vertical-align: top; }}
  code {{ font-family: ui-monospace, monospace; font-size: 12px; color: #38bdf8; }}
  .phone {{ font-size: 15px; font-weight: 600; color: #f1f5f9; }}
  .conf {{ font-size: 12px; color: #94a3b8; }}
  .ts {{ font-size: 12px; color: #64748b; white-space: nowrap; }}
  .name {{ font-size: 12px; color: #94a3b8; }}
  .badge-review {{ display: inline-block; padding: 2px 8px; border-radius: 6px;
                   background: #7c3aed22; color: #a78bfa; font-size: 11px;
                   font-weight: 600; letter-spacing: .4px; }}
  .empty {{ text-align: center; color: #64748b; padding: 40px 0; }}
  .action-form {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
  .action-form input[type=text] {{
    padding: 6px 10px; font-size: 13px; border-radius: 8px;
    border: 1px solid #334155; background: #0f172a; color: #f1f5f9;
    width: 200px; outline: none; }}
  .action-form input[type=text]:focus {{
    border-color: #38bdf8; box-shadow: 0 0 0 2px rgba(56,189,248,.2); }}
  .btn-confirm {{ padding: 6px 14px; font-size: 13px; font-weight: 600;
                  border: none; border-radius: 8px; background: #059669;
                  color: #fff; cursor: pointer; white-space: nowrap; }}
  .btn-confirm:hover {{ background: #047857; }}
  .btn-reject {{ padding: 6px 14px; font-size: 13px; font-weight: 600;
                 border: none; border-radius: 8px; background: #be123c;
                 color: #fff; cursor: pointer; white-space: nowrap; }}
  .btn-reject:hover {{ background: #9f1239; }}
  .hint {{ margin-top: 18px; font-size: 12px; color: #64748b; text-align: center; }}
  a.batch-link {{ color: #38bdf8; font-size: 13px; text-decoration: none; }}
  a.batch-link:hover {{ text-decoration: underline; }}
  .result-banner {{ margin-top: 16px; border-radius: 10px; padding: 12px 18px;
                    font-size: 14px; font-weight: 600; }}
  .result-banner.ok {{ background: #064e3b; color: #6ee7b7; }}
  .result-banner.err {{ background: #7f1d1d; color: #fca5a5; }}
</style>
</head>
<body>
  <main class="card">
    <h1>Hug &middot; Hàng chờ xem xét (CS)</h1>
    <p class="sub">Các opt-in bị gắn cờ — SĐT đã thuộc khách khác hoặc tín hiệu chéo (quà/đại diện).
      CS xác nhận hoặc bác bỏ từng dòng.</p>
    {body}
    <p class="hint">
      <a class="batch-link" href="/hug/batches">&larr; Sinh tem mới</a>
      &nbsp;·&nbsp;
      <a class="batch-link" href="/hug/claim">Quét gắn tem &rarr;</a>
    </p>
  </main>
</body>
</html>"""


def render_action_result(message: str, *, ok: bool) -> str:
    """Return a small result-banner HTML fragment (not a full page).

    Used as the POST /hug/review/action response so the page can be returned
    as a simple redirect or embedded status; full-page re-render follows a
    redirect to GET /hug/review.
    """
    cls = "ok" if ok else "err"
    icon = "✓" if ok else "✕"
    return f'<div class="result-banner {cls}">{icon} {html.escape(message)}</div>'


# ── Private helpers ────────────────────────────────────────────────────────────

def _render_queue_body(rows: list[dict]) -> str:
    if not rows:
        return (
            '<div class="empty">'
            '<div style="font-size:40px;margin-bottom:12px">&#10003;</div>'
            '<strong>Không có dòng nào cần xem xét.</strong>'
            '<br><span style="font-size:13px">Tất cả opt-in đã được giải quyết tự động.</span>'
            '</div>'
        )

    rows_html = "\n".join(_render_row(r) for r in rows)
    return f"""<table>
      <thead>
        <tr>
          <th>SĐT quét</th>
          <th>Token / Trạng thái</th>
          <th>Buyer (đơn)</th>
          <th>Resolved (đề xuất)</th>
          <th style="text-align:right">Thời gian</th>
          <th>Hành động</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>"""


def _render_row(r: dict) -> str:
    token = html.escape(str(r.get("token") or ""))
    phone = html.escape(str(r.get("scanner_phone") or "—"))
    zalo = html.escape(str(r.get("scanner_zalo_uid") or ""))
    buyer_id = html.escape(str(r.get("buyer_customer_id") or "—"))
    buyer_name = html.escape(str(r.get("buyer_name") or ""))
    resolved_id = html.escape(str(r.get("resolved_customer_id") or "—"))
    scanner_name = html.escape(str(r.get("scanner_name") or ""))
    conf = r.get("confidence", 1.0)
    ts_raw = str(r.get("ts") or "")
    ts = html.escape(ts_raw[:16])  # show YYYY-MM-DDTHH:MM

    phone_html = f'<span class="phone">{phone}</span>'
    if zalo:
        phone_html += f'<br><span class="name">Zalo: {zalo}</span>'
    if scanner_name:
        phone_html += f'<br><span class="name">{scanner_name}</span>'

    buyer_html = f'<code>{buyer_id}</code>'
    if buyer_name:
        buyer_html += f'<br><span class="name">{buyer_name}</span>'

    resolved_html = f'<code>{resolved_id}</code>'
    if scanner_name and resolved_id != buyer_id:
        resolved_html += f'<br><span class="name">{scanner_name}</span>'

    conf_html = f'<br><span class="conf">conf: {conf:.0%}</span>'

    # Action key: (token, scanner_phone) — URL-encoded in hidden inputs.
    # scanner_phone may be NULL; we transmit empty string and the handler
    # maps "" → NULL when matching the UNIQUE constraint.
    raw_phone = str(r.get("scanner_phone") or "")
    token_input = f'<input type="hidden" name="token" value="{token}">'
    phone_input = f'<input type="hidden" name="scanner_phone" value="{html.escape(raw_phone)}">'

    confirm_form = f"""<form method="post" action="/hug/review/action" class="action-form">
      {token_input}{phone_input}
      <input type="hidden" name="action" value="confirm">
      <input type="text" name="override_customer_id"
             placeholder="party_id (để trống = dùng đề xuất)"
             title="Nhập party_id nếu muốn gán về khách khác; để trống dùng resolved_customer_id">
      <button class="btn-confirm" type="submit">&#10003; Xác nhận</button>
    </form>"""

    reject_form = f"""<form method="post" action="/hug/review/action" class="action-form" style="margin-top:6px">
      {token_input}{phone_input}
      <input type="hidden" name="action" value="reject">
      <button class="btn-reject" type="submit">&#10005; Bác bỏ</button>
    </form>"""

    return (
        f"<tr>"
        f"<td>{phone_html}</td>"
        f"<td><code>{token}</code><br>"
        f'<span class="badge-review">needs_review</span>{conf_html}</td>'
        f"<td>{buyer_html}</td>"
        f"<td>{resolved_html}</td>"
        f'<td class="ts">{ts}</td>'
        f"<td>{confirm_form}{reject_form}</td>"
        f"</tr>"
    )
