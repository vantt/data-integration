"""Shared timestamp utilities for the CRM Python server."""
from __future__ import annotations
from datetime import datetime, timezone


def utc_now() -> str:
    """Return current UTC time as ISO-8601 with milliseconds and Z suffix.

    Format: 2026-06-29T10:30:00.123Z
    """
    now = datetime.now(timezone.utc)
    ms = now.microsecond // 1000
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms:03d}Z"
