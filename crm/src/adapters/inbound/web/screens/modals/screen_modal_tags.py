"""Web adapter — M03 Tag Management modal + S14 inline tag assign.

Routes:
  GET  /modals/m03?party_id=              open the tag-management modal
  POST /customers/{party_id}/tags         save tag selection (attach/detach diff)
  POST /customers/{party_id}/tags/inline  S14 collect-row inline tag assign
       (Phase 02, 260706-0833) — whitelisted categories only, see
       INLINE_ALLOWED_CATEGORIES below.
  POST /customers/{party_id}/tags/create  M03 free-text provisional tag
       creation — see CREATE_EXCLUDED_CATEGORIES below.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import List, Optional

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from adapters.inbound.web.screens.modals.screen_modal_shared import ProfileSvc, redirect_to_customer

log = logging.getLogger(__name__)

# Security/data-integrity boundary (phase-02-s14-health-collect.md): S14 is a
# fast inline path with no confirmation step, so only low-risk domain-tagging
# categories are reachable here. Sensitive categories (risk, vip_tier, ...)
# must go through the full M03 tag modal, which shows the whole tag picker
# and requires an explicit save action.
INLINE_ALLOWED_CATEGORIES = {"health_domain", "health_concern"}

# Row label shown by _s14_collect_row.html's tag_multiselect variant, keyed by
# category. Falls back to the raw category string for any future whitelisted
# category that hasn't got a Vietnamese label yet.
_INLINE_CATEGORY_LABEL = {
    "health_domain": "Lĩnh vực sức khỏe",
    "health_concern": "Vấn đề sức khỏe",
}

# M03 free-text tag creation (rep-facing): categories excluded here drive
# automated business logic downstream (mart_customer_action_queue — see
# plans/260706-1738-crm-tag-signal-action-queue-consumer) and must stay
# admin-curated (M14) to avoid typo/near-duplicate tags silently affecting
# worklist prioritization. Reps can still *attach* an existing tag in these
# categories from M03 — only ad-hoc creation is blocked.
CREATE_EXCLUDED_CATEGORIES = {"risk", "vip_tier"}

# Vietnamese labels for the M03 create-form category dropdown. Falls back to
# the raw category string for any category not listed here.
_CREATE_CATEGORY_LABEL = {
    "behavioral": "Hành vi mua",
    "demographic": "Đặc điểm KH",
    "preference": "Sở thích SP",
    "source": "Nguồn gốc",
    "health_domain": "Lĩnh vực sức khỏe",
    "health_concern": "Vấn đề sức khỏe",
    "general": "Chung",
}

_SLUG_DIACRITICS_RE = re.compile(r"[̀-ͯ]")
_SLUG_INVALID_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    """Convert free-text (Vietnamese OK) into a crm_tag.name slug.

    'đ'/'Đ' don't decompose under NFKD like other diacritics, so they're
    mapped explicitly before normalizing the rest.
    """
    text = text.replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFKD", text)
    stripped = _SLUG_DIACRITICS_RE.sub("", normalized)
    return _SLUG_INVALID_RE.sub("-", stripped.lower()).strip("-")


def _build_m03_context(request: Request, profile: ProfileSvc, party_id: str) -> dict:
    all_tags = profile.list_tags("")
    current = profile.list_party_tags(party_id)
    party_tag_ids = {t.tag_id for t in current}
    party_name = ""
    try:
        p360 = profile.get_party_360(party_id)
        if p360:
            party_name = p360.display_name
    except Exception:
        pass
    categories_present = sorted({
        t.category for t in all_tags
        if t.category and t.category not in CREATE_EXCLUDED_CATEGORIES
    })
    available_categories = [(c, _CREATE_CATEGORY_LABEL.get(c, c)) for c in categories_present]
    return {
        "request": request, "party_id": party_id,
        "all_tags": all_tags, "party_tag_ids": party_tag_ids,
        "party_name": party_name, "available_categories": available_categories,
    }


def make_tags_modal_router(templates: Jinja2Templates, profile: ProfileSvc) -> APIRouter:
    router = APIRouter()

    @router.get("/modals/m03", response_class=HTMLResponse)
    async def get_modal_m03(request: Request, party_id: str) -> Response:
        return templates.TemplateResponse(
            "fragments/modal_m03_tags.html", _build_m03_context(request, profile, party_id),
        )

    @router.post("/customers/{party_id}/tags", response_class=HTMLResponse)
    async def post_tags(
        party_id: str,
        tag_ids: List[str] = Form(default=[]),
    ) -> Response:
        current = profile.list_party_tags(party_id)
        current_ids = {t.tag_id for t in current}
        submitted = set(tag_ids)
        try:
            for tid in current_ids - submitted:
                profile.detach_tag(party_id, tid)
            for tid in submitted - current_ids:
                profile.attach_tag(party_id, tid)
        except Exception as exc:
            log.error("post_tags %s: %s", party_id, exc)
            return HTMLResponse(f"Lỗi lưu tags: {exc}", status_code=500)
        return redirect_to_customer(party_id)

    @router.post("/customers/{party_id}/tags/inline", response_class=HTMLResponse)
    async def post_tags_inline(
        request: Request,
        party_id: str,
        category: str = Form(""),
        tag_names: List[str] = Form(default=[]),
    ) -> Response:
        """Phase 02 (260706-0833): S14 collect-row inline multi-tag assign.

        Whitelist enforced hard — category outside INLINE_ALLOWED_CATEGORIES
        is rejected with 400 before any lookup/attach happens.
        """
        category = category.strip()
        if category not in INLINE_ALLOWED_CATEGORIES:
            return HTMLResponse(f"Category không được phép qua inline: {category!r}", status_code=400)
        names = {n.strip() for n in tag_names if n.strip()}
        if not names:
            return HTMLResponse("tag_names là bắt buộc", status_code=400)

        current_user = getattr(request.state, "current_user", None)
        actor_id = getattr(current_user, "user_id", None)

        try:
            candidates = profile.list_tags(category)
            matched = [t for t in candidates if t.name in names]
        except Exception as exc:
            log.error("post_tags_inline lookup %s %s: %s", party_id, category, exc)
            return HTMLResponse("Lỗi tra cứu tag", status_code=500)
        if not matched:
            return HTMLResponse(
                f"Không tìm thấy tag nào khớp trong category {category!r}", status_code=400
            )
        try:
            for tag in matched:
                profile.attach_tag(party_id, tag.tag_id, actor_id, source="crm_user")
        except Exception as exc:
            log.error("post_tags_inline attach %s %s: %s", party_id, category, exc)
            return HTMLResponse("Lỗi lưu tag", status_code=500)

        labels = [t.display_label or t.name for t in matched]
        row = {
            "key": category,
            "label": _INLINE_CATEGORY_LABEL.get(category, category),
            "kind": "tag_multiselect",
            "category": category,
            "current": ", ".join(labels),
        }
        return templates.TemplateResponse(
            "fragments/_s14_collect_row.html",
            {"request": request, "party_id": party_id, "row": row, "saved": True},
        )

    @router.post("/customers/{party_id}/tags/create", response_class=HTMLResponse)
    async def post_tags_create(
        request: Request,
        party_id: str,
        name: str = Form(...),
        category: str = Form(""),
    ) -> Response:
        """M03 free-text provisional tag creation (rep-facing).

        Creates an L1 provisional tag (category given) or L2 (category left
        blank — admin assigns one later via the Tag Governance L2 queue) and
        attaches it to this party immediately. See CREATE_EXCLUDED_CATEGORIES
        for why risk/vip_tier are rejected here.
        """
        display_label = name.strip()
        if not display_label:
            return HTMLResponse("Tên tag không được để trống", status_code=400)
        category = category.strip()
        if category in CREATE_EXCLUDED_CATEGORIES:
            return HTMLResponse(
                f"Không thể tạo tag mới cho category {category!r} qua form này — dùng M14",
                status_code=400,
            )
        slug = _slugify(display_label)
        if not slug:
            return HTMLResponse("Tên tag không hợp lệ", status_code=400)

        current_user = getattr(request.state, "current_user", None)
        actor_id = getattr(current_user, "user_id", None)

        try:
            tag = profile.find_or_create_tag(
                name=slug, category=category or None,
                display_label=display_label, is_provisional=True,
            )
            profile.attach_tag(party_id, tag.tag_id, actor_id, source="crm_user")
        except Exception as exc:
            log.error("post_tags_create %s %s: %s", party_id, display_label, exc)
            return HTMLResponse("Lỗi tạo tag", status_code=500)

        return templates.TemplateResponse(
            "fragments/modal_m03_tags.html", _build_m03_context(request, profile, party_id),
        )

    return router
