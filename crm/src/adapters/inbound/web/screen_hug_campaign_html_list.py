"""screen_hug_campaign_html_list.py — campaign list HTML renderer.

No FastAPI dependency. Renders the /hug/campaigns list page.

Shared constants (_STATUS_COLOR, _STATUS_LABEL, _DEST_LABEL, _e, _targeting_summary)
are defined here and re-used by screen_hug_campaign_html_form.py via import.
"""
from __future__ import annotations

import html
import json
from typing import Any

from hug.targeting_catalog import TARGETING_CATALOG
from adapters.inbound.web.screen_hug_mint_html import _COMMON_CSS

# ── Shared constants (imported by _html_form.py too) ─────────────────────────

_STATUS_COLOR = {
    "active":   "#16a34a",
    "paused":   "#d97706",
    "archived": "#64748b",
}

_STATUS_LABEL = {
    "active":   "Đang chạy",
    "paused":   "Tạm dừng",
    "archived": "Đã lưu trữ",
}

_DEST_LABEL = {
    "zalo_oa":  "Zalo OA",
    "cf_pages": "CF Pages",
    "url":      "URL",
}

_LIST_CSS = """
  body { align-items: flex-start; padding: 32px 16px; }
  .card { width: min(900px, 98vw); }
  table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px; }
  th { text-align: left; padding: 8px 12px; font-size: 12px; text-transform: uppercase;
       letter-spacing: .6px; color: #94a3b8; border-bottom: 1px solid #334155; }
  td { padding: 10px 12px; border-bottom: 1px solid #1a2535; vertical-align: top; }
  .badge { display: inline-block; padding: 2px 10px; border-radius: 99px;
           font-size: 12px; font-weight: 600; }
  .act-btn { display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 12px;
             border: 1px solid #334155; background: #1e293b; color: #e2e8f0;
             cursor: pointer; text-decoration: none; }
  .act-btn:hover { background: #334155; }
  .act-btn.danger { border-color: #7f1d1d; color: #fca5a5; }
  .act-btn.danger:hover { background: #7f1d1d; }
  .flash { margin-bottom: 16px; padding: 12px 18px; border-radius: 10px; font-size: 14px; }
  .flash.ok   { background: #14532d; color: #86efac; }
  .flash.warn { background: #78350f; color: #fde68a; }
  .new-btn { display: inline-block; padding: 10px 22px; background: #38bdf8;
             color: #0f172a; font-weight: 700; border-radius: 10px;
             text-decoration: none; font-size: 14px; }
  .new-btn:hover { background: #0ea5e9; }
"""


def _e(s: Any) -> str:
    """HTML-escape a value to a string."""
    return html.escape(str(s) if s is not None else "")


def _targeting_summary(targeting_json: str, max_len: int = 80) -> str:
    """Return a short human-readable summary of a targeting JSON string."""
    try:
        t: dict = json.loads(targeting_json or "{}")
    except (json.JSONDecodeError, TypeError):
        return "(JSON không hợp lệ)"
    if not t:
        return "Tất cả khách"
    parts = []
    for k, v in t.items():
        spec = TARGETING_CATALOG.get(k, {})
        label = spec.get("description", k)
        if isinstance(v, list):
            parts.append(f"{label}: {', '.join(str(x) for x in v)}")
        elif isinstance(v, dict):
            ops = ", ".join(f"{op}={val}" for op, val in v.items())
            parts.append(f"{label}: {ops}")
        else:
            parts.append(f"{label}: {v}")
    summary = " | ".join(parts)
    return summary[:max_len] + "…" if len(summary) > max_len else summary


def _campaign_row_html(c: dict) -> str:
    """Render one <tr> for a campaign in the list table."""
    cid = _e(c["campaign_id"])
    name = _e(c["name"])
    priority = _e(c.get("priority", 100))
    status = c.get("status", "active")
    badge_color = _STATUS_COLOR.get(status, "#64748b")
    badge_label = _STATUS_LABEL.get(status, status)
    dest = _e(_DEST_LABEL.get(c.get("destination_type", ""), c.get("destination_type", "")))
    summary = _e(_targeting_summary(c.get("targeting", "{}")))

    if status == "active":
        toggle_action, toggle_label = "pause", "Dừng"
    elif status == "paused":
        toggle_action, toggle_label = "activate", "Kích hoạt"
    else:
        toggle_action, toggle_label = "", ""

    toggle_btn = ""
    if toggle_action:
        toggle_btn = (
            f'<form method="post" action="/hug/campaign/{cid}/status" style="display:inline">'
            f'<input type="hidden" name="action" value="{toggle_action}">'
            f'<button type="submit" class="act-btn">{toggle_label}</button>'
            f'</form> '
        )

    archive_btn = ""
    if status != "archived":
        archive_btn = (
            f'<form method="post" action="/hug/campaign/{cid}/status" style="display:inline">'
            f'<input type="hidden" name="action" value="archive">'
            f'<button type="submit" class="act-btn danger">Lưu trữ</button>'
            f'</form>'
        )

    return (
        f'<tr>'
        f'<td style="font-weight:600">{name}<br>'
        f'<code style="font-size:11px;color:#64748b">{cid}</code></td>'
        f'<td style="text-align:center">{priority}</td>'
        f'<td><span class="badge" style="background:{badge_color}20;color:{badge_color}">'
        f'{badge_label}</span></td>'
        f'<td style="color:#94a3b8;font-size:12px">{dest}</td>'
        f'<td style="color:#94a3b8;font-size:12px">{summary}</td>'
        f'<td><a href="/hug/campaign/{cid}/edit" class="act-btn">Sửa</a> '
        f'{toggle_btn}{archive_btn}</td>'
        f'</tr>'
    )


def render_campaign_list(campaigns: list[dict], flash: str = "", flash_ok: bool = True) -> str:
    """Render the /hug/campaigns list page."""
    flash_html = ""
    if flash:
        cls = "ok" if flash_ok else "warn"
        flash_html = f'<div class="flash {cls}">{_e(flash)}</div>'

    if not campaigns:
        rows_html = (
            '<tr><td colspan="6" style="text-align:center;color:#64748b;padding:24px">'
            'Chưa có campaign nào. '
            '<a href="/hug/campaign/new" style="color:#38bdf8">Tạo campaign đầu tiên →</a>'
            '</td></tr>'
        )
    else:
        rows_html = "\n".join(_campaign_row_html(c) for c in campaigns)

    return f"""<!doctype html>
<html lang="vi" data-surface="HUG-CAMPAIGNS">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hug · Campaign</title><style>{_COMMON_CSS}{_LIST_CSS}</style></head>
<body>
  <main class="card">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
      <h1>Hug · Campaign</h1>
      <a href="/hug/campaign/new" class="new-btn">+ Tạo mới</a>
    </div>
    <p class="sub">Quản lý campaign Hug. Priority thấp hơn = ưu tiên cao hơn.</p>
    {flash_html}
    <table>
      <thead><tr>
        <th>Tên / ID</th><th style="text-align:center">Priority</th>
        <th>Trạng thái</th><th>Đích</th><th>Targeting</th><th>Hành động</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    <p class="hint" style="margin-top:20px">
      <a class="batch-link" href="/hug/mint">&larr; Hug mint</a>
    </p>
  </main>
</body></html>"""
