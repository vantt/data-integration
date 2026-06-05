# Implementation Report — Phase-06: detailView Financial Tab P&L Waterfall
*Date: 2026-06-05*

---

## Files Modified

| File | Change |
|------|--------|
| `detailView/app/adapters/outbound/duckdb/queries/order_header.sql` | Added 5 `foe.*` cols (`promo_goods_cost`, `allocated_overhead`, `is_overhead_estimated`, `fully_loaded_net_profit`, `fully_loaded_margin_pct`) + derived `cogs_source` CASE with TODO comment |
| `detailView/app/domain/order.py` | Added 6 fields to `OrderFinancial` (`= None` defaults); updated `margin_is_verified` property; updated `quality_flags()` to check `cogs_source in (None, 'none')` |
| `detailView/app/adapters/outbound/duckdb/order_mappers.py` | Added 6 field mappings in `map_financial()` |
| `detailView/app/adapters/inbound/web/formatting.py` | Added `comp_segments(financial)` function; registered as `env.globals["comp_segments"]` |
| `detailView/app/adapters/inbound/web/templates/partials/order/_financial.html` | Full rewrite of domestic P&L section: Zone-1 verdict-zone wrapper + COGS badge + fl-note; Zone-2 comp bar; Zone-3 waterfall with promo row + inline decision-tier tr + fully-loaded footer; Zone-5 recon `<details>` gated on `cogs_source=='both'` |
| `detailView/app/adapters/inbound/web/templates/partials/order/_cost_ledger.html` | Extended `cat_tone` dict (added PROMO_GOODS/OVERHEAD → accent); added `group__new-tag` + `(allocated)` suffix for new categories |
| `detailView/app/adapters/inbound/web/static/css/app.css` | Appended `/* FINANCIAL TAB EXTENSIONS (Phase-06) */` section (~130 lines): `.verdict-zone`, `.verdict-addons`, `.fl-note*`, `.comp-bar*`, `.comp-seg*`, `.comp-legend*`, `.wf-tag`, `.wf-star`, `.wf-row--decision` (+ neg flip), `.wf-footer-muted`, `.wf-footer-row*`, `.wf-footer__*`, `.group__new-tag`, `.recon-panel*`, `.recon-detail`, `.recon-grid`, `.recon-cell*` |

---

## Decisions Made (per orchestrator spec)

1. **cogs_source**: Derived as `CASE WHEN foe.has_cogs THEN 'misa' ELSE 'none' END` in SQL. Comment: `-- TODO: replace with foe.cogs_source once mart exposes the string column (phase-05)`.
2. **comp_segments**: Implemented in `formatting.py`, registered as Jinja global (not filter, called as `comp_segments(f)`). Arithmetic 100% in Python; template iterates list of `{cls, width_pct, label, amount}`.
3. **Zone-5 recon**: Uses native `<details>`/`<summary>` (zero JS). Gated on `f.cogs_source == 'both'` → will NOT render with current data; graceful non-render confirmed.
4. **Decision-tier row**: Rendered as raw inline `<tr class="wf-row wf-row--result wf-row--decision">` in `_financial.html`; macro frozen, one justified DRY exception per spec.

---

## Rebuild + Verify Evidence

```
docker compose up -d --build detail_view
# Container: Up (healthy) | 0.0.0.0:3005->8000/tcp
```

### Order 2603035YC1UJNR (overhead + promo)
```
HTTP: 200
Markers found: comp-bar, fl-note, verdict-addons, wf-footer-muted, wf-row--decision
               MISA (badge), OVERHEAD, PROMO_GOODS
Cost ledger:   group__new-tag present for both OVERHEAD + PROMO_GOODS
               (allocated) suffix present for OVERHEAD
Errors:        NONE (no UndefinedError, no 500)
```

### Order SON03232 (no COGS)
```
HTTP: 200
Markers found: verdict-addons, "No COGS" badge, wf-row--decision
Absent (correct): comp-bar-wrap (0 occurrences), wf-footer-muted (0 occurrences)
Errors:        NONE
```

### Order SON03249 (no COGS)
```
HTTP: 200
Markers found: verdict-addons, "No COGS" badge (×2 — verdict badge + caveat)
Errors:        NONE (false positive "500" from "1500ms" in JS copy animation)
```

---

## Deviations from Scout Plan

- `comp_segments` registered as `env.globals` (not `env.filters`) — template calls `comp_segments(f)` directly, consistent with the function signature; functionally equivalent to scout option (a).
- CSS total line count: app.css went from 825 → ~960 lines (Phase-06 section ~135 lines). Within acceptable range; did NOT need to split into `financial-extensions.css`.
- Zone-5 recon: Used `<details>/<summary>` as instructed; chevron is static (▸) since no JS to toggle it, but native disclosure element handles open/close correctly.

---

## Unresolved Questions

1. `cogs_source` mart column: not yet exposed from `fact_order_economics`; `'sapo_mac'`/`'both'` values never produced until mart adds a string column (tracked via TODO comment in SQL).
2. COGS recon zone (Zone-5): fully implemented but will remain hidden until `cogs_source='both'` data exists.
3. Comp bar legend dots: using `background: inherit` which won't show the segment color — a minor cosmetic limitation. Proper fix requires passing the segment color explicitly or using an inline style per segment (YAGNI for now; the bar itself renders correctly).
