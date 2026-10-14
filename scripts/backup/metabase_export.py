#!/usr/bin/env python3
"""Export Metabase content (collections, cards, dashboards, and best effort users, groups,
permissions, subscriptions) to JSON files through the Metabase API.

  python3 scripts/backup/metabase_export.py <out_dir>

Called by backup.sh as a step of the nightly backup. The export is a readable record of the
content, not a full restore: ids, users' passwords, settings and history are not in it. The full
restore point is the cold copy of the H2 file (scripts/backup/metabase_cold_backup.sh).

Env: METABASE_URL (inside data_platform: http://metabase:3000), METABASE_API_KEY. The key is
sent as a header and never printed. Exit code 0 when collections, cards and dashboards were all
exported (optional parts may be skipped with a warning), 1 otherwise; backup.sh treats a non-zero
exit as a warning only.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

TIMEOUT_SEC = 60

# Optional content: exported when the API key's group may read it, skipped with a warning when not.
OPTIONAL = {
    "users.json": "/api/user",
    "permission_groups.json": "/api/permissions/group",
    "permissions_graph.json": "/api/permissions/graph",
    "collection_permissions_graph.json": "/api/collection/graph",
    "subscriptions.json": "/api/pulse",
}


class Api:
    def __init__(self, base: str, key: str):
        self.base = base.rstrip("/")
        self.key = key

    def get(self, path: str):
        req = urllib.request.Request(self.base + path, headers={"x-api-key": self.key})
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
            return json.load(resp)


def write(out_dir: str, name: str, data) -> None:
    path = os.path.join(out_dir, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)


def export(api: Api, out_dir: str) -> dict:
    counts: dict = {}
    warnings: list[str] = []

    collections = api.get("/api/collection")
    write(out_dir, "collections.json", collections)
    counts["collections"] = len(collections)

    # GET /api/card returns every card with its full query and visualization settings.
    cards = [c for c in api.get("/api/card") if not c.get("archived")]
    for card in cards:
        write(out_dir, f"cards/{card['id']}.json", card)
    counts["cards"] = len(cards)

    # The dashboard list omits dashcards and filters; fetch each dashboard in full.
    dashboards = [d for d in api.get("/api/dashboard") if not d.get("archived")]
    for d in dashboards:
        write(out_dir, f"dashboards/{d['id']}.json", api.get(f"/api/dashboard/{d['id']}"))
    counts["dashboards"] = len(dashboards)

    for name, path in OPTIONAL.items():
        try:
            data = api.get(path)
        except urllib.error.HTTPError as exc:
            warnings.append(f"{path}: HTTP {exc.code}, skipped")
            continue
        write(out_dir, name, data)
        # Lists (users, groups, subscriptions) are counted; graphs are single documents.
        items = data.get("data") if isinstance(data, dict) and "data" in data else data
        counts[name.removesuffix(".json")] = len(items) if isinstance(items, list) else "exported"

    props = api.get("/api/session/properties")
    return {
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "metabase_version": (props.get("version") or {}).get("tag"),
        "counts": counts,
        "warnings": warnings,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: metabase_export.py <out_dir>", file=sys.stderr)
        return 2
    out_dir = sys.argv[1]
    base = os.environ.get("METABASE_URL", "")
    key = os.environ.get("METABASE_API_KEY", "")
    if not base or not key:
        print("metabase export: METABASE_URL or METABASE_API_KEY is not set", file=sys.stderr)
        return 1
    os.makedirs(out_dir, exist_ok=True)
    try:
        manifest = export(Api(base, key), out_dir)
    except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
        # The message never contains the key: it is only ever sent as a request header.
        print(f"metabase export failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    write(out_dir, "manifest.json", manifest)
    c = manifest["counts"]
    print(
        f"metabase export: {c['dashboards']} dashboards, {c['cards']} cards, "
        f"{c['collections']} collections (Metabase {manifest['metabase_version']})"
    )
    for w in manifest["warnings"]:
        print(f"metabase export warning: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
