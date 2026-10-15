"""Validator of the metric registry (analytics/registry/) and tenant profiles.

  python3 scripts/checks/check_analytics_registry.py [--manifest <manifest.json>] [--registry <dir>] [--profile <path>]

Needs PyYAML and jsonschema (host python3 and the data_platform image have both). Runs in
scripts/checks/run-all.sh after `dbt parse`, so the column check reads a fresh manifest. Exit 1 on
any ERROR; WARN lines do not fail. Rules: analytics/README.md ("Lệnh").
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from analytics.compiler.validate import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
