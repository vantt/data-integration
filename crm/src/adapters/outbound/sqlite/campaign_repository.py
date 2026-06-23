"""SQLiteCampaignRepository — SQLite adapter for Campaign and CampaignTarget persistence.

Mirrors Go campaign_repo.go / campaign_queries.sql exactly.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from domain.entities.segment import Campaign, CampaignTarget


class SQLiteCampaignRepository:
    """SQLite adapter implementing the CampaignRepository port."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ── Campaign CRUD ─────────────────────────────────────────────────────────

    def insert(self, campaign: Campaign) -> None:
        """INSERT a new campaign row."""
        self._conn.execute(
            """
            INSERT INTO crm_campaign (
              campaign_id, name, objective, channel, segment_id, status,
              scheduled_at, created_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                campaign.campaign_id,
                campaign.name,
                campaign.objective,
                campaign.channel or None,
                campaign.segment_id,
                campaign.status,
                campaign.scheduled_at,
                campaign.created_by,
                campaign.created_at,
                campaign.updated_at,
            ),
        )
        self._conn.commit()

    def get_by_id(self, campaign_id: str) -> Optional[Campaign]:
        """Return a campaign by PK, or None if not found."""
        row = self._conn.execute(
            """
            SELECT campaign_id, name, objective, channel, segment_id, status,
                   scheduled_at, created_by, created_at, updated_at
            FROM crm_campaign
            WHERE campaign_id = ?
            """,
            (campaign_id,),
        ).fetchone()
        if row is None:
            return None
        return self._campaign_from_row(row)

    def update(self, campaign: Campaign) -> None:
        """Persist mutable campaign fields — accepts a full Campaign object (port contract)."""
        self._conn.execute(
            """
            UPDATE crm_campaign
            SET name         = ?,
                objective    = ?,
                channel      = ?,
                segment_id   = ?,
                status       = ?,
                scheduled_at = ?,
                updated_at   = ?
            WHERE campaign_id = ?
            """,
            (
                campaign.name,
                campaign.objective,
                campaign.channel or None,
                campaign.segment_id,
                campaign.status,
                campaign.scheduled_at,
                campaign.updated_at,
                campaign.campaign_id,
            ),
        )
        self._conn.commit()

    def list(self) -> list[Campaign]:
        """Return all campaigns ordered by created_at DESC (port contract name)."""
        return self.list_campaigns()

    def list_campaigns(self) -> list[Campaign]:
        """Return all campaigns ordered by created_at DESC."""
        rows = self._conn.execute(
            """
            SELECT campaign_id, name, objective, channel, segment_id, status,
                   scheduled_at, created_by, created_at, updated_at
            FROM crm_campaign
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [self._campaign_from_row(r) for r in rows]

    # ── CampaignTarget CRUD ───────────────────────────────────────────────────

    def upsert_target(self, target: CampaignTarget) -> None:
        """INSERT a campaign target; ON CONFLICT DO NOTHING (idempotent on PK)."""
        self._conn.execute(
            """
            INSERT INTO crm_campaign_target (
              campaign_id, party_id, status, assigned_user_id, last_touch_at,
              converted_order_code, converted_revenue_vnd, converted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (campaign_id, party_id) DO NOTHING
            """,
            (
                target.campaign_id,
                target.party_id,
                target.status,
                target.assigned_user_id,
                target.last_touch_at,
                target.converted_order_code,
                target.converted_revenue_vnd,
                target.converted_at,
            ),
        )
        self._conn.commit()

    def update_target(self, target: CampaignTarget) -> None:
        """Persist mutable target fields — accepts a full CampaignTarget object (port contract)."""
        self._conn.execute(
            """
            UPDATE crm_campaign_target
            SET status                = ?,
                assigned_user_id      = ?,
                last_touch_at         = ?,
                converted_order_code  = ?,
                converted_revenue_vnd = ?,
                converted_at          = ?
            WHERE campaign_id = ? AND party_id = ?
            """,
            (
                target.status,
                target.assigned_user_id,
                target.last_touch_at,
                target.converted_order_code,
                target.converted_revenue_vnd,
                target.converted_at,
                target.campaign_id,
                target.party_id,
            ),
        )
        self._conn.commit()

    def get_target(self, campaign_id: str, party_id: str) -> Optional[CampaignTarget]:
        """Return a single target row, or None if not found."""
        row = self._conn.execute(
            """
            SELECT campaign_id, party_id, status, assigned_user_id, last_touch_at,
                   converted_order_code, converted_revenue_vnd, converted_at
            FROM crm_campaign_target
            WHERE campaign_id = ? AND party_id = ?
            """,
            (campaign_id, party_id),
        ).fetchone()
        if row is None:
            return None
        return self._target_from_row(row)

    def list_targets(
        self, campaign_id: str, status: Optional[str] = None, limit: int = 200
    ) -> list[CampaignTarget]:
        """Return targets for a campaign, optionally filtered by status, capped at limit."""
        if status:
            rows = self._conn.execute(
                """
                SELECT campaign_id, party_id, status, assigned_user_id, last_touch_at,
                       converted_order_code, converted_revenue_vnd, converted_at
                FROM crm_campaign_target
                WHERE campaign_id = ? AND status = ?
                ORDER BY party_id
                LIMIT ?
                """,
                (campaign_id, status, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT campaign_id, party_id, status, assigned_user_id, last_touch_at,
                       converted_order_code, converted_revenue_vnd, converted_at
                FROM crm_campaign_target
                WHERE campaign_id = ?
                ORDER BY party_id
                LIMIT ?
                """,
                (campaign_id, limit),
            ).fetchall()
        return [self._target_from_row(r) for r in rows]

    # ── Mapping helpers ───────────────────────────────────────────────────────

    # ── Query helpers (pulled out of application layer for hex boundary) ─────────

    def fetch_consent_map(self) -> dict:
        """Return {party_id: consent_value} from crm_customer_profile.consent_enum.

        Values: 'allowed' | 'denied' | None (na — not collected).
        Graceful-empty: returns {} when the profile table does not yet exist.
        """
        try:
            cur = self._conn.execute(
                "SELECT party_id, consent_enum FROM crm_customer_profile"
            )
        except Exception as exc:
            if "no such table" in str(exc).lower():
                return {}
            raise
        return {row[0]: row[1] for row in cur.fetchall()}

    def find_earliest_order(
        self, party_id: str, scheduled_date_key: int
    ) -> "tuple[str, int, str] | None":
        """Look up the earliest qualifying order for a party via sapo_customer identity.

        Returns (order_code, net_revenue, converted_at_iso) or None.
        Raises on errors other than missing cache tables (caller catches those).
        """
        sql = """
            SELECT oh.order_code, oh.net_revenue, oh.date_key
            FROM cache.wh_order_hdr oh
            JOIN crm_party_identity pi2
                ON pi2.identity_type = 'sapo_customer'
                AND oh.customer_id = CAST(pi2.identity_value AS INTEGER)
            WHERE pi2.party_id = ?
              AND oh.date_key >= ?
            ORDER BY oh.date_key ASC
            LIMIT 1
        """
        cur = self._conn.execute(sql, (party_id, scheduled_date_key))
        row = cur.fetchone()
        if row is None:
            return None
        order_code, net_revenue, date_key = row[0], row[1], row[2]
        dk = str(date_key)
        if len(dk) == 8:
            date_str = f"{dk[:4]}-{dk[4:6]}-{dk[6:]}T00:00:00.000Z"
        else:
            from datetime import datetime, timezone
            date_str = datetime.now(timezone.utc).isoformat()
        return (order_code or "", int(net_revenue or 0), date_str)

    # ── Mapping helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _campaign_from_row(row: sqlite3.Row) -> Campaign:
        return Campaign(
            campaign_id=row["campaign_id"],
            name=row["name"],
            objective=row["objective"],
            channel=row["channel"] or "",
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            segment_id=row["segment_id"],
            scheduled_at=row["scheduled_at"],
            created_by=row["created_by"],
        )

    @staticmethod
    def _target_from_row(row: sqlite3.Row) -> CampaignTarget:
        return CampaignTarget(
            campaign_id=row["campaign_id"],
            party_id=row["party_id"],
            status=row["status"],
            assigned_user_id=row["assigned_user_id"],
            last_touch_at=row["last_touch_at"],
            converted_order_code=row["converted_order_code"],
            converted_revenue_vnd=row["converted_revenue_vnd"],
            converted_at=row["converted_at"],
        )
