"""Composition root — the ONLY place that wires adapters to ports for the CRM Python server.

Mirrors the wiring order in crm/src/cmd/server/main.go.
All concrete adapter imports live here; the rest of the codebase depends on
protocols/ports only.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
import sqlite3
from typing import Optional, TypedDict

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from adapters.inbound.web.templating import make_templates

from config import (
    crm_db_path,
    olap_path,
    refresh_token,
    server_port,
    cf_team_domain,
)

# ── Outbound: SQLite ──────────────────────────────────────────────────────────
from adapters.outbound.sqlite.connection import CRMDatabase
from adapters.outbound.sqlite.hug_campaign_repository_adapter import HugCampaignRepositoryAdapter
from adapters.outbound.sqlite.hug_voucher_repository_adapter import HugVoucherRepositoryAdapter
from adapters.outbound.sqlite.hug_token_repository import HugTokenRepository
from adapters.outbound.sqlite.party_repository import SQLitePartyRepository
from adapters.outbound.sqlite.dedup_repository import SQLiteDedupRepository
from adapters.outbound.sqlite.profile_repository import SQLiteProfileRepository
from adapters.outbound.sqlite.custom_field_repository import SQLiteCustomFieldRepository
from adapters.outbound.sqlite.tag_note_repository import SQLiteTagRepository, SQLiteNoteRepository
from adapters.outbound.sqlite.cache_repository import SQLiteCacheRepository
from adapters.outbound.sqlite.action_state_repository import SQLiteActionStateRepository
from adapters.outbound.sqlite.activity_repository import SQLiteActivityRepository
from adapters.outbound.sqlite.last_contact_repository import SQLiteLastContactRepository
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
from adapters.outbound.duckdb.staff_id_resolver import StaffIdResolver

# ── Application services ──────────────────────────────────────────────────────
from application.merge_service import MergeService
from application.party_seed_service import PartySeedService
from application.profile_service import ProfileService
from application.note_service import NoteService
from application.tag_service import TagService
from application.custom_field_service import CustomFieldService
from application.activity_service import ActivityService
from application.task_service import TaskService
from application.conversation_service import ConversationService
from application.segment_service import SegmentService
from application.campaign_service import CampaignService
from application.app_user_service import AppUserService
from application.worklist_query_service import WorklistQueryService
from application.customer_list_query_service import CustomerListQueryService

# ── Inbound: HTTP API handlers ────────────────────────────────────────────────
from adapters.inbound.http.health_handler import create_health_router
from adapters.inbound.http.admin_handler import create_admin_router
from adapters.inbound.http.dedup_handler import make_dedup_router
from adapters.inbound.http.customer360_handler import make_customer360_router
from adapters.inbound.http.insight_handler import make_insight_router
from adapters.inbound.http.activity_handler import make_activity_router
from adapters.inbound.http.task_handler import make_task_router
from adapters.inbound.http.conversation_handler import make_conversation_router
from adapters.inbound.http.debug_handler import make_debug_router
from adapters.inbound.http.segment_handler import make_segment_router
from adapters.inbound.http.campaign_handler import make_campaign_router
from adapters.inbound.http.json_api_mirror_handler import make_json_api_mirror_router
from adapters.inbound.http.dataquality_handler import make_dataquality_router
from adapters.inbound.http.approach_script_handler import make_approach_script_router
from adapters.inbound.http.script_nav_handler import make_script_nav_router
from adapters.inbound.http.cf_access_middleware import CFAccessMiddleware

# ── Outbound: File ────────────────────────────────────────────────────────────
from adapters.outbound.file.approach_script_file_repository import FileApproachScriptRepository

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
from adapters.inbound.web.screens.modals.screen_modals import init_modals, router as modals_router
from adapters.inbound.web.screens.modals.screen_modals_party import make_party_modals_router
from adapters.inbound.web.screen_worklist import make_worklist_router
from adapters.inbound.web.screen_customer_list import make_customer_list_router
from adapters.inbound.web.screens.customer360.screen_customer_360 import make_customer_360_router
from adapters.inbound.web.screen_tasks_board import make_tasks_board_router
from adapters.inbound.web.screen_inbox import make_inbox_router
from adapters.inbound.web.screen_order_detail import make_order_detail_router
from adapters.inbound.web.screens.management.screen_management import make_management_router
from adapters.inbound.web.screen_search import make_search_router
from adapters.inbound.web.screen_resolver import make_resolver_router
from adapters.inbound.web.screens.hug.screen_hug_claim import make_hug_claim_router
from adapters.inbound.web.screens.hug.screen_hug_mint import make_hug_mint_router
from adapters.inbound.web.screens.hug.screen_hug_review import make_hug_review_router
from adapters.inbound.web.screens.hug.screen_hug_campaign import make_hug_campaign_router
from adapters.inbound.web.screens.hug.screen_hug_voucher_attribution import make_hug_voucher_attribution_router

# ── Hug — local token-provisioning master (separate Python-owned hug.db) ──────
from hug import db as hug_db

log = logging.getLogger(__name__)


class SqliteRepos(TypedDict):
    """All SQLite-backed repositories plus the raw connection and database handle."""
    db: CRMDatabase
    conn: sqlite3.Connection
    party: SQLitePartyRepository
    dedup: SQLiteDedupRepository
    cache: SQLiteCacheRepository
    action_state: SQLiteActionStateRepository
    profile: SQLiteProfileRepository
    cf: SQLiteCustomFieldRepository
    tag: SQLiteTagRepository
    note: SQLiteNoteRepository
    activity: SQLiteActivityRepository
    last_contact: SQLiteLastContactRepository
    task: SQLiteTaskRepository
    conv: SQLiteConversationRepository
    segment: SQLiteSegmentRepository
    campaign: SQLiteCampaignRepository
    app_user: SQLiteAppUserRepository
    approach: FileApproachScriptRepository


class DuckdbRepos(TypedDict):
    """All DuckDB-backed repositories — Optional because olap.duckdb may be absent."""
    orders: Optional[DuckDBOrderRepository]
    timeline: Optional[CustomerTimelineRepository]
    customer_orders: Optional[CustomerOrdersRepository]
    dim_metrics: Optional[CustomerDimMetricsRepository]
    list_rfm: Optional[CustomerListRFMRepository]
    dq: Optional[DataQualityRepository]


class Services(TypedDict):
    """All application-layer services wired from SQLite repositories."""
    merge: MergeService
    profile: ProfileService
    note: NoteService
    tag: TagService
    cf: CustomFieldService
    activity: ActivityService
    task: TaskService
    conv: ConversationService
    segment: SegmentService
    campaign: CampaignService
    app_user: AppUserService


# Paths relative to this file (crm/src/).
_THIS_DIR = Path(__file__).parent
_TEMPLATES_DIR = _THIS_DIR / "adapters" / "inbound" / "web" / "templates"
_STATIC_DIR = _THIS_DIR / "adapters" / "inbound" / "web" / "static"


def _resolve_static_dir() -> Optional[Path]:
    if _STATIC_DIR.exists():
        return _STATIC_DIR
    return None


# ── Public entry point ────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Wire all dependencies and return a ready-to-serve FastAPI application."""
    db = _setup_database()
    sqlite_repos: SqliteRepos = _build_sqlite_repos(db)
    duckdb_repos: DuckdbRepos = _build_duckdb_repos(olap_path())
    services: Services = _build_services(sqlite_repos)
    app = FastAPI(title="CRM", docs_url="/api/docs", redoc_url=None)
    _configure_middleware(app, services["app_user"])
    templates = _configure_templates(app)
    _register_api_routes(app, sqlite_repos, duckdb_repos, services, templates)
    _register_web_routes(app, sqlite_repos, duckdb_repos, services, templates)
    _mount_hug_stations(app, sqlite_repos["conn"])
    return app


