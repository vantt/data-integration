"""Asset checks registry for ingestion health monitoring.

Iterates ingestion_sla.yaml and builds check lists for every registered asset.
`ALL_CHECKS` is imported by orchestration/definitions.py.

Check factories return None for inapplicable assets (e.g. cursor checks on
file-drop assets) — those are filtered out before appending to ALL_CHECKS.
"""
from __future__ import annotations

import logging
from typing import Any

from dagster import AssetChecksDefinition

from orchestration.asset_checks.cursor_checks import make_cursor_stall_check
from orchestration.asset_checks.freshness_checks import make_freshness_check
from orchestration.asset_checks.row_trend_checks import make_not_empty_check, make_row_trend_check
from orchestration.asset_checks.sla_loader import list_asset_keys

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Asset def registry: maps asset_key_str → Dagster asset object.
# Import only the asset objects (not the full module side-effects) so this
# module stays lightweight and doesn't drag in dlt/ingestion heavy deps.
# ---------------------------------------------------------------------------
def _build_asset_def_map() -> dict[str, Any]:
    from orchestration.assets import (  # noqa: PLC0415  (deferred import — intentional)
        misa_amis_assets,
        sapo_assets,
        sheets_assets,
        shopee_assets,
    )

    return {
        "sapo/sapo_webhook_consumer_asset": sapo_assets.sapo_webhook_consumer_asset,
        "sapo/sapo_history_log_asset": sapo_assets.sapo_history_log_asset,
        "sapo/sapo_orders_batch_asset": sapo_assets.sapo_orders_batch_asset,
        "sapo/sapo_customers_batch_asset": sapo_assets.sapo_customers_batch_asset,
        "sapo/sapo_accounts_batch_asset": sapo_assets.sapo_accounts_batch_asset,
        "sapo/sapo_products_batch_asset": sapo_assets.sapo_products_batch_asset,
        "shopee/shopee_income_file_drop_asset": shopee_assets.shopee_income_file_drop_asset,
        "misa_amis/misa_sales_file_drop_asset": misa_amis_assets.misa_sales_file_drop_asset,
        "sheets/sheets_targets_asset": sheets_assets.sheets_targets_asset,
        "sheets/sheets_marketing_spend_asset": sheets_assets.sheets_marketing_spend_asset,
    }


def _build_all_checks() -> list[AssetChecksDefinition]:
    asset_def_map = _build_asset_def_map()
    checks: list[AssetChecksDefinition] = []

    for asset_key_str in list_asset_keys():
        asset_def = asset_def_map.get(asset_key_str)
        if asset_def is None:
            _log.warning(
                "Asset key '%s' in ingestion_sla.yaml has no registered asset def — skipping checks.",
                asset_key_str,
            )
            continue

        # 1. Freshness check (always)
        checks.append(make_freshness_check(asset_def, asset_key_str))

        # 2. Not-empty check (always)
        checks.append(make_not_empty_check(asset_def, asset_key_str))

        # 3. Row trend check (skipped when trend_min_ratio=null)
        trend = make_row_trend_check(asset_def, asset_key_str)
        if trend is not None:
            checks.append(trend)

        # 4. Cursor stall check (Sapo incremental/batch only)
        cursor = make_cursor_stall_check(asset_def, asset_key_str)
        if cursor is not None:
            checks.append(cursor)

    _log.info("Registered %d asset checks across %d assets.", len(checks), len(list_asset_keys()))
    return checks


ALL_CHECKS: list[AssetChecksDefinition] = _build_all_checks()
