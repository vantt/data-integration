"""Larksuite Custom Bot client with log-stub fallback.

Sends interactive card messages to a Lark chat group via Custom Bot webhook.
When LARK_ALERT_WEBHOOK env var is unset, gracefully degrades to stdlib logging
so the caller code works identically regardless of Lark setup state.

See plans/260408-1611-fix-serving-db-hang-metabase-lock/plan.md Phase 3.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import time
from typing import Optional

try:
    import requests
except ImportError:  # requests should be available via dagster deps; safe fallback
    requests = None  # type: ignore

logger = logging.getLogger("orchestration.lark")


def _sign(secret: str, timestamp: int) -> str:
    """Lark signature: base64(HMAC-SHA256(timestamp + '\\n' + secret, ''))."""
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(
        string_to_sign.encode("utf-8"), b"", digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def _log_stub(title: str, fields: dict, color: str) -> bool:
    """Fallback: print alert to stdlib logger when no webhook is configured."""
    body = " | ".join(f"{k}={v}" for k, v in fields.items())
    logger.warning(f"[LARK-STUB][{color.upper()}] {title} :: {body}")
    return True


def send_lark_card(
    title: str,
    fields: dict,
    color: str = "red",
    webhook: Optional[str] = None,
    secret: Optional[str] = None,
) -> bool:
    """Send an interactive card to Lark group via Custom Bot webhook.

    Args:
        title: Card header title.
        fields: Key-value pairs rendered as card body rows.
        color: Header theme (red|orange|yellow|green|blue|grey).
        webhook: Override env LARK_ALERT_WEBHOOK.
        secret: Override env LARK_ALERT_SECRET (signature verification).

    Returns:
        True if delivered (or log-stubbed) successfully, False on network error.
    """
    webhook = webhook or os.getenv("LARK_ALERT_WEBHOOK")
    secret = secret or os.getenv("LARK_ALERT_SECRET")

    # Stub path — no webhook configured, just log
    if not webhook:
        return _log_stub(title, fields, color)

    # requests missing — degrade to stub with a notice
    if requests is None:
        logger.error("requests lib unavailable; falling back to log stub")
        return _log_stub(title, fields, color)

    body_elements = [
        {
            "tag": "div",
            "fields": [
                {
                    "is_short": False,
                    "text": {"tag": "lark_md", "content": f"**{k}:** {v}"},
                }
                for k, v in fields.items()
            ],
        }
    ]
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": color,
            },
            "elements": body_elements,
        },
    }

    if secret:
        ts = int(time.time())
        payload["timestamp"] = str(ts)
        payload["sign"] = _sign(secret, ts)

    try:
        resp = requests.post(webhook, json=payload, timeout=5)
        ok = resp.status_code == 200 and resp.json().get("code", 0) == 0
        if not ok:
            logger.error(f"Lark webhook returned non-OK: {resp.status_code} {resp.text[:200]}")
        return ok
    except Exception as e:
        logger.error(f"Lark webhook send failed: {e}")
        return False