# ── Private sub-functions ─────────────────────────────────────────────────────

def _setup_database() -> CRMDatabase:
    """Open CRMDatabase (crm.db with cache.db ATTACHed) and apply migrations."""
    data_dir = os.path.dirname(crm_db_path())
    db = CRMDatabase(data_dir)
    db.apply_migrations()
    log.info("migrations applied")
    return db


def _build_sqlite_repos(db: CRMDatabase) -> SqliteRepos:
    """Instantiate all SQLite repositories and return as a named dict.

    Includes ``conn`` (raw SQLite connection) and ``db`` (CRMDatabase) so
    callers needing either handle can access them without re-opening.
    ``approach`` (FileApproachScriptRepository) is bundled here for colocation
    with the other repo objects even though it is file-backed.
    """
    conn = db.conn
    data_dir = os.path.dirname(crm_db_path())
    scripts_dir = os.getenv(
        "CRM_APPROACH_SCRIPT_DIR",
        os.path.join(data_dir, "approach_scripts"),
    )
    return {
        "db": db,
        "conn": conn,
        "party": SQLitePartyRepository(conn),
        "dedup": SQLiteDedupRepository(conn),
        "cache": SQLiteCacheRepository(conn),
        "action_state": SQLiteActionStateRepository(conn),
        "profile": SQLiteProfileRepository(db),
        "cf": SQLiteCustomFieldRepository(db),
        "tag": SQLiteTagRepository(db),
        "note": SQLiteNoteRepository(db),
        "activity": SQLiteActivityRepository(db),
        "last_contact": SQLiteLastContactRepository(db),
        "task": SQLiteTaskRepository(db),
        "conv": SQLiteConversationRepository(db),
        "segment": SQLiteSegmentRepository(conn),
        "campaign": SQLiteCampaignRepository(conn),
        "app_user": SQLiteAppUserRepository(conn),
        "approach": FileApproachScriptRepository(scripts_dir),
    }


