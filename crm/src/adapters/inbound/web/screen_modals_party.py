"""Web adapter — S03 party modal HTMX fragment routes (router composition).

Composes the per-modal sub-routers for the Customer 360 sidebar and topbar.
The factory functions and shared helpers/protocols live in sibling modules:

  M03 — Tag Management       screen_modal_tags.py
  M04 — Assign Owner         screen_modal_owner.py
  M05 — Create / Edit Task   screen_modal_task.py
  M06 — Custom Fields        screen_modal_custom_fields.py
  M15 — Edit Contact/Addr    screen_modal_contact.py
  shared helpers/protocols   screen_modal_shared.py
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.templating import Jinja2Templates

from crm.src.adapters.inbound.web.screen_modal_contact import make_contact_modal_router
from crm.src.adapters.inbound.web.screen_modal_custom_fields import make_custom_fields_modal_router
from crm.src.adapters.inbound.web.screen_modal_owner import make_owner_modal_router
from crm.src.adapters.inbound.web.screen_modal_shared import (
    AppUserRepo,
    PartyRepo,
    ProfileSvc,
    TaskSvc,
)
from crm.src.adapters.inbound.web.screen_modal_tags import make_tags_modal_router
from crm.src.adapters.inbound.web.screen_modal_task import make_task_modal_router


def make_party_modals_router(
    templates: Jinja2Templates,
    profile: ProfileSvc,
    party_repo: PartyRepo,
    task_svc: TaskSvc,
    app_users: AppUserRepo,
) -> APIRouter:
    """Return APIRouter for all /modals/m* GET routes and related POST handlers."""
    router = APIRouter()
    router.include_router(make_tags_modal_router(templates, profile))
    router.include_router(make_owner_modal_router(templates, profile, app_users))
    router.include_router(make_task_modal_router(templates, profile, task_svc, app_users))
    router.include_router(make_custom_fields_modal_router(templates, profile))
    router.include_router(make_contact_modal_router(templates, profile, party_repo))
    return router
