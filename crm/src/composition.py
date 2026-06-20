"""Composition root — the ONLY place that wires adapters to ports for the CRM Python server.

Mirrors the wiring order in crm/src/cmd/server/main.go.
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

from adapters.inbound.web.templating import make_templates

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
from adapters.outbound.sqlite.action_state_repository import SQLiteActionStateRepository
from adapters.outbound.sqlite.activity_repository import SQLiteActivityRepository
from adapters.outbound.sqlite.task_repository import SQLiteTaskRepository
from adapters.outbound.sqlite.conversation_repository import SQLiteConversationRepository
from adapters.outbound.sqlite.segment_repository import SQLiteSegmentRepository
from adapters.outbound.sqlite.campaign_repository import SQLiteCampaignRepository
from adapters.outbound.sqlite.app_user_repository import SQLiteAppUserRepository

# ── Outbound: DuckDB ──────────────────────────────────────────────────────────
from adapters.outbound.duckdb.order_repository import DuckDBOrderRepository
from adapters.outbound.duckdb.customer_timeline_repository import CustomerTimelineRepository
from adapters.outbound.duckdb.customer_orders_repository import CustomerOrdersRepository
from adapters.outbound.duckdb.customer_dim_metrics_repository import CustomerDimMetricsRepository
from adapters.outbound.duckdb.customer_list_rfm_repository import CustomerListRFMRepository
from adapters.outbound.duckdb.dataquality_repository import DataQualityRepository

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
from adapters.inbound.http.json_api_mirror_handler import make_json_api_mirror_router
from adapters.inbound.http.dataquality_handler import make_dataquality_router

# ── Inbound: Web UI screens ───────────────────────────────────────────────────
from adapters.inbound.web.format_helpers import (
    format_vnd, fmt_vnd, format_date_ict, format_datetime_ict, format_relative,
    format_ict, truncate_str, join_nonempty, segment_days_since, segment_channel_pref,
    action_type_badge_class, task_status_css, task_status_chip_class, conv_status_bdg,
    campaign_status_bdg, target_status_bdg, customer_label, status_badge_class,
    fmt_pct, fmt_vnd_signed, order_status_tone, payment_tone, ship_tone,
    verdict_tone, verdict_word, fmt_date_key, days_since, recency_days_label,
    bdg_cls_filter, bdg_tip_filter,
)
from adapters.inbound.web.badge_catalog import bdg_lookup
from adapters.inbound.web.screen_modals import init_modals, router as modals_router
from adapters.inbound.web.screen_modals_party import make_party_modals_router
from adapters.inbound.web.screen_worklist import make_worklist_router
from adapters.inbound.web.screen_customer_list import make_customer_list_router
from adapters.inbound.web.screen_customer_360 import make_customer_360_router
from adapters.inbound.web.screen_tasks_board import make_tasks_board_router
from adapters.inbound.web.screen_inbox import make_inbox_router
from adapters.inbound.web.screen_order_detail import make_order_detail_router
from adapters.inbound.web.screen_management import make_management_router
from adapters.inbound.web.screen_search import make_search_router
from adapters.inbound.web.screen_resolver import make_resolver_router
from adapters.inbound.web.screen_hug_claim import make_hug_claim_router
from adapters.inbound.web.screen_hug_mint import make_hug_mint_router
from adapters.inbound.web.screen_hug_review import make_hug_review_router
from adapters.inbound.web.screen_hug_campaign import make_hug_campaign_router

# ── Hug — local token-provisioning master (separate Python-owned hug.db) ──────
from hug import db as hug_db

log = logging.getLogger(__name__)

# Paths relative to this file (crm/src/).
_THIS_DIR = Path(__file__).parent
_TEMPLATES_DIR = _THIS_DIR / "adapters" / "inbound" / "web" / "templates"
_STATIC_DIR = _THIS_DIR / "adapters" / "inbound" / "web" / "static"


def _resolve_static_dir() -> Optional[Path]:
    if _STATIC_DIR.exists():
        return _STATIC_DIR
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
    action_state_repo = SQLiteActionStateRepository(conn)
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

    # 4. DuckDB repos — non-fatal if olap.duckdb is unavailable.
    order_repo: Optional[DuckDBOrderRepository] = None
    try:
        order_repo = DuckDBOrderRepository(olap_path())
        log.info("order repo: olap.duckdb mounted at %s", olap_path())
    except Exception as exc:
        log.warning("order repo unavailable (%s) — /orders/* will return 503", exc)

    timeline_repo: Optional[CustomerTimelineRepository] = None
    try:
        timeline_repo = CustomerTimelineRepository(olap_path())
    except Exception as exc:
        log.warning("timeline repo unavailable (%s) — status_history panel will return 503", exc)

    customer_orders_repo: Optional[CustomerOrdersRepository] = None
    try:
        customer_orders_repo = CustomerOrdersRepository(olap_path())
    except Exception as exc:
        log.warning("customer_orders repo unavailable (%s) — orders panel falls back to cache", exc)

    dim_metrics_repo: Optional[CustomerDimMetricsRepository] = None
    try:
        dim_metrics_repo = CustomerDimMetricsRepository(olap_path())
    except Exception as exc:
        log.warning("dim_metrics repo unavailable (%s) — insight panel segments/profitability hidden", exc)

    list_rfm_repo: Optional[CustomerListRFMRepository] = None
    try:
        list_rfm_repo = CustomerListRFMRepository(olap_path())
    except Exception as exc:
        log.warning("list_rfm repo unavailable (%s) — Recency/Frequency/customer_type hidden in S02", exc)

    dq_repo: Optional[DataQualityRepository] = None
    try:
        dq_repo = DataQualityRepository(olap_path())
    except Exception as exc:
        log.warning("dq repo unavailable (%s) — /_dq_strip will return empty", exc)

    # 5. FastAPI app.
    app = FastAPI(title="CRM", docs_url="/api/docs", redoc_url=None)

    # Store conversation_service on app.state (used by conversation_handler.py via request.app.state).
    app.state.conversation_service = conv_svc

    # 6. Templates + static.
    templates = make_templates(str(_TEMPLATES_DIR))
    # Custom Jinja2 filters
    templates.env.filters["format_vnd"] = format_vnd
    templates.env.filters["fmt_vnd"] = fmt_vnd
    templates.env.filters["format_date_ict"] = format_date_ict
    templates.env.filters["format_datetime_ict"] = format_datetime_ict
    templates.env.filters["format_relative"] = format_relative
    templates.env.filters["truncate_str"] = truncate_str
    templates.env.filters["join_nonempty"] = join_nonempty
    templates.env.filters["format_ict"] = format_ict
    templates.env.filters["segment_days_since"] = segment_days_since
    templates.env.filters["segment_channel_pref"] = segment_channel_pref
    # Global functions callable from any template
    templates.env.globals["action_type_badge_class"] = action_type_badge_class
    templates.env.globals["task_status_css"] = task_status_css
    templates.env.globals["task_status_chip_class"] = task_status_chip_class
    templates.env.globals["status_badge_class"] = status_badge_class
    # Order detail filters
    templates.env.filters["fmt_pct"] = fmt_pct
    templates.env.filters["fmt_vnd_signed"] = fmt_vnd_signed
    templates.env.filters["order_status_tone"] = order_status_tone
    templates.env.filters["payment_tone"] = payment_tone
    templates.env.filters["ship_tone"] = ship_tone
    templates.env.filters["verdict_tone"] = verdict_tone
    templates.env.filters["verdict_word"] = verdict_word
    templates.env.globals["conv_status_bdg"] = conv_status_bdg
    templates.env.globals["campaign_status_bdg"] = campaign_status_bdg
    templates.env.globals["target_status_bdg"] = target_status_bdg
    templates.env.globals["customer_label"] = customer_label
    templates.env.filters["fmt_date_key"] = fmt_date_key
    templates.env.filters["days_since"] = days_since
    templates.env.filters["recency_days_label"] = recency_days_label
    templates.env.filters["bdg_cls"] = bdg_cls_filter
    templates.env.filters["bdg_tip"] = bdg_tip_filter
    templates.env.globals["bdg_lookup"] = bdg_lookup
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
    app.include_router(make_json_api_mirror_router(orders=order_repo, parties=party_repo))
    app.include_router(make_dataquality_router(dq=dq_repo, templates=templates))

    # 8. Web UI routers (no prefix — serve at root paths).
    init_modals(
        deps=_make_modal_deps(party_repo, profile_svc, app_user_repo),
        templates=templates,
    )
    app.include_router(modals_router)

    app.include_router(make_party_modals_router(
        templates=templates,
        profile=profile_svc,
        party_repo=party_repo,
        task_svc=task_svc,
        app_users=app_user_repo,
    ))

    app.include_router(make_worklist_router(
        templates=templates,
        action_queue=cache_repo,
        tasks=task_svc,
        task_writer=task_svc,
        action_state=action_state_repo,
    ))
    app.include_router(make_customer_list_router(
        templates=templates,
        parties=party_repo,
        customer_code_resolver=order_repo,
        sapo_id_resolver=party_repo,
        rfm_loader=list_rfm_repo,
        tier_loader=cache_repo,
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
        party_finder=party_repo,
        customer_code_resolver=order_repo,
        customer_timeline=timeline_repo,
        customer_orders=customer_orders_repo,
        customer_dim_metrics=dim_metrics_repo,
        task_svc=task_svc,
        app_users=app_user_repo,
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
    app.include_router(make_search_router(
        templates=templates,
        parties=party_repo,
        orders=order_repo,
    ))
    app.include_router(make_resolver_router(
        parties=party_repo,
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

    # 9. Hug stations — claim + mint — share one hug.db connection (single writer).
    #    Non-fatal: if hug.db can't open the rest of the CRM still serves.
    try:
        hug_conn = hug_db.connect()
        app.state.hug_conn = hug_conn  # keep alive for the app's lifetime
        app.include_router(make_hug_claim_router(hug_conn))
        app.include_router(make_hug_mint_router(hug_conn))
        # Review queue reads crm.db only; conn is the crm.db connection.
        app.include_router(make_hug_review_router(conn))
        # Campaign admin also uses crm.db (crm_hug_campaign lives there, not hug.db).
        campaign_router = make_hug_campaign_router(conn)
        assert campaign_router is not None, "make_hug_campaign_router returned None"
        app.include_router(campaign_router)
        log.info("hug stations mounted at /hug/claim, /hug/mint, /hug/review, /hug/campaigns")
    except Exception as exc:  # noqa: BLE001
        log.warning("hug stations unavailable (%s) — /hug/claim and /hug/mint disabled", exc)

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
