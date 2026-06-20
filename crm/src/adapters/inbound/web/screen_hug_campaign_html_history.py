"""screen_hug_campaign_html_history.py — history list HTML for campaign admin.

No FastAPI dependency. Renders the /hug/campaign/{id}/history page showing
up to 20 saved snapshots with a "Khôi phục" POST button on each row.
"""
from __future__ import annotations

import json
from typing import Any

from adapters.inbound.web.screen_hug_mint_html import _COMMON_CSS
from adapters.inbound.web.screen_hug_campaign_html_list import _e, _targeting_summary

_HISTORY_CSS = """
  body { align-items: flex-start; padding: 32px 16px; }
  .card { width: min(820px, 98vw); }
  table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px; }
  th { text-align: left; padding: 8px 12px; font-size: 12px; text-transform: uppercase;
       letter-spacing: .6px; color: #94a3b8; border-bottom: 1px solid #334155; }
  td { padding: 10px 12px; border-bottom: 1px solid #1a2535; vertical-align: top; }
  .restore-btn { display: inline-block; padding: 5px 14px; border-radius: 6px;
    font-size: 13px; border: 1px solid #334155; background: #1e293b; color: #e2e8f0;
    cursor: pointer; white-space: nowrap; }
  .restore-btn:hover { background: #334155; }
  .ts { font-family: ui-monospace, monospace; font-size: 12px; color: #94a3b8; }
  .version-name { color: #f1f5f9; font-size: 13px; }
  .empty { text-align: center; color: #64748b; padding: 24px; }
"""


def _format_saved_at(saved_at: Any) -> str:
    """Format a UTC ISO timestamp for display in ICT (UTC+7)."""
    if not saved_at:
        return "—"
    s = str(saved_at)
    # Convert ISO UTC string to a slightly more readable form.
    # Full datetime conversion would require pytz/zoneinfo — keep it simple:
    # strip the trailing Z/+00:00 and show the raw UTC value with a note.
    s = s.replace("T", " ").rstrip("Z").rstrip("+00:00")
    # Truncate microseconds to seconds for readability.
    if "." in s:
        s = s[: s.index(".")]
    return s + " UTC"


def _snapshot_name(snapshot_json: str) -> str:
    """Extract a short display name from a snapshot JSON string."""
    try:
        snap: dict = json.loads(snapshot_json)
        return snap.get("name") or snap.get("campaign_id") or "—"
    except (json.JSONDecodeError, TypeError):
        return "(JSON không đọc được)"


def _snapshot_targeting_summary(snapshot_json: str) -> str:
    """Extract targeting summary from a snapshot JSON string."""
    try:
        snap: dict = json.loads(snapshot_json)
        return _targeting_summary(snap.get("targeting") or "{}")
    except (json.JSONDecodeError, TypeError):
        return "—"


def _snapshot_status(snapshot_json: str) -> str:
    try:
        snap: dict = json.loads(snapshot_json)
        return snap.get("status") or "—"
    except (json.JSONDecodeError, TypeError):
        return "—"


def _render_snapshot_row(campaign_id: str, snap_row: Any) -> str:
    """Render one <tr> for a history snapshot."""
    snap_id = _e(snap_row["id"])
    cid_e = _e(campaign_id)
    saved_at = _format_saved_at(snap_row["saved_at"])
    name = _e(_snapshot_name(snap_row["snapshot"]))
    summary = _e(_snapshot_targeting_summary(snap_row["snapshot"]))
    status = _e(_snapshot_status(snap_row["snapshot"]))

    return (
        f"<tr>"
        f'<td class="ts">{_e(saved_at)}</td>'
        f'<td class="version-name">{name}</td>'
        f'<td style="font-size:12px;color:#94a3b8">{status}</td>'
        f'<td style="font-size:12px;color:#94a3b8">{summary}</td>'
        f"<td>"
        f'<form method="post" action="/hug/campaign/{cid_e}/restore/{snap_id}">'
        f'<button type="submit" class="restore-btn">&#128257; Khôi phục</button>'
        f"</form>"
        f"</td>"
        f"</tr>"
    )


def render_history_page(campaign_id: str, snapshots: list[Any]) -> str:
    """Render the history list page for a campaign.

    Args:
        campaign_id: The campaign being viewed.
        snapshots:   List of sqlite3.Row from list_history(), newest-first.
    """
    cid_e = _e(campaign_id)

    if not snapshots:
        rows_html = (
            f'<tr><td colspan="5" class="empty">'
            f"Chưa có lịch sử nào cho campaign <code>{cid_e}</code>."
            f"</td></tr>"
        )
    else:
        rows_html = "\n".join(_render_snapshot_row(campaign_id, s) for s in snapshots)

    return f"""<!doctype html>
<html lang="vi" data-surface="HUG-CAMPAIGN-HISTORY">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hug · Lịch sử — {cid_e}</title><style>{_COMMON_CSS}{_HISTORY_CSS}</style></head>
<body>
  <main class="card">
    <h1>Lịch sử thay đổi</h1>
    <p class="sub">Campaign: <code>{cid_e}</code> · Hiển thị tối đa 20 phiên bản gần nhất.</p>
    <table>
      <thead><tr>
        <th>Thời gian lưu</th>
        <th>Tên phiên bản</th>
        <th>Trạng thái</th>
        <th>Targeting</th>
        <th>Hành động</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    <p style="margin-top:20px">
      <a class="batch-link" href="/hug/campaign/{cid_e}/edit">&larr; Quay lại sửa campaign</a>
    </p>
  </main>
</body></html>"""
