# detailView Styling Fix Report
**Date:** 2026-05-31 | **Agent:** fullstack-developer

---

## (A) panel_head: source right-alignment broken

**Root cause:** `panel_head` macro in `macros.html` wrapped `.panel-title` + `.panel-sub` in an extra `<div>`, making them siblings within that wrapper div — so `.panel-head { justify-content: space-between }` pushed only the wrapper-div and (if present) the right-slot div apart. The sub (source label) was stuck to the left under the title.

**Fix:** `macros.html` lines 172-184 — removed the extra `<div>` wrapper. `.panel-title` and `.panel-sub` are now direct children of `.panel-head`, matching JSX `PanelHead` (orderTabs.jsx:604).

**Before:**
```html
<div class="panel-head"><div><div class="panel-title">…</div><div class="panel-sub">…</div></div></div>
```

**After:**
```html
<div class="panel-head"><div class="panel-title">…</div><div class="panel-sub">…</div></div>
```

**Verified:** `curl …/tab/financial | grep panel-head` confirms direct children. Screenshot `after/order-financial.png` shows "FACT_ORDERS · FACT_ORDER_ECONOMICS" right-aligned opposite "Financial" title.

---

## (B) Sidebar eyebrow block titles missing `scard__eyebrow`

**Root cause:** `eyebrow()` macro had no `cls` parameter. All sidebar scard block-title eyebrows called `eyebrow()` without the `scard__eyebrow` class, so they lacked `margin-bottom: var(--sp-3)` (CSS: `.scard__eyebrow { margin-bottom: var(--sp-3) }`). Titles hugged the next element with no gap.

**Fix:**
1. Extended `eyebrow(text, accent=False, cls="")` in `macros.html` — appends `cls` to class list.
2. Updated every sidebar scard block-title call site to pass `cls="scard__eyebrow"`, matching JSX `<Eyebrow className="scard__eyebrow">`.

**Order sidebar** (`order_detail.html`):
- "Order at a glance" → `cls="scard__eyebrow"` (JSX order.jsx:51)
- "Money headline" → `cls="scard__eyebrow"` (JSX order.jsx:63)
- "Recipient · Buyer" inside `.party-head` → `cls="scard__eyebrow"` (JSX order.jsx:137; note: `.party-head .scard__eyebrow { margin-bottom:0 }` override keeps it compact inside flex row)
- "Quick facts" → `cls="scard__eyebrow"` (JSX order.jsx:86)
- "Data-quality flags" → `cls="scard__eyebrow"` (JSX order.jsx:100)

**Operations tab** (`partials/order/_operations.html`):
- "Recipient — receives the goods" inside `.party-head` → `cls="scard__eyebrow"` (JSX order.jsx:161)
- "Buyer — placed & paid" → `cls="scard__eyebrow"` (JSX order.jsx:174)

**Customer sidebar** (`customer_detail.html`):
- "Customer profile" → `cls="scard__eyebrow"` (JSX customer.jsx:55)
- "Headline" → `cls="scard__eyebrow"` (JSX customer.jsx:67)
- "Contact & geo" → `cls="scard__eyebrow"` (JSX customer.jsx:84)
- "Dates" → `cls="scard__eyebrow"` (JSX customer.jsx:97)

**Also removed** manual `style="margin-top:var(--sp-3)"` from `kpi-grid` and two `.facts` divs in `customer_detail.html` that previously compensated for missing scard__eyebrow gap.

**NOT changed** (correct as-is per JSX):
- `_channel_staff.html` "Channel"/"Staff" eyebrows: JSX uses plain `<Eyebrow accent>` with no `scard__eyebrow`; spacing handled by `style={{marginTop:"var(--sp-3)"}}` on `.facts` — preserved.
- `_overview.html` / `_behavior.html` "Segmentation" eyebrow: JSX uses `style={{marginBottom:"var(--sp-3)"}}` inline, Jinja equivalent is `margin-top:var(--sp-3)` on `.badge-row` — preserved.

---

## (C) Font: Geist Mono all weights pointing to wrong 6KB file

