# Scout Report — Phase-06: detailView Financial Tab P&L Waterfall
*Generated: 2026-06-05 | Context: Phase-06 of 260604-1030-unified-order-pl-cogs-overhead plan*

---

## Summary

The Order-P&L pipeline is fully live in `fact_order_economics` + `fact_order_costs`. All 6 new fields (`allocated_overhead`, `fully_loaded_net_profit`, `fully_loaded_margin_pct`, `is_overhead_estimated`, `promo_goods_cost`, `cogs_source`) are present in the mart SQL — they just need to be surfaced to detailView via: (1) SQL `order_header.sql` extension, (2) domain + mapper updates, (3) template rewrite of `_financial.html` + `_cost_ledger.html`, (4) new CSS classes. The design reference JSX (`financial.jsx`) + CSS in `docs/design/app/styles/app.css` provide pixel-faithful blueprints for all 5 zones. Concurrent customer stream is already merged (only `main` branch, no open PRs). Zero blockers.

---

## 1. New Design Language (Precision DS — must follow)

Source: `detailView/docs/design/README.md` + `docs/design/app/styles/app.css`

- **Fonts**: Fraunces (display/section titles), Geist (body 14px), Geist Mono (labels, all numbers). Already loaded.
- **Theme**: `data-theme="dark"` default. All CSS uses `var(--*)` tokens only — dark/light free.
- **Color tokens** (use by name, never hex inline):
  - Ink ramp: `--ink-050` page, `--ink-100` card, `--ink-150` raised
  - Semantic: `--accent` amber, `--success`/`--moss-500` good, `--honey-500` warn, `--coral-500` bad
  - Text: `--fg`, `--fg-1`, `--fg-muted`, `--fg-tertiary`, `--fg-disabled`
- **Spacing**: 4px base — `--sp-1:4 --sp-2:8 --sp-3:12 --sp-4:16 --sp-5:24`
- **Motion**: ≤260ms, no spring/bounce
- **Rule**: Color is NEVER the only signal — every badge carries text
- **Waterfall grid**: `op (20px) | label (1fr) | % (72px) | amount (140px)` — real `<table>` using CSS classes `.wf-op`, `.wf-label`, `.wf-pct`, `.wf-amt`
- **Decision tier** `.wf-row--decision`: moss-bg tint, bold moss-500 amount, star glyph `★`; coral flips when negative (via `.wf-amt--neg`)
- **Fully-loaded footer** `.wf-footer-muted`: dashed border box, 2 rows (overhead + fully-loaded), grid `op | label | amount`
- **Composition bar** `.comp-bar`: flex strip 24px tall, 5 color segments, legend below
- **NEW tag** `.group__new-tag`: moss-500 mono 9px bold for PROMO_GOODS and OVERHEAD categories
- **Recon panel** `.recon-panel`: dashed border, click-to-expand, shows `▸`/`▾` chevron

---

## 2. Old Design Good-Parts to Keep

Source: `plans/260604-1030-unified-order-pl-cogs-overhead/design-prompt-financial-tab.md` + current `_financial.html`

- **Full VAT bridge intact** (Gross → −Discount → Total Collected → −VAT → Net Revenue) — non-negotiable for domain fidelity
- **EN labels + VN tooltips via `title` attribute** — already partially in current template, expand to all rows
- **Verdict bar** (`.verdict.verdict--bar`) with dot + verdict word (Lãi/Lỗ/Chưa xác định) + Vietnamese sentence + right-side figures — keep exactly; only ADD addons below
- **Grouped collapsible cost ledger** (`.group` with `▾` chevron, subtotal, `tbl tbl--ledger` table with 5 columns) — strong provenance model; just add PROMO_GOODS + OVERHEAD styling
- **`caveat` macro usage** — keep for returns note + unverified margin notes
- **`waterfall_row` macro** — reuse as-is for existing rows; new rows use same macro
- **Graceful degradation contract** — all new zones conditional; page renders as today when new fields are null

---

## 3. Current Financial-Tab Code Map

