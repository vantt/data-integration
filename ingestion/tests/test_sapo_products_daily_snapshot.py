"""Nightly full capture of Sapo products into the append-only raw table.

Uses a fake Sapo session and fake products only. The dlt tests load into a temporary
filesystem destination with the production layout, so they also prove where the file lands.
"""
import glob
import json
import os
import sys
from datetime import datetime, timezone

import pyarrow.parquet as pq
import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, os.path.join(HERE, ".."))

from sapo import products_daily_snapshot as snap  # noqa: E402
import run_sapo_v2_product_daily_snapshot as runner  # noqa: E402

PROD_LAYOUT = "{table_name}/ingest_method={ingest_method}/year={year}/month={month}/{file_id}.{ext}"
CAPTURED_AT = datetime(2026, 10, 15, 20, 1, tzinfo=timezone.utc)  # 03:01 ICT on 16/10


class FakeResponse:
    def __init__(self, body, status_code=200):
        self.status_code = status_code
        self._body = body
        self.headers = {}

    def json(self):
        return self._body

    def raise_for_status(self):
        pass


class FakeSession:
    def __init__(self, pages, total):
        self.pages = pages
        self.total = total
        self.requested = []

    def get(self, url, params=None, timeout=None):
        self.requested.append(params["page"])
        return FakeResponse({
            "metadata": {"total": self.total, "page": params["page"], "limit": params["limit"]},
            "products": self.pages.get(params["page"], []),
        })


class FakeClient:
    base_url = "https://shop.example/admin"
    request_delay = 0

    def __init__(self, session):
        self.session = session

    def refresh_session(self, current_session):
        return current_session


def _variant(vid, price, on_hand):
    return {
        "id": vid,
        "sku": f"SKU-{vid}",
        "name": f"Fake variant {vid}",
        "barcode": "000",
        "variant_prices": [
            {"price_list_id": 1, "value": price, "name": "Giá bán lẻ",
             "price_list": {"id": 1, "code": "BANLE", "is_cost": False}},
        ],
        "inventories": [
            {"location_id": 10, "variant_id": vid, "on_hand": on_hand, "available": on_hand,
             "committed": 0, "incoming": 0, "onway": 0, "mac": 1000.0},
        ],
    }


def _product(pid, modified_on, price=100000.0):
    return {
        "id": pid,
        "modified_on": modified_on,
        "name": f"Fake product {pid}",
        "status": "active",
        "images": [{"src": "x"}],
        "variants": [_variant(pid * 10, price, 5)],
    }


def _catalogue():
    # page 2 repeats product 3 with a newer modified_on (edited during the scan)
    return {
        1: [_product(5, "2026-10-05T00:00:00Z"), _product(4, "2026-10-04T00:00:00Z")],
        2: [_product(3, "2026-10-15T09:00:00Z", price=120000.0), _product(2, "2026-10-02T00:00:00Z")],
        3: [_product(3, "2026-10-03T00:00:00Z"), _product(1, "2026-10-01T00:00:00Z")],
    }


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    import time
    monkeypatch.setattr(time, "sleep", lambda _s: None)


# --- scan --------------------------------------------------------------------------------------

def test_scan_reads_every_page_until_empty_without_early_stop():
    session = FakeSession(_catalogue(), total=5)
    scan = snap.scan_catalogue(FakeClient(session), page_size=2)

    assert sorted(p["id"] for p in scan.products) == [1, 2, 3, 4, 5]
    assert scan.pages == 3
    assert scan.sapo_total == 5
    # page 4 is empty, retried once, then the scan ends
    assert session.requested == [1, 2, 3, 4, 4]


def test_scan_keeps_one_row_per_product_with_the_latest_modified_on():
    scan = snap.scan_catalogue(FakeClient(FakeSession(_catalogue(), total=5)), page_size=2)

    by_id = {p["id"]: p for p in scan.products}
    assert scan.duplicates == 1
    assert by_id[3]["modified_on"] == "2026-10-15T09:00:00Z"
    assert by_id[3]["variants"][0]["variant_prices"][0]["value"] == 120000.0


