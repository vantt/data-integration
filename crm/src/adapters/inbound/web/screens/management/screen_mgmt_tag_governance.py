"""Web adapter — S13 Tag Governance Admin (Phase 03, 260706-0833).

Routes (all admin-gated via require_admin, same dependency used by the rest
of S13 settings — see screen_mgmt_settings.py):

  GET  /settings/tags                        main screen (?tab=<category|l1|l2>)
  GET  /settings/tags/merge/modal            merge modal fragment
  POST /settings/tags/merge                  perform merge (canonical_tag_id, merge_tag_ids[])
  POST /settings/tags/{tag_id}/archive
  POST /settings/tags/{tag_id}/unarchive
  POST /settings/tags/{tag_id}/promote-l1
  POST /settings/tags/{tag_id}/promote-l2    (category form field)
  POST /settings/tags/{tag_id}/rename        (name form field, L1 queue only)
  POST /settings/tags/{tag_id}/delete-provisional
  POST /settings/tags/chipify/create-tag     posted by the reused M14 create-tag modal
  POST /settings/tags/chipify/map-existing
  POST /settings/tags/chipify/skip
  POST /settings/tags/chipify/skip-all

Mutating routes return `Response(200, headers={"HX-Redirect": ...})` — the
same convention screen_mgmt_settings.py uses — so every action is a full
server-rendered reload of /settings/tags (simplest correct option given how
much a single action can change: a tag moving queues, a category tab
appearing/disappearing, a chipify group clearing).
"""
from __future__ import annotations

import logging
from typing import List, Optional, Protocol
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Query, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from adapters.inbound.http.auth_dependency import require_admin
from domain.entities.profile import Tag

log = logging.getLogger(__name__)


class TagGovernanceSvc(Protocol):
    """Structural protocol for the service used by make_tag_governance_router."""

    def list_categories(self) -> list[str]: ...
    def list_tags_for_category(self, category: str) -> list[dict]: ...
    def list_mergeable_tags(self, category: str) -> list[dict]: ...
    def list_provisional_l1(self) -> list[dict]: ...
    def list_provisional_l2(self) -> list[dict]: ...
    def list_chipify_groups(self) -> list[dict]: ...
    def list_all_tags(self) -> list[Tag]: ...
    def merge_tags(self, canonical_tag_id: str, merge_tag_ids: list[str]) -> None: ...
    def archive_tag(self, tag_id: str) -> None: ...
    def unarchive_tag(self, tag_id: str) -> None: ...
    def promote_l1(self, tag_id: str) -> None: ...
    def assign_category_and_promote_l2(self, tag_id: str, category: str) -> None: ...
    def rename_tag(self, tag_id: str, new_name: str) -> None: ...
    def delete_provisional_tag(self, tag_id: str) -> None: ...
    def chipify_create_tag(
        self, raw_text: str, name: str, category: Optional[str], is_provisional: bool,
        color: str, display_label: str, actor_id: Optional[str],
    ) -> Tag: ...
    def chipify_map_existing(self, raw_text: str, tag_id: str, actor_id: Optional[str]) -> None: ...
    def chipify_skip(self, raw_text: str) -> None: ...
    def chipify_bulk_skip_all(self) -> None: ...


def _actor_id(request: Request) -> Optional[str]:
    user = getattr(request.state, "current_user", None)
    return getattr(user, "user_id", None)


def _redirect(tab: str) -> Response:
    return Response(status_code=200, headers={"HX-Redirect": f"/settings/tags?tab={quote(tab)}"})


