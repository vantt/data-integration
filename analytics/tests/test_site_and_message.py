"""Report site Caddyfile and summary message rendering."""
from __future__ import annotations

import copy
from datetime import date

import pytest

from analytics.compiler.loader import CATALOG_FILE, load_catalog, load_profile, load_registry, profile_path
from analytics.renderers import message, site

PROFILE = load_profile(profile_path("fine_japan"))


def test_committed_caddyfile_is_up_to_date():
    assert site.OUT_FILE.read_text(encoding="utf-8") == site.render_caddyfile(PROFILE), \
        "run: python3 -m analytics render site"


def test_every_area_has_its_own_login_and_root():
    text = site.render_caddyfile(PROFILE)
    for area in PROFILE["access"]["areas"]:
        assert f"import /etc/caddy/users/{area['id']}.caddy" in text
        assert f"root * /srv/{area['id']}/current" in text
    assert "handle_path /dieu-hanh/*" in text
    assert text.count("basic_auth {") == len(PROFILE["access"]["areas"])


def test_without_legacy_area_other_paths_are_404():
    profile = copy.deepcopy(PROFILE)
    profile["access"]["areas"] = [a for a in profile["access"]["areas"] if not a.get("legacy")]
    text = site.render_caddyfile(profile)
    assert "respond 404" in text and "legacy" not in text


def test_new_area_gets_a_path():
    profile = copy.deepcopy(PROFILE)
    profile["access"]["areas"].insert(0, {"id": "ban-hang", "title": "Bán hàng", "functions": ["SAL"], "can_view_cost": False})
    text = site.render_caddyfile(profile)
    assert "handle_path /ban-hang/*" in text and "import /etc/caddy/users/ban-hang.caddy" in text


@pytest.mark.parametrize("value,unit,decimals,expected", [
    (1234567.4, "currency", None, "1.234.567 ₫"),
    (12.345, "percent", None, "12,3 %"),
    (1.456, "index", 2, "1,46"),
    (None, "count", None, "–"),
    (42, "count", None, "42"),
])
def test_format_number(value, unit, decimals, expected):
    assert message.format_number(value, unit, decimals) == expected


def test_format_change():
    assert message.format_change(120, 100, "currency") == "▲ 20,0 %"
    assert message.format_change(40.0, 45.5, "percent") == "▼ 5,5 điểm %"
    assert message.format_change(10, 0, "count") is None


def test_tiles_drop_costs_for_channels_without_cost_access():
    reg, catalog = load_registry(), load_catalog(CATALOG_FILE)
    full = message.summary_tiles(reg, PROFILE, catalog, CATALOG_FILE, "ceo_weekly_pulse", date(2026, 10, 18), True)
    restricted = message.summary_tiles(reg, PROFILE, catalog, CATALOG_FILE, "ceo_weekly_pulse", date(2026, 10, 18), False)
    assert {t.card_id for t in full} == set(catalog["reports"][0]["kpi_tiles"])
    assert {t.card_id for t in full} - {t.card_id for t in restricted} == {"channel_net_profit_wow", "gross_margin_wow"}
    for tile in full:
        assert "DATE '2026-10-18'" in tile.sql and "now()" not in tile.sql


def test_summary_card_fields_and_link():
    report = load_catalog(CATALOG_FILE)["reports"][0]
    tile = message.Tile("net_sales_wow", "Doanh thu bán hàng", "net_sales", "currency", None, "prev_week_full", "")
    title, fields = message.summary_card(report, [tile], {"net_sales_wow": {"net_sales": 200, "net_sales__cmp": 100}},
                                         date(2026, 10, 18), message.report_link(PROFILE, report))
    assert title == "CEO Weekly Pulse — 18/10/2026"
    assert fields["Doanh thu bán hàng"] == "200 ₫ (▲ 100,0 % so với tuần trước)"
    assert fields["Xem báo cáo"] == "[CEO Weekly Pulse](https://evidence.lan.fwg.vn/dieu-hanh/ceo_weekly_pulse/)"
