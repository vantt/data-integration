"""Composition root — the ONLY place that wires adapters to ports for the CRM Python server.

Mirrors the wiring order in crm/app/cmd/server/main.go.
All concrete adapter imports live here; the rest of the codebase depends on
protocols/ports only.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import (
    crm_db_path,
    olap_path,
    refresh_token,
    server_port,
)

# ── Outbound: SQLite ──────────────────────────────────────────────────────────
from adapters.outbound.sqlite.connection import CRMDatabase
from adapters.outbound.sqlite.party_repository import SQLitePartyRepository
from adapters.outbound.sqlite.dedup_repository import SQLiteDedupRepository
from adapters.outbound.sqlite.profile_repository import SQLiteProfileRepository
from adapters.outbound.sqlite.custom_field_repository import SQLiteCustomFieldRepository
from adapters.outbound.sqlite.tag_note_repository import SQLiteTagRepository, SQLiteNoteRepository
from adapters.outbound.sqlite.cache_repository import SQLiteCacheRepository
from adapters.outbound.sqlite.activity_repository import SQLiteActivityRepository
from adapters.outbound.sqlite.task_repository import SQLiteTaskRepository
from adapters.outbound.sqlite.conversation_repository import SQLiteConversationRepository
from adapters.outbound.sqlite.segment_repository import SQLiteSegmentRepository
from adapters.outbound.sqlite.campaign_repository import SQLiteCampaignRepository
from adapters.outbound.sqlite.app_user_repository import SQLiteAppUserRepository

# ── Outbound: DuckDB ──────────────────────────────────────────────────────────
from adapters.outbound.duckdb.order_repository import DuckDBOrderRepository

# ── Application services ──────────────────────────────────────────────────────
from application.merge_service import MergeService
from application.profile_service import ProfileService
from application.activity_service import ActivityService
from application.task_service import TaskService
from application.conversation_service import ConversationService
from application.segment_service import SegmentService
from application.campaign_service import CampaignService

# ── Inbound: HTTP API handlers ────────────────────────────────────────────────
from adapters.inbound.http.health_handler import create_health_router
from adapters.inbound.http.admin_handler import create_admin_router
from adapters.inbound.http.dedup_handler import make_dedup_router
from adapters.inbound.http.customer360_handler import make_customer360_router
from adapters.inbound.http.insight_handler import wire_insight_router, router as insight_router
from adapters.inbound.http.activity_handler import wire_activity_router, router as activity_router
from adapters.inbound.http.task_handler import wire_task_router, router as task_router
from adapters.inbound.http.conversation_handler import router as conv_router
from adapters.inbound.http.segment_handler import make_segment_router
from adapters.inbound.http.campaign_handler import make_campaign_router

# ── Inbound: Web UI screens ───────────────────────────────────────────────────
from adapters.inbound.web.format_helpers import (
    format_vnd, fmt_vnd, format_date_ict, format_datetime_ict, format_relative,
    truncate_str, join_nonempty,
    action_type_badge_class, task_status_css, conv_status_bdg,
    campaign_status_bdg, target_status_bdg, customer_label,
)
from adapters.inbound.web.screen_modals import init_modals, router as modals_router
from adapters.inbound.web.screen_worklist import make_worklist_router
from adapters.inbound.web.screen_customer_list import make_customer_list_router
from adapters.inbound.web.screen_customer_360 import make_customer_360_router
from adapters.inbound.web.screen_tasks_board import make_tasks_board_router
from adapters.inbound.web.screen_inbox import make_inbox_router
from adapters.inbound.web.screen_order_detail import make_order_detail_router
from adapters.inbound.web.screen_management import make_management_router

log = logging.getLogger(__name__)

# Paths relative to this file (crm/python/).
_THIS_DIR = Path(__file__).parent
_TEMPLATES_DIR = _THIS_DIR / "adapters" / "inbound" / "web" / "templates"
# Static assets: fall back to the Go web adapter's static dir when no Python-specific dir exists.
_STATIC_DIR = _THIS_DIR / "adapters" / "inbound" / "web" / "static"
_GO_STATIC_DIR = _THIS_DIR.parent / "app" / "internal" / "adapters" / "inbound" / "web" / "static"


def _resolve_static_dir() -> Optional[Path]:
    if _STATIC_DIR.exists():
        return _STATIC_DIR
    if _GO_STATIC_DIR.exists():
        return _GO_STATIC_DIR
    return None


def create_app() -> FastAPI:
    """Wire all dependencies and return a ready-to-serve FastAPI application."""

    # 1. Open CRMDatabase (crm.db with cache.db ATTACHed).
    data_dir = os.path.dirname(crm_db_path())
    db = CRMDatabase(data_dir)
    db.apply_migrations()
    log.info("migrations applied")

    # 2. Repositories (SQLite).
    conn = db.conn
    party_repo = SQLitePartyRepository(conn)
    dedup_repo = SQLiteDedupRepository(conn)
    cache_repo = SQLiteCacheRepository(conn)
    profile_repo = SQLiteProfileRepository(db)
    cf_repo = SQLiteCustomFieldRepository(db)
    tag_repo = SQLiteTagRepository(db)
    note_repo = SQLiteNoteRepository(db)
    activity_repo = SQLiteActivityRepository(db)
    task_repo = SQLiteTaskRepository(db)
    conv_repo = SQLiteConversationRepository(db)
    segment_repo = SQLiteSegmentRepository(conn)
    campaign_repo = SQLiteCampaignRepository(conn)
    app_user_repo = SQLiteAppUserRepository(conn)

    # 3. Application services.
    merge_svc = MergeService(party_repo, dedup_repo)
    profile_svc = ProfileService(profile_repo, cf_repo, tag_repo, note_repo)
    activity_svc = ActivityService(activity_repo)
    task_svc = TaskService(task_repo, party_repo, cache_repo)
    conv_svc = ConversationService(conv_repo, party_repo)
    segment_svc = SegmentService(segment_repo, conn)
    campaign_svc = CampaignService(campaign_repo, segment_repo, party_repo, conn)

    # 4. DuckDB order repo — non-fatal if olap.duckdb is unavailable.
    order_repo: Optional[DuckDBOrderRepository] = None
    try:
        order_repo = DuckDBOrderRepository(olap_path())
        log.info("order repo: olap.duckdb mounted at %s", olap_path())
    except Exception as exc:
        log.warning("order repo unavailable (%s) — /orders/* will return 503", exc)

    # 5. FastAPI app.
    app = FastAPI(title="CRM", docs_url="/api/docs", redoc_url=None)

    # Store conversation_service on app.state (used by conversation_handler.py via request.app.state).
    app.state.conversation_service = conv_svc

    # 6. Templates + static.
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
    # Custom Jinja2 filters
    templates.env.filters["format_vnd"] = format_vnd
    templates.env.filters["fmt_vnd"] = fmt_vnd
    templates.env.filters["format_date_ict"] = format_date_ict
    templates.env.filters["format_datetime_ict"] = format_datetime_ict
    templates.env.filters["format_relative"] = format_relative
    templates.env.filters["truncate_str"] = truncate_str
    templates.env.filters["join_nonempty"] = join_nonempty
    # Global functions callable from any template
    templates.env.globals["action_type_badge_class"] = action_type_badge_class
    templates.env.globals["task_status_css"] = task_status_css
    templates.env.globals["conv_status_bdg"] = conv_status_bdg
    templates.env.globals["campaign_status_bdg"] = campaign_status_bdg
    templates.env.globals["target_status_bdg"] = target_status_bdg
    templates.env.globals["customer_label"] = customer_label
    static_dir = _resolve_static_dir()
    if static_dir:
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    else:
        log.warning("no static dir found — /static will not be served")

    # 7. HTTP API routers (prefix=/api already set per handler).
    app.include_router(create_health_router(db))
    app.include_router(create_admin_router())

    wire_insight_router(party_repo, cache_repo)
    app.include_router(insight_router)

    wire_activity_router(activity_svc)
    app.include_router(activity_router)

    wire_task_router(task_svc)
    app.include_router(task_router)

    # conversation_handler uses request.app.state — just mount the router.
    app.include_router(conv_router)

    app.include_router(make_dedup_router(dedup_repo, merge_svc))
    app.include_router(make_customer360_router(
        profile_q=profile_svc,
        profile_w=profile_svc,
        tags=profile_svc,
        notes=profile_svc,
        cf_admin=profile_svc,
        party_lookup=party_repo,
        insight_q=cache_repo,
    ))
    app.include_router(make_segment_router(segment_svc))
    app.include_router(make_campaign_router(campaign_svc))

    # 8. Web UI routers (no prefix — serve at root paths).
    init_modals(
        deps=_make_modal_deps(party_repo, profile_svc, app_user_repo),
        templates=templates,
    )
    app.include_router(modals_router)

    app.include_router(make_worklist_router(
        templates=templates,
        action_queue=cache_repo,
        tasks=task_svc,
        task_writer=task_svc,
    ))
    app.include_router(make_customer_list_router(
        templates=templates,
        parties=party_repo,
    ))
    app.include_router(make_customer_360_router(
        templates=templates,
        profile=profile_svc,
        identities=party_repo,
        insight=cache_repo,
        activities=activity_svc,
        activity_log=activity_svc,
        notes=profile_svc,
        party_tasks=task_repo,
    ))
    app.include_router(make_tasks_board_router(
        templates=templates,
        task_querier=task_svc,
        task_writer=task_svc,
        task_creator=task_svc,
        task_generator=task_svc,
    ))
    app.include_router(make_inbox_router(
        templates=templates,
        conversations=conv_svc,
        conv_reader=conv_repo,
        conv_writer=conv_svc,
        parties=party_repo,
        app_users=app_user_repo,
        activity_log=activity_svc,
    ))
    app.include_router(make_order_detail_router(
        templates=templates,
        orders=order_repo,
    ))
    app.include_router(make_management_router(
        templates=templates,
        segments_svc=segment_svc,
        campaigns_svc=campaign_svc,
        dedup_svc=dedup_repo,
        merger_svc=merge_svc,
        parties_svc=party_repo,
        settings_svc=profile_svc,
        app_users_svc=app_user_repo,
    ))

    return app


# ── Helpers ───────────────────────────────────────────────────────────────────

class _ModalDeps:
    """Thin struct satisfying screen_modals.WebDeps protocol."""
    def __init__(self, party_creator, profile_querier, owner_assigner, app_users):
        self.party_creator = party_creator
        self.profile_querier = profile_querier
        self.owner_assigner = owner_assigner
        self.app_users = app_users


def _make_modal_deps(party_repo, profile_svc, app_user_repo) -> _ModalDeps:
    return _ModalDeps(
        party_creator=party_repo,
        profile_querier=profile_svc,
        owner_assigner=profile_svc,
        app_users=app_user_repo,
    )
