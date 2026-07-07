"""Tests for Phase 03 (260706-0833 CRM Health Profile + Tag Governance Admin):

- SQLiteTagGovernanceRepository: merge (PK-collision reassign, ext_tag_map
  dedupe+repoint), archive (deactivates inbound mapping), unarchive (does NOT
  reactivate mapping), provisional queue filtering, chipify group query/apply.
- TagGovernanceService: thin business rules on top of the repository.
- make_tag_governance_router: HTTP wiring (status codes, HX-Redirect).
"""
from __future__ import annotations

import json
import pathlib
import sys
import uuid
from unittest.mock import MagicMock

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.templating import Jinja2Templates

from crm.src.adapters.outbound.sqlite.tag_governance_repository import SQLiteTagGovernanceRepository
from crm.src.adapters.outbound.sqlite.tag_note_repository import SQLiteTagRepository
from crm.src.application.tag_governance_service import TagGovernanceService
from crm.src.application.tag_service import TagService
from crm.src.adapters.inbound.web.screens.management.screen_mgmt_tag_governance import (
    make_tag_governance_router,
)
from adapters.inbound.http.auth_dependency import require_admin  # unprefixed: matches the
# import path screen_mgmt_tag_governance.py uses internally, so overriding this exact
# function object actually takes effect (a `crm.src.…` import would be a distinct module).


def _insert_party(db, party_id: str) -> None:
    db.conn.execute(
        "INSERT INTO crm_party (party_id, display_name) VALUES (?, ?)", (party_id, "Test Party")
    )
    db.conn.commit()


def _insert_tag(db, tag_id: str, name: str, category, is_provisional=0, is_archived=0) -> None:
    db.conn.execute(
        "INSERT INTO crm_tag (tag_id, name, category, is_provisional, is_archived) VALUES (?, ?, ?, ?, ?)",
        (tag_id, name, category, is_provisional, is_archived),
    )
    db.conn.commit()


def _attach(db, party_id, tag_id, source="crm_user") -> None:
    db.conn.execute(
        "INSERT INTO crm_party_tag (party_id, tag_id, tagged_at, source) VALUES (?, ?, '2026-01-01T00:00:00Z', ?)",
        (party_id, tag_id, source),
    )
    db.conn.commit()


def _insert_ext_mapping(db, map_id, ext_tag_id, crm_tag_id, direction="inbound", is_active=1) -> None:
    db.conn.execute(
        "INSERT OR IGNORE INTO crm_ext_tag (ext_tag_id, source_system, ext_key) VALUES (?, 'sapo_v2', ?)",
        (ext_tag_id, ext_tag_id),
    )
    db.conn.execute(
        "INSERT INTO crm_ext_tag_map (map_id, ext_tag_id, crm_tag_id, direction, is_active) VALUES (?, ?, ?, ?, ?)",
        (map_id, ext_tag_id, crm_tag_id, direction, is_active),
    )
    db.conn.commit()


@pytest.fixture()
def gov_repo(seeded_crm_db):
    return SQLiteTagGovernanceRepository(seeded_crm_db)


@pytest.fixture()
def tag_svc(seeded_crm_db):
    tag_repo = SQLiteTagRepository(seeded_crm_db)
    return TagService(tag_repo, seeded_crm_db)


@pytest.fixture()
def gov_service(seeded_crm_db, gov_repo, tag_svc):
    return TagGovernanceService(gov_repo, tag_svc, seeded_crm_db)


# ── Merge: PK collision + ext_tag_map dedupe/repoint ─────────────────────────

