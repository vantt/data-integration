# Phase 06 — detailView Per-Order P&L Panel + COGS Reconciliation

## Context Links
- Master plan: `plans/260604-1030-unified-order-pl-cogs-overhead/plan.md`
- Phase 05 output (serving layer ready): `phase-05-pl-marts-serving.md`
- COGS design §8 (detailView spec): `docs/architecture/order-pl/cogs-reconciliation-design.md`
- Overhead design §5 (fact_order_economics extensions): `docs/architecture/order-pl/overhead-cost-allocation-design.md`
- P&L schema: `docs/architecture/order-pl/order-pl-schema-design.md`
- Hexagonal arch reference: `detailView/app/domain/order.py`, `detailView/app/adapters/outbound/duckdb/order_mappers.py`
- Serving contract: `detailView/app/adapters/outbound/duckdb/queries/order_header.sql`
- Cost ledger query: `detailView/app/adapters/outbound/duckdb/queries/order_costs.sql`
- Line items query: `detailView/app/adapters/outbound/duckdb/queries/order_line_items.sql`
- Repository: `detailView/app/adapters/outbound/duckdb/order_repository.py`
- Mapper: `detailView/app/adapters/outbound/duckdb/order_mappers.py`

---

## Overview

**Priority:** P2 (blocked by phase 05 AND concurrent detailView customer stream merge)
**Status:** TODO

**CRITICAL CONCURRENCY GATE — READ FIRST:**
A concurrent work-stream is actively modifying the detailView codebase (customer pages). This phase shares files across the entire `detailView/` directory tree. **Phase 06 MUST NOT begin until the concurrent customer stream's work is fully merged and committed.** Any parallel edit risks merge conflicts in `order.py`, `order_mappers.py`, `order_header.sql`, and HTML templates. Coordinate merge timing explicitly — do not assume the concurrent stream is done.

**Scope:**
1. `OrderFinancial` domain dataclass — add 6 new fields: `promo_goods_cost`, `cogs_source`, `allocated_overhead`, `is_overhead_estimated`, `fully_loaded_net_profit`, `fully_loaded_margin_pct`.
2. `LineItem` domain dataclass — add `cogs_amount` (per-line, from `fact_inventory_movements`) and `cogs_margin` property.
3. New domain dataclass `CogsReconPanel` — order-level MISA-632 vs Sapo-MAC reconciliation.
4. `order_header.sql` — add the 6 new `fact_order_economics` columns.
5. New SQL query `order_line_cogs.sql` — per-line COGS from `fact_inventory_movements`.
6. New SQL query `order_cogs_recon.sql` — order-level reconciliation panel from `fact_order_economics` + `int_order_cogs_reconciled` (if exposed as mart view, else derive from existing economics columns).
7. `order_mappers.py` — extend `map_financial`, extend `map_line_item`, add `map_cogs_recon`.
8. `order_repository.py` — fetch line-COGS and recon panel alongside existing collections.
9. `OrderDetail` dataclass — add `cogs_recon` field.
10. Template HTML — per-line COGS column, P&L waterfall panel (all 3 tiers), recon panel.

**Architecture constraint (non-negotiable):** detailView is read-only from `fact_*`/`mart_*`/`dim_*` views only. Never query `int_*` or `stg_*`. All new SQL queries read from serving views only. Domain and application layers have zero DuckDB imports.

---

## Key Insights

### Serving Contract: Only `fact_*`/`mart_*`/`dim_*`
`int_order_cogs_reconciled` is an intermediate model — detailView **cannot** query it directly. The COGS reconciliation data must be exposed either:
- (a) Via columns promoted to `fact_order_economics` (cogs_source, has_cogs already planned in phase 05); OR
- (b) Via a dedicated `mart_order_cogs_reconciliation` view if richer per-line recon data is needed.

For the **order-level reconciliation panel**, the phase 05 columns in `fact_order_economics` (`cogs_amount` = Sapo-MAC primary, `cogs_source`, `has_cogs`) are sufficient for the summary. The `misa_gross_profit` and variance require either promoting those fields from `int_order_cogs_reconciled` into a mart, or approximating variance from existing data.

**Decision for this phase (KISS):** The recon panel uses only columns already in `fact_order_economics` after phase 05. If a dedicated `mart_order_cogs_reconciliation` is needed for richer variance data, that is a follow-up. Flag this as an open question.

