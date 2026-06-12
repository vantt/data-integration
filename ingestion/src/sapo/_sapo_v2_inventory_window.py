"""
Sapo Inventory Transactions v2 — Date Window Helpers
Pure date/timezone utilities. No network I/O.

Window definitions (all times inclusive):
  hour    : [floor(now_ict, h) - 1h .. floor(now_ict, h) + 1h - 1s]
  day     : [today_ict 00:00:00 .. today_ict 23:59:59]
  backfill: iterate calendar-month windows from backfill_start through now (ICT)
  custom  : caller supplies start_utc_iso / end_utc_iso directly (pass-through)
"""

from datetime import datetime, timezone, timedelta, date
from typing import List, Tuple, Optional
import calendar

# ICT = Asia/Ho_Chi_Minh = UTC+7 (fixed offset, no DST)
ICT = timezone(timedelta(hours=7))


def iso_z(dt: datetime) -> str:
    """Convert any timezone-aware datetime to UTC ISO string ending in Z."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_ict(inject: Optional[datetime] = None) -> datetime:
    """Return current time in ICT. Pass inject for testing."""
    if inject is not None:
        return inject if inject.tzinfo is not None else inject.replace(tzinfo=ICT)
    return datetime.now(ICT)


def compute_hour_window(now_ict: Optional[datetime] = None) -> Tuple[str, str]:
    """
    Return (start_utc_iso, end_utc_iso) for the current + previous hour window.
    start = floor(now_ict, h) - 1h
    end   = floor(now_ict, h) + 1h - 1s
    """
    now = _now_ict(now_ict)
    floored = now.replace(minute=0, second=0, microsecond=0)
    start = floored - timedelta(hours=1)
    end = floored + timedelta(hours=1) - timedelta(seconds=1)
    return iso_z(start), iso_z(end)


def compute_day_window(now_ict: Optional[datetime] = None) -> Tuple[str, str]:
    """
    Return (start_utc_iso, end_utc_iso) for today ICT [00:00:00 .. 23:59:59].
    """
    now = _now_ict(now_ict)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    return iso_z(start), iso_z(end)


def month_windows(
    backfill_start_date_str: str = "2021-05-01",
    now_ict: Optional[datetime] = None,
) -> List[Tuple[str, str]]:
    """
    Return list of (start_utc_iso, end_utc_iso) for each calendar month from
    backfill_start through the current month (inclusive), in chronological order.

    Each month window: [day1 00:00:00 ICT .. lastday 23:59:59 ICT]

    Args:
        backfill_start_date_str: First date to include (YYYY-MM-DD); only year+month used.
        now_ict: Injectable current time (for tests). Defaults to datetime.now(ICT).
    """
    now = _now_ict(now_ict)
    start_date = date.fromisoformat(backfill_start_date_str)

    windows: List[Tuple[str, str]] = []
    year, month = start_date.year, start_date.month

    while (year, month) <= (now.year, now.month):
        _, last_day = calendar.monthrange(year, month)
        w_start = datetime(year, month, 1, 0, 0, 0, tzinfo=ICT)
        w_end = datetime(year, month, last_day, 23, 59, 59, tzinfo=ICT)
        windows.append((iso_z(w_start), iso_z(w_end)))

        # Advance to next month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

    return windows