class TestMergeTags:
    def test_merge_reassigns_party_tag_without_pk_collision(self, seeded_crm_db, gov_repo):
        party = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party)
        _insert_tag(seeded_crm_db, "tag-a", "tag-a", "segment")
        _insert_tag(seeded_crm_db, "tag-b", "tag-b", "segment")
        # Party already holds BOTH the canonical target and the tag being merged away.
        _attach(seeded_crm_db, party, "tag-a")
        _attach(seeded_crm_db, party, "tag-b")

        gov_repo.merge_tags("tag-a", ["tag-b"])

        rows = seeded_crm_db.conn.execute(
            "SELECT tag_id FROM crm_party_tag WHERE party_id = ?", (party,)
        ).fetchall()
        assert [r["tag_id"] for r in rows] == ["tag-a"]  # exactly 1 row, no duplicate/crash
        assert seeded_crm_db.conn.execute(
            "SELECT 1 FROM crm_tag WHERE tag_id = 'tag-b'"
        ).fetchone() is None

    def test_merge_reassigns_party_tag_when_only_merged_tag_held(self, seeded_crm_db, gov_repo):
        party = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party)
        _insert_tag(seeded_crm_db, "tag-a", "tag-a", "segment")
        _insert_tag(seeded_crm_db, "tag-b", "tag-b", "segment")
        _attach(seeded_crm_db, party, "tag-b")

        gov_repo.merge_tags("tag-a", ["tag-b"])

        rows = seeded_crm_db.conn.execute(
            "SELECT tag_id FROM crm_party_tag WHERE party_id = ?", (party,)
        ).fetchall()
        assert [r["tag_id"] for r in rows] == ["tag-a"]

    def test_merge_repoints_ext_tag_map_with_dedupe(self, seeded_crm_db, gov_repo):
        _insert_tag(seeded_crm_db, "tag-a", "tag-a", "segment")
        _insert_tag(seeded_crm_db, "tag-b", "tag-b", "segment")
        # ext_tag already maps to BOTH a and b (dedupe case: repoint would collide on UNIQUE).
        _insert_ext_mapping(seeded_crm_db, "map-1", "ext-1", "tag-a")
        _insert_ext_mapping(seeded_crm_db, "map-2", "ext-1", "tag-b")

        gov_repo.merge_tags("tag-a", ["tag-b"])

        rows = seeded_crm_db.conn.execute(
            "SELECT crm_tag_id FROM crm_ext_tag_map WHERE ext_tag_id = 'ext-1'"
        ).fetchall()
        assert [r["crm_tag_id"] for r in rows] == ["tag-a"]  # deduped, no orphan/duplicate

    def test_merge_repoints_ext_tag_map_without_prior_target_mapping(self, seeded_crm_db, gov_repo):
        _insert_tag(seeded_crm_db, "tag-a", "tag-a", "segment")
        _insert_tag(seeded_crm_db, "tag-b", "tag-b", "segment")
        _insert_ext_mapping(seeded_crm_db, "map-1", "ext-2", "tag-b")

        gov_repo.merge_tags("tag-a", ["tag-b"])

        row = seeded_crm_db.conn.execute(
            "SELECT crm_tag_id FROM crm_ext_tag_map WHERE ext_tag_id = 'ext-2'"
        ).fetchone()
        assert row["crm_tag_id"] == "tag-a"
        # No FK orphan: the merged-away tag no longer exists, and nothing references it.
        assert seeded_crm_db.conn.execute(
            "SELECT 1 FROM crm_ext_tag_map WHERE crm_tag_id = 'tag-b'"
        ).fetchone() is None

    def test_service_rejects_merge_with_no_valid_ids(self, gov_service):
        with pytest.raises(ValueError):
            gov_service.merge_tags("tag-a", ["tag-a"])  # only self-reference, filtered to empty


# ── Archive / unarchive ───────────────────────────────────────────────────────

class TestArchiveUnarchive:
    def test_archive_deactivates_active_inbound_mapping_and_sets_archived(self, seeded_crm_db, gov_repo):
        _insert_tag(seeded_crm_db, "tag-a", "tag-a", "segment")
        _insert_ext_mapping(seeded_crm_db, "map-1", "ext-1", "tag-a", direction="inbound", is_active=1)

        gov_repo.archive_tag("tag-a")

        tag_row = seeded_crm_db.conn.execute(
            "SELECT is_archived FROM crm_tag WHERE tag_id = 'tag-a'"
        ).fetchone()
        assert tag_row["is_archived"] == 1
        map_row = seeded_crm_db.conn.execute(
            "SELECT is_active FROM crm_ext_tag_map WHERE map_id = 'map-1'"
        ).fetchone()
        assert map_row["is_active"] == 0

    def test_archive_leaves_outbound_only_mapping_untouched(self, seeded_crm_db, gov_repo):
        _insert_tag(seeded_crm_db, "tag-a", "tag-a", "segment")
        _insert_ext_mapping(seeded_crm_db, "map-1", "ext-1", "tag-a", direction="outbound", is_active=1)

        gov_repo.archive_tag("tag-a")

        map_row = seeded_crm_db.conn.execute(
            "SELECT is_active FROM crm_ext_tag_map WHERE map_id = 'map-1'"
        ).fetchone()
        assert map_row["is_active"] == 1  # outbound-only mapping is not an inbound sync risk

    def test_unarchive_does_not_reactivate_mapping(self, seeded_crm_db, gov_repo):
        _insert_tag(seeded_crm_db, "tag-a", "tag-a", "segment")
        _insert_ext_mapping(seeded_crm_db, "map-1", "ext-1", "tag-a", direction="inbound", is_active=1)
        gov_repo.archive_tag("tag-a")

        gov_repo.unarchive_tag("tag-a")

        tag_row = seeded_crm_db.conn.execute(
            "SELECT is_archived FROM crm_tag WHERE tag_id = 'tag-a'"
        ).fetchone()
        assert tag_row["is_archived"] == 0
        map_row = seeded_crm_db.conn.execute(
            "SELECT is_active FROM crm_ext_tag_map WHERE map_id = 'map-1'"
        ).fetchone()
        assert map_row["is_active"] == 0  # deliberately NOT reactivated


