"""test_hug_tokens.py — unit tests for hug.tokens module.

Covers: normalize_input() parity with the Worker TS normalizeToken() including
the broadened separator set (-, _, ., whitespace).
"""
from __future__ import annotations

import pathlib
import sys

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])    # .../data-integration
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])  # .../crm/src
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hug.tokens import normalize_input, is_valid_token  # noqa: E402


# ── normalize_input parity matrix ────────────────────────────────────────────

def test_bare_token_passes_through():
    assert normalize_input("7K2NQ9XRWAB4") == "7K2NQ9XRWAB4"


def test_lowercase_bare_token_uppercased():
    assert normalize_input("7k2nq9xrwab4") == "7K2NQ9XRWAB4"


def test_grouped_code_dashes_stripped():
    assert normalize_input("7K2N-Q9XR-WAB4") == "7K2NQ9XRWAB4"


def test_human_code_hug_prefix_stripped():
    assert normalize_input("HUG-7K2N-Q9XR-WAB4") == "7K2NQ9XRWAB4"


def test_human_code_lowercase():
    assert normalize_input("hug-7k2n-q9xr-wab4") == "7K2NQ9XRWAB4"


def test_full_scan_url_extracts_token():
    assert normalize_input("https://hug.fjp.vn/h/7K2NQ9XRWAB4") == "7K2NQ9XRWAB4"


def test_full_url_with_query_and_fragment():
    assert normalize_input("https://hug.fjp.vn/h/7K2NQ9XRWAB4?foo=1#bar") == "7K2NQ9XRWAB4"


def test_underscore_separators_stripped():
    assert normalize_input("7K2N_Q9XR_WAB4") == "7K2NQ9XRWAB4"


def test_dot_separators_stripped():
    assert normalize_input("7K2N.Q9XR.WAB4") == "7K2NQ9XRWAB4"


def test_mixed_separators_stripped():
    assert normalize_input("7K2N-Q9XR_WAB4") == "7K2NQ9XRWAB4"


def test_12_char_token_starting_with_hug_not_stripped():
    # A 12-char token that begins with HUG must NOT have those chars stripped.
    # The 15-char length guard in normalize_input prevents corruption — the token
    # is already at TOKEN_LEN (12) so the HUG-prefix branch never fires.
    # HUG2345678AB: H-U-G-2-3-4-5-6-7-8-A-B = 12 chars, starts with HUG.
    result = normalize_input("HUG2345678AB")
    assert result == "HUG2345678AB"
    assert len(result) == 12


def test_garbage_input_returned_as_is():
    # normalize_input does not validate; caller checks is_valid_token.
    assert normalize_input("XXXX") == "XXXX"


def test_normalized_token_passes_is_valid_token():
    """Round-trip: normalize a human code then confirm is_valid_token accepts it."""
    token = normalize_input("HUG-7K2N-Q9XR-WAB4")
    assert is_valid_token(token)


def test_underscore_form_passes_is_valid_after_normalize():
    token = normalize_input("7K2N_Q9XR_WAB4")
    assert is_valid_token(token)


def test_dot_form_passes_is_valid_after_normalize():
    token = normalize_input("7K2N.Q9XR.WAB4")
    assert is_valid_token(token)
