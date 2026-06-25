"""approach_script_file_repository.py — File-based adapter for ApproachScriptRepository.

Reads {scripts_dir}/{customer_id}.json (UTF-8).
- Missing file → None (graceful empty state ST-CALL-NO-SCRIPT)
- Malformed JSON → log warning + None (no raise)
- refreshed_at = file mtime as ISO-8601 UTC ("...Z")
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from domain.entities.approach_script import ApproachScript

log = logging.getLogger(__name__)


class FileApproachScriptRepository:
    """Read-only file adapter: {scripts_dir}/{customer_id}.json → ApproachScript."""

    def __init__(self, scripts_dir: str | Path) -> None:
        self._scripts_dir = Path(scripts_dir)

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
        return ApproachScript.from_json(customer_id, data, refreshed_at)
