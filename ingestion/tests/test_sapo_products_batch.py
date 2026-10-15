"""Behaviour of the incremental Sapo products batch (`sapo.products.products`).

Pins what the nightly products batch does with a fake Sapo session: request parameters,
the envelope it yields, the early stop after `min_overlap_items` old products and the
stop on an empty page. The page-fetch helper is shared with the daily snapshot, so these
tests guard the batch against changes made for the snapshot.
"""
import os
import sys

import dlt
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import sapo.client as sapo_client  # noqa: E402
from sapo.products import products  # noqa: E402


class FakeResponse:
    def __init__(self, body, status_code=200, headers=None):
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


class FakeSession:
    """Serves `pages[page]` for products.json; missing pages are empty."""

    def __init__(self, pages, total):
        self.pages = pages
        self.total = total
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params)))
        page = params["page"]
        return FakeResponse({
            "metadata": {"total": self.total, "page": page, "limit": params["limit"]},
            "products": self.pages.get(page, []),
        })


class FakeClient:
    base_url = "https://shop.example/admin"
    request_delay = 0

    def __init__(self, session):
        self.session = session

    def refresh_session(self, current_session):
        return current_session


def _product(pid, modified_on):
    return {"id": pid, "modified_on": modified_on, "name": f"Fake product {pid}", "variants": []}


@pytest.fixture
def no_sleep(monkeypatch):
    import time
    monkeypatch.setattr(time, "sleep", lambda _s: None)


def _install(monkeypatch, session):
    monkeypatch.setattr(sapo_client, "get_sapo_client", lambda: FakeClient(session))


def test_batch_reads_until_empty_page_and_yields_envelopes(monkeypatch, no_sleep):
    session = FakeSession({
        1: [_product(3, "2026-10-03T00:00:00Z"), _product(2, "2026-10-02T00:00:00Z")],
        2: [_product(1, "2026-10-01T00:00:00Z")],
    }, total=3)
    _install(monkeypatch, session)

    rows = list(products(max_pages=10, page_size=2, min_overlap_items=100))

    assert [r["entity_id"] for r in rows] == ["3", "2", "1"]
    first = rows[0]
    assert first["entity_type"] == "product"
    assert first["ingest_method"] == "batch_sync"
    assert first["event_type"] == "snapshot"
    assert first["event_timestamp"] == "2026-10-03T00:00:00Z"
    assert (first["year"], first["month"]) == ("2026", "10")
    assert first["payload"]["name"] == "Fake product 3"
    assert len(first["payload_hash"]) == 32
    assert first["sync_metadata"]["source_system"] == "sapo_v2"
    # pages 1, 2, then page 3 twice (one retry of an empty page) before stopping
    assert [c[1]["page"] for c in session.calls] == [1, 2, 3, 3]
    assert session.calls[0] == (
        "https://shop.example/admin/products.json",
        {"page": 1, "limit": 2, "sort_by": "modified_on", "sort_direction": "desc"},
    )


def test_batch_stops_early_after_enough_old_products(monkeypatch, no_sleep):
    session = FakeSession({
        1: [_product(9, "2026-10-09T00:00:00Z"), _product(8, "2026-10-08T00:00:00Z")],
        2: [_product(7, "2026-10-07T00:00:00Z"), _product(6, "2026-10-06T00:00:00Z")],
        3: [_product(5, "2026-10-05T00:00:00Z"), _product(4, "2026-10-04T00:00:00Z")],
    }, total=6)
    _install(monkeypatch, session)
    cursor = dlt.sources.incremental("sync_metadata.event_timestamp", initial_value="2026-10-07T00:00:00Z")

    rows = list(products(max_pages=10, page_size=2, min_overlap_items=2, first_timestamp=cursor))

    assert [r["entity_id"] for r in rows] == ["9", "8"]
    # page 2 holds the second consecutive old product, so page 3 is never requested
    assert [c[1]["page"] for c in session.calls] == [1, 2]
