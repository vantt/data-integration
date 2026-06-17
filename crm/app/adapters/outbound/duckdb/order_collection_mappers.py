"""Row-dict → domain entity mappers for CRM order child collections.

Each function maps one row from a per-collection query (LINE_ITEMS_SQL,
COSTS_SQL, PAYMENTS_SQL, RETURNS_SQL, SHIPMENTS_SQL, COGS_ITEMS_SQL).
Header-row mappers live in order_mappers.py (which also exports _s/_i/_f/_b).
"""
from __future__ import annotations

from crm.app.domain.entities.order import (
    CogsItem,
    CostRow,
    OrderLineItem,
    Payment,
    ReturnEvent,
    Shipment,
)
from .order_mappers import _b, _f, _i, _s


def map_line_item(row: dict) -> OrderLineItem:
    wg_raw = row.get("weight_grams")
    weight_grams: int | None = int(round(float(wg_raw))) if wg_raw is not None else None
    return OrderLineItem(
        order_line_id=_s(row, "order_line_id"),
        sku=_s(row, "sku"),
        product_name=_s(row, "product_name"),
        variant_name=_s(row, "variant_name"),
        brand_name=_s(row, "brand_name"),
        category=_s(row, "category"),
        unit=_s(row, "unit"),
        quantity=int(round(float(row.get("quantity") or 0))),
        revenue=_i(row, "revenue"),
        discount_amount=_i(row, "discount_amount"),
        distributed_discount_amount=_i(row, "distributed_discount_amount"),
        weight_grams=weight_grams,
    )


def map_cost_row(row: dict) -> CostRow:
    return CostRow(
        cost_type=_s(row, "cost_type"),
        cost_category=_s(row, "cost_category"),
        amount=_i(row, "amount"),
        discount_type=_s(row, "discount_type"),
        source_system=_s(row, "source_system"),
        source_record=_s(row, "source_record"),
        fee_source=_s(row, "fee_source"),
        discount_rate=_f(row, "discount_rate"),
    )


def map_payment(row: dict) -> Payment:
    return Payment(
        payment_method_name=_s(row, "payment_method_name"),
        payment_method_type=_s(row, "payment_method_type"),
        amount=_i(row, "amount"),
        status=_s(row, "status"),
        payment_timestamp=_s(row, "payment_timestamp"),
        paid_on=_s(row, "paid_on"),
    )


def map_return_event(row: dict) -> ReturnEvent:
    return ReturnEvent(
        return_date=_s(row, "return_date"),
        refund_amount=_i(row, "refund_amount"),
        return_quantity=int(row.get("return_quantity") or 0),
        return_status=_s(row, "return_status"),
        refund_status=_s(row, "refund_status"),
        return_reason=_s(row, "return_reason"),
    )


def map_shipment(row: dict) -> Shipment:
    return Shipment(
        fulfillment_id=_s(row, "fulfillment_id"),
        fulfillment_code=_s(row, "fulfillment_code"),
        tracking_code=_s(row, "tracking_code"),
        carrier_id=_s(row, "carrier_id"),
        shipping_service=_s(row, "shipping_service"),
        status=_s(row, "status"),
        cod_amount=_i(row, "cod_amount"),
        created_at=_s(row, "created_at"),
        shipped_at=_s(row, "shipped_at"),
    )


def map_cogs_item(row: dict) -> CogsItem:
    return CogsItem(
        sku=_s(row, "sku"),
        variant_id=_s(row, "variant_id"),
        cogs_goods_sapo=_i(row, "cogs_goods_sapo"),
        cogs_goods_misa=_i(row, "cogs_goods_misa"),
        cogs_goods_primary=_i(row, "cogs_goods_primary"),
        cogs_source=_s(row, "cogs_source"),
        qty_sapo=float(row.get("qty_sapo") or 0.0),
        is_promo=_b(row, "is_promo"),
        is_gift_no_invoice=_b(row, "is_gift_no_invoice"),
    )
