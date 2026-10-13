"""Dagster inventory: prove a refactor kept the orchestration wiring identical.

  export --manifest transformation/target/manifest.json --out dagster.json
  diff A.json B.json [--allow-new]

Loads `orchestration.definitions.defs` (run inside the shadow container) and records:
asset keys with group, asset check keys, every job with its selected asset keys and the
dbt unique_ids those keys resolve to, schedules (cron, job, timezone, default status),
sensors (targets, default status, interval) and the resolved SLA for every SLA asset key.

A job whose dbt selection resolves to a different set of unique_ids, or to nothing, is a
difference: dagster-dbt turns selected keys into a dbt `--select`, so an empty or shifted
set means the job silently builds the wrong models.
"""
from __future__ import annotations

import argparse
import json
import sys


def _key(k) -> str:
    return "/".join(k.path)


def cmd_export(args: argparse.Namespace) -> int:
    from orchestration.asset_checks import sla_loader
    from orchestration.assets.dbt import SapoDbtTranslator
    from orchestration.definitions import defs

    repo = defs.get_repository_def()
    graph = repo.asset_graph

    manifest = json.load(open(args.manifest))
    translator = SapoDbtTranslator()
    key_to_uid = {}
    for uid, node in {**manifest["nodes"], **manifest.get("sources", {})}.items():
        if node["resource_type"] in {"model", "seed", "snapshot", "source"}:
            try:
                key_to_uid[_key(translator.get_asset_key(node))] = uid
            except Exception:  # sources without a mapping keep their default key
                continue

    assets = {}
    for k in sorted(graph.get_all_asset_keys(), key=_key):
        node = graph.get(k)
        assets[_key(k)] = {"group": node.group_name, "dbt_unique_id": key_to_uid.get(_key(k))}

    jobs = {}
    for job in sorted(repo.get_all_jobs(), key=lambda j: j.name):
        if job.name.startswith("__"):
            continue
        selected = sorted(_key(k) for k in job.asset_layer.selected_asset_keys)
        dbt_uids = sorted(u for u in (key_to_uid.get(k) for k in selected) if u and not u.startswith("source."))
        jobs[job.name] = {"assets": selected, "dbt_unique_ids": dbt_uids, "tags": dict(sorted((job.tags or {}).items()))}

    schedules = {
        s.name: {
            "cron": s.cron_schedule if isinstance(s.cron_schedule, str) else list(s.cron_schedule),
            "job": s.job_name,
            "timezone": s.execution_timezone,
            "default_status": str(s.default_status),
        }
        for s in sorted(repo.schedule_defs, key=lambda s: s.name)
    }
    sensors = {}
    for s in sorted(repo.sensor_defs, key=lambda s: s.name):
        try:
            targets = sorted(t.job_name for t in s.targets)
        except Exception:
            targets = []
        sensors[s.name] = {"targets": targets, "default_status": str(s.default_status),
                           "minimum_interval_seconds": s.minimum_interval_seconds}

    doc = {
        "assets": assets,
        "asset_checks": sorted(f"{_key(c.asset_key)}:{c.name}" for c in graph.asset_check_keys),
        "jobs": jobs,
        "schedules": schedules,
        "sensors": sensors,
        "sla": {k: sla_loader.get_sla(k) for k in sorted(sla_loader.list_asset_keys())},
    }
    json.dump(doc, open(args.out, "w"), indent=1, sort_keys=True, default=str)
    empty = [j for j, v in jobs.items() if any(a in key_to_uid for a in v["assets"]) and not v["dbt_unique_ids"]]
    print(f"wrote {args.out}: {len(assets)} assets, {len(doc['asset_checks'])} checks, {len(jobs)} jobs, "
          f"{len(schedules)} schedules, {len(sensors)} sensors")
    return 1 if empty else 0


def cmd_diff(args: argparse.Namespace) -> int:
    a, b = json.load(open(args.a)), json.load(open(args.b))
    problems, info = [], []
    for section in ("assets", "jobs", "schedules", "sensors", "sla"):
        sa, sb = a.get(section, {}), b.get(section, {})
        for name in sorted(set(sa) - set(sb)):
            problems.append(f"{section}.{name}: removed")
        for name in sorted(set(sb) - set(sa)):
            (info if args.allow_new else problems).append(f"{section}.{name}: added")
        for name in sorted(set(sa) & set(sb)):
            if sa[name] == sb[name]:
                continue
            if section == "jobs" and args.allow_new:
                xa, xb = sa[name], sb[name]
                grown = set(xa["assets"]) <= set(xb["assets"]) and set(xa["dbt_unique_ids"]) <= set(xb["dbt_unique_ids"])
                if grown and xa["tags"] == xb["tags"]:
                    info.append(f"jobs.{name}: selection grew by {sorted(set(xb['assets']) - set(xa['assets']))}")
                    continue
            problems.append(f"{section}.{name}: {sa[name]} -> {sb[name]}")
    ca, cb = set(a["asset_checks"]), set(b["asset_checks"])
    problems += [f"asset_check removed: {c}" for c in sorted(ca - cb)]
    (info if args.allow_new else problems).extend(f"asset_check added: {c}" for c in sorted(cb - ca))
    for m in info:
        print("INFO", m)
    for m in problems:
        print("DIFF", m)
    print(f"dagster inventory: {len(problems)} difference(s), {len(info)} info")
    return 1 if problems else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("export"); s.add_argument("--manifest", required=True); s.add_argument("--out", required=True)
    s = sub.add_parser("diff"); s.add_argument("a"); s.add_argument("b"); s.add_argument("--allow-new", action="store_true")
    args = p.parse_args()
    return cmd_export(args) if args.cmd == "export" else cmd_diff(args)


if __name__ == "__main__":
    sys.exit(main())
