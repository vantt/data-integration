# CANONICAL way to run dbt-metabase exposures — patches DEFAULT_SCHEMA to main_marts
"""
Wrapper that patches dbtmetabase.manifest.DEFAULT_SCHEMA to "main_marts" before
running the exposures extraction. Required because dbt-metabase defaults to "PUBLIC"
(PostgreSQL convention) but this project uses DuckDB with schema main_marts.
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
# NOTE: dbtmetabase._exposures does `from .manifest import DEFAULT_SCHEMA`, which
# creates a local name binding at import time. Patching manifest alone is not enough —
# we must patch both manifest AND _exposures after they are imported.
import dbtmetabase.manifest as _manifest_mod
import dbtmetabase._exposures as _exposures_mod

_TARGET_SCHEMA = "main_marts"
_manifest_mod.DEFAULT_SCHEMA = _TARGET_SCHEMA
_exposures_mod.DEFAULT_SCHEMA = _TARGET_SCHEMA
print(f"[patch] dbtmetabase.manifest.DEFAULT_SCHEMA  = {_TARGET_SCHEMA!r}")
print(f"[patch] dbtmetabase._exposures.DEFAULT_SCHEMA = {_TARGET_SCHEMA!r}")

# ── Now import the rest of dbtmetabase ────────────────────────────────────────
from dbtmetabase import DbtMetabase  # noqa: E402 (import after patch is intentional)

# ── Defaults ──────────────────────────────────────────────────────────────────
_DEFAULT_MANIFEST = "D:/Vantt/app/data-integration/transformation/target/manifest.json"
_DEFAULT_OUTPUT   = "D:/Vantt/app/data-integration/transformation"  # dbtmetabase writes {dir}/exposures.yml
_DEFAULT_URL      = "http://127.0.0.1:3001"


def _get_credentials() -> dict:
    """Return auth kwargs for DbtMetabase — prefer API key, fall back to username/password."""
    url     = os.environ.get("METABASE_URL", _DEFAULT_URL)
    api_key = os.environ.get("METABASE_API_KEY")
    username = os.environ.get("METABASE_USERNAME") or os.environ.get("METABASE_EMAIL")
    password = os.environ.get("METABASE_PASSWORD")
    return {"url": url, "api_key": api_key, "username": username, "password": password}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run dbt-metabase exposures with DEFAULT_SCHEMA=main_marts patch."
    )
    parser.add_argument("--manifest",    default=_DEFAULT_MANIFEST, help="Path to manifest.json")
    parser.add_argument("--output-path", default=_DEFAULT_OUTPUT,   help="Output exposures.yml path")
    args = parser.parse_args()

    creds = _get_credentials()
    url      = creds["url"]
    api_key  = creds["api_key"]
    username = creds["username"]
    password = creds["password"]

    # Validate: need either API key or username+password
    if not api_key and not username:
        print("ERROR: No Metabase credentials found. Set METABASE_API_KEY or METABASE_USERNAME/METABASE_EMAIL.", file=sys.stderr)
        sys.exit(1)
    if not api_key and username and not password:
        print("ERROR: METABASE_USERNAME set but METABASE_PASSWORD missing.", file=sys.stderr)
        sys.exit(1)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    auth_method = "api_key" if api_key else "username/password"
    print(f"[config] manifest   : {manifest_path}")
    print(f"[config] output     : {args.output_path}")
    print(f"[config] metabase   : {url}")
    print(f"[config] auth       : {auth_method}")

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

    client.extract_exposures(output_path=args.output_path)
    print(f"[done] Exposures written to {args.output_path}/exposures.yml")


if __name__ == "__main__":
    main()
