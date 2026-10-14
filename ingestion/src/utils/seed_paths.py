"""Locate dbt seed CSVs by name.

Seeds live in subfolders of ``transformation/seeds/`` (for example ``taxonomy/``). Python code
that reads or writes a seed must not hard-code the subfolder, otherwise moving a seed breaks
the writer silently. ``seed_path("ref_brands")`` finds the one file ``**/ref_brands.csv``.

dbt requires seed names to be unique across folders, so more than one match is an error here
too (scripts/checks/check_boundaries.py reports the same condition at review time).
"""
from __future__ import annotations

from pathlib import Path

# ingestion/src/utils/seed_paths.py -> repository root is three levels above ``utils``
REPO_ROOT = Path(__file__).resolve().parents[3]
SEEDS_DIR = REPO_ROOT / "transformation" / "seeds"


class SeedNotFoundError(FileNotFoundError):
    """No seed CSV with that name exists under the seeds directory."""


class AmbiguousSeedError(RuntimeError):
    """More than one seed CSV with that name exists under the seeds directory."""


def seed_path(name: str, seeds_dir: str | Path | None = None) -> Path:
    """Return the path of the seed ``name`` (without ``.csv``) under ``seeds_dir``.

    Raises SeedNotFoundError when there is no such file and AmbiguousSeedError when the name
    is not unique. ``seeds_dir`` defaults to ``transformation/seeds`` of this checkout.
    """
    if not name or "/" in name or "\\" in name or name.endswith(".csv"):
        raise ValueError(f"seed name must be a bare name without folder or extension, got {name!r}")
    root = Path(seeds_dir) if seeds_dir is not None else SEEDS_DIR
    matches = sorted(p for p in root.rglob(f"{name}.csv") if p.is_file())
    if not matches:
        raise SeedNotFoundError(f"seed {name!r} not found under {root}")
    if len(matches) > 1:
        listed = ", ".join(str(p.relative_to(root)) for p in matches)
        raise AmbiguousSeedError(f"seed {name!r} is not unique under {root}: {listed}")
    return matches[0]