def test_scan_raises_when_a_page_fails():
    calls = []

    def failing_fetch(client, session, page, page_size):
        calls.append(page)
        if page == 3:
            raise RuntimeError("HTTP 500 on page 3")
        return {"metadata": {"total": 6}, "products": _catalogue()[page]}

    with pytest.raises(RuntimeError, match="page 3"):
        snap.scan_catalogue(FakeClient(None), page_size=2, fetch_page=failing_fetch)
    assert calls == [1, 2, 3]


# --- envelope ----------------------------------------------------------------------------------

def test_envelopes_share_one_capture_time_and_run_id_and_keep_a_compact_payload():
    scan = snap.scan_catalogue(FakeClient(FakeSession(_catalogue(), total=5)), page_size=2)
    rows = snap.build_envelopes(scan.products, CAPTURED_AT, "run-1")

    assert len(rows) == 5
    assert {r["captured_at"] for r in rows} == {CAPTURED_AT}
    assert {r["capture_run_id"] for r in rows} == {"run-1"}
    assert {r["ingest_method"] for r in rows} == {"daily_snapshot"}
    assert {r["entity_type"] for r in rows} == {"product"}

    row = next(r for r in rows if r["entity_id"] == "3")
    assert row["modified_on"] == "2026-10-15T09:00:00Z"
    assert set(row["payload"]) == {"id", "modified_on", "variants"}
    variant = row["payload"]["variants"][0]
    assert set(variant) == {"id", "sku", "variant_prices", "inventories"}
    assert variant["variant_prices"][0]["price_list"]["code"] == "BANLE"
    assert variant["inventories"][0]["available"] == 5
    assert row["payload_hash"] == snap.build_envelopes([_product(3, "2026-10-15T09:00:00Z", 120000.0)],
                                                        CAPTURED_AT, "other")[0]["payload_hash"]


@pytest.mark.parametrize("captured_utc, expected", [
    (datetime(2026, 10, 31, 23, 30, tzinfo=timezone.utc), {"year": "2026", "month": "11"}),
    (datetime(2026, 12, 31, 17, 0, tzinfo=timezone.utc), {"year": "2027", "month": "1"}),
    (datetime(2026, 10, 15, 16, 59, tzinfo=timezone.utc), {"year": "2026", "month": "10"}),
])
def test_partition_follows_the_ict_calendar(captured_utc, expected):
    assert snap.ict_partition(captured_utc) == expected
    row = snap.build_envelopes([_product(1, "2026-10-01T00:00:00Z")], captured_utc, "r")[0]
    assert {"year": row["year"], "month": row["month"]} == expected


def test_naive_capture_time_is_rejected():
    with pytest.raises(ValueError):
        snap.build_envelopes([_product(1, None)], datetime(2026, 10, 15, 20, 1), "r")


@pytest.mark.parametrize("captured, total, expected", [
    (560, 560, 1.0),
    (548, 560, 548 / 560),
    (10, 0, None),
    (10, None, None),
])
def test_coverage_ratio(captured, total, expected):
    assert snap.coverage_ratio(captured, total) == expected


# --- load through dlt ----------------------------------------------------------------------------

@pytest.fixture
def lake(tmp_path, monkeypatch):
    """Temporary filesystem destination configured like ingestion/.dlt/config.toml."""
    root = tmp_path / "lake"
    monkeypatch.setenv("DESTINATION__FILESYSTEM__BUCKET_URL", str(root))
    monkeypatch.setenv("DESTINATION__FILESYSTEM__LAYOUT", PROD_LAYOUT)
    monkeypatch.setenv(
        "DESTINATION__FILESYSTEM__EXTRA_PLACEHOLDERS",
        json.dumps({"ingest_method": "batch_sync", "year": "_default", "month": "_default"}),
    )
    return root


def _snapshot_files(root):
    return sorted(glob.glob(str(root / "sapo_v2_raw" / "product_daily_snapshot" / "**" / "*.parquet"),
                            recursive=True))


