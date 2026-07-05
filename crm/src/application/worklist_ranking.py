"""Pure ranking module — merges action-queue items and manual tasks into one
urgency-banded, sorted worklist structure.

No HTTP or DB imports — fully unit-testable. Called by screen_worklist adapter.

Two opposite priority scales must be normalized before comparison:
  - wh_action_queue.priority (priority_rank): lower number = more urgent (1=CALL_NOW)
  - crm_task.priority: higher number = more urgent (2=urgent)
Normalize both to urgency_score where higher = more urgent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional


# ---------------------------------------------------------------------------
# ICT helper
# ---------------------------------------------------------------------------

def today_ict() -> date:
    """Return the current date in ICT (UTC+7) to avoid 0h–7h boundary drift."""
    return datetime.now(timezone(timedelta(hours=7))).date()


# ---------------------------------------------------------------------------
# Urgency normalization
# ---------------------------------------------------------------------------

def urgency_score(kind: str, priority_or_rank: int) -> int:
    """Normalize priority to urgency_score where higher = more urgent.

    Actions use priority_rank (warehouse tier): lower rank = more urgent.
      urgency = 10 - priority_rank  → CALL_NOW(rank=1) → 9, ELSE(rank=9) → 1
    Tasks use crm priority: 0=normal, 1=high, 2=urgent (higher = more urgent).
      urgency = 7 + priority       → normal → 7, urgent → 9

    Both scales produce scores in [1, 9]; an urgent task and CALL_NOW share
    urgency=9 so they interleave by value when tied.
    """
    if kind == "action":
        return max(1, min(9, 10 - int(priority_or_rank)))
    # kind == "task"
    return 7 + int(priority_or_rank)


# ---------------------------------------------------------------------------
# WorklistRow
# ---------------------------------------------------------------------------

@dataclass
class WorklistRow:
    """Unified row for the ranked worklist.

    payload holds the original ActionQueueItem or Task object so templates
    can access all fields without re-fetching.
    """
    kind: str           # 'action' | 'task'
    band: int           # 0=overdue, 1=today/urgent, 2=on-track, 3=neglected
    urgency: int        # normalized urgency_score (higher = more urgent)
    value: int          # value_at_stake_vnd (action) or 0 (task)
    neglect_days: int   # days since pending_since / due_at (for badge display)
    ref_id: str         # action_id or task_id
    payload: Any        # original entity (ActionQueueItem | Task)
    pending_date: Optional[date] = None  # pre-parsed pending_since; reused by sort keys
    value_group: str = ""  # VIP/GOLD/HIGH/MID/LOW (item 3 — B3 auto-expand)
    wake_badge: bool = False  # True when snoozed_until passed within last 24h (item 4)

    @property
    def should_show_neglect_badge(self) -> bool:
        """True for actions waiting 1–6 days; 7+ days are already routed to band 3 (Treo lâu)."""
        return 1 <= self.neglect_days <= 6


# ---------------------------------------------------------------------------
# Date parsing helpers
# ---------------------------------------------------------------------------

def _parse_date(value: Optional[str]) -> Optional[date]:
    """Parse YYYY-MM-DD or ISO datetime string to a date. Returns None on failure.

    Fast path: if the string is exactly 10 chars (YYYY-MM-DD), parse directly.
    Warehouse fields (pending_since, snoozed_until, generated_date) always use
    this format; the slow strptime loop is only reached for task timestamps.
    """
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S+00:00"):
        try:
            return datetime.strptime(value[:26], fmt[:len(fmt)]).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Band assignment
# ---------------------------------------------------------------------------

def assign_band(
    kind: str,
    urgency: int,
    due_date: Optional[date],
    pending_date: Optional[date],
    snoozed_until: Optional[date],
    status: str,
    today: date,
) -> int:
    """Assign urgency band (first match wins).

    Band 0 — overdue manual tasks: deadline already passed; surface first so
              deadlines are never buried.
    Band 1 — today / urgent: task due today, urgency>=9 (urgent task or CALL_NOW
              action), or woke-up snoozed action (was snoozed, now past due).
    Band 3 — neglected actions: pending >= 7 days and not already in band 1.
              Collapsed by default in UI to reduce overwhelm.
    Band 2 — on-track: everything else.
    """
    if kind == "task" and due_date is not None and due_date < today:
        return 0

    if kind == "task" and due_date == today:
        return 1
    if urgency >= 9:
        return 1
    if kind == "action" and status == "snoozed" and snoozed_until is not None and snoozed_until <= today:
        return 1

    if kind == "action" and pending_date is not None:
        if (today - pending_date).days >= 7:
            return 3

    return 2


# ---------------------------------------------------------------------------
# Band sort keys
# ---------------------------------------------------------------------------

def _sort_key_b0(row: WorklistRow) -> tuple:
    """Band 0: overdue tasks — most overdue first (due_at asc), then value desc."""
    due = _parse_date(getattr(row.payload, "due_at", None))
    due_ord = due.toordinal() if due else 99999  # missing due sorts last
    return (due_ord, -row.value)


def _sort_key_b1(row: WorklistRow) -> tuple:
    """Band 1: today/urgent — urgency desc, value desc, due asc."""
    due = _parse_date(getattr(row.payload, "due_at", None))
    due_ord = due.toordinal() if due else 99999
    return (-row.urgency, -row.value, due_ord)


def _sort_key_b2(row: WorklistRow) -> tuple:
    """Band 2: on-track — urgency desc, value desc, then oldest pending first."""
    ps_ord = row.pending_date.toordinal() if row.pending_date else 99999
    return (-row.urgency, -row.value, ps_ord)


def _sort_key_b3(row: WorklistRow) -> tuple:
    """Band 3: neglected actions — value desc (highest opportunity first)."""
    return (-row.value,)


_BAND_SORT_KEYS = {0: _sort_key_b0, 1: _sort_key_b1, 2: _sort_key_b2, 3: _sort_key_b3, 4: _sort_key_b1}

# ---------------------------------------------------------------------------
# Band metadata
# ---------------------------------------------------------------------------

_BAND_META = {
    0: {"id": 0, "label": "Quá hạn",        "icon": "🔴", "display_capacity": 10, "is_expanded": True},
    1: {"id": 1, "label": "Hôm nay / Khẩn", "icon": "⏰", "display_capacity": 10, "is_expanded": True},
    2: {"id": 2, "label": "Trong hạn",       "icon": "📋", "display_capacity": 10, "is_expanded": True},
    3: {"id": 3, "label": "Treo lâu",        "icon": "💤", "display_capacity": 5,  "is_expanded": False},
    4: {"id": 4, "label": "Đã liên hệ",      "icon": "✅", "display_capacity": 10, "is_expanded": False},
}


# ---------------------------------------------------------------------------
# Main ranking function
# ---------------------------------------------------------------------------

def rank_worklist(
    actions: list,   # list[ActionQueueItem]
    tasks: list,     # list[Task]
    today: date,
    contacted_party_ids: Optional[set] = None,
) -> dict:
    """Merge actions + tasks into an urgency-banded sorted structure.

    Returns a dict with:
      bands       — list of band dicts [{id, label, icon, rows, count, total_value}]
                    ordered 0→1→2→3. Empty bands are included (count=0) so the
                    template always has a stable structure.
      value_total — sum of value_at_stake_vnd across all actions in the result.
      counts      — {actions: int, tasks: int, total: int}
      task_open   — count of tasks with status not done/cancelled (for KPI strip)
      urgent_count — count of rows in bands 0+1 (for progress KPI)
    """
    _contacted = contacted_party_ids or set()

    rows: list[WorklistRow] = []

    for a in actions:
        rank = int(getattr(a, "priority", 9) or 9)
        us = urgency_score("action", rank)
        pending = _parse_date(getattr(a, "pending_since", None))
        snooze_d = _parse_date(getattr(a, "snoozed_until", None))
        status = getattr(a, "status", "open") or "open"
        band = assign_band("action", us, None, pending, snooze_d, status, today)
        # Actions whose party was positively contacted recently move to band 4.
        pid = getattr(a, "party_id", None) or ""
        if pid and pid in _contacted:
            band = 4
        neglect = (today - pending).days if pending else 0
        # Item 3: value_group for B3 VIP/GOLD auto-expand
        value_group = str(getattr(a, "value_group", "") or "")
        # Item 4: wake_badge — snoozed_until passed within last 24 hours
        wake_badge = False
        raw_snooze = getattr(a, "snoozed_until", None)
        if raw_snooze:
            try:
                if isinstance(raw_snooze, str):
                    snooze_dt = datetime.fromisoformat(
                        raw_snooze.replace("Z", "+00:00")
                    )
                elif isinstance(raw_snooze, datetime):
                    snooze_dt = raw_snooze if raw_snooze.tzinfo else raw_snooze.replace(tzinfo=timezone.utc)
                else:
                    snooze_dt = None
                if snooze_dt is not None:
                    if snooze_dt.tzinfo is None:
                        snooze_dt = snooze_dt.replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    delta = (now - snooze_dt).total_seconds()
                    wake_badge = 0 < delta <= 86400
            except Exception:
                wake_badge = False
        rows.append(WorklistRow(
            kind="action",
            band=band,
            urgency=us,
            value=int(getattr(a, "value_at_stake_vnd", 0) or 0),
            neglect_days=neglect,
            ref_id=str(getattr(a, "action_id", "")),
            payload=a,
            pending_date=pending,
            value_group=value_group,
            wake_badge=wake_badge,
        ))

    for t in tasks:
        prio = int(getattr(t, "priority", 0) or 0)
        us = urgency_score("task", prio)
        due = _parse_date(getattr(t, "due_at", None))
        band = assign_band("task", us, due, None, None, "", today)
        # Claim tasks: if party was recently contacted, move to Band 4 (mirrors action logic).
        pid = getattr(t, "party_id", None) or ""
        if getattr(t, "source", "") == "action_queue_claim" and pid and pid in _contacted:
            band = 4
        neglect = (today - due).days if due and due < today else 0
        rows.append(WorklistRow(
            kind="task",
            band=band,
            urgency=us,
            value=0,
            neglect_days=neglect,
            ref_id=str(getattr(t, "task_id", "")),
            payload=t,
        ))

    # Group into bands and sort within each band
    bands_map: dict[int, list[WorklistRow]] = {0: [], 1: [], 2: [], 3: [], 4: []}
    for row in rows:
        bands_map[row.band].append(row)

    for band_id, band_rows in bands_map.items():
        band_rows.sort(key=_BAND_SORT_KEYS[band_id])

    # Item 3: check band 3 for VIP/GOLD rows — auto-expand and add vip_count badge
    _VIP_GROUPS = {"VIP", "GOLD"}
    b3_vip_rows = [r for r in bands_map[3] if r.value_group in _VIP_GROUPS]
    b3_vip_count = len(b3_vip_rows)

    # Build output structure — band 4 ("Đã liên hệ") renders above band 0 in template.
    bands = []
    for band_id in (4, 0, 1, 2, 3):
        band_rows = bands_map[band_id]
        total_val = sum(r.value for r in band_rows)
        meta = dict(_BAND_META[band_id])  # copy to avoid mutating module-level constant
        if band_id == 3 and b3_vip_count > 0:
            meta["is_expanded"] = True
        bands.append({
            **meta,
            "rows": band_rows,
            "count": len(band_rows),
            "total_value": total_val,
            "vip_count": b3_vip_count if band_id == 3 else 0,
        })

    value_total = sum(int(getattr(a, "value_at_stake_vnd", 0) or 0) for a in actions)
    total_rows = len(rows)
    urgent_count = len(bands_map[0]) + len(bands_map[1])

    return {
        "bands": bands,
        "value_total": value_total,
        "counts": {
            "actions": len(actions),
            "tasks": len(tasks),
            "total": total_rows,
        },
        "task_open": len(tasks),      # all tasks passed in are open (filter applied upstream)
        "urgent_count": urgent_count,  # rows needing attention today
    }
