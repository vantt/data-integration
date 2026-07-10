"""Application service — ActivityService: log and retrieve activity touchpoints.

Pure domain + ports only; no adapter imports.
"""
from __future__ import annotations

import logging
import uuid
from shared.timestamps import utc_now
from typing import TYPE_CHECKING, Optional

from domain.entities.activity import (
    Activity,
    VALID_ACTIVITY_TYPES,
    CONTACT_OUTCOMES_BY_CHANNEL_TYPE,
    VALID_CONTACT_OUTCOMES,
    VALID_OUTCOME_REASONS,
    REASON_REQUIRED_OUTCOMES,
)
from domain.ports.activity_repository import ActivityRepository

if TYPE_CHECKING:
    from adapters.outbound.sqlite.connection import CRMDatabase

log = logging.getLogger(__name__)


class ActivityService:
    """Handles business logic for activity logging and timeline retrieval."""

    def __init__(
        self,
        activity_repo: ActivityRepository,
        last_contact_repo=None,
        db: Optional[CRMDatabase] = None,
    ) -> None:
        self._repo = activity_repo
        self._last_contact_repo = last_contact_repo
        self._db = db

    def log_activity(self, activity_data: dict) -> Activity:
        """Validate and store a new activity for a party. Returns the Activity."""
        party_id = activity_data.get("party_id") or ""
        if not party_id:
            raise ValueError("party_id is required")

        activity_type = (activity_data.get("activity_type") or "").strip()
        if not activity_type:
            raise ValueError("activity_type is required")
        if activity_type not in VALID_ACTIVITY_TYPES:
            raise ValueError(f"unknown activity_type {activity_type!r}")

        # D2 Phase 03: validate contact_outcome + outcome_reason enum
        contact_outcome = (activity_data.get("contact_outcome") or "").strip() or None
        outcome_reason  = (activity_data.get("outcome_reason") or "").strip() or None
        channel_type    = (activity_data.get("channel_type") or "").strip()

        if contact_outcome:
            valid_for_channel = CONTACT_OUTCOMES_BY_CHANNEL_TYPE.get(
                channel_type, VALID_CONTACT_OUTCOMES
            )
            if contact_outcome not in valid_for_channel:
                raise ValueError(
                    f"contact_outcome {contact_outcome!r} not valid for channel_type {channel_type!r}"
                )
            if contact_outcome in REASON_REQUIRED_OUTCOMES and not outcome_reason:
                raise ValueError("outcome_reason is required when contact_outcome is 'refused'")
            if outcome_reason and outcome_reason not in VALID_OUTCOME_REASONS:
                raise ValueError(f"unknown outcome_reason {outcome_reason!r}")
            # 'irritation' ("Tác dụng phụ") is a quality signal that must be escalated —
            # a body note describing what happened is mandatory, not just client-side.
            if outcome_reason == "irritation" and not (activity_data.get("body") or "").strip():
                raise ValueError("body is required when outcome_reason is 'irritation'")

        now = utc_now()
        activity = Activity(
            activity_id=activity_data.get("activity_id") or str(uuid.uuid4()),
            party_id=party_id,
            activity_type=activity_type,
            occurred_at=activity_data.get("occurred_at") or now,
            created_at=now,
            direction=activity_data.get("direction"),
            channel=activity_data.get("channel"),
            subject=activity_data.get("subject"),
            body=activity_data.get("body"),
            outcome=activity_data.get("outcome"),
            related_order_code=activity_data.get("related_order_code"),
            staff_user_id=activity_data.get("staff_user_id"),
            custom_fields=activity_data.get("custom_fields"),
            task_id=activity_data.get("task_id") or None,
            channel_type=channel_type or None,
            contact_outcome=contact_outcome,
            outcome_reason=outcome_reason,
        )
        self._repo.insert(activity)
        # Keep last_contact snapshot in sync whenever an outcome is recorded.
        # Prefer contact_outcome (D2 structured enum) over legacy free-text outcome.
        effective_outcome = activity.contact_outcome or activity.outcome
        if effective_outcome and self._last_contact_repo is not None:
            try:
                self._last_contact_repo.upsert(
                    party_id=activity.party_id,
                    activity_id=activity.activity_id,
                    contacted_at=activity.occurred_at,
                    result=effective_outcome,
                    channel=activity.channel,
                    staff_user_id=activity.staff_user_id,
                )
            except Exception as exc:
                log.warning("last_contact upsert %s: %s", activity.party_id, exc)
        # Single commit covers both activity insert and last_contact upsert atomically.
        if self._db:
            self._db.commit()
        return activity

    def list_activities(self, party_id: str, limit: int = 50) -> list[Activity]:
        """Return a party's activities newest-first."""
        if not party_id:
            raise ValueError("party_id is required")
        acts = self._repo.list_by_party(party_id)
        return acts[:limit]