**Root cause:** `fonts.css` had **all 30 Geist Mono @font-face declarations** (6 subsets × 5 weights) pointing to the same file `v5_or3nQ6H-1_WfwkMZ.woff2` (6,180 bytes). Inspecting: this file is a valid woff2 but covers only the `symbols2` unicode range (U+2000-2001 etc.), not Latin characters. Browser falls back to `ui-monospace / SF Mono / Menlo` for all regular ASCII — different x-height, different visual weight.

**Fix:**
1. Downloaded 6 correct Geist Mono v5 subset files from Google Fonts CDN:
   - `v5_geistmono_cyrillicext.woff2` (6,180 b)
   - `v5_geistmono_cyrillic.woff2` (12,876 b)
   - `v5_geistmono_symbols2.woff2` (5,804 b)
   - `v5_geistmono_vietnamese.woff2` (7,716 b)
   - `v5_geistmono_latinext.woff2` (14,784 b)
   - **`v5_geistmono_latin.woff2` (29,896 b)** ← the key missing file for Latin glyphs
2. Updated all 30 Geist Mono `@font-face` src lines in `fonts.css` to use the correct subset file for each unicode-range.

**Files added to repo:**
- `detailView/app/adapters/inbound/web/static/fonts/v5_geistmono_*.woff2` (6 files)

**Verified:** `curl …/static/fonts/fonts.css | grep geistmono` shows all 6 unique filenames.

---

## (D) Horizontal spacing / sidebar structure

**Finding:** After (A) and (B) fixes, the sidebar structure already matched JSX. No structural markup divergences found for `.money-line`, `.facts`, `.party-head`, `.mini-meta`, `.id-code`/`.id-sub` — all present and correct in existing templates. The "inconsistent" spacing perception was entirely caused by the missing `scard__eyebrow` margin (fixed in B) and the manual inline `margin-top` compensations (removed in B).

**Intentionally unchanged:** inline `style="margin-top:var(--sp-3)"` on `.facts` inside `_channel_staff.html` — JSX explicitly uses `style={{marginTop:"var(--sp-3)"}}` there (JSX orderTabs.jsx:533,542), so this is correct per design.

---

## Files Modified

| File | Change |
|------|--------|
| `detailView/app/adapters/inbound/web/templates/macros.html` | `panel_head` rm wrapper div; `eyebrow` add `cls` param |
| `detailView/app/adapters/inbound/web/templates/order_detail.html` | 5 eyebrow call sites → `cls="scard__eyebrow"` |
| `detailView/app/adapters/inbound/web/templates/customer_detail.html` | 4 eyebrow call sites → `cls="scard__eyebrow"`; rm 2 manual margin-top |
| `detailView/app/adapters/inbound/web/templates/partials/order/_operations.html` | 2 eyebrow call sites → `cls="scard__eyebrow"` |
| `detailView/app/adapters/inbound/web/static/fonts/fonts.css` | 30 Geist Mono `@font-face` src lines → correct subset files |
| `detailView/app/adapters/inbound/web/static/fonts/v5_geistmono_*.woff2` | 6 new font files added |

---

## Screenshots

- `plans/260531-1316-detailview-styling/after/order-financial.png` — order page, financial tab (panel_head + sidebar fixes visible)
- `plans/260531-1316-detailview-styling/after/customer-overview.png` — customer page (sidebar eyebrow spacing + panel_head fixes visible)

No "before" screenshots captured (app was already modified before screenshot tooling was set up; HTML diff above provides the before/after contrast).

---

## Unresolved Questions

1. **Geist Mono Vietnamese / latin-ext subsets**: The app primarily serves Vietnamese text. The Vietnamese woff2 (7,716 b) covers U+1EA0-1EF9 (Vietnamese-specific characters). These were also missing — now fixed. Verify in browser that Vietnamese names (e.g. "Trà My") render in Geist Mono.
2. **Jinja2 template caching**: Container was restarted (not hot-reloaded) to pick up template changes. If future edits are made, `docker compose restart detail_view` or `docker cp` + process signal (SIGHUP) is needed — no volume mount for templates.
3. **Geist body font** (`v5_gyByhwUxId8gMEwc.woff2`, 29,400 b for Latin): verified present and correct size — assumed to load correctly. Could not verify computed font-family without headless devtools font inspection (browser automation session was hitting `about:blank` issue).
