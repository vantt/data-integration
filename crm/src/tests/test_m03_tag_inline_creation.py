"""Tests for M03 free-text provisional tag creation (rep-facing follow-up to
Phase 02/03, 260706-0833 — closes the "rep không thể nhập tag mới" gap):

- TagService.find_or_create_tag() — L1 dedupe (incl. archived-name collision
  that would otherwise hit crm_tag's UNIQUE(category, name)), L2 delegation
  to create_tag's existing dedup.
- screen_modal_tags._slugify() — Vietnamese-aware slug generation.
- POST /customers/{party_id}/tags/create — category allow/deny, validation,
  attach source, response shape.
"""
from __future__ import annotations

import pathlib
import sys
import uuid
from unittest.mock import MagicMock

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.templating import Jinja2Templates

from crm.src.application.tag_service import TagService
from crm.src.adapters.inbound.web.screens.modals.screen_modal_tags import (
    make_tags_modal_router,
    _slugify,
    CREATE_EXCLUDED_CATEGORIES,
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
    return Jinja2Templates(env=env)


def _build_app(profile) -> TestClient:
    templates = _make_templates()
    app = FastAPI()
    app.include_router(make_tags_modal_router(templates, profile))
    return TestClient(app, raise_server_exceptions=False)


# ── _slugify ───────────────────────────────────────────────────────────────

class TestSlugify:
    def test_vietnamese_diacritics_stripped(self):
        assert _slugify("Huyết áp cao") == "huyet-ap-cao"

    def test_dee_with_stroke_mapped(self):
        assert _slugify("Đau khớp") == "dau-khop"

    def test_punctuation_collapsed_to_single_hyphen(self):
        assert _slugify("mất ngủ!!  kéo dài") == "mat-ngu-keo-dai"

    def test_empty_or_symbols_only_returns_empty(self):
        assert _slugify("!!!") == ""
        assert _slugify("   ") == ""


# ── TagService.find_or_create_tag ───────────────────────────────────────────

class TestFindOrCreateTag:
    def test_l1_returns_existing_exact_match_without_creating(self):
        repo = MagicMock()
        existing = Tag(tag_id="tag-1", name="huyet-ap-cao", category="health_concern")
        repo.get_tag_by_name_category.return_value = existing
        svc = TagService(repo)
        result = svc.find_or_create_tag("huyet-ap-cao", "health_concern")
        assert result is existing
        repo.create_tag.assert_not_called()

    def test_l1_creates_when_no_existing_match(self):
        repo = MagicMock()
        repo.get_tag_by_name_category.return_value = None
        svc = TagService(repo)
        result = svc.find_or_create_tag(
            "di-ung-phan-hoa", "health_concern", display_label="Dị ứng phấn hoa"
        )
        assert result.category == "health_concern"
        assert result.is_provisional is True
        repo.create_tag.assert_called_once()

    def test_l1_matches_previously_archived_tag_instead_of_raising(self):
        """get_tag_by_name_category includes archived rows — guards the
        UNIQUE(category, name) IntegrityError a plain create would hit."""
        repo = MagicMock()
        archived = Tag(tag_id="tag-old", name="mat-ngu", category="health_concern", is_archived=True)
        repo.get_tag_by_name_category.return_value = archived
        svc = TagService(repo)
        result = svc.find_or_create_tag("mat-ngu", "health_concern")
        assert result is archived
        repo.create_tag.assert_not_called()

    def test_l2_delegates_to_create_tag_dedup(self):
        repo = MagicMock()
        repo.list_tags.return_value = []
        svc = TagService(repo)
        result = svc.find_or_create_tag("thich-combo", None)
        assert result.category is None
        assert result.is_provisional is True
        repo.get_tag_by_name_category.assert_not_called()
        repo.create_tag.assert_called_once()


# ── POST /customers/{party_id}/tags/create ──────────────────────────────────

class TestTagsCreateEndpoint:
    def test_excluded_category_returns_400(self):
        profile = MagicMock()
        client = _build_app(profile)
        r = client.post(
            f"/customers/{_PARTY_ID}/tags/create",
            data={"name": "khach vip", "category": "vip_tier"},
        )
        assert r.status_code == 400
        profile.find_or_create_tag.assert_not_called()
        profile.attach_tag.assert_not_called()

    def test_empty_name_returns_400(self):
        profile = MagicMock()
        client = _build_app(profile)
        r = client.post(f"/customers/{_PARTY_ID}/tags/create", data={"name": "  ", "category": ""})
        assert r.status_code == 400
        profile.find_or_create_tag.assert_not_called()

    def test_symbols_only_name_returns_400(self):
        profile = MagicMock()
        client = _build_app(profile)
        r = client.post(f"/customers/{_PARTY_ID}/tags/create", data={"name": "!!!", "category": ""})
        assert r.status_code == 400
        profile.find_or_create_tag.assert_not_called()

    def test_l1_creates_provisional_and_attaches_with_crm_user_source(self):
        profile = MagicMock()
        new_tag = Tag(tag_id="tag-new", name="huyet-ap-cao", category="health_concern",
                      display_label="Huyết áp cao", is_provisional=True)
        profile.find_or_create_tag.return_value = new_tag
        profile.list_tags.return_value = [new_tag]
        profile.list_party_tags.return_value = [new_tag]
        client = _build_app(profile)
        r = client.post(
            f"/customers/{_PARTY_ID}/tags/create",
            data={"name": "Huyết áp cao", "category": "health_concern"},
        )
        assert r.status_code == 200
        profile.find_or_create_tag.assert_called_once_with(
            name="huyet-ap-cao", category="health_concern",
            display_label="Huyết áp cao", is_provisional=True,
        )
        profile.attach_tag.assert_called_once()
        assert profile.attach_tag.call_args.kwargs.get("source") == "crm_user"

    def test_blank_category_creates_l2(self):
        profile = MagicMock()
        new_tag = Tag(tag_id="tag-new2", name="thich-combo", category=None,
                      display_label="Thích combo", is_provisional=True)
        profile.find_or_create_tag.return_value = new_tag
        profile.list_tags.return_value = []
        profile.list_party_tags.return_value = []
        client = _build_app(profile)
        r = client.post(
            f"/customers/{_PARTY_ID}/tags/create",
            data={"name": "Thích combo", "category": ""},
        )
        assert r.status_code == 200
        profile.find_or_create_tag.assert_called_once_with(
            name="thich-combo", category=None,
            display_label="Thích combo", is_provisional=True,
        )

    def test_response_is_m03_modal_fragment(self):
        profile = MagicMock()
        new_tag = Tag(tag_id="tag-new", name="huyet-ap-cao", category="health_concern",
                      display_label="Huyết áp cao", is_provisional=True)
        profile.find_or_create_tag.return_value = new_tag
        profile.list_tags.return_value = [new_tag]
        profile.list_party_tags.return_value = [new_tag]
        profile.get_party_360.return_value = MagicMock(display_name="Nguyễn Văn A")
        client = _build_app(profile)
        r = client.post(
            f"/customers/{_PARTY_ID}/tags/create",
            data={"name": "Huyết áp cao", "category": "health_concern"},
        )
        assert 'data-surface="M03"' in r.text
        assert "Huyết áp cao" in r.text


def test_create_excluded_categories_matches_action_queue_consumer_categories():
    """Sanity link to plans/260706-1738-crm-tag-signal-action-queue-consumer —
    these are exactly the categories that drive automated action_type logic,
    so ad-hoc rep-created tags there could silently skew worklist priority."""
    assert CREATE_EXCLUDED_CATEGORIES == {"risk", "vip_tier"}
