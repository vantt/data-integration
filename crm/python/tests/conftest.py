"""conftest.py — shared pytest fixtures for crm/python/tests/.

sys.path setup:
  - repo root (data-integration/) for crm.python.* namespace
  - crm/python/ for bare domain.* / application.* imports used inside app modules

Fixtures:
  tmp_data_dir   — temporary directory path (str) cleaned up after each test
  crm_db         — CRMDatabase opened in tmp_data_dir (migrations NOT applied)
  seeded_crm_db  — CRMDatabase with migrations applied + one wh_party_seed row
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys
import tempfile

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])   # .../data-integration
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1]) # .../crm/python
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from crm.python.adapters.outbound.sqlite.connection import CRMDatabase  # noqa: E402


@pytest.fixture()
def tmp_data_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture()
def crm_db(tmp_data_dir):
    db = CRMDatabase(tmp_data_dir)
    yield db
    db.close()


@pytest.fixture()
def seeded_crm_db(tmp_data_dir):
    """CRMDatabase with migrations applied and one wh_party_seed row in cache.db."""
    db = CRMDatabase(tmp_data_dir)
    db.apply_migrations()

    cache_path = str(pathlib.Path(tmp_data_dir) / "cache.db")
    cache_conn = sqlite3.connect(cache_path)
    try:
        cache_conn.execute("""
            CREATE TABLE IF NOT EXISTS wh_party_seed (
                customer_id   INTEGER PRIMARY KEY,
                customer_key  TEXT,
                display_name  TEXT,
                phone         TEXT,
                email         TEXT,
                source_contact_quality TEXT,
                contact_quality        TEXT,
                seen_at       TEXT
            )
        """)
        cache_conn.execute("""
            INSERT OR IGNORE INTO wh_party_seed VALUES
              (1001, 'key-cust-001', 'Nguyen Van A', '0901000001',
               'a@test.vn', 'unverified', 'unverified', '2026-06-15T00:00:00Z')
        """)
        cache_conn.commit()
    finally:
        cache_conn.close()

    yield db
    db.close()
