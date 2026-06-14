import json
import os
import urllib.error
import urllib.request

from dagster import AssetExecutionContext, MetadataValue, Output, RetryPolicy, asset

from .serving import build_serving_db

# In-network address: `crm` and `data_platform` share docker network `caddy_net`,
# so DNS-by-container-name resolves. Override via env for local/native runs.
CRM_REFRESH_URL = os.environ.get("CRM_REFRESH_URL", "http://crm:8090/admin/refresh")

# Shared secret for POST /admin/refresh. Header is only sent when set, mirroring
# the CRM contract (unset token = endpoint unprotected). Never hardcode here —
# wired via .env.docker (same value as the `crm` service's CRM_REFRESH_TOKEN).
CRM_REFRESH_TOKEN = os.environ.get("CRM_REFRESH_TOKEN", "")

# Generous timeout: the refresh is synchronous (~1s on current data) but the
# warehouse can grow, so allow ample headroom before treating it as a hang.
CRM_REFRESH_TIMEOUT_SEC = int(os.environ.get("CRM_REFRESH_TIMEOUT_SEC", "600"))


@asset(
    deps=[build_serving_db],
    group_name="reporting_layer",
    description=(
        "Triggers the CRM reverse-ETL refresh (POST /admin/refresh) after the "
        "serving layer (olap.duckdb) has been rebuilt, so the CRM cache reflects "
        "the latest warehouse data."
    ),
    # HTTP trigger to a separate container — transient network/restart blips are
    # worth a couple of automatic retries. No duckdb_lock key: this asset makes
    # an HTTP call and never touches DuckDB directly.
    retry_policy=RetryPolicy(max_retries=2),
)
def crm_cache_refresh(context: AssetExecutionContext):
    context.log.info("Triggering CRM reverse-ETL refresh...")
    context.log.info(f"   URL: {CRM_REFRESH_URL}")
    context.log.info(f"   Timeout: {CRM_REFRESH_TIMEOUT_SEC}s")
    context.log.info(f"   Auth header: {'set' if CRM_REFRESH_TOKEN else 'unset'}")

    headers = {}
    if CRM_REFRESH_TOKEN:
        headers["X-Refresh-Token"] = CRM_REFRESH_TOKEN

    request = urllib.request.Request(
        CRM_REFRESH_URL, method="POST", headers=headers, data=b""
    )

    status = None
    body_text = ""
    try:
        with urllib.request.urlopen(request, timeout=CRM_REFRESH_TIMEOUT_SEC) as resp:
            status = resp.status
            body_text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        # HTTPError covers all non-2xx responses. 409 (busy) is an expected,
        # non-fatal outcome — a refresh is already running, so this one is a
        # harmless skip. Everything else (401 auth, 5xx) is a real failure.
        status = exc.code
        body_text = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        if status != 409:
            raise Exception(
                f"CRM refresh failed with HTTP {status}. Body: {body_text[:500]}"
            ) from exc
    except urllib.error.URLError as exc:
        # Connection refused / DNS failure / timeout — raise so Dagster retries.
        raise Exception(
            f"CRM refresh could not reach {CRM_REFRESH_URL}: {exc.reason}"
        ) from exc

    summary = _summarize_body(body_text)

    if status == 409:
        context.log.info(
            f"CRM refresh already running (HTTP 409) — treated as success. {summary}"
        )
        result_value = "CRM refresh skipped (already running)"
    else:
        context.log.info(f"CRM refresh completed (HTTP {status}). {summary}")
        result_value = "CRM cache refreshed"

    return Output(
        value=result_value,
        metadata={
            "http_status": status,
            "response_body": MetadataValue.md(f"```json\n{body_text}\n```"),
        },
    )


def _summarize_body(body_text: str) -> str:
    """Best-effort one-line summary of the CRM JSON response for logs."""
    try:
        body = json.loads(body_text)
    except (ValueError, TypeError):
        return f"body={body_text[:200]}"
    parts = []
    for key in ("status", "duration_ms", "output"):
        if key in body:
            parts.append(f"{key}={body[key]}")
    return " ".join(parts) if parts else f"body={body_text[:200]}"