### Per-Line COGS from `fact_inventory_movements`
`fact_inventory_movements` is a rolling parquet table accessible via serving views. Grain: `(document_code, sku, variant_id)`. Columns include `cogs_amount` (= `export_amount`), `quantity_delta`, `trans_type`. Sales COGS = `trans_type = 301` (sale_order_fulfillment). Join key: `document_code = order_code`.

The line-item COGS query joins `fact_inventory_movements` on `(order_code, sku)` — matching the `order_line_items.sql` grain — then aggregates net COGS per line (OUT movements − return IN legs: `SUM(cogs_amount) WHERE trans_type IN (301)` minus `SUM(cogs_amount) WHERE trans_type IN (350)`).

### Hexagonal Architecture — Change Surface
The hexagonal pattern means:
- **Domain** (`order.py`): add dataclass fields and properties only. No imports from duckdb, fastapi, or adapters.
- **Application** (`services.py`): no changes needed (passes OrderDetail through; new fields auto-included).
- **Adapter/outbound** (`order_repository.py`, `order_mappers.py`, SQL files): all data plumbing.
- **Adapter/inbound** (web routes + templates): rendering only.

This cleanly confines changes to 4 files + 2 new SQL files + 1 HTML template update.

### `quality_flags` — `no_cogs` Flag Evolution
`OrderDetail.quality_flags()` currently shows `"no_cogs"` warn flag when `has_cogs = False`. After phase 06, `has_cogs` reflects Sapo-MAC coverage (~100% fulfilled orders). The flag should update: show `"no_cogs"` only when Sapo-MAC is also missing (extreme edge case), not when MISA is missing. This is a domain-logic change in `order.py` that touches the `quality_flags` method.

### `margin_is_verified` Property
Currently: `return self.has_cogs`. After phase 06, Sapo-MAC is primary (~100% coverage) so this should be `True` for all fulfilled orders regardless of MISA coverage. Update to: `return self.cogs_source in ('sapo_mac', 'both') if self.cogs_source else self.has_cogs`.

### Promo Line Display
`promo_goods_cost` rows appear in `fact_order_costs` as `cost_category='PROMO_GOODS'`. The existing `order_costs.sql` query fetches all rows from `fact_order_costs` — promo rows will appear automatically in the cost ledger. No SQL change needed for promo display; the template may need a label/styling update for `PROMO_GOODS`.

Overhead rows (`cost_category='OVERHEAD'`, `fee_source='allocated'`) similarly appear automatically in the cost ledger. Template can show them in an "Overhead" section styled distinctly from actuals.

---

## Requirements

### Functional
- R1: P&L waterfall panel in order detail UI: shows `gross_profit`, `channel_net_profit`, `fully_loaded_net_profit`, all three margin %s.
- R2: `is_overhead_estimated` badge visible when overhead is budgeted (not MISA-confirmed).
- R3: Per-line COGS column in line items table: `cogs_amount` per line, `margin = revenue − cogs_amount`.
- R4: COGS source badge per order (`cogs_source`: sapo_mac / misa / both / none).
- R5: COGS reconciliation panel: Sapo-MAC primary COGS vs. available variance context; `cogs_source` drives display.
- R6: Promo goods cost visible in cost ledger as `PROMO_GOODS` category (auto, no SQL change).
- R7: Overhead visible in cost ledger as `OVERHEAD` category with `fee_source='allocated'` indicator (auto, template styling).
- R8: `quality_flags` updated: `"no_cogs"` fires only when `cogs_source = 'none'` (Sapo-MAC absent), not when only MISA is absent.
- R9: `margin_is_verified` updated: True when `cogs_source in ('sapo_mac', 'both')`.

### Non-Functional
- Zero DuckDB/FastAPI imports in domain or application layers.
- All new SQL queries read from `fact_*`/`mart_*`/`dim_*` views only (no `int_*`).
- Graceful degradation: if `order_line_cogs` or `order_cogs_recon` fetch fails → log warning, degrade to [] / None (existing `_safe_fetch` pattern in `order_repository.py`).
- New dataclass fields in `order.py` must have defaults so existing unit tests constructing `OrderFinancial()` / `LineItem()` without new fields do not break (use `= None` or `= False` defaults).

