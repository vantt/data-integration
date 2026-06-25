"""load_approach_scripts.py — Copy AI approach-script JSON files into the CRM data directory.

Renames script-NN-{customer_id}.json → {customer_id}.json so that
FileApproachScriptRepository can look them up by customer_id.

Extraction priority:
  1. Numeric customer_id from filename pattern: script-NN-{cid}.json
  2. JSON field customer_json.customer_id (fallback if filename doesn't match)

Idempotent: re-running overwrites existing files (no duplicates).

Usage:
  python scripts/load_approach_scripts.py [--src <dir>] [--dest <dir>]

Defaults:
  --src   plans/260624-1917-customer-insight-prompt-template/pilot-run-1/scripts/
  --dest  <CRM_DATA_DIR>/approach_scripts
          where CRM_DATA_DIR = dirname of CRM_DB_PATH env var
          or fallback /data/approach_scripts (Docker) / crm/data/approach_scripts (host)

Run from repo root or inside the CRM container.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Pattern: script-01-603264280.json → customer_id = 603264280
_FILENAME_RE = re.compile(r"^script-\d+-(\d+)\.json$", re.IGNORECASE)


def _default_src() -> Path:
    """Pilot scripts relative to repo root."""
    here = Path(__file__).parent
    return here.parent / "plans" / "260624-1917-customer-insight-prompt-template" / "pilot-run-1" / "scripts"


def _default_dest() -> Path:
    """Derive dest mirroring composition.py: CRM_APPROACH_SCRIPT_DIR override,
    else {CRM_DATA_DIR}/approach_scripts, then common fallbacks."""
    explicit = os.getenv("CRM_APPROACH_SCRIPT_DIR")
    if explicit:
        return Path(explicit)
    data_dir = os.getenv("CRM_DATA_DIR")  # docker-compose sets CRM_DATA_DIR=/data
    if data_dir:
        return Path(data_dir) / "approach_scripts"
    # Docker default
    docker_data = Path("/data/approach_scripts")
    if docker_data.parent.exists():
        return docker_data
    # Host dev default
    return Path(__file__).parent.parent / "crm" / "data" / "approach_scripts"


def _extract_customer_id(path: Path) -> int | None:
    """Extract customer_id from filename first, then JSON content."""
    m = _FILENAME_RE.match(path.name)
    if m:
        return int(m.group(1))
    # Fallback: look inside JSON
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cid = data.get("customer_json", {}).get("customer_id")
        if cid is not None:
            return int(cid)
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        pass
    return None


def load(src: Path, dest: Path) -> int:
    """Copy and rename scripts from src into dest. Returns count of files written."""
    if not src.exists():
        log.error("Source directory not found: %s", src)
        return 0

    os.makedirs(dest, exist_ok=True)
    log.info("Source: %s", src)
    log.info("Dest:   %s", dest)

    written = 0
    skipped = 0
    for json_file in sorted(src.glob("*.json")):
        customer_id = _extract_customer_id(json_file)
        if customer_id is None:
            log.warning("Skipping %s — cannot extract customer_id", json_file.name)
            skipped += 1
            continue
        target = dest / f"{customer_id}.json"
        shutil.copy2(json_file, target)
        log.info("  %s → %s/%d.json", json_file.name, dest.name, customer_id)
        written += 1

    log.info("Done: %d written, %d skipped", written, skipped)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Load pilot approach-script JSONs into CRM data dir.")
    parser.add_argument("--src", type=Path, default=_default_src(), help="Source directory of script-NN-{cid}.json files")
    parser.add_argument("--dest", type=Path, default=_default_dest(), help="Destination directory (approach_scripts/)")
    args = parser.parse_args()
    load(args.src, args.dest)


if __name__ == "__main__":
    main()