# ── Provisional queues (L1/L2) ────────────────────────────────────────────────

class TestProvisionalQueues:
    def test_l1_queue_only_shows_category_set_and_provisional(self, seeded_crm_db, gov_service):
        _insert_tag(seeded_crm_db, "tag-l1", "tag-l1", "health_concern", is_provisional=1)
        _insert_tag(seeded_crm_db, "tag-l2", "tag-l2", None, is_provisional=1)
        _insert_tag(seeded_crm_db, "tag-canon", "tag-canon", "health_concern", is_provisional=0)

        l1 = gov_service.list_provisional_l1()
        assert {t["tag_id"] for t in l1} == {"tag-l1"}

    def test_l2_queue_only_shows_category_null_and_provisional(self, seeded_crm_db, gov_service):
        _insert_tag(seeded_crm_db, "tag-l1", "tag-l1", "health_concern", is_provisional=1)
        _insert_tag(seeded_crm_db, "tag-l2", "tag-l2", None, is_provisional=1)

        l2 = gov_service.list_provisional_l2()
        assert {t["tag_id"] for t in l2} == {"tag-l2"}

    def test_promote_l1_clears_provisional_flag(self, seeded_crm_db, gov_service):
        _insert_tag(seeded_crm_db, "tag-l1", "tag-l1", "health_concern", is_provisional=1)
        gov_service.promote_l1("tag-l1")
        row = seeded_crm_db.conn.execute(
            "SELECT is_provisional, category FROM crm_tag WHERE tag_id = 'tag-l1'"
        ).fetchone()
        assert row["is_provisional"] == 0
        assert row["category"] == "health_concern"

    def test_promote_l2_assigns_category_and_clears_provisional(self, seeded_crm_db, gov_service):
        _insert_tag(seeded_crm_db, "tag-l2", "tag-l2", None, is_provisional=1)
        gov_service.assign_category_and_promote_l2("tag-l2", "health_concern")
        row = seeded_crm_db.conn.execute(
            "SELECT is_provisional, category FROM crm_tag WHERE tag_id = 'tag-l2'"
        ).fetchone()
        assert row["is_provisional"] == 0
        assert row["category"] == "health_concern"

    def test_delete_provisional_removes_tag_and_party_tag_rows(self, seeded_crm_db, gov_service):
        party = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party)
        _insert_tag(seeded_crm_db, "tag-l1", "tag-l1", "health_concern", is_provisional=1)
        _attach(seeded_crm_db, party, "tag-l1")

        gov_service.delete_provisional_tag("tag-l1")

        assert seeded_crm_db.conn.execute("SELECT 1 FROM crm_tag WHERE tag_id = 'tag-l1'").fetchone() is None
        assert seeded_crm_db.conn.execute(
            "SELECT 1 FROM crm_party_tag WHERE tag_id = 'tag-l1'"
        ).fetchone() is None

    def test_delete_provisional_cleans_up_ext_tag_map_instead_of_crashing(self, seeded_crm_db, gov_service):
        # crm_ext_tag_map.crm_tag_id is a NOT NULL FK with no ON DELETE CASCADE
        # (migration 0039) and foreign_keys=ON — a stray mapping row pointing at
        # a provisional tag would otherwise raise IntegrityError on delete.
        _insert_tag(seeded_crm_db, "tag-l1", "tag-l1", "health_concern", is_provisional=1)
        _insert_ext_mapping(seeded_crm_db, "map-1", "ext-1", "tag-l1", direction="inbound", is_active=1)

        gov_service.delete_provisional_tag("tag-l1")  # must not raise

        assert seeded_crm_db.conn.execute("SELECT 1 FROM crm_tag WHERE tag_id = 'tag-l1'").fetchone() is None
        assert seeded_crm_db.conn.execute(
            "SELECT 1 FROM crm_ext_tag_map WHERE crm_tag_id = 'tag-l1'"
        ).fetchone() is None


