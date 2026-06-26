import json
import os
import urllib.error
import urllib.request

from dagster import AssetExecutionContext, MetadataValue, Output, asset

from .serving import build_serving_db

# In-network address: `crm` and `data_platform` share docker network `caddy_net`,
# so DNS-by-container-name resolves. Override via env for local/native runs.
CRM_REFRESH_URL = os.environ.get("CRM_REFRESH_URL", "http://crm:8090/admin/refresh")

# Shared secret for POST /admin/refresh. Header is only sent when set, mirroring
# the CRM contract (unset token = endpoint unprotected). Never hardcode here —
# wired via .env.docker (same value as the `crm` service's CRM_REFRESH_TOKEN).
CRM_REFRESH_TOKEN = os.environ.get("CRM_REFRESH_TOKEN", "")

# Short timeout: the CRM endpoint is fire-and-forget (it starts the refresh on a
# background goroutine and returns 202 immediately), so this POST is just the
# handoff. A few seconds is plenty; anything slower means CRM is unreachable.
CRM_REFRESH_TIMEOUT_SEC = int(os.environ.get("CRM_REFRESH_TIMEOUT_SEC", "10"))


@asset(
    deps=[build_serving_db],
    group_name="reporting_layer",
    description=(
        "Triggers the CRM reverse-ETL refresh (POST /admin/refresh) after the "
        "serving layer (olap.duckdb) has been rebuilt, so the CRM cache reflects "
        "the latest warehouse data. Fire-and-forget: best-effort handoff only."
    ),
    # No retry_policy: this is a best-effort handoff. The CRM runs the refresh
    # async and we never fail the warehouse run on a CRM hiccup (see below), so
    # there is nothing for Dagster to retry.
)
def crm_cache_refresh(context: AssetExecutionContext):
    context.log.info("Triggering CRM reverse-ETL refresh (fire-and-forget)...")
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
        status = exc.code
        body_text = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
    except urllib.error.URLError as exc:
        # Connection refused / DNS failure / timeout.
        status = None
        body_text = f"unreachable: {exc.reason}"

    summary = _summarize_body(body_text)

    # fire-and-forget: CRM refresh is best-effort; never fail the warehouse run on
    # CRM errors. 200 (legacy sync), 202 (accepted async), and 409 (already
    # running) all mean the trigger landed. Anything else (401 auth, 5xx, timeout,
    # connection refused) is logged as a WARNING and we return success regardless.
    if status in (200, 202, 409):
        if status == 409:
            context.log.info(
                f"CRM refresh already running (HTTP 409) — trigger skipped. {summary}"
            )
            result_value = "CRM refresh skipped (already running)"
        else:
            context.log.info(
                f"CRM refresh triggered (HTTP {status}) — running async. {summary}"
            )
            result_value = "CRM refresh triggered"
    else:
        status_label = status if status is not None else "unreachable"
        context.log.warning(
            "CRM refresh trigger failed (HTTP %s) — ignored; warehouse pipeline "
            "is unaffected. %s" % (status_label, summary)
        )
        result_value = "CRM refresh trigger failed (ignored)"

    return Output(
        value=result_value,
        metadata={
            "http_status": status if status is not None else "unreachable",
            "response_body": MetadataValue.md(f"```json\n{body_text}\n```"),
        },
    )


CRM_BACKUP_URL = os.environ.get("CRM_BACKUP_URL", "http://crm:8090/admin/backup")
# Backup reads + checksums all rows then snapshots — seconds, not ms. Generous cap.
CRM_BACKUP_TIMEOUT_SEC = int(os.environ.get("CRM_BACKUP_TIMEOUT_SEC", "120"))