---

## Architecture

### Domain Changes (`order.py`)

**`OrderFinancial` — 6 new fields:**
```python
# New P&L tier-3 fields
promo_goods_cost: Decimal | None = None
cogs_source: str | None = None          # 'sapo_mac' | 'misa' | 'both' | 'none'
allocated_overhead: Decimal | None = None
is_overhead_estimated: bool | None = None
fully_loaded_net_profit: Decimal | None = None
fully_loaded_margin_pct: float | None = None
```

**`LineItem` — 1 new field + 1 new property:**
```python
cogs_amount: Decimal | None = None      # per-line COGS from fact_inventory_movements

@property
def cogs_margin(self) -> Decimal | None:
    if self.revenue is None or self.cogs_amount is None:
        return None
    return self.revenue - self.cogs_amount
```

**New `CogsReconPanel` dataclass:**
```python
@dataclass
class CogsReconPanel:
    sapo_mac_cogs: Decimal | None = None   # cogs_amount from fact_order_economics (Sapo-MAC)
    cogs_source: str | None = None         # 'sapo_mac' | 'misa' | 'both' | 'none'
    has_sapo_cogs: bool = False
    has_misa_cogs: bool = False
    # Fields below present only if mart_order_cogs_reconciliation exists:
    misa_cogs_632: Decimal | None = None   # MISA TK632-only COGS (None if not exposed as mart)
    cogs_variance: Decimal | None = None   # sapo_mac_cogs − misa_cogs_632
    cogs_variance_pct: float | None = None
```

**`OrderDetail` — 1 new field:**
```python
cogs_recon: CogsReconPanel = field(default_factory=CogsReconPanel)
```

**`quality_flags` method update:**
```python
# Replace: if not self.financial.has_cogs:
if self.financial.cogs_source in (None, 'none'):
    flags.append(DataQualityFlag("no_cogs", "Margin unverified — no COGS (Sapo or MISA)", "warn"))
```

**`margin_is_verified` property update:**
```python
@property
def margin_is_verified(self) -> bool:
    if self.cogs_source is not None:
        return self.cogs_source in ('sapo_mac', 'both')
    return self.has_cogs   # fallback for pre-phase-06 rows
```

### Adapter — New SQL Queries

**`order_line_cogs.sql`** (new file — reads `fact_inventory_movements`):
```sql
-- Per-line COGS for one order from Sapo inventory movements (trans_type=301 sales only).
-- Returns net COGS per (sku, variant_id): OUT movements minus return legs.
-- Join key: document_code = order_code (cast to match fact_sales.order_code).
SELECT
    fim.sku,
    fim.variant_id,
    SUM(CASE WHEN fim.trans_type = 301 THEN fim.cogs_amount ELSE 0 END)
    - SUM(CASE WHEN fim.trans_type = 350 THEN ABS(fim.cogs_amount) ELSE 0 END)
        AS cogs_amount
FROM fact_inventory_movements fim
WHERE fim.document_code = ?
  AND fim.trans_type IN (301, 350)
GROUP BY fim.sku, fim.variant_id
HAVING cogs_amount IS NOT NULL;
```

**`order_cogs_recon.sql`** (new file — reads `fact_order_economics`):
```sql
-- COGS reconciliation summary for one order (order-level, not line-level).
-- Source: fact_order_economics (cogs_amount = Sapo-MAC primary after phase 05).
-- misa_cogs_632 and variance columns present only if promoted from int_ to mart_ in future.
SELECT
    foe.cogs_amount          AS sapo_mac_cogs,
    foe.cogs_source,
    foe.has_cogs             AS has_sapo_cogs,
    -- has_misa_cogs: derived from cogs_source until int_ data is mart-promoted
    (foe.cogs_source IN ('misa', 'both')) AS has_misa_cogs
FROM fact_order_economics foe
WHERE foe.order_id = ?
LIMIT 1;
```

### Adapter — Repository Changes (`order_repository.py`)

Add two `_safe_fetch` calls in `get_by_code`:
```python
line_cogs_rows = _safe_fetch(conn, "order_line_cogs", [canonical_code])
cogs_recon_rows = _safe_fetch(conn, "order_cogs_recon", [order_id])
```

