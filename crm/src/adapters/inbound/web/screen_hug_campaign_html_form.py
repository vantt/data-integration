"""screen_hug_campaign_html_form.py — campaign create/edit form + status result HTML.

No FastAPI dependency. Renders the /hug/campaign/new and /hug/campaign/{id}/edit forms,
plus the brief status-update confirmation page.

Phase 5: preview panel and overlap warnings live in screen_hug_campaign_html_preview.py;
render_preview_panel is imported here and re-exported via screen_hug_campaign_html.py.

Form is split into 3 tabs:
  Tab 1 "basic"     — Campaign ID, Name, Status, Priority
  Tab 2 "targeting" — rule-builder (AND/OR logic note included)
  Tab 3 "dest"      — Destination, Offer ref, Quota, Schedule
Buttons (Preview / Save) are outside tabs and always visible.
"""
from __future__ import annotations

import json
from typing import Any

from adapters.inbound.web.screen_hug_mint_html import _COMMON_CSS
from adapters.inbound.web.screen_hug_campaign_html_list import _e, _STATUS_LABEL
from adapters.inbound.web.screen_hug_campaign_html_preview import render_preview_panel  # noqa: F401

_FORM_CSS = """
  body { align-items: flex-start; padding: 32px 16px; }
  .card { width: min(700px, 98vw); }

  /* ── Tab nav ── */
  .tab-nav { display: flex; gap: 2px; margin-bottom: 24px;
             border-bottom: 1px solid #334155; padding-bottom: 0; }
  .tab-btn { padding: 9px 18px; font-size: 13px; font-weight: 600; letter-spacing: .3px;
             background: none; border: none; border-bottom: 2px solid transparent;
             margin-bottom: -1px; color: #64748b; cursor: pointer; transition: color .12s; }
  .tab-btn:hover { color: #e2e8f0; }
  .tab-btn.tab-active { color: #38bdf8; border-bottom-color: #38bdf8; }
  .tab-panel { display: none; }
  .tab-panel.tab-visible { display: block; }

  /* ── AND/OR logic note ── */
  .logic-note { background: #0a1f12; border: 1px solid #166534; border-radius: 8px;
                padding: 13px 16px; margin-bottom: 20px; font-size: 13px; line-height: 1.6; }
  .logic-note .ln-head { font-weight: 700; color: #4ade80; margin-bottom: 6px; font-size: 13px; }
  .logic-note p { margin: 0 0 4px; color: #86efac; }
  .logic-note code { font-family: ui-monospace,monospace; font-size: 11px;
                     background: #052e16; padding: 1px 5px; border-radius: 3px; color: #6ee7b7; }
  .logic-note .ln-ex { margin-top: 10px; padding-top: 10px; border-top: 1px solid #166534;
                        font-size: 12px; color: #6ee7b7; }
  .logic-note .ln-warn { margin-top: 8px; font-size: 12px; color: #fde68a;
                          background: #3b1c00; border-radius: 5px; padding: 6px 10px; }

  /* ── Form controls ── */
  input[type=text], input[type=number] {
    width: 100%; padding: 10px 12px; font-size: 15px; box-sizing: border-box;
    border-radius: 8px; border: 1px solid #334155; background: #0f172a;
    color: #f1f5f9; outline: none; }
  input:focus { border-color: #38bdf8; box-shadow: 0 0 0 3px rgba(56,189,248,.15); }
  select { width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #334155;
          background: #0f172a; color: #f1f5f9; font-size: 14px; }
  select:focus { outline: none; border-color: #38bdf8; }
  label { display: block; margin: 14px 0 4px; font-size: 13px; color: #94a3b8; }

  /* ── Buttons (outside tabs, always visible) ── */
  .btn-row { display: flex; gap: 10px; margin-top: 28px; padding-top: 20px;
             border-top: 1px solid #334155; }
  button[type=submit] { flex: 1; padding: 14px; font-size: 16px;
    font-weight: 700; border: none; border-radius: 10px;
    background: #38bdf8; color: #0f172a; cursor: pointer; }
  button[type=submit]:hover { background: #0ea5e9; }
  button.btn-preview { background: #334155; color: #e2e8f0; }
  button.btn-preview:hover { background: #475569; }

  .err-banner { background: #7f1d1d; border-radius: 10px; padding: 12px 16px;
    font-size: 14px; color: #fca5a5; margin-bottom: 16px; }
  .err-banner li { margin: 4px 0; }
  .hint-text { font-size: 12px; color: #64748b; margin: 2px 0 0; }
  code { font-family: ui-monospace, monospace; font-size: 13px; color: #38bdf8; }
  .readonly-field { padding: 10px 12px; background: #0f172a; border: 1px solid #334155;
    border-radius: 8px; font-family: ui-monospace, monospace; font-size: 13px;
    color: #94a3b8; }
"""

