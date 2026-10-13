"""Snapshot and compare the live on/off state of every Dagster schedule and sensor.

Used by the deploy runbook (docs/operations/deployment.md): capture before stopping
`data_platform`, capture again after it starts, then diff. A rename or a lost toggle shows
up as a difference.

Reads the running webserver's GraphQL API (read-only query). Do NOT use
`dagster schedule list -f ...` for this: the CLI builds its own code location and reports
every instigator as STOPPED even when the webserver runs them (verified 2026-10-13).

Usage (host, stdlib only):
  python3 scripts/checks/instigator_state.py capture --out before.json [--url http://127.0.0.1:3000/graphql]
  python3 scripts/checks/instigator_state.py diff before.json after.json
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request

QUERY = """{ repositoriesOrError { ... on RepositoryConnection { nodes {
  name location { name }
  schedules { name cronSchedule scheduleState { status } }
  sensors { name sensorState { status } } } } } }"""


def capture(url: str) -> dict:
    req = urllib.request.Request(url, data=json.dumps({"query": QUERY}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)["data"]["repositoriesOrError"]["nodes"]
    out = {}
    for repo in data:
        loc = f"{repo['location']['name']}/{repo['name']}"
        for s in repo["schedules"]:
            out[f"{loc}:schedule:{s['name']}"] = f"{s['scheduleState']['status']} {s['cronSchedule']}"
        for s in repo["sensors"]:
            out[f"{loc}:sensor:{s['name']}"] = s["sensorState"]["status"]
    return dict(sorted(out.items()))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capture"); c.add_argument("--out", required=True)
    c.add_argument("--url", default="http://127.0.0.1:3000/graphql")
    d = sub.add_parser("diff"); d.add_argument("a"); d.add_argument("b")
    args = p.parse_args()
    if args.cmd == "capture":
        state = capture(args.url)
        json.dump(state, open(args.out, "w"), indent=1)
        running = sum(1 for v in state.values() if v.startswith("RUNNING"))
        print(f"wrote {args.out}: {len(state)} instigators, {running} running")
        return 0
    a, b = json.load(open(args.a)), json.load(open(args.b))
    diffs = [f"{k}: {a.get(k)} -> {b.get(k)}" for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
    for line in diffs:
        print("DIFF", line)
    print(f"instigator state: {len(diffs)} difference(s)")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
