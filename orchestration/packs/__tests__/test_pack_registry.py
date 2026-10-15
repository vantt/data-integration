"""Pack package contract and modules.yaml loading."""
from __future__ import annotations

import pytest
import yaml

from orchestration import packs

PACKAGE_EXPORTS = ("ASSETS", "NIGHTLY_ASSETS", "AFTER_SERVING_ASSETS")
JOBS_EXPORTS = ("JOBS", "SCHEDULES", "SENSORS")


@pytest.fixture
def modules_file(tmp_path, monkeypatch):
    def write(ids):
        path = tmp_path / "modules.yaml"
        path.write_text(yaml.safe_dump({"connectors": [], "packs": ids}))
        monkeypatch.setattr(packs, "_MODULES_FILE", path)
    return write


def test_load_enabled_returns_only_listed_packs(modules_file):
    modules_file(["hug", "finance"])
    assert packs.enabled_ids() == ["hug", "finance"]
    assert [m.__name__ for m in packs.load_enabled()] == ["orchestration.packs.hug", "orchestration.packs.finance"]
    assert [m.__name__ for m in packs.load_enabled_jobs()] == [
        "orchestration.packs.hug.jobs", "orchestration.packs.finance.jobs"]


def test_missing_packs_key_loads_nothing(tmp_path, monkeypatch):
    path = tmp_path / "modules.yaml"
    path.write_text(yaml.safe_dump({"connectors": ["hug"]}))
    monkeypatch.setattr(packs, "_MODULES_FILE", path)
    assert packs.load_enabled() == []


def test_unknown_pack_fails_loudly(modules_file):
    modules_file(["no_such_pack"])
    with pytest.raises(ModuleNotFoundError):
        packs.load_enabled()


def test_every_enabled_pack_honours_the_contract():
    assert packs.enabled_ids() == ["crm", "hug", "finance", "sales_playbook", "marketplace",
                                   "facebook_ads", "facebook_messenger"]
    for pkg, jobs in zip(packs.load_enabled(), packs.load_enabled_jobs()):
        for name in PACKAGE_EXPORTS:
            assert isinstance(getattr(pkg, name), list), f"{pkg.__name__} lacks {name}"
        for name in JOBS_EXPORTS:
            assert isinstance(getattr(jobs, name), list), f"{jobs.__name__} lacks {name}"
        assert set(map(id, pkg.NIGHTLY_ASSETS)) <= set(map(id, pkg.ASSETS))
        assert set(map(id, pkg.AFTER_SERVING_ASSETS)) <= set(map(id, pkg.ASSETS))


def test_crm_pack_keeps_its_asset_and_job_names():
    crm = packs.load_enabled(["crm"])[0]
    names = {key.to_user_string() for a in crm.ASSETS for key in a.keys}
    assert {"crm_cache_refresh", "crm_backup", "crm_restore_verify", "crm_task_export"} <= names
    assert len(crm.ASSETS) == 14
    jobs = packs.load_enabled_jobs(["crm"])[0]
    assert [j.name for j in jobs.JOBS] == ["crm_backup_job"]
    assert [s.name for s in jobs.SCHEDULES] == ["crm_backup_schedule"]
    assert [a.key.to_user_string() for a in crm.AFTER_SERVING_ASSETS] == ["crm_cache_refresh"]


def test_packs_without_dagster_code_export_empty_lists():
    """marketplace and facebook_* exist so modules.yaml lists every dbt pack folder."""
    ids = ["marketplace", "facebook_ads", "facebook_messenger"]
    for pkg, jobs in zip(packs.load_enabled(ids), packs.load_enabled_jobs(ids)):
        assert pkg.ASSETS == [] and pkg.NIGHTLY_ASSETS == [] and pkg.AFTER_SERVING_ASSETS == []
        assert jobs.JOBS == [] and jobs.SCHEDULES == [] and jobs.SENSORS == []