class TestPendingReviewCount:
    """Badge count backing the Settings 'Quản lý Tag' link — must reflect L1 +
    L2 + unreviewed chipify groups so the queue doesn't silently pile up."""

    def test_counts_l1_and_l2_provisional_tags(self, seeded_crm_db, gov_service):
        _insert_tag(seeded_crm_db, "tag-l1", "tag-l1", "health_concern", is_provisional=1)
        _insert_tag(seeded_crm_db, "tag-l2", "tag-l2", None, is_provisional=1)
        _insert_tag(seeded_crm_db, "tag-canon", "tag-canon", "health_concern", is_provisional=0)

        assert gov_service.pending_review_count() == 2

    def test_excludes_archived_provisional_tags(self, seeded_crm_db, gov_service):
        _insert_tag(seeded_crm_db, "tag-l1", "tag-l1", "health_concern", is_provisional=1, is_archived=1)

        assert gov_service.pending_review_count() == 0

    def test_counts_unreviewed_chipify_groups(self, seeded_crm_db, gov_service):
        party = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party)
        seeded_crm_db.conn.execute(
            "INSERT INTO crm_customer_profile (party_id, custom) VALUES (?, ?)",
            (party, json.dumps({"health_context_raw": "hay met moi"})),
        )
        seeded_crm_db.conn.commit()

        assert gov_service.pending_review_count() == 1

    def test_zero_when_nothing_pending(self, seeded_crm_db, gov_service):
        assert gov_service.pending_review_count() == 0


# ── L2 provisional duplicate prevention ───────────────────────────────────────
# crm_tag's UNIQUE(category, name) never blocks two L2 tags (category IS NULL)
# sharing a name — SQLite treats every NULL as distinct. TagService.create_tag
# guards this idempotently instead of relying on the DB constraint.

class TestL2DuplicatePrevention:
    def test_create_tag_l2_duplicate_name_returns_existing_not_new(self, seeded_crm_db, tag_svc):
        first = tag_svc.create_tag(name="thich-combo", category="", color="", is_provisional=True)
        second = tag_svc.create_tag(name="thich-combo", category="", color="", is_provisional=True)

        assert second.tag_id == first.tag_id
        row = seeded_crm_db.conn.execute(
            "SELECT COUNT(*) AS c FROM crm_tag WHERE name = ? AND category IS NULL",
            ("thich-combo",),
        ).fetchone()
        assert row["c"] == 1

    def test_chipify_create_tag_l2_duplicate_name_reuses_existing_tag(self, seeded_crm_db, gov_service):
        p1, p2 = str(uuid.uuid4()), str(uuid.uuid4())
        _insert_profile(seeded_crm_db, p1, {"health_context_raw": "hay met 1"})
        _insert_profile(seeded_crm_db, p2, {"health_context_raw": "hay met 2"})

        tag1 = gov_service.chipify_create_tag(
            raw_text="hay met 1", name="dup-name", category=None,
            is_provisional=True, color="", display_label="", actor_id=None,
        )
        tag2 = gov_service.chipify_create_tag(
            raw_text="hay met 2", name="dup-name", category=None,
            is_provisional=True, color="", display_label="", actor_id=None,
        )

        assert tag2.tag_id == tag1.tag_id
        row = seeded_crm_db.conn.execute(
            "SELECT COUNT(*) AS c FROM crm_tag WHERE name = ? AND category IS NULL",
            ("dup-name",),
        ).fetchone()
        assert row["c"] == 1


# ── Chipify ────────────────────────────────────────────────────────────────

