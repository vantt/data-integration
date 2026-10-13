"""Container-start step: pre-create rolling export directories for dbt external models.

Runs before `dbt parse` in the data_platform start command, so it uses the manifest left by
the previous parse (or scans models/ on a fresh install). The sapo_dbt_assets op repeats the
step after its own `dbt parse`, which covers models added since the last start.
"""
import os
import sys

PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "/app/transformation")
sys.path.insert(0, os.path.join(PROJECT_DIR, "scripts"))

from rolling_dirs import ensure_rolling_dirs, rolling_model_names  # noqa: E402


def ensure_directories():
    print("-> [Auto-Setup] checking dbt output directories...")
    dbt_export_path = os.environ.get("DBT_EXPORT_PATH")
    if not dbt_export_path:
        print("   [WARN] DBT_EXPORT_PATH not set. Skipping directory creation.")
        return

    names = rolling_model_names(PROJECT_DIR)
    print(f"   [DEBUG] {len(names)} rolling models")
    created = ensure_rolling_dirs(dbt_export_path, names)
    for d in created:
        print(f"   [+] Created directory: {d}")
    if created:
        print(f"-> [Auto-Setup] Created {len(created)} missing directories.")
    else:
        print("-> [Auto-Setup] All directories present.")


if __name__ == "__main__":
    ensure_directories()
