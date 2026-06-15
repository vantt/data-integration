"""cache_repository.py — SQLiteCacheRepository: read-only adapter over cache.db.

Queries use the "cache." schema prefix (cache.db is ATTACHed read-only via CRMDatabase).
Graceful-empty: OperationalError for missing tables/columns → [] or None, never raised.
Python is the SOLE writer of cache.db; this adapter never writes to it.
Money = INTEGER (VND); realized_margin_pct (H010-corrected).
date_key is ICT YYYYMMDD — passed through as-is, never recomputed.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from domain.entities.app_user import AppUser
from domain.entities.cache_insight import (
    ActionQueueItem,
    CacheInsight,
    CustomerInsight,
    RecentOrder,
)
from domain.entities.party import PartySeed


def _is_missing_table(exc: sqlite3.OperationalError) -> bool:
    return "no such table" in str(exc).lower()


def _is_missing_column(exc: sqlite3.OperationalError) -> bool:
    return "no such column" in str(exc).lower()


class SQLiteCacheRepository:
    """Read-only adapter over the cache.* schema (cache.db ATTACHed as 'cache')."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_customer_insight(self, customer_id: int) -> Optional[CacheInsight]:
        """Return composed CacheInsight (insight + actions + recent orders) for customer_id.

        Returns None when no data exists or cache tables are absent.
        """
        insight = self._fetch_insight(customer_id)
        customer_key = insight.customer_key if insight else ""
        actions = self._fetch_actions(customer_key)
        recent_orders = self._fetch_recent_orders(customer_id)

        if insight is None and not actions and not recent_orders:
            return None

        return CacheInsight(
            insight=insight,
            actions=actions,
            recent_orders=recent_orders,
            refreshed_at=insight.refreshed_at if insight else "",
        )

    def list_party_seed(self) -> list[PartySeed]:
        """Return all wh_party_seed rows enriched with display_name/phone/email.

        JOIN is on INTEGER customer_id. Returns [] when table is absent.
        COALESCE on quality fields handles rows written before column was added.
        """
        sql = """
            SELECT ps.customer_id, ps.customer_key, ps.seen_at,
                   COALESCE(ps.source_contact_quality, 'real') AS source_contact_quality,
                   COALESCE(ps.contact_quality, 'real') AS contact_quality,
                   bc.display_name, bc.phone, bc.email
            FROM cache.wh_party_seed ps
            LEFT JOIN cache.wh_customer_base bc ON bc.customer_id = ps.customer_id
        """
        try:
            rows = self._conn.execute(sql).fetchall()
        except sqlite3.OperationalError as exc:
            if _is_missing_table(exc) or _is_missing_column(exc):
                return []
            raise
        return [
            PartySeed(
                customer_id=row["customer_id"],
                customer_key=row["customer_key"],
                seen_at=row["seen_at"] or "",
                source_contact_quality=row["source_contact_quality"] or "real",
                contact_quality=row["contact_quality"] or "real",
                display_name=row["display_name"] or "",
                phone=row["phone"] or "",
                email=row["email"] or "",
            )
            for row in rows
        ]

    def list_all_action_queue(self) -> list[ActionQueueItem]:
        """Return all wh_action_queue rows enriched with customer_name and party_id.

        Returns [] when table is absent.
        """
        sql = """
            SELECT a.action_id, a.customer_key, a.action_type, a.rationale_vi,
                   a.value_at_stake_vnd, a.priority, a.generated_date, a.refreshed_at,
                   COALESCE(bc.display_name, '') AS customer_name,
                   pi.party_id AS party_id
            FROM cache.wh_action_queue a
            LEFT JOIN cache.wh_party_seed ps ON ps.customer_key = a.customer_key
            LEFT JOIN cache.wh_customer_base bc ON bc.customer_id = ps.customer_id
            LEFT JOIN crm_party_identity pi
                   ON pi.identity_type = 'sapo_customer'
                  AND pi.identity_value = CAST(ps.customer_id AS TEXT)
            ORDER BY a.priority ASC
        """
        try:
            rows = self._conn.execute(sql).fetchall()
        except sqlite3.OperationalError as exc:
            if _is_missing_table(exc):
                return []
            raise
        return [
            ActionQueueItem(
                action_id=row["action_id"],
                customer_key=row["customer_key"],
                action_type=row["action_type"],
                rationale_vi=row["rationale_vi"] or "",
                value_at_stake_vnd=row["value_at_stake_vnd"] or 0,
                priority=row["priority"] or 0,
                generated_date=row["generated_date"] or "",
                refreshed_at=row["refreshed_at"] or "",
                customer_name=row["customer_name"] or "",
                party_id=row["party_id"],
            )
            for row in rows
        ]

    # ── Private helpers ────────────────────────────────────────────────────────

    def _fetch_insight(self, customer_id: int) -> Optional[CustomerInsight]:
        sql = """
            SELECT customer_key, customer_id,
                   value_group, customer_status,
                   next_purchase_signal, predicted_next_purchase_date,
                   avg_days_between_orders, avg_order_spend,
                   discount_sensitivity, cancel_rate,
                   last_purchased_sku, top_affinity_product, second_affinity_product,
                   channel_preference, lifetime_contribution_margin, is_margin_negative,
                   refreshed_at
            FROM cache.wh_customer_insight
            WHERE customer_id = ?
            LIMIT 1
        """
        try:
            row = self._conn.execute(sql, (customer_id,)).fetchone()
        except sqlite3.OperationalError as exc:
            if _is_missing_table(exc):
                return None
            raise
        if row is None:
            return None
        return CustomerInsight(
            customer_key=row["customer_key"],
            customer_id=row["customer_id"],
            value_group=row["value_group"] or "",
            customer_status=row["customer_status"] or "",
            next_purchase_signal=row["next_purchase_signal"] or "",
            predicted_next_purchase_date=row["predicted_next_purchase_date"] or "",
            avg_days_between_orders=row["avg_days_between_orders"] or 0.0,
            avg_order_spend=row["avg_order_spend"] or 0.0,
            discount_sensitivity=row["discount_sensitivity"] or "",
            cancel_rate=row["cancel_rate"] or 0.0,
            last_purchased_sku=row["last_purchased_sku"] or "",
            top_affinity_product=row["top_affinity_product"] or "",
            second_affinity_product=row["second_affinity_product"] or "",
            channel_preference=row["channel_preference"] or "",
            lifetime_contribution_margin=row["lifetime_contribution_margin"] or 0.0,
            is_margin_negative=bool(row["is_margin_negative"]),
            refreshed_at=row["refreshed_at"] or "",
        )

    def _fetch_actions(self, customer_key: str) -> list[ActionQueueItem]:
        if not customer_key:
            return []
        sql = """
            SELECT action_id, customer_key, action_type, rationale_vi,
                   value_at_stake_vnd, priority, generated_date, refreshed_at
            FROM cache.wh_action_queue
            WHERE customer_key = ?
            ORDER BY priority ASC
            LIMIT 10
        """
        try:
            rows = self._conn.execute(sql, (customer_key,)).fetchall()
        except sqlite3.OperationalError as exc:
            if _is_missing_table(exc):
                return []
            raise
        return [
            ActionQueueItem(
                action_id=row["action_id"],
                customer_key=row["customer_key"],
                action_type=row["action_type"],
                rationale_vi=row["rationale_vi"] or "",
                value_at_stake_vnd=row["value_at_stake_vnd"] or 0,
                priority=row["priority"] or 0,
                generated_date=row["generated_date"] or "",
                refreshed_at=row["refreshed_at"] or "",
            )
            for row in rows
        ]

    def _fetch_recent_orders(self, customer_id: int) -> list[RecentOrder]:
        sql = """
            SELECT order_id, order_code, customer_id, date_key,
                   net_revenue, status, channel, item_count
            FROM cache.wh_order_hdr
            WHERE customer_id = ?
            ORDER BY date_key DESC
            LIMIT 20
        """
        try:
            rows = self._conn.execute(sql, (customer_id,)).fetchall()
        except sqlite3.OperationalError as exc:
            if _is_missing_table(exc):
                return []
            raise
        return [
            RecentOrder(
                order_id=row["order_id"],
                order_code=row["order_code"] or "",
                customer_id=row["customer_id"],
                date_key=row["date_key"] or 0,
                net_revenue=row["net_revenue"] or 0,
                status=row["status"] or "",
                channel=row["channel"] or "",
                item_count=row["item_count"] or 0,
            )
            for row in rows
        ]
