"""S13 Settings management routes (admin-only).

Custom field definitions and tag CRUD across the settings tabs. Mirrors Go
screen_settings.go (same URL patterns, same redirect semantics). All routes
require admin via require_admin.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional, Protocol

from fastapi import APIRouter, Depends, Form, Query, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from adapters.inbound.http.auth_dependency import require_admin
from domain.entities.app_user import AppUser
from domain.entities.profile import CustomFieldDef, Tag
from adapters.inbound.web.screens.management.screen_mgmt_helpers import (
    _is_valid_hex_color,
    _parse_options,
    _safe,
)

_NAMED_COLORS = {"default", "moss", "coral", "amber"}


class SettingsSvc(Protocol):
    """Structural protocol for the settings service used by make_settings_router."""

    def list_custom_field_defs(self, entity_type: Optional[str] = None) -> list[CustomFieldDef]: ...
    def get_custom_field_def(self, field_id: str) -> Optional[CustomFieldDef]: ...
    def create_custom_field_def(self, **kwargs: Any) -> Any: ...
    def update_custom_field_def(self, field_id: str, **kwargs: Any) -> None: ...
    def list_tags(self, category: str) -> list[Tag]: ...
    def get_tag(self, tag_id: str) -> Optional[Tag]: ...
    def create_tag(self, name: str, category: str, color: str, display_label: str = "") -> Tag: ...
    def update_tag(self, tag_id: str, name: str, category: str, color: str, display_label: str = "") -> None: ...
    def delete_tag(self, tag_id: str) -> None: ...


class AppUsersSvc(Protocol):
    """Structural protocol for the app-user repository used by make_settings_router."""

    def list_active(self) -> list[AppUser]: ...


def make_settings_router(
    templates: Jinja2Templates,
    settings_svc: SettingsSvc,
    app_users_svc: AppUsersSvc,
) -> APIRouter:
    router = APIRouter()

    @router.get("/settings", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
    def settings(request: Request, tab: str = Query(default="custom_fields")):
        fields = _safe(lambda: settings_svc.list_custom_field_defs("party"), [], "cfd")
        tags = _safe(lambda: settings_svc.list_tags(""), [], "tags")
        users = _safe(app_users_svc.list_active, [], "users")
        return templates.TemplateResponse("settings.html", {
            "request": request, "active_tab": tab,
            "custom_fields": fields, "tags": tags, "users": users,
        })

    @router.get("/settings/custom-fields/modal/create", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
    def modal_custom_field_create(request: Request):
        return templates.TemplateResponse("settings.html", {
            "request": request, "field": None, "is_new": True, "view": "modal_cfd",
        })

    @router.post("/settings/custom-fields", dependencies=[Depends(require_admin)])
    async def custom_field_create(
        field_key: str = Form(""), label: str = Form(""),
        data_type: str = Form(""), is_required: str = Form("false"),
        options: str = Form(""),
    ):
        if not field_key.strip() or not label.strip():
            return HTMLResponse("field_key and label required", status_code=400)
        settings_svc.create_custom_field_def(
            field_id=str(uuid.uuid4()), entity_type="party",
            field_key=field_key.strip(), label=label.strip(),
            data_type=data_type.strip(), is_required=(is_required == "true"),
            is_active=True, options=_parse_options(options),
        )
        return Response(status_code=200,
                        headers={"HX-Redirect": "/settings?tab=custom_fields"})

    @router.get("/settings/custom-fields/{field_id}/modal/edit",
                response_class=HTMLResponse, dependencies=[Depends(require_admin)])
    def modal_custom_field_edit(request: Request, field_id: str):
        f = settings_svc.get_custom_field_def(field_id)
        if not f:
            return HTMLResponse("field not found", status_code=404)
        return templates.TemplateResponse("settings.html", {
            "request": request, "field": f, "is_new": False, "view": "modal_cfd",
        })

    @router.patch("/settings/custom-fields/{field_id}", dependencies=[Depends(require_admin)])
    async def custom_field_update(
        field_id: str,
        label: str = Form(""), data_type: str = Form(""),
        is_required: str = Form("false"), options: str = Form(""),
    ):
        settings_svc.update_custom_field_def(
            field_id=field_id, label=label.strip(),
            data_type=data_type.strip(), is_required=(is_required == "true"),
            is_active=True, options=_parse_options(options),
        )
        return Response(status_code=200,
                        headers={"HX-Redirect": "/settings?tab=custom_fields"})

    @router.get("/settings/tags/modal/create", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
    def modal_tag_create(request: Request):
        return templates.TemplateResponse("fragments/modal_m14_create_tag.html", {
            "request": request, "tag": None,
        })

    @router.get("/settings/tags/{tag_id}/modal/edit", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
    def modal_tag_edit(request: Request, tag_id: str):
        tag = settings_svc.get_tag(tag_id)
        if not tag:
            return HTMLResponse("not found", status_code=404)
        return templates.TemplateResponse("fragments/modal_m14_create_tag.html", {
            "request": request, "tag": tag,
        })

    @router.post("/settings/tags", dependencies=[Depends(require_admin)])
    async def tag_create(
        name: str = Form(""), color: str = Form(""),
        category: str = Form(""), display_label: str = Form(""),
    ):
        if not name.strip():
            return HTMLResponse("name required", status_code=400)
        color_val = color.strip()
        if color_val and color_val not in _NAMED_COLORS and not _is_valid_hex_color(color_val):
            return HTMLResponse("invalid color", status_code=400)
        settings_svc.create_tag(
            name=name.strip(),
            category=category.strip(), color=color_val,
            display_label=display_label.strip(),
        )
        return Response(status_code=200, headers={"HX-Redirect": "/settings?tab=tags"})

    @router.patch("/settings/tags/{tag_id}", dependencies=[Depends(require_admin)])
    async def tag_update(
        tag_id: str,
        name: str = Form(""), color: str = Form(""),
        category: str = Form(""), display_label: str = Form(""),
    ):
        if not name.strip():
            return HTMLResponse("name required", status_code=400)
        color_val = color.strip()
        if color_val and color_val not in _NAMED_COLORS and not _is_valid_hex_color(color_val):
            return HTMLResponse("invalid color", status_code=400)
        settings_svc.update_tag(
            tag_id=tag_id, name=name.strip(),
            category=category.strip(), color=color_val,
            display_label=display_label.strip(),
        )
        return Response(status_code=200, headers={"HX-Redirect": "/settings?tab=tags"})

    @router.delete("/settings/tags/{tag_id}", dependencies=[Depends(require_admin)])
    async def tag_delete(tag_id: str):
        settings_svc.delete_tag(tag_id)
        return Response(status_code=200)  # HTMX removes the row via outerHTML swap

    return router