### Route Handler
`detailView/app/adapters/inbound/web/routes.py`
- `GET /orders/{order_code}` → renders `order_detail.html` with `active_tab=OrderTab.FINANCIAL`
- `GET /orders/{order_code}/tab/{tab}` → HTMX partial → `partials/order/_financial.html`
- No service or domain changes needed for routing

### SQL — Order Economics (`order_header.sql`)
`detailView/app/adapters/outbound/duckdb/queries/order_header.sql`
Currently reads from `fact_order_economics` (aliased `foe`) via LEFT JOIN. Already projects: `cogs_amount`, `gross_profit`, `gross_margin_pct`, `channel_net_profit`, `channel_net_margin_pct`, `shopee_platform_fees` (+breakdown), `has_cogs`, `has_platform_fees`, `has_returns`.
**MISSING** (need to add): `foe.cogs_source`, `foe.promo_goods_cost`, `foe.allocated_overhead`, `foe.is_overhead_estimated`, `foe.fully_loaded_net_profit`, `foe.fully_loaded_margin_pct`

### SQL — Cost Ledger (`order_costs.sql`)
`detailView/app/adapters/outbound/duckdb/queries/order_costs.sql`
Reads `fact_order_costs WHERE order_id = ?` — already gets ALL rows including PROMO_GOODS and OVERHEAD (these categories exist in the mart). **No SQL change needed.** Template just needs styling for new categories.

### Domain Model (`order.py`)
`detailView/app/domain/order.py`
`OrderFinancial` dataclass: has all current fields. **Missing**: `promo_goods_cost`, `cogs_source`, `allocated_overhead`, `is_overhead_estimated`, `fully_loaded_net_profit`, `fully_loaded_margin_pct`.
`quality_flags()`: currently checks `not self.financial.has_cogs` → should shift to `cogs_source in (None, 'none')`.

### Mapper (`order_mappers.py`)
`detailView/app/adapters/outbound/duckdb/order_mappers.py`
`map_financial()`: maps header row dict → `OrderFinancial`. **Missing** mappings for 6 new fields.

### Templates
- `detailView/app/adapters/inbound/web/templates/partials/order/_financial.html` — main file to edit (Zone 1-3 + recon)
- `detailView/app/adapters/inbound/web/templates/partials/order/_cost_ledger.html` — edit for new category tones + NEW tag
- `detailView/app/adapters/inbound/web/templates/macros.html` — **FREEZE CONTRACT**, do not rename/change signatures. `waterfall_row` signature: `(op, label, amount, total=False, result=False, neg=False, pct_val=None)`

### CSS
`detailView/app/adapters/inbound/web/static/css/app.css`
Current has: `.waterfall`, `.wf-row`, `.wf-op`, `.wf-label`, `.wf-pct`, `.wf-amt`, `.wf-row--total`, `.wf-row--result`, `.wf-amt--neg`.
**MISSING** (need to add from design ref `docs/design/app/styles/app.css`):
`.verdict-zone`, `.verdict-addons`, `.fl-note`, `.fl-note__mark`, `.fl-note__fig`, `.comp-bar-wrap`, `.comp-bar`, `.comp-seg` + variants, `.comp-legend`, `.wf-tag`, `.wf-star`, `.wf-row--decision`, `.wf-footer-muted`, `.wf-footer-row`, `.wf-footer__op/label/amt/pct`, `.group__new-tag`, `.recon-panel`, `.recon-panel__*`, `.recon-detail`, `.recon-grid`, `.recon-cell`, `.recon-cell__*`

---

## 4. Field Availability Confirmation

### `fact_order_economics` (confirmed from SQL source)
All 6 fields ARE present in the dbt model:
- `foe.promo_goods_cost` ✓ (from `int_order_promo_goods_cost`)
- `foe.allocated_overhead` ✓ (from `int_order_overhead_allocation`)
- `foe.is_overhead_estimated` ✓
- `foe.fully_loaded_net_profit` ✓ (computed column)
- `foe.fully_loaded_margin_pct` ✓ (computed column)
- `cogs_source`: **NOT explicitly in `fact_order_economics.sql`** — the mart derives `has_cogs` from `m.cogs_amount IS NOT NULL` but does NOT output a `cogs_source` string column. The design references `cogs_source` ("sapo_mac"/"misa"/"both"/"none") but the mart does not produce it.
  → **Mitigation**: derive in `order_mappers.py` from `has_cogs`: if `has_cogs=True` → `"misa"` (current MISA-only source); or add as computed string column to `fact_order_economics`. This needs a decision — see Risks.

