"""Guard the Jinja templates factory configuration.

auto_reload=False in prod (CRM_DEV_RELOAD unset/0): Jinja re-stats the
filesystem on every {% include %}; under the container FS that turns the
worklist (~8.5k icon includes) from ~20ms into ~17s.

auto_reload=True in dev (CRM_DEV_RELOAD=1): template edits are visible on
the next request without restarting the container.
"""
from __future__ import annotations

import pytest

from adapters.inbound.web.templating import make_templates


def test_make_templates_prod_disables_auto_reload(tmp_data_dir, monkeypatch):
    monkeypatch.delenv("CRM_DEV_RELOAD", raising=False)
    templates = make_templates(tmp_data_dir)
    assert templates.env.auto_reload is False


def test_make_templates_dev_enables_auto_reload(tmp_data_dir, monkeypatch):
    monkeypatch.setenv("CRM_DEV_RELOAD", "1")
    templates = make_templates(tmp_data_dir)
    assert templates.env.auto_reload is True
