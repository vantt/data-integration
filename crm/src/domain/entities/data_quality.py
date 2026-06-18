"""Domain entity for data quality summary shown in the data-health footer strip."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DataQualitySummary:
    as_of_str: str = ""                         # ICT formatted, e.g. "2026-06-18 14:30"
    cogs_rate_pct: Optional[float] = None       # COGS coverage percentage (0–100)
    stale_views: list[str] = field(default_factory=list)  # names of stale mart views