Merge line-COGS into line items (by sku+variant_id) before constructing `LineItem` objects. Build `CogsReconPanel` from `cogs_recon_rows[0]` if present.

Return from `get_by_code`:
```python
return OrderDetail(
    ...existing fields...,
    line_items=[om.map_line_item(r, line_cogs_map) for r in line_rows],
    cogs_recon=om.map_cogs_recon(cogs_recon_rows[0] if cogs_recon_rows else {}),
)
```

### Adapter — Mapper Changes (`order_mappers.py`)

**`map_financial`** — add 6 new field mappings:
```python
promo_goods_cost=rc.as_decimal(row.get("promo_goods_cost")),
cogs_source=rc.as_str(row.get("cogs_source")),
allocated_overhead=rc.as_decimal(row.get("allocated_overhead")),
is_overhead_estimated=rc.as_bool(row.get("is_overhead_estimated")),
fully_loaded_net_profit=rc.as_decimal(row.get("fully_loaded_net_profit")),
fully_loaded_margin_pct=rc.as_float(row.get("fully_loaded_margin_pct")),
```

**`map_line_item`** — add `cogs_amount` parameter (from pre-joined dict keyed by `(sku, variant_id)`):
```python
def map_line_item(row: Row, cogs_map: dict | None = None) -> LineItem:
    key = (rc.as_str(row.get("sku")), rc.as_str(row.get("variant_id")))
    line_cogs = cogs_map.get(key) if cogs_map else None
    return LineItem(
        ...existing fields...,
        cogs_amount=line_cogs,
    )
```

**New `map_cogs_recon`:**
```python
def map_cogs_recon(row: Row) -> CogsReconPanel:
    return CogsReconPanel(
        sapo_mac_cogs=rc.as_decimal(row.get("sapo_mac_cogs")),
        cogs_source=rc.as_str(row.get("cogs_source")),
        has_sapo_cogs=rc.as_bool(row.get("has_sapo_cogs")),
        has_misa_cogs=rc.as_bool(row.get("has_misa_cogs")),
    )
```

### `order_header.sql` Extension

Add 6 columns after `foe.has_returns`:
```sql
    foe.cogs_source,
    foe.promo_goods_cost,
    foe.allocated_overhead,
    foe.is_overhead_estimated,
    foe.fully_loaded_net_profit,
    foe.fully_loaded_margin_pct,
```

### Template — P&L Panel (HTML)

Add/extend the financial section in the order detail template. Panels to add:

**P&L Waterfall panel:**
```
Gross Profit         [gross_margin_pct %]
  − Promo Goods      [promo_goods_cost]           (if present)
  − Platform Fees    [shopee_platform_fees]         (if Shopee)
  − Shop Discount    [discount_amount]
= Channel Net Profit [channel_net_margin_pct %]
  − Overhead         [allocated_overhead]           (if present; badge: "Estimated" if is_overhead_estimated)
= Fully Loaded NP    [fully_loaded_margin_pct %]   (if overhead present)
```

**COGS Source badge** near the COGS row: `[Sapo-MAC]` / `[MISA]` / `[Both]` / `[No COGS]` in different colors.

**COGS Reconciliation panel** (collapsible): shows `sapo_mac_cogs` with source badge. If `misa_cogs_632` available (future), shows variance row.

**Per-line COGS column** in line items table: `COGS` column showing `cogs_amount` per line and `margin = revenue − cogs_amount`. Shown only when at least one line has COGS data.

**Cost ledger styling** for new categories: `PROMO_GOODS` = orange label, `OVERHEAD` = purple label with "(allocated)" note when `fee_source='allocated'`.

---

## Related Code Files

### Modify (this phase OWNS these — after concurrent stream merges)
- `detailView/app/domain/order.py` — new fields in `OrderFinancial`, `LineItem`; new `CogsReconPanel`; new field in `OrderDetail`; update `quality_flags`, `margin_is_verified`
- `detailView/app/adapters/outbound/duckdb/order_mappers.py` — extend `map_financial`, `map_line_item`; add `map_cogs_recon`
- `detailView/app/adapters/outbound/duckdb/order_repository.py` — fetch `order_line_cogs` + `order_cogs_recon`; build `cogs_recon`; pass `line_cogs_map` to `map_line_item`
- `detailView/app/adapters/outbound/duckdb/queries/order_header.sql` — add 6 columns

