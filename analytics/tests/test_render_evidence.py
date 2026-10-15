"""Evidence renderer: deterministic, committed output up to date, cost cards gated by area."""
from __future__ import annotations

import copy
import re

from analytics.compiler.loader import CATALOG_FILE, load_catalog, load_profile, load_registry, profile_path
from analytics.renderers import evidence as ev

PROFILE_PATH = profile_path("fine_japan")
COST_METRICS = ("channel_net_profit", "gross_margin_pct", "gross_profit", "cogs_amount")


def _render(profile=None):
    prof = profile or load_profile(PROFILE_PATH)
    return ev.render_tenant(load_registry(), prof, PROFILE_PATH, load_catalog(CATALOG_FILE), CATALOG_FILE)


def test_render_is_deterministic():
    assert _render().files == _render().files


def test_committed_output_is_up_to_date():
    assert ev.stale(_render()) == [], "run: python3 -m analytics render evidence"


def test_every_data_card_has_one_extract_and_no_clock():
    files = _render().files
    sources = [p for p in files if p.startswith("dieu-hanh/sources/datalake/ceo_weekly_pulse__")]
    assert len(sources) == 24 + 1  # 24 data cards + meta
    for path in sources:
        sql = files[path]
        assert sql.startswith("-- GENERATED"), path
        assert "current_date" not in sql.lower(), path
    assert files["dieu-hanh/evidence.config.yaml"].count("basePath: /dieu-hanh") == 1
    assert "legacy/" not in "".join(files)  # the legacy area holds hand-written pages only


def test_page_reads_only_its_extracts():
    page = _render().files["dieu-hanh/pages/ceo_weekly_pulse/index.md"]
    tables = set(re.findall(r"from (\w+\.\w+)", page))
    assert tables and all(t.startswith("datalake.ceo_weekly_pulse__") for t in tables)
    assert "Doanh thu được tính thế nào" in page


def test_area_without_cost_access_gets_no_cost_data():
    profile = copy.deepcopy(load_profile(PROFILE_PATH))
    for area in profile["access"]["areas"]:
        area["can_view_cost"] = False
    files = _render(profile).files
    assert not any("loss_making_channels" in p or "channel_net_profit_wow" in p or "gross_margin_wow" in p
                   for p in files)
    for path, content in files.items():
        for metric in COST_METRICS:
            assert metric not in content, (path, metric)
    assert ev.NO_COST_NOTE in files["dieu-hanh/pages/ceo_weekly_pulse/index.md"]
