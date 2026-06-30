"""Shared Jinja2 templates factory for the web layer.

Single seam for constructing the Jinja environment so every router shares the
same configuration. Production: ``auto_reload=False`` — templates are baked
into the container image and never change at runtime, while the default
(``auto_reload=True``) makes Jinja re-stat the filesystem on every
``{% include %}``. Under the container FS that stat costs ~8 ms, so loop-heavy
pages (the worklist renders ~8.5k icon includes) take ~17 s instead of ~20 ms.

Dev: set ``CRM_DEV_RELOAD=1`` to enable ``auto_reload=True`` so template edits
are picked up on the next request without restarting the container.

A preconfigured ``jinja2.Environment`` is passed to Starlette (rather than
``**env_options``) because Starlette deprecated forwarding env options. The
environment mirrors Starlette's defaults: a filesystem loader and
``autoescape=True`` (HTML escaping — do not drop, templates rely on it).
"""
from __future__ import annotations

import os
from datetime import date

import jinja2
from fastapi.templating import Jinja2Templates


def make_templates(directory: str) -> Jinja2Templates:
    """Return a Jinja2Templates instance.

    auto_reload follows CRM_DEV_RELOAD env var (1 = dev, anything else = prod).
    """
    dev = os.environ.get("CRM_DEV_RELOAD", "0") == "1"
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(directory),
        autoescape=True,
        auto_reload=dev,
    )
    # today() callable so it resolves at render time, not at startup
    env.globals["today"] = lambda: date.today().isoformat()

    # Margin quality thresholds (visual classification)
    _MARGIN_GOOD = 0.28
    _MARGIN_BAD = 0.24

    def _fmt_discount_pct(rate) -> str:
        if rate is None:
            return ""
        return f"{rate * 100:.0f}%"

    def _format_date_key(dk) -> str:
        s = str(int(dk))
        return f"{s[:4]}-{s[4:6]}-{s[6:]}" if len(s) == 8 else s

    def _margin_quality_cls(pct) -> str:
        if pct is None:
            return ""
        if pct >= _MARGIN_GOOD:
            return "pct--good"
        if pct < _MARGIN_BAD:
            return "pct--bad"
        return ""

    env.filters["fmt_discount_pct"] = _fmt_discount_pct
    env.filters["format_date_key"] = _format_date_key
    env.filters["margin_quality_cls"] = _margin_quality_cls

    return Jinja2Templates(env=env)