### Create (new)
- `detailView/app/adapters/outbound/duckdb/queries/order_line_cogs.sql`
- `detailView/app/adapters/outbound/duckdb/queries/order_cogs_recon.sql`
- Template partial/section for P&L waterfall panel (path depends on template engine used — locate existing order detail template before creating)

### Read-Only Reference (do not modify)
- `detailView/app/adapters/outbound/duckdb/queries/order_costs.sql` — PROMO_GOODS + OVERHEAD rows appear automatically; no edit needed
- `detailView/app/adapters/outbound/duckdb/queries/order_line_items.sql` — `variant_id` column needed; verify it is already projected
- `detailView/app/adapters/outbound/duckdb/row_coercion.py` — use existing `as_decimal`, `as_bool`, `as_str`, `as_float`

---

## Implementation Steps

### Pre-Requisites (hard gates — verify all before starting)
1. **Phase 05 complete and Dagster-green:** `fact_order_economics` has `allocated_overhead`, `fully_loaded_net_profit`, `promo_goods_cost`, `cogs_source`; `fact_order_costs` has PROMO_GOODS + OVERHEAD rows.
2. **Concurrent detailView customer stream merged:** Confirm with git log that `detailView/` has no open PRs or uncommitted changes from the customer work-stream. Check: `git log --oneline detailView/ | head -5` and confirm no pending branches touching these files.
3. **Serving views updated:** New columns visible in serving layer. Verify: query `fact_order_economics` via DuckDB and confirm `fully_loaded_net_profit` column exists.
4. **`fact_inventory_movements` view exists in serving layer:** Confirm bootstrap ran after phase 02/05 and `fact_inventory_movements` is a queryable view in `olap.duckdb`.
5. **Read `order_line_items.sql` to confirm `variant_id` is projected** — the line-COGS join key requires it.

### Step 1 — Verify Serving Columns
```bash
docker exec data_platform python -c "
import duckdb
con = duckdb.connect('/app/var/data_lake/serving/olap.duckdb', read_only=True)
cols = [r[0] for r in con.execute(\"SELECT column_name FROM information_schema.columns WHERE table_name='fact_order_economics'\").fetchall()]
print('New cols present:', [c for c in ['fully_loaded_net_profit','allocated_overhead','promo_goods_cost','cogs_source'] if c in cols])
con.close()
"
```
All 4 must appear before proceeding.

### Step 2 — Verify `variant_id` in `order_line_items.sql`
Check current SQL. If `variant_id` is not projected by `fact_sales`, add it (or join `dim_products` for `variant_id`). This is needed to build the `(sku, variant_id)` join key for per-line COGS.

### Step 3 — Create `order_line_cogs.sql`
Create `detailView/app/adapters/outbound/duckdb/queries/order_line_cogs.sql` with the SQL defined in the Architecture section. Parameter: `?` = `order_code` (document_code in fact_inventory_movements = order_code).

### Step 4 — Create `order_cogs_recon.sql`
Create `detailView/app/adapters/outbound/duckdb/queries/order_cogs_recon.sql` with the SQL defined in the Architecture section. Parameter: `?` = `order_id`.

### Step 5 — Update `order.py` (Domain)
- Add 6 fields to `OrderFinancial` (with `= None` defaults).
- Add `cogs_amount: Decimal | None = None` to `LineItem`.
- Add `cogs_margin` property to `LineItem`.
- Add `CogsReconPanel` dataclass (before `OrderDetail`).
- Add `cogs_recon: CogsReconPanel = field(default_factory=CogsReconPanel)` to `OrderDetail`.
- Update `quality_flags`: replace `if not self.financial.has_cogs:` with `if self.financial.cogs_source in (None, 'none'):`.
- Update `margin_is_verified` property.

No imports to add — `Decimal` already imported.

### Step 6 — Update `order_header.sql`
Add 6 columns to the SELECT after `foe.has_returns`:
```sql
    foe.cogs_source,
    foe.promo_goods_cost,
    foe.allocated_overhead,
    foe.is_overhead_estimated,
    foe.fully_loaded_net_profit,
    foe.fully_loaded_margin_pct,
```