def _insert_profile(db, party_id: str, custom: dict) -> None:
    db.conn.execute("INSERT INTO crm_party (party_id, display_name) VALUES (?, ?)", (party_id, "P"))
    db.conn.execute(
        "INSERT INTO crm_customer_profile (party_id, custom) VALUES (?, ?)",
        (party_id, json.dumps(custom)),
    )
    db.conn.commit()


class TestChipify:
    def test_list_chipify_groups_groups_unreviewed_by_raw_text(self, seeded_crm_db, gov_service):
        p1, p2, p3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
        _insert_profile(seeded_crm_db, p1, {"health_context_raw": "huyết áp cao"})
        _insert_profile(seeded_crm_db, p2, {"health_context_raw": "huyết áp cao"})
        _insert_profile(seeded_crm_db, p3, {"health_context_raw": "mất ngủ"})

        groups = gov_service.list_chipify_groups()
        by_text = {g["raw_text"]: g["n"] for g in groups}
        assert by_text == {"huyết áp cao": 2, "mất ngủ": 1}

    def test_list_chipify_groups_excludes_reviewed(self, seeded_crm_db, gov_service):
        p1 = str(uuid.uuid4())
        _insert_profile(seeded_crm_db, p1, {
            "health_context_raw": "huyết áp cao", "health_context_raw_reviewed": "true",
        })
        assert gov_service.list_chipify_groups() == []

    def test_chipify_create_tag_assigns_matching_parties_and_marks_reviewed(self, seeded_crm_db, gov_service):
        p1, p2 = str(uuid.uuid4()), str(uuid.uuid4())
        _insert_profile(seeded_crm_db, p1, {"health_context_raw": "hay mệt"})
        _insert_profile(seeded_crm_db, p2, {"health_context_raw": "hay mệt"})

        tag = gov_service.chipify_create_tag(
            raw_text="hay mệt", name="hay-met", category="health_concern",
            is_provisional=False, color="", display_label="Hay mệt", actor_id=None,
        )

        assert tag.category == "health_concern"
        assert tag.is_provisional is False
        rows = seeded_crm_db.conn.execute(
            "SELECT party_id FROM crm_party_tag WHERE tag_id = ?", (tag.tag_id,)
        ).fetchall()
        assert {r["party_id"] for r in rows} == {p1, p2}
        assert gov_service.list_chipify_groups() == []  # now reviewed

    def test_chipify_create_tag_l2_leaves_category_null(self, seeded_crm_db, gov_service):
        p1 = str(uuid.uuid4())
        _insert_profile(seeded_crm_db, p1, {"health_context_raw": "thích combo"})

        tag = gov_service.chipify_create_tag(
            raw_text="thích combo", name="thich-combo", category=None,
            is_provisional=True, color="", display_label="", actor_id=None,
        )
        assert tag.category is None
        assert tag.is_provisional is True

    def test_chipify_skip_marks_reviewed_without_creating_tag(self, seeded_crm_db, gov_service):
        p1 = str(uuid.uuid4())
        _insert_profile(seeded_crm_db, p1, {"health_context_raw": "note vô nghĩa"})

        gov_service.chipify_skip("note vô nghĩa")

        assert gov_service.list_chipify_groups() == []
        assert seeded_crm_db.conn.execute(
            "SELECT 1 FROM crm_party_tag WHERE party_id = ?", (p1,)
        ).fetchone() is None

    def test_chipify_bulk_skip_all_clears_every_group(self, seeded_crm_db, gov_service):
        p1, p2 = str(uuid.uuid4()), str(uuid.uuid4())
        _insert_profile(seeded_crm_db, p1, {"health_context_raw": "a"})
        _insert_profile(seeded_crm_db, p2, {"health_context_raw": "b"})

        gov_service.chipify_bulk_skip_all()

        assert gov_service.list_chipify_groups() == []


# ── Router wiring (HTTP-level) ───────────────────────────────────────────────

def _make_templates() -> Jinja2Templates:
    import jinja2
    templates_dir = str(
        pathlib.Path(__file__).parents[1] / "adapters" / "inbound" / "web" / "templates"
    )
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(templates_dir), autoescape=True)
    return Jinja2Templates(env=env)


