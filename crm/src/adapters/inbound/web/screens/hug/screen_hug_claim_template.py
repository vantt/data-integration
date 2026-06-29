"""Self-contained kiosk page template for the Hug claim station.

A single str.format() template — no template engine dependency. The station
runs on a tablet/PC with a USB 2D scanner, so the whole page (CSS + JS) ships
inline. All literal CSS/JS braces are doubled (``{{`` / ``}}``); the five
runtime placeholders are filled by ``screen_hug_claim_render._render_page``:

  fields_html        — config-driven CLAIM_FIELDS inputs
  tk                 — escaped token prefill value
  result_html        — the live-region result banner
  claim_fields_json  — CLAIM_FIELDS serialised for the JS block
  play               — "ok" | "err" | null sound cue for the no-JS POST path
"""
from __future__ import annotations

CLAIM_PAGE_TEMPLATE = """<!doctype html>
<html lang="vi" data-surface="HUG-CLAIM">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hug · Claim station</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
         margin: 0; background: #0f172a; color: #e2e8f0;
         display: flex; min-height: 100vh; align-items: center; justify-content: center; }}
  .card {{ width: min(560px, 92vw); background: #1e293b; border-radius: 16px;
          padding: 28px 28px 32px; box-shadow: 0 12px 40px rgba(0,0,0,.4); }}
  h1 {{ font-size: 20px; margin: 0 0 4px; letter-spacing: .5px; }}
  .sub {{ color: #94a3b8; font-size: 13px; margin: 0 0 20px; }}
  label {{ display: block; font-size: 12px; text-transform: uppercase;
          letter-spacing: .6px; color: #94a3b8; margin: 14px 0 6px; }}
  input[type=text] {{ width: 100%; padding: 14px 16px; font-size: 20px;
          border-radius: 10px; border: 1px solid #334155; background: #0f172a;
          color: #f1f5f9; outline: none; }}
  input#f_token {{ font-size: 26px; letter-spacing: 3px; text-align: center;
          font-variant-numeric: tabular-nums; }}
  input:focus {{ border-color: #38bdf8; box-shadow: 0 0 0 3px rgba(56,189,248,.25); }}
  .row {{ display: flex; gap: 16px; align-items: center; margin-top: 16px; flex-wrap: wrap; }}
  .row .grp {{ flex: 1; min-width: 160px; }}
  .toggle {{ display: flex; align-items: center; gap: 8px; font-size: 15px; }}
  .toggle input {{ width: 22px; height: 22px; }}
  .sublabel {{ display: block; font-size: 12px; margin-top: 3px; min-height: 16px; }}
  .sublabel-ok  {{ color: #4ade80; }}
  .sublabel-err {{ color: #f87171; }}
  .sublabel-warn {{ color: #fbbf24; }}
  .result {{ margin-top: 22px; text-align: center; border-radius: 12px; padding: 0; }}
  .result.ok {{ background: #064e3b; padding: 20px; }}
  .result.err {{ background: #7f1d1d; padding: 20px; }}
  .result .big {{ font-size: 48px; line-height: 1; }}
  .result .msg {{ font-size: 18px; margin-top: 8px; font-weight: 600; }}
  .result .edge {{ font-size: 12px; color: #cbd5e1; margin-top: 8px; }}
  .hint {{ margin-top: 18px; font-size: 12px; color: #64748b; text-align: center; }}
  button {{ width: 100%; margin-top: 18px; padding: 16px; font-size: 18px; font-weight: 700;
          border: none; border-radius: 10px; background: #38bdf8; color: #0f172a; cursor: pointer; }}
  button:hover {{ background: #0ea5e9; }}
</style>
</head>
<body>
  <main class="card">
    <h1>Hug · Claim station</h1>
    <p class="sub">Quét tem → tự bind vào đơn → bíp + xanh → dán.</p>
    <form id="claim" method="post" action="/hug/claim" autocomplete="off">
      {fields_html}
      <label for="f_token">Tem (quét mã 2D)</label>
      <input type="text" id="f_token" name="token" value="{tk}"
             placeholder="quét tem…" autofocus autocapitalize="characters" spellcheck="false">
      <small id="lbl_token" class="sublabel"></small>
      <button type="submit">Gắn tem vào đơn</button>
    </form>
    {result_html}
    <p class="hint">Tem = 12 ký tự. Máy quét tự xuống dòng → tự gửi.</p>
  </main>
<script>
  // ── Config injected from Python CLAIM_FIELDS (validate key stripped) ──────
  const FIELDS = {claim_fields_json};
  // One UUID per page-load; persists across re-scans within the same session.
  // Reset only on full page reload or fresh navigation.
  const SESSION_ID = crypto.randomUUID();

  // ── Audio cues via WebAudio — no asset files needed ───────────────────────
  function beep(ok) {{
    try {{
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator(), gain = ctx.createGain();
      osc.connect(gain); gain.connect(ctx.destination);
      osc.frequency.value = ok ? 880 : 220;
      gain.gain.setValueAtTime(0.15, ctx.currentTime);
      osc.start();
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + (ok ? 0.18 : 0.45));
      osc.stop(ctx.currentTime + (ok ? 0.2 : 0.5));
    }} catch (e) {{}}
  }}

  // Play sound on full-page re-render (no-JS fallback POST path result).
  const lastResult = {play};
  if (lastResult) beep(lastResult === "ok");

  // ── DOM helpers ───────────────────────────────────────────────────────────
  function getFieldEl(key)  {{ return document.getElementById('f_' + key); }}
  function getLabelEl(key)  {{ return document.getElementById('lbl_' + key); }}

  function showSubLabel(key, text, state) {{
    // state: 'ok' | 'err' | 'warn'
    const el = getLabelEl(key);
    if (!el) return;
    el.textContent = text;
    el.className = 'sublabel sublabel-' + state;
  }}

  function clearSubLabel(key) {{
    const el = getLabelEl(key);
    if (el) {{ el.textContent = ''; el.className = 'sublabel'; }}
  }}

  // ── Token normalisation — mirrors server-side normalize_input() logic ─────
  // Printed human codes (HUG-XXXX-XXXX-XXXX) and scanned full QR URLs are
  // both reduced to the raw 12-char token so they auto-check correctly.
  const RE = /^[2-9A-HJKMNP-Z]{{12}}$/;
  function normalizeToken(v) {{
    v = v.trim().toUpperCase();
    // Full QR URL emitted by scanner → extract last path segment.
    if (v.includes("://")) {{
      v = v.split("?")[0].split("#")[0].replace(/\\/+$/, "").split("/").pop();
    }}
    // Remove separator characters: dashes, underscores, dots, whitespace.
    // Matches the Worker normalizeToken separator set so all three copies accept the same inputs.
    v = v.replace(/[-_.\\s]/g, "");
    // Strip a "HUG" prefix only when the result is exactly 15 chars (= "HUG" + 12-char token).
    // A genuine 12-char token starting with HUG stays intact — length 12 never triggers this.
    if (v.length === 15 && v.startsWith("HUG")) v = v.slice(3);
    return v;
  }}

  // ── Per-field live validation (text fields with validate set) ─────────────
  async function checkField(key, value) {{
    try {{
      const r = await fetch('/hug/claim/check-field?key=' + encodeURIComponent(key)
                            + '&value=' + encodeURIComponent(value)
                            + '&session=' + encodeURIComponent(SESSION_ID));
      return await r.json();
    }} catch (_) {{
      return {{ ok: null, message: 'Lỗi kết nối' }};
    }}
  }}

  // Wire debounced check-field to every text FIELD that has a validate key.
  // This loop makes adding a new validated text field require zero frontend edits.
  const fieldTimers = {{}};
  for (const f of FIELDS) {{
    if (f.type !== 'text') continue;
    const el = getFieldEl(f.key);
    if (!el) continue;
    el.addEventListener('input', () => {{
      clearTimeout(fieldTimers[f.key]);
      fieldTimers[f.key] = setTimeout(async () => {{
        const v = el.value.trim();
        if (!v) {{ clearSubLabel(f.key); return; }}
        const res = await checkField(f.key, v);
        if (res.ok === true)       showSubLabel(f.key, res.message, 'ok');
        else if (res.ok === false) {{ showSubLabel(f.key, res.message, 'err'); beep(false); }}
        else                       showSubLabel(f.key, res.message || 'Không thể kiểm tra', 'warn');
      }}, 600);
    }});
    // Pre-fill from query param: if field already has a value on page load,
    // trigger the check immediately so the sub-label shows state without user interaction.
    if (el.value.trim()) {{
      setTimeout(() => el.dispatchEvent(new Event('input')), 0);
    }}
  }}

  // ── Token field: normalise → check-token → doBind ────────────────────────
  const tokenEl = getFieldEl('token');

  async function checkToken(value) {{
    let res;
    try {{
      const r = await fetch('/hug/claim/check-token?token=' + encodeURIComponent(value)
                            + '&session=' + encodeURIComponent(SESSION_ID));
      res = await r.json();
    }} catch (_) {{
      res = {{ state: 'error', message: 'Lỗi kết nối' }};
    }}

    if (res.state === 'ready' || res.state === 'rebind_ok') {{
      const isAmber = res.state === 'rebind_ok';
      showSubLabel('token', res.message, isAmber ? 'warn' : 'ok');
      beep(true);
      await doBind(value);
    }} else {{
      showSubLabel('token', res.message, 'err');
      beep(false);
    }}
  }}

  async function doBind(token) {{
    // Collect current values from all CLAIM_FIELDS inputs.
    const fields = {{}};
    for (const f of FIELDS) {{
      const el = getFieldEl(f.key);
      if (!el) continue;
      fields[f.key] = f.type === 'bool' ? el.checked : el.value.trim();
    }}

    // Guard: order_code must be present before binding — show amber hint and wait.
    if (!fields['order_code']) {{
      showSubLabel('token', 'Nhập mã đơn trước', 'warn');
      return;
    }}

    let res;
    try {{
      const r = await fetch('/hug/claim/bind', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ session_id: SESSION_ID, token, fields }}),
      }});
      res = await r.json();
    }} catch (_) {{
      res = {{ ok: false, message: 'Lỗi kết nối khi gắn tem' }};
    }}

    const resultEl = document.getElementById('result');
    if (res.ok) {{
      if (resultEl) {{
        resultEl.className = 'result ok';
        resultEl.innerHTML = '<div class="big">✓</div>'
          + '<div class="msg"><strong>' + res.message + '</strong></div>'
          + (res.edge ? '<div class="edge">' + res.edge + '</div>' : '');
      }}
      beep(true);
      // Clear token field + sub-label; keep order field so next sticker binds to same order.
      if (tokenEl) {{ tokenEl.value = ''; tokenEl.focus(); }}
      clearSubLabel('token');
    }} else {{
      if (resultEl) {{
        resultEl.className = 'result err';
        resultEl.innerHTML = '<div class="big">✕</div>'
          + '<div class="msg"><strong>' + res.message + '</strong></div>';
      }}
      beep(false);
    }}
  }}

  // Token field input: normalise → check against RE → trigger async check+bind.
  // Last scan always wins (no debounce; 12-char RE is the gate).
  if (tokenEl) {{
    tokenEl.addEventListener('input', async () => {{
      const v = normalizeToken(tokenEl.value);
      tokenEl.value = v;
      clearSubLabel('token');
      if (RE.test(v)) {{
        await checkToken(v);
      }}
    }});
  }}

  // ── Initial focus ─────────────────────────────────────────────────────────
  const orderEl = getFieldEl('order_code');
  // If order_code already pre-filled (e.g. from ?order=), focus token for scanning.
  if (orderEl && orderEl.value.trim()) {{
    if (tokenEl) {{ tokenEl.focus(); tokenEl.select(); }}
  }} else if (orderEl) {{
    orderEl.focus();
  }}

  // Post-form-POST clear: after a full-page re-render on the no-JS fallback path,
  // clear the token field and refocus so the kiosk is ready for the next scan.
  if (lastResult === "ok") {{
    if (tokenEl) {{ tokenEl.value = ""; tokenEl.focus(); }}
  }}
</script>
</body>
</html>"""
