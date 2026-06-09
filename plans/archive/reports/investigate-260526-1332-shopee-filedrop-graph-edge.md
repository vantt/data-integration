# Shopee File-Drop: Asset Graph Edge Investigation

**Date:** 2026-05-26 | **Branch:** main

---

## TL;DR

`ingest_filedrop_shopee_job` **skips dbt entirely** on every sensor-triggered run. The sensor fires correctly, ingestion writes 4 parquet tables, but dbt never runs → dashboard never reflects the new Shopee data until the nightly batch at 03:00.

Root cause: `SapoDbtTranslator` has no mapping for `shopee_raw.*` sources → they keep default dbt keys → zero graph edges from `shopee_income_file_drop_asset` → `.downstream()` returns empty.

---

## Evidence

### Job definition (definitions.py:119-128)

```python
_shopee_source = AssetSelection.assets(shopee_assets.shopee_income_file_drop_asset)
ingest_filedrop_shopee_job = define_asset_job(
    selection=(
        _shopee_source
        | _shopee_source.downstream()           # ← returns EMPTY
        | AssetSelection.assets(serving.sapo_serving_db)
    ),
)
```

Effective selection = `shopee_income_file_drop_asset + sapo_serving_db`. dbt is absent.

### SapoDbtTranslator (dbt.py:26-53)

```python
elif source_name == "misa_raw":
    return AssetKey(["misa_amis", "misa_sales_file_drop_asset"])  # ✅ wired

# shopee_raw has 4 source tables → cannot share one asset key
# (Dagster requires unique keys per dbt resource). Shopee sources keep their default keys.
```

MISA is wired correctly. Shopee is not.

### dbt sources.yml: shopee has 4 tables

```yaml
- name: shopee_raw
  tables:
    - name: order_revenue
    - name: order_revenue_items
    - name: order_service_fees
    - name: order_adjustments
```

MISA has 1 table (`sales_lines`). This asymmetry caused the team to skip Shopee.

---

## False Constraint: "Cannot share one asset key"

The code comment is **incorrect**. In dagster-dbt, `get_asset_key()` for source nodes does NOT create a new Dagster asset — it returns the key of an **existing upstream asset** (a dependency reference). Multiple source nodes can point to the same upstream key. Dagster just draws multiple edges FROM the same upstream, not duplicate asset nodes.

Evidence: the `sapo_raw` case already maps `order`, `customer`, `account` to 3 different assets — same pattern works for mapping N sources to 1 asset.

MISA is a degenerate case (1:1), Shopee needs N:1 (4 sources → 1 ingestion asset). Both patterns are valid.

---

## Fix

**File:** `orchestration/assets/dbt.py`  
**Function:** `SapoDbtTranslator.get_asset_key()`

Add alongside the `misa_raw` case:

```python
elif source_name == "shopee_raw":
    # All 4 shopee_raw tables come from the same file-drop ingestion asset.
    # Multiple sources mapping to one upstream key is valid in dagster-dbt.
    return AssetKey(["shopee", "shopee_income_file_drop_asset"])
```

This creates 4 graph edges:
- `shopee_income_file_drop_asset` → `src_shopee_order_revenue`
- `shopee_income_file_drop_asset` → `src_shopee_order_revenue_items`
- `shopee_income_file_drop_asset` → `src_shopee_order_service_fees`
- `shopee_income_file_drop_asset` → `src_shopee_order_adjustments`

`_shopee_source.downstream()` will then resolve all dbt models downstream of these sources (stg → int → mart chain).

**Requires dbt manifest refresh** after this change (`dbt parse` or restart Dagster).

---

## Bonus: Same omission in sheets

```python
# Note: teams_raw and team_members_raw both come from sheets_team_config_asset
# but cannot share the same asset key — dependency omitted by design.
```

Same false constraint. `ingest_sheets_sync_job` misses `teams_raw`/`team_members_raw` downstreams. Impact is lower (team config rarely changes), but the pattern is broken.

Fix (optional, separate PR):
```python
elif name in ("teams_raw", "team_members_raw"):
    return AssetKey(["sheets", "sheets_team_config_asset"])
```

---

## Affected dbt models (Shopee chain)

```
shopee_income_file_drop_asset
  └─ src_shopee_order_revenue          ─┐
  └─ src_shopee_order_revenue_items     │
  └─ src_shopee_order_service_fees      ├→ stg_shopee_* → int_shopee_* → marts
  └─ src_shopee_order_adjustments      ─┘
```

Models discovered by glob: `stg_shopee_order_{revenue,revenue_items,service_fees,adjustments}`, `int_shopee_order_{items,fees,adjustments}`, `assert_shopee_net_settlement_matches_total_paid`.

---

## Risk Assessment

**Low risk.** The change is additive (maps existing keys, no new assets). The worst case: if multiple sources mapping to one key causes a dagster-dbt version-specific issue, the job falls back to its current broken state (which is the status quo). Can validate by running `dagster asset materialize --select shopee/shopee_income_file_drop_asset+` in staging.

---

## Unresolved Questions

- None. Root cause confirmed, fix is clear.
