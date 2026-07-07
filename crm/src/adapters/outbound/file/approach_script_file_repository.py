"""approach_script_file_repository.py — File-based adapter for ApproachScriptRepository.

Reads {scripts_dir}/{customer_id}.json (UTF-8).
- Missing file → None (graceful empty state ST-CALL-NO-SCRIPT)
- Malformed JSON → log warning + None (no raise)
- refreshed_at = file mtime as ISO-8601 UTC ("...Z")
- list_customer_ids() uses os.scandir each call — no cache — so newly-dropped
  files are auto-reflected at next worklist load without restart.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_IDS_TTL = 60.0  # re-scan at most once per minute

from domain.entities.approach_script import ApproachScript

log = logging.getLogger(__name__)


class FileApproachScriptRepository:
    """Read-only file adapter: {scripts_dir}/{customer_id}.json → ApproachScript."""

    def __init__(self, scripts_dir: str | Path) -> None:
        self._scripts_dir = Path(scripts_dir)
        self._ids_cache: set[int] | None = None
        self._ids_cache_ts: float = 0.0

    @property
    def scripts_dir(self) -> Path:
        """Exposed so other adapters (e.g. the auto-load admin endpoint) write
        into the same directory without re-reading CRM_APPROACH_SCRIPT_DIR."""
        return self._scripts_dir

    def get_by_customer_id(self, customer_id: int) -> ApproachScript | None:
        """Return ApproachScript for customer_id, or None if file missing/malformed."""
        path = self._scripts_dir / f"{customer_id}.json"

        if not path.exists():
            return None

        # Capture mtime before reading so it's consistent even on slow FS.
        try:
            mtime = path.stat().st_mtime
        except OSError as exc:
            log.warning("approach_script: stat failed for cid=%s path=%s: %s", customer_id, path, exc)
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("approach_script: read/parse failed for cid=%s path=%s: %s", customer_id, path, exc)
            return None

        refreshed_at = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        # meta block: auto-gen scripts embed provenance (model, template_version).
        meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
        return ApproachScript.from_json(
            customer_id,
            data,
            refreshed_at,
            model=meta.get("model"),
            template_version=meta.get("template_version"),
        )

    def list_customer_ids(self) -> set[int]:
        """Return set of customer_ids with a script file, cached for _SCRIPT_IDS_TTL seconds.

        Uses os.scandir for efficiency; ignores non-matching filenames silently.
        Pattern: ^(\\d+)\\.json$  — e.g. 603264280.json → 603264280.
        """
        now = time.monotonic()
        if self._ids_cache is not None and (now - self._ids_cache_ts) < _SCRIPT_IDS_TTL:
            return self._ids_cache

        _PATTERN = re.compile(r"^(\d+)\.json$")
        result: set[int] = set()
        try:
            with os.scandir(self._scripts_dir) as it:
                for entry in it:
                    if not entry.is_file():
                        continue
                    m = _PATTERN.match(entry.name)
                    if m:
                        result.add(int(m.group(1)))
        except OSError as exc:
            log.warning("approach_script: scandir failed for dir=%s: %s", self._scripts_dir, exc)

        self._ids_cache = result
        self._ids_cache_ts = time.monotonic()
        return result