def _build_duckdb_repos(olap: str) -> DuckdbRepos:
    """Instantiate DuckDB repositories — non-fatal if olap.duckdb is unavailable.

    All values are Optional; callers must handle None (handlers return 503).
    """
    order_repo: Optional[DuckDBOrderRepository] = None
    try:
        order_repo = DuckDBOrderRepository(olap)
        log.info("order repo: olap.duckdb mounted at %s", olap)
    except Exception as exc:
        log.warning("order repo unavailable (%s) — /orders/* will return 503", exc)

    timeline_repo: Optional[CustomerTimelineRepository] = None
    try:
        timeline_repo = CustomerTimelineRepository(olap)
    except Exception as exc:
        log.warning("timeline repo unavailable (%s) — status_history panel will return 503", exc)

    customer_orders_repo: Optional[CustomerOrdersRepository] = None
    try:
        customer_orders_repo = CustomerOrdersRepository(olap)
    except Exception as exc:
        log.warning("customer_orders repo unavailable (%s) — orders panel falls back to cache", exc)

    dim_metrics_repo: Optional[CustomerDimMetricsRepository] = None
    try:
        dim_metrics_repo = CustomerDimMetricsRepository(olap)
    except Exception as exc:
        log.warning("dim_metrics repo unavailable (%s) — insight panel segments/profitability hidden", exc)

    list_rfm_repo: Optional[CustomerListRFMRepository] = None
    try:
        list_rfm_repo = CustomerListRFMRepository(olap)
    except Exception as exc:
        log.warning("list_rfm repo unavailable (%s) — Recency/Frequency/customer_type hidden in S02", exc)

    dq_repo: Optional[DataQualityRepository] = None
    try:
        dq_repo = DataQualityRepository(olap)
    except Exception as exc:
        log.warning("dq repo unavailable (%s) — /_dq_strip will return empty", exc)

    return {
        "orders": order_repo,
        "timeline": timeline_repo,
        "customer_orders": customer_orders_repo,
        "dim_metrics": dim_metrics_repo,
        "list_rfm": list_rfm_repo,
        "dq": dq_repo,
    }


