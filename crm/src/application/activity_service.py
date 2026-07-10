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
    ACTIVITY_TYPE_CALL,
    ACTIVITY_STATUS_DRAFT,
    ACTIVITY_STATUS_FINAL,
    DIRECTION_OUT,
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


class ActivityNotFoundError(Exception):
    """Raised by patch_activity/finalize_activity/get_activity when the id is unknown."""


class ActivityFinalizeConflictError(Exception):
    """Raised by finalize_activity when the activity has no contact_outcome yet.

    Maps to HTTP 409 at the route layer — the caller must PATCH an outcome onto
    the draft before it can be finalized (never auto-invent one; see decision
    "KHÔNG bao giờ tự bịa outcome").
    """


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

    def get_activity(self, activity_id: str) -> Optional[Activity]:
        """Return one activity by id, or None. Used by M08 edit_activity prefill."""
        if not activity_id:
            return None
        return self._repo.get_by_id(activity_id)

    # ── P1: draft lifecycle (create_draft → patch_activity* → finalize_activity) ──

    def create_draft(
        self,
        party_id: str,
        staff_user_id: str,
        *,
        channel_identity_id: Optional[str] = None,
        channel_value: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Activity:
        """Create (or adopt) the single open call draft for (staff, party).

        Idempotent by design: a second call with the same (staff, party) returns
        the SAME row rather than creating a new draft — "1 draft mở/(staff, party)"
        (see decision log). Triggered when staff presses "Gọi" on the identity bar,
        never on cockpit page load (no lazy/implicit draft creation).
        """
        if not party_id:
            raise ValueError("party_id is required")
        if not staff_user_id:
            raise ValueError("staff_user_id is required to own a draft")

        existing = self._repo.find_open_draft(staff_user_id, party_id)
        if existing is not None:
            return existing

        now = utc_now()
        custom_fields: Optional[dict] = None
        if channel_identity_id:
            custom_fields = {"channel_identity_id": channel_identity_id}
        activity = Activity(
            activity_id=str(uuid.uuid4()),
            party_id=party_id,
            activity_type=ACTIVITY_TYPE_CALL,
            occurred_at=now,
            created_at=now,
            direction=DIRECTION_OUT,
            channel=channel_value or None,
            channel_type=ACTIVITY_TYPE_CALL,
            staff_user_id=staff_user_id,
            task_id=task_id or None,
            custom_fields=custom_fields,
            status=ACTIVITY_STATUS_DRAFT,
            started_at=now,
        )
        self._repo.insert(activity)
        if self._db:
            self._db.commit()
        return activity

    def patch_activity(
        self,
        activity_id: str,
        fields: dict,
        actor_id: Optional[str] = None,
        *,
        is_edit_mode: bool = False,
    ) -> Activity:
        """Apply a subset of fields onto an existing activity. No side effects.

        `fields` may contain any of: contact_outcome, outcome_reason, body,
        related_order_code, occurred_at, custom_fields_patch (dict merged into the
        existing custom_fields, not replacing it — draft-creation may have already
        written channel_identity_id there).

        `is_edit_mode=True` marks this as an M08 "edit_activity" submission against
        an already-final activity — stamps an audit trail (edited_at/edited_by/
        previous_outcome) into custom_fields instead of silently overwriting mart
        source data (decision: "sửa tự do trong ngày... sau đó vẫn cho sửa nhưng
        ghi audit"). We audit every edit_activity PATCH of a final row, not only
        ones after the 02:30 ICT export cutoff — a strictly safer superset that
        avoids needing exact cutoff-time logic in P1.
        """
        activity = self._repo.get_by_id(activity_id)
        if activity is None:
            raise ActivityNotFoundError(f"activity {activity_id!r} not found")

        channel_type = activity.channel_type or ""
        next_outcome = fields.get("contact_outcome", activity.contact_outcome) \
            if "contact_outcome" in fields else activity.contact_outcome
        next_reason = fields.get("outcome_reason", activity.outcome_reason) \
            if "outcome_reason" in fields else activity.outcome_reason

        if "contact_outcome" in fields and next_outcome:
            valid_for_channel = CONTACT_OUTCOMES_BY_CHANNEL_TYPE.get(
                channel_type, VALID_CONTACT_OUTCOMES
            )
            if next_outcome not in valid_for_channel:
                raise ValueError(
                    f"contact_outcome {next_outcome!r} not valid for channel_type {channel_type!r}"
                )
        if next_outcome in REASON_REQUIRED_OUTCOMES and not next_reason:
            raise ValueError("outcome_reason is required when contact_outcome is 'refused'")
        if next_reason and next_reason not in VALID_OUTCOME_REASONS:
            raise ValueError(f"unknown outcome_reason {next_reason!r}")
        next_body = fields.get("body", activity.body) if "body" in fields else activity.body
        if next_reason == "irritation" and not (next_body or "").strip():
            raise ValueError("body is required when outcome_reason is 'irritation'")

        custom_fields = dict(activity.custom_fields) if activity.custom_fields else {}
        custom_patch = fields.get("custom_fields_patch")
        if custom_patch:
            for k, v in custom_patch.items():
                if v is None:
                    custom_fields.pop(k, None)
                else:
                    custom_fields[k] = v

        if is_edit_mode and activity.status == ACTIVITY_STATUS_FINAL and (
            "contact_outcome" in fields and fields["contact_outcome"] != activity.contact_outcome
        ):
            custom_fields["edited_at"] = utc_now()
            custom_fields["edited_by"] = actor_id
            custom_fields["previous_outcome"] = activity.contact_outcome

        if "contact_outcome" in fields:
            activity.contact_outcome = fields["contact_outcome"]
        if "outcome_reason" in fields:
            activity.outcome_reason = fields["outcome_reason"]
        if "body" in fields:
            activity.body = fields["body"]
        if "related_order_code" in fields:
            activity.related_order_code = fields["related_order_code"]
        if "occurred_at" in fields and fields["occurred_at"]:
            activity.occurred_at = fields["occurred_at"]
        activity.custom_fields = custom_fields or None

        self._repo.update(activity)
        if self._db:
            self._db.commit()
        return activity

    def finalize_activity(
        self,
        activity_id: str,
        *,
        contact_duration_s_override: Optional[int] = None,
    ) -> tuple[Activity, bool]:
        """Finalize a draft: stamps status=final + finalize_at + contact_duration_s.

        Returns (activity, already_finalized). Idempotent — calling finalize twice
        on the same activity_id does NOT re-run and returns already_finalized=True
        so the caller (route layer) can skip side effects on the second call.
        Raises ActivityFinalizeConflictError (→ 409) when contact_outcome is still
        empty — never invents one.
        """
        activity = self._repo.get_by_id(activity_id)
        if activity is None:
            raise ActivityNotFoundError(f"activity {activity_id!r} not found")

        if activity.status == ACTIVITY_STATUS_FINAL:
            return activity, True

        if not activity.contact_outcome:
            raise ActivityFinalizeConflictError(
                "contact_outcome is required before an activity can be finalized"
            )

        now = utc_now()
        duration = contact_duration_s_override
        if duration is None and activity.started_at:
            started = _parse_utc_iso(activity.started_at)
            ended = _parse_utc_iso(now)
            if started is not None and ended is not None:
                duration = max(0, int((ended - started).total_seconds()))

        activity.status = ACTIVITY_STATUS_FINAL
        activity.finalize_at = now
        activity.contact_duration_s = duration
        self._repo.update(activity)

        # Keep last_contact snapshot in sync — deferred to finalize (not PATCH) so a
        # draft that gets re-patched with a different outcome before finalizing
        # doesn't leave a stale/incorrect last_contact row behind.
        if self._last_contact_repo is not None:
            try:
                self._last_contact_repo.upsert(
                    party_id=activity.party_id,
                    activity_id=activity.activity_id,
                    contacted_at=activity.occurred_at,
                    result=activity.contact_outcome,
                    channel=activity.channel,
                    staff_user_id=activity.staff_user_id,
                )
            except Exception as exc:
                log.warning("finalize_activity: last_contact upsert %s: %s", activity.party_id, exc)

        if self._db:
            self._db.commit()
        return activity, False


def _parse_utc_iso(value: str):
    """Parse a utc_now()-formatted string (2026-06-29T10:30:00.123Z) into datetime.

    Returns None on any parse failure (defensive — never raises, duration just
    stays unset in that case).
    """
    from datetime import datetime
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except (ValueError, TypeError):
        return None
