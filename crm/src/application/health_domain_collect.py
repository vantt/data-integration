"""Shared helper for S14 health-domain collect-row gap detection.

Both the full-screen call cockpit route (screen_call_cockpit.py) and the
embedded S03 panel route (screen_customer_360_panels.py) need the same two
pieces of health-domain context: whether the party already has a
health_domain tag (gap check) and, when the gap exists, the ordered chip
options to render (crm_tag rows in category='health_domain', ranked by
attach-count). Centralised here to avoid duplicating try/except boilerplate
in both call sites.

Part of plan 260706-0833-crm-health-profile-tag-governance (Phase 02).
"""
from __future__ import annotations

import logging

from domain.entities.profile import Tag

log = logging.getLogger(__name__)

HEALTH_DOMAIN_CATEGORY = "health_domain"


def load_health_domain_collect_context(tags_svc, party_id: str) -> dict:
    """Return ``{"has_health_domain_tag": bool, "health_domain_options": list[Tag]}``.

    ``tags_svc`` is optional (None when a composition root hasn't wired a tag
    service into this route) — degrades to "no gap shown" (has_health_domain_tag
    reported True to suppress the collect row) rather than rendering a picker
    with no working options or raising.
    """
    options: list[Tag] = []
    if tags_svc is None:
        return {"has_health_domain_tag": True, "health_domain_options": options}
    has_tag = False
    try:
        party_tags = tags_svc.list_party_tags(party_id)
        has_tag = any(getattr(t, "category", None) == HEALTH_DOMAIN_CATEGORY for t in party_tags)
    except Exception as exc:
        log.warning("health_domain_collect: list_party_tags %s: %s", party_id, exc)
    if not has_tag:
        try:
            options = tags_svc.list_tags_by_category_ordered_by_usage(HEALTH_DOMAIN_CATEGORY)
        except Exception as exc:
            log.warning(
                "health_domain_collect: list_tags_by_category_ordered_by_usage %s: %s",
                party_id, exc,
            )
    return {"has_health_domain_tag": has_tag, "health_domain_options": options}