### `fact_order_costs` (confirmed from SQL source)
- `PROMO_GOODS` cost_category ✓ (from `int_order_promo_goods_cost` CTE)
- `OVERHEAD` cost_category ✓ (from `int_order_overhead_allocation` CTE)
- `fee_source='estimated'` for overhead ✓
- All standard columns present: `cost_type`, `cost_category`, `amount`, `source_system`, `source_record`, `fee_source`

### Serving view mechanism
Views are auto-refreshed parquet globs bootstrapped by `scripts/provisioning/bootstrap_serving_views.py`. Views named `fact_order_economics` and `fact_order_costs` exist if parquet files are in `rolling/` dir.

### `order_line_items.sql`
Does NOT project `variant_id` — only `order_line_id, sku, product_name, variant_name, ...`. Per-line COGS (Phase-06 R3) would require `variant_id` for the join key. However, **per-line COGS is NOT part of this Financial tab scope** (it belongs on the Items tab). Skip for this phase.

---

## 5. Files to Modify / Create

### Modify (ordered by dependency)
| File | What changes |
|------|-------------|
| `detailView/app/adapters/outbound/duckdb/queries/order_header.sql` | ADD 5 columns from `foe.*`: `promo_goods_cost`, `allocated_overhead`, `is_overhead_estimated`, `fully_loaded_net_profit`, `fully_loaded_margin_pct`. Add derived `cogs_source` (see Step 3 note). |
| `detailView/app/domain/order.py` | ADD 6 fields to `OrderFinancial` with `= None` defaults. Update `quality_flags()` to check `cogs_source`. Update `margin_is_verified`. |
| `detailView/app/adapters/outbound/duckdb/order_mappers.py` | Extend `map_financial()` with 6 new field mappings. |
| `detailView/app/adapters/inbound/web/templates/partials/order/_financial.html` | Full rewrite of content (keep structure). Add Zones 1-addons, Zone 2 comp bar, extend Zone 3 waterfall (promo row + overhead footer), add Zone 5 recon panel. |
| `detailView/app/adapters/inbound/web/templates/partials/order/_cost_ledger.html` | Add `PROMO_GOODS` and `OVERHEAD` to `cat_tone` dict. Add `NEW` tag for those categories. Add `(allocated)` suffix for OVERHEAD. |
| `detailView/app/adapters/inbound/web/static/css/app.css` | Append new CSS classes for all missing selectors listed above (≈80-100 lines). |