def make_tag_governance_router(templates: Jinja2Templates, svc: TagGovernanceSvc) -> APIRouter:
    router = APIRouter(dependencies=[Depends(require_admin)])

    @router.get("/settings/tags", response_class=HTMLResponse)
    def tag_governance(request: Request, tab: str = Query(default="")):
        categories = svc.list_categories()
        active_tab = tab if (tab == "l1" or tab == "l2" or tab in categories) else (
            categories[0] if categories else "l1"
        )
        if active_tab == "l1":
            tags = svc.list_provisional_l1()
        elif active_tab == "l2":
            tags = svc.list_provisional_l2()
        else:
            tags = svc.list_tags_for_category(active_tab)
        return templates.TemplateResponse("settings_tag_governance.html", {
            "request": request,
            "categories": categories,
            "active_tab": active_tab,
            "tags": tags,
            "chipify_groups": svc.list_chipify_groups(),
            "all_tags": svc.list_all_tags(),
        })

    @router.get("/settings/tags/merge/modal", response_class=HTMLResponse)
    def merge_modal(request: Request, category: str = Query(...), preselect: str = Query(default=""),
                    tab: str = Query(default="")):
        return templates.TemplateResponse("fragments/modal_tag_governance_merge.html", {
            "request": request, "category": category, "tab": tab or category,
            "candidates": svc.list_mergeable_tags(category), "preselect": preselect,
        })

    @router.post("/settings/tags/merge")
    async def merge(
        canonical_tag_id: str = Form(...),
        merge_tag_ids: List[str] = Form(default=[]),
        tab: str = Form(default=""),
    ):
        try:
            svc.merge_tags(canonical_tag_id, merge_tag_ids)
        except ValueError as exc:
            return HTMLResponse(str(exc), status_code=400)
        except Exception as exc:
            log.error("merge_tags %s <- %s: %s", canonical_tag_id, merge_tag_ids, exc)
            return HTMLResponse("Lỗi merge tag", status_code=500)
        return _redirect(tab or "l1")

    @router.post("/settings/tags/{tag_id}/archive")
    async def archive(tag_id: str, tab: str = Query(default="")):
        svc.archive_tag(tag_id)
        return _redirect(tab)

    @router.post("/settings/tags/{tag_id}/unarchive")
    async def unarchive(tag_id: str, tab: str = Query(default="")):
        svc.unarchive_tag(tag_id)
        return _redirect(tab)

    @router.post("/settings/tags/{tag_id}/promote-l1")
    async def promote_l1(tag_id: str):
        svc.promote_l1(tag_id)
        return _redirect("l1")

    @router.post("/settings/tags/{tag_id}/promote-l2")
    async def promote_l2(tag_id: str, category: str = Form(...)):
        try:
            svc.assign_category_and_promote_l2(tag_id, category)
        except ValueError as exc:
            return HTMLResponse(str(exc), status_code=400)
        return _redirect("l2")

    @router.post("/settings/tags/{tag_id}/rename")
    async def rename(tag_id: str, name: str = Form(...), tab: str = Form(default="l1")):
        try:
            svc.rename_tag(tag_id, name)
        except ValueError as exc:
            return HTMLResponse(str(exc), status_code=400)
        return _redirect(tab)

    @router.post("/settings/tags/{tag_id}/delete-provisional")
    async def delete_provisional(tag_id: str, tab: str = Query(default="l1")):
        svc.delete_provisional_tag(tag_id)
        return _redirect(tab)

    @router.post("/settings/tags/chipify/create-tag")
    async def chipify_create_tag(
        request: Request,
        raw_text: str = Form(...),
        name: str = Form(...),
        category: str = Form(""),
        color: str = Form(""),
        display_label: str = Form(""),
        is_provisional: str = Form("false"),
        tab: str = Form(default=""),
    ):
        if not name.strip():
            return HTMLResponse("name required", status_code=400)
        try:
            svc.chipify_create_tag(
                raw_text=raw_text,
                name=name.strip(),
                category=category.strip() or None,
                is_provisional=(is_provisional == "true"),
                color=color.strip(),
                display_label=display_label.strip(),
                actor_id=_actor_id(request),
            )
        except Exception as exc:
            log.error("chipify_create_tag: %s", exc)
            return HTMLResponse("Lỗi tạo tag", status_code=500)
        return _redirect(tab)

    @router.post("/settings/tags/chipify/map-existing")
    async def chipify_map_existing(
        request: Request, raw_text: str = Form(...), tag_id: str = Form(...), tab: str = Form(default=""),
    ):
        try:
            svc.chipify_map_existing(raw_text, tag_id, _actor_id(request))
        except ValueError as exc:
            return HTMLResponse(str(exc), status_code=400)
        return _redirect(tab)

    @router.post("/settings/tags/chipify/skip")
    async def chipify_skip(raw_text: str = Form(...), tab: str = Form(default="")):
        svc.chipify_skip(raw_text)
        return _redirect(tab)

    @router.post("/settings/tags/chipify/skip-all")
    async def chipify_skip_all(tab: str = Form(default="")):
        svc.chipify_bulk_skip_all()
        return _redirect(tab)

    return router