### Step 7 — Update `order_mappers.py`
- Extend `map_financial` with 6 new fields.
- Update `map_line_item` signature to accept optional `cogs_map: dict | None = None`; look up `cogs_amount` by `(sku, variant_id)` key.
- Add `map_cogs_recon(row: Row) -> CogsReconPanel`.

### Step 8 — Update `order_repository.py`
In `get_by_code`:
1. Add `line_cogs_rows = _safe_fetch(conn, "order_line_cogs", [canonical_code])` after `line_rows`.
2. Add `cogs_recon_rows = _safe_fetch(conn, "order_cogs_recon", [order_id])` after line_cogs.
3. Build `line_cogs_map: dict[tuple, Decimal]` from `line_cogs_rows` keyed by `(sku, variant_id)` before constructing `OrderDetail`.
4. Update `OrderDetail` construction:
   - `line_items=[om.map_line_item(r, line_cogs_map) for r in line_rows]`
   - `cogs_recon=om.map_cogs_recon(cogs_recon_rows[0] if cogs_recon_rows else {})`

### Step 9 — Update HTML Template
Locate existing order detail template (find with `Glob detailView/app/**/*.html`). Add:
1. **P&L waterfall panel** — renders `financial.gross_profit → channel_net_profit → fully_loaded_net_profit` with margin %.
2. **`is_overhead_estimated` badge** — conditional "Estimated" badge next to overhead row.
3. **`cogs_source` badge** — near COGS row in financial summary.
4. **Per-line COGS column** — in line items table if any line has `cogs_amount`.
5. **COGS recon panel** — collapsible section showing `cogs_recon.sapo_mac_cogs` + source. Styled as info/audit section.
6. **Cost ledger label styling** — `PROMO_GOODS` and `OVERHEAD` categories get distinct CSS classes.

Use existing Jinja/template patterns; do not introduce new frontend dependencies.

### Step 10 — detailView Integration Test (Manual)
```bash
# detailView runs read-only on olap.duckdb — no restart needed for SQL/Python changes
# But if Docker image bakes templates (static assets), rebuild:
docker compose up -d --build detail_view
# Verify with a real order that has MISA COGS + Sapo-MAC data:
curl http://localhost:<detailview_port>/orders/<known_order_code>
```
Check in browser:
- P&L waterfall shows all 3 tiers.
- `cogs_source` badge visible.
- At least one line item has COGS if order is fulfilled.
- Overhead row shows "Estimated" or not per period.
- Cost ledger has PROMO_GOODS and OVERHEAD rows for relevant orders.

### Step 11 — Full Dagster Run (Regression)
Launch `transform_batch_nightly_job`. Confirm SUCCESS — this validates no upstream breakage from phase 05 + 06 combined. detailView reads from serving views that are populated by this run.

---

## Todo

- [ ] Verify concurrent detailView customer stream merged (git log check)
- [ ] Verify phase 05 Dagster-green + serving columns present (step 1)
- [ ] Confirm `variant_id` in `order_line_items.sql`; add if missing (step 2)
- [ ] Create `order_line_cogs.sql` (step 3)
- [ ] Create `order_cogs_recon.sql` (step 4)
- [ ] Update `order.py` — 6 new `OrderFinancial` fields, `LineItem.cogs_amount`, `CogsReconPanel` dataclass, `OrderDetail.cogs_recon`, `quality_flags` update, `margin_is_verified` update (step 5)
- [ ] Update `order_header.sql` — 6 new columns (step 6)
- [ ] Update `order_mappers.py` — `map_financial`, `map_line_item`, `map_cogs_recon` (step 7)
- [ ] Update `order_repository.py` — fetch line_cogs + cogs_recon, build line_cogs_map (step 8)
- [ ] Update HTML template — waterfall panel, badges, per-line COGS, recon panel (step 9)
- [ ] detailView manual integration test passes (step 10)
- [ ] Full Dagster nightly run SUCCESS (step 11)

---

## Success Criteria

