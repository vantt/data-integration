"""CampaignService: campaign CRUD, target generation, conversion scanning, ROI summary.

Pure domain + ports only; no adapter imports.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from shared.timestamps import utc_now

from domain.ports.campaign_repository import CampaignRepository
from domain.entities.segment import (
    VALID_CAMPAIGN_OBJECTIVES,
    VALID_TARGET_STATUSES,
    TARGET_TERMINAL_STATUSES,
    CAMPAIGN_ALLOWED_TRANSITIONS,
    TARGET_ALLOWED_TRANSITIONS,
    Campaign,
    CampaignTarget,
    CampaignROI,
)

# ICT = Asia/Ho_Chi_Minh (UTC+7, no DST). Matches wh_order_hdr.date_key semantics.
_ICT = timezone(timedelta(hours=7))


def _today_ict_date_key() -> int:
    """Return today's date as ICT YYYYMMDD integer."""
    return _time_to_date_key(datetime.now(_ICT))


def _time_to_date_key(dt: datetime) -> int:
    return int(dt.strftime("%Y%m%d"))


def _date_to_ict_key(ts: str) -> int:
    """Parse an ISO-8601 / RFC3339 string and return its ICT date as YYYYMMDD int."""
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return _time_to_date_key(datetime.strptime(ts, fmt).astimezone(_ICT))
        except ValueError:
            pass
    # Fallback: treat first 10 chars as YYYY-MM-DD literal.
    if len(ts) >= 10:
        return int(ts[:4] + ts[5:7] + ts[8:10])
    return 0


def _is_missing_table_error(exc: Exception) -> bool:
    return "no such table" in str(exc).lower()


