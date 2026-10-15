"""The backup Lark card follows status/local.json: ok green, partial yellow, failed red."""
import json
from unittest.mock import MagicMock, patch

import pytest
from dagster import Failure

from orchestration.ops import system_backup as sb


def _status(tmp_path, state, errors=()):
    (tmp_path / "status").mkdir(exist_ok=True)
    (tmp_path / "status" / "local.json").write_text(json.dumps({"state": state, "errors": list(errors)}))


def _run(tmp_path, monkeypatch, run_side_effect=None):
    monkeypatch.setenv("BACKUP_ROOT", str(tmp_path))
    context = MagicMock(run_id="abcdef123456")
    with patch.object(sb, "_run_and_log", side_effect=run_side_effect), \
         patch.object(sb, "send_lark_card") as send:
        if run_side_effect:
            with pytest.raises(Failure):
                sb.run_platform_backup.compute_fn.decorated_fn(context)
        else:
            sb.run_platform_backup.compute_fn.decorated_fn(context)
    return send.call_args.kwargs


@pytest.mark.parametrize("state,color", [("ok", "green"), ("partial", "yellow")])
def test_card_color_follows_state(tmp_path, monkeypatch, state, color):
    _status(tmp_path, state, ["parity log export failed"] if state == "partial" else [])
    card = _run(tmp_path, monkeypatch)
    assert card["color"] == color
    assert ("Backup xong" in card["title"]) == (state == "ok")
    if state == "partial":
        assert "parity log export failed" in card["fields"]["Errors"]


def test_failure_is_red_even_with_a_stale_ok_status(tmp_path, monkeypatch):
    _status(tmp_path, "ok")
    card = _run(tmp_path, monkeypatch, run_side_effect=Failure("rc=1"))
    assert card["color"] == "red"


def test_missing_status_after_success_is_yellow(tmp_path, monkeypatch):
    card = _run(tmp_path, monkeypatch)
    assert card["color"] == "yellow"
    assert "missing" in card["fields"]["Errors"]