1. **Dagster-green:** `transform_batch_nightly_job` SUCCESS (regression check — no broken upstreams).
2. **detailView renders without 500:** Order detail page loads for known orders. New panel and columns render; no stack traces.
3. **P&L waterfall complete:** `gross_profit`, `channel_net_profit`, `fully_loaded_net_profit` all visible in order detail for orders with overhead data.
4. **Per-line COGS visible:** At least one fulfilled order shows per-line `cogs_amount` in line items table.
5. **COGS source badge:** `cogs_source` badge renders for all orders (sapo_mac for fulfilled, none for edge cases).
6. **Graceful degradation:** Order detail for an order without overhead data (open month or no pool) renders without error; `fully_loaded_net_profit` section simply absent/null.
7. **`no_cogs` flag correct:** `quality_flags()` no longer fires warn for orders with Sapo-MAC COGS (`cogs_source='sapo_mac'`).
8. **No domain layer DuckDB imports:** `order.py` and `services.py` remain import-clean.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Concurrent customer stream not yet merged — merge conflict in `order.py` / templates | High | High — days of conflict resolution | Hard gate: do NOT start until `git log detailView/` confirms customer stream merged |
| `variant_id` not in `order_line_items.sql` / `fact_sales` serving view | Medium | Medium — line-COGS join key missing; fallback to sku-only join | Check in step 2 before creating SQL; adjust join key if needed |
| `fact_inventory_movements` view missing from `olap.duckdb` (bootstrap not run) | Low | Medium — `order_line_cogs` fetch fails, degrades to [] | `_safe_fetch` handles gracefully; verify in step 1 pre-req |
| Template baked into Docker image (not volume-mounted) | High (known) | Medium — edit not visible until rebuild | Memory note: always `docker compose up -d --build detail_view` after template edits |
| `order_cogs_recon.sql` returns empty for orders pre-dating phase 05 | Medium | Low — degrades to empty `CogsReconPanel` (all None) | `_safe_fetch` + `cogs_recon_rows[0] if cogs_recon_rows else {}` handles |
| `is_overhead_estimated = None` for orders without overhead data causes template error | Low | Low | Template must guard: `{% if financial.is_overhead_estimated is not none %}` |
| `map_line_item` signature change breaks existing tests that call it without `cogs_map` | Medium | Low | Use `cogs_map: dict \| None = None` default — backward compatible |

---

## Security / Data Integrity

- detailView is read-only: no write paths introduced. All new queries use `?` parameterised binding — no SQL injection risk.
- `order_line_cogs.sql` reads `fact_inventory_movements` with `order_code` filter — same data access pattern as existing queries. No PII exposure.
- `cogs_source` is a categorical string from the pipeline; no user input echoed.
- Template escaping: all new fields rendered via existing Jinja `{{ ... }}` auto-escape mechanism — no raw HTML injection.

---

## Next Steps

Phase 06 is the final phase of the unified Order P&L plan. After completion:
- Notify stakeholders that the full P&L waterfall (gross → contribution → fully-loaded) is live in both Metabase (phase 05) and detailView.
- Document MISA-632 vs Sapo-MAC variance expectation for finance team (variance is **expected**, not a bug — different cost basis and timing).
- Follow-up candidates (out of scope for this plan): richer recon panel using `mart_order_cogs_reconciliation` (if promoted from int_), carrier-cost integration, B2B wholesale-price-gap labelling.

---

## Unresolved Questions

1. **`mart_order_cogs_reconciliation` promotion:** Should `int_order_cogs_reconciled` be promoted to a `mart_` model so detailView can query per-line MISA-vs-Sapo variance directly? Without it, the recon panel is order-level only (no per-line variance). Decide before step 4 (affects `order_cogs_recon.sql` scope).
2. **`variant_id` in `fact_sales` serving view:** Does `order_line_items.sql` already project `variant_id`? If not, is `variant_id` available in `fact_sales`? Needed for the `(sku, variant_id)` COGS join key. Verify in step 2.
3. **Template engine and path:** Where is the order detail HTML template located? (Glob `detailView/app/**/*.html` before starting step 9.) Confirms whether partials/includes are used.
4. **`document_code` format in `fact_inventory_movements`:** Does it match `order_code` in `fact_orders` exactly (same case, same prefix)? Marketplace orders may have different codes. Verify with a spot-check query before deploying `order_line_cogs.sql`.
5. **`channel_net_profit` value shift communication:** Phase 05 fixes BUG-1, changing `channel_net_profit` by ~1.08B across historical data. detailView users will see the corrected (higher) channel_net_profit. Proactive stakeholder communication needed — coordinate timing with business team.
