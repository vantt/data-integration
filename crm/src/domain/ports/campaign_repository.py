from __future__ import annotations

from typing import Optional, Protocol

from domain.entities.segment import Campaign, CampaignTarget


class CampaignRepository(Protocol):
    """Outbound port for crm_campaign + crm_campaign_target persistence."""

    def insert(self, campaign: Campaign) -> None:
        """Insert a new campaign row."""
        ...

    def get_by_id(self, campaign_id: str) -> Optional[Campaign]:
        """Return a campaign by primary key, or None if not found."""
        ...

    def update(self, campaign: Campaign) -> None:
        """Persist mutable campaign fields (name, objective, channel, segment_id, status, scheduled_at, updated_at)."""
        ...

    def list(self) -> list[Campaign]:
        """Return all campaigns ordered by created_at DESC."""
        ...

    def list_campaigns(self) -> list[Campaign]:
        """Return all campaigns ordered by created_at DESC (alias for list())."""
        ...

    def upsert_target(self, target: CampaignTarget) -> None:
        """Insert a campaign target; ON CONFLICT DO NOTHING (idempotent on PK)."""
        ...

    def update_target(self, target: CampaignTarget) -> None:
        """Persist mutable target fields (status, assigned_user_id, last_touch_at, converted_*)."""
        ...

    def get_target(self, campaign_id: str, party_id: str) -> Optional[CampaignTarget]:
        """Return a single target row, or None if not found."""
        ...

    def list_targets(
        self, campaign_id: str, status: Optional[str] = None, limit: int = 200
    ) -> list[CampaignTarget]:
        """Return targets for a campaign, optionally filtered by status, capped at limit."""
        ...

    def fetch_consent_map(self) -> dict:
        """Return {party_id: consent_value} from crm_customer_profile.consent_enum."""
        ...

    def find_earliest_order(
        self, party_id: str, scheduled_date_key: int
    ) -> tuple[str, int, str] | None:
        """Look up the earliest qualifying order for a party on or after scheduled_date_key.

        Returns (order_code, net_revenue_vnd, converted_at_iso) or None.
        """
        ...
