"""Tests for Phase 02 (260706-0833 CRM Health Profile + Tag Governance):

- application.health_domain_collect.load_health_domain_collect_context()
- SQLiteTagRepository.list_tags_by_category_ordered_by_usage() + attach_tag() source column
- TagService.attach_tag() source passthrough
- S14 call cockpit context: health_domain / health_context_raw collect rows
- POST /customers/{party_id}/tags/inline — whitelist + attach + fragment swap
- POST /customers/{party_id}/custom-field-inline — health_context_raw whitelist + maxlength
- skin_type / preferred_contact regression (unchanged custom_select behaviour)
"""
from __future__ import annotations

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

from crm.src.application.health_domain_collect import (
    load_health_domain_collect_context,
    HEALTH_DOMAIN_CATEGORY,
)
from crm.src.application.tag_service import TagService
from crm.src.adapters.outbound.sqlite.tag_note_repository import SQLiteTagRepository
from crm.src.adapters.inbound.web.screens.customer360.screen_call_cockpit import (
    register_call_cockpit_route,
)
from crm.src.adapters.inbound.web.screens.modals.screen_modal_tags import (
    make_tags_modal_router,
    INLINE_ALLOWED_CATEGORIES,
)
from crm.src.adapters.inbound.web.screens.modals.screen_modal_contact import (
    make_contact_modal_router,
)
from crm.src.domain.entities.profile import Tag

_PARTY_ID = str(uuid.uuid4())
_TEMPLATES_DIR = str(
    pathlib.Path(__file__).parents[1] / "adapters" / "inbound" / "web" / "templates"
)


def _make_templates() -> Jinja2Templates:
    import jinja2
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(_TEMPLATES_DIR),
        autoescape=True,
        auto_reload=False,
    )
    env.filters["fmt_vnd"] = lambda v: f"{v:,}₫" if v else "0₫"
    env.filters["truncate_str"] = lambda s, n=80: (s or "")[:n]
    env.filters["format_datetime_ict"] = lambda v: v or ""
    env.globals["today"] = lambda: "2026-07-02"
    return Jinja2Templates(env=env)


# ── application.health_domain_collect (pure unit) ────────────────────────────

class TestLoadHealthDomainCollectContext:
    def test_no_tags_svc_returns_no_gap_shown(self):
        # tags_svc unavailable → suppress the row (has_tag=True) rather than
        # render a chip picker with no working options.
        ctx = load_health_domain_collect_context(None, "party-1")
        assert ctx == {"has_health_domain_tag": True, "health_domain_options": []}

    def test_has_tag_true_when_party_has_health_domain_tag(self):
        tags_svc = MagicMock()
        tags_svc.list_party_tags.return_value = [
            Tag(tag_id="t1", name="tim-mach", category=HEALTH_DOMAIN_CATEGORY)
        ]
        ctx = load_health_domain_collect_context(tags_svc, "party-1")
        assert ctx["has_health_domain_tag"] is True
        assert ctx["health_domain_options"] == []
        tags_svc.list_tags_by_category_ordered_by_usage.assert_not_called()

    def test_has_tag_false_fetches_ordered_options(self):
        tags_svc = MagicMock()
        tags_svc.list_party_tags.return_value = []
        options = [Tag(tag_id="t1", name="tim-mach", category=HEALTH_DOMAIN_CATEGORY)]
        tags_svc.list_tags_by_category_ordered_by_usage.return_value = options
        ctx = load_health_domain_collect_context(tags_svc, "party-1")
        assert ctx["has_health_domain_tag"] is False
        assert ctx["health_domain_options"] == options
        tags_svc.list_tags_by_category_ordered_by_usage.assert_called_once_with(
            HEALTH_DOMAIN_CATEGORY
        )

    def test_exception_in_list_party_tags_degrades_gracefully(self):
        tags_svc = MagicMock()
        tags_svc.list_party_tags.side_effect = RuntimeError("db down")
        tags_svc.list_tags_by_category_ordered_by_usage.return_value = []
        ctx = load_health_domain_collect_context(tags_svc, "party-1")
        assert ctx["has_health_domain_tag"] is False  # falls back to "show gap"


# ── SQLiteTagRepository / TagService — usage ordering + explicit source ──────

