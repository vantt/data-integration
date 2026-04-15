"""Load and merge SLA config from orchestration/config/ingestion_sla.yaml.

Provides a single entry point: get_sla(asset_key_str) -> dict.
Falls back to defaults for any key not explicitly listed — never raises.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

_log = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "orchestration" / "config" / "ingestion_sla.yaml"

# Cached after first load (module-level singleton)
_sla_cache: dict[str, Any] | None = None


def _load() -> dict[str, Any]:
    global _sla_cache
    if _sla_cache is not None:
        return _sla_cache

    try:
        with open(_CONFIG_PATH) as fh:
            raw = yaml.safe_load(fh)
    except FileNotFoundError:
        _log.warning("ingestion_sla.yaml not found at %s — using hardcoded defaults", _CONFIG_PATH)
        raw = {}

    _sla_cache = raw or {}
    return _sla_cache


def get_defaults() -> dict[str, Any]:
    data = _load()
    return data.get("defaults", {})


def get_sla(asset_key_str: str) -> dict[str, Any]:
    """Return merged SLA config for the given asset key string.

    Keys in the per-asset block override defaults. Missing asset falls back
    entirely to defaults. Never raises.
    """
    data = _load()
    defaults = data.get("defaults", {})
    per_asset: dict[str, Any] = data.get("assets", {}).get(asset_key_str, {})

    if not per_asset and asset_key_str not in data.get("assets", {}):
        _log.warning(
            "Asset key '%s' not found in ingestion_sla.yaml — using defaults only",
            asset_key_str,
        )

    merged = {**defaults, **{k: v for k, v in per_asset.items() if v is not None}}
    # Explicit null in YAML means "disable" — keep nulls for those keys
    for k, v in per_asset.items():
        if v is None:
            merged[k] = None

    return merged


def list_asset_keys() -> list[str]:
    """Return all asset key strings defined in the YAML."""
    data = _load()
    return list(data.get("assets", {}).keys())
