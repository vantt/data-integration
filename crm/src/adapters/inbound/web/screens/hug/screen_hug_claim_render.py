"""Rendering for the Hug claim station (self-contained kiosk HTML).

Pure functions — no template engine, no DB. They assemble the result banner
and fill the inline kiosk template with config-driven CLAIM_FIELDS inputs.
"""
from __future__ import annotations

import html
import json as _json

from fastapi.responses import HTMLResponse

from hug.claim_fields import CLAIM_FIELDS

from adapters.inbound.web.screens.hug.screen_hug_claim_template import CLAIM_PAGE_TEMPLATE


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


def _render_fields_html(order_code: str) -> str:
    """Build config-driven field inputs from CLAIM_FIELDS.

    Adding a new field to CLAIM_FIELDS automatically renders it here — no edit needed.
    Note: when a 2nd prefill field is added, accept a generic prefill dict instead
    of the named order_code param.
    """
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
    return fields_html


def _render_page(
    order_code: str = "",
    token: str = "",
    result: tuple[bool, str, str] | None = None,
) -> str:
    tk = html.escape(token)
    if result is None:
        result_html = _result_block(None, "")
        play = "null"
    else:
        success, message, edge = result
        result_html = _result_block(success, message, edge)
        play = '"ok"' if success else '"err"'

    # Serialise CLAIM_FIELDS for the JS block (validate key stripped).
    # _json.dumps always escapes < > & so embedding in <script> is XSS-safe.
    claim_fields_json = _json.dumps(
        [{k: v for k, v in f.items() if k != "validate"} for f in CLAIM_FIELDS]
    )

    return CLAIM_PAGE_TEMPLATE.format(
        fields_html=_render_fields_html(order_code),
        tk=tk,
        result_html=result_html,
        claim_fields_json=claim_fields_json,
        play=play,
    )
