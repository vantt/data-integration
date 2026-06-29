"""Web adapter — Hug campaign admin (list / create / edit / status toggle).

  GET  /hug/campaigns               -> campaign list
  GET  /hug/campaign/new            -> blank create form
  POST /hug/campaign/new            -> action=preview → preview+overlap, re-render (no save)
                                       action=save    → validate + upsert + push → redirect
  GET  /hug/campaign/{id}/edit      -> edit form pre-filled from crm.db
  POST /hug/campaign/{id}/edit      -> action=preview → preview+overlap, re-render (no save)
                                       action=save    → validate + upsert + push → redirect
  POST /hug/campaign/{id}/status    -> pause / activate / archive

Design:
- Pattern A: self-contained HTML from screen_hug_campaign_html.py (no FastAPI dep
  in _html module — independently testable).
- targeting assembled server-side via screen_hug_campaign_form_helpers.parse_targeting.
- Push is best-effort: failure shows a warning, local save always wins.
- campaign_id from URL validated early against safe-slug pattern (safe_campaign_id).
- Preview action: runs preview_match_customers + find_overlapping_campaigns, re-renders
  the form with a results panel. Does NOT save. op_type/channel constraints produce an
  upper-bound warning (touchpoint-level attrs cannot be counted per customer).
"""
from __future__ import annotations

import html
import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from hug.campaign_push import push_campaign  # imported at module level for test mocking
from hug.targeting_catalog import TARGETING_CATALOG, validate_targeting
from hug.targeting_engine import preview_match_customers_d1
from domain.ports.hug_ports import HugCampaignPort
from adapters.inbound.web.screens.hug.screen_hug_campaign_html_list import render_campaign_list
from adapters.inbound.web.screens.hug.screen_hug_campaign_html_form import (
    render_campaign_form,
    render_status_result,
)
from adapters.inbound.web.screens.hug.screen_hug_campaign_html_history import render_history_page
from adapters.inbound.web.screens.hug.screen_hug_campaign_form_helpers import (
    attempt_push,
    build_campaign_row,
    form_to_partial,
    parse_targeting,
    priority_duplicate_warning,
    safe_campaign_id,
    VALID_STATUS_ACTIONS,
    STATUS_FOR_ACTION,
)

log = logging.getLogger(__name__)

# Private aliases exported for test compatibility (tests import from this module).
_parse_targeting = parse_targeting
_build_row = build_campaign_row
_safe_campaign_id = safe_campaign_id


def _attempt_push(saved_row: dict) -> bool:
    """Push a saved campaign row to the edge Worker.

    Defined here (not just aliased from form_helpers) so tests can mock
    `adapters.inbound.web.screen_hug_campaign.push_campaign` and have the
    patch apply to the call inside this function.
    """
    result = push_campaign(saved_row)
    return result.get("ok", False) or result.get("skipped", False)


