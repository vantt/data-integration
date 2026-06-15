"""WebDeps — dependency container for the CRM web adapter.

Ported from Go: crm/app/internal/adapters/inbound/web/deps.go

Holds all service / repository instances wired by the composition root
(main.py / app factory). Web handlers receive a WebDeps instance and call
only the methods they need — no direct imports of adapter concretes.

Fields mirror the Go Deps struct; Optional marks fields that may be absent
in lightweight deployments (e.g. order_repo requires DuckDB).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class WebDeps:
    # ── Party / profile ───────────────────────────────────────────────────────
    party_repo: Any = field(default=None)
    """PartyRepository: get_by_id, search_by_name, list_by_phone, list_all."""

    profile_svc: Any = field(default=None)
    """ProfileService: get_party_360, list_notes, add_note, upsert_profile."""

    # ── Tasks ─────────────────────────────────────────────────────────────────
    task_svc: Any = field(default=None)
    """TaskService: list_tasks, get_task, transition_status, create_task,
    generate_tasks_from_action_queue, list_by_party."""

    # ── Segments / campaigns ──────────────────────────────────────────────────
    segment_svc: Any = field(default=None)
    """SegmentService: list, get, create, update, refresh, list_members."""

    campaign_svc: Any = field(default=None)
    """CampaignService: list, get, create, update, targets, conversions, ROI."""

    # ── Conversations / inbox ─────────────────────────────────────────────────
    conv_svc: Any = field(default=None)
    """ConversationService: list_inbox, get_messages, assign, set_status."""

    # ── Activity timeline ─────────────────────────────────────────────────────
    activity_svc: Any = field(default=None)
    """ActivityService: list_timeline, log_activity."""

    # ── Caching / action queue ────────────────────────────────────────────────
    cache_repo: Any = field(default=None)
    """CacheRepository: list_all_action_queue, get_customer_insight."""

    # ── Dedup / merge ─────────────────────────────────────────────────────────
    dedup_repo: Any = field(default=None)
    """DedupRepository: list_candidates, get_candidate, update_candidate_status."""

    merge_svc: Any = field(default=None)
    """MergeService: merge(surviving_party_id, merged_party_id, reason, merged_by)."""

    # ── App users ─────────────────────────────────────────────────────────────
    app_user_repo: Any = field(default=None)
    """AppUserRepository: list_active (for assign-conversation dropdown)."""

    # ── Order detail (optional — requires DuckDB / olap.duckdb) ──────────────
    order_repo: Optional[Any] = field(default=None)
    """OrderRepository: get_by_code(order_code) → OrderDetail. May be None."""