class CampaignService:
    """Handles campaign lifecycle, target management, conversion scanning, and ROI."""

    def __init__(
        self,
        campaign_repo: CampaignRepository,
        segment_repo: Any,
        party_repo: Any,
    ) -> None:
        self._campaign_repo = campaign_repo
        self._segment_repo = segment_repo
        self._party_repo = party_repo

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create_campaign(self, data: dict) -> Campaign:
        """Validate and store a new campaign. Returns the created Campaign."""
        import uuid
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("campaign name is required")
        objective = data.get("objective", "")
        if objective not in VALID_CAMPAIGN_OBJECTIVES:
            raise ValueError(
                f"invalid objective {objective!r} — must be one of: "
                + ", ".join(VALID_CAMPAIGN_OBJECTIVES)
            )
        now = utc_now()
        c = Campaign(
            campaign_id=data.get("campaign_id") or str(uuid.uuid4()),
            name=name,
            objective=objective,
            channel=data.get("channel", ""),
            status=data.get("status") or "draft",
            created_at=now,
            updated_at=now,
            segment_id=data.get("segment_id"),
            scheduled_at=data.get("scheduled_at"),
            created_by=data.get("created_by"),
        )
        self._campaign_repo.insert(c)
        return c

    def update_campaign(self, campaign_id: str, **kwargs: Any) -> None:
        """Apply mutable field changes with status-transition validation."""
        c = self._campaign_repo.get_by_id(campaign_id)
        if c is None:
            raise ValueError(f"campaign {campaign_id!r} not found")
        if "status" in kwargs and kwargs["status"] != c.status:
            new_status = kwargs["status"]
            allowed = CAMPAIGN_ALLOWED_TRANSITIONS.get(c.status, [])
            if new_status not in allowed:
                raise ValueError(
                    f"cannot transition campaign from {c.status!r} to {new_status!r}"
                )
            c.status = new_status
        if "name" in kwargs:
            c.name = kwargs["name"]
        if "objective" in kwargs:
            obj = kwargs["objective"]
            if obj not in VALID_CAMPAIGN_OBJECTIVES:
                raise ValueError(f"invalid objective {obj!r}")
            c.objective = obj
        if "channel" in kwargs:
            c.channel = kwargs["channel"]
        if "segment_id" in kwargs:
            c.segment_id = kwargs["segment_id"]
        if "scheduled_at" in kwargs:
            c.scheduled_at = kwargs["scheduled_at"]
        c.updated_at = utc_now()
        self._campaign_repo.update(c)

    def get_campaign(self, campaign_id: str) -> Campaign | None:
        """Return a campaign by ID, or None if not found."""
        return self._campaign_repo.get_by_id(campaign_id)

    def list_campaigns(self) -> list[Campaign]:
        """Return all campaigns."""
        return self._campaign_repo.list()

    # ── Targets ────────────────────────────────────────────────────────────────

    def generate_targets(self, campaign_id: str) -> int:
        """Create campaign_target rows from the campaign's segment members.

        COMPLIANCE: parties with consent_contact='denied' are excluded; NULL/na are allowed through.
        Idempotent: existing targets are left unchanged (upsert-ignore semantics).
        Returns the count of targets created (skips already-existing rows).
        """
        c = self._campaign_repo.get_by_id(campaign_id)
        if c is None:
            raise ValueError(f"campaign {campaign_id!r} not found")
        if not c.segment_id:
            raise ValueError("campaign has no segment")

        members = self._segment_repo.list_members(c.segment_id)
        consent_map = self._fetch_consent_map()

        created = 0
        for m in members:
            if consent_map.get(m.party_id) == "denied":
                continue
            self._campaign_repo.upsert_target(
                CampaignTarget(
                    campaign_id=campaign_id,
                    party_id=m.party_id,
                    status="queued",
                )
            )
            created += 1
        return created

    def update_target(self, campaign_id: str, party_id: str, **kwargs: Any) -> None:
        """Apply status transition or field update to a campaign target."""
        t = self._campaign_repo.get_target(campaign_id, party_id)
        if t is None:
            raise ValueError(f"target ({campaign_id}, {party_id}) not found")
        if "status" in kwargs:
            new_status = kwargs["status"]
            if new_status not in VALID_TARGET_STATUSES:
                raise ValueError(f"invalid target status {new_status!r}")
            allowed = TARGET_ALLOWED_TRANSITIONS.get(t.status, [])
            if new_status not in allowed:
                raise ValueError(
                    f"cannot transition target from {t.status!r} to {new_status!r}"
                )
            t.status = new_status
            t.last_touch_at = utc_now()
        if "assigned_user_id" in kwargs:
            t.assigned_user_id = kwargs["assigned_user_id"]
        self._campaign_repo.update_target(t)

    def get_target(self, campaign_id: str, party_id: str) -> CampaignTarget | None:
        """Return a single campaign target, or None if not found."""
        return self._campaign_repo.get_target(campaign_id, party_id)

    def update_target_status(
        self, campaign_id: str, party_id: str, status: str
    ) -> None:
        """Transition a target to a new status with validation."""
        self.update_target(campaign_id, party_id, status=status)

    def record_conversion(
        self,
        campaign_id: str,
        party_id: str,
        order_code: str | None = None,
        revenue_vnd: int | None = None,
    ) -> None:
        """Manually mark a target as converted with optional order details."""
        t = self._campaign_repo.get_target(campaign_id, party_id)
        if t is None:
            raise ValueError(f"target ({campaign_id}, {party_id}) not found")
        allowed = TARGET_ALLOWED_TRANSITIONS.get(t.status, [])
        if "converted" not in allowed:
            raise ValueError(
                f"cannot transition target from {t.status!r} to 'converted'"
            )
        t.status = "converted"
        t.last_touch_at = utc_now()
        if order_code is not None:
            t.converted_order_code = order_code
        if revenue_vnd is not None:
            t.converted_revenue_vnd = revenue_vnd
        t.converted_at = utc_now()
        self._campaign_repo.update_target(t)

    def list_targets(self, campaign_id: str, status: str | None = None) -> list[CampaignTarget]:
        """Return targets for a campaign, optionally filtered by status."""
        if status:
            if status not in VALID_TARGET_STATUSES:
                raise ValueError(
                    f"invalid target status {status!r} — must be one of: "
                    + ", ".join(VALID_TARGET_STATUSES)
                )
            return self._campaign_repo.list_targets(campaign_id, status)
        return self._campaign_repo.list_targets(campaign_id)

    # ── Conversion scanning ────────────────────────────────────────────────────

    def scan_conversions(self, campaign_id: str) -> int:
        """Check cache.wh_order_hdr for orders placed after the campaign's scheduled_at.

        Conversion rule: earliest qualifying order (date_key >= campaign scheduled_at
        ICT date) marks the target as converted.
        Idempotent: already-converted targets are not overwritten.
        Graceful-empty: if cache tables are absent, returns 0.
        """
        c = self._campaign_repo.get_by_id(campaign_id)
        if c is None:
            raise ValueError(f"campaign {campaign_id!r} not found")

        # date_key in wh_order_hdr is ICT (UTC+7); compare in ICT to avoid ±1-day drift.
        if c.scheduled_at and len(c.scheduled_at) >= 10:
            scheduled_date_key = _date_to_ict_key(c.scheduled_at)
        else:
            scheduled_date_key = _today_ict_date_key()

        targets = self._campaign_repo.list_targets(campaign_id)
        converted = 0
        for t in targets:
            if t.status in TARGET_TERMINAL_STATUSES:
                continue
            try:
                result = self._find_earliest_order(t.party_id, scheduled_date_key)
            except Exception as exc:
                if _is_missing_table_error(exc):
                    return converted
                raise
            if result is None:
                continue
            order_code, revenue, order_date = result
            t.status = "converted"
            t.converted_order_code = order_code
            t.converted_revenue_vnd = revenue
            t.converted_at = order_date
            self._campaign_repo.update_target(t)
            converted += 1
        return converted

    # ── ROI ───────────────────────────────────────────────────────────────────

    def get_roi(self, campaign_id: str) -> dict:
        """Return summary stats: status counts, total targets, total converted revenue."""
        targets = self._campaign_repo.list_targets(campaign_id)
        counts: dict[str, int] = {}
        total_rev = 0
        for t in targets:
            counts[t.status] = counts.get(t.status, 0) + 1
            if t.status == "converted" and t.converted_revenue_vnd:
                total_rev += t.converted_revenue_vnd
        return CampaignROI(
            campaign_id=campaign_id,
            total_targets=len(targets),
            total_converted_revenue_vnd=total_rev,
            status_counts=counts,
        ).__dict__

    # ── Private helpers ────────────────────────────────────────────────────────

    def _fetch_consent_map(self) -> dict[str, str | None]:
        """Delegate to the campaign repository adapter which owns the SQL."""
        return self._campaign_repo.fetch_consent_map()

    def _find_earliest_order(
        self, party_id: str, scheduled_date_key: int
    ) -> tuple[str, int, str] | None:
        """Delegate to the campaign repository adapter which owns the SQL."""
        return self._campaign_repo.find_earliest_order(party_id, scheduled_date_key)
