"""Load the metric registry (semantic models + metrics) and tenant profiles from YAML."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PACKAGE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_DIR.parent
REGISTRY_DIR = PACKAGE_DIR / "registry"
SCHEMA_DIR = PACKAGE_DIR / "schema"
TENANTS_DIR = REPO_ROOT / "tenants"


class RegistryError(Exception):
    """The registry or a profile cannot be loaded (unreadable YAML, duplicate id, missing file)."""


@dataclass
class Registry:
    root: Path
    semantic: dict[str, dict[str, Any]] = field(default_factory=dict)
    metrics: dict[str, dict[str, Any]] = field(default_factory=dict)
    # id -> file the definition came from, relative to the repository when possible
    sources: dict[str, str] = field(default_factory=dict)
    # raw documents, kept for JSON Schema validation: (relative path, kind, document)
    documents: list[tuple[str, str, Any]] = field(default_factory=list)

    def model(self, model_id: str) -> dict[str, Any]:
        try:
            return self.semantic[model_id]
        except KeyError:
            raise RegistryError(f"unknown semantic model '{model_id}'") from None

    def metric(self, metric_id: str) -> dict[str, Any]:
        try:
            return self.metrics[metric_id]
        except KeyError:
            raise RegistryError(f"unknown metric '{metric_id}'") from None


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_yaml(path: Path) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except OSError as exc:
        raise RegistryError(f"{_rel(path)}: cannot read ({exc.strerror})") from exc
    except yaml.YAMLError as exc:
        raise RegistryError(f"{_rel(path)}: invalid YAML ({exc})") from exc


def load_schema(name: str) -> dict[str, Any]:
    path = SCHEMA_DIR / f"{name}.schema.json"
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"{_rel(path)}: cannot load schema ({exc})") from exc


def load_registry(root: Path | None = None) -> Registry:
    """Read every semantic model and metric file under `root` (default: analytics/registry).

    Files are read in sorted order so that every derived output is deterministic.
    """
    root = Path(root) if root else REGISTRY_DIR
    reg = Registry(root=root)
    sem_dir, met_dir = root / "semantic", root / "metrics"
    if not sem_dir.is_dir() or not met_dir.is_dir():
        raise RegistryError(f"{_rel(root)}: expected sub-directories semantic/ and metrics/")

    for path in sorted(sem_dir.glob("*.yml")):
        doc = read_yaml(path)
        reg.documents.append((_rel(path), "semantic", doc))
        if not isinstance(doc, dict) or "id" not in doc:
            continue  # reported by schema validation
        mid = doc["id"]
        if mid in reg.semantic:
            raise RegistryError(f"{_rel(path)}: duplicate semantic model id '{mid}' (also in {reg.sources[mid]})")
        reg.semantic[mid] = doc
        reg.sources[mid] = _rel(path)

    for path in sorted(met_dir.glob("*.yml")):
        doc = read_yaml(path)
        reg.documents.append((_rel(path), "metric", doc))
        items = doc.get("metrics") if isinstance(doc, dict) else None
        if not isinstance(items, list):
            continue  # reported by schema validation
        for item in items:
            if not isinstance(item, dict) or "id" not in item:
                continue
            mid = item["id"]
            if mid in reg.metrics:
                raise RegistryError(f"{_rel(path)}: duplicate metric id '{mid}' (also in {reg.sources['metric:' + mid]})")
            reg.metrics[mid] = item
            reg.sources["metric:" + mid] = _rel(path)
    return reg


CATALOG_FILE = PACKAGE_DIR / "catalog" / "catalog.yml"


def load_catalog(path: Path | None = None) -> dict[str, Any]:
    doc = read_yaml(Path(path) if path else CATALOG_FILE)
    if not isinstance(doc, dict):
        raise RegistryError(f"{_rel(Path(path) if path else CATALOG_FILE)}: the catalog must be a mapping")
    return doc


def spec_file(catalog_path: Path, spec_ref: str) -> Path:
    """A catalog `spec` entry is relative to the analytics package root (catalog/..)."""
    return Path(catalog_path).resolve().parent.parent / spec_ref


def load_spec(path: Path) -> dict[str, Any]:
    doc = read_yaml(Path(path))
    if not isinstance(doc, dict):
        raise RegistryError(f"{_rel(Path(path))}: a report spec must be a mapping")
    return doc


def profile_path(tenant: str) -> Path:
    return TENANTS_DIR / tenant / "analytics" / "profile.yml"


def load_profile(path: Path) -> dict[str, Any]:
    doc = read_yaml(Path(path))
    if not isinstance(doc, dict):
        raise RegistryError(f"{_rel(Path(path))}: a profile must be a mapping")
    return doc


def discover_profiles() -> list[Path]:
    """Every tenant profile in the repository (tenants/<t>/analytics/profile.yml)."""
    if not TENANTS_DIR.is_dir():
        return []
    return sorted(TENANTS_DIR.glob("*/analytics/profile.yml"))
