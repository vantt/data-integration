"""Connector package contract and modules.yaml loading."""
from __future__ import annotations

from datetime import timedelta

import pytest
import yaml

from orchestration import connectors
from orchestration.asset_checks import sla_loader

PACKAGE_EXPORTS = (
    "ASSETS", "CHECK_ASSET_DEFS", "NIGHTLY_ASSETS", "DIGEST_ASSETS",
    "DIGEST_DISPLAY", "JOB_MAX_RUNTIME", "DBT_SOURCE_KEYS",
)
JOBS_EXPORTS = ("JOBS", "SCHEDULES", "SENSORS")


@pytest.fixture
def modules_file(tmp_path, monkeypatch):
    def write(ids):
        path = tmp_path / "modules.yaml"
        path.write_text(yaml.safe_dump({"connectors": ids}))
        monkeypatch.setattr(connectors, "_MODULES_FILE", path)
    return write


def test_enabled_ids_follow_file_order(modules_file):
    modules_file(["hug", "sheets"])
    assert connectors.enabled_ids() == ["hug", "sheets"]


def test_load_enabled_returns_only_listed_packages(modules_file):
    modules_file(["hug"])
    assert [m.__name__ for m in connectors.load_enabled()] == ["orchestration.connectors.hug"]
    assert [m.__name__ for m in connectors.load_enabled_jobs()] == ["orchestration.connectors.hug.jobs"]


def test_empty_list_loads_nothing(modules_file):
    modules_file([])
    assert connectors.load_enabled() == []


def test_unknown_connector_fails_loudly(modules_file):
    modules_file(["no_such_connector"])
    with pytest.raises(ModuleNotFoundError):
        connectors.load_enabled()


def test_every_enabled_connector_honours_the_contract():
    ids = connectors.enabled_ids()
    assert {"sapo_v2", "shopee", "misa_amis", "sheets", "hug"} <= set(ids)
    for pkg, jobs in zip(connectors.load_enabled(), connectors.load_enabled_jobs()):
        for name in PACKAGE_EXPORTS:
            assert hasattr(pkg, name), f"{pkg.__name__} lacks {name}"
        for name in JOBS_EXPORTS:
            assert hasattr(jobs, name), f"{jobs.__name__} lacks {name}"
        assert {s for s, _, _ in pkg.DIGEST_ASSETS} == set(pkg.DIGEST_DISPLAY)
        job_names = {j.name for j in jobs.JOBS}
        assert set(pkg.JOB_MAX_RUNTIME) <= job_names
        assert all(isinstance(v, timedelta) for v in pkg.JOB_MAX_RUNTIME.values())
        assert set(pkg.CHECK_ASSET_DEFS) <= set(sla_loader.list_asset_keys())
        assert {s.job_name for s in jobs.SCHEDULES} <= job_names


def test_connectors_do_not_share_names():
    packages = connectors.load_enabled()
    jobs = [j.name for m in connectors.load_enabled_jobs() for j in m.JOBS]
    assert len(jobs) == len(set(jobs))
    digest = [s for p in packages for s, _, _ in p.DIGEST_ASSETS]
    assert len(digest) == len(set(digest))


def test_missing_sla_file_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(sla_loader, "_CONFIG_PATH", tmp_path / "missing.yaml")
    monkeypatch.setattr(sla_loader, "_sla_cache", None)
    with pytest.raises(FileNotFoundError):
        sla_loader.get_sla("sapo/ingest_sapo_v2_orders_batch_asset")