class TestSqliteTagRepositoryHealthDomain:
    def _insert_party(self, db, party_id: str) -> None:
        db.conn.execute(
            "INSERT INTO crm_party (party_id, display_name) VALUES (?, ?)",
            (party_id, "Test Party"),
        )
        db.conn.commit()

    def test_list_tags_by_category_ordered_by_usage_ranks_by_attach_count(self, seeded_crm_db):
        repo = SQLiteTagRepository(seeded_crm_db)
        party_a, party_b = str(uuid.uuid4()), str(uuid.uuid4())
        self._insert_party(seeded_crm_db, party_a)
        self._insert_party(seeded_crm_db, party_b)

        # 'da' (tag-health-0008) gets 2 attaches, 'tim-mach' (tag-health-0001) gets 1.
        seeded_crm_db.conn.execute(
            "INSERT INTO crm_party_tag (party_id, tag_id, tagged_at, source) VALUES (?, ?, '2026-01-01T00:00:00Z', 'crm_user')",
            (party_a, "tag-health-0008"),
        )
        seeded_crm_db.conn.execute(
            "INSERT INTO crm_party_tag (party_id, tag_id, tagged_at, source) VALUES (?, ?, '2026-01-01T00:00:00Z', 'crm_user')",
            (party_b, "tag-health-0008"),
        )
        seeded_crm_db.conn.execute(
            "INSERT INTO crm_party_tag (party_id, tag_id, tagged_at, source) VALUES (?, ?, '2026-01-01T00:00:00Z', 'crm_user')",
            (party_a, "tag-health-0001"),
        )
        seeded_crm_db.conn.commit()

        ordered = repo.list_tags_by_category_ordered_by_usage("health_domain")
        assert len(ordered) == 8  # all 8 seeded tags present
        assert ordered[0].name == "da"          # 2 attaches — most used
        assert ordered[1].name == "tim-mach"    # 1 attach

    def test_list_tags_by_category_ordered_by_usage_excludes_archived(self, seeded_crm_db):
        seeded_crm_db.conn.execute(
            "UPDATE crm_tag SET is_archived = 1 WHERE tag_id = 'tag-health-0001'"
        )
        seeded_crm_db.conn.commit()
        repo = SQLiteTagRepository(seeded_crm_db)
        ordered = repo.list_tags_by_category_ordered_by_usage("health_domain")
        assert "tim-mach" not in [t.name for t in ordered]
        assert len(ordered) == 7

    def test_attach_tag_writes_source_explicitly(self, seeded_crm_db):
        repo = SQLiteTagRepository(seeded_crm_db)
        party_id = str(uuid.uuid4())
        self._insert_party(seeded_crm_db, party_id)
        svc = TagService(repo, db=seeded_crm_db)

        svc.attach_tag(party_id, "tag-health-0001", user_id=None, source="crm_user")

        row = seeded_crm_db.conn.execute(
            "SELECT source FROM crm_party_tag WHERE party_id=? AND tag_id=?",
            (party_id, "tag-health-0001"),
        ).fetchone()
        assert row["source"] == "crm_user"

    def test_list_party_tags_excludes_tag_archived_after_attachment(self, seeded_crm_db):
        # Zombie-tag regression: a tag archived by admin after already being
        # attached to a party must stop surfacing on that party's tag list
        # (S14 cockpit / M03 modal), even though the crm_party_tag row itself
        # is left untouched (history preserved).
        repo = SQLiteTagRepository(seeded_crm_db)
        party_id = str(uuid.uuid4())
        self._insert_party(seeded_crm_db, party_id)
        seeded_crm_db.conn.execute(
            "INSERT INTO crm_party_tag (party_id, tag_id, tagged_at, source) "
            "VALUES (?, ?, '2026-01-01T00:00:00Z', 'crm_user')",
            (party_id, "tag-health-0001"),
        )
        seeded_crm_db.conn.commit()

        seeded_crm_db.conn.execute(
            "UPDATE crm_tag SET is_archived = 1 WHERE tag_id = 'tag-health-0001'"
        )
        seeded_crm_db.conn.commit()

        assert "tim-mach" not in [t.name for t in repo.list_party_tags(party_id)]
        assert "tim-mach" not in [
            t.name for t in repo.list_party_tags_with_meta(party_id)
        ]
        # crm_party_tag history row itself survives the archive.
        assert seeded_crm_db.conn.execute(
            "SELECT 1 FROM crm_party_tag WHERE party_id = ? AND tag_id = 'tag-health-0001'",
            (party_id,),
        ).fetchone() is not None


# ── S14 call cockpit — health_domain / health_context_raw gap rendering ──────