def _build_services(sqlite_repos: SqliteRepos) -> Services:
    """Instantiate all application services from SQLite repository objects."""
    db = sqlite_repos["db"]
    return {
        "merge": MergeService(sqlite_repos["party"], sqlite_repos["dedup"]),
        "profile": ProfileService(
            sqlite_repos["profile"],
            sqlite_repos["cf"],
            db,
        ),
        "note": NoteService(sqlite_repos["note"], db),
        "tag": TagService(sqlite_repos["tag"], db),
        "cf": CustomFieldService(sqlite_repos["cf"], db),
        "activity": ActivityService(sqlite_repos["activity"], sqlite_repos["last_contact"], db),
        "task": TaskService(sqlite_repos["task"], sqlite_repos["cache"], db),
        "conv": ConversationService(sqlite_repos["conv"], sqlite_repos["party"], db),
        "segment": SegmentService(sqlite_repos["segment"]),
        "campaign": CampaignService(
            sqlite_repos["campaign"],
            sqlite_repos["segment"],
            sqlite_repos["party"],
        ),
        "app_user": AppUserService(
            sqlite_repos["app_user"],
            staff_resolver=StaffIdResolver(olap_path()) if olap_path() else None,
        ),
    }


def _make_sync_parties_runner():
    """Return a plain callable that runs sync_parties (used with run_in_executor).

    Keeps concrete outbound-adapter wiring inside the composition root so that
    the admin inbound adapter never imports from adapters.outbound.*.
    """
    def _run() -> None:
        import os as _os
        data_dir = _os.environ.get("CRM_DATA_DIR", "./data")
        db = CRMDatabase(data_dir)
        try:
            db.apply_migrations()
            party_repo = SQLitePartyRepository(db.conn)
            cache_repo = SQLiteCacheRepository(db.conn)
            svc = PartySeedService(cache_repo, party_repo)
            n = svc.sync_parties(cache_repo)
            log.info("syncparties: %d parties upserted", n)
        finally:
            db.close()

    return _run


def _configure_middleware(app: FastAPI, app_user_svc: AppUserService) -> None:
    """Add CFAccessMiddleware to the FastAPI application."""
    app.add_middleware(CFAccessMiddleware, user_svc=app_user_svc)


def _configure_templates(app: FastAPI):  # returns Jinja2Templates
    """Build Jinja2Templates, register all filters/globals, and mount /static."""
    templates = make_templates(str(_TEMPLATES_DIR))
    templates.env.globals["cf_team_domain"] = cf_team_domain()
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
    return templates


class _ProfileTagCFComposite:
    """Composite adapter satisfying both the ProfileSvc protocol (party modals)
    and the settings_svc duck-type (management screen).

    Delegates each method group to the matching application service so that
    screens using a combined protocol receive a single object without requiring
    ProfileService to know about tags or custom-field definitions.
    """

    def __init__(
        self,
        profile_svc: ProfileService,
        tag_svc: TagService,
        cf_svc: CustomFieldService,
    ) -> None:
        self._profile = profile_svc
        self._tags = tag_svc
        self._cf = cf_svc

    # --- ProfileService delegates ---
    def get_party_360(self, party_id):
        return self._profile.get_party_360(party_id)

    def upsert_profile(self, party_id, **kwargs):
        return self._profile.upsert_profile(party_id, **kwargs)

    # --- TagService delegates ---
    def list_tags(self, category):
        return self._tags.list_tags(category)

    def list_party_tags(self, party_id):
        return self._tags.list_party_tags(party_id)

    def attach_tag(self, party_id, tag_id, user_id=None):
        return self._tags.attach_tag(party_id, tag_id, user_id)

    def detach_tag(self, party_id, tag_id):
        return self._tags.detach_tag(party_id, tag_id)

    def get_tag(self, tag_id):
        return self._tags.get_tag(tag_id)

    def create_tag(self, name, category, color, display_label=""):
        return self._tags.create_tag(name, category, color, display_label)

    def update_tag(self, tag_id, name, category, color, display_label=""):
        return self._tags.update_tag(tag_id, name, category, color, display_label)

    def delete_tag(self, tag_id):
        return self._tags.delete_tag(tag_id)

    # --- CustomFieldService delegates ---
    def list_custom_field_defs(self, entity_type=None):
        return self._cf.list_custom_field_defs(entity_type)

    def get_custom_field_def(self, field_id):
        return self._cf.get_custom_field_def(field_id)

    def create_custom_field_def(self, **kwargs):
        from domain.entities.profile import CustomFieldDef
        defn = CustomFieldDef(
            field_id=kwargs.get("field_id", ""),
            entity_type=kwargs.get("entity_type", "party"),
            field_key=kwargs.get("field_key", ""),
            label=kwargs.get("label", ""),
            data_type=kwargs.get("data_type", "text"),
            is_required=kwargs.get("is_required", False),
            is_active=kwargs.get("is_active", True),
            sort_order=kwargs.get("sort_order", 0),
            options=kwargs.get("options"),
            section=kwargs.get("section"),
        )
        return self._cf.create_custom_field_def(defn)

    def update_custom_field_def(self, field_id, **kwargs):
        return self._cf.update_custom_field_def(field_id, **kwargs)