def make_hug_campaign_router(campaign_port: HugCampaignPort) -> APIRouter:
    """Return the campaign admin router bound to a HugCampaignPort.

    IMPORTANT: must end with `return router`. A missing return yields None,
    causing include_router(None) to disable all hug stations. The assert in
    composition.py provides a runtime guard; this docstring documents the why.
    """
    router = APIRouter()

    # ── List ──────────────────────────────────────────────────────────────────

    @router.get("/hug/campaigns", response_class=HTMLResponse)
    async def campaign_list(request: Request) -> HTMLResponse:
        rows = [dict(r) for r in campaign_port.list_campaigns()]
        flash = request.query_params.get("flash", "")
        flash_ok = request.query_params.get("flash_ok", "1") == "1"
        return HTMLResponse(render_campaign_list(rows, flash=flash, flash_ok=flash_ok))

    # ── Create form ───────────────────────────────────────────────────────────

    @router.get("/hug/campaign/new", response_class=HTMLResponse)
    async def campaign_new_form() -> HTMLResponse:
        return HTMLResponse(
            render_campaign_form(
                campaign=None, errors=[], catalog=TARGETING_CATALOG,
                suggested_priority=campaign_port.suggest_next_priority(), is_new=True,
            )
        )

    # ── Create submit ─────────────────────────────────────────────────────────

    @router.post("/hug/campaign/new", response_class=HTMLResponse)
    async def campaign_new_submit(request: Request) -> HTMLResponse:
        form_multi = _multi(await request.form())
        action = form_multi.get("action", ["save"])[0]

        cid = _safe_campaign_id(form_multi.get("campaign_id", [""])[0])
        if not cid:
            return HTMLResponse(_rerender(form_multi, ["Campaign ID chỉ dùng chữ, số, gạch ngang, "
                "gạch dưới (tối đa 128 ký tự)."], campaign_port, is_new=True))

        targeting = _validated_targeting_or_errors(form_multi)
        if isinstance(targeting, list):  # errors list
            return HTMLResponse(_rerender(form_multi, targeting, campaign_port, is_new=True))

        if action == "preview":
            return HTMLResponse(_rerender_with_preview(
                form_multi, targeting, campaign_port, exclude_id=None, is_new=True,
            ))

        # action == "save" (default)
        row = _build_row(cid, form_multi, targeting)
        try:
            saved = campaign_port.upsert_campaign(row)
        except ValueError as exc:
            return HTMLResponse(_rerender(form_multi, [str(exc)], campaign_port, is_new=True))

        ok = _attempt_push(dict(saved))
        prio_warn = priority_duplicate_warning(campaign_port, saved["priority"], cid)
        log.info("hug campaign: created %r push_ok=%s prio_dup=%s", cid, ok, bool(prio_warn))
        return RedirectResponse(_flash_url(row["name"], ok, prio_warn), status_code=303)

    # ── Edit form ─────────────────────────────────────────────────────────────

    @router.get("/hug/campaign/{campaign_id}/edit", response_class=HTMLResponse)
    async def campaign_edit_form(campaign_id: str, request: Request) -> HTMLResponse:
        cid = _safe_campaign_id(campaign_id)
        if not cid:
            return HTMLResponse(_bad_id(campaign_id), status_code=400)
        row = campaign_port.get_campaign(cid)
        if row is None:
            return HTMLResponse(_not_found(cid), status_code=404)
        # Flash from restore or other redirects (non-blocking info banner).
        flash = request.query_params.get("flash", "")
        flash_ok = request.query_params.get("flash_ok", "1") == "1"
        return HTMLResponse(
            render_campaign_form(
                campaign=dict(row), errors=[], catalog=TARGETING_CATALOG,
                suggested_priority=campaign_port.suggest_next_priority(), is_new=False,
                flash=flash, flash_ok=flash_ok,
            )
        )

    # ── Edit submit ───────────────────────────────────────────────────────────

    @router.post("/hug/campaign/{campaign_id}/edit", response_class=HTMLResponse)
    async def campaign_edit_submit(campaign_id: str, request: Request) -> HTMLResponse:
        cid = _safe_campaign_id(campaign_id)
        if not cid:
            return HTMLResponse(_bad_id(campaign_id), status_code=400)
        if campaign_port.get_campaign(cid) is None:
            return HTMLResponse(_not_found(cid), status_code=404)

        form_multi = _multi(await request.form())
        action = form_multi.get("action", ["save"])[0]

        targeting = _validated_targeting_or_errors(form_multi)
        if isinstance(targeting, list):
            partial = form_to_partial(form_multi)
            partial["campaign_id"] = cid
            return HTMLResponse(
                render_campaign_form(campaign=partial, errors=targeting,
                    catalog=TARGETING_CATALOG,
                    suggested_priority=campaign_port.suggest_next_priority(), is_new=False)
            )

        if action == "preview":
            return HTMLResponse(_rerender_with_preview(
                form_multi, targeting, campaign_port, exclude_id=cid, is_new=False,
            ))

        # action == "save" (default)
        row = _build_row(cid, form_multi, targeting)
        try:
            saved = campaign_port.upsert_campaign(row)
        except ValueError as exc:
            partial = form_to_partial(form_multi)
            partial["campaign_id"] = cid
            return HTMLResponse(
                render_campaign_form(campaign=partial, errors=[str(exc)],
                    catalog=TARGETING_CATALOG,
                    suggested_priority=campaign_port.suggest_next_priority(), is_new=False)
            )

        ok = _attempt_push(dict(saved))
        prio_warn = priority_duplicate_warning(campaign_port, saved["priority"], cid)
        log.info("hug campaign: updated %r push_ok=%s prio_dup=%s", cid, ok, bool(prio_warn))
        return RedirectResponse(_flash_url(row["name"], ok, prio_warn), status_code=303)

    # ── Status toggle ─────────────────────────────────────────────────────────

    @router.post("/hug/campaign/{campaign_id}/status", response_class=HTMLResponse)
    async def campaign_status_toggle(
        campaign_id: str,
        action: str = Form(default=""),
    ) -> HTMLResponse:
        cid = _safe_campaign_id(campaign_id)
        if not cid:
            return HTMLResponse(_bad_id(campaign_id), status_code=400)
        if action not in VALID_STATUS_ACTIONS:
            return HTMLResponse(
                _err(f"Hành động không hợp lệ: '{html.escape(action)}'"), status_code=400
            )
        existing = campaign_port.get_campaign(cid)
        if existing is None:
            return HTMLResponse(_not_found(cid), status_code=404)

        row = dict(existing)
        row["status"] = STATUS_FOR_ACTION[action]
        saved = campaign_port.upsert_campaign(row)
        ok = _attempt_push(dict(saved))
        log.info("hug campaign: %r status→%s push_ok=%s", cid, row["status"], ok)
        return HTMLResponse(render_status_result(cid, row["status"], ok))

    # ── History list ──────────────────────────────────────────────────────────

    @router.get("/hug/campaign/{campaign_id}/history", response_class=HTMLResponse)
    async def campaign_history(campaign_id: str) -> HTMLResponse:
        cid = _safe_campaign_id(campaign_id)
        if not cid:
            return HTMLResponse(_bad_id(campaign_id), status_code=400)
        if campaign_port.get_campaign(cid) is None:
            return HTMLResponse(_not_found(cid), status_code=404)
        snapshots = campaign_port.list_history(cid, limit=20)
        return HTMLResponse(render_history_page(cid, snapshots))

    # ── Restore snapshot ──────────────────────────────────────────────────────

    @router.post("/hug/campaign/{campaign_id}/restore/{snapshot_id}",
                 response_class=HTMLResponse)
    async def campaign_restore(campaign_id: str, snapshot_id: int) -> HTMLResponse:
        from urllib.parse import quote as _quote
        cid = _safe_campaign_id(campaign_id)
        if not cid:
            return HTMLResponse(_bad_id(campaign_id), status_code=400)
        if snapshot_id < 1:
            return HTMLResponse(_err("snapshot_id không hợp lệ."), status_code=400)
        try:
            restored = campaign_port.restore_snapshot(cid, snapshot_id)
        except KeyError as exc:
            return HTMLResponse(_err(html.escape(str(exc))), status_code=404)
        except (ValueError, Exception) as exc:
            log.error("hug campaign restore failed cid=%r snap=%s: %s", cid, snapshot_id, exc)
            return HTMLResponse(
                _err(f"Khôi phục thất bại: {html.escape(str(exc))}"), status_code=500
            )
        push_result = _attempt_push(dict(restored))
        push_note = "✓" if push_result else "✗ (kiểm tra log)"
        flash = f"Đã khôi phục phiên bản #{snapshot_id}. Đẩy D1: {push_note}"
        log.info("hug campaign: restored %r snap=%s push_ok=%s", cid, snapshot_id, push_result)
        return RedirectResponse(
            f"/hug/campaign/{cid}/edit?flash={_quote(flash, safe='')}&flash_ok={'1' if push_result else '0'}",
            status_code=303,
        )

    return router  # MUST be last — see docstring above


