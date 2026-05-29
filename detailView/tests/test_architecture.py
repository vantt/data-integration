"""Hexagonal-architecture guards.

1. domain/* and application/* must NOT import infrastructure (duckdb, fastapi).
2. The three concrete adapters must satisfy their runtime_checkable Protocol ports.
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