def _register_api_routes(
    app: FastAPI,
    sqlite_repos: SqliteRepos,
    duckdb_repos: DuckdbRepos,
    services: Services,
    templates,
) -> None:
    """Register all HTTP API routers (prefix=/api already set per handler)."""
    app.include_router(create_health_router(sqlite_repos["db"]))
    app.include_router(create_admin_router(sync_parties_runner=_make_sync_parties_runner()))
    app.include_router(make_insight_router(sqlite_repos["party"], sqlite_repos["cache"]))
    app.include_router(make_approach_script_router(sqlite_repos["party"], sqlite_repos["approach"]))
    app.include_router(make_script_nav_router(sqlite_repos["party"], sqlite_repos["approach"], templates))
    app.include_router(make_activity_router(services["activity"]))
    app.include_router(make_task_router(services["task"]))

    app.include_router(make_debug_router(services["app_user"]))
    app.include_router(make_conversation_router(services["conv"]))
    app.include_router(make_dedup_router(sqlite_repos["dedup"], services["merge"]))
    app.include_router(make_customer360_router(
        profile_q=services["profile"],
        profile_w=services["profile"],
        tags=services["tag"],
        notes=services["note"],
        cf_admin=services["cf"],
        party_lookup=sqlite_repos["party"],
        insight_q=sqlite_repos["cache"],
    ))
    app.include_router(make_segment_router(services["segment"]))
    app.include_router(make_campaign_router(services["campaign"]))
    app.include_router(make_json_api_mirror_router(
        orders=duckdb_repos["orders"],
        parties=sqlite_repos["party"],
    ))
    app.include_router(make_dataquality_router(dq=duckdb_repos["dq"], templates=templates))


def _register_web_routes(
    app: FastAPI,
    sqlite_repos: SqliteRepos,
    duckdb_repos: DuckdbRepos,
    services: Services,
    templates,
) -> None:
    """Register all Web UI screen routers (served at root paths, no /api prefix)."""
    init_modals(
        deps=_make_modal_deps(
            sqlite_repos["party"],
            services["profile"],
            services["activity"],
            sqlite_repos["app_user"],
        ),
        templates=templates,
    )
    app.include_router(modals_router)

    _profile_cf_tag = _ProfileTagCFComposite(services["profile"], services["tag"], services["cf"])
    app.include_router(make_party_modals_router(
        templates=templates,
        profile=_profile_cf_tag,
        party_repo=sqlite_repos["party"],
        task_svc=services["task"],
        app_users=sqlite_repos["app_user"],
    ))
    worklist_svc = WorklistQueryService(
        action_queue=sqlite_repos["cache"],
        last_contact=sqlite_repos["last_contact"],
    )
    app.include_router(make_worklist_router(
        templates=templates,
        worklist_svc=worklist_svc,
        tasks=services["task"],
        task_writer=services["task"],
        action_state=sqlite_repos["action_state"],
    ))
    customer_list_svc = CustomerListQueryService(
        parties=sqlite_repos["party"],
        rfm_loader=duckdb_repos["list_rfm"],
        tier_loader=sqlite_repos["cache"],
    )
    app.include_router(make_customer_list_router(
        templates=templates,
        customer_list_svc=customer_list_svc,
        customer_code_resolver=duckdb_repos["orders"],
    ))
    app.include_router(make_customer_360_router(
        templates=templates,
        profile=services["profile"],
        identities=sqlite_repos["party"],
        insight=sqlite_repos["cache"],
        activities=services["activity"],
        activity_log=services["activity"],
        notes=services["note"],
        party_tasks=sqlite_repos["task"],
        party_finder=sqlite_repos["party"],
        customer_code_resolver=duckdb_repos["orders"],
        customer_timeline=duckdb_repos["timeline"],
        customer_orders=duckdb_repos["customer_orders"],
        customer_dim_metrics=duckdb_repos["dim_metrics"],
        task_svc=services["task"],
        app_users=sqlite_repos["app_user"],
        approach_repo=sqlite_repos["approach"],
    ))
    app.include_router(make_tasks_board_router(
        templates=templates,
        task_querier=services["task"],
        task_writer=services["task"],
        task_creator=services["task"],
        task_generator=services["task"],
    ))
    app.include_router(make_inbox_router(
        templates=templates,
        conversations=services["conv"],
        conv_reader=sqlite_repos["conv"],
        conv_writer=services["conv"],
        parties=sqlite_repos["party"],
        app_users=sqlite_repos["app_user"],
        activity_log=services["activity"],
    ))
    app.include_router(make_order_detail_router(
        templates=templates,
        orders=duckdb_repos["orders"],
    ))
    app.include_router(make_search_router(
        templates=templates,
        parties=sqlite_repos["party"],
        orders=duckdb_repos["orders"],
    ))
    app.include_router(make_resolver_router(
        parties=sqlite_repos["party"],
        orders=duckdb_repos["orders"],
    ))
    app.include_router(make_management_router(
        templates=templates,
        segments_svc=services["segment"],
        campaigns_svc=services["campaign"],
        dedup_svc=sqlite_repos["dedup"],
        merger_svc=services["merge"],
        parties_svc=sqlite_repos["party"],
        settings_svc=_profile_cf_tag,
        app_users_svc=sqlite_repos["app_user"],
    ))