# ── Private helpers ───────────────────────────────────────────────────────────

def _multi(form) -> dict[str, list[str]]:
    """Convert a FastAPI FormData to {key: [values]} dict."""
    out: dict[str, list[str]] = {}
    for k, v in form.multi_items():
        out.setdefault(k, []).append(str(v))
    return out


def _validated_targeting_or_errors(form_multi: dict[str, list[str]]):
    """Return targeting dict if valid, else list[str] of errors."""
    targeting = _parse_targeting(form_multi)
    errors = validate_targeting(targeting)
    return errors if errors else targeting


def _rerender(form_multi, errors, campaign_port: HugCampaignPort, *, is_new: bool) -> str:
    partial = form_to_partial(form_multi)
    return render_campaign_form(
        campaign=partial, errors=errors, catalog=TARGETING_CATALOG,
        suggested_priority=campaign_port.suggest_next_priority(), is_new=is_new,
    )


def _touchpoint_warning(targeting: dict) -> str | None:
    """Return a warning string if targeting constrains op_type or channel.

    These are touchpoint-level attrs (per-scan, not per-customer) — the preview
    count is an UPPER BOUND when they are present.
    """
    from hug.targeting_catalog import TARGETING_CATALOG
    tp_attrs = [a for a, s in TARGETING_CATALOG.items() if s.get("touchpoint_level")]
    constrained = [a for a in tp_attrs if a in targeting]
    if not constrained:
        return None
    names = ", ".join(f"'{a}'" for a in constrained)
    return (
        f"Lưu ý: {names} là thuộc tính theo lượt quét, không tính được theo khách hàng. "
        f"Kết quả preview bỏ qua điều kiện này — số khách là CẬN TRÊN (upper bound)."
    )


