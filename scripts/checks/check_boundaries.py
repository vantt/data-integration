"""Module boundary check for the data platform (stdlib + dbt manifest, no extra deps).

  python3 scripts/checks/check_boundaries.py --manifest <manifest.json> [--write-allowlist]

Run it from a full checkout (host), not inside the data_platform container: crm/ and
detailView/ are not mounted there and a missing tree is reported as a violation.

Rules (design: docs/architecture/modules.md §2b, §3 and §12):

  py-import       crm/ and detailView/ must not import orchestration, ingestion or
                  transformation; ingestion/ must not import orchestration.
  dbt-bucket      every dbt model (enabled or disabled) has a bucket in model_buckets.yaml.
  dbt-path        a model's file lives under models/<module folder of its bucket>/.
  dbt-ref         a model may only depend on models allowed by the bucket matrix below.
  dbt-source      only connector:* and tenant:* models read dbt sources.
  seed-duplicate  no two seed CSVs under transformation/seeds/ share a basename (dbt would
                  fail to parse and the container would not start).
  connector-url   no hard-coded http(s) URL in orchestration/connectors/** (tenant values
                  belong in tenant config).

Matrix (row = model's bucket, may depend on):
  connector:<x>   connector:<x>, seeds
  cdm             connector:*, cdm, seeds
  core            cdm, core, seeds
  pack:<p>        cdm, core, pack:<p>, connectors declared in pack_connectors
  tenant:<t>      anything
  monitoring      anything

Known violations live in boundary_allowlist.yaml with a reason; the check fails only on
violations that are not allowlisted, and reports allowlist entries that no longer occur.
`--write-allowlist` rewrites the allowlist from the current violations, keeping reasons.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from collections import defaultdict

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BUCKETS_FILE = os.path.join(HERE, "model_buckets.yaml")
ALLOWLIST_FILE = os.path.join(HERE, "boundary_allowlist.yaml")

PY_RULES = [
    ("crm", {"orchestration", "ingestion", "transformation"}),
    ("detailView", {"orchestration", "ingestion", "transformation"}),
    ("ingestion", {"orchestration"}),
]
URL_RE = re.compile(r"https?://[^\s'\"]+")


# ------------------------------------------------------------------ python imports
def python_violations() -> list[tuple[str, str, str]]:
    out = []
    for top, forbidden in PY_RULES:
        base = os.path.join(ROOT, top)
        if not os.path.isdir(base):
            # A missing tree must not pass silently (e.g. running inside a container that
            # does not mount crm/). Run this check from a full checkout.
            out.append(("py-scan", top, "directory not found"))
            continue
        for dirpath, dirnames, files in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in {"venv", ".venv", "node_modules", "__pycache__"}]
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(dirpath, f)
                rel = os.path.relpath(path, ROOT)
                try:
                    tree = ast.parse(open(path, encoding="utf-8").read(), filename=rel)
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    names = []
                    if isinstance(node, ast.Import):
                        names = [a.name for a in node.names]
                    elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                        names = [node.module]
                    for name in names:
                        if name.split(".")[0] in forbidden:
                            out.append(("py-import", rel, name))
    return out


# ------------------------------------------------------------------ dbt
def _allowed(src_bucket: str, dst_bucket: str, pack_connectors: dict) -> bool:
    if src_bucket.startswith("tenant:") or src_bucket == "monitoring":
        return True
    if src_bucket.startswith("connector:"):
        return dst_bucket == src_bucket
    if src_bucket == "cdm":
        return dst_bucket == "cdm" or dst_bucket.startswith("connector:")
    if src_bucket == "core":
        return dst_bucket in {"cdm", "core"}
    if src_bucket.startswith("pack:"):
        pack = src_bucket.split(":", 1)[1]
        declared = {f"connector:{c}" for c in pack_connectors.get(pack, [])}
        return dst_bucket in {"cdm", "core", src_bucket} | declared
    return False


def _module_dir(bucket: str) -> str | None:
    if bucket in ("core", "cdm", "monitoring"):
        return bucket
    kind, _, name = bucket.partition(":")
    return {"connector": f"connectors/{name}", "pack": f"packs/{name}", "tenant": f"tenants/{name}"}.get(kind)


def dbt_violations(manifest: dict, spec: dict) -> list[tuple[str, str, str]]:
    buckets: dict = spec["buckets"]
    pack_connectors = spec.get("pack_connectors", {})
    out = []
    nodes = dict(manifest["nodes"])
    for uid, versions in manifest.get("disabled", {}).items():
        nodes.setdefault(uid, versions[0])
    models = {uid: n for uid, n in nodes.items() if n["resource_type"] == "model"}
    for uid, n in sorted(models.items()):
        name = n["name"]
        if name not in buckets:
            out.append(("dbt-bucket", name, "no bucket in model_buckets.yaml"))
            continue
        src_b = buckets[name]
        expected = _module_dir(src_b)
        path = n.get("original_file_path", "")
        if expected and not path.startswith(f"models/{expected}/"):
            out.append(("dbt-path", name, f"{path} not under models/{expected}/"))
        for dep in n.get("depends_on", {}).get("nodes", []):
            kind, dep_name = dep.split(".")[0], dep.split(".")[-1]
            if kind == "source":
                if not (src_b.startswith("connector:") or src_b.startswith("tenant:")):
                    out.append(("dbt-source", name, dep.split(".", 2)[-1]))
            elif kind == "model":
                dst_b = buckets.get(dep_name)
                if dst_b and not _allowed(src_b, dst_b, pack_connectors):
                    out.append(("dbt-ref", name, f"{dep_name} [{src_b} -> {dst_b}]"))
    return out


# ------------------------------------------------------------------ files
def seed_violations() -> list[tuple[str, str, str]]:
    seen = defaultdict(list)
    for dirpath, _, files in os.walk(os.path.join(ROOT, "transformation", "seeds")):
        for f in files:
            if f.endswith(".csv"):
                seen[f].append(os.path.relpath(os.path.join(dirpath, f), ROOT))
    return [("seed-duplicate", f, ", ".join(sorted(p))) for f, p in sorted(seen.items()) if len(p) > 1]


def url_violations() -> list[tuple[str, str, str]]:
    out = []
    base = os.path.join(ROOT, "orchestration", "connectors")
    for dirpath, _, files in os.walk(base):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(dirpath, f)
                for i, line in enumerate(open(path, encoding="utf-8"), 1):
                    for url in URL_RE.findall(line):
                        out.append(("connector-url", f"{os.path.relpath(path, ROOT)}:{i}", url))
    return out


# ------------------------------------------------------------------ main
def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--manifest", required=True, help="dbt manifest.json (run `dbt parse` first)")
    p.add_argument("--write-allowlist", action="store_true")
    args = p.parse_args()

    spec = yaml.safe_load(open(BUCKETS_FILE))
    manifest = json.load(open(args.manifest))
    found = python_violations() + dbt_violations(manifest, spec) + seed_violations() + url_violations()
    found_keys = {(r, s, t) for r, s, t in found}

    allow = yaml.safe_load(open(ALLOWLIST_FILE)) if os.path.exists(ALLOWLIST_FILE) else {}
    entries = (allow or {}).get("allow", []) or []
    allowed = {(e["rule"], e["subject"], e["target"]): e.get("reason", "") for e in entries}

    if args.write_allowlist:
        doc = {
            "description": "Known boundary violations. Each needs a reason and a planned exit; "
            "check_boundaries.py fails on anything not listed here.",
            "allow": [
                {"rule": r, "subject": s, "target": t,
                 "reason": allowed.get((r, s, t), "TODO: reason and exit plan")}
                for r, s, t in sorted(found_keys)
            ],
        }
        with open(ALLOWLIST_FILE, "w") as fh:
            yaml.safe_dump(doc, fh, sort_keys=False, allow_unicode=True, width=200)
        print(f"wrote {ALLOWLIST_FILE}: {len(found_keys)} entries")
        return 0

    new = sorted(k for k in found_keys if k not in allowed)
    stale = sorted(k for k in allowed if k not in found_keys)
    for r, s, t in new:
        print(f"VIOLATION [{r}] {s} -> {t}")
    for r, s, t in stale:
        print(f"STALE-ALLOW [{r}] {s} -> {t} (no longer occurs; remove from allowlist)")
    by_rule = defaultdict(int)
    for r, _, _ in found_keys:
        by_rule[r] += 1
    print(f"boundaries: {len(found_keys)} known ({dict(sorted(by_rule.items()))}), "
          f"{len(new)} new violation(s), {len(stale)} stale allowlist entr(y/ies)")
    return 1 if new or stale else 0


if __name__ == "__main__":
    sys.exit(main())