def _build_cockpit_app(tags_svc=None, party_custom: dict = None) -> TestClient:
    templates = _make_templates()
    app = FastAPI()
    from fastapi import APIRouter
    router = APIRouter()

    party_mock = MagicMock()
    party_mock.display_name = "Nguyen Van A"
    party_mock.province = "Hồ Chí Minh"
    party_mock.birthday = "1990-01-01"
    party_mock.gender = "female"
    import json
    party_mock.custom = json.dumps(party_custom or {})

    def _load_base(party_id):
        return party_mock, []

    def _load_insight(ids):
        return None

    def _sapo_customer_id(ids):
        return 1001

    notes_mock = MagicMock()
    notes_mock.list_notes.return_value = []
    party_tasks_mock = MagicMock()
    party_tasks_mock.list_by_party.return_value = []

    register_call_cockpit_route(
        router,
        templates,
        _load_base=_load_base,
        _load_insight=_load_insight,
        _sapo_customer_id=_sapo_customer_id,
        notes=notes_mock,
        party_tasks=party_tasks_mock,
        approach_repo=None,
        action_task_resolver=None,
        tags=tags_svc,
    )
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


class TestCallCockpitHealthDomainGap:
    def test_health_domain_row_shown_when_no_tag(self):
        tags_svc = MagicMock()
        tags_svc.list_party_tags.return_value = []
        tags_svc.list_tags_by_category_ordered_by_usage.return_value = [
            Tag(tag_id="tag-health-0001", name="tim-mach", category="health_domain",
                display_label="Tim mạch"),
        ]
        client = _build_cockpit_app(tags_svc=tags_svc)
        r = client.get(f"/customers/{_PARTY_ID}/call")
        assert r.status_code == 200
        assert "s14-cr-health_domain" in r.text
        assert "Lĩnh vực sức khỏe" in r.text
        assert "Tim mạch" in r.text

    def test_health_domain_row_hidden_when_tag_present(self):
        tags_svc = MagicMock()
        tags_svc.list_party_tags.return_value = [
            Tag(tag_id="tag-health-0001", name="tim-mach", category="health_domain")
        ]
        client = _build_cockpit_app(tags_svc=tags_svc)
        r = client.get(f"/customers/{_PARTY_ID}/call")
        assert r.status_code == 200
        assert "s14-cr-health_domain" not in r.text
        tags_svc.list_tags_by_category_ordered_by_usage.assert_not_called()

    def test_health_domain_row_hidden_gracefully_when_no_tags_service(self):
        # tags=None (composition root not wired) must not 500 the whole cockpit
        client = _build_cockpit_app(tags_svc=None)
        r = client.get(f"/customers/{_PARTY_ID}/call")
        assert r.status_code == 200
        assert "s14-cr-health_domain" not in r.text

    def test_health_context_row_shown_when_empty(self):
        client = _build_cockpit_app(party_custom={})
        r = client.get(f"/customers/{_PARTY_ID}/call")
        assert r.status_code == 200
        assert "s14-crow-health_context_raw" in r.text
        assert "Ghi chú sức khỏe" in r.text

    def test_health_context_row_hidden_when_set(self):
        client = _build_cockpit_app(party_custom={"health_context_raw": "huyết áp cao"})
        r = client.get(f"/customers/{_PARTY_ID}/call")
        assert r.status_code == 200
        assert "s14-crow-health_context_raw" not in r.text

    def test_skin_type_row_unaffected_by_health_rows(self):
        """Regression: skin_type gap row (Phase 06) still renders alongside the
        2 new health rows and is untouched by this phase's changes."""
        client = _build_cockpit_app(party_custom={})
        r = client.get(f"/customers/{_PARTY_ID}/call")
        assert r.status_code == 200
        assert "s14-cr-skin_type" in r.text
        assert "Loại da" in r.text


# ── POST /customers/{party_id}/tags/inline ────────────────────────────────────

def _build_tags_modal_app(profile=None) -> TestClient:
    templates = _make_templates()
    app = FastAPI()
    app.include_router(make_tags_modal_router(templates, profile))
    return TestClient(app, raise_server_exceptions=False)


