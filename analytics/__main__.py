"""Command line: python3 -m analytics {validate|compile|render|docs} (analytics/README.md)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .compiler import validate as validate_mod
from .compiler.loader import RegistryError, load_profile, load_registry, profile_path
from .compiler.sql import AsOf, CompileError, compile_kpi
from .compiler.loader import CATALOG_FILE, load_catalog
from .renderers import evidence as evidence_renderer
from .renderers.docs import render_all

DOCS_DIR = validate_mod.DEFAULT_DOCS_DIR


def _profile(args: argparse.Namespace) -> dict:
    return load_profile(args.profile if args.profile else profile_path(args.tenant))


def cmd_compile(args: argparse.Namespace) -> int:
    reg = load_registry()
    profile = _profile(args)
    as_of = AsOf.runtime(profile["locale"]["timezone"]) if args.as_of == "runtime" else AsOf.literal(args.as_of)
    print(compile_kpi(reg, profile, args.metric, args.window, as_of, args.compare), end="")
    return 0


def cmd_docs(args: argparse.Namespace) -> int:
    reg = load_registry()
    stale = []
    for name, content in render_all(reg).items():
        path = DOCS_DIR / name
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == content:
            continue
        if args.check:
            stale.append(name)
        else:
            path.write_text(content, encoding="utf-8")
            print(f"wrote {path}")
    for name in stale:
        print(f"out of date: {DOCS_DIR / name} (run `python3 -m analytics docs`)")
    return 1 if stale else 0


def cmd_render(args: argparse.Namespace) -> int:
    if args.engine != "evidence":
        print(f"error: renderer '{args.engine}' does not exist yet", file=sys.stderr)
        return 2
    path = args.profile if args.profile else profile_path(args.tenant)
    rendered = evidence_renderer.render_tenant(load_registry(), load_profile(path), path,
                                               load_catalog(CATALOG_FILE), CATALOG_FILE)
    if args.check:
        stale = evidence_renderer.stale(rendered)
        for rel in stale:
            print(f"out of date: evidence/areas/{rel} (run `python3 -m analytics render evidence`)")
        return 1 if stale else 0
    for rel in evidence_renderer.write(rendered):
        print(f"wrote evidence/areas/{rel}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python3 -m analytics", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate", help="validate the registry (same as scripts/checks/check_analytics_registry.py)",
                   add_help=False)
    c = sub.add_parser("compile", help="print the SQL of one metric over one window")
    c.add_argument("--metric", required=True)
    c.add_argument("--window", required=True)
    c.add_argument("--compare", help="comparison window, returned as <metric>__cmp")
    c.add_argument("--as-of", required=True, help="YYYY-MM-DD, or 'runtime' for yesterday when the SQL runs")
    g = c.add_mutually_exclusive_group()
    g.add_argument("--tenant", default="fine_japan", help="tenant id (default: %(default)s)")
    g.add_argument("--profile", type=Path, help="explicit profile path")
    r = sub.add_parser("render", help="generate report files for an engine (evidence/areas/<area>/)")
    r.add_argument("engine", choices=["evidence"])
    rg = r.add_mutually_exclusive_group()
    rg.add_argument("--tenant", default="fine_japan", help="tenant id (default: %(default)s)")
    rg.add_argument("--profile", type=Path, help="explicit profile path")
    r.add_argument("--check", action="store_true", help="exit 1 when a generated file is out of date")
    d = sub.add_parser("docs", help="regenerate metric-registry.md and glossary.md")
    d.add_argument("--check", action="store_true", help="exit 1 when a generated file is out of date")

    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["validate"]:
        return validate_mod.main(argv[1:])
    args = p.parse_args(argv)
    try:
        return {"compile": cmd_compile, "docs": cmd_docs, "render": cmd_render}[args.cmd](args)
    except (RegistryError, CompileError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
