"""approach_script_autoload.py — POST batch script pass-lint tới CRM (phase 05).

Luồng tự động không ghi approach_out/{cid}.json chờ tay người — gọi thẳng
CRM (POST /admin/approach-scripts/load) để CRM tự ghi vào CRM_APPROACH_SCRIPT_DIR.
Auth dùng chung CRM_REFRESH_TOKEN với /admin/refresh.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def post_batch(url: str, items: list[dict], timeout: int) -> dict | None:
    """POST batch tới CRM /admin/approach-scripts/load. None nếu unreachable/lỗi
    (không raise — auto-gen là fire-and-forget, xem orchestration asset)."""
    body = json.dumps(items).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("CRM_REFRESH_TOKEN", "")
    if token:
        headers["X-Refresh-Token"] = token
    request = urllib.request.Request(url, method="POST", data=body, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        print(f"    auto-load FAIL (HTTP {exc.code}): {detail[:500]}")
        return None
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"    auto-load FAIL (unreachable): {exc}")
        return None
