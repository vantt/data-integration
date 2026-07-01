"""Application service — ActivityService: log and retrieve activity touchpoints.

Pure domain + ports only; no adapter imports.
"""
from __future__ import annotations

import logging
import uuid
from shared.timestamps import utc_now
from typing import TYPE_CHECKING, Optional

from domain.entities.activity import Activity, VALID_ACTIVITY_TYPES
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
        )
        self._repo.insert(activity)
        # Keep last_contact snapshot in sync whenever outcome is recorded.
        if activity.outcome and self._last_contact_repo is not None:
            try:
                self._last_contact_repo.upsert(
                    party_id=activity.party_id,
                    activity_id=activity.activity_id,
                    contacted_at=activity.occurred_at,
                    result=activity.outcome,
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
