"""screen_hug_voucher_attribution_html.py — pure HTML rendering for voucher attribution.

No FastAPI dependency — only stdlib.  Split from the router so rendering helpers
can be unit-tested without the HTTP framework (same pattern as screen_hug_review_html.py).

Exported:
  render_attribution_page(rows)  -> full page HTML for GET /hug/vouchers
"""
from __future__ import annotations

import html

from adapters.inbound.web.screens.hug.screen_hug_mint_html import _COMMON_CSS


def render_attribution_page(rows: list[dict]) -> str:
    """Render the full /hug/vouchers attribution page.

    Args:
        rows: dicts with keys campaign_id, code, issued, redeemed, redeem_rate_pct.
              Expected to be pre-sorted by issued desc.
    """
    body = _render_body(rows)
    return f"""<!doctype html>
<html lang="vi" data-surface="HUG-VOUCHERS">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hug · Phát hành voucher</title>
<style>
{_COMMON_CSS}
  body {{ align-items: flex-start; padding: 24px 16px; }}
  .card {{ width: min(800px, 98vw); }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px; }}
  th {{ text-align: left; padding: 8px 12px; font-size: 12px; text-transform: uppercase;
       letter-spacing: .6px; color: #94a3b8; border-bottom: 1px solid #334155; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #1e293b; vertical-align: middle; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  code {{ font-family: ui-monospace, monospace; font-size: 12px; color: #38bdf8; }}
  .rate-hi {{ color: #34d399; font-weight: 600; }}
  .rate-mid {{ color: #fbbf24; font-weight: 600; }}
  .rate-lo {{ color: #94a3b8; }}
  .empty {{ text-align: center; color: #64748b; padding: 40px 0; }}
  .hint {{ margin-top: 18px; font-size: 12px; color: #64748b; text-align: center; }}
  a.batch-link {{ color: #38bdf8; font-size: 13px; text-decoration: none; }}
  a.batch-link:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
  <main class="card">
    <h1>Hug &middot; Phát hành voucher</h1>
    <p class="sub">Thống kê phát hành và đổi mã ưu đãi theo chiến dịch.</p>
    {body}
    <p class="hint">
      <a class="batch-link" href="/hug/campaigns">&larr; Chiến dịch</a>
      &nbsp;·&nbsp;
      <a class="batch-link" href="/hug/review">Hàng chờ CS &rarr;</a>
    </p>
  </main>
</body>
</html>"""


# ── Private helpers ────────────────────────────────────────────────────────────

def _render_body(rows: list[dict]) -> str:
    if not rows:
        return (
            '<div class="empty">'
            '<div style="font-size:40px;margin-bottom:12px">&#128230;</div>'
            '<strong>Chưa phát hành voucher nào.</strong>'
            '<br><span style="font-size:13px">'
            'Hệ thống sẽ cập nhật khi có đơn opt-in và voucher được tạo.</span>'
            '</div>'
        )

    rows_html = "\n".join(_render_row(r) for r in rows)
    return f"""<table>
      <thead>
        <tr>
          <th>Chiến dịch</th>
          <th>Mã</th>
          <th style="text-align:right">Đã phát</th>
          <th style="text-align:right">Đã dùng</th>
          <th style="text-align:right">Tỉ lệ dùng %</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>"""


def _render_row(r: dict) -> str:
    campaign_id = html.escape(str(r.get("campaign_id") or "—"))
    code = html.escape(str(r.get("code") or "—"))
    issued = int(r.get("issued") or 0)
    redeemed = int(r.get("redeemed") or 0)
    rate = r.get("redeem_rate_pct")

    if rate is None:
        rate_html = '<span class="rate-lo">—</span>'
    else:
        rate_val = float(rate)
        if rate_val >= 50:
            cls = "rate-hi"
        elif rate_val >= 20:
            cls = "rate-mid"
        else:
            cls = "rate-lo"
        rate_html = f'<span class="{cls}">{rate_val:.1f}%</span>'

    return (
        f"<tr>"
        f"<td><code>{campaign_id}</code></td>"
        f"<td><code>{code}</code></td>"
        f'<td class="num">{issued}</td>'
        f'<td class="num">{redeemed}</td>'
        f'<td class="num">{rate_html}</td>'
        f"</tr>"
    )
