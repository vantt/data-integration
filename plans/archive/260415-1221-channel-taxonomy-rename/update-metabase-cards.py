"""Update Metabase cards to use new channel taxonomy naming.

Replacements applied to native SQL (both legacy `query` field and Lib format `native`):
    platform_group     -> channel_format
    'Ecom'             -> 'Marketplace'
    'Ecommerce'        -> 'Online-Ecommerce'
    "Ecommerce"        -> "Online-Ecommerce"

Safe to run multiple times (idempotent — second run replaces 0).
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

URL = os.environ.get("METABASE_URL", "http://127.0.0.1:3000").rstrip("/")
KEY = os.environ["METABASE_API_KEY"]


def api(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"{URL}{path}",
        method=method,
        headers={"x-api-key": KEY, "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body else None,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read()) if resp.status != 204 else {}


REPLACEMENTS = [
    (re.compile(r"\bplatform_group\b"), "channel_format"),
    (re.compile(r"'Ecommerce'"), "'Online-Ecommerce'"),
    (re.compile(r'"Ecommerce"'), '"Online-Ecommerce"'),
    (re.compile(r"'Ecom'"), "'Marketplace'"),
]


def apply_text(text: str) -> tuple[str, int]:
    if not text:
        return text, 0
    count = 0
    for pat, repl in REPLACEMENTS:
        text, n = pat.subn(repl, text)
        count += n
    return text, count


def patch_query(dq: dict) -> tuple[dict, int]:
    """Return (new_dq, change_count). Supports legacy `native.query` and Lib `stages`."""
    total = 0
    # Legacy format: {"type":"native", "native": {"query": "..."}}
    native = dq.get("native")
    if isinstance(native, dict) and "query" in native:
        new_q, n = apply_text(native["query"])
        if n:
            native["query"] = new_q
            total += n
    # Lib format: {"stages": [{"lib/type": "mbql.stage/native", "native": "..."}]}
    for stage in dq.get("stages", []) or []:
        q = stage.get("native")
        if isinstance(q, str):
            new_q, n = apply_text(q)
            if n:
                stage["native"] = new_q
                total += n
    return dq, total


def main():
    ids: list[int] = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else []
    if not ids:
        print("Usage: update-metabase-cards.py <id1> <id2> ...", file=sys.stderr)
        sys.exit(1)

    log = Path(__file__).with_name("metabase-update-log.txt")
    with log.open("w", encoding="utf-8") as f:
        for cid in ids:
            try:
                card = api("GET", f"/api/card/{cid}")
                dq = card.get("dataset_query") or {}
                new_dq, n = patch_query(dq)
                # Also patch visualization_settings (series colors keyed by value)
                vs = card.get("visualization_settings") or {}
                vs_json = json.dumps(vs)
                new_vs_json, nvs = apply_text(vs_json)
                payload = {}
                if n:
                    payload["dataset_query"] = new_dq
                if nvs:
                    payload["visualization_settings"] = json.loads(new_vs_json)
                if not payload:
                    msg = f"#{cid} {card.get('name','?')}: no changes"
                    print(msg); f.write(msg + "\n")
                    continue
                api("PUT", f"/api/card/{cid}", payload)
                msg = f"#{cid} {card.get('name','?')}: SQL={n} viz={nvs} replacement(s)"
                print(msg); f.write(msg + "\n")
            except Exception as e:
                msg = f"#{cid} ERROR: {e}"
                print(msg, file=sys.stderr); f.write(msg + "\n")


if __name__ == "__main__":
    main()