def _build_app(svc) -> TestClient:
    # These tests exercise router wiring only (status codes, service calls,
    # HX-Redirect) — CF Access admin-role enforcement is covered separately
    # by auth_dependency's own tests, so bypass it here as an authenticated admin.
    app = FastAPI()
    app.include_router(make_tag_governance_router(_make_templates(), svc))
    app.dependency_overrides[require_admin] = lambda: None
    return TestClient(app, raise_server_exceptions=False)


class TestTagGovernanceRouter:
    def test_get_settings_tags_renders_default_tab(self):
        svc = MagicMock()
        svc.list_categories.return_value = ["health_domain"]
        svc.list_tags_for_category.return_value = []
        svc.list_chipify_groups.return_value = []
        svc.list_all_tags.return_value = []
        client = _build_app(svc)
        r = client.get("/settings/tags")
        assert r.status_code == 200
        svc.list_tags_for_category.assert_called_once_with("health_domain")

    def test_get_settings_tags_l1_tab_calls_l1_query(self):
        svc = MagicMock()
        svc.list_categories.return_value = ["health_domain"]
        svc.list_provisional_l1.return_value = []
        svc.list_chipify_groups.return_value = []
        svc.list_all_tags.return_value = []
        client = _build_app(svc)
        r = client.get("/settings/tags?tab=l1")
        assert r.status_code == 200
        svc.list_provisional_l1.assert_called_once()

    def test_post_archive_redirects_via_hx_redirect(self):
        svc = MagicMock()
        client = _build_app(svc)
        r = client.post("/settings/tags/tag-a/archive?tab=health_domain")
        assert r.status_code == 200
        assert r.headers["hx-redirect"] == "/settings/tags?tab=health_domain"
        svc.archive_tag.assert_called_once_with("tag-a")

    def test_post_merge_success_redirects(self):
        svc = MagicMock()
        client = _build_app(svc)
        r = client.post("/settings/tags/merge", data={
            "canonical_tag_id": "tag-a", "merge_tag_ids": ["tag-b", "tag-c"], "tab": "segment",
        })
        assert r.status_code == 200
        svc.merge_tags.assert_called_once_with("tag-a", ["tag-b", "tag-c"])

    def test_post_merge_value_error_returns_400(self):
        svc = MagicMock()
        svc.merge_tags.side_effect = ValueError("bad merge")
        client = _build_app(svc)
        r = client.post("/settings/tags/merge", data={"canonical_tag_id": "tag-a", "merge_tag_ids": ["tag-a"]})
        assert r.status_code == 400


# ── Settings "Tags" tab link — pending-review badge (make_settings_router) ────

def _build_settings_app(tag_governance_svc):
    from adapters.inbound.web.screens.management.screen_mgmt_settings import make_settings_router

    app = FastAPI()
    settings_svc = MagicMock()
    settings_svc.list_custom_field_defs.return_value = []
    settings_svc.list_tags.return_value = []
    app_users_svc = MagicMock()
    app_users_svc.list_active.return_value = []
    app.include_router(make_settings_router(_make_templates(), settings_svc, app_users_svc, tag_governance_svc))
    app.dependency_overrides[require_admin] = lambda: None
    return TestClient(app, raise_server_exceptions=False)


class TestSettingsTagsBadge:
    def test_badge_shown_when_pending_review_count_positive(self):
        svc = MagicMock()
        svc.pending_review_count.return_value = 3
        client = _build_settings_app(svc)
        r = client.get("/settings?tab=tags")
        assert r.status_code == 200
        assert '<span class="bdg bdg--bad"' in r.text
        assert ">3<" in r.text

    def test_badge_hidden_when_nothing_pending(self):
        svc = MagicMock()
        svc.pending_review_count.return_value = 0
        client = _build_settings_app(svc)
        r = client.get("/settings?tab=tags")
        assert r.status_code == 200
        assert '<span class="bdg bdg--bad"' not in r.text

    def test_badge_hidden_when_tag_governance_svc_not_wired(self):
        client = _build_settings_app(None)
        r = client.get("/settings?tab=tags")
        assert r.status_code == 200
        assert '<span class="bdg bdg--bad"' not in r.text

    def test_post_chipify_skip_all(self):
        svc = MagicMock()
        client = _build_app(svc)
        r = client.post("/settings/tags/chipify/skip-all", data={"tab": "l1"})
        assert r.status_code == 200
        svc.chipify_bulk_skip_all.assert_called_once()
