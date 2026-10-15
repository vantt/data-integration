"""Report site orchestration: build request file, status sensor decisions, summary sending rules.

No network, no Lark call, no Evidence build: the notifier and the SQL runner are stubbed.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pytest

from orchestration.reports import build_request, build_status, summary_message
from orchestration.reports.build_status import evaluate

ICT = timezone(timedelta(hours=7))
MONDAY_0730 = datetime(2026, 10, 19, 7, 30, tzinfo=ICT)  # a Monday
PROFILE = {
    "locale": {"timezone": "Asia/Ho_Chi_Minh"},
    "message": {
        "channels": [{"id": "lanh_dao", "env_webhook": "TEST_REPORT_WEBHOOK", "can_view_cost": True},
                     {"id": "nhan_vien", "env_webhook": "TEST_STAFF_WEBHOOK", "can_view_cost": False}],
        "reports": [{"report": "ceo_weekly_pulse", "channels": ["lanh_dao"], "weekdays": ["mon"], "not_before": "07:00"}],
    },
}


class Alerts:
    def __init__(self):
        self.calls = []

    def __call__(self, title, fields, color="red", **kw):
        self.calls.append((title, fields, color))
        return True


def _status(ok=True, as_of="2026-10-18", rid="r1"):
    return {"request_id": rid, "ok": ok, "as_of": as_of,
            "areas": {"dieu-hanh": {"ok": ok, "error": "" if ok else "evidence build failed"}}}


def test_write_request_is_atomic_json(tmp_path):
    path = build_request.write_request("run-123", "nightly:abc", tmp_path)
    data = json.loads(path.read_text())
    assert data["request_id"] == "run-123" and data["trigger"] == "nightly:abc"
    assert not (tmp_path / "request.json.tmp").exists()


def test_failed_build_alerts_once():
    alerts = Alerts()
    runs, cur = evaluate({"request_id": "r1", "requested_at": MONDAY_0730.isoformat()}, _status(ok=False), {},
                         PROFILE, MONDAY_0730, alert=alerts)
    assert runs == [] and len(alerts.calls) == 1 and alerts.calls[0][2] == "red"
    assert "evidence build failed" in json.dumps(alerts.calls[0][1], ensure_ascii=False)
    runs, _ = evaluate({"request_id": "r1", "requested_at": MONDAY_0730.isoformat()}, _status(ok=False), cur,
                       PROFILE, MONDAY_0730, alert=alerts)
    assert len(alerts.calls) == 1  # not repeated


def test_overdue_request_alerts():
    alerts = Alerts()
    req = {"request_id": "r2", "requested_at": (MONDAY_0730 - timedelta(hours=3)).isoformat()}
    evaluate(req, _status(rid="r1"), {}, PROFILE, MONDAY_0730, alert=alerts)
    assert len(alerts.calls) == 1 and alerts.calls[0][2] == "orange"
    alerts2 = Alerts()
    fresh = {"request_id": "r2", "requested_at": (MONDAY_0730 - timedelta(minutes=30)).isoformat()}
    evaluate(fresh, _status(rid="r1"), {}, PROFILE, MONDAY_0730, alert=alerts2)
    assert alerts2.calls == []


def test_successful_fresh_build_triggers_due_summary_once():
    alerts = Alerts()
    runs, cur = evaluate(None, _status(), {}, PROFILE, MONDAY_0730, alert=alerts)
    assert [r.run_key for r in runs] == ["summary-ceo_weekly_pulse@2026-10-18"]
    cfg = runs[0].run_config["ops"]["send_report_summary"]["config"]
    assert cfg == {"report": "ceo_weekly_pulse", "as_of": "2026-10-18"}
    runs, _ = evaluate(None, _status(), cur, PROFILE, MONDAY_0730, alert=alerts)
    assert runs == [] and alerts.calls == []


@pytest.mark.parametrize("now,as_of", [
    (MONDAY_0730.replace(hour=6, minute=0), "2026-10-18"),   # before not_before
    (MONDAY_0730 + timedelta(days=1), "2026-10-19"),         # Tuesday
    (MONDAY_0730, "2026-10-17"),                             # stale build (nightly failed)
])
def test_no_summary_when_not_due_or_stale(now, as_of):
    runs, _ = evaluate(None, _status(as_of=as_of), {}, PROFILE, now, alert=Alerts())
    assert runs == []


class Log:
    def __init__(self):
        self.lines = []

    def info(self, m):
        self.lines.append(("info", m))

    def error(self, m):
        self.lines.append(("error", m))


@pytest.fixture()
def stub_queries(monkeypatch):
    calls = {"sent": []}
    monkeypatch.setattr(summary_message, "_query_rows",
                        lambda tiles, db: {t.card_id: {t.metric: 100, f"{t.metric}__cmp": 80} for t in tiles})
    monkeypatch.setattr(summary_message, "send_lark_card",
                        lambda title, fields, **kw: calls["sent"].append((title, fields, kw)) or True)
    return calls


def _profile(real_profile, **channel):
    profile = json.loads(json.dumps(real_profile))
    profile["message"] = {
        "channels": [{"id": "c", "env_webhook": "TEST_REPORT_WEBHOOK", "env_secret": "TEST_REPORT_SECRET",
                      "can_view_cost": True, **channel}],
        "reports": [{"report": "ceo_weekly_pulse", "channels": ["c"], "weekdays": ["mon"]}],
    }
    return profile


@pytest.fixture()
def real_profile():
    return summary_message.tenant_profile()


def test_dry_run_is_the_default(stub_queries, real_profile, monkeypatch):
    monkeypatch.delenv("REPORT_MESSAGE_DRY_RUN", raising=False)
    monkeypatch.setenv("TEST_REPORT_WEBHOOK", "https://example.invalid/hook")
    log = Log()
    out = summary_message.send_summary("ceo_weekly_pulse", date(2026, 10, 18), log, "unused", _profile(real_profile))
    assert out == {"c": "logged"} and stub_queries["sent"] == []
    assert any("dry run" in m for _, m in log.lines)


def test_missing_webhook_never_falls_back_to_the_alert_channel(stub_queries, real_profile, monkeypatch):
    monkeypatch.setenv("REPORT_MESSAGE_DRY_RUN", "0")
    monkeypatch.delenv("TEST_REPORT_WEBHOOK", raising=False)
    monkeypatch.setenv("LARK_ALERT_WEBHOOK", "https://example.invalid/alerts")
    out = summary_message.send_summary("ceo_weekly_pulse", date(2026, 10, 18), Log(), "unused", _profile(real_profile))
    assert out == {"c": "logged"} and stub_queries["sent"] == []


def test_send_with_webhook_and_cost_rules(stub_queries, real_profile, monkeypatch):
    monkeypatch.setenv("REPORT_MESSAGE_DRY_RUN", "0")
    monkeypatch.setenv("TEST_REPORT_WEBHOOK", "https://example.invalid/hook")
    monkeypatch.setenv("TEST_REPORT_SECRET", "s")
    out = summary_message.send_summary("ceo_weekly_pulse", date(2026, 10, 18), Log(), "unused", _profile(real_profile))
    assert out == {"c": "sent"}
    title, fields, kw = stub_queries["sent"][0]
    assert kw["webhook"] == "https://example.invalid/hook" and kw["secret"] == "s"
    assert "Lãi ròng kênh" in fields and "Biên lãi gộp" in fields
    assert fields["Xem báo cáo"].endswith("/dieu-hanh/ceo_weekly_pulse/)")
    stub_queries["sent"].clear()
    summary_message.send_summary("ceo_weekly_pulse", date(2026, 10, 18), Log(), "unused",
                                 _profile(real_profile, can_view_cost=False))
    _, fields, _ = stub_queries["sent"][0]
    assert "Lãi ròng kênh" not in fields and "Biên lãi gộp" not in fields
    assert "Doanh thu bán hàng" in fields


def test_query_error_does_not_raise(real_profile, monkeypatch):
    monkeypatch.setattr(summary_message, "_query_rows", lambda tiles, db: (_ for _ in ()).throw(RuntimeError("db gone")))
    log = Log()
    out = summary_message.send_summary("ceo_weekly_pulse", date(2026, 10, 18), log, "unused", _profile(real_profile))
    assert out == {"c": "error"} and any(level == "error" for level, _ in log.lines)
