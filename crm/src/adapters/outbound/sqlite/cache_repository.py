"""cache_repository.py — SQLiteCacheRepository: read-only adapter over cache.db.

Queries use the "cache." schema prefix (cache.db is ATTACHed read-only via CRMDatabase).
Graceful-empty: OperationalError for missing tables/columns → [] or None, never raised.
Python is the SOLE writer of cache.db; this adapter never writes to it.
Money = INTEGER (VND); realized_margin_pct (H010-corrected).
date_key is ICT YYYYMMDD — passed through as-is, never recomputed.

Cross-schema JOINs: list_all_action_queue() and _fetch_actions() intentionally JOIN
crm.* tables (crm_party_identity, crm_action_state, crm_task). list_all_action_queue()
additionally JOINs crm_action_dismissal, matched on (party_id, action_type, source_mart)
(migration 0046 — mart-scoped: a customer-level and SKU-level suppression of the same
action_type are independent) — _fetch_actions() (C360 reason rail) intentionally does
NOT join it at all, since it reports per-episode crm_action_state.status only (verified,
locked decision — do not change). Both DBs are ATTACHed to the same connection via
CRMDatabase. Schema changes to crm_task or crm_party_identity must be reflected in
the SQL in this file.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from domain.entities.action_scenario import MART_CUSTOMER, MART_SKU
from domain.entities.app_user import AppUser
from domain.entities.cache_insight import (
    ActionQueueItem,
    CacheInsight,
    CustomerInsight,
    CustomerTier,
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
        """Return composed CacheInsight (insight + tier + actions + recent orders) for customer_id.

        Returns None when no data exists or cache tables are absent.
        """
        insight = self._fetch_insight(customer_id)
        customer_key = insight.customer_key if insight else ""
        tier = self._fetch_tier(customer_id)
        actions = self._fetch_actions(customer_key)
        recent_orders = self._fetch_recent_orders(customer_id)

        if insight is None and tier is None and not actions and not recent_orders:
            return None

        return CacheInsight(
            insight=insight,
            tier=tier,
            actions=actions,
            recent_orders=recent_orders,
            refreshed_at=insight.refreshed_at if insight else "",
        )

    def get_tiers_batch(self, customer_ids: list[int]) -> dict[int, str]:
        """Return {customer_id: strategic_tier} for a batch of customer_ids.

        Used by the customer list to show tier badge without DuckDB round-trip.
        Returns {} when table is absent or customer_ids is empty.
        """
        if not customer_ids:
            return {}
        placeholders = ",".join("?" for _ in customer_ids)
        sql = (
            f"SELECT customer_id, strategic_tier "
            f"FROM cache.wh_customer_tier "
            f"WHERE customer_id IN ({placeholders})"
        )
        try:
            rows = self._conn.execute(sql, customer_ids).fetchall()
        except sqlite3.OperationalError as exc:
            if _is_missing_table(exc) or _is_missing_column(exc):
                return {}
            raise
        return {row["customer_id"]: row["strategic_tier"] or "" for row in rows}

    def list_party_seed(self) -> list[PartySeed]:
        """Return all wh_party_seed rows enriched with display_name/phone/email.

        JOIN is on INTEGER customer_id. Returns [] when table is absent.
        COALESCE on quality fields handles rows written before column was added.
        """
        sql = """
            SELECT ps.customer_id, ps.customer_key, ps.seen_at,
                   COALESCE(ps.source_contact_quality, 'real') AS source_contact_quality,
                   COALESCE(ps.contact_quality, 'real') AS contact_quality,
                   bc.display_name, bc.phone, bc.email, bc.customer_code,
                   bc.address1, bc.ward, bc.district, bc.province,
                   bc.birth_date, bc.gender
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
                customer_code=row["customer_code"] or "",
                address1=row["address1"] or "",
                ward=row["ward"] or "",
                district=row["district"] or "",
                province=row["province"] or "",
                birth_date=row["birth_date"] or "",
                gender=row["gender"] or "",
            )
            for row in rows
        ]

    def list_all_action_queue(self) -> list[ActionQueueItem]:
        """Return actionable rows from wh_action_queue UNION wh_sku_action_queue.

        Filters out: dismissed (per-episode crm_action_state OR active B5
        (party_id, action_type, source_mart) TTL dismissal in crm_action_dismissal),
        snoozed-until-future, and actions with open crm_task. Falls back to
        customer-level queue only if wh_sku_action_queue is absent (e.g. before the
        first dbt run that materialises mart_customer_sku_action_queue). Returns []
        when all tables are absent.

        B5 (migration 0038, mart-scoped since migration 0046): crm_action_dismissal
        survives the warehouse regenerating a new action_id for the same
        (party, action_type, mart) across weekly refreshes — the per-episode
        crm_action_state.status filter above cannot, since it is keyed on the old
        action_id. Both filters apply independently; either one hides the row.
        Matching includes source_mart so a customer-level and SKU-level suppression
        of the same action_type are independent (see suggestion_settings_service.py).
        """
        # NOTE: wh_action_queue or wh_sku_action_queue schema changes must be applied
        # in BOTH list_all_action_queue() and _fetch_actions().
        _customer_branch = """
            SELECT a.action_id, a.customer_key, a.action_type, a.rationale_vi,
                   a.value_at_stake_vnd, a.priority,
                   COALESCE(a.pending_since, a.generated_date) AS pending_since,
                   a.generated_date, a.refreshed_at,
                   COALESCE(bc.display_name, '') AS customer_name,
                   pi.party_id AS party_id,
                   bc.customer_id AS customer_id,
                   COALESCE(s.status, 'open') AS status,
                   s.snoozed_until,
                   COALESCE(a.top_affinity_product, '') AS top_affinity_product,
                   COALESCE(a.last_purchased_product, '') AS last_purchased_product,
                   COALESCE(ct.strategic_tier, '') AS strategic_tier,
                   COALESCE(ct.value_group, '') AS value_group,
                   NULL AS supply_stream,
                   COALESCE(ct.is_contactable, 1) AS is_contactable
            FROM cache.wh_action_queue a
            LEFT JOIN cache.wh_customer_base bc ON bc.customer_key = a.customer_key
            LEFT JOIN cache.wh_party_seed ps ON ps.customer_key = a.customer_key
            LEFT JOIN crm_party_identity pi
                   ON pi.identity_type = 'sapo_customer'
                  AND pi.identity_value = CAST(ps.customer_id AS TEXT)
            LEFT JOIN crm_action_state s ON s.action_id = a.action_id
            LEFT JOIN cache.wh_customer_tier ct ON ct.customer_key = a.customer_key
            LEFT JOIN crm_action_dismissal ad
                   ON ad.party_id = pi.party_id
                  AND ad.action_type = a.action_type
                  AND ad.source_mart = '""" + MART_CUSTOMER + """'
            WHERE COALESCE(s.status, 'open') != 'dismissed'
              AND (COALESCE(s.status, 'open') != 'snoozed'
                   OR s.snoozed_until < date('now', '+7 hours'))  -- snoozed_until is an ICT date; date('now','+7h') = today in ICT
              AND (ad.party_id IS NULL OR ad.dismissed_until <= strftime('%Y-%m-%dT%H:%M:%fZ','now'))
              AND NOT EXISTS (
                  -- Hide when an active claim task exists, OR when a done/cancelled claim task
                  -- was created after the last contact (same contact cycle — customer already handled).
                  SELECT 1 FROM crm_task t
                  WHERE t.source = 'action_queue_claim'
                    AND t.party_id = pi.party_id
                    AND pi.party_id IS NOT NULL
                    AND (
                        t.status NOT IN ('done', 'cancelled')
                        OR EXISTS (
                            SELECT 1 FROM crm_last_contact lc
                            WHERE lc.party_id = pi.party_id
                              AND t.created_at >= datetime(lc.last_contacted_at, '-5 minutes')
                        )
                    )
              )"""

        _sku_branch = """
            SELECT sa.action_id, sa.customer_key, sa.action_type, sa.rationale_vi,
                   0 AS value_at_stake_vnd, sa.priority,
                   COALESCE(sa.pending_since, sa.generated_date) AS pending_since,
                   sa.generated_date, sa.refreshed_at,
                   COALESCE(bc.display_name, '') AS customer_name,
                   pi.party_id AS party_id,
                   bc.customer_id AS customer_id,
                   COALESCE(s.status, 'open') AS status,
                   s.snoozed_until,
                   COALESCE(sa.product_display_name, '') AS top_affinity_product,
                   '' AS last_purchased_product,
                   COALESCE(ct.strategic_tier, '') AS strategic_tier,
                   COALESCE(ct.value_group, '') AS value_group,
                   sa.supply_stream AS supply_stream,
                   COALESCE(ct.is_contactable, 1) AS is_contactable
            FROM cache.wh_sku_action_queue sa
            LEFT JOIN cache.wh_customer_base bc ON bc.customer_key = sa.customer_key
            LEFT JOIN cache.wh_party_seed ps ON ps.customer_key = sa.customer_key
            LEFT JOIN crm_party_identity pi
                   ON pi.identity_type = 'sapo_customer'
                  AND pi.identity_value = CAST(ps.customer_id AS TEXT)
            LEFT JOIN crm_action_state s ON s.action_id = sa.action_id
            LEFT JOIN cache.wh_customer_tier ct ON ct.customer_key = sa.customer_key
            LEFT JOIN crm_action_dismissal ad
                   ON ad.party_id = pi.party_id
                  AND ad.action_type = sa.action_type
                  AND ad.source_mart = '""" + MART_SKU + """'
            WHERE COALESCE(s.status, 'open') != 'dismissed'
              AND (COALESCE(s.status, 'open') != 'snoozed'
                   OR s.snoozed_until < date('now', '+7 hours'))
              AND (ad.party_id IS NULL OR ad.dismissed_until <= strftime('%Y-%m-%dT%H:%M:%fZ','now'))
              AND NOT EXISTS (
                  SELECT 1 FROM crm_task t
                  WHERE t.source = 'action_queue_claim'
                    AND t.party_id = pi.party_id
                    AND pi.party_id IS NOT NULL
                    AND (
                        t.status NOT IN ('done', 'cancelled')
                        OR EXISTS (
                            SELECT 1 FROM crm_last_contact lc
                            WHERE lc.party_id = pi.party_id
                              AND t.created_at >= datetime(lc.last_contacted_at, '-5 minutes')
                        )
                    )
              )"""

        full_sql = (
            "SELECT * FROM (" + _customer_branch + " UNION ALL " + _sku_branch + ") ORDER BY priority ASC"
        )
        # Wrap in subquery (same pattern as full_sql) to avoid "ambiguous column name: priority"
        # when crm_task.priority collides with wh_action_queue.priority in ORDER BY.
        fallback_sql = "SELECT * FROM (" + _customer_branch + ") ORDER BY priority ASC"

        try:
            rows = self._conn.execute(full_sql).fetchall()
        except sqlite3.OperationalError as exc:
            if _is_missing_table(exc) or _is_missing_column(exc):
                # wh_sku_action_queue not yet created — fall back to customer-level only
                try:
                    rows = self._conn.execute(fallback_sql).fetchall()
                except sqlite3.OperationalError as exc2:
                    if _is_missing_table(exc2) or _is_missing_column(exc2):
                        return []
                    raise
            else:
                raise
        return [
            self._row_to_action_queue_item(
                row,
                customer_name=row["customer_name"] or "",
                party_id=row["party_id"],
                customer_id=row["customer_id"],
                top_affinity_product=row["top_affinity_product"] or "",
                last_purchased_product=row["last_purchased_product"] or "",
                strategic_tier=row["strategic_tier"] or "",
                value_group=row["value_group"] or "",
                supply_stream=row["supply_stream"] or "",
                is_contactable=bool(row["is_contactable"]),
            )
            for row in rows
        ]

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_action_queue_item(row: sqlite3.Row, **extra: object) -> ActionQueueItem:
        """Map the 11 common ActionQueueItem fields from a sqlite3.Row.

        Method-specific fields (customer_name/party_id/customer_id/top_affinity_product/
        last_purchased_product for list_all_action_queue; last_purchase_date/last_order_code/
        last_sku_discount_rate/last_net_unit_price/estimated_depletion_date for _fetch_actions)
        are passed by the caller as kwargs.
        """
        return ActionQueueItem(
            action_id=row["action_id"],
            customer_key=row["customer_key"],
            action_type=row["action_type"],
            rationale_vi=row["rationale_vi"] or "",
            value_at_stake_vnd=row["value_at_stake_vnd"] or 0,
            priority=row["priority"] or 0,
            pending_since=row["pending_since"] or "",
            generated_date=row["generated_date"] or "",
            refreshed_at=row["refreshed_at"] or "",
            status=row["status"] or "open",
            snoozed_until=row["snoozed_until"],
            **extra,  # type: ignore[arg-type]
        )

    def _fetch_tier(self, customer_id: int) -> Optional[CustomerTier]:
        sql = """
            SELECT customer_key, customer_id, strategic_tier, tier_reason,
                   recency_days, order_count, value_group,
                   is_contactable, tier_generated_at
            FROM cache.wh_customer_tier
            WHERE customer_id = ?
            LIMIT 1
        """
        try:
            row = self._conn.execute(sql, (customer_id,)).fetchone()
        except sqlite3.OperationalError as exc:
            if _is_missing_table(exc) or _is_missing_column(exc):
                return None
            raise
        if row is None:
            return None
        return CustomerTier(
            customer_key=row["customer_key"] or "",
            customer_id=row["customer_id"],
            strategic_tier=row["strategic_tier"] or "",
            tier_reason=row["tier_reason"] or "",
            recency_days=row["recency_days"] or 0,
            order_count=row["order_count"] or 0,
            value_group=row["value_group"] or "",
            is_contactable=bool(row["is_contactable"]),
            tier_generated_at=row["tier_generated_at"] or "",
        )

    def _fetch_insight(self, customer_id: int) -> Optional[CustomerInsight]:
        sql = """
            SELECT ci.customer_key, ci.customer_id,
                   ci.value_group, ci.customer_status,
                   ci.next_purchase_signal, ci.predicted_next_purchase_date,
                   ci.avg_days_between_orders, ci.avg_order_spend,
                   ci.discount_sensitivity, ci.cancel_rate,
                   ci.last_purchased_sku, ci.top_affinity_product, ci.second_affinity_product,
                   ci.channel_preference, ci.lifetime_contribution_margin, ci.is_margin_negative,
                   ci.refreshed_at,
                   COALESCE(cb.first_order_date, '') AS first_order_date,
                   ci.last_line_discount_rate, ci.max_line_discount_rate,
                   ci.last_voucher_discount_rate, ci.max_voucher_discount_rate,
                   ci.last_campaign_discount_rate, ci.max_campaign_discount_rate,
                   ci.last_negotiated_discount_rate, ci.max_negotiated_discount_rate
            FROM cache.wh_customer_insight ci
            LEFT JOIN cache.wh_customer_base cb ON cb.customer_id = ci.customer_id
            WHERE ci.customer_id = ?
            LIMIT 1
        """
        try:
            row = self._conn.execute(sql, (customer_id,)).fetchone()
        except sqlite3.OperationalError as exc:
            if _is_missing_table(exc) or _is_missing_column(exc):
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
            first_order_date=row["first_order_date"] or "",
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
            last_line_discount_rate=row["last_line_discount_rate"],
            max_line_discount_rate=row["max_line_discount_rate"],
            last_voucher_discount_rate=row["last_voucher_discount_rate"],
            max_voucher_discount_rate=row["max_voucher_discount_rate"],
            last_campaign_discount_rate=row["last_campaign_discount_rate"],
            max_campaign_discount_rate=row["max_campaign_discount_rate"],
            last_negotiated_discount_rate=row["last_negotiated_discount_rate"],
            max_negotiated_discount_rate=row["max_negotiated_discount_rate"],
        )

    def _fetch_actions(self, customer_key: str) -> list[ActionQueueItem]:
        """Return all actions for a customer (customer 360 view — no status filtering).

        UNIONs customer-level (wh_action_queue) and SKU-level (wh_sku_action_queue) actions.
        Falls back to customer-level only when wh_sku_action_queue is absent.
        """
        if not customer_key:
            return []

        # NOTE: wh_action_queue or wh_sku_action_queue schema changes must be applied
        # in BOTH list_all_action_queue() and _fetch_actions().
        _customer_branch = """
            SELECT a.action_id, a.customer_key, a.action_type, a.rationale_vi,
                   a.value_at_stake_vnd, a.priority,
                   COALESCE(a.pending_since, a.generated_date) AS pending_since,
                   a.generated_date, a.refreshed_at,
                   COALESCE(s.status, 'open') AS status,
                   s.snoozed_until,
                   NULL AS last_purchase_date,
                   NULL AS last_order_code,
                   NULL AS last_sku_discount_rate,
                   NULL AS last_net_unit_price,
                   NULL AS estimated_depletion_date,
                   COALESCE(ct.strategic_tier, '') AS strategic_tier,
                   COALESCE(ct.value_group, '') AS value_group,
                   NULL AS supply_stream,
                   COALESCE(ct.is_contactable, 1) AS is_contactable
            FROM cache.wh_action_queue a
            LEFT JOIN crm_action_state s ON s.action_id = a.action_id
            LEFT JOIN cache.wh_customer_tier ct ON ct.customer_key = a.customer_key
            WHERE a.customer_key = ?"""

        _sku_branch = """
            SELECT sa.action_id, sa.customer_key, sa.action_type, sa.rationale_vi,
                   0 AS value_at_stake_vnd, sa.priority,
                   COALESCE(sa.pending_since, sa.generated_date) AS pending_since,
                   sa.generated_date, sa.refreshed_at,
                   COALESCE(s.status, 'open') AS status,
                   s.snoozed_until,
                   sa.last_purchase_date,
                   sa.last_order_code,
                   sa.last_sku_discount_rate,
                   sa.last_net_unit_price,
                   sa.estimated_depletion_date,
                   COALESCE(ct.strategic_tier, '') AS strategic_tier,
                   COALESCE(ct.value_group, '') AS value_group,
                   sa.supply_stream AS supply_stream,
                   COALESCE(ct.is_contactable, 1) AS is_contactable
            FROM cache.wh_sku_action_queue sa
            LEFT JOIN crm_action_state s ON s.action_id = sa.action_id
            LEFT JOIN cache.wh_customer_tier ct ON ct.customer_key = sa.customer_key
            WHERE sa.customer_key = ?"""

        full_sql = (
            "SELECT * FROM (" + _customer_branch + " UNION ALL " + _sku_branch
            + ") ORDER BY priority ASC LIMIT 20"
        )
        fallback_sql = _customer_branch + " ORDER BY priority ASC LIMIT 20"

        try:
            rows = self._conn.execute(full_sql, (customer_key, customer_key)).fetchall()
        except sqlite3.OperationalError as exc:
            if _is_missing_table(exc) or _is_missing_column(exc):
                try:
                    rows = self._conn.execute(fallback_sql, (customer_key,)).fetchall()
                except sqlite3.OperationalError as exc2:
                    if _is_missing_table(exc2) or _is_missing_column(exc2):
                        return []
                    raise
            else:
                raise
        return [
            self._row_to_action_queue_item(
                row,
                last_purchase_date=row["last_purchase_date"] or "",
                last_order_code=row["last_order_code"] or "",
                last_sku_discount_rate=row["last_sku_discount_rate"],
                last_net_unit_price=row["last_net_unit_price"],
                estimated_depletion_date=row["estimated_depletion_date"] or "",
                strategic_tier=row["strategic_tier"] or "",
                value_group=row["value_group"] or "",
                supply_stream=row["supply_stream"] or "",
                is_contactable=bool(row["is_contactable"]),
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
