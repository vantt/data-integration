# CANONICAL way to run dbt-metabase models — patches DEFAULT_SCHEMA to main_marts
"""
Wrapper that patches dbtmetabase.manifest.DEFAULT_SCHEMA and dbtmetabase._models.DEFAULT_SCHEMA
to "main_marts" before running the models export. Required because dbt-metabase defaults to
"PUBLIC" (PostgreSQL convention) but this project uses DuckDB with schema main_marts.

Usage:
    C:/Python314/python.exe tools/run-dbt-metabase-models.py [--manifest PATH] [--database NAME]
"""
import argparse
import os
import sys
from pathlib import Path

# ── Load .env.local before touching any dbtmetabase modules ──────────────────
_ENV_FILE = Path("D:/Vantt/app/data-integration/.env.local")
if _ENV_FILE.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_ENV_FILE, override=False)
    except ImportError:
        # Manual parse fallback — dotenv not installed
        with open(_ENV_FILE, encoding="utf-8") as _fh:
            for _line in _fh:
                _line = _line.strip()
                if not _line or _line.startswith("#") or "=" not in _line:
                    continue
                _key, _, _val = _line.partition("=")
                _key = _key.strip()
                _val = _val.strip().strip('"').strip("'")
                if _key and _key not in os.environ:
                    os.environ[_key] = _val

# ── Patch DEFAULT_SCHEMA in ALL dbtmetabase modules that bind it ──────────────
# NOTE: dbtmetabase._models does `from .manifest import DEFAULT_SCHEMA`, which
# creates a local name binding at import time. Patching manifest alone is not enough —
# we must patch both manifest AND _models after they are imported.
import dbtmetabase.manifest as _manifest_mod
import dbtmetabase._models as _models_mod

_TARGET_SCHEMA = "main_marts"
_manifest_mod.DEFAULT_SCHEMA = _TARGET_SCHEMA
_models_mod.DEFAULT_SCHEMA = _TARGET_SCHEMA
print(f"[patch] dbtmetabase.manifest.DEFAULT_SCHEMA = {_TARGET_SCHEMA!r}")
print(f"[patch] dbtmetabase._models.DEFAULT_SCHEMA  = {_TARGET_SCHEMA!r}")

# ── Now import the rest of dbtmetabase ────────────────────────────────────────
from dbtmetabase import DbtMetabase, Filter  # noqa: E402 (import after patch is intentional)
from dbtmetabase.errors import MetabaseStateError  # noqa: E402

# ── Defaults ──────────────────────────────────────────────────────────────────
_DEFAULT_MANIFEST = "D:/Vantt/app/data-integration/transformation/target/manifest.json"
_DEFAULT_DATABASE = "Sapo"
_DEFAULT_URL      = "http://127.0.0.1:3001"


def _get_credentials() -> dict:
    """Return auth kwargs for DbtMetabase — prefer API key, fall back to username/password."""
    url      = os.environ.get("METABASE_URL", _DEFAULT_URL)
    api_key  = os.environ.get("METABASE_API_KEY")
    username = os.environ.get("METABASE_USERNAME") or os.environ.get("METABASE_EMAIL")
    password = os.environ.get("METABASE_PASSWORD")
    return {"url": url, "api_key": api_key, "username": username, "password": password}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run dbt-metabase models with DEFAULT_SCHEMA=main_marts patch."
    )
    parser.add_argument("--manifest",  default=_DEFAULT_MANIFEST, help="Path to manifest.json")
    parser.add_argument("--database",  default=_DEFAULT_DATABASE, help="Metabase database name")
    parser.add_argument("--sync-timeout", type=int, default=0,
                        help="Seconds to wait for Metabase schema sync (0 = skip). Default: 0 "
                             "(skip sync — Metabase only holds mart tables, staging tables "
                             "would cause sync to never complete)")
    parser.add_argument("--order-fields", action="store_true",
                        help="Preserve column order from dbt project")
    args = parser.parse_args()

    creds    = _get_credentials()
    url      = creds["url"]
    api_key  = creds["api_key"]
    username = creds["username"]
    password = creds["password"]

    # Validate: need either API key or username+password
    if not api_key and not username:
        print("ERROR: No Metabase credentials. Set METABASE_API_KEY or METABASE_USERNAME.", file=sys.stderr)
        sys.exit(1)
    if not api_key and username and not password:
        print("ERROR: METABASE_USERNAME set but METABASE_PASSWORD missing.", file=sys.stderr)
        sys.exit(1)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    auth_method = "api_key" if api_key else "username/password"
    print(f"[config] manifest      : {manifest_path}")
    print(f"[config] metabase      : {url}")
    print(f"[config] database      : {args.database}")
    print(f"[config] auth          : {auth_method}")
    print(f"[config] sync_timeout  : {args.sync_timeout}s {'(skip)' if args.sync_timeout == 0 else ''}")
    print(f"[config] schema_filter : main_marts only")

    client_kwargs: dict = dict(
        manifest_path=str(manifest_path),
        metabase_url=url,
    )
    if api_key:
        client_kwargs["metabase_api_key"] = api_key
    else:
        client_kwargs["metabase_username"] = username
        client_kwargs["metabase_password"] = password

    client = DbtMetabase(**client_kwargs)

    # schema_filter: only push main_marts — staging/source schemas don't exist in Metabase's
    # "Sapo" database. Without this filter the sync loop waits for staging tables that never
    # appear and raises MetabaseStateError("Unable to sync models with Metabase").
    #
    # model_filter: exclude dbt models that exist in the manifest but are NOT materialized as
    # views in the serving DuckDB (olap.duckdb main_marts schema). As of 2026-06:
    #   - dim_customers_base: intermediate dependency of dim_customers, not served
    #   - int_customer_metrics: intermediate computation node, not served
    _EXCLUDE_MODELS = ["dim_customers_base", "int_customer_metrics"]
    try:
        client.export_models(
            metabase_database=args.database,
            schema_filter=Filter(include=["main_marts"]),
            model_filter=Filter(exclude=_EXCLUDE_MODELS),
            sync_timeout=args.sync_timeout,
            order_fields=args.order_fields,
        )
        print("[done] Models exported to Metabase.")
    except MetabaseStateError as exc:
        msg = str(exc)
        if "Non-critical" in msg:
            # FK references to dim_customers_base.customer_key (not served as a view) cause
            # a success=False path inside dbtmetabase, but all table/field descriptions are
            # still written. Treat as warning, not fatal.
            print(f"[warn] {msg} — descriptions were still written; see above for details.")
            sys.exit(0)
        raise


if __name__ == "__main__":
    main()
