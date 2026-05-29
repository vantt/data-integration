"""FastAPI application factory (composition root entry point).

Run:  uvicorn app.main:app --host 0.0.0.0 --port 8000

Wires: config -> services (composition) -> web adapter, plus two lead-owned
cross-cutting routes plain enough to live here:
  - GET /healthz       liveness + schema presence (no parquet needed)
  - GET /api/orders/{code}, /api/customers/{id}   thin JSON mirror of the domain
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .adapters.inbound.web.web import register_web
from .adapters.outbound.duckdb import read_only_connection
from .composition import Services, build_services
from .config import Settings

# Views the app depends on — presence checked by /healthz.
_REQUIRED_VIEWS = ("fact_orders", "fact_order_economics", "dim_customers")


def _register_health(app: FastAPI, settings: Settings) -> None:
    @app.get("/healthz")
    def healthz():
        try:
            with read_only_connection(settings.olap_db_path) as con:
                rows = con.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_name = ANY(?)",
                    [list(_REQUIRED_VIEWS)],
                ).fetchall()
            present = {r[0] for r in rows}
            missing = [v for v in _REQUIRED_VIEWS if v not in present]
            if missing:
                return JSONResponse(
                    {"status": "degraded", "missing_views": missing}, status_code=503
                )
            return {"status": "ok", "db": settings.olap_db_path}
        except Exception as exc:  # noqa: BLE001 — surface any connect failure as 503
            return JSONResponse({"status": "down", "error": str(exc)}, status_code=503)


def _register_api(app: FastAPI, services: Services) -> None:
    @app.get("/api/orders/{order_code}")
    def api_order(order_code: str):
        order = services.order.get_detail(order_code)
        if order is None:
            return JSONResponse({"error": "not_found"}, status_code=404)
        return asdict(order)

    @app.get("/api/customers/{customer_id}")
    def api_customer(customer_id: str):
        customer = services.customer.get_detail(customer_id)
        if customer is None:
            return JSONResponse({"error": "not_found"}, status_code=404)
        return asdict(customer)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title=settings.title, docs_url="/api/docs", redoc_url=None)
    services = build_services(settings)

    _register_health(app, settings)
    _register_api(app, services)
    register_web(
        app,
        order_service=services.order,
        customer_service=services.customer,
        search_service=services.search,
    )
    return app


app = create_app()