@asset(
    group_name="ops_maintenance",
    description=(
        "Daily CRM backup: POST /admin/backup → verified SQLite snapshot (crm/ops/backup_crm) "
        "to the crm_backups volume. Independent of the warehouse. FAILS LOUDLY on a backup-gate "
        "failure so the failure sensor alerts (silent backup stoppage is the zombie-run lesson)."
    ),
)
def crm_backup(context: AssetExecutionContext):
    context.log.info(f"Triggering CRM backup → {CRM_BACKUP_URL}")
    headers = {}
    if CRM_REFRESH_TOKEN:
        headers["X-Refresh-Token"] = CRM_REFRESH_TOKEN
    request = urllib.request.Request(CRM_BACKUP_URL, method="POST", headers=headers, data=b"")
    try:
        with urllib.request.urlopen(request, timeout=CRM_BACKUP_TIMEOUT_SEC) as resp:
            status, body_text = resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        body_text = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
    except urllib.error.URLError as exc:
        raise Exception(f"CRM backup unreachable: {exc.reason}")  # noqa: TRY002 — surface to Dagster

    if status != 200:
        # Unlike crm_cache_refresh (fire-and-forget), a failed BACKUP must red the run.
        raise Exception(f"CRM backup FAILED (HTTP {status}): {_summarize_body(body_text)}")  # noqa: TRY002
    context.log.info(f"CRM backup OK: {_summarize_body(body_text)}")
    return Output(
        value="CRM backup OK",
        metadata={"response_body": MetadataValue.md(f"```json\n{body_text}\n```")},
    )


CRM_DRILL_URL = os.environ.get("CRM_DRILL_URL", "http://crm_drill_runner:9000/run-drill")
# Same shared secret the crm_drill_runner sidecar enforces (root .env + .env.docker).
DRILL_TOKEN = os.environ.get("DRILL_TOKEN", "")
# The drill boots an ephemeral CRM + runs gates — up to a few minutes. Kept just above
# the sidecar's own DRILL_TIMEOUT (300s) so the sidecar returns a clean 504 first.
CRM_DRILL_TIMEOUT_SEC = int(os.environ.get("CRM_DRILL_TIMEOUT_SEC", "330"))


@asset(
    deps=[crm_backup],
    group_name="ops_maintenance",
    description=(
        "Restore-verify drill (runs after each backup): POST the crm_drill_runner sidecar "
        "(/run-drill) which boots an ephemeral CRM from the LATEST backup and asserts file "
        "integrity vs manifest + a functional read/write + prod-untouched. FAILS LOUDLY if "
        "the backup is not restorable — a backup isn't trusted until proven recoverable."
    ),
)
def crm_restore_verify(context: AssetExecutionContext):
    context.log.info(f"Triggering restore-verify drill → {CRM_DRILL_URL}")
    headers = {}
    if DRILL_TOKEN:
        headers["X-Drill-Token"] = DRILL_TOKEN
    request = urllib.request.Request(CRM_DRILL_URL, method="POST", headers=headers, data=b"")
    try:
        with urllib.request.urlopen(request, timeout=CRM_DRILL_TIMEOUT_SEC) as resp:
            status, body_text = resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        body_text = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
    except urllib.error.URLError as exc:
        raise Exception(f"drill-runner unreachable: {exc.reason}")  # noqa: TRY002 — surface to Dagster

    if status != 200:
        # A non-restorable backup MUST red the run so the failure sensor alerts.
        raise Exception(f"CRM restore-verify FAILED (HTTP {status}): {_summarize_body(body_text)}")  # noqa: TRY002
    context.log.info(f"CRM restore-verify PASS: {_summarize_body(body_text)}")
    return Output(
        value="CRM restore-verify PASS",
        metadata={"response_body": MetadataValue.md(f"```json\n{body_text}\n```")},
    )


def _summarize_body(body_text: str) -> str:
    """Best-effort one-line summary of the CRM JSON response for logs."""
    try:
        body = json.loads(body_text)
    except (ValueError, TypeError):
        return f"body={body_text[:200]}"
    parts = []
    for key in ("status", "started_at", "duration_ms", "output"):
        if key in body:
            parts.append(f"{key}={body[key]}")
    return " ".join(parts) if parts else f"body={body_text[:200]}"