### Create (new files)
None strictly required for this scope. The phase-06 plan spec mentioned `order_line_cogs.sql` and `order_cogs_recon.sql` but:
- Per-line COGS is Items tab scope (not this task)
- COGS recon panel: the design shows it only when `cogs_source == "both"` and `sapo_mac_cogs`/`misa_cogs_632` fields exist. Since `fact_order_economics` only has Sapo-MAC COGS as `cogs_amount` and MISA as `cogs_amount` (currently MISA-sourced per phase-05), and no explicit `sapo_mac_cogs`/`misa_cogs_632` separate fields exist in the mart, the recon zone will be hidden in practice (condition `cogs_source == "both"` won't be met). Can implement the zone but it will only show when both sources are available. For now, implement the zone with graceful degradation — it won't render until both COGS sources coexist.

---

## 6. Step-by-Step Implementation Plan

### Step 1 — Verify serving columns (pre-req gate)
```bash
docker compose exec data_platform python -c "
import duckdb
con = duckdb.connect('/app/var/data_lake/serving/olap.duckdb', read_only=True)
cols = [r[0] for r in con.execute(\"SELECT column_name FROM information_schema.columns WHERE table_name='fact_order_economics'\").fetchall()]
print(cols)
con.close()
"
```
Confirm `allocated_overhead`, `fully_loaded_net_profit`, `fully_loaded_margin_pct`, `is_overhead_estimated`, `promo_goods_cost` all present. If any missing, run `docker compose exec data_platform dbt build --select fact_order_economics` first.

### Step 2 — Extend `order_header.sql`
File: `detailView/app/adapters/outbound/duckdb/queries/order_header.sql`

After `foe.has_returns`, add:
```sql
    foe.promo_goods_cost,
    foe.allocated_overhead,
    foe.is_overhead_estimated,
    foe.fully_loaded_net_profit,
    foe.fully_loaded_margin_pct,
    -- cogs_source: derive from has_cogs until mart exposes string column
    CASE
        WHEN foe.has_cogs THEN 'misa'
        ELSE 'none'
    END AS cogs_source,
```
Note: once `fact_order_economics` exposes `cogs_source` as a proper column (future), replace this CASE with `foe.cogs_source`.

### Step 3 — Update `order.py` (Domain)
File: `detailView/app/domain/order.py`

In `OrderFinancial` dataclass, add after `has_returns`:
```python
# Phase-06: P&L tier-3 fields
promo_goods_cost: Decimal | None = None
cogs_source: str | None = None        # 'misa' | 'none' (extend when sapo_mac/both available)
allocated_overhead: Decimal | None = None
is_overhead_estimated: bool | None = None
fully_loaded_net_profit: Decimal | None = None
fully_loaded_margin_pct: float | None = None
```

Update `quality_flags()`:
```python
# Replace: if not self.financial.has_cogs:
if self.financial.cogs_source in (None, 'none'):
    flags.append(DataQualityFlag("no_cogs", "Margin unverified — no COGS match for this order", "warn"))
```

Update `margin_is_verified`:
```python
@property
def margin_is_verified(self) -> bool:
    if self.cogs_source is not None:
        return self.cogs_source in ('sapo_mac', 'both', 'misa')
    return self.has_cogs
```

### Step 4 — Update `order_mappers.py`
File: `detailView/app/adapters/outbound/duckdb/order_mappers.py`

In `map_financial()`, add after `has_returns=...`:
```python
promo_goods_cost=rc.as_decimal(row.get("promo_goods_cost")),
cogs_source=rc.as_str(row.get("cogs_source")),
allocated_overhead=rc.as_decimal(row.get("allocated_overhead")),
is_overhead_estimated=rc.as_bool(row.get("is_overhead_estimated")),
fully_loaded_net_profit=rc.as_decimal(row.get("fully_loaded_net_profit")),
fully_loaded_margin_pct=rc.as_float(row.get("fully_loaded_margin_pct")),
```
No other mapper changes needed (repository already calls `map_financial(header_row)` and cost ledger rows already flow through `map_cost_row()` which maps `cost_category` — PROMO_GOODS/OVERHEAD will appear automatically).

### Step 5 — Rewrite `_financial.html`
File: `detailView/app/adapters/inbound/web/templates/partials/order/_financial.html`

Keep the outer structure (`{% from "macros.html" import ... %}`, `{% set f = order.financial %}`, `.tab-sections` wrapper). Rewrite the domestic P&L section (everything inside `{% else %}` block):

**Zone 1 — Verdict bar + addons**
- Keep existing verdict bar div (`.verdict.verdict--bar.verdict--{{ _vt }}`) unchanged
- ADD below the verdict bar div: `.verdict-addons` with COGS source badge (inline, no macro needed)
  ```jinja2
  <div class="verdict-addons">
    {% if f.cogs_source == 'sapo_mac' %}
      {{ badge("Sapo-MAC", "good", dot=True) }}
    {% elif f.cogs_source == 'misa' %}
      {{ badge("MISA", "neutral") }}
    {% elif f.cogs_source == 'both' %}
      {{ badge("Sapo + MISA", "good", dot=True) }}
    {% else %}
      {{ badge("No COGS", "warn", dot=True) }}
    {% endif %}
  </div>
  ```
- ADD fully-loaded footnote (conditional on `f.allocated_overhead is not none`):
  ```jinja2
  {% if f.allocated_overhead is not none and f.fully_loaded_net_profit is not none %}
  <div class="fl-note" title="Lãi ròng đầy đủ — Lãi đóng góp − chi phí vận hành. Để báo cáo.">
    <span class="fl-note__mark">ⓘ</span>
    <span>Sau phân bổ chi phí vận hành (ước tính):
      <span class="fl-note__fig">Fully-loaded net profit
        <span class="mono">{{ "+" if f.fully_loaded_net_profit >= 0 else "−" }}{{ f.fully_loaded_net_profit | abs | vnd }}</span>
        {% if f.fully_loaded_margin_pct is not none %}
          <span class="mono"> · {{ f.fully_loaded_margin_pct | pct }}</span>
        {% endif %}
      </span>
    </span>
  </div>
  {% endif %}
  ```

**Zone 2 — Composition bar** (new block, only when `f.cogs_amount is not none` and `f.net_revenue`):
```jinja2
{% if f.cogs_amount is not none and f.net_revenue %}
  {# inline composition bar — pure CSS, no JS #}
  {% set _net = f.net_revenue | float %}
  {# pct calculations in Jinja — each segment as % of net_revenue #}
  <div class="comp-bar-wrap">
    <div class="comp-bar__head">
      <span class="comp-bar__title caption">NET REVENUE COMPOSITION</span>
    </div>
    <div class="comp-bar" role="img" aria-label="Revenue composition">
      {# segments rendered as inline style widths — zero-width segments skipped #}
      ...
    </div>
    <div class="comp-legend">...</div>
  </div>
{% endif %}
```
Note: Jinja2 cannot do arithmetic easily. Use Python-computed values from template context, or use a simple approach: compute segment percents in the template using `| float` and `{% set %}`. The design reference `financial.jsx` shows the logic — replicate in Jinja. If math is too complex, add a template filter `comp_segments` that computes segments from `OrderFinancial` and returns a list of `{cls, width_pct, label}` dicts. This keeps templates clean and is consistent with hexagonal — add to `formatting.py`.

**Zone 3 — Waterfall (extend existing)**
Keep existing rows unchanged up to `channel_net_profit`. Add before `channel_net_profit` row:
```jinja2
{# Promo goods cost — only render if > 0 #}
{% if f.promo_goods_cost is not none and f.promo_goods_cost > 0 %}
  {{ waterfall_row("−",
     "Promo goods cost <span class='wf-tag'>promo</span>" | safe,
     f.promo_goods_cost, neg=True,
     pct_val=((f.promo_goods_cost / f.net_revenue) if f.net_revenue else none)) }}
{% endif %}
```

Change the `channel_net_profit` row's CSS: the macro's `result=True` gives `.wf-row--result`. Need to add `.wf-row--decision` too. Since the `waterfall_row` macro is frozen (no new params), use an extra wrapper or add a `<tr>` directly for this row instead of using the macro (one exception to DRY, justified by FREEZE CONTRACT). Or better: add `decision=False` param to macro... but FREEZE CONTRACT forbids changing signature. Solution: render the decision row directly as `<tr class="wf-row wf-row--result wf-row--decision">` inline in the template (not via macro).

**Fully-loaded footer** (new block after the waterfall `</table>`, conditional):
```jinja2
{% if f.allocated_overhead is not none and f.allocated_overhead > 0 %}
<div class="wf-footer-muted">
  <div class="wf-footer-row">
    <span class="wf-footer__op">+</span>
    <span class="wf-footer__label">
      Allocated overhead <span class="wf-tag">[est.]</span>
      {% if f.is_overhead_estimated %}{{ badge("estimated", "warn") }}{% endif %}
    </span>
    <span class="wf-footer__amt mono">−{{ f.allocated_overhead | vnd }}</span>
  </div>
  <div class="wf-footer-row wf-footer-row--result">
    <span class="wf-footer__op">=</span>
    <span class="wf-footer__label">
      Fully-loaded net profit <span class="wf-tag">[for reporting]</span>
    </span>
    <span class="wf-footer__amt mono">
      {% if f.fully_loaded_net_profit is not none %}
        {{ "+" if f.fully_loaded_net_profit >= 0 else "−" }}{{ f.fully_loaded_net_profit | abs | vnd }}
        {% if f.fully_loaded_margin_pct is not none %}
          <span class="wf-footer__pct">{{ f.fully_loaded_margin_pct | pct }}</span>
        {% endif %}
      {% endif %}
    </span>
  </div>
</div>
{% endif %}
```

**Caveats update**: replace `{% if not f.has_cogs %}` with `{% if f.cogs_source in (none, 'none') %}`.

**Zone 5 — COGS Recon** (new, after cost ledger section — inside `.tab-sections`):
```jinja2
{# COGS reconciliation — only when both Sapo-MAC and MISA data coexist #}
{# Currently will not render (cogs_source='both' not yet available) — graceful non-render #}
{% if f.cogs_source == 'both' %}
<div class="tabpanel stack-4">
  <div class="recon-panel" id="cogs-recon" ...>
    ... collapsed panel with ▸/▾ toggle via HTMX or minimal JS ...
  </div>
</div>
{% endif %}
```
For toggle behavior without heavy JS: use `<details>`/`<summary>` HTML native elements (no JS needed, consistent with HTMX approach). Style `.recon-panel` with `<details>` semantics.

### Step 6 — Update `_cost_ledger.html`
File: `detailView/app/adapters/inbound/web/templates/partials/order/_cost_ledger.html`

Extend `cat_tone` dict:
```jinja2
{% set cat_tone = {
  "COGS": "good",
  "PLATFORM_FEE": "warn",
  "TAX": "neutral",
  "SHIPPING": "neutral",
  "DISCOUNT": "accent",
  "PROMO_GOODS": "accent",
  "OVERHEAD": "accent"
} %}
```

In the group header, add NEW tag and suffix for new categories:
```jinja2
<div class="group__cat">
  <span class="group__chev">▾</span>
  {{ badge(cat or "UNKNOWN", cat_tone.get(cat, "neutral")) }}
  {% if cat in ("PROMO_GOODS", "OVERHEAD") %}
    <span class="group__new-tag">NEW</span>
  {% endif %}
  {% if cat == "OVERHEAD" %}
    <span class="wf-tag" style="margin-left:6px">(allocated)</span>
  {% endif %}
</div>
```

### Step 7 — Add CSS to `app.css`
File: `detailView/app/adapters/inbound/web/static/css/app.css`

Append a new section `/* ── FINANCIAL TAB EXTENSIONS (Phase-06) ─────── */` with all classes from `detailView/docs/design/app/styles/app.css` that are not yet in the production CSS:
- Copy verbatim: `.verdict-zone`, `.verdict-addons`, `.fl-note*`, `.comp-bar-wrap`, `.comp-bar`, `.comp-seg*`, `.comp-legend*`, `.wf-tag`, `.wf-star`, `.wf-row--decision` (+negative variant), `.wf-footer-muted`, `.wf-footer-row*`, `.wf-footer__*`, `.group__new-tag`, `.recon-panel*`, `.recon-detail`, `.recon-grid`, `.recon-cell*`
- Also add `waterfall--pl` variant classes (`.waterfall--pl .wf-row--head`, `.waterfall--pl .wf-amt`, etc.)
- Stay under 200 lines for this appended section; split into a `financial-extensions.css` partial if it exceeds that.

### Step 8 — Docker rebuild + verify
```bash
# Templates/static are baked into Docker image — MUST rebuild
docker compose up -d --build detail_view

# Verify renders — pick an order known to have overhead allocated
# (check fact_order_economics WHERE allocated_overhead IS NOT NULL LIMIT 1)
docker compose exec data_platform python -c "
import duckdb
con = duckdb.connect('/app/var/data_lake/serving/olap.duckdb', read_only=True)
r = con.execute(\"SELECT order_code, allocated_overhead, fully_loaded_net_profit FROM fact_order_economics WHERE allocated_overhead IS NOT NULL LIMIT 3\").fetchall()
print(r); con.close()
"
# Then open in browser: http://localhost:<detailview_port>/orders/<order_code>
```

---

## 7. Verify Step

1. **Find test orders**:
   - Order with overhead: query `fact_order_economics WHERE allocated_overhead IS NOT NULL LIMIT 1`
   - Order with promo goods: query `fact_order_costs WHERE cost_category='PROMO_GOODS' LIMIT 1` → get `order_code`
   - Order without COGS: query `fact_order_economics WHERE has_cogs = FALSE LIMIT 1`

2. **Rebuild** (mandatory since templates are baked):
   ```bash
   docker compose up -d --build detail_view
   ```

3. **Check each order in browser** and verify:
   - COGS source badge appears in verdict zone (Sapo-MAC / MISA / No COGS)
   - Composition bar renders when `cogs_amount` is not null
   - Promo goods row appears only for promo orders
   - Overhead footer renders for orders with `allocated_overhead`
   - Cost ledger shows PROMO_GOODS + OVERHEAD with NEW tag
   - Unverified order: only verdict + waterfall + cost ledger (no comp bar, no overhead footer)
   - No Python 500 or Jinja2 UndefinedError

4. **Check in Python** that new domain fields are populated:
   ```bash
   docker compose exec detail_view python -c "
   from app.composition import build_container
   c = build_container()
   o = c.order_service.get_detail('HD00123')  # replace with real code
   print(o.financial.allocated_overhead, o.financial.promo_goods_cost, o.financial.cogs_source)
   "
   ```

---

## 8. Risks / Unresolved Questions

1. **`cogs_source` not in `fact_order_economics` mart**: The mart SQL does not output a `cogs_source` string column. The plan spec says it should, but it wasn't implemented in Phase-04/05. For this phase, derive it from `has_cogs` as `'misa'` or `'none'` — gives correct badge for current data. Full `'sapo_mac'`/`'both'` discrimination needs a mart column addition (separate follow-up). Mark in plan.

2. **COGS recon zone won't render today**: The design's Zone 5 requires `cogs_source='both'` and separate `sapo_mac_cogs`/`misa_cogs_632` columns. Neither exists in the mart yet. Implement the zone + CSS but it will remain hidden. No harm.

3. **Composition bar Jinja arithmetic**: Jinja2 doesn't support complex math natively. Either: (a) compute segment list as a Python filter added to `formatting.py` and registered with Jinja env, or (b) use inline `{% set %}` with float divisions for each segment. Option (a) is cleaner. Implementer must decide.

4. **`waterfall_row` macro FREEZE for decision tier**: The decision tier CSS requires class `.wf-row--decision` on the `<tr>`. The frozen macro only supports `total=True` (adds `.wf-row--total`) and `result=True` (adds `.wf-row--result`). Solution options: (a) render the decision row as raw HTML inline in template (bypass macro), (b) add a new separate macro `waterfall_row_decision` with separate name to avoid breaking existing callers. Option (a) is simplest.

5. **`f.shopee_platform_fees` is stored negative** in `fact_order_economics` (Shopee fees are negative cash flows). Current template uses `(f.shopee_platform_fees | abs)` correctly. The new promo goods cost is positive in `fact_order_economics` (`promo_goods_cost` = positive amount). Confirm sign convention from the mart SQL — `order_promo` CTE does `SUM(promo_goods_cost_amount)` (positive). Template should show it as a cost row (neg=True) and pass the positive value. Verify.

6. **Concurrent stream gate**: Confirmed clear — only `main` branch exists, latest detailView commits are design/rename updates (no open PR). Safe to proceed.

7. **Docker compose service name**: Ensure `docker compose up -d --build detail_view` matches the service name in `docker-compose.yml`. Verify before rebuild step.

---

**Status:** DONE
**Summary:** All fields are confirmed in the mart layer; serving views auto-include them. The 6 implementation files are clearly identified. The design reference JSX provides pixel-faithful blueprints for all 5 zones. One gap: `cogs_source` string column missing from mart (derive workaround provided).
**Concerns/Blockers:** `cogs_source` not exposed as a proper `fact_order_economics` column — workaround is `CASE WHEN has_cogs THEN 'misa' ELSE 'none' END` in `order_header.sql`. Full `'sapo_mac'`/`'both'` discrimination needs a separate mart PR. COGS recon zone (Zone 5) will be implemented but will not render until `cogs_source='both'` data exists.
