from __future__ import annotations

from typing import Protocol

from domain.entities.segment import Segment, SegmentMember
from domain.entities.campaign import Campaign, CampaignTarget


class SegmentRepository(Protocol):
    """Outbound port for Segment and SegmentMember persistence."""

    def insert(self, segment: Segment) -> None:
        """Store a new segment row."""
        ...

    def get_by_id(self, segment_id: str) -> Segment | None:
        """Return a segment by primary key, or None if not found."""
        ...

    def update(self, segment: Segment) -> None:
        """Persist mutable segment fields (name, description, is_dynamic,
        definition, owner_user_id)."""
        ...

    def list(self) -> list[Segment]:
        """Return all segments ordered by created_at DESC."""
        ...

    def upsert_member(self, member: SegmentMember) -> None:
        """Insert or update a segment member (idempotent on PK)."""
        ...

    def delete_member(self, segment_id: str, party_id: str) -> None:
        """Remove a party from a segment."""
        ...

    def list_members(self, segment_id: str) -> list[SegmentMember]:
        """Return all members of a segment."""
        ...

    def delete_rule_members(self, segment_id: str) -> None:
        """Remove all rule-sourced members from a segment.
        Called before re-evaluating a dynamic segment to purge stale members."""
        ...


class CampaignRepository(Protocol):
    """Outbound port for Campaign and CampaignTarget persistence."""

    def insert(self, campaign: Campaign) -> None:
        """Store a new campaign row."""
        ...

    def get_by_id(self, campaign_id: str) -> Campaign | None:
        """Return a campaign by primary key, or None if not found."""
        ...

    def update(self, campaign: Campaign) -> None:
        """Persist mutable campaign fields (name, objective, channel,
        segment_id, status, scheduled_at)."""
        ...

    def list(self) -> list[Campaign]:
        """Return all campaigns ordered by created_at DESC."""
        ...

    def upsert_target(self, target: CampaignTarget) -> None:
        """Insert or ignore a campaign target (idempotent on PK)."""
        ...

    def update_target(self, target: CampaignTarget) -> None:
        """Persist mutable target fields (status, assigned_user_id, last_touch_at,
        converted_order_code, converted_revenue_vnd, converted_at)."""
        ...

    def get_target(self, campaign_id: str, party_id: str) -> CampaignTarget | None:
        """Return a single target row, or None if not found."""
        ...

    def list_targets(self, campaign_id: str) -> list[CampaignTarget]:
        """Return all targets for a campaign."""
        ...

    def list_targets_by_campaign_and_status(
        self, campaign_id: str, status: str
    ) -> list[CampaignTarget]:
        """Return targets filtered by status (empty string = all)."""
        ...
