"""HTTP adapter — Script-navigation endpoint.

POST /api/parties/{id}/script-nav
  Form params: current_node_id, outcome
  Response:    HTML fragment (HTMX swap) — the next node to render.

Pure interpreter: (script, current_node_id, outcome) → next node HTML.
No session state, no activity writes (deferred; terminal outcome is logged
via the existing outcome bar → M08 → ActivityService chain unchanged).

Auth: DEFERRED — LAN-trust only.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from domain.ports.approach_script_repository import ApproachScriptRepository
from domain.ports.party_repository import PartyRepository

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ── dependency holders ────────────────────────────────────────────────────────

_party_repo: PartyRepository | None = None
_approach_repo: ApproachScriptRepository | None = None
_templates: Jinja2Templates | None = None


def wire_script_nav_router(
    party_repo: PartyRepository,
    approach_repo: ApproachScriptRepository,
    templates: Jinja2Templates,
) -> None:
    """Bind repositories and template engine; called during app startup."""
    global _party_repo, _approach_repo, _templates
    _party_repo = party_repo
    _approach_repo = approach_repo
    _templates = templates


def _deps() -> tuple[PartyRepository, ApproachScriptRepository, Jinja2Templates]:
    if _party_repo is None or _approach_repo is None or _templates is None:
        raise RuntimeError("ScriptNavHandler not wired — call wire_script_nav_router first")
    return _party_repo, _approach_repo, _templates


# ── pure interpreter ──────────────────────────────────────────────────────────

def _resolve_next_node(
    nodes: dict,
    current_node_id: str,
    outcome: str,
    entry_node_id: str,
) -> tuple[bool, dict | None]:
    """Return (is_terminal, next_node_dict).

    Pure function — no I/O, no side effects.
    Fallback rules:
      - unknown current_node_id  → fall back to entry_node
      - unknown outcome          → return current node unchanged (idempotent)
      - next is null             → terminal
      - next not in nodes        → fall back to entry_node (defensive)
    """
    node = nodes.get(current_node_id) or nodes.get(entry_node_id)
    if node is None:
        # No usable node at all — treat as terminal so UI doesn't hang.
        return True, None

    for option in node.get("options", []):
        if option.get("outcome") == outcome:
            next_id = option.get("next")
            if next_id is None:
                return True, None  # explicit terminal
            next_node = nodes.get(next_id) or nodes.get(entry_node_id)
            return False, next_node

    # No matching option — return current node unchanged (idempotent, no crash).
    return False, node


# ── endpoint ──────────────────────────────────────────────────────────────────

@router.post("/parties/{party_id}/script-nav", response_class=HTMLResponse)
async def post_script_nav(
    request: Request,
    party_id: str,
    current_node_id: str = Form(...),
    outcome: str = Form(...),
):
    """POST /api/parties/{id}/script-nav — advance branching script to next node.

    Returns an HTML fragment for HTMX to swap into #s14-node-area.
    On terminal (next=null): returns the terminal fragment (no nav buttons).
    On node-not-found: returns entry_node fragment (never 404).
    """
    party_repo, approach_repo, templates = _deps()

    # ── Resolve sapo_customer identity → numeric customer_id ─────────────────
    try:
        identities = party_repo.list_identities(party_id)
    except Exception as exc:
        log.error("script_nav: list_identities party=%s: %s", party_id, exc)
        return HTMLResponse("<div class='s14-node-error'>Lỗi tra cứu khách hàng.</div>", status_code=500)

    customer_id: int | None = None
    for ident in identities:
        if ident.identity_type == "sapo_customer":
            try:
                customer_id = int(ident.identity_value)
                break
            except (ValueError, TypeError):
                continue

    if customer_id is None:
        return HTMLResponse("<div class='s14-node-error'>Không tìm thấy khách hàng.</div>", status_code=404)

    # ── Load script ───────────────────────────────────────────────────────────
    try:
        script = approach_repo.get_by_customer_id(customer_id)
    except Exception as exc:
        log.error("script_nav: get_by_customer_id party=%s cid=%d: %s", party_id, customer_id, exc)
        return HTMLResponse("<div class='s14-node-error'>Lỗi tải kịch bản.</div>", status_code=500)

    if script is None:
        return HTMLResponse("<div class='s14-node-error'>Không có kịch bản.</div>", status_code=404)

    # ── Guard: STOP state (recommended=false) → refuse navigation ────────────
    if not script.recommended:
        return HTMLResponse("<div class='s14-node-error'>Kịch bản đang ở trạng thái STOP.</div>", status_code=403)

    # ── Guard: no branching script ────────────────────────────────────────────
    nodes = script.data.get("nodes") if isinstance(script.data, dict) else None
    if not isinstance(nodes, dict) or not nodes:
        return HTMLResponse("<div class='s14-node-error'>Kịch bản không có cây phân nhánh.</div>", status_code=404)

    entry_node_id: str = script.data.get("entry_node") or "root"

    # ── Interpret: resolve next node ──────────────────────────────────────────
    is_terminal, next_node = _resolve_next_node(nodes, current_node_id, outcome, entry_node_id)

    # ── Render HTML fragment ──────────────────────────────────────────────────
    return templates.TemplateResponse(
        "fragments/_s14_node_fragment.html",
        {
            "request": request,
            "node": next_node,
            "terminal": is_terminal,
            "party_id": party_id,
        },
    )
