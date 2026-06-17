"""SegmentService: segment CRUD + dynamic rule evaluator.

SECURITY: refresh_dynamic_segment builds SQL from a WHITELIST of allowed rule
fields mapped to fixed column names. JSON key names are never interpolated into
SQL; only parameterised values are passed. Unknown keys → ValueError.

GRACEFUL-EMPTY: if cache.wh_customer_insight is absent, the query yields zero
members and returns 0 (no error).
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from domain.entities.segment import (
    ALLOWED_RULE_KEYS,
    MEMBER_SOURCE_MANUAL,
    MEMBER_SOURCE_RULE,
    Segment,
    SegmentMember,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_missing_table_error(exc: Exception) -> bool:
    """Return True for SQLite 'no such table' errors (cache tables not yet populated)."""
    msg = str(exc).lower()
    return "no such table" in msg


class SegmentService:
    """Handles segment CRUD and dynamic member refresh."""

    def __init__(self, segment_repo: Any, conn: sqlite3.Connection) -> None:
        self._repo = segment_repo
        self._conn = conn

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create_segment(self, data: dict) -> Segment:
        """Validate and store a new segment. Returns the created Segment."""
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("segment name is required")
        is_dynamic = bool(data.get("is_dynamic", False))
        definition = data.get("definition")
        if is_dynamic and definition:
            _validate_rule_keys(definition)
        now = _utc_now()
        seg = Segment(
            segment_id=data.get("segment_id") or str(uuid.uuid4()),
            name=name,
            is_dynamic=is_dynamic,
            created_at=now,
            updated_at=now,
            description=data.get("description"),
            definition=definition,
            owner_user_id=data.get("owner_user_id"),
        )
        self._repo.insert(seg)
        return seg

    def get_segment(self, segment_id: str) -> Segment | None:
        """Return segment by ID, or None if not found."""
        return self._repo.get_by_id(segment_id)

    def update_segment(self, segment_id: str, **kwargs: Any) -> None:
        """Persist mutable segment fields supplied as keyword arguments."""
        seg = self._repo.get_by_id(segment_id)
        if seg is None:
            raise ValueError(f"segment {segment_id!r} not found")
        if "name" in kwargs:
            name = (kwargs["name"] or "").strip()
            if not name:
                raise ValueError("segment name is required")
            seg.name = name
        if "description" in kwargs:
            seg.description = kwargs["description"]
        if "is_dynamic" in kwargs:
            seg.is_dynamic = bool(kwargs["is_dynamic"])
        if "definition" in kwargs:
            seg.definition = kwargs["definition"]
        if "owner_user_id" in kwargs:
            seg.owner_user_id = kwargs["owner_user_id"]
        if seg.is_dynamic and seg.definition:
            _validate_rule_keys(seg.definition)
        seg.updated_at = _utc_now()
        self._repo.update(seg)

    def list_segments(self) -> list[Segment]:
        """Return all segments."""
        return self._repo.list()

    # ── Member management ──────────────────────────────────────────────────────

    def add_member(self, segment_id: str, party_id: str) -> None:
        """Manually add a party to a segment (source='manual')."""
        self._repo.upsert_member(
            SegmentMember(
                segment_id=segment_id,
                party_id=party_id,
                source=MEMBER_SOURCE_MANUAL,
                added_at=_utc_now(),
            )
        )

    def remove_member(self, segment_id: str, party_id: str) -> None:
        """Remove a party from a segment."""
        self._repo.delete_member(segment_id, party_id)

    def list_members(self, segment_id: str) -> list[SegmentMember]:
        """Return all members of a segment."""
        return self._repo.list_members(segment_id)

    # ── Dynamic refresh ────────────────────────────────────────────────────────

    def refresh_dynamic_segment(self, segment_id: str) -> int:
        """Re-evaluate the segment's rule definition and recompute rule-sourced members.

        Manual members are preserved. Returns the number of members upserted.

        SECURITY INVARIANT: SQL is built from a fixed column whitelist; rule values
        are always passed as query parameters — never interpolated. Unknown rule keys
        are rejected before any SQL is built.
        """
        seg = self._repo.get_by_id(segment_id)
        if seg is None:
            raise ValueError(f"segment {segment_id!r} not found")
        if not seg.is_dynamic:
            raise ValueError("segment is not dynamic; use manual member management")
        if not seg.definition:
            raise ValueError("dynamic segment has no rule definition")

        rule = _parse_and_validate_rule(seg.definition)
        party_ids = self._evaluate_rule(rule)

        # Purge stale rule members, then insert fresh set.
        self._repo.delete_rule_members(segment_id)
        now = _utc_now()
        for pid in party_ids:
            self._repo.upsert_member(
                SegmentMember(
                    segment_id=segment_id,
                    party_id=pid,
                    source=MEMBER_SOURCE_RULE,
                    added_at=now,
                )
            )
        return len(party_ids)

    def _evaluate_rule(self, rule: dict) -> list[str]:
        """Translate a validated rule dict into SQL and return matching party_ids."""
        needs_orders = bool(rule.get("days_since_last_order_gte"))
        needs_insight = bool(
            rule.get("value_group") or rule.get("customer_status") or rule.get("channel_preference")
        )
        if needs_orders:
            query, args = _build_query_with_having(rule, needs_insight)
        else:
            query, args = _build_query_no_having(rule, needs_insight)

        try:
            cur = self._conn.execute(query, args)
        except Exception as exc:
            if _is_missing_table_error(exc):
                return []
            raise
        return [row[0] for row in cur.fetchall()]


# ── Rule parsing helpers (module-level for testability) ────────────────────────

def _validate_rule_keys(definition: dict | str) -> None:
    """Reject any unknown key in the rule definition (security boundary)."""
    if isinstance(definition, str):
        try:
            raw = json.loads(definition)
        except json.JSONDecodeError as exc:
            raise ValueError(f"segment definition is not valid JSON: {exc}") from exc
    else:
        raw = definition
    for k in raw:
        if k not in ALLOWED_RULE_KEYS:
            raise ValueError(
                f"unknown segment rule key {k!r} — allowed: {sorted(ALLOWED_RULE_KEYS)}"
            )


def _parse_and_validate_rule(definition: dict | str) -> dict:
    _validate_rule_keys(definition)
    return definition if isinstance(definition, dict) else json.loads(definition)


def _build_query_no_having(rule: dict, needs_insight: bool) -> tuple[str, list]:
    """Simple WHERE-only query for insight-only rules. All values parameterised."""
    where, args = _insight_where_clauses(rule)
    sql = "SELECT DISTINCT p.party_id FROM crm_party p"
    if needs_insight:
        sql += (
            " LEFT JOIN crm_party_identity pi2"
            " ON pi2.party_id = p.party_id AND pi2.identity_type = 'sapo_customer'"
            " LEFT JOIN cache.wh_customer_insight ci"
            " ON ci.customer_id = CAST(pi2.identity_value AS INTEGER)"
        )
    sql += " WHERE p.is_merged = 0 AND p.status = 'active'"
    if where:
        sql += " AND " + " AND ".join(where)
    return sql, args


def _build_query_with_having(rule: dict, needs_insight: bool) -> tuple[str, list]:
    """GROUP BY + HAVING query when days_since_last_order_gte is present.

    REACTIVATION SEMANTIC: parties with NO orders are excluded by the HAVING clause
    (MAX(date_key) IS NULL → elapsed days expression returns NULL → NULL >= threshold
    is false). This is intentional: parties with no orders are acquisition targets,
    not reactivation candidates.
    """
    where, args = _insight_where_clauses(rule)
    # days_since_last_order_gte goes into HAVING (MAX aggregate).
    having = (
        "(julianday('now') - julianday("
        "substr(CAST(MAX(oh.date_key) AS TEXT), 1, 4) || '-' ||"
        "substr(CAST(MAX(oh.date_key) AS TEXT), 5, 2) || '-' ||"
        "substr(CAST(MAX(oh.date_key) AS TEXT), 7, 2)"
        ")) >= ?"
    )
    args.append(rule["days_since_last_order_gte"])

    sql = (
        "SELECT p.party_id FROM crm_party p"
        " LEFT JOIN crm_party_identity pi2"
        " ON pi2.party_id = p.party_id AND pi2.identity_type = 'sapo_customer'"
    )
    if needs_insight:
        sql += (
            " LEFT JOIN cache.wh_customer_insight ci"
            " ON ci.customer_id = CAST(pi2.identity_value AS INTEGER)"
        )
    sql += (
        " LEFT JOIN cache.wh_order_hdr oh"
        " ON oh.customer_id = CAST(pi2.identity_value AS INTEGER)"
        " WHERE p.is_merged = 0 AND p.status = 'active'"
    )
    if where:
        sql += " AND " + " AND ".join(where)
    sql += f" GROUP BY p.party_id HAVING {having}"
    return sql, args


def _insight_where_clauses(rule: dict) -> tuple[list[str], list]:
    """Build WHERE clauses + args for insight fields (value_group, customer_status,
    channel_preference). Column names are hard-coded — never from user input."""
    where: list[str] = []
    args: list = []
    value_group = rule.get("value_group")
    if value_group:
        placeholders = ",".join("?" * len(value_group))
        where.append(f"ci.value_group IN ({placeholders})")
        args.extend(value_group)
    if rule.get("customer_status"):
        where.append("ci.customer_status = ?")
        args.append(rule["customer_status"])
    if rule.get("channel_preference"):
        where.append("ci.channel_preference = ?")
        args.append(rule["channel_preference"])
    return where, args
