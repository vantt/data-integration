"""dbt inventory: prove a refactor kept every relation and its configuration.

  export --manifest target/manifest.json --out inventory.json
  diff A.json B.json [--allow-code-change] [--allow-new]

For every model, seed and snapshot the inventory keeps what decides where and how data is
written: relation name, schema, alias, resource type, the full resolved `config` (minus an
explicit ignore list), dependencies, code checksum and the number of attached tests. Paths
(`original_file_path`, `fqn`, ...) are excluded so moving a file is not a difference;
anything that changes a relation, a materialization, a tag used for selection,
`on_schema_change`, seed `column_types`, or a ref is.

`--allow-code-change` reports SQL checksum changes as information (phases that rewrite SQL
prove data equality with the golden snapshot instead) and, with it, a changed `depends_on`
whose every removed dependency is still an ancestor of the node in the new graph (a model
repointed to a pass-through keeps its lineage to the original source; reported as INFO with the
new dependency it now goes through). `--allow-new` accepts added nodes and added dependencies.

  compiled-diff A_manifest.json B_manifest.json [--allow-code-change]

Compares the SQL dbt actually executed (`compiled_code` in the manifest written by
`dbt build`) per model, whitespace-normalized and independent of file paths. Moving files or
replacing an inline CASE with a macro that returns the same SQL must produce no difference.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

RESOURCE_TYPES = {"model", "seed", "snapshot"}
IGNORED_CONFIG_KEYS = {"packages", "docs"}
_TS_SUFFIX = re.compile(r"_\d{14}(?=\.parquet$)")


def _normalize_config(cfg: dict) -> dict:
    out = {k: v for k, v in cfg.items() if k not in IGNORED_CONFIG_KEYS}
    loc = out.get("location")
    if isinstance(loc, str):
        out["location"] = _TS_SUFFIX.sub("_<ts>", loc)
    return out


def cmd_export(args: argparse.Namespace) -> int:
    manifest = json.load(open(args.manifest))
    nodes = manifest["nodes"]
    tests_per_node: dict[str, list[str]] = {}
    for uid, n in nodes.items():
        if n["resource_type"] == "test":
            for dep in n.get("depends_on", {}).get("nodes", []):
                tests_per_node.setdefault(dep, []).append(uid)
    inv = {}
    for uid, n in sorted(nodes.items()):
        if n["resource_type"] not in RESOURCE_TYPES:
            continue
        inv[uid] = {
            "resource_type": n["resource_type"],
            "relation_name": n.get("relation_name"),
            "database": n.get("database"),
            "schema": n.get("schema"),
            "alias": n.get("alias"),
            "config": _normalize_config(n.get("config", {})),
            "depends_on": sorted(n.get("depends_on", {}).get("nodes", [])),
            "checksum": (n.get("checksum") or {}).get("checksum"),
            "tests": sorted(tests_per_node.get(uid, [])),
        }
        # dbt strips trailing whitespace of a properties file, so a block that moves to the
        # end of a file loses the final newline of a folded description: compare stripped.
        inv[uid]["description"] = (n.get("description") or "").strip()
        inv[uid]["columns"] = sorted((n.get("columns") or {}).keys())
    json.dump(inv, open(args.out, "w"), indent=1, sort_keys=True, default=str)
    print(f"wrote {args.out}: {len(inv)} nodes")
    return 0


def _flat(d, prefix=""):
    if isinstance(d, dict):
        for k, v in d.items():
            yield from _flat(v, f"{prefix}.{k}" if prefix else k)
    else:
        yield prefix, d


def _ancestors(inv: dict, uid: str) -> set[str]:
    """All upstream nodes of `uid` in the inventory graph (sources and unknown ids are leaves)."""
    seen: set[str] = set()
    stack = list(inv.get(uid, {}).get("depends_on") or [])
    while stack:
        dep = stack.pop()
        if dep not in seen:
            seen.add(dep)
            stack.extend(inv.get(dep, {}).get("depends_on") or [])
    return seen


def _repoint_info(a: dict, b: dict, uid: str) -> str | None:
    """Describe a dependency change that keeps every removed dependency upstream; None otherwise."""
    old, new = set(a[uid].get("depends_on") or []), set(b[uid].get("depends_on") or [])
    removed, added = old - new, new - old
    upstream = _ancestors(b, uid)
    if not removed or not removed <= upstream:
        return None
    via = {r: sorted(d for d in added if r in _ancestors(b, d)) for r in removed}
    return "; ".join(f"{r} -> via {', '.join(v)}" for r, v in sorted(via.items()))


def cmd_diff(args: argparse.Namespace) -> int:
    a, b = json.load(open(args.a)), json.load(open(args.b))
    problems, info = [], []
    for uid in sorted(set(a) - set(b)):
        problems.append(f"{uid}: removed")
    for uid in sorted(set(b) - set(a)):
        (info if args.allow_new else problems).append(f"{uid}: added")
    for uid in sorted(set(a) & set(b)):
        fa, fb = dict(_flat(a[uid])), dict(_flat(b[uid]))
        for key in sorted(set(fa) | set(fb)):
            if fa.get(key) == fb.get(key):
                continue
            msg = f"{uid}: {key}: {fa.get(key)!r} -> {fb.get(key)!r}"
            if key == "checksum" and args.allow_code_change:
                info.append(msg)
            elif key == "depends_on" and args.allow_new and set(fa.get(key) or []) <= set(fb.get(key) or []):
                info.append(msg)
            elif key == "depends_on" and args.allow_code_change and (via := _repoint_info(a, b, uid)):
                info.append(f"{uid}: repointed dependency kept upstream: {via}")
            else:
                problems.append(msg)
    for m in info:
        print("INFO", m)
    for m in problems:
        print("DIFF", m)
    print(f"dbt inventory: {len(a)} vs {len(b)} nodes, {len(problems)} difference(s), {len(info)} info")
    return 1 if problems else 0


def _norm_sql(code: str) -> str:
    return " ".join((code or "").split())


def cmd_compiled_diff(args: argparse.Namespace) -> int:
    def load(path):
        nodes = json.load(open(path))["nodes"]
        return {uid: _norm_sql(n.get("compiled_code")) for uid, n in nodes.items()
                if n["resource_type"] == "model" and n.get("compiled_code") is not None}
    a, b = load(args.a), load(args.b)
    changed = sorted(u for u in set(a) & set(b) if a[u] != b[u])
    missing = sorted(set(a) - set(b))
    for u in missing:
        print("DIFF", u, "compiled SQL missing in B")
    for u in changed:
        print("INFO" if args.allow_code_change else "DIFF", u, "compiled SQL differs")
    print(f"compiled SQL: {len(a)} vs {len(b)} models, {len(changed)} changed, {len(missing)} missing")
    return 1 if missing or (changed and not args.allow_code_change) else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("export"); s.add_argument("--manifest", required=True); s.add_argument("--out", required=True)
    s = sub.add_parser("diff"); s.add_argument("a"); s.add_argument("b")
    s.add_argument("--allow-code-change", action="store_true"); s.add_argument("--allow-new", action="store_true")
    s = sub.add_parser("compiled-diff"); s.add_argument("a"); s.add_argument("b")
    s.add_argument("--allow-code-change", action="store_true")
    args = p.parse_args()
    return {"export": cmd_export, "diff": cmd_diff, "compiled-diff": cmd_compiled_diff}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
