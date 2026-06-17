"""Guard the Jinja templates factory configuration.

Locks in auto_reload=False. With the default (True), Jinja re-stats the
filesystem on every {% include %}; under the container FS that turns the
worklist (~8.5k icon includes) from ~20ms into ~17s.
"""
from __future__ import annotations

from adapters.inbound.web.templating import make_templates


def test_make_templates_disables_auto_reload(tmp_data_dir):
    templates = make_templates(tmp_data_dir)
    assert templates.env.auto_reload is False
