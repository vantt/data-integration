"""Refuse to operate on the production checkout or its data.

The prod checkout is bind-mounted into the running `data_platform` container, so any
write under it changes production immediately. Shadow tooling calls this guard with every
path it is about to touch (code dir, lake dir, output dir).

Usage:
    python scripts/checks/guard_not_prod.py <path> [<path> ...]

Exit 0 when every path is outside the prod root, exit 1 otherwise. The prod root is fixed
on purpose (no env override) so a mistyped variable cannot disable the guard.
"""
from __future__ import annotations

import os
import sys

PROD_ROOT = "/home/vantt/app/fg-dataware-house"


def is_under_prod(path: str) -> bool:
    real = os.path.realpath(path)
    prod = os.path.realpath(PROD_ROOT)
    return real == prod or real.startswith(prod + os.sep)


def main(argv: list[str]) -> int:
    if not argv:
        print("guard_not_prod: no path given", file=sys.stderr)
        return 1
    bad = [p for p in argv if is_under_prod(p)]
    for p in bad:
        print(f"guard_not_prod: REFUSED {p} -> {os.path.realpath(p)} is inside {PROD_ROOT}", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
