"""Shared Jinja2 templates factory for the web layer.

Single seam for constructing the Jinja environment so every router shares the
same configuration. Crucially sets ``auto_reload=False``: templates are baked
into the container image and never change at runtime, while the default
(``auto_reload=True``) makes Jinja re-stat the filesystem on every
``{% include %}``. Under the container FS that stat costs ~8 ms, so loop-heavy
pages (the worklist renders ~8.5k icon includes) take ~17 s instead of ~20 ms.

A preconfigured ``jinja2.Environment`` is passed to Starlette (rather than
``**env_options``) because Starlette deprecated forwarding env options. The
environment mirrors Starlette's defaults: a filesystem loader and
``autoescape=True`` (HTML escaping — do not drop, templates rely on it).
"""
from __future__ import annotations

import jinja2
from fastapi.templating import Jinja2Templates


def make_templates(directory: str) -> Jinja2Templates:
    """Return a Jinja2Templates configured for production rendering speed."""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(directory),
        autoescape=True,
        auto_reload=False,
    )
    return Jinja2Templates(env=env)
