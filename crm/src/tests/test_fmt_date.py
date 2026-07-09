"""test_fmt_date.py — unit tests for fmt_date.py's ISO parsing + ICT formatting.

Coverage: format_datetime_ict across every input shape the app actually produces
(Z-suffixed UTC, space-separated +HH:MM offset — the DuckDB TIMESTAMPTZ str() shape,
both with and without microseconds — and bare date-only strings), plus format_date_ict
never appending "ICT" itself (so callers that add a literal "ICT" suffix are correct to).

Regression guard: _parse_iso previously only handled T/Z-suffixed strings, silently
returning the raw unparsed string for space+offset timestamps (e.g. order create/ship/
payment times from the warehouse mart) — and format_datetime_ict's date-vs-datetime
heuristic checked for "T"/"Z" specifically, which silently dropped the time-of-day even
after the parsing fix, for that same space+offset shape.
"""
from __future__ import annotations

import pathlib
import sys

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from adapters.inbound.web.fmt_date import format_date_ict, format_datetime_ict  # noqa: E402


class TestFormatDatetimeIct:
    def test_z_suffixed_utc(self):
        assert format_datetime_ict("2026-03-03T02:51:56Z") == "03/03/2026 09:51 ICT"

    def test_z_suffixed_utc_with_microseconds(self):
        assert format_datetime_ict("2026-03-03T02:51:56.123456Z") == "03/03/2026 09:51 ICT"

    def test_space_separated_with_offset(self):
        # DuckDB TIMESTAMPTZ -> str() shape: "YYYY-MM-DD HH:MM:SS+HH:MM"
        assert format_datetime_ict("2026-03-03 09:51:56+07:00") == "03/03/2026 09:51 ICT"

    def test_space_separated_with_offset_and_microseconds(self):
        assert format_datetime_ict("2026-03-03 09:51:56.500000+07:00") == "03/03/2026 09:51 ICT"

    def test_bare_date_has_no_time_suffix(self):
        assert format_datetime_ict("2026-03-03") == "03/03/2026"

    def test_none_returns_dash(self):
        assert format_datetime_ict(None) == "—"

    def test_unparseable_falls_back_to_raw_string(self):
        raw = "not-a-date"
        assert format_datetime_ict(raw) == raw


class TestFormatDateIct:
    def test_never_appends_ict_suffix(self):
        # format_date_ict (and its format_ict alias) return date-only — callers that
        # append a literal "ICT" after it are doing so correctly, unlike
        # format_datetime_ict callers (which must NOT, since it self-appends "ICT").
        result = format_date_ict("2026-03-03T02:51:56Z")
        assert result == "03/03/2026"
        assert "ICT" not in result
