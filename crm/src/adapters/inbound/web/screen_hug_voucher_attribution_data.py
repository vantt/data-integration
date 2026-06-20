"""screen_hug_voucher_attribution_data.py — data helpers for the voucher attribution screen.

No FastAPI dependency — only stdlib + hug domain modules.  Split from the router
so the business logic can be unit-tested without the HTTP framework.

Exported:
  load_attribution(conn)  -> list[dict] sorted by issued desc
"""
from __future__ import annotations

import sqlite3

from hug.voucher_repository import attribution_rows


def load_attribution(conn: sqlite3.Connection) -> list[dict]:
    """Return all rows from v_hug_voucher_attribution, sorted by issued desc.

    Columns: campaign_id, code, issued, redeemed, redeem_rate_pct.
    """
    rows = attribution_rows(conn)
    result = [dict(r) for r in rows]
    result.sort(key=lambda r: r.get("issued", 0), reverse=True)
    return result