def test_run_writes_one_file_in_the_ict_month_partition(lake, tmp_path):
    session = FakeSession(_catalogue(), total=5)
    result = runner.run(client=FakeClient(session), captured_at=CAPTURED_AT,
                        pipelines_dir=str(tmp_path / "pipelines"))

    files = _snapshot_files(lake)
    assert len(files) == 1
    assert "/product_daily_snapshot/ingest_method=daily_snapshot/year=2026/month=10/" in files[0]
    table = pq.read_table(files[0])
    assert table.num_rows == 5
    assert set(table.column("capture_run_id").to_pylist()) == {result.capture_run_id}
    assert {v.astimezone(timezone.utc) for v in table.column("captured_at").to_pylist()} == {CAPTURED_AT}
    payload = json.loads(table.column("payload").to_pylist()[0])
    assert set(payload) == {"id", "modified_on", "variants"}
    assert (result.products, result.pages, result.sapo_total) == (5, 3, 5)
    assert result.coverage_ratio == 1.0 and result.warnings == []


def test_failed_run_loads_nothing_and_next_run_loads_everything(lake, tmp_path, monkeypatch):
    pipelines_dir = str(tmp_path / "pipelines")

    def failing_fetch(client, session, page, page_size):
        if page == 3:
            raise RuntimeError("HTTP 500 on page 3")
        return {"metadata": {"total": 5}, "products": _catalogue()[page]}

    real_scan = snap.scan_catalogue
    monkeypatch.setattr(runner, "scan_catalogue",
                        lambda client: real_scan(client, page_size=2, fetch_page=failing_fetch))
    with pytest.raises(RuntimeError, match="page 3"):
        runner.run(client=FakeClient(None), captured_at=CAPTURED_AT, pipelines_dir=pipelines_dir)
    assert _snapshot_files(lake) == []

    monkeypatch.setattr(runner, "scan_catalogue", lambda client: real_scan(client, page_size=2))
    runner.run(client=FakeClient(FakeSession(_catalogue(), total=5)), captured_at=CAPTURED_AT,
               pipelines_dir=pipelines_dir)
    files = _snapshot_files(lake)
    assert len(files) == 1
    assert pq.read_table(files[0]).num_rows == 5


def test_second_run_appends_and_keeps_the_first(lake, tmp_path, monkeypatch):
    pipelines_dir = str(tmp_path / "pipelines")
    real_scan = snap.scan_catalogue
    monkeypatch.setattr(runner, "scan_catalogue", lambda client: real_scan(client, page_size=2))

    first = runner.run(client=FakeClient(FakeSession(_catalogue(), total=5)),
                       captured_at=CAPTURED_AT, pipelines_dir=pipelines_dir)
    second = runner.run(client=FakeClient(FakeSession(_catalogue(), total=5)),
                        captured_at=datetime(2026, 10, 16, 3, 0, tzinfo=timezone.utc),
                        pipelines_dir=pipelines_dir)

    files = _snapshot_files(lake)
    assert len(files) == 2
    run_ids = {rid for f in files for rid in pq.read_table(f).column("capture_run_id").to_pylist()}
    assert run_ids == {first.capture_run_id, second.capture_run_id}


def test_short_capture_is_loaded_with_a_warning(lake, tmp_path, monkeypatch):
    real_scan = snap.scan_catalogue
    monkeypatch.setattr(runner, "scan_catalogue", lambda client: real_scan(client, page_size=2))
    result = runner.run(client=FakeClient(FakeSession(_catalogue(), total=10)),
                        captured_at=CAPTURED_AT, pipelines_dir=str(tmp_path / "pipelines"))

    assert result.coverage_ratio == 0.5
    assert result.warnings and "coverage 0.500" in result.warnings[0]
    assert len(_snapshot_files(lake)) == 1


def test_empty_catalogue_is_refused(lake, tmp_path):
    with pytest.raises(RuntimeError, match="no products"):
        runner.run(client=FakeClient(FakeSession({}, total=0)), captured_at=CAPTURED_AT,
                   pipelines_dir=str(tmp_path / "pipelines"))
    assert _snapshot_files(lake) == []
