"""Demo stub — hand-built domain objects + stub services for local template verification.

Usage (from detailView/ directory):
    uvicorn app.adapters.inbound.web._demo_stub:app --reload

This file is within the web adapter's ownership boundary and is NOT imported
in production. The composition root uses real services.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import FastAPI

from app.domain.customer import (
    CustomerBehavior,
    CustomerDetail,
    CustomerProfile,
    CustomerValueMetrics,
    OrderSummary,
    StatusSnapshot,
)
from app.domain.order import (
    ChannelInfo,
    CostRow,
    CustomerRef,
    LineItem,
    OrderDetail,
    OrderFinancial,
    OrderHeader,
    Payment,
    ReturnEvent,
    ShippingInfo,
    StaffInfo,
)
from app.domain.shared import SearchResolution, CustomerHit

from .web import register_web

# ---------------------------------------------------------------------------
# Sample datetimes
# ---------------------------------------------------------------------------
_DT_CREATED  = datetime(2026, 5, 18, 7, 20, tzinfo=timezone.utc)  # 14:20 ICT
_DT_SHIPPED  = datetime(2026, 5, 19, 4, 0,  tzinfo=timezone.utc)  # 11:00 ICT
_DT_UPDATED  = datetime(2026, 5, 21, 5, 0,  tzinfo=timezone.utc)  # 12:00 ICT

# ---------------------------------------------------------------------------
# Stub order
# ---------------------------------------------------------------------------
_STUB_ORDER = OrderDetail(
    header=OrderHeader(
        order_code="HD00123",
        order_id=4821,
        status="COMPLETED",
        payment_status="PAID",
        fulfillment_status="SHIPPED_COD",
        created_at=_DT_CREATED,
        first_shipped_at=_DT_SHIPPED,
        updated_at=_DT_UPDATED,
        time_to_complete_hours=70,
    ),
    financial=OrderFinancial(
        gross_revenue=Decimal("1400000"),
        discount_amount=Decimal("150000"),
        net_revenue=Decimal("1250000"),
        tax_amount=Decimal("100000"),
        total_collected=Decimal("1350000"),
        cogs_amount=Decimal("870000"),
        gross_profit=Decimal("380000"),
        gross_margin_pct=0.304,
        shopee_platform_fees=Decimal("40000"),
        shopee_infra_fee=Decimal("10000"),
        shopee_voucher_xtra_fee=Decimal("5000"),
        shopee_taxes=Decimal("5000"),
        shopee_net_settlement=Decimal("320000"),
        channel_net_profit=Decimal("320000"),
        channel_net_margin_pct=0.256,
        cod_amount=Decimal("1350000"),
        carrier_id="GHN",
        return_amount=Decimal("0"),
        return_count=0,
        has_cogs=True,
        has_platform_fees=True,
        has_returns=False,
        is_us=False,
    ),
    line_items=[
        LineItem(
            order_line_id=1, sku="A-01", product_name="Kem dưỡng da 50ml",
            variant_name="Vanilla", brand_name="FINE", category="Skincare",
            unit="hộp", quantity=2, revenue=Decimal("600000"),
            discount_amount=Decimal("0"), distributed_discount_amount=Decimal("75000"),
            weight_grams=Decimal("120"),
        ),
        LineItem(
            order_line_id=2, sku="B-12", product_name="Serum vitamin C",
            variant_name="Large 50ml", brand_name="FG", category="Skincare",
            unit="hộp", quantity=1, revenue=Decimal("650000"),
            discount_amount=Decimal("150000"), distributed_discount_amount=Decimal("75000"),
            weight_grams=Decimal("80"),
        ),
    ],
    cost_ledger=[
        CostRow(cost_type="cogs", cost_category="COGS",
                amount=Decimal("870000"), fee_source="actual",
                source_system="MISA", source_record="HD00123"),
        CostRow(cost_type="platform_service", cost_category="PLATFORM_FEE",
                amount=Decimal("40000"), fee_source="estimated",
                source_system="Shopee", source_record="SHP-001"),
    ],
    payments=[
        Payment(
            payment_method_name="COD", payment_method_type="COD",
            amount=Decimal("1350000"), status="PAID",
            payment_timestamp=_DT_SHIPPED,
            paid_on=_DT_UPDATED,
        ),
    ],
    returns=[],
    channel=ChannelInfo(
        channel_name="Shopee Mall", channel_code="SHP-MALL",
        channel_category="Marketplace", channel_format="Online",
        platform="Shopee", channel_brand="FINE", market="Domestic",
        promotion_code="SALE520", max_discount_rate=Decimal("0.12"),
        primary_discount_type="bundle",
    ),
    staff=StaffInfo(
        seller_name="Nguyễn Linh", seller_email="linh@example.com",
        creator_name="Trần Anh", team_name="Team A", branch_name="HCM-01",
    ),
    shipping=ShippingInfo(
        province="Hồ Chí Minh", district="Quận 1",
        ward="Phường Bến Nghé", country="VN",
        address="123 Lê Lợi",
    ),
    customer=CustomerRef(
        customer_id="C7781",
        full_name="Nguyễn Thị A",
        customer_type="RETAIL",
        value_group="VALUE_VIP",
        lifetime_value=Decimal("52000000"),
    ),
)

# ---------------------------------------------------------------------------
# Stub customer
# ---------------------------------------------------------------------------
_STUB_CUSTOMER = CustomerDetail(
    profile=CustomerProfile(
        customer_id="C7781",
        full_name="Nguyễn Thị A",
        phone="0912345678",
        email="a.nguyen@example.com",
        address1="123 Lê Lợi",
        ward="Phường Bến Nghé",
        district="Quận 1",
        province="Hồ Chí Minh",
        country="VN",
        geo_region="HCM",
        loyalty_point=1200,
        customer_type="RETAIL",
        customer_group="VIP",
        created_at=datetime(2024, 1, 5, tzinfo=timezone.utc),
    ),
    value_metrics=CustomerValueMetrics(
        lifetime_value=Decimal("52000000"),
        total_orders_count=24,
        value_group="VALUE_VIP",
        total_gross_profit=Decimal("15000000"),
        total_cogs=Decimal("30000000"),
        avg_gross_margin_pct=0.29,
        total_return_amount=Decimal("500000"),
        return_count=2,
        cogs_order_count=16,
    ),
    behavior=CustomerBehavior(
        recency_days=12,
        frequency=24,
        monetary=Decimal("52000000"),
        lifecycle_stage="LIFECYCLE_ACTIVE",
        channel_preference="CHANNEL_SHOPEE",
        product_affinity="PRODUCT_FINE_JAPAN",
        payment_behavior="PAYMENT_COD",
        geo_region="GEO_HCMC",
        customer_type="RETAIL",
        first_order_date=datetime(2024, 2, 14, tzinfo=timezone.utc),
        last_order_date=_DT_CREATED,
        lifespan_days=820,
    ),
    status_timeline=[
        StatusSnapshot(
            snapshot_month=__import__("datetime").date(2025, m, 1),
            status=s, is_new=(m == 2 and s == "ACTIVE"), days_since_last_order=d,
            value_group="VALUE_VIP",
        )
        for m, s, d in [
            (2, "ACTIVE", 5), (3, "ACTIVE", 10), (4, "ACTIVE", 8),
            (5, "ACTIVE", 12), (6, "ACTIVE", 7), (7, "AT_RISK", 45),
            (8, "ACTIVE", 9), (9, "ACTIVE", 11), (10, "ACTIVE", 6),
            (11, "ACTIVE", 14), (12, "AT_RISK", 50), (1, "CHURNED", 90),
        ]
    ],
    order_history=[
        OrderSummary(
            order_code="HD00123",
            order_date=_DT_CREATED,
            status="COMPLETED",
            channel_name="Shopee Mall",
            seller_name="Nguyễn Linh",
            total_collected=Decimal("1350000"),
            gross_profit=Decimal("380000"),
            gross_margin_pct=0.304,
            payment_label="COD",
            has_return=False,
            carrier_id="GHN",
        ),
        OrderSummary(
            order_code="HD00098",
            order_date=datetime(2026, 4, 2, tzinfo=timezone.utc),
            status="COMPLETED",
            channel_name="Facebook",
            seller_name="Nguyễn Linh",
            total_collected=Decimal("820000"),
            gross_profit=Decimal("210000"),
            gross_margin_pct=0.256,
            payment_label="Prepaid",
            has_return=True,
            carrier_id="GHTK",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Stub services (duck-typed — match the service interface)
# ---------------------------------------------------------------------------
class _StubOrderService:
    def get_detail(self, order_code: str):
        if order_code.upper() == "HD00123":
            return _STUB_ORDER
        return None


class _StubCustomerService:
    def get_detail(self, customer_id: str):
        if customer_id in ("C7781", "c7781"):
            return _STUB_CUSTOMER
        return None


class _StubSearchService:
    def resolve(self, mode: str, query: str) -> SearchResolution:
        q = (query or "").strip().upper()
        if mode == "order":
            if q == "HD00123":
                return SearchResolution(redirect_to="/orders/HD00123")
            return SearchResolution(not_found=True)
        # customer
        if q in ("C7781", "0912345678", "A.NGUYEN@EXAMPLE.COM"):
            return SearchResolution(redirect_to="/customers/C7781")
        if q == "NGUYEN":
            return SearchResolution(customer_hits=[
                CustomerHit("C7781", "Nguyễn Thị A", "0912345678", "VALUE_VIP"),
                CustomerHit("C7782", "Nguyễn Văn B", "0987654321", "VALUE_GOLD"),
            ])
        return SearchResolution(not_found=True)


# ---------------------------------------------------------------------------
# FastAPI app wired with stub services — used only for demo/dev
# ---------------------------------------------------------------------------
app = FastAPI(title="detailView — demo")

register_web(
    app,
    order_service=_StubOrderService(),
    customer_service=_StubCustomerService(),
    search_service=_StubSearchService(),
)