def _rerender_with_preview(
    form_multi: dict[str, list[str]],
    targeting: dict,
    campaign_port: HugCampaignPort,
    *,
    exclude_id: str | None,
    is_new: bool,
) -> str:
    """Re-render the form with preview count + overlap warnings injected."""
    partial = form_to_partial(form_multi)
    if not is_new:
        partial["campaign_id"] = exclude_id or form_multi.get("campaign_id", [""])[0]

    # Run preview: prefers D1 live replica when Worker is configured, falls back to
    # cache.db snapshot automatically. Never raises — returns error dict on failure.
    preview_result = preview_match_customers_d1(targeting)
    ub_warn = _touchpoint_warning(targeting)
    if ub_warn:
        preview_result["upper_bound_warning"] = ub_warn

    # Detect overlapping active campaigns via the port.
    try:
        overlaps = campaign_port.find_overlapping_campaigns(targeting, exclude_id=exclude_id)
    except Exception as exc:
        log.warning("find_overlapping_campaigns failed: %s", exc)
        overlaps = []

    return render_campaign_form(
        campaign=partial,
        errors=[],
        catalog=TARGETING_CATALOG,
        suggested_priority=campaign_port.suggest_next_priority(),
        is_new=is_new,
        preview=preview_result,
        overlaps=overlaps,
    )



def _flash_url(name: str, push_ok: bool, extra: str = "") -> str:
    """Build the redirect URL for the campaign list page after save.

    ok_flag is False (amber banner) when push failed OR a priority warning is present,
    so the user notices the warning alongside the save confirmation.
    """
    from urllib.parse import quote
    push_note = "✓" if push_ok else "✗ (kiểm tra log)"
    msg = f"Đã lưu '{html.escape(name)}'. Đẩy D1: {push_note}{extra}"
    # Show amber banner when push failed OR when a priority duplicate warning was appended.
    all_ok = push_ok and not extra
    return f"/hug/campaigns?flash={quote(msg, safe='')}&flash_ok={'1' if all_ok else '0'}"


def _bad_id(raw: str) -> str:
    return (
        f'<html><body style="font-family:sans-serif;background:#0f172a;color:#e2e8f0;padding:40px">'
        f'Campaign ID không hợp lệ: <code>{html.escape(str(raw))}</code><br>'
        f'<a href="/hug/campaigns" style="color:#38bdf8">← Danh sách</a></body></html>'
    )


def _not_found(cid: str) -> str:
    return (
        f'<html><body style="font-family:sans-serif;background:#0f172a;color:#e2e8f0;padding:40px">'
        f'Không tìm thấy campaign: <code>{html.escape(cid)}</code><br>'
        f'<a href="/hug/campaigns" style="color:#38bdf8">← Danh sách</a></body></html>'
    )


def _err(msg: str) -> str:
    return (
        f'<html><body style="font-family:sans-serif;background:#0f172a;color:#e2e8f0;padding:40px">'
        f'{msg}<br><a href="/hug/campaigns" style="color:#38bdf8">← Danh sách</a></body></html>'
    )
