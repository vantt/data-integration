"""Pre-create the rolling export directories that dbt external models write into.

DuckDB `COPY ... TO '<dir>/<file>.parquet'` fails when the parent directory is missing, and
get_rolling_location() writes `$DBT_EXPORT_PATH/rolling/<model>/<model>_<ts>.parquet`. The
model list comes from the dbt manifest (external models whose location uses
get_rolling_location), so it does not depend on which folder a model lives in. Without a
manifest (fresh install, before the first `dbt parse`) every model file under models/ that
calls get_rolling_location() is used.

Used by scripts/ensure_dbt_directories.py (container start), the sapo_dbt_assets op and
transformation/scripts/run_dbt.py.
"""
from __future__ import annotations

import glob
import json
import os

ROLLING_MACRO = "get_rolling_location"


def rolling_model_names(project_dir: str, manifest_path: str | None = None) -> list[str]:
    manifest_path = manifest_path or os.path.join(project_dir, "target", "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path) as fh:
            nodes = json.load(fh)["nodes"]
        return sorted(
            n["name"] for n in nodes.values()
            if n["resource_type"] == "model"
            and n["config"].get("materialized") == "external"
            and ROLLING_MACRO in str(n["config"].get("location") or "")
        )
    names = set()
    for path in glob.glob(os.path.join(project_dir, "models", "**", "*.sql"), recursive=True):
        with open(path, encoding="utf-8") as fh:
            if ROLLING_MACRO in fh.read():
                names.add(os.path.splitext(os.path.basename(path))[0])
    return sorted(names)


def ensure_rolling_dirs(export_path: str, model_names: list[str]) -> list[str]:
    """Create `<export_path>/rolling/<model>` for each model; return the directories created."""
    created = []
    for name in model_names:
        target = os.path.join(export_path, "rolling", name)
        if not os.path.isdir(target):
            os.makedirs(target, exist_ok=True)
            created.append(target)
    return created
