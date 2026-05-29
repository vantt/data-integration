"""Tiny fetch helpers turning DuckDB cursor results into column-keyed dicts.

Repositories work against ``dict[str, Any]`` rows (mapped via ``row_coercion``) instead
of positional tuples, so column order in the ``.sql`` files never silently breaks mapping.
"""
from __future__ import annotations

from typing import Any

import duckdb


def _columns(cursor: duckdb.DuckDBPyConnection) -> list[str]:
    # cursor.description -> list of 7-tuples; first element is the column name.
    return [col[0] for col in (cursor.description or [])]


def fetch_one_dict(
    connection: duckdb.DuckDBPyConnection, sql: str, params: list[Any]
) -> dict[str, Any] | None:
    """Execute ``sql`` and return the first row as a dict, or None if no rows."""
    cursor = connection.execute(sql, params)
    row = cursor.fetchone()
    if row is None:
        return None
    return dict(zip(_columns(cursor), row))


def fetch_all_dicts(
    connection: duckdb.DuckDBPyConnection, sql: str, params: list[Any]
) -> list[dict[str, Any]]:
    """Execute ``sql`` and return every row as a column-keyed dict."""
    cursor = connection.execute(sql, params)
    rows = cursor.fetchall()
    columns = _columns(cursor)
    return [dict(zip(columns, row)) for row in rows]