_TAB_JS = """
<script>
(function () {
  function hugTab(id, save) {
    document.querySelectorAll('.tab-btn').forEach(function(b) {
      b.classList.toggle('tab-active', b.dataset.tab === id);
    });
    document.querySelectorAll('.tab-panel').forEach(function(p) {
      p.classList.toggle('tab-visible', p.id === 'tab-' + id);
    });
    if (save) { try { localStorage.setItem('hug-campaign-tab', id); } catch(e) {} }
  }

  window.hugTab = hugTab;

  document.addEventListener('DOMContentLoaded', function() {
    var defaultTab = document.body.dataset.defaultTab || 'basic';
    var saved;
    try { saved = localStorage.getItem('hug-campaign-tab'); } catch(e) {}
    hugTab(defaultTab === 'basic' && saved ? saved : defaultTab, false);
  });
}());
</script>
"""


def _select_opts(options: list[tuple[str, str]], selected: str) -> str:
    parts = []
    for val, label in options:
        sel = ' selected' if str(val) == str(selected) else ''
        parts.append(f'<option value="{_e(val)}"{sel}>{_e(label)}</option>')
    return "\n".join(parts)


def _rule_row(attr: str, spec: dict, current_rule: Any) -> str:
    """Render one targeting rule-builder block for a catalog attribute."""
    label = _e(spec.get("description", attr))
    attr_e = _e(attr)
    is_touchpoint = spec.get("touchpoint_level", False)
    touchpoint_badge = (
        ' <span style="font-size:10px;background:#1e293b;color:#64748b;'
        'padding:1px 6px;border-radius:4px;vertical-align:middle">per-scan</span>'
        if is_touchpoint else ""
    )

    if spec["type"] == "list":
        domain = spec.get("values", [])
        active: set[str] = {str(v) for v in current_rule} if isinstance(current_rule, list) else set()
        checks = []
        for v in domain:
            v_str = str(v)
            chk = ' checked' if v_str in active else ''
            checks.append(
                f'<label style="display:inline-flex;align-items:center;gap:4px;'
                f'margin:2px 4px;font-size:12px;text-transform:none;letter-spacing:0">'
                f'<input type="checkbox" name="val_{attr_e}" value="{_e(v_str)}"{chk}>'
                f'{_e(v_str)}</label>'
            )
        controls = (
            '<div style="display:flex;flex-wrap:wrap;gap:2px;margin-top:6px">'
            + "".join(checks) + '</div>'
        )
    else:
        # range type: gte / lte number inputs
        gte_val = lte_val = ""
        if isinstance(current_rule, dict):
            raw_gte = current_rule.get("gte", current_rule.get("gt", ""))
            raw_lte = current_rule.get("lte", current_rule.get("lt", ""))
            gte_val = "" if raw_gte is None else str(raw_gte)
            lte_val = "" if raw_lte is None else str(raw_lte)
        controls = (
            f'<div style="display:flex;gap:8px;align-items:center;margin-top:6px">'
            f'<label style="margin:0;font-size:12px;text-transform:none;flex-shrink:0">Từ (≥)</label>'
            f'<input type="number" name="gte_{attr_e}" value="{_e(gte_val)}" '
            f'placeholder="ví dụ: 30" min="0" style="width:100px">'
            f'<label style="margin:0;font-size:12px;text-transform:none;flex-shrink:0">Đến (≤)</label>'
            f'<input type="number" name="lte_{attr_e}" value="{_e(lte_val)}" '
            f'placeholder="ví dụ: 365" min="0" style="width:100px">'
            f'</div>'
        )

    return (
        f'<div style="margin:10px 0;padding:10px 14px;background:#0f172a;'
        f'border-radius:8px;border:1px solid #334155">'
        f'<div style="font-size:12px;text-transform:uppercase;letter-spacing:.6px;'
        f'color:#94a3b8;margin-bottom:2px">{label}{touchpoint_badge} '
        f'<code style="font-size:11px;color:#475569">({attr_e})</code></div>'
        f'{controls}</div>'
    )


