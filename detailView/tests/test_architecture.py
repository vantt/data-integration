"""Hexagonal-architecture guards.

1. domain/* and application/* must NOT import infrastructure (duckdb, fastapi).
2. The three concrete adapters must satisfy their runtime_checkable Protocol ports.
3. Smoke-queries confirm the SQL executes against :memory: without raising.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.adapters.outbound.duckdb.customer_repository import DuckDbCustomerRepository
from app.adapters.outbound.duckdb.order_repository import DuckDbOrderRepository
from app.adapters.outbound.duckdb.search import DuckDbSearchAdapter
from app.domain.ports import CustomerRepository, OrderRepository, SearchPort

_APP_ROOT = Path(__file__).resolve().parent.parent / "app"
_FORBIDDEN = re.compile(r"^\s*(import|from)\s+(duckdb|fastapi)\b", re.MULTILINE)


def _source_files(*relative_dirs: str) -> list[Path]:
    files: list[Path] = []
    for rel in relative_dirs:
        files.extend((_APP_ROOT / rel).rglob("*.py"))
    return files


def test_domain_and_application_have_no_infra_imports() -> None:
    offenders: list[str] = []
    for path in _source_files("domain", "application"):
        text = path.read_text(encoding="utf-8")
        if _FORBIDDEN.search(text):
            offenders.append(str(path))
    assert not offenders, f"infra imports leaked into pure layers: {offenders}"


def test_repositories_satisfy_ports() -> None:
    db = ":memory:"
    assert isinstance(DuckDbOrderRepository(db), OrderRepository)
    assert isinstance(DuckDbCustomerRepository(db), CustomerRepository)
    assert isinstance(DuckDbSearchAdapter(db), SearchPort)


def test_repositories_smoke_query_nonexistent_returns_none(seeded_db_path: str) -> None:
    """Smoke: real SQL executes; a missing code/id returns None, not an exception.

    This closes the silent-SQL-failure gap: a structural isinstance() match does not
    guarantee the queries compile and run. Exercises both repos against the seeded DB.
    """
    order_repo = DuckDbOrderRepository(seeded_db_path)
    result = order_repo.get_by_code("NONEXISTENT-ORDER-XYZ")
    assert result is None, "get_by_code must return None for unknown code"

    customer_repo = DuckDbCustomerRepository(seeded_db_path)
    result = customer_repo.get_by_id("NONEXISTENT-CUSTOMER-XYZ")
    assert result is None, "get_by_id must return None for unknown id"
