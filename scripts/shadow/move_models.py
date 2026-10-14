"""Move dbt models into module folders: models/<module>/<layer>/...

  python3 scripts/shadow/move_models.py --manifest <manifest.json> --buckets core,cdm,connector:*,pack:* [--dry-run]

The module comes from scripts/checks/model_buckets.yaml; the layer (staging, intermediate,
marts) is the model's current top folder and is kept, because dbt_project.yml configures
schema, materialization and tags per layer. So a move changes the file path and fqn only:
relation, schema and tags stay identical (verified by scripts/shadow/gate.sh).

A model already in a module folder (models/<module>/<layer>/...) whose bucket changed moves to
models/<new module>/<layer>/... with the rest of its path kept (e.g. core/marts/sales/x.sql ->
packs/finance/marts/sales/x.sql).

For each moved model the script:
  - `git mv`s the .sql file,
  - cuts the model's block out of its properties YAML (text based, comments preserved) and
    appends it to `_<module>__models.yml` in the new directory,
and moves each dbt source block of a moved bucket (SOURCE_OWNER) from models/sources.yml to
models/<module>/staging/_sources.yml; models/sources.yml is removed once empty.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from collections import defaultdict

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRANSFORMATION = os.path.join(ROOT, "transformation")
# dbt source -> bucket that owns it (the module whose staging models read it)
SOURCE_OWNER = {
    "sapo_v2_raw": "connector:sapo_v2", "gsheet_raw": "connector:gsheet", "shopee_raw": "connector:shopee",
    "misa_raw": "connector:misa", "hug_raw": "connector:hug", "crm_export": "pack:crm",
}
MODULE_ROOTS = {"core": 1, "cdm": 1, "monitoring": 1, "connectors": 2, "packs": 2, "tenants": 2}
STAGING_SUBFOLDERS_TO_DROP = {"standard", "facebook_ads", "facebook_messenger"}


def module_dir(bucket: str) -> str | None:
    if bucket in ("core", "cdm"):
        return bucket
    kind, _, name = bucket.partition(":")
    return {"connector": f"connectors/{name}", "pack": f"packs/{name}", "tenant": f"tenants/{name}"}.get(kind)


def target_path(path: str, bucket: str) -> str:
    """models/<layer>/<rest...> or models/<old module>/<layer>/<rest...> -> models/<module>/<layer>/<rest...>"""
    parts = path.split("/")
    assert parts[0] == "models", path
    mod = module_dir(bucket)
    depth = MODULE_ROOTS.get(parts[1])
    if depth and mod is not None:                # already in a module folder: swap the module only
        layer_and_rest = parts[1 + depth:]
        if layer_and_rest and layer_and_rest[0] in ("staging", "intermediate", "marts"):
            return "/".join(["models", *mod.split("/"), *layer_and_rest])
        return path
    layer, rest = parts[1], parts[2:]
    if mod is None or layer not in ("staging", "intermediate", "marts"):
        return path
    if layer == "staging" and len(rest) > 1 and rest[0] in STAGING_SUBFOLDERS_TO_DROP:
        rest = rest[1:]
    if layer == "marts" and len(rest) > 1:
        if bucket == "core" and rest[0] == "core":
            rest = rest[1:]                      # marts/core/x -> core/marts/x
        elif bucket.startswith(("pack:", "tenant:")):
            rest = rest[1:]                      # marts/finance/x -> packs/finance/marts/x
    return "/".join(["models", *mod.split("/"), layer, *rest])


# ---------------------------------------------------------------- YAML block surgery
def split_models_blocks(text: str) -> tuple[list[str], dict[str, list[str]], list[str]]:
    """Return (head lines incl. `models:` key, {model: block lines}, tail lines after models)."""
    lines = text.splitlines(keepends=True)
    head, blocks, tail = [], {}, []
    i, n = 0, len(lines)
    while i < n and not lines[i].startswith("models:"):
        head.append(lines[i]); i += 1
    if i == n:
        return head, {}, []
    head.append(lines[i]); i += 1
    pending: list[str] = []
    current = None
    while i < n:
        line = lines[i]
        if re.match(r"^[A-Za-z_]", line):           # next top-level key
            tail = pending + lines[i:]
            pending = []
            break
        m = re.match(r"^  - name:\s*(\S+)", line)
        if m:
            current = m.group(1).strip("'\"")
            blocks[current] = pending + [line]
            pending = []
        elif current is None or line.strip() == "" or line.lstrip().startswith("#") and line.startswith("  #"):
            pending.append(line)                    # comments/blanks belong to the next block
        else:
            blocks[current].extend(pending + [line]); pending = []
        i += 1
    if pending and current:
        blocks[current].extend(pending)
    return head, blocks, tail


def append_blocks(path: str, block_lines: list[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w") as fh:
            fh.write("version: 2\n\nmodels:\n")
    if block_lines and not block_lines[-1].endswith("\n"):
        block_lines = block_lines[:-1] + [block_lines[-1] + "\n"]  # source file had no final newline
    if block_lines and block_lines[-1].strip():
        # keep a blank line after each block: a folded scalar (`>`) that ends the file
        # otherwise loses its trailing newline, which changes the parsed description
        block_lines = block_lines + ["\n"]
    with open(path, "a") as fh:
        fh.writelines(block_lines)


def git_mv(src: str, dst: str, dry: bool) -> None:
    print(f"mv {os.path.relpath(src, ROOT)} -> {os.path.relpath(dst, ROOT)}")
    if not dry:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        subprocess.run(["git", "mv", src, dst], cwd=ROOT, check=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--manifest", required=True)
    p.add_argument("--buckets", required=True, help="comma-separated bucket patterns, e.g. core,cdm,connector:*,pack:*")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    patterns = args.buckets.split(",")

    buckets = yaml.safe_load(open(os.path.join(ROOT, "scripts", "checks", "model_buckets.yaml")))["buckets"]
    manifest = json.load(open(args.manifest))
    nodes = list(manifest["nodes"].values()) + [v[0] for v in manifest.get("disabled", {}).values()]
    models = {n["name"]: n for n in nodes if n["resource_type"] == "model"}

    moves: dict[str, tuple[str, str]] = {}
    for name, n in sorted(models.items()):
        bucket = buckets[name]
        if not any(fnmatch.fnmatch(bucket, pat) for pat in patterns):
            continue
        src = n["original_file_path"]
        dst = target_path(src, bucket)
        if dst != src:
            moves[name] = (src, dst)

    # properties YAML: collect blocks of moved models per source yml
    by_yml: dict[str, list[str]] = defaultdict(list)
    for name, (src, _) in moves.items():
        patch = models[name].get("patch_path")
        if patch:
            by_yml[patch.split("://", 1)[1]].append(name)

    for name, (src, dst) in moves.items():
        git_mv(os.path.join(TRANSFORMATION, src), os.path.join(TRANSFORMATION, dst), args.dry_run)

    for yml_rel, names in sorted(by_yml.items()):
        yml = os.path.join(TRANSFORMATION, yml_rel)
        head, blocks, tail = split_models_blocks(open(yml).read())
        missing = [nm for nm in names if nm not in blocks]
        if missing:
            sys.exit(f"{yml_rel}: blocks not found for {missing}")
        for nm in names:
            new_dir = os.path.dirname(os.path.join(TRANSFORMATION, moves[nm][1]))
            module = module_dir(buckets[nm]).split("/")[-1]
            target = os.path.join(new_dir, f"_{module}__models.yml")
            print(f"yml {yml_rel}: {nm} -> {os.path.relpath(target, ROOT)}")
            if not args.dry_run:
                append_blocks(target, blocks.pop(nm))
        if args.dry_run:
            continue
        remaining = [line for b in blocks.values() for line in b]
        # the head may hold other top-level keys (e.g. a `seeds:` block before `models:`)
        head_content = [l for l in head if l.strip() and not l.lstrip().startswith("#")
                        and not l.startswith(("version:", "models:"))]
        if remaining or head_content or [l for l in tail if l.strip()]:
            with open(yml, "w") as fh:
                fh.writelines(head + remaining + tail)
        else:
            subprocess.run(["git", "rm", "-q", yml], cwd=ROOT, check=True)
            print(f"rm {yml_rel} (empty)")

    # dbt sources owned by moved buckets
    src_yml = os.path.join(TRANSFORMATION, "models", "sources.yml")
    owners = {s: b for s, b in SOURCE_OWNER.items() if any(fnmatch.fnmatch(b, pat) for pat in patterns)}
    if os.path.exists(src_yml) and owners:
        text = open(src_yml).read().replace("\nsources:\n", "\nmodels:\n", 1)  # reuse block splitter
        head, blocks, tail = split_models_blocks(text)
        for source, bucket in owners.items():
            if source in blocks:
                target = os.path.join(TRANSFORMATION, "models", *module_dir(bucket).split("/"), "staging", "_sources.yml")
                print(f"source {source} -> {os.path.relpath(target, ROOT)}")
                if not args.dry_run:
                    if os.path.exists(target):
                        sys.exit(f"{os.path.relpath(target, ROOT)} already exists; merge the {source} block by hand")
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with open(target, "w") as fh:
                        fh.write("version: 2\n\nsources:\n")
                        fh.writelines(blocks.pop(source))
        if not args.dry_run:
            remaining = [line for b in blocks.values() for line in b]
            if remaining or [l for l in tail if l.strip()]:
                with open(src_yml, "w") as fh:
                    fh.write("".join(head).replace("\nmodels:\n", "\nsources:\n", 1) + "".join(remaining + tail))
            else:
                subprocess.run(["git", "rm", "-q", src_yml], cwd=ROOT, check=True)
                print("rm models/sources.yml (empty)")
    print(f"{len(moves)} model(s) {'would move' if args.dry_run else 'moved'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
