"""Module boundary check for the data platform (stdlib + dbt manifest, no extra deps).

  python3 scripts/checks/check_boundaries.py --manifest <manifest.json> [--write-allowlist]

Run it from a full checkout (host), not inside the data_platform container: crm/ and
detailView/ are not mounted there and a missing tree is reported as a violation.

Rules (design: docs/architecture/modules.md §2b, §3 and §12):

  py-import       crm/, detailView/ and analytics/ must not import orchestration, ingestion
                  or transformation; ingestion/ must not import orchestration.
  orch-import     orchestration/connectors/<c>/ must not import orchestration.packs; a pack
                  (orchestration/packs/<p>/) must not import another pack. Packs are loaded by
                  the kernel from modules.yaml; a known coupling is allowlisted per file.
  dbt-bucket      every dbt model (enabled or disabled) has a bucket in model_buckets.yaml.
  dbt-path        a model's file lives under models/<module folder of its bucket>/.
  dbt-ref         an enabled model may only depend on models allowed by the bucket matrix below.
                  core -> pack:<p> model <m> is allowed only through pack_ref: the core model's
                  raw SQL calls pack_ref('<p>', '<m>'...), never ref('<m>'), and <m> has a
                  contract for pack <p> in transformation/macros/packs/pack_contracts.sql.
                  Other core -> packs and core -> tenants edges are hooks: allowlist only.
  dbt-source      only connector:* and tenant:* models read dbt sources.
  dbt-seed        a tenant seed (transformation/seeds/tenants/<t>/) is business data: only
                  packs, monitoring and tenant:<t> itself may ref it; core only through
                  tenant_ref('<seed>') (raw SQL calls it literally, no direct ref('<seed>'));
                  cdm and connectors may not.
  tenant-seed-contract
                  every seed core reads through tenant_ref('<seed>') has a core default
                  transformation/seeds/defaults/<seed>__default.csv whose header equals the
                  enabled tenant's seeds/tenants/<tenant>/<seed>.csv header, and a
                  `+column_types` entry for each of its columns in dbt_project.yml
                  (seeds: sapo_warehouse: defaults: <seed>__default:).
  seed-duplicate  no two seed CSVs under transformation/seeds/ share a basename (dbt would
                  fail to parse and the container would not start).
  connector-url   no hard-coded http(s) URL in orchestration/connectors/**, and no domain
                  name in a string literal there (tenant values belong in tenant config:
                  orchestration/tenants/<t>/config.py).
  pack-url        the same for orchestration/packs/**.
  module-config   the pack switch is declared consistently: `packs:` in
                  orchestration/config/modules.yaml == `vars.enabled_packs` in
                  transformation/dbt_project.yml; every folder under transformation/models/packs/
                  has `+enabled` with exactly that default list; pack_ids() in
                  transformation/macros/packs/pack_enabled.sql lists the pack folders;
                  `tenants:` in modules.yaml has at most one id and equals `vars.tenant` ("" for
                  none); `connectors:` in modules.yaml equals `vars.enabled_connectors`. Never allowlisted; the check prints the block to paste.

Disabled models (dbt `config.enabled = false`, e.g. a pack turned off) still need a bucket and
the right folder, but their dependencies are not checked: dbt does not resolve them. Run the check
on the manifest of the default profile (no --vars), where every pack of modules.yaml is enabled;
a manifest built with packs turned off reports their allowlisted edges as stale.

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
MODULES_FILE = os.path.join(ROOT, "orchestration", "config", "modules.yaml")
DBT_PROJECT_FILE = os.path.join(ROOT, "transformation", "dbt_project.yml")
PACK_MODELS_DIR = os.path.join(ROOT, "transformation", "models", "packs")
PACK_MACROS_DIR = os.path.join(ROOT, "transformation", "macros", "packs")
SEEDS_DIR = os.path.join(ROOT, "transformation", "seeds")

PY_RULES = [
    ("crm", {"orchestration", "ingestion", "transformation"}),
    ("detailView", {"orchestration", "ingestion", "transformation"}),
    ("ingestion", {"orchestration"}),
    ("analytics", {"orchestration", "ingestion", "transformation"}),
]
URL_RE = re.compile(r"https?://[^\s'\"]+")
# A host name with a public suffix inside a string literal ("docs.google.com", "x.mysapo.net").
# Module paths ("orchestration.packs.crm") and file names ("seed.csv") do not match.
DOMAIN_RE = re.compile(r"\b(?:[a-z0-9-]+\.)+(?:com|net|org|vn|io|dev|app|cloud|co|xyz|site)\b(?![.\w])", re.I)
ORCH_TREES = (("connectors", "connector-url"), ("packs", "pack-url"))


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


def _imported_modules(tree: ast.AST) -> list[str]:
    """Absolute module names imported by a file; `from a.b import c` yields `a.b.c` too."""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.append(node.module)
            out += [f"{node.module}.{a.name}" for a in node.names]
    return out


def orchestration_violations() -> list[tuple[str, str, str]]:
    """Connector packages must not import packs; a pack must not import another pack."""
    out = []
    for kind in ("connectors", "packs"):
        base = os.path.join(ROOT, "orchestration", kind)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, files in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in {"__pycache__", "__tests__"}]
            rel_dir = os.path.relpath(dirpath, base)
            if rel_dir == ".":
                continue                          # the loader (__init__.py) itself
            own = rel_dir.split(os.sep)[0]
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(dirpath, f)
                rel = os.path.relpath(path, ROOT)
                try:
                    tree = ast.parse(open(path, encoding="utf-8").read(), filename=rel)
                except SyntaxError:
                    continue
                targets = set()
                for name in _imported_modules(tree):
                    parts = name.split(".")
                    if parts[:2] != ["orchestration", "packs"] or len(parts) < 3:
                        continue
                    if kind == "packs" and parts[2] == own:
                        continue
                    targets.add(".".join(parts[:3]))
                out += [("orch-import", rel, t) for t in sorted(targets)]
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


TENANT_SEED_RE = re.compile(r"^seeds/tenants/([^/]+)/")
# pack_ref('<pack>', '<model>' ... — the one accepted spelling (positional, literal ids).
PACK_REF_RE = re.compile(r"""pack_ref\(\s*(['"])(\w+)\1\s*,\s*(['"])(\w+)\3""")
# ref('<model>' not preceded by a word character, so pack_ref( does not count.
DIRECT_REF_RE = re.compile(r"""(?<!\w)ref\(\s*['"](\w+)['"]""")
# tenant_ref('<seed>') — the one accepted spelling.
TENANT_REF_RE = re.compile(r"""tenant_ref\(\s*(['"])(\w+)\1\s*\)""")
# An entry of pack_contracts(): '<model>': {'pack': '<pack>'
CONTRACT_RE = re.compile(r"""['"](\w+)['"]\s*:\s*\{\s*['"]pack['"]\s*:\s*['"](\w+)['"]""")


def pack_contract_models(path: str | None = None) -> dict[str, str]:
    """model -> pack declared in pack_contracts() (transformation/macros/packs/pack_contracts.sql)."""
    path = path or os.path.join(PACK_MACROS_DIR, "pack_contracts.sql")
    if not os.path.exists(path):
        return {}
    source = re.sub(r"\{#.*?#\}", "", open(path, encoding="utf-8").read(), flags=re.S)
    return {m: p for m, p in CONTRACT_RE.findall(source)}


def _pack_ref_allowed(raw_code: str, pack: str, model: str, contracts: dict[str, str]) -> bool:
    """A core -> pack edge is legal only when it comes from pack_ref and the model has a contract."""
    calls = {(m.group(2), m.group(4)) for m in PACK_REF_RE.finditer(raw_code or "")}
    direct = set(DIRECT_REF_RE.findall(raw_code or ""))
    return (pack, model) in calls and model not in direct and contracts.get(model) == pack


def _seed_reader_allowed(src_bucket: str, tenant: str) -> bool:
    """Packs consume tenant data by design; core, cdm and connectors must not depend on it."""
    return (src_bucket.startswith("pack:") or src_bucket == "monitoring"
            or src_bucket == f"tenant:{tenant}")


def _tenant_ref_allowed(raw_code: str, seed: str) -> bool:
    """Core reads a tenant seed only through tenant_ref('<seed>') and never through ref('<seed>')."""
    calls = {m.group(2) for m in TENANT_REF_RE.finditer(raw_code or "")}
    return seed in calls and seed not in set(DIRECT_REF_RE.findall(raw_code or ""))


def _csv_header(path: str) -> list[str] | None:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return [c.strip() for c in fh.readline().strip().split(",")]


def tenant_seed_contract_violations(manifest: dict) -> list[tuple[str, str, str]]:
    """Each seed read through tenant_ref has a typed core default with the tenant seed's header."""
    out = []
    seeds = set()
    for n in manifest["nodes"].values():
        if n["resource_type"] == "model" and _enabled(n):
            seeds |= {m.group(2) for m in TENANT_REF_RE.finditer(n.get("raw_code") or "")}
    tenants = (yaml.safe_load(open(MODULES_FILE)) or {}).get("tenants") or []
    project = yaml.safe_load(open(DBT_PROJECT_FILE)) or {}
    defaults_cfg = (((project.get("seeds") or {}).get(project.get("name", ""), {}) or {}).get("defaults") or {})
    for seed in sorted(seeds):
        default = _csv_header(os.path.join(SEEDS_DIR, "defaults", f"{seed}__default.csv"))
        if default is None:
            out.append(("tenant-seed-contract", seed, f"no seeds/defaults/{seed}__default.csv"))
            continue
        types = ((defaults_cfg.get(f"{seed}__default") or {}).get("+column_types") or {})
        untyped = [c for c in default if c not in types]
        if untyped or set(types) - set(default):
            out.append(("tenant-seed-contract", f"{seed}__default",
                        f"+column_types {sorted(types)} != header {default} (every column needs a type)"))
        for t in tenants:
            header = _csv_header(os.path.join(SEEDS_DIR, "tenants", t, f"{seed}.csv"))
            if header is None:
                out.append(("tenant-seed-contract", seed, f"tenant {t} has no seeds/tenants/{t}/{seed}.csv"))
            elif header != default:
                out.append(("tenant-seed-contract", seed, f"tenant {t} header {header} != default {default}"))
    return out


def _enabled(node: dict) -> bool:
    return (node.get("config") or {}).get("enabled", True) is not False


def dbt_violations(manifest: dict, spec: dict, contracts: dict[str, str] | None = None) -> list[tuple[str, str, str]]:
    buckets: dict = spec["buckets"]
    pack_connectors = spec.get("pack_connectors", {})
    contracts = {} if contracts is None else contracts
    out = []
    nodes = dict(manifest["nodes"])
    disabled = set()
    for uid, versions in manifest.get("disabled", {}).items():
        disabled.add(uid)
        nodes.setdefault(uid, versions[0])
    models = {uid: n for uid, n in nodes.items() if n["resource_type"] == "model"}
    tenant_seeds = {}                                   # seed unique_id -> tenant id
    for uid, n in nodes.items():
        if n["resource_type"] == "seed":
            m = TENANT_SEED_RE.match(n.get("original_file_path", ""))
            if m:
                tenant_seeds[uid] = m.group(1)
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
        if uid in disabled or not _enabled(n):
            continue                                  # not built: dbt does not resolve its refs
        for dep in n.get("depends_on", {}).get("nodes", []):
            kind, dep_name = dep.split(".")[0], dep.split(".")[-1]
            if kind == "source":
                if not (src_b.startswith("connector:") or src_b.startswith("tenant:")):
                    out.append(("dbt-source", name, dep.split(".", 2)[-1]))
            elif kind == "model":
                dst_b = buckets.get(dep_name)
                if (src_b == "core" and dst_b and dst_b.startswith("pack:")
                        and _pack_ref_allowed(n.get("raw_code", ""), dst_b.split(":", 1)[1], dep_name, contracts)):
                    continue
                if dst_b and not _allowed(src_b, dst_b, pack_connectors):
                    out.append(("dbt-ref", name, f"{dep_name} [{src_b} -> {dst_b}]"))
            elif dep in tenant_seeds and src_b == "core" and _tenant_ref_allowed(n.get("raw_code", ""), dep_name):
                continue
            elif dep in tenant_seeds and not _seed_reader_allowed(src_b, tenant_seeds[dep]):
                out.append(("dbt-seed", name, f"{dep_name} [{src_b} -> tenant:{tenant_seeds[dep]}]"))
    return out


# ------------------------------------------------------------------ pack switch
ENABLED_TEMPLATE = "{{{{ ('{pack}' in var('enabled_packs', {default})) | as_bool }}}}"
PACK_IDS_RE = re.compile(r"\{%-?\s*macro\s+pack_ids\(\)\s*-?%\}(.*?)\{%-?\s*endmacro", re.S)


def _yaml_list(ids: list[str]) -> str:
    return "[" + ", ".join(ids) + "]"


def expected_pack_config(modules_packs: list[str], folders: list[str], tenant: str = "",
                         connectors: list[str] | None = None) -> str:
    """The dbt side of the pack switch for `modules_packs`, ready to paste."""
    default = repr(list(modules_packs))
    lines = ["# transformation/dbt_project.yml, under models: sapo_warehouse: packs: <pack>:"]
    lines += [f"      {p}:\n        +enabled: \"{ENABLED_TEMPLATE.format(pack=p, default=default)}\"" for p in folders]
    lines += ["# transformation/dbt_project.yml, under vars:",
              f"  enabled_packs: {_yaml_list(modules_packs)}",
              f"  enabled_connectors: {_yaml_list(connectors or [])}",
              "  tenant: " + (tenant or '""'),
              "# transformation/macros/packs/pack_enabled.sql, macro pack_ids():",
              f"  {{{{ return({repr(list(folders))}) }}}}"]
    return "\n".join(lines)


def module_config_violations() -> tuple[list[tuple[str, str, str]], str]:
    """modules.yaml packs == vars.enabled_packs == every +enabled default; pack_ids() == pack folders."""
    out = []
    modules = (yaml.safe_load(open(MODULES_FILE)) or {}).get("packs") or []
    project = yaml.safe_load(open(DBT_PROJECT_FILE)) or {}
    folders = sorted(d for d in os.listdir(PACK_MODELS_DIR)
                     if os.path.isdir(os.path.join(PACK_MODELS_DIR, d))) if os.path.isdir(PACK_MODELS_DIR) else []
    enabled_var = (project.get("vars") or {}).get("enabled_packs")
    if enabled_var != modules:
        out.append(("module-config", "vars.enabled_packs", f"{enabled_var} != modules.yaml packs {modules}"))
    for p in modules:
        if p not in folders:
            out.append(("module-config", f"modules.yaml packs.{p}", "no folder transformation/models/packs/" + p))
    pack_cfg = (((project.get("models") or {}).get(project.get("name", ""), {}) or {}).get("packs") or {})
    default = repr(list(modules))
    for p in folders:
        got = (pack_cfg.get(p) or {}).get("+enabled")
        if got != ENABLED_TEMPLATE.format(pack=p, default=default):
            out.append(("module-config", f"models.packs.{p}.+enabled",
                        "missing" if got is None else f"{got!r} is not the expected switch"))
    for p in sorted(set(pack_cfg) - set(folders)):
        out.append(("module-config", f"models.packs.{p}", "configured in dbt_project.yml but no folder"))
    connectors = (yaml.safe_load(open(MODULES_FILE)) or {}).get("connectors") or []
    connectors_var = (project.get("vars") or {}).get("enabled_connectors")
    if connectors_var != connectors:
        out.append(("module-config", "vars.enabled_connectors", f"{connectors_var} != modules.yaml connectors {connectors}"))
    tenants = (yaml.safe_load(open(MODULES_FILE)) or {}).get("tenants") or []
    tenant_var = (project.get("vars") or {}).get("tenant")
    if len(tenants) > 1:
        out.append(("module-config", "modules.yaml tenants", f"{tenants}: at most one tenant per deployment"))
    elif tenant_var != (tenants[0] if tenants else ""):
        out.append(("module-config", "vars.tenant", f"{tenant_var!r} != modules.yaml tenants {tenants}"))
    macro_path = os.path.join(PACK_MACROS_DIR, "pack_enabled.sql")
    m = PACK_IDS_RE.search(open(macro_path, encoding="utf-8").read()) if os.path.exists(macro_path) else None
    ids = re.findall(r"['\"](\w+)['\"]", m.group(1)) if m else None
    if ids is None or sorted(ids) != folders:
        out.append(("module-config", "pack_ids()", f"{ids} != pack folders {folders}"))
    return out, (expected_pack_config(modules, folders, tenants[0] if len(tenants) == 1 else "", connectors) if out else "")


# ------------------------------------------------------------------ files
def seed_violations() -> list[tuple[str, str, str]]:
    seen = defaultdict(list)
    for dirpath, _, files in os.walk(os.path.join(ROOT, "transformation", "seeds")):
        for f in files:
            if f.endswith(".csv"):
                seen[f].append(os.path.relpath(os.path.join(dirpath, f), ROOT))
    return [("seed-duplicate", f, ", ".join(sorted(p))) for f, p in sorted(seen.items()) if len(p) > 1]


def _string_literals(source: str) -> list[tuple[int, str]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return [(n.lineno, n.value) for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def url_violations() -> list[tuple[str, str, str]]:
    """http(s) URLs anywhere and domain names in string literals under connectors/ and packs/."""
    out = []
    for tree_name, rule in ORCH_TREES:
        base = os.path.join(ROOT, "orchestration", tree_name)
        for dirpath, dirnames, files in os.walk(base):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(dirpath, f)
                rel = os.path.relpath(path, ROOT)
                source = open(path, encoding="utf-8").read()
                found = set()
                for i, line in enumerate(source.splitlines(), 1):
                    found |= {(i, url) for url in URL_RE.findall(line)}
                for lineno, value in _string_literals(source):
                    if not URL_RE.search(value):
                        found |= {(lineno, d) for d in DOMAIN_RE.findall(value)}
                out += [(rule, f"{rel}:{i}", v) for i, v in sorted(found)]
    return out


# ------------------------------------------------------------------ main
def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--manifest", required=True, help="dbt manifest.json (run `dbt parse` first)")
    p.add_argument("--write-allowlist", action="store_true")
    args = p.parse_args()

    spec = yaml.safe_load(open(BUCKETS_FILE))
    manifest = json.load(open(args.manifest))
    found = (python_violations() + orchestration_violations()
             + dbt_violations(manifest, spec, pack_contract_models())
             + seed_violations() + url_violations())
    config_problems, expected_block = module_config_violations()
    config_problems += tenant_seed_contract_violations(manifest)
    found_keys = {(r, s, t) for r, s, t in found}

    allow = yaml.safe_load(open(ALLOWLIST_FILE)) if os.path.exists(ALLOWLIST_FILE) else {}
    entries = (allow or {}).get("allow", []) or []
    allowed = {(e["rule"], e["subject"], e["target"]): e.get("reason", "") for e in entries}

    if args.write_allowlist:
        doc = {
            "description": "Known boundary violations, generated from the dbt manifest and the "
            "orchestration imports (check_boundaries.py --write-allowlist). Each needs a reason and a "
            "planned exit; check_boundaries.py fails on anything not listed here and on entries that "
            "no longer occur.",
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

    for r, s, t in config_problems:                # never allowlisted
        print(f"VIOLATION [{r}] {s}: {t}")
    if expected_block:
        print("Expected pack switch (from orchestration/config/modules.yaml and the pack folders):")
        print(expected_block)
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
          f"{len(new)} new violation(s), {len(stale)} stale allowlist entr(y/ies), "
          f"{len(config_problems)} module-config/tenant-seed-contract problem(s)")
    return 1 if new or stale or config_problems else 0


if __name__ == "__main__":
    sys.exit(main())
