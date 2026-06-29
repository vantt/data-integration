"""screen_hug_campaign_html.py — public re-export facade for campaign HTML helpers.

Sub-modules (each ≤ 200 lines):
  screen_hug_campaign_html_list.py    — render_campaign_list + shared utils
  screen_hug_campaign_html_form.py    — render_campaign_form + render_status_result
  screen_hug_campaign_html_preview.py — render_preview_panel + overlap warnings
  screen_hug_campaign_html_history.py — render_history_page (Phase 6)

Import from here for a stable single-point public API; direct sub-module imports
are also fine (both paths resolve to the same implementation).
"""
from adapters.inbound.web.screens.hug.screen_hug_campaign_html_list import (  # noqa: F401
    render_campaign_list,
    _targeting_summary,
    _e,
)
from adapters.inbound.web.screens.hug.screen_hug_campaign_html_form import (  # noqa: F401
    render_campaign_form,
    render_status_result,
)
from adapters.inbound.web.screens.hug.screen_hug_campaign_html_preview import (  # noqa: F401
    render_preview_panel,
)
from adapters.inbound.web.screens.hug.screen_hug_campaign_html_history import (  # noqa: F401
    render_history_page,
)
