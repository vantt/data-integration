"""hug_qr_print.py — render a minted batch as printable QR labels (HTML).

Each label shows:
  - a QR encoding  https://{HUG_DOMAIN}/h/{token}
  - a centered 1-char op-type code overlaid on the QR (logo-style)

Output is a single self-contained .html file optimised for THERMAL ROLL label
printers.  Page height is auto (continuous roll), page width is driven by the
layout settings (default: 2×40mm labels on an 86mm roll).  Open it and
Ctrl-P, or trigger window.print() from the web UI.

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
from hug.op_types import OP_TYPES, op_meta  # noqa: E402
from hug.tokens import grouped_code  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _qr_svg(data: str) -> str | None:
    """Return an inline SVG string for `data`, or None if qrcode unavailable.

    ECC level M (~15% recovery) keeps the module count low so the QR stays
    visually clean and crisp at the small 40mm sticker size. Nothing overlays
    the QR (the op code sits on the token line below it), so M is plenty robust
    for the short scan URL.
    """
    try:
        import qrcode  # type: ignore
        import qrcode.image.svg  # type: ignore
    except ImportError:
        return None
    import io

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode("utf-8")
    # Strip XML prolog so it embeds cleanly inline; make it fill its container.
    svg = svg.replace('<?xml version="1.0" encoding="UTF-8"?>\n', "")
    svg = svg.replace("<svg ", '<svg width="100%" height="100%" ', 1)
    return svg


def _label_html(token: str, url: str, use_server_qr: bool, badge: dict[str, str]) -> str:
    """Render a single sticker label: a clean QR with a token line beneath it.

    The QR is never overlaid (keeps it crisp at 40mm). The op-type identifier
    is the 1-char `badge["code"]` prepended to the token line — thermal roll
    printers are MONOCHROME so a printed character, not color, is what tells the
    op_types apart. Token line carries no HUG- prefix (just the grouped token).
    """
    op_code = html.escape(badge["code"])
    op_label = html.escape(badge["label"])

    if use_server_qr:
        qr_inner = _qr_svg(url) or ""
    else:
        # Client-side render via qrcodejs (JS reads data-url after DOM ready).
        qr_inner = f'<div class="js-qr" data-url="{html.escape(url)}" style="width:100%;height:100%"></div>'

    code_line = f"{op_code} &middot; {html.escape(grouped_code(token))}"

    return (
        '<div class="label">'
        f'<div class="qr">{qr_inner}</div>'
        f'<div class="code" title="{op_label}">{code_line}</div>'
        "</div>"
    )


def render_labels_html(
    tokens: list[str], batch_id: str, op_type: str = "package_insert"
) -> str:
    """Return a self-contained print-ready HTML page for the given token batch.

    QR rendering strategy:
    - Server-side SVG via the `qrcode` lib when available (fully offline).
    - Client-side CDN (qrcodejs) fallback when the lib is absent — labels still
      print correctly from any internet-connected machine.

    Layout is driven by CSS custom properties updated by an on-page control bar
    (hidden from print).  Default preset: 2 labels/row × 40mm × 40mm on an
    86mm thermal roll.  Operator can pick a different preset or enter manual
    dimensions; settings persist to localStorage.

    This function is imported by both the CLI (hug_qr_print.py) and the web
    admin screen (screen_hug_mint.py) so QR HTML is never duplicated.
    """
    badge = op_meta(op_type)
    use_server_qr = _qr_svg("probe") is not None
    if not use_server_qr:
        log.warning(
            "qrcode lib not installed — labels will render QR in-browser via CDN. "
            'For fully-offline printing run: pip install "qrcode[pil]"'
        )
    labels = "\n".join(
        _label_html(t, hug_config.scan_url(t), use_server_qr, badge) for t in tokens
    )

    # Full code legend (all op_types) so the operator can verify the batch's
    # op_type before printing.  Wrapped in .no-print so it never appears on paper.
    legend = " · ".join(
        f'{m["code"]}={html.escape(m["label"].split(" / ")[0].split(" (")[0])}'
        for m in OP_TYPES.values()
    )
    op_caption_html = (
        '<div class="op-caption">'
        f'<span class="dot" style="background:{html.escape(badge["color"])}"></span>'
        f'<span>{html.escape(badge["code"])} · {html.escape(badge["label"])}</span>'
        f'<span class="legend">{legend}</span>'
        "</div>"
    )

    cdn = (
        ""
        if use_server_qr
        else '<script src="https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js"></script>'
    )
    # Client-side QR fallback uses CorrectLevel.H to match the server SVG path.
    js_qr_init = (
        ""
        if use_server_qr
        else """
<script>
  document.querySelectorAll('.js-qr').forEach(function (el) {
    new QRCode(el, {
      text: el.dataset.url,
      width: 120, height: 120,
      correctLevel: QRCode.CorrectLevel.M
    });
  });
