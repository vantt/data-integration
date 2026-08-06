"""suggestion_settings_service.py — Customer 360 "Cài đặt gợi ý" panel (P07).

Composes the opportunity-type catalog (ActionCatalogPort) with per-party suppression
state (ActionSuppressionPort) into a scenario_group-grouped view model, and validates
writes against the catalog before delegating. No SQL, no HTTP, no template imports —
pure composition + date conversion.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol
from zoneinfo import ZoneInfo

from domain.entities.action_dismissal import ActionDismissal
from domain.entities.action_scenario import ActionScenario

_ICT = ZoneInfo("Asia/Ho_Chi_Minh")
_MAX_HORIZON_DAYS = 365


# ── Internal port protocols (mirrors WorklistQueryService's pattern) ────────


class _CatalogPort(Protocol):
    def list_catalog(self) -> list[ActionScenario]: ...


class _SuppressionPort(Protocol):
    def suppress(self, party_id: str, action_type: str, source_mart: str,
                 until_utc: str, user_id: Optional[str] = None) -> None: ...
    def unsuppress(self, party_id: str, action_type: str, source_mart: str) -> None: ...
    def list_dismissals_for_party(self, party_id: str) -> list[ActionDismissal]: ...


# ── View model ────────────────────────────────────────────────────────────────


@dataclass
class SuggestionSettingRow:
    """One (action_type, mart) toggle row for the panel."""
    action_type: str
    source_mart: str
    description_vi: str
    is_globally_disabled: bool   # catalog enabled=0 — never togglable, greyed in UI
    is_suppressed: bool          # a non-expired dismissal exists for this party
    is_expired: bool             # a dismissal exists but its dismissed_until has passed
    until_date_ict: Optional[str]   # 'YYYY-MM-DD', None if never suppressed
    set_by_display: Optional[str]   # who set it ("Hệ thống" fallback), None if never suppressed


@dataclass
class SuggestionSettingGroup:
    scenario_group: str
    rows: list[SuggestionSettingRow]


# ── Date conversion (ICT date input <-> stored UTC instant) ──────────────────


def _parse_utc(iso_utc: str) -> datetime:
    """Parse the exact format this app writes: '%Y-%m-%dT%H:%M:%S.%fZ' (UTC)."""
    return datetime.strptime(iso_utc, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def _format_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def _until_date_ict_to_utc(until_date_ict: str) -> str:
    """Convert a staff-picked 'YYYY-MM-DD' (interpreted as end-of-day ICT) to a stored
    UTC instant. Never store a bare date — it would sort before every '...T..Z'
    timestamp already in the column and the suppression would expire immediately."""
    try:
        d = datetime.strptime(until_date_ict, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"Ngày không hợp lệ: {until_date_ict!r}") from exc

    end_of_day_ict = datetime(d.year, d.month, d.day, 23, 59, 59, 999000, tzinfo=_ICT)
    now_utc = datetime.now(timezone.utc)

    if end_of_day_ict <= now_utc:
        raise ValueError("Ngày kết thúc phải ở tương lai")
    if end_of_day_ict > now_utc + timedelta(days=_MAX_HORIZON_DAYS):
        raise ValueError(f"Ngày kết thúc không được quá {_MAX_HORIZON_DAYS} ngày kể từ hôm nay")

    return _format_utc(end_of_day_ict)


# ── Service ────────────────────────────────────────────────────────────────────


class SuggestionSettingsService:
    def __init__(self, catalog: _CatalogPort, suppression: _SuppressionPort) -> None:
        self._catalog = catalog
        self._suppression = suppression

    def get_settings(self, party_id: str) -> list[SuggestionSettingGroup]:
        """Group the full catalog by scenario_group, joined to this party's dismissals."""
        catalog = self._catalog.list_catalog()
        dismissals = {
            (d.action_type, d.source_mart): d
            for d in self._suppression.list_dismissals_for_party(party_id)
        }
        now_utc = datetime.now(timezone.utc)

        groups: dict[str, list[SuggestionSettingRow]] = {}
        for scenario in catalog:
            d = dismissals.get((scenario.action_type, scenario.mart))
            is_suppressed = is_expired = False
            until_date_ict = set_by_display = None
            if d is not None:
                until_date_ict = _parse_utc(d.dismissed_until).astimezone(_ICT).strftime("%Y-%m-%d")
                set_by_display = d.dismissed_by_display
                if _parse_utc(d.dismissed_until) > now_utc:
                    is_suppressed = True
                else:
                    is_expired = True
            groups.setdefault(scenario.scenario_group, []).append(SuggestionSettingRow(
                action_type=scenario.action_type,
                source_mart=scenario.mart,
                description_vi=scenario.description_vi,
                is_globally_disabled=not scenario.enabled,
                is_suppressed=is_suppressed,
                is_expired=is_expired,
                until_date_ict=until_date_ict,
                set_by_display=set_by_display,
            ))
        return [SuggestionSettingGroup(scenario_group=g, rows=rows) for g, rows in groups.items()]

    def suppress(self, party_id: str, action_type: str, source_mart: str,
                 until_date_ict: str, user_id: Optional[str] = None) -> None:
        """Turn an opportunity type off for a party. Validates (action_type, source_mart)
        exists in the catalog and is not globally disabled — prevents writing an orphan
        row the panel would never show, or a pointless toggle on an already-dead type."""
        catalog = self._catalog.list_catalog()
        scenario = next(
            (s for s in catalog if s.action_type == action_type and s.mart == source_mart),
            None,
        )
        if scenario is None:
            raise ValueError(f"Không tìm thấy loại gợi ý ({action_type}, {source_mart}) trong danh mục")
        if not scenario.enabled:
            raise ValueError(f"{action_type} đang tắt toàn hệ thống — không thể tắt riêng cho khách")

        until_utc = _until_date_ict_to_utc(until_date_ict)
        self._suppression.suppress(party_id, action_type, source_mart, until_utc, user_id)

    def unsuppress(self, party_id: str, action_type: str, source_mart: str) -> None:
        self._suppression.unsuppress(party_id, action_type, source_mart)