def _mount_hug_stations(app: FastAPI, conn) -> None:
    """Mount hug station routers — non-fatal if hug.db cannot be opened.

    ``conn`` is the crm.db SQLite connection used by review/campaign/attribution
    screens that read crm_hug_* tables (not hug.db).
    """
    try:
        hug_conn = hug_db.connect()
        app.state.hug_conn = hug_conn  # keep alive for the app's lifetime
        hug_token_repo = HugTokenRepository(hug_conn)
        app.include_router(make_hug_claim_router(hug_token_repo))
        app.include_router(make_hug_mint_router(hug_token_repo))
        # Review queue reads crm.db only; conn is the crm.db connection.
        app.include_router(make_hug_review_router(conn))
        # Campaign admin also uses crm.db (crm_hug_campaign lives there, not hug.db).
        campaign_router = make_hug_campaign_router(HugCampaignRepositoryAdapter(conn))
        if campaign_router is None:
            raise RuntimeError("make_hug_campaign_router returned None")
        app.include_router(campaign_router)
        # Attribution readout — crm.db only; read-only screen.
        attribution_router = make_hug_voucher_attribution_router(HugVoucherRepositoryAdapter(conn))
        if attribution_router is None:
            raise RuntimeError("make_hug_voucher_attribution_router returned None")
        app.include_router(attribution_router)
        log.info("hug stations mounted at /hug/claim, /hug/mint, /hug/review, /hug/campaigns, /hug/vouchers")
    except Exception as exc:  # noqa: BLE001
        log.warning("hug stations unavailable (%s) — /hug/claim and /hug/mint disabled", exc)


# ── Helpers ───────────────────────────────────────────────────────────────────

class _ModalDeps:
    """Thin struct satisfying screen_modals.WebDeps protocol."""
    def __init__(self, party_creator, profile_querier, owner_assigner, activity_logger, app_users):
        self.party_creator = party_creator
        self.profile_querier = profile_querier
        self.owner_assigner = owner_assigner
        self.activity_logger = activity_logger
        self.app_users = app_users


def _make_modal_deps(party_repo, profile_svc, activity_svc, app_user_repo) -> _ModalDeps:
    return _ModalDeps(
        party_creator=party_repo,
        profile_querier=profile_svc,
        owner_assigner=profile_svc,
        activity_logger=activity_svc,
        app_users=app_user_repo,
    )
