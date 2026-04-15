# Migration Report — Channel Taxonomy Rename

**Date:** 2026-04-15 12:21 → 13:10 Asia/Saigon
**Branch:** `refactor/channel-taxonomy-rename`
**Plan:** `plans/260415-1221-channel-taxonomy-rename/plan.md`
**Commits:** 4 (preceded by 1 staff-attribution refactor moved to main)

## Outcome

All acceptance criteria met. Clean atomic migration across 4 layers (seed, dbt, Rill, docs) + Metabase.

## Final Naming

| Tier | Column | Values |
|------|--------|--------|
| 1 | `channel_category` | `Online-Ecommerce` / `Offline` / `Internal` |
| 2 | `channel_format` (renamed from `platform_group`) | `Marketplace` / `Social` / `Web` / `Retail` / `B2B` / `Direct` / `System` / `CrossBorder Fulfillment` / `Other` |
| 3 | `platform` | Shopee / Lazada / TikTok / ... |
| 4 | `channel_name` (kept — `storefront` is conceptual label only) | Sapo `order_source.source_name` 1:1 |

Telesale & CS moved Internal/System → Offline/Direct (is_sales_channel=true).
Marketing-spend derived bucket renamed `channel_group` → `marketing_spend_bucket`.

## Commits

1. `470b786 refactor(taxonomy): rename platform_group→channel_format, value Ecommerce→Online-Ecommerce` — seed + dbt core (8 files)
2. `26ec0ae refactor(taxonomy): propagate channel_format to Rill layer` — 3 Rill files
3. `579e69d docs(taxonomy): sync handbook/dictionaries/skills to channel_format + Online-Ecommerce` — 25 doc files + plan artifact
4. *(Metabase)* — 35 cards updated live via API (log: `plans/260415-1221-channel-taxonomy-rename/metabase-update-log.txt`); not a git commit, runtime DB mutation

## Verification

### dbt
- `dbt seed --full-refresh` → `ref_order_sources` 46 rows, PASS
- `dbt build --select dim_channels+` → 3 models + 7 tests, ALL PASS
- `dbt build --select +fact_orders +fact_sales` → 70 tests PASS
- `accepted_values` tests pass for both `channel_category` and `channel_format`

### dim_channels distribution (after build)
| channel_category | channel_format | n | is_sales_channel |
|---|---|---:|---|
| Internal | CrossBorder Fulfillment | 1 | false |
| Internal | Other | 3 | false |
| Internal | System | 3 | false |
| Offline | B2B | 2 | true |
| Offline | Direct | 2 | true |
| Offline | Retail | 6 | true |
| Online-Ecommerce | Marketplace | 28 | true |
| Online-Ecommerce | Social | 5 | true |
| Online-Ecommerce | Web | 2 | true |

All 9 channel_format values present, distributed correctly across 3 channel_category values.

### Rill
- Restarted with clean state → all 10 src_ models reconciled; 3 enriched models + 3 metrics_views + 3 explores reconciled clean (no warn/error).
- Marketing-spend `marketing_spend_bucket` dimension renamed.

### Metabase (live API)
- 629 cards scanned; 35 matched (platform_group SQL, 'Ecommerce' value, or series_settings).
- All 35 updated via PUT /api/card: 32 SQL + 3 visualization_settings.
- Rescan post-update: 0 `platform_group` remaining; remaining `Ecommerce` hits are correct `'Online-Ecommerce'` substrings or KPI display labels ("Ecom Share %" card title).

### Grep acceptance
- `platform_group` in `transformation/ rill/ scripts/ ingestion/` → only in `logs/` (gitignored) and `target/` (gitignored)
- `platform_group` in `docs/ .skills/` → only in `channel-classification.md` intentional historical rename notes (2 lines, lines 117 + 886)
- `'Ecom'` / `'Ecommerce'` as literal value → 0 hits in live code

## Edge cases / surprises

