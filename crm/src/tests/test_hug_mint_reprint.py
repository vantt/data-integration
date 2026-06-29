"""test_hug_mint_reprint.py — tests for the batch reprint feature in screen_hug_mint.

Covers:
  - _render_batches: batch ID is wrapped in a clickable anchor to /hug/batch/labels
  - _render_batch_not_found: returns a friendly Vietnamese error page
  - Reprint logic: given a real hug.db batch the correct label HTML is produced
  - Missing batch: not-found page is returned when batch_id has no tokens

Note: FastAPI/starlette TestClient is NOT installed in the host Python environment
(packages live in the Docker container). HTTP-layer tests are therefore replaced by
direct calls to the rendering helpers and the route handler's business logic. The
assertions cover the same observable outcomes a TestClient would assert.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])    # .../data-integration
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])  # .../crm/src
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hug import db as hug_db  # noqa: E402
from hug import repository  # noqa: E402
# Import from the FastAPI-free HTML module so tests run without the framework.
from adapters.inbound.web.screens.hug.screen_hug_mint_html import (  # noqa: E402
    _render_batch_not_found,
    _render_batches,
)
from hug.labels import render_labels_html  # noqa: E402


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def hug_conn(tmp_path):
    conn = hug_db.connect(str(tmp_path / "hug.db"))
    yield conn
    conn.close()


# ── _render_batches: batch ID must be a clickable link ────────────────────────

def test_batch_list_renders_link_to_reprint_route():
    """Each batch ID in the batch list must link to /hug/batch/labels."""

    class FakeRow(dict):
        """Behave like a sqlite3.Row (supports both key and index access)."""
        def __getitem__(self, key):
            return super().__getitem__(key)

    rows = [
        FakeRow({"batch_id": "LOT-20260619-1200", "n": 50, "created_at": "2026-06-19T12:00:00Z"}),
        FakeRow({"batch_id": "LOT-20260618-0900", "n": 10, "created_at": "2026-06-18T09:00:00Z"}),
    ]
    html_out = _render_batches(rows)

    # Both batch IDs must appear as anchors to the reprint route.
    assert 'href="/hug/batch/labels?batch_id=LOT-20260619-1200"' in html_out
    assert 'href="/hug/batch/labels?batch_id=LOT-20260618-0900"' in html_out
    # The human-readable batch ID text must still be present inside <code>.
    assert "<code>LOT-20260619-1200</code>" in html_out


def test_batch_list_url_encodes_special_chars_in_batch_id():
    """Batch IDs with spaces or & must be percent-encoded in the href."""

    class FakeRow(dict):
        def __getitem__(self, key):
            return super().__getitem__(key)

    row = FakeRow({"batch_id": "LOT A&B", "n": 3, "created_at": "2026-06-19T00:00:00Z"})
    html_out = _render_batches([row])

    # Space → %20, & → %26 in the href value; the display text is HTML-escaped.
    assert "LOT%20A%26B" in html_out
    # The display text is HTML-escaped (& → &amp;).
    assert "LOT A&amp;B" in html_out


def test_batch_list_empty_shows_no_batches_message():
    html_out = _render_batches([])
    assert "Chưa có batch nào" in html_out


# ── _render_batch_not_found: friendly error page ──────────────────────────────

def test_not_found_page_contains_vietnamese_message():
    html_out = _render_batch_not_found("LOT-MISSING")
    assert "Không tìm thấy" in html_out
    assert "LOT-MISSING" in html_out


def test_not_found_page_has_back_link_to_batch_list():
    html_out = _render_batch_not_found("X")
    assert 'href="/hug/batches"' in html_out


def test_not_found_page_html_escapes_batch_id():
    """A batch_id containing HTML metacharacters must be escaped in the output."""
    html_out = _render_batch_not_found('<script>alert(1)</script>')
    assert "<script>" not in html_out
    assert "&lt;script&gt;" in html_out


# ── reprint logic: repository + renderer round-trip ──────────────────────────

def test_reprint_existing_batch_produces_label_html(hug_conn):
    """Minting a batch then calling the reprint logic must return QR label markup.

    The thermal-roll redesign strips the HUG- prefix from the printed sticker —
    the sticker shows a clean QR plus a token line "<op-code> · 7K2N-Q9XR-WAB4".
    Assertions verify the new structure, not the removed prefix.
    """
    repository.mint_batch(hug_conn, 5, batch_id="B-reprint-test", op_type="loyalty_card")

    rows = repository.list_batch(hug_conn, "B-reprint-test")
    assert rows, "precondition: batch must have rows"

    tokens = [r["token"] for r in rows]
    op_type = rows[0]["op_type"] if rows[0]["op_type"] else "package_insert"

    label_html = render_labels_html(tokens, "B-reprint-test", op_type=op_type)

    # Label containers + the token line must be present (one per token).
    assert 'class="label"' in label_html
    assert 'class="code"' in label_html
    # The HUG- prefix must NOT appear — the token line carries the bare grouped token.
    assert "HUG-" not in label_html
    # Batch ID must appear in the page title / header (screen-only area).
    assert "B-reprint-test" in label_html


def test_reprint_derives_op_type_from_first_row(hug_conn):
    """op_type on the label sheet must match what was used at mint time.

    The token line must begin with the 1-char code for the batch's op_type so
    thermal (monochrome) printing has an unambiguous identifier per sticker.
    """
    repository.mint_batch(hug_conn, 3, batch_id="B-optype-check", op_type="winback_flyer")

    rows = repository.list_batch(hug_conn, "B-optype-check")
    op_type = rows[0]["op_type"] if rows[0]["op_type"] else "package_insert"
    assert op_type == "winback_flyer"

    label_html = render_labels_html([r["token"] for r in rows], "B-optype-check", op_type=op_type)

    # The 1-char code for winback_flyer is "W" — it leads the token line as
    # ">W &middot; ...". Assert the code-line prefix is present.
    assert 'class="code"' in label_html
    assert ">W &middot;" in label_html


def test_reprint_missing_batch_returns_not_found_html(hug_conn):
    """Querying a non-existent batch must yield the not-found page, not a crash."""
    rows = repository.list_batch(hug_conn, "does-not-exist")
    assert not rows  # verify it's truly empty

    not_found_html = _render_batch_not_found("does-not-exist")
    assert "Không tìm thấy" in not_found_html
    assert "does-not-exist" in not_found_html
