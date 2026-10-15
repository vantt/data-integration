"""Connector sync jobs run the enabled packs' AFTER_SERVING_ASSETS without importing any pack."""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml
from dagster import AssetKey

from orchestration import packs
from orchestration.job_support import after_serving_selection
from orchestration.packs.crm import crm_sync

REPO = Path(__file__).resolve().parents[3]
MODULES = REPO / "orchestration" / "config" / "modules.yaml"
MANIFEST = REPO / "transformation" / "target" / "manifest.json"

# The connector sync jobs that rebuild serving and therefore end with the packs' after-serving assets.
CONNECTOR_SYNC_JOBS = [
    "ingest_filedrop_misa_account_ledger_job",
    "ingest_filedrop_misa_job",
    "ingest_filedrop_shopee_job",
    "ingest_sheets_sync_job",
    "pipeline_sapo_v2_incremental_job",
    "pipeline_sapo_v2_realtime_job",
]
CRM_REFRESH = "crm_cache_refresh"


def _packs_file(tmp_path, ids):
    path = tmp_path / "modules.yaml"
    path.write_text(yaml.safe_dump({"packs": ids}))
    return path


@pytest.mark.parametrize("ids,expected", [
    (["crm"], {AssetKey([CRM_REFRESH])}),
    (["crm", "hug", "finance", "sales_playbook"], {AssetKey([CRM_REFRESH])}),
    (["hug", "finance"], set()),
    ([], set()),
])
def test_after_serving_selection_follows_enabled_packs(tmp_path, monkeypatch, ids, expected):
    monkeypatch.setattr(packs, "_MODULES_FILE", _packs_file(tmp_path, ids))
    assert after_serving_selection().resolve([crm_sync.crm_cache_refresh]) == expected


def test_connector_jobs_do_not_import_packs():
    for jobs in sorted((REPO / "orchestration" / "connectors").glob("*/jobs.py")):
        assert "orchestration.packs" not in jobs.read_text(), jobs


_PROBE = textwrap.dedent("""
    import json, sys
    from pathlib import Path
    from orchestration import packs
    packs._MODULES_FILE = Path(sys.argv[1])
    from orchestration.definitions import defs
    repo = defs.get_repository_def()
    jobs = {j.name: sorted("/".join(k.path) for k in j.asset_layer.selected_asset_keys)
            for j in repo.get_all_jobs() if not j.name.startswith("__")}
    assets = sorted("/".join(k.path) for k in repo.asset_graph.get_all_asset_keys())
    print(json.dumps({"jobs": jobs, "assets": assets}))
""")


def _load_definitions(tmp_path, pack_ids):
    """Load orchestration.definitions in a fresh interpreter with the given packs enabled."""
    doc = yaml.safe_load(MODULES.read_text())
    doc["packs"] = pack_ids
    path = tmp_path / "modules.yaml"
    path.write_text(yaml.safe_dump(doc))
    out = subprocess.run([sys.executable, "-c", _PROBE, str(path)], cwd=REPO, capture_output=True,
                         text=True, timeout=300)
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


needs_manifest = pytest.mark.skipif(not MANIFEST.exists(), reason="needs transformation/target/manifest.json (dbt parse)")


@needs_manifest
def test_crm_enabled_connector_jobs_end_with_crm_cache_refresh(tmp_path):
    loaded = _load_definitions(tmp_path, yaml.safe_load(MODULES.read_text())["packs"])
    for job in CONNECTOR_SYNC_JOBS:
        assert CRM_REFRESH in loaded["jobs"][job], job


@needs_manifest
def test_crm_disabled_definitions_load_without_crm_cache_refresh(tmp_path):
    # sales_playbook depends on crm, so it goes off with it.
    ids = [p for p in yaml.safe_load(MODULES.read_text())["packs"] if p not in ("crm", "sales_playbook")]
    loaded = _load_definitions(tmp_path, ids)
    assert CRM_REFRESH not in loaded["assets"]
    for job in CONNECTOR_SYNC_JOBS:
        assert "build_serving_db" in " ".join(loaded["jobs"][job]), job
        assert CRM_REFRESH not in loaded["jobs"][job], job
    assert not [j for j, sel in loaded["jobs"].items() if CRM_REFRESH in sel]
