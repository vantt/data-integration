"""screen_hug_campaign_html_preview.py — preview panel + overlap warnings HTML.

No FastAPI dependency. Renders the preview result panel that is injected
below the campaign form buttons after an action=preview POST.

Exported:
  render_preview_panel(preview, overlaps, new_priority) → str
"""
from __future__ import annotations

from adapters.inbound.web.screens.hug.screen_hug_campaign_html_list import _e


def _format_data_as_of(iso_utc: str | None) -> str | None:
    """Convert ISO UTC timestamp to ICT (UTC+7) display string.

    Returns None when the input is absent, so callers can guard easily.
    Uses ZoneInfo (stdlib 3.9+) — no extra deps.
    """
    if not iso_utc:
        return None
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        ict = dt.astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
        return ict.strftime("%d/%m/%Y %H:%M ICT")
    except Exception:
        return iso_utc  # Graceful degradation: show raw string on parse failure


def render_preview_panel(
    preview: dict,
    overlaps: list[dict],
    new_priority: int,
) -> str:
    """Render the preview result panel injected below the form buttons.

    Args:
        preview:      Result from preview_match_customers_d1() or preview_match_customers()
                      or {} on skip.
                      Keys (extended):
                        matched, total, sample (list[dict]), error (opt),
                        upper_bound_warning (opt str),
                        source ("d1" | "cache"),
                        data_as_of (opt str, ISO UTC),
                        upper_bound (bool — touchpoint attrs were stripped),
                        fallback_reason (opt str).
        overlaps:     List of {campaign_id, name, priority} from find_overlapping_campaigns().
        new_priority: The priority of the campaign being edited/created.
                      Used to determine shadow direction per overlap.
    """
    if not preview and not overlaps:
        return ""

    parts: list[str] = []

    # ── Preview count + sample ────────────────────────────────────────────────
    if "error" in preview:
        parts.append(
            f'<div style="color:#fca5a5;background:#7f1d1d;padding:10px 14px;'
            f'border-radius:8px;font-size:13px">'
            f'Preview không khả dụng: {_e(preview["error"])}</div>'
        )
    elif preview:
        matched = preview.get("matched", 0)
        total   = preview.get("total", 0)
        sample  = preview.get("sample", [])
        source  = preview.get("source", "cache")    # "d1" | "cache"
        data_as_of = preview.get("data_as_of")
        upper_bound = preview.get("upper_bound", False)
        fallback_reason = preview.get("fallback_reason")

        parts.append(
            f'<div style="background:#0f2340;border:1px solid #1d4ed8;border-radius:10px;'
            f'padding:14px 18px;margin-top:4px">'
        )

        # Source badge: shows data provenance.
        # D1 → green pill (exact count for customer-level attrs).
        # cache.db → amber pill (yesterday's snapshot).
        if source == "d1":
            badge_html = (
                '<span style="display:inline-block;padding:2px 8px;font-size:11px;'
                'background:#14532d;color:#86efac;border-radius:99px;margin-left:8px;'
                'font-weight:600">D1 · chính xác</span>'
            )
        else:
            badge_html = (
                '<span style="display:inline-block;padding:2px 8px;font-size:11px;'
                'background:#451a03;color:#fde68a;border-radius:99px;margin-left:8px;'
                'font-weight:600">cache.db · hôm qua</span>'
            )

        # Count header: omit ~ tilde when D1 (exact) and no touchpoint stripping.
        # Keep ~ when cache.db OR when upper_bound (touchpoint attrs stripped).
        show_tilde = (source != "d1") or upper_bound
        tilde = "~" if show_tilde else ""
        parts.append(
            f'<div style="font-size:15px;font-weight:700;color:#93c5fd;margin-bottom:4px">'
            f'Khớp {tilde}<strong style="color:#fff">{matched}</strong> / {total} '
            f'khách hàng{badge_html}</div>'
        )

        # data_as_of subscript: replica freshness (D1 path only, but guard for both).
        formatted_as_of = _format_data_as_of(data_as_of)
        if formatted_as_of:
            parts.append(
                f'<div style="font-size:11px;color:#64748b;margin-bottom:4px">'
                f'Dữ liệu tính đến: {_e(formatted_as_of)}</div>'
            )

        # Fallback notice: shown when Worker was configured but the call failed.
        if fallback_reason:
            parts.append(
                f'<div style="font-size:11px;color:#fde68a;margin-bottom:4px">'
                f'&#9888; {_e(fallback_reason)}</div>'
            )

        # Upper-bound warning when op_type / channel / sku was present in targeting
        # and stripped before the D1 loop (or when cache.db path skips touchpoint attrs).
        ub_warn = preview.get("upper_bound_warning")
        if ub_warn:
            parts.append(
                f'<div style="font-size:12px;color:#fde68a;background:#451a03;'
                f'border-radius:6px;padding:6px 10px;margin-bottom:8px">'
                f'&#9888; {_e(ub_warn)}</div>'
            )

        # Contactable note (always shown when preview runs).
        parts.append(
            '<div style="font-size:11px;color:#64748b;margin-bottom:10px">'
            'is_contactable từ kho dữ liệu, chưa phản ánh số mới Hug capture.</div>'
        )

        # Customer list table.
        # D1 path: show up to 50 rows (Worker limit=50 by default, no cap here).
        # cache.db path: sample capped at 5 by preview_match_customers(); display all returned.
        # customer_id is an opaque Sapo integer — no name/phone in this panel (PII boundary).
        if sample:
            # customer_type column present when D1 path (Phase 2 populates it in hug_customer).
            # Guard with .get() for cache.db rows that lack the column.
            has_customer_type = any("customer_type" in s for s in sample)
            if has_customer_type:
                headers = ("customer_id", "tier", "recency_days", "value_group", "contactable", "customer_type")
            else:
                headers = ("customer_id", "tier", "recency_days", "value_group", "contactable")

            header_cells = "".join(
                f'<th style="padding:4px 8px;text-align:left;font-size:11px;'
                f'color:#64748b;font-weight:500">{h}</th>'
                for h in headers
            )
            rows_html = ""
            for s in sample:
                ctype_cell = ""
                if has_customer_type:
                    ctype_cell = (
                        f'<td style="padding:3px 8px;font-size:12px">'
                        f'{_e(s.get("customer_type", ""))}</td>'
                    )
                rows_html += (
                    f'<tr>'
                    f'<td style="padding:3px 8px;font-family:ui-monospace,monospace;font-size:12px">'
                    f'{_e(s.get("customer_id", ""))}</td>'
                    f'<td style="padding:3px 8px;font-size:12px">{_e(s.get("tier", ""))}</td>'
                    f'<td style="padding:3px 8px;font-size:12px;text-align:right">'
                    f'{_e(s.get("recency_days", ""))}</td>'
                    f'<td style="padding:3px 8px;font-size:12px">{_e(s.get("value_group", ""))}</td>'
                    f'<td style="padding:3px 8px;font-size:12px;text-align:center">'
                    f'{_e(s.get("is_contactable", ""))}</td>'
                    f'{ctype_cell}'
                    f'</tr>'
                )
            row_count = len(sample)
            parts.append(
                f'<table style="width:100%;border-collapse:collapse">'
                f'<thead><tr>{header_cells}</tr></thead>'
                f'<tbody>{rows_html}</tbody></table>'
            )
            if row_count >= 50:
                parts.append(
                    '<div style="font-size:11px;color:#64748b;margin-top:6px">'
                    'Hiển thị tối đa 50 khách hàng. Phân trang sẽ được bổ sung sau.</div>'
                )

        parts.append('</div>')  # close preview box

    # ── Overlap warnings ──────────────────────────────────────────────────────
    if overlaps:
        parts.append(
            '<div style="margin-top:10px;background:#2d1b00;border:1px solid #d97706;'
            'border-radius:10px;padding:12px 16px">'
        )
        parts.append(
            '<div style="font-size:13px;font-weight:700;color:#fde68a;margin-bottom:8px">'
            '&#9888; Cảnh báo chồng lấp campaign</div>'
        )
        for ov in overlaps:
            other_p    = ov["priority"]
            other_name = _e(ov["name"])
            other_cid  = _e(ov["campaign_id"])
            other_p_e  = _e(other_p)
            # Lower priority number = higher precedence (first-match-by-priority).
            if other_p < new_priority:
                shadow_note = (
                    f'Campaign <strong>{other_name}</strong> (priority {other_p_e}) '
                    f'có ưu tiên cao hơn — campaign đó sẽ thắng khi cùng khớp.'
                )
            elif other_p > new_priority:
                shadow_note = (
                    f'Campaign <strong>{other_name}</strong> (priority {other_p_e}) '
                    f'có ưu tiên thấp hơn — campaign này sẽ thắng khi cùng khớp.'
                )
            else:
                shadow_note = (
                    f'Campaign <strong>{other_name}</strong> (priority {other_p_e}) '
                    f'có cùng priority — thứ tự không xác định, nên điều chỉnh.'
                )
            parts.append(
                f'<div style="font-size:12px;color:#fde68a;margin-bottom:6px">'
                f'<code style="font-size:11px;color:#fb923c">{other_cid}</code> — '
                f'{shadow_note}</div>'
            )
        parts.append('</div>')  # close overlap box

    return "\n".join(parts)
