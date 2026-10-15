"""Regenerate golden SQL after an intended compiler change: python3 -m analytics.tests.regen_golden

Review the diff before committing: every changed file is a changed query.
"""
from __future__ import annotations

from analytics.compiler.loader import load_profile, load_registry, profile_path
from analytics.compiler.sql import AsOf, Compiler, window

from .golden_cases import AS_OF, CASES, GOLDEN_DIR, golden_path


def render(metric: str, window_name: str, runtime: bool) -> str:
    profile = load_profile(profile_path("fine_japan"))
    as_of = AsOf.runtime(profile["locale"]["timezone"]) if runtime else AsOf.literal(AS_OF)
    compiler = Compiler(load_registry(), profile)
    return f"SELECT\n  {compiler.total(metric, window(window_name, as_of), as_of)} AS {metric}\n"


def main() -> None:
    GOLDEN_DIR.mkdir(exist_ok=True)
    wanted = set()
    for metric, window_name, runtime in CASES:
        path = golden_path(metric, window_name, runtime)
        wanted.add(path)
        path.write_text(render(metric, window_name, runtime), encoding="utf-8")
    for stale in GOLDEN_DIR.glob("*.sql"):
        if stale not in wanted:
            stale.unlink()
    print(f"wrote {len(wanted)} golden files to {GOLDEN_DIR}")


if __name__ == "__main__":
    main()