_LOGIC_NOTE = """
<div class="logic-note">
  <div class="ln-head">&#128270; Cách hoạt động của Targeting</div>
  <p><strong style="color:#4ade80">Nhiều attribute được set</strong> → khách phải thoả <strong>TẤT CẢ</strong> (AND).</p>
  <p><strong style="color:#4ade80">Nhiều giá trị trong cùng một attribute</strong> → thoả <strong>MỘT</strong> là đủ (OR).</p>
  <p><strong style="color:#4ade80">Bỏ trống attribute</strong> → không lọc, mọi khách đều pass điều kiện đó.</p>
  <div class="ln-ex">
    <strong>Ví dụ:</strong> <code>tier = [VIP, CORE]</code> + <code>recency_days ≥ 30</code> + <code>is_contactable = [1]</code><br>
    → Gửi cho khách <em>VIP hoặc CORE</em>, <em>mua lần cuối cách đây ít nhất 30 ngày</em>, <em>có thể liên hệ qua Zalo</em>.
  </div>
  <div class="ln-warn">
    &#9888; <strong>op_type</strong> và <strong>channel</strong> là điều kiện per-scan (lúc quét QR), không phải per-khách —
    Preview count sẽ không đếm được 2 attribute này.
  </div>
</div>
"""


def render_campaign_form(
    campaign: dict | None,
    errors: list[str],
    catalog: dict,
    suggested_priority: int,
    is_new: bool = True,
    preview: dict | None = None,
    overlaps: list[dict] | None = None,
    flash: str = "",
    flash_ok: bool = True,
) -> str:
    """Render the create/edit form for a Hug campaign (3-tab layout).

    Args:
        campaign:           Existing campaign dict (None for new form).
        errors:             Validation error strings (shown as red banner on Tab 1).
        catalog:            TARGETING_CATALOG.
        suggested_priority: Hint for priority field.
        is_new:             True = create form, False = edit form.
        preview:            Preview result dict or None.
        overlaps:           Overlap list or None.
        flash:              One-shot info/success message.
        flash_ok:           True = green banner, False = amber banner.
    """
    c = campaign or {}
    action = "/hug/campaign/new" if is_new else f"/hug/campaign/{_e(c.get('campaign_id', ''))}/edit"
    page_title = "Tạo campaign mới" if is_new else f"Sửa campaign: {_e(c.get('name', ''))}"
    history_link = (
        f'<a href="/hug/campaign/{_e(c.get("campaign_id", ""))}/history" '
        f'style="font-size:12px;color:#64748b;text-decoration:none;float:right">'
        f'&#128337; Lịch sử</a>'
        if not is_new else ""
    )

    try:
        targeting: dict = json.loads(c.get("targeting") or "{}")
    except (json.JSONDecodeError, TypeError):
        targeting = {}

    errors_html = ""
    if errors:
        items = "".join(f"<li>{_e(e)}</li>" for e in errors)
        errors_html = f'<div class="err-banner"><ul style="margin:0;padding-left:18px">{items}</ul></div>'

    flash_html = ""
    if flash:
        flash_bg = "#14532d" if flash_ok else "#78350f"
        flash_color = "#86efac" if flash_ok else "#fde68a"
        flash_html = (
            f'<div style="background:{flash_bg};color:{flash_color};border-radius:10px;'
            f'padding:12px 16px;font-size:14px;margin-bottom:12px">{_e(flash)}</div>'
        )

    # Campaign ID: editable (new) or readonly (edit)
    if is_new:
        cid_field = (
            f'<input type="text" id="campaign_id" name="campaign_id" '
            f'value="{_e(c.get("campaign_id", ""))}" placeholder="vip-winback-zalo" required '
            f'pattern="[A-Za-z0-9_-]+" maxlength="128">'
            f'<p class="hint-text">Chỉ dùng chữ, số, gạch ngang, gạch dưới. Không sửa được sau khi tạo.</p>'
        )
    else:
        cid = _e(c.get("campaign_id", ""))
        cid_field = (
            f'<div class="readonly-field">{cid}</div>'
            f'<input type="hidden" name="campaign_id" value="{cid}">'
        )

    dest_opts = _select_opts(
        [("zalo_oa", "Zalo OA deep-link"), ("cf_pages", "Cloudflare Pages URL"), ("url", "URL tuỳ chỉnh")],
        c.get("destination_type", "zalo_oa"),
    )
    status_opts = _select_opts(
        [("active", "Đang chạy"), ("paused", "Tạm dừng"), ("archived", "Lưu trữ")],
        c.get("status", "active"),
    )

    rules_html = "\n".join(_rule_row(attr, spec, targeting.get(attr)) for attr, spec in catalog.items())
    priority_val = _e(c.get("priority", suggested_priority))

    try:
        new_priority_int = int(c.get("priority") or suggested_priority)
    except (ValueError, TypeError):
        new_priority_int = suggested_priority

    preview_html = render_preview_panel(
        preview=preview or {},
        overlaps=overlaps or [],
        new_priority=new_priority_int,
    )

    # If errors present, force Tab 1 (where the error banner lives).
    default_tab = "basic" if errors else "basic"

    return f"""<!doctype html>
<html lang="vi" data-surface="HUG-CAMPAIGN-FORM">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hug · {_e(page_title)}</title><style>{_COMMON_CSS}{_FORM_CSS}</style></head>
<body data-default-tab="{default_tab}">
  <main class="card">
    <div style="display:flex;align-items:baseline;justify-content:space-between">
      <h1>{_e(page_title)}</h1>
      {history_link}
    </div>
    {flash_html}
    {errors_html}

    <form method="post" action="{action}" autocomplete="off">

      <!-- ── Tab nav ── -->
      <div class="tab-nav">
        <button type="button" class="tab-btn" data-tab="basic"
                onclick="hugTab('basic', true)">Cơ bản</button>
        <button type="button" class="tab-btn" data-tab="targeting"
                onclick="hugTab('targeting', true)">Targeting</button>
        <button type="button" class="tab-btn" data-tab="dest"
                onclick="hugTab('dest', true)">Đích đến &amp; Thêm</button>
      </div>

      <!-- ── Tab 1: Cơ bản ── -->
      <div id="tab-basic" class="tab-panel">
        <label for="campaign_id">Campaign ID</label>
        {cid_field}

        <label for="name">Tên hiển thị</label>
        <input type="text" id="name" name="name" value="{_e(c.get('name', ''))}"
               placeholder="VIP Winback — Zalo OA" required maxlength="200">

        <label for="status">Trạng thái</label>
        <select id="status" name="status">{status_opts}</select>

        <label for="priority">Priority <span style="font-size:12px;color:#64748b">(thấp hơn = ưu tiên cao hơn)</span></label>
        <input type="number" id="priority" name="priority"
               value="{priority_val}" min="1" max="9999" required>
        <p class="hint-text">Gợi ý: {suggested_priority} · Khi nhiều campaign cùng match, engine chọn priority nhỏ nhất.</p>
      </div>

      <!-- ── Tab 2: Targeting ── -->
      <div id="tab-targeting" class="tab-panel">
        {_LOGIC_NOTE}
        {rules_html}
      </div>

      <!-- ── Tab 3: Đích đến & Thêm ── -->
      <div id="tab-dest" class="tab-panel">
        <label for="destination_type">Loại đích</label>
        <select id="destination_type" name="destination_type">{dest_opts}</select>

        <label for="destination_url">URL đích</label>
        <input type="text" id="destination_url" name="destination_url"
               value="{_e(c.get('destination_url', ''))}"
               placeholder="https://oa.zalo.me/...">
        <p class="hint-text">URL khách được redirect đến sau khi claim token.</p>

        <label for="offer_ref" style="margin-top:24px">Mã offer <span style="color:#475569">(tuỳ chọn)</span></label>
        <input type="text" id="offer_ref" name="offer_ref"
               value="{_e(c.get('offer_ref') or '')}" placeholder="HUG50 / WINBACK_VIP">

        <label for="quota_total">Quota tổng <span style="color:#475569">(để trống = không giới hạn)</span></label>
        <input type="number" id="quota_total" name="quota_total"
               value="{_e(c.get('quota_total') or '')}" min="1" placeholder="">

        <label for="schedule_start">Thời gian bắt đầu <span style="color:#475569">(UTC, tuỳ chọn)</span></label>
        <input type="text" id="schedule_start" name="schedule_start"
               value="{_e(c.get('schedule_start') or '')}" placeholder="2026-07-01T00:00:00Z">

        <label for="schedule_end">Thời gian kết thúc <span style="color:#475569">(UTC, tuỳ chọn)</span></label>
        <input type="text" id="schedule_end" name="schedule_end"
               value="{_e(c.get('schedule_end') or '')}" placeholder="2026-07-31T23:59:59Z">
      </div>

      <!-- ── Actions (outside tabs, always visible) ── -->
      <div class="btn-row">
        <button type="submit" name="action" value="preview" class="btn-preview">
          &#128269; Xem trước
        </button>
        <button type="submit" name="action" value="save">&#128190; Lưu &amp; Đẩy D1</button>
      </div>

    </form>

    {preview_html}

    <p class="hint" style="margin-top:16px">
      <a class="batch-link" href="/hug/campaigns">&larr; Danh sách campaign</a>
    </p>
  </main>
  {_TAB_JS}
</body></html>"""


def render_status_result(campaign_id: str, new_status: str, push_ok: bool) -> str:
    """Brief confirmation page that auto-redirects to /hug/campaigns after 1 s."""
    cid_e = _e(campaign_id)
    status_label = _STATUS_LABEL.get(new_status, new_status)
    push_note = "Đẩy D1: ✓" if push_ok else "Đẩy D1: ✗ (kiểm tra log)"
    return f"""<!doctype html>
<html lang="vi" data-surface="HUG-CAMPAIGN-STATUS">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="1;url=/hug/campaigns">
<title>Hug · Cập nhật trạng thái</title><style>{_COMMON_CSS}</style></head>
<body>
  <main class="card">
    <h1>Đã cập nhật</h1>
    <p class="sub">Campaign <code>{cid_e}</code> → <strong>{_e(status_label)}</strong>.</p>
    <p style="font-size:13px;color:#94a3b8">{_e(push_note)}</p>
    <p class="hint">Đang chuyển hướng…
      <a class="batch-link" href="/hug/campaigns">Nhấn đây nếu không tự chuyển</a>
    </p>
  </main>
</body></html>"""