- **Rill cache staleness:** first restart after schema change surfaced stale parquet binding. Required clearing `rill/tmp` and full restart; automatic watcher did not refresh catalog on parquet schema change.
- **dbt seed schema mismatch on re-seed:** `dbt seed` without `--full-refresh` loaded into legacy table → model failed to find `channel_format`. Fixed by `--full-refresh`.
- **Pre-existing bug in `ANALYTICS_2SKILL_SPEC.md`:** filter `channel_category != 'US'` — US was never a valid channel_category value (it's Tier-3 `platform`). Replaced with semantically-correct `is_sales_channel = true` across 9 call sites.
- **`channel_classification_implementation_prompt.md` bug:** `is_sales_channel = platform_group != 'System'` was incomplete (missed CrossBorder, Other). Corrected to `channel_format NOT IN ('System', 'CrossBorder Fulfillment', 'Other')`.
- **Metabase `visualization_settings.series_settings`:** keys = actual data values; had to patch these separately from SQL (3 cards: #898, #247, #262).
- **Staff attribution refactor unrelated:** 22 files of staff `seller_staff_key`/`creator_staff_key` work were on the working tree at session start. Moved to main as commit `003c65d` before starting taxonomy work to keep PR single-concern.

## Post-commit: Blueprint redeploy (forward-only flow)

After initial live-API patch, followed up with **blueprint-as-SoT redeploy** to make the migration durable across Metabase DB restores:

- Ran `deploy_from_markdown.js` on all 24 blueprints in `docs/analytics-handbook/blueprints/*.md` sequentially.
- Script is idempotent (matches card by tab+name, reuses ID). All 24 → "Deployment Complete". No duplicates.
- **Post-redeploy rescan (629 cards):** 0 `platform_group`, 0 `'Ecommerce'/'Ecom'` value literals; 28 cards use `channel_format`; 7 use `Online-Ecommerce`.
- Per-file deploy logs at `plans/260415-1221-channel-taxonomy-rename/deploy-logs/*.log` (gitignored via `*.log`).

**Caveat noted during redeploy:** `deploy_from_markdown.js --dry-run` flag is documented but **not implemented** — first invocation deployed live. Same-content idempotent overwrite, no harm. Suggest wiring a real dry-run flag as a follow-up.

## Post-deploy fix: stale serving views

Encountered after blueprint redeploy when Metabase tried to query dim_channels:

```
Binder Error: Contents of view were altered: names don't match!
Expected [..., platform_group, ...] but found [..., channel_format, ...]
```

**Cause:** DuckDB serving views in `data_lake/serving/olap.duckdb` (consumed by Metabase) cache the column list at CREATE time. When dbt wrote new parquet with `channel_format`, the view still expected `platform_group` → binder mismatch at query time. Applies to any column-renaming migration touching dim/fact parquet.

**Fix:** `python scripts/provisioning/bootstrap_serving_views.py` (idempotent, uses CREATE OR REPLACE). Must stop Metabase first because DuckDB held a PID 0 lock on the file despite Metabase's `read_only=True` — a DuckDB/Metabase JDBC quirk not reflected in the script's docstring claim that read_only coexists. Restart Metabase after.

Add to runbook for future column renames: **after `dbt build` + `refresh_rolling`, always rerun `bootstrap_serving_views.py` when a mart column changed name or was dropped.**

**Second binder-error class encountered (types-mismatch, not names):** After rebuilding views, some cards still threw `Binder Error: Contents of view were altered: types don't match`. Two separate caches needed clearing:

1. **Metabase JDBC connection pool** — pooled connections retain view schema from the moment they were opened. A brief `docker restart metabase && sleep 3` is insufficient; the pool only fully recreates on cold Metabase startup (~30-60s). Fix: cold restart, then poll `/api/health` until `{status: "ok"}` before proceeding.
2. **Metabase field metadata cache** — app-layer cache of column names/types per table. Fix: `POST /api/database/{id}/sync_schema`.

Updated runbook (final):

```
dbt build
python scripts/provisioning/refresh_rolling.py
docker stop metabase
python scripts/provisioning/bootstrap_serving_views.py
docker start metabase
# wait for /api/health == ok
curl -X POST -H "x-api-key: $KEY" $URL/api/database/{id}/sync_schema
docker restart rill   # if schema-affecting
# then redeploy blueprints
```

## Artifacts

- Plan: `plans/260415-1221-channel-taxonomy-rename/plan.md`
- Metabase one-shot update script (kept for future ad-hoc use): `plans/260415-1221-channel-taxonomy-rename/update-metabase-cards.py`
- Metabase per-card log (first pass): `plans/260415-1221-channel-taxonomy-rename/metabase-update-log.txt`
- Blueprint redeploy logs: `plans/260415-1221-channel-taxonomy-rename/deploy-logs/`

## Unresolved questions

- Rill metric views `orders_core_metrics.yaml` and `sales_items_core_metrics.yaml` **do not expose `channel_format` as a dimension** (they never did). Per YAGNI, not added. If dashboards need to filter/group by Tier 2 in Rill, add later.
- Metabase cards edits are in H2 DB (`metabase.db.mv.db`) — not version-controlled. If the Metabase DB is rebuilt from snapshot, these updates will be lost. Consider scripting this into `bootstrap_reporting.py` as a one-shot migration or snapshotting current state.
- `docs/analytics-handbook/blueprints/*` display labels still use "Ecom Share %" / "Ecom" as KPI nicknames (business-facing). Left intentionally; if finance wants consistent labels, do a separate pass.
