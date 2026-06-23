"""Regression tests for the SQLite migration statement splitter.

The splitter must:
  - NOT split on a ';' that sits inside a trailing '-- comment' (the bug that
    cut migration 0002's crm_party_merge_log table mid-definition →
    "incomplete input").
  - keep BEGIN...END trigger bodies as one statement.
  - still split on real statement terminators.
"""
from __future__ import annotations

import pathlib
import sys

_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])  # crm/src
if _PYTHON_ROOT not in sys.path:
    sys.path.insert(0, _PYTHON_ROOT)

from adapters.outbound.sqlite.migrations import _split_statements  # noqa: E402


def test_semicolon_inside_inline_comment_does_not_split():
    sql = (
        "CREATE TABLE t (\n"
        "  a TEXT,\n"
        "  b TEXT  -- set on undo; prevents double-undo\n"
        ");"
    )
    stmts = _split_statements(sql)
    assert len(stmts) == 1
    assert stmts[0].strip().endswith(");")


def test_trigger_body_kept_as_single_statement():
    sql = (
        "CREATE TRIGGER trg AFTER UPDATE ON t\n"
        "BEGIN\n"
        "  UPDATE t SET a = '1';\n"   # inner ';' must not split
        "END;"
    )
    stmts = _split_statements(sql)
    assert len(stmts) == 1


def test_real_terminators_still_split():
    sql = "CREATE TABLE a (x TEXT);\nCREATE TABLE b (y TEXT);"
    stmts = _split_statements(sql)
    assert len(stmts) == 2
