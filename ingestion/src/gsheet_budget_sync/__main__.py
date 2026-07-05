"""CLI entrypoint — run with `python -m ingestion.src.gsheet_budget_sync [--dry-run]
[--write-suggestions [--target-month YYYY-MM]]` (see package __init__.py docstring)."""
import sys

from . import run

if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]) or 0)
