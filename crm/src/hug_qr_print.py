"""hug_qr_print.py — render a minted batch as printable QR labels (HTML).

Each label shows:
  - a QR encoding  https://{HUG_DOMAIN}/h/{token}
  - the human-readable fallback code  HUG-XXXX-XXXX-XXXX

Output is a single self-contained .html file (A4 grid, print-ready). Open it
and Ctrl-P -> Save as PDF, or print directly to a label sheet.

QR rendering:
  - Primary: the `qrcode` Python lib (SVG, embedded inline — fully offline).
    Install: pip install "qrcode[pil]"  (or just `qrcode` for the SVG factory).
  - Fallback: if `qrcode` is not installed, the page renders QRs in-browser via
    the qrcodejs CDN library, so labels still print from a connected machine.
    A warning is logged so the dependency can be added when going fully offline.

Usage:
    python hug_qr_print.py --batch-id B-20260619-...  [--out labels.html] [--data ./data]
    python hug_qr_print.py --latest                    # most recent batch
"""
from __future__ import annotations

import argparse
import html
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from hug import config as hug_config  # noqa: E402
from hug import db as hug_db  # noqa: E402
from hug import repository  # noqa: E402
from hug.tokens import human_code  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _qr_svg(data: str) -> str | None:
    """Return an inline SVG string for `data`, or None if qrcode unavailable."""
    try:
        import qrcode  # type: ignore
        import qrcode.image.svg  # type: ignore
    except ImportError:
        return None
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(data, image_factory=factory, box_size=10, border=2)
    import io

    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode("utf-8")
    # Strip XML prolog so it embeds cleanly inline; make it responsive.
    svg = svg.replace('<?xml version="1.0" encoding="UTF-8"?>\n', "")
    svg = svg.replace("<svg ", '<svg width="100%" height="100%" ', 1)
    return svg


def _label_html(token: str, url: str, use_server_qr: bool) -> str:
    code = human_code(token)
    if use_server_qr:
        qr = _qr_svg(url) or ""
        qr_block = f'<div class="qr">{qr}</div>'
    else:
        # Client-side render via qrcodejs (data-url attribute consumed by JS).
        qr_block = f'<div class="qr js-qr" data-url="{html.escape(url)}"></div>'
    return (
        '<div class="label">'
        f"{qr_block}"
        f'<div class="code">{html.escape(code)}</div>'
        "</div>"
    )


def _render(tokens: list[str], batch_id: str) -> str:
    use_server_qr = _qr_svg("probe") is not None
    if not use_server_qr:
        log.warning(
            "qrcode lib not installed — labels will render QR in-browser via CDN. "
            'For fully-offline printing run: pip install "qrcode[pil]"'
        )
    labels = "\n".join(
        _label_html(t, hug_config.scan_url(t), use_server_qr) for t in tokens
    )
    cdn = (
        ""
        if use_server_qr
        else '<script src="https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js"></script>'
    )
    js = (
        ""
        if use_server_qr
        else """
<script>
  document.querySelectorAll('.js-qr').forEach(function (el) {
    new QRCode(el, { text: el.dataset.url, width: 120, height: 120,
      correctLevel: QRCode.CorrectLevel.M });
  });
</script>"""
    )
    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>Hug labels · {html.escape(batch_id)}</title>
{cdn}
<style>
  body {{ font-family: system-ui, sans-serif; margin: 12mm; }}
  h1 {{ font-size: 14px; color: #334155; }}
  .sheet {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 6mm; }}
  .label {{ border: 1px dashed #cbd5e1; border-radius: 6px; padding: 6mm 4mm;
           text-align: center; break-inside: avoid; }}
  .qr {{ width: 32mm; height: 32mm; margin: 0 auto; }}
  .qr svg, .qr img, .qr canvas {{ width: 100%; height: 100%; }}
  .code {{ margin-top: 3mm; font-family: ui-monospace, "SF Mono", Menlo, monospace;
          font-size: 13px; letter-spacing: 1px; color: #0f172a; }}
  @media print {{ .label {{ border-color: #e2e8f0; }} h1 {{ display:none; }} }}
</style>
</head>
<body>
  <h1>Hug labels · batch {html.escape(batch_id)} · {len(tokens)} tem · scan domain {html.escape(hug_config.hug_domain())}</h1>
  <div class="sheet">
    {labels}
  </div>
  {js}
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Hug QR labels for a batch.")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--batch-id", help="Batch id to print.")
    g.add_argument("--latest", action="store_true", help="Print the most recent batch.")
    parser.add_argument("--out", default=None, help="Output HTML path (default: hug_labels_<batch>.html).")
    parser.add_argument("--data", default=None, help="Override data dir (else CRM_DATA_DIR / HUG_DB).")
    args = parser.parse_args()

    if args.data:
        os.environ["CRM_DATA_DIR"] = args.data

    conn = hug_db.connect()
    try:
        if args.latest:
            batches = repository.list_recent_batches(conn, limit=1)
            if not batches:
                log.error("no batches found in hug.db")
                sys.exit(1)
            batch_id = batches[0]["batch_id"]
        else:
            batch_id = args.batch_id
        rows = repository.list_batch(conn, batch_id)
    finally:
        conn.close()

    if not rows:
        log.error("batch %s has no tokens", batch_id)
        sys.exit(1)

    tokens = [r["token"] for r in rows]
    out = args.out or f"hug_labels_{batch_id}.html"
    html_doc = _render(tokens, batch_id)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html_doc)

    print(f"wrote {len(tokens)} labels for batch {batch_id} -> {out}")
    print("Open it and Ctrl-P -> Save as PDF (or print to a label sheet).")


if __name__ == "__main__":
    main()
