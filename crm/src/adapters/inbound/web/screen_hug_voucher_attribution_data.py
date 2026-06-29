"""screen_hug_voucher_attribution_data.py — data helpers for the voucher attribution screen.

No FastAPI dependency — only stdlib + domain ports.  Split from the router
so the business logic can be unit-tested without the HTTP framework.

Exported:
  load_attribution(port)  -> list[dict] sorted by issued desc
"""
from __future__ import annotations

from domain.ports.hug_ports import HugVoucherPort


def load_attribution(port: HugVoucherPort) -> list[dict]:
    """Return all rows from v_hug_voucher_attribution, sorted by issued desc.

    Columns: campaign_id, code, issued, redeemed, redeem_rate_pct.
    """
    rows = port.attribution_rows()
    result = [dict(r) for r in rows]
    result.sort(key=lambda r: r.get("issued", 0), reverse=True)
    return result
