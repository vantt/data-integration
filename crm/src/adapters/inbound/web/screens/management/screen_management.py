"""Management screen handlers — segments, campaigns, dedup, settings.

Single public entry point that composes the four management sub-routers.
Each route group lives in its own module:
  - screen_mgmt_segments  (S08 segments)
  - screen_mgmt_campaigns (S10 campaigns)
  - screen_mgmt_dedup     (S04 dedup review)
  - screen_mgmt_settings  (S13 settings, admin-only)

Mirrors Go screen_segments.go / screen_campaigns.go / screen_dedup_review.go /
screen_settings.go exactly (same URL patterns, same redirect semantics).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.templating import Jinja2Templates

from adapters.inbound.web.screens.management.screen_mgmt_campaigns import make_campaigns_router
from adapters.inbound.web.screens.management.screen_mgmt_dedup import make_dedup_router
from adapters.inbound.web.screens.management.screen_mgmt_segments import make_segments_router
from adapters.inbound.web.screens.management.screen_mgmt_settings import make_settings_router


def make_management_router(
    templates: Jinja2Templates,
    segments_svc: Any,
    campaigns_svc: Any,
    dedup_svc: Any,
    merger_svc: Any,
    parties_svc: Any,
    settings_svc: Any,
    app_users_svc: Any,
) -> APIRouter:
    router = APIRouter()
    router.include_router(make_segments_router(templates, segments_svc))
    router.include_router(
        make_campaigns_router(templates, campaigns_svc, segments_svc, parties_svc, app_users_svc)
    )
    router.include_router(make_dedup_router(templates, dedup_svc, merger_svc, parties_svc))
    router.include_router(make_settings_router(templates, settings_svc, app_users_svc))
    return router
