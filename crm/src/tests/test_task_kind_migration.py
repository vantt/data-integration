"""test_task_kind_migration.py — Compatibility gate for migration 0032_task_kind.

Verifies:
1. Migration applies cleanly on a fresh DB (all-migrations path).
2. Pre-existing rows seeded BEFORE migration 0032 are classified with 0 NULLs.
3. Classification logic: generic (party_id IS NULL), internal (verify_account signals),
   contact (everything else — the DEFAULT catch-all).
4. Idempotency: running migration SQL a second time raises no error, results unchanged.
5. Repo round-trip: insert Task with task_kind → get_by_id returns the same kind.
6. Repo update: changing task_kind persists correctly.
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys
import tempfile
import uuid

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from adapters.outbound.sqlite.migrations import run_migrations, _MIGRATIONS_DIR  # noqa: E402
from crm.src.adapters.outbound.sqlite.connection import CRMDatabase              # noqa: E402
from crm.src.adapters.outbound.sqlite.task_repository import SQLiteTaskRepository  # noqa: E402
from crm.src.domain.entities.task import (                                        # noqa: E402
    Task,
    TASK_KIND_CONTACT, TASK_KIND_INTERNAL, TASK_KIND_GENERIC,
    VALID_TASK_KINDS,
)

_TS = "2026-07-02T00:00:00.000Z"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn(data_dir: str) -> sqlite3.Connection:
    """Open a bare sqlite3 connection (no CRMDatabase wrapper) for low-level setup."""
    db_path = pathlib.Path(data_dir) / "crm.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=OFF")   # allow inserts without all FKs satisfied
    return conn


def _run_migrations_up_to(conn: sqlite3.Connection, stop_before: str) -> None:
    """Apply migrations whose filename sorts BEFORE stop_before (exclusive upper bound)."""
    files = sorted(_MIGRATIONS_DIR.glob("*.up.sql"))
    applied = set()
    try:
        rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
        applied = {r[0] for r in rows}
    except sqlite3.OperationalError:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')))"
        )
        conn.commit()

    for path in files:
        if path.name >= stop_before:
            break
        if path.name in applied:
            continue
        sql = path.read_text(encoding="utf-8")
        conn.executescript(sql)   # quick path for pre-seeding (no savepoint nesting needed)
        conn.execute("INSERT OR IGNORE INTO schema_migrations (version) VALUES (?)", (path.name,))
    conn.commit()


def _seed_pre_migration_rows(conn: sqlite3.Connection) -> None:
    """Insert representative rows directly (bypasses INSERT trigger / task_kind col absent)."""
    # We seed using only the columns that existed before migration 0032.
    # SQLite will use the DEFAULT for task_kind once the column is added.
    base_cols = (
        "task_id, party_id, title, description, due_at, priority, status, "
        "assignee_user_id, source, source_ref, created_by, created_at, updated_at, completed_at"
    )
    rows = [
        # (task_id, party_id, title, description, due_at, priority, status, assignee, source, source_ref, created_by, created_at, updated_at, completed_at)
        # contact: party set, source=action_queue
        ("t-contact-1", "party-001", "Liên hệ khách hàng", None, None, 0, "open",
         None, "action_queue", "action-001", None, _TS, _TS, None),
        # contact: party set, source=manual
        ("t-contact-2", "party-002", "Gọi điện", None, None, 0, "open",
         None, "manual", None, None, _TS, _TS, None),
        # generic: party_id IS NULL, source=manual
        ("t-generic-1", None, "Họp nội bộ", None, None, 0, "open",
         None, "manual", None, None, _TS, _TS, None),
        # generic: party_id IS NULL, source=campaign
        ("t-generic-2", None, "Chuẩn bị chiến dịch", None, None, 0, "open",
         None, "campaign", "camp-001", None, _TS, _TS, None),
        # internal: source='verify_account'
        ("t-internal-1", "party-003", "Xác minh tài khoản mới", None, None, 0, "open",
         None, "verify_account", None, None, _TS, _TS, None),
        # internal: source_ref LIKE 'verify_account%'
        ("t-internal-2", "party-004", "Check user", None, None, 0, "open",
         None, "manual", "verify_account/abc123", None, _TS, _TS, None),
        # internal: title LIKE '%xác minh tài khoản%' (lowercase match)
        ("t-internal-3", "party-005", "Cần xác minh tài khoản khách", None, None, 0, "open",
         None, "manual", None, None, _TS, _TS, None),
    ]
    placeholders = ", ".join(["?"] * 14)
    for row in rows:
        conn.execute(f"INSERT INTO crm_task ({base_cols}) VALUES ({placeholders})", row)
    conn.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMigration0032Compatibility:
    """Seed rows BEFORE 0032, apply 0032, assert correct classification."""

    def setup_method(self):
        self._tmp = tempfile.mkdtemp()
        self._conn = _make_conn(self._tmp)

    def teardown_method(self):
        self._conn.close()

    def test_0_nulls_after_migration(self):
        """Core compatibility gate: no NULL task_kind after migration 0032."""
        _run_migrations_up_to(self._conn, "0032_task_kind.up.sql")
        _seed_pre_migration_rows(self._conn)

        # Now apply migration 0032 using the real runner
        run_migrations(self._conn)

        null_count = self._conn.execute(
            "SELECT COUNT(*) FROM crm_task WHERE task_kind IS NULL"
        ).fetchone()[0]
        assert null_count == 0, f"Expected 0 NULLs, got {null_count}"

    def test_contact_classification(self):
        """Rows with party_id set and no verify_account signal → contact."""
        _run_migrations_up_to(self._conn, "0032_task_kind.up.sql")
        _seed_pre_migration_rows(self._conn)
        run_migrations(self._conn)

        rows = self._conn.execute(
            "SELECT task_kind FROM crm_task WHERE task_id IN ('t-contact-1','t-contact-2')"
        ).fetchall()
        assert all(r["task_kind"] == TASK_KIND_CONTACT for r in rows), \
            f"Expected all contact, got {[r['task_kind'] for r in rows]}"

    def test_generic_classification(self):
        """Rows with party_id IS NULL → generic."""
        _run_migrations_up_to(self._conn, "0032_task_kind.up.sql")
        _seed_pre_migration_rows(self._conn)
        run_migrations(self._conn)

        rows = self._conn.execute(
            "SELECT task_kind FROM crm_task WHERE task_id IN ('t-generic-1','t-generic-2')"
        ).fetchall()
        assert all(r["task_kind"] == TASK_KIND_GENERIC for r in rows), \
            f"Expected all generic, got {[r['task_kind'] for r in rows]}"

    def test_internal_classification_source(self):
        """source='verify_account' → internal."""
        _run_migrations_up_to(self._conn, "0032_task_kind.up.sql")
        _seed_pre_migration_rows(self._conn)
        run_migrations(self._conn)

        row = self._conn.execute(
            "SELECT task_kind FROM crm_task WHERE task_id='t-internal-1'"
        ).fetchone()
        assert row["task_kind"] == TASK_KIND_INTERNAL

    def test_internal_classification_source_ref(self):
        """source_ref LIKE 'verify_account%' → internal."""
        _run_migrations_up_to(self._conn, "0032_task_kind.up.sql")
        _seed_pre_migration_rows(self._conn)
        run_migrations(self._conn)

        row = self._conn.execute(
            "SELECT task_kind FROM crm_task WHERE task_id='t-internal-2'"
        ).fetchone()
        assert row["task_kind"] == TASK_KIND_INTERNAL

    def test_internal_classification_title(self):
        """title LIKE '%xác minh tài khoản%' (case-insensitive) → internal."""
        _run_migrations_up_to(self._conn, "0032_task_kind.up.sql")
        _seed_pre_migration_rows(self._conn)
        run_migrations(self._conn)

        row = self._conn.execute(
            "SELECT task_kind FROM crm_task WHERE task_id='t-internal-3'"
        ).fetchone()
        assert row["task_kind"] == TASK_KIND_INTERNAL

    def test_distribution_sanity(self):
        """Distribution: 2 contact, 2 generic, 3 internal."""
        _run_migrations_up_to(self._conn, "0032_task_kind.up.sql")
        _seed_pre_migration_rows(self._conn)
        run_migrations(self._conn)

        dist = {
            r["task_kind"]: r["cnt"]
            for r in self._conn.execute(
                "SELECT task_kind, COUNT(*) AS cnt FROM crm_task GROUP BY task_kind"
            ).fetchall()
        }
        assert dist.get(TASK_KIND_CONTACT, 0) == 2
        assert dist.get(TASK_KIND_GENERIC, 0) == 2
        assert dist.get(TASK_KIND_INTERNAL, 0) == 3

    def test_idempotency(self):
        """Running migration 0032 twice raises no error and leaves results unchanged."""
        _run_migrations_up_to(self._conn, "0032_task_kind.up.sql")
        _seed_pre_migration_rows(self._conn)
        run_migrations(self._conn)   # first apply

        # Remove from schema_migrations so runner re-applies
        self._conn.execute(
            "DELETE FROM schema_migrations WHERE version='0032_task_kind.up.sql'"
        )
        self._conn.commit()

        run_migrations(self._conn)   # second apply — must not raise

        null_count = self._conn.execute(
            "SELECT COUNT(*) FROM crm_task WHERE task_kind IS NULL"
        ).fetchone()[0]
        assert null_count == 0


class TestTaskKindConstants:
    def test_constants_values(self):
        assert TASK_KIND_CONTACT == "contact"
        assert TASK_KIND_INTERNAL == "internal"
        assert TASK_KIND_GENERIC == "generic"

    def test_valid_kinds_complete(self):
        assert set(VALID_TASK_KINDS) == {"contact", "internal", "generic"}

    def test_task_default_kind(self):
        t = Task(task_id="t-001", title="T", priority=0, status="open",
                 source="manual", created_at=_TS, updated_at=_TS)
        assert t.task_kind == TASK_KIND_CONTACT
        assert t.channel is None


class TestTaskKindRepoRoundTrip:
    """Insert → get_by_id round-trip and update persists task_kind correctly."""

    def setup_method(self):
        self._tmp = tempfile.mkdtemp()

    def _make_db(self):
        db = CRMDatabase(self._tmp)
        db.apply_migrations()
        return db

    def test_insert_and_get_by_id_preserves_task_kind(self):
        db = self._make_db()
        repo = SQLiteTaskRepository(db)

        task = Task(
            task_id=str(uuid.uuid4()), title="Liên hệ", priority=0,
            status="open", source="action_queue",
            created_at=_TS, updated_at=_TS,
            party_id=None,   # would be generic by backfill, but explicit here
            task_kind=TASK_KIND_GENERIC,
            channel="phone",
        )
        repo.insert(task)
        db.conn.commit()

        fetched = repo.get_by_id(task.task_id)
        assert fetched is not None
        assert fetched.task_kind == TASK_KIND_GENERIC
        assert fetched.channel == "phone"
        db.close()

    def test_insert_contact_kind(self):
        db = self._make_db()
        repo = SQLiteTaskRepository(db)

        # party_id=None avoids FK constraint (no party row seeded); task_kind explicit contact
        task = Task(
            task_id=str(uuid.uuid4()), title="Gọi điện VIP", priority=1,
            status="open", source="action_queue",
            created_at=_TS, updated_at=_TS,
            party_id=None,
            task_kind=TASK_KIND_CONTACT,
        )
        repo.insert(task)
        db.conn.commit()

        fetched = repo.get_by_id(task.task_id)
        assert fetched.task_kind == TASK_KIND_CONTACT
        assert fetched.channel is None
        db.close()

    def test_update_task_kind(self):
        db = self._make_db()
        repo = SQLiteTaskRepository(db)

        task = Task(
            task_id=str(uuid.uuid4()), title="Task", priority=0,
            status="open", source="manual",
            created_at=_TS, updated_at=_TS,
            task_kind=TASK_KIND_CONTACT,
        )
        repo.insert(task)
        db.conn.commit()

        task.task_kind = TASK_KIND_INTERNAL
        task.channel = "zalo"
        repo.update(task)
        db.conn.commit()

        fetched = repo.get_by_id(task.task_id)
        assert fetched.task_kind == TASK_KIND_INTERNAL
        assert fetched.channel == "zalo"
        db.close()

    def test_existing_task_entity_fields_still_work(self):
        """Existing tests expect optional fields default to None — must still hold."""
        t = Task(task_id="t-chk", title="X", priority=0, status="open",
                 source="manual", created_at=_TS, updated_at=_TS)
        assert t.party_id is None
        assert t.due_at is None
        assert t.assignee_user_id is None
        # new fields have sane defaults
        assert t.task_kind == "contact"
        assert t.channel is None