class TestTagsInlineEndpoint:
    def test_whitelist_constant_matches_phase_spec(self):
        assert INLINE_ALLOWED_CATEGORIES == {"health_domain", "health_concern"}

    def test_disallowed_category_returns_400_and_does_not_attach(self):
        profile = MagicMock()
        client = _build_tags_modal_app(profile=profile)
        r = client.post(
            f"/customers/{_PARTY_ID}/tags/inline",
            data={"category": "risk", "tag_names": ["vip"]},
        )
        assert r.status_code == 400
        profile.list_tags.assert_not_called()
        profile.attach_tag.assert_not_called()

    def test_allowed_category_attaches_with_crm_user_source(self):
        profile = MagicMock()
        profile.list_tags.return_value = [
            Tag(tag_id="tag-health-0001", name="tim-mach", category="health_domain",
                display_label="Tim mạch"),
            Tag(tag_id="tag-health-0002", name="ho-hap", category="health_domain",
                display_label="Hô hấp"),
        ]
        client = _build_tags_modal_app(profile=profile)
        r = client.post(
            f"/customers/{_PARTY_ID}/tags/inline",
            data={"category": "health_domain", "tag_names": ["tim-mach", "ho-hap"]},
        )
        assert r.status_code == 200
        assert "Tim mạch" in r.text
        assert "Hô hấp" in r.text
        assert profile.attach_tag.call_count == 2
        for call in profile.attach_tag.call_args_list:
            assert call.kwargs.get("source") == "crm_user"

    def test_source_activity_id_passthrough_when_provided(self):
        """S14 strip now sends S.draftId as source_activity_id (plan 260709-1638
        phase-01 "Handoff wiring", closed 2026-07-11) — confirm the route
        forwards whatever the client sends through to attach_tag()."""
        profile = MagicMock()
        profile.list_tags.return_value = [
            Tag(tag_id="tag-health-0001", name="tim-mach", category="health_domain",
                display_label="Tim mạch"),
        ]
        client = _build_tags_modal_app(profile=profile)
        r = client.post(
            f"/customers/{_PARTY_ID}/tags/inline",
            data={"category": "health_domain", "tag_names": ["tim-mach"],
                  "source_activity_id": "act-abc-123"},
        )
        assert r.status_code == 200
        assert profile.attach_tag.call_args.kwargs.get("source_activity_id") == "act-abc-123"

    def test_source_activity_id_blank_stays_none(self):
        """Outside an active call, S.draftId is null → strip sends '' — must
        stay backward compatible with the pre-existing NULL-column behaviour."""
        profile = MagicMock()
        profile.list_tags.return_value = [
            Tag(tag_id="tag-health-0001", name="tim-mach", category="health_domain",
                display_label="Tim mạch"),
        ]
        client = _build_tags_modal_app(profile=profile)
        r = client.post(
            f"/customers/{_PARTY_ID}/tags/inline",
            data={"category": "health_domain", "tag_names": ["tim-mach"],
                  "source_activity_id": ""},
        )
        assert r.status_code == 200
        assert profile.attach_tag.call_args.kwargs.get("source_activity_id") is None

    def test_no_matching_tag_names_returns_400(self):
        profile = MagicMock()
        profile.list_tags.return_value = []
        client = _build_tags_modal_app(profile=profile)
        r = client.post(
            f"/customers/{_PARTY_ID}/tags/inline",
            data={"category": "health_domain", "tag_names": ["nonexistent-slug"]},
        )
        assert r.status_code == 400
        profile.attach_tag.assert_not_called()


# ── POST /customers/{party_id}/custom-field-inline — health_context_raw ─────

def _build_contact_modal_app() -> TestClient:
    templates = _make_templates()
    profile = MagicMock()
    profile.get_party_360.return_value = MagicMock(display_name="X")
    profile.upsert_profile.return_value = None
    party_repo = MagicMock()
    party_repo.list_identities.return_value = []
    app = FastAPI()
    app.include_router(make_contact_modal_router(templates, profile, party_repo))
    return TestClient(app, raise_server_exceptions=False)


class TestCustomFieldInlineHealthContext:
    def test_health_context_raw_saves_and_returns_done_row(self):
        client = _build_contact_modal_app()
        r = client.post(
            f"/customers/{_PARTY_ID}/custom-field-inline",
            data={"field_key": "health_context_raw", "value": "huyết áp cao, hay mệt", "inline": "1"},
        )
        assert r.status_code == 200
        assert "huyết áp cao, hay mệt" in r.text

    def test_health_context_raw_over_200_chars_rejected(self):
        client = _build_contact_modal_app()
        r = client.post(
            f"/customers/{_PARTY_ID}/custom-field-inline",
            data={"field_key": "health_context_raw", "value": "a" * 201, "inline": "1"},
        )
        assert r.status_code == 400

    def test_skin_type_still_accepted_unchanged(self):
        """Regression: skin_type whitelist entry + custom_select rendering untouched."""
        client = _build_contact_modal_app()
        r = client.post(
            f"/customers/{_PARTY_ID}/custom-field-inline",
            data={"field_key": "skin_type", "value": "khô", "inline": "1"},
        )
        assert r.status_code == 200
        assert "khô" in r.text

    def test_unknown_field_key_still_rejected(self):
        client = _build_contact_modal_app()
        r = client.post(
            f"/customers/{_PARTY_ID}/custom-field-inline",
            data={"field_key": "not_whitelisted", "value": "x", "inline": "1"},
        )
        assert r.status_code == 400