</script>"""
    )

    # Layout JS: drives CSS custom properties from preset select + manual inputs,
    # recomputes @page size for continuous roll printing, and persists to
    # localStorage so the operator's last-used settings survive page reloads.
    layout_js = r"""
<script>
(function () {
  var STORAGE_KEY = 'hug_label_layout';

  // Presets: [label, cols, labelW, labelH, margin, gap]
  var PRESETS = {
    'roll40x40': ['Cuộn nhiệt 40×40 · 2 tem/hàng', 2, 40, 40, 2, 2],
    'a4_3col':   ['A4 · 3 cột', 3, 64, 40, 10, 4]
  };

  function applyLayout(cols, w, h, margin, gap) {
    var root = document.documentElement;
    root.style.setProperty('--cols',    cols);
    root.style.setProperty('--label-w', w + 'mm');
    root.style.setProperty('--label-h', h + 'mm');
    root.style.setProperty('--margin',  margin + 'mm');
    root.style.setProperty('--gap',     gap + 'mm');

    // Compute roll width and update the @page rule for the continuous roll.
    var pageW = cols * w + (cols - 1) * gap + 2 * margin;
    var style = document.getElementById('page-rule');
    if (style) {
      style.textContent = '@page { size: ' + pageW + 'mm auto; margin: 0; }';
    }
  }

  function readInputs() {
    return {
      cols:   parseInt(document.getElementById('lyt-cols').value,   10) || 2,
      labelW: parseInt(document.getElementById('lyt-w').value,      10) || 40,
      labelH: parseInt(document.getElementById('lyt-h').value,      10) || 40,
      margin: parseInt(document.getElementById('lyt-margin').value,  10) || 2,
      gap:    parseInt(document.getElementById('lyt-gap').value,     10) || 2
    };
  }

  function fillInputs(cols, w, h, margin, gap) {
    document.getElementById('lyt-cols').value   = cols;
    document.getElementById('lyt-w').value      = w;
    document.getElementById('lyt-h').value      = h;
    document.getElementById('lyt-margin').value = margin;
    document.getElementById('lyt-gap').value    = gap;
  }

  function save(cols, w, h, margin, gap) {
    try {
      localStorage.setItem(STORAGE_KEY,
        JSON.stringify({cols: cols, labelW: w, labelH: h, margin: margin, gap: gap}));
    } catch (e) {}
  }

  function load() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return JSON.parse(raw);
    } catch (e) {}
    return null;
  }

  function onPresetChange() {
    var key = document.getElementById('lyt-preset').value;
    var p = PRESETS[key];
    if (!p) return;
    // p = [label, cols, w, h, margin, gap]
    fillInputs(p[1], p[2], p[3], p[4], p[5]);
    applyAndSave();
  }

  function applyAndSave() {
    var v = readInputs();
    applyLayout(v.cols, v.labelW, v.labelH, v.margin, v.gap);
    save(v.cols, v.labelW, v.labelH, v.margin, v.gap);
  }

  document.getElementById('lyt-preset').addEventListener('change', onPresetChange);
  ['lyt-cols','lyt-w','lyt-h','lyt-margin','lyt-gap'].forEach(function (id) {
    document.getElementById(id).addEventListener('input', applyAndSave);
  });

  // Restore from localStorage, falling back to the roll-40x40 default.
  var saved = load();
  if (saved) {
    fillInputs(saved.cols, saved.labelW, saved.labelH, saved.margin, saved.gap);
    applyLayout(saved.cols, saved.labelW, saved.labelH, saved.margin, saved.gap);
  } else {
    var def = PRESETS['roll40x40'];
    fillInputs(def[1], def[2], def[3], def[4], def[5]);
    applyLayout(def[1], def[2], def[3], def[4], def[5]);
  }
})();
</script>"""

    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>Hug labels · {html.escape(batch_id)}</title>
{cdn}
<!-- Dynamic @page rule updated by layout JS (continuous thermal roll). -->
<style id="page-rule">@page {{ size: 86mm auto; margin: 0; }}</style>
<style>
  /* Layout defaults via CSS custom properties — overridden by JS on load. */
  :root {{
    --cols:    2;
    --label-w: 40mm;
    --label-h: 40mm;
    --margin:  2mm;
    --gap:     2mm;
  }}
  body {{ font-family: system-ui, sans-serif; margin: 0; padding: var(--margin); }}
  h1 {{ font-size: 14px; color: #334155; margin: 0 0 4px; }}

  /* Screen-only toolbar — never printed. */
  .no-print {{ margin-bottom: 6mm; display: flex; flex-wrap: wrap;
              gap: 6px; align-items: center; }}
  .btn-print {{ padding: 8px 18px; background: #0f172a; color: #f1f5f9; border: none;
              border-radius: 6px; font-size: 14px; cursor: pointer; }}
  .btn-print:hover {{ background: #1e293b; }}
  .btn-back {{ font-size: 13px; color: #475569; text-decoration: none; }}

  /* Layout controls (inside .no-print). */
  .lyt-bar {{ display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
             font-size: 12px; color: #475569; margin-top: 4px; width: 100%; }}
  .lyt-bar select, .lyt-bar input[type=number] {{
    font-size: 12px; border: 1px solid #cbd5e1; border-radius: 4px;
    padding: 3px 5px; background: #f8fafc; }}
  .lyt-bar input[type=number] {{ width: 52px; }}
  .lyt-bar label {{ margin: 0 2px 0 6px; white-space: nowrap; }}

  /* Op-type caption — screen-only, hidden when printing. */
  .op-caption {{ display: flex; align-items: center; gap: 8px; margin: 0 0 4mm;
               font-size: 14px; font-weight: 700; color: #0f172a; }}
  .op-caption .dot {{ width: 14px; height: 14px; border-radius: 50%;
                     display: inline-block; flex-shrink: 0; }}
  .op-caption .legend {{ margin-left: auto; font-weight: 400; font-size: 11px;
                        color: #64748b; }}

  /* Label grid — driven by CSS custom properties set by JS. */
  .sheet {{
    display: grid;
    grid-template-columns: repeat(var(--cols), var(--label-w));
    gap: var(--gap);
    justify-content: start;
  }}
  .label {{
    width: var(--label-w);
    height: var(--label-h);
    box-sizing: border-box;
    /* Faint guide border on screen only (hidden in print below). */
    border: 1px dashed #cbd5e1;
    border-radius: 4px;
    padding: 1.5mm;
    break-inside: avoid;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }}

  /* QR fills the cell minus the token line; never overlaid, so it stays crisp. */
  .qr {{
    flex: 1 1 auto;
    min-height: 0;
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .qr svg, .qr img, .qr canvas {{ width: 100%; height: 100%; object-fit: contain; }}

  /* Token line under the QR: "<op-code> · 7K2N-Q9XR-WAB4". The leading op code
     is the bold identifier; sized to fit the sticker width (no wrap). */
  .code {{
    flex: 0 0 auto;
    margin-top: 1mm;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: calc(var(--label-w) * 0.085);
    font-weight: 700;
    line-height: 1;
    letter-spacing: .3px;
    white-space: nowrap;
    color: #000;
  }}

  @media print {{
    .no-print {{ display: none; }}
    .op-caption {{ display: none; }}
    .label {{ border: none; }}
    body {{ padding: 0; }}
  }}
</style>
</head>
<body>
  <div class="no-print">
    <button class="btn-print" onclick="window.print()">&#128438; In</button>
    <a class="btn-back" href="/hug/mint">&#8592; Sinh batch khác</a>
    <span style="color:#64748b;font-size:13px">Batch {html.escape(batch_id)} &middot; {len(tokens)} tem</span>
    <div class="lyt-bar">
      <select id="lyt-preset">
        <option value="roll40x40">Cuộn nhiệt 40×40 · 2 tem/hàng</option>
        <option value="a4_3col">A4 · 3 cột</option>
      </select>
      <label for="lyt-cols">Số cột</label>
      <input type="number" id="lyt-cols" min="1" max="10" value="2">
      <label for="lyt-w">Rộng (mm)</label>
      <input type="number" id="lyt-w" min="10" max="200" value="40">
      <label for="lyt-h">Cao (mm)</label>
      <input type="number" id="lyt-h" min="10" max="200" value="40">
      <label for="lyt-margin">Lề (mm)</label>
      <input type="number" id="lyt-margin" min="0" max="30" value="2">
      <label for="lyt-gap">Khe (mm)</label>
      <input type="number" id="lyt-gap" min="0" max="20" value="2">
    </div>
  </div>
  <div class="no-print">
    {op_caption_html}
  </div>
  <div class="sheet">
    {labels}
  </div>
  {js_qr_init}
  {layout_js}
</body>
</html>"""


# Keep internal alias used by main() for the CLI path (no API change).
_render = render_labels_html


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
    # op_type is uniform across a mint batch — read it off the first row.
    op_type = rows[0]["op_type"] if "op_type" in rows[0].keys() else "package_insert"
    out = args.out or f"hug_labels_{batch_id}.html"
    html_doc = _render(tokens, batch_id, op_type)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html_doc)

    print(f"wrote {len(tokens)} labels for batch {batch_id} -> {out}")
    print("Open it and Ctrl-P -> Save as PDF (or print to a label sheet).")


if __name__ == "__main__":
    main()
