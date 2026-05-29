"""Search adapter tests against the seeded temp DuckDB."""
from __future__ import annotations

from app.adapters.outbound.duckdb.search import DuckDbSearchAdapter


def test_resolve_order_exact_case_insensitive(seeded_db_path: str) -> None:
    adapter = DuckDbSearchAdapter(seeded_db_path)
    assert adapter.resolve_order("ord-normal") == "ORD-NORMAL"
    assert adapter.resolve_order("MISSING") is None
    assert adapter.resolve_order("") is None


def test_resolve_customer_by_id(seeded_db_path: str) -> None:
    adapter = DuckDbSearchAdapter(seeded_db_path)
    hits = adapter.resolve_customer("CUST-1")
    assert len(hits) == 1
    assert hits[0].customer_id == "CUST-1"
    assert hits[0].value_group == "VALUE_GOLD"


def test_resolve_customer_by_phone_digits_normalised(seeded_db_path: str) -> None:
    adapter = DuckDbSearchAdapter(seeded_db_path)
    # Stored as '0901234567'; query with separators must still match.
    hits = adapter.resolve_customer("090-123-4567")
    assert [h.customer_id for h in hits] == ["CUST-1"]


def test_resolve_customer_by_email(seeded_db_path: str) -> None:
    adapter = DuckDbSearchAdapter(seeded_db_path)
    hits = adapter.resolve_customer("BUYER@US.COM")
    assert [h.customer_id for h in hits] == ["CUST-2"]


def test_resolve_customer_empty_query(seeded_db_path: str) -> None:
    adapter = DuckDbSearchAdapter(seeded_db_path)
    assert adapter.resolve_customer("   ") == []


# --- order_id fallback tests (root-cause fix for bug: order_id != order_code) ----------

def test_resolve_order_by_order_id_returns_order_code(seeded_db_path: str) -> None:
    """Searching by numeric order_id must return the canonical order_code."""
    adapter = DuckDbSearchAdapter(seeded_db_path)
    # Seed: order_id='9991', order_code='CODE-ALPHA'
    assert adapter.resolve_order("9991") == "CODE-ALPHA"


def test_resolve_order_by_order_code_still_works(seeded_db_path: str) -> None:
    """order_code search must continue to work after adding order_id fallback."""
    adapter = DuckDbSearchAdapter(seeded_db_path)
    assert adapter.resolve_order("code-alpha") == "CODE-ALPHA"   # case-insensitive
    assert adapter.resolve_order("CODE-ALPHA") == "CODE-ALPHA"


def test_resolve_order_code_priority_over_id(seeded_db_path: str) -> None:
    """order_code match wins when the query string could match both columns."""
    adapter = DuckDbSearchAdapter(seeded_db_path)
    # 'ORD-NORMAL' matches order_code only; verify no cross-match confusion.
    assert adapter.resolve_order("ORD-NORMAL") == "ORD-NORMAL"


def test_resolve_order_junk_returns_none(seeded_db_path: str) -> None:
    """A query matching neither order_code nor order_id must return None."""
    adapter = DuckDbSearchAdapter(seeded_db_path)
    assert adapter.resolve_order("DOES-NOT-EXIST-XYZ") is None
    assert adapter.resolve_order("") is None
    assert adapter.resolve_order("   ") is None
