# Phase 1 — i18n Infrastructure

**Status:** Todo  
**Effort:** ~2h

## Overview

Build the core i18n plumbing: locale loader, `t()` function via `ContextVar`, FastAPI middleware, and single injection into Jinja2 globals. No string migration yet.

## Files to create

### `crm/src/adapters/inbound/web/i18n.py`

```python
"""JSON locale loader and request-scoped t() function.

Uses contextvars.ContextVar so t() can be called from anywhere in
a request — Jinja2 filters, helpers, handlers — without passing lang explicitly.
Middleware calls set_lang() once per request; everything downstream reads it.
"""
from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

_LOCALES_DIR = Path(__file__).parent / "locales"
_SUPPORTED = {"vi", "en"}
_DEFAULT_LANG = "vi"

_current_lang: ContextVar[str] = ContextVar("lang", default=_DEFAULT_LANG)
_locale_cache: dict[str, dict] = {}


def _load(lang: str) -> dict:
    if lang not in _locale_cache:
        path = _LOCALES_DIR / f"{lang}.json"
        try:
            _locale_cache[lang] = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            log.warning("locale file not found: %s", path)
            _locale_cache[lang] = {}
    return _locale_cache[lang]


def set_lang(lang: str) -> None:
    """Set language for current async context (called by middleware)."""
    _current_lang.set(lang if lang in _SUPPORTED else _DEFAULT_LANG)


def get_lang() -> str:
    return _current_lang.get()


def t(key: str) -> str:
    """Translate key using dot-notation. Falls back to key itself if missing."""
    data = _load(_current_lang.get())
    val = data
    for part in key.split("."):
        if isinstance(val, dict):
            val = val.get(part)
        else:
            val = None
        if val is None:
            # Fallback to vi if key missing in en
            if _current_lang.get() != _DEFAULT_LANG:
                return t_lang(key, _DEFAULT_LANG)
            return key
    return val if isinstance(val, str) else key


def t_lang(key: str, lang: str) -> str:
    """Translate key in a specific language (used for fallback only)."""
    data = _load(lang)
    val = data
    for part in key.split("."):
        if isinstance(val, dict):
            val = val.get(part)
        else:
            return key
        if val is None:
            return key
    return val if isinstance(val, str) else key
```

## Files to modify

### `crm/src/composition.py` — add middleware + inject globals

```python
# Add import at top
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from adapters.inbound.web.i18n import set_lang, get_lang, t

# After app = FastAPI(...):
class _LangMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        lang = request.cookies.get("lang", "vi")
        set_lang(lang)
        response = await call_next(request)
        return response

app.add_middleware(_LangMiddleware)

# In section "6. Templates + static", after make_templates():
templates.env.globals["t"] = t
templates.env.globals["get_lang"] = get_lang
```

### `crm/src/adapters/inbound/web/templates/layout.html` — add lang toggle

Add a small toggle button in the nav/header area:
```html
<form method="post" action="/set-lang" style="display:inline">
  <input type="hidden" name="lang" value="{{ 'en' if get_lang() == 'vi' else 'vi' }}">
  <button type="submit" class="btn-lang-toggle">
    {{ 'EN' if get_lang() == 'vi' else 'VI' }}
  </button>
</form>
```

### Add `/set-lang` route (in `routes.py` or `composition.py`)

```python
@app.post("/set-lang")
async def set_language(lang: str = Form("vi")):
    from fastapi.responses import RedirectResponse
    resp = RedirectResponse(url="/", status_code=302)
    resp.set_cookie("lang", lang if lang in {"vi", "en"} else "vi",
                    max_age=60*60*24*365, httponly=False)
    return resp
```

## Success criteria

- `t("common.back")` returns "Quay lại" when cookie=vi, "Back" when cookie=en
- Missing key falls back to vi then to key string (no exception)
- Toggle button switches lang and reloads page
- No per-handler changes needed — `t` works globally

## Notes

- `_locale_cache` is module-level dict → locales loaded once at first request, cached for lifetime of process. No hot-reload needed (internal tool).
- `ContextVar` is safe for async FastAPI — each request runs in its own async context.
- `set_cookie httponly=False` because JS may need to read it for future in-context editing (Tolgee integration).
