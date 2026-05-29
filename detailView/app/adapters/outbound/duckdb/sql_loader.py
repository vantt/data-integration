"""Loads ``.sql`` files from the sibling ``queries/`` directory, cached per process.

Keeps SQL out of the Python modules (so repositories stay small and readable) while
avoiding repeated disk reads. The files are static assets shipped with the adapter.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_QUERIES_DIR = Path(__file__).resolve().parent / "queries"


@lru_cache(maxsize=None)
def load_sql(name: str) -> str:
    """Return the text of ``queries/<name>.sql`` (cached).

    Args:
        name: File stem without the ``.sql`` extension (e.g. ``"order_header"``).

    Raises:
        FileNotFoundError: If the query file does not exist (programming error).
    """
    path = _QUERIES_DIR / f"{name}.sql"
    if not path.is_file():
        raise FileNotFoundError(f"SQL query not found: {path}")
    return path.read_text(encoding="utf-8")
