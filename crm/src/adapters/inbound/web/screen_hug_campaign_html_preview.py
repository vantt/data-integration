"""screen_hug_campaign_html_preview.py — preview panel + overlap warnings HTML.

No FastAPI dependency. Renders the preview result panel that is injected
below the campaign form buttons after an action=preview POST.

Exported:
  render_preview_panel(preview, overlaps, new_priority) → str
"""
from __future__ import annotations

from adapters.inbound.web.screen_hug_campaign_html_list import _e


def render_preview_panel(
    preview: dict,
    overlaps: list[dict],
    new_priority: int,
) -> str:
    """Render the preview result panel injected below the form buttons.

    Args:
        preview:      Result from preview_match_customers() or {} on skip.
                      Keys: matched, total, sample (list[dict]), error (opt),
                      upper_bound_warning (opt str).
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

        parts.append(
            f'<div style="background:#0f2340;border:1px solid #1d4ed8;border-radius:10px;'
            f'padding:14px 18px;margin-top:4px">'
        )
        parts.append(
            f'<div style="font-size:15px;font-weight:700;color:#93c5fd;margin-bottom:6px">'
            f'Khớp ~<strong style="color:#fff">{matched}</strong> / {total} khách hàng</div>'
        )

        # Upper-bound warning when op_type / channel was present in targeting.
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

        if sample:
            header_cells = "".join(
                f'<th style="padding:4px 8px;text-align:left;font-size:11px;'
                f'color:#64748b;font-weight:500">{h}</th>'
                for h in ("customer_id", "tier", "recency_days", "value_group", "contactable")
            )
            rows_html = ""
            for s in sample:
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
                    f'</tr>'
                )
            parts.append(
                f'<table style="width:100%;border-collapse:collapse">'
                f'<thead><tr>{header_cells}</tr></thead>'
                f'<tbody>{rows_html}</tbody></table>'
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
