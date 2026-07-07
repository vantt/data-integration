# Phase 1 — GCP Service Account + Centralized Auth Helper

**Depends on:** none (human/GCP step first)
**Blocks:** phase-02, phase-03

## Context

Both needs (5 read-only sheets currently public-link, 1 sheet needing Editor write) are blocked on the same missing piece: no Google service-account credential exists in this repo. `ingestion/requirements.txt` already lists `gspread` (added for the budget write-back, unused until now). One SA, shared at different privilege levels per sheet, removes the duplicate setup.

## Steps — human/GCP (outside this repo, cannot be automated)

1. Create or reuse a GCP project; enable the **Google Sheets API** (and Drive API — `gspread.open_by_url` needs it to resolve the URL to a file).
2. Create a service account under that project; generate + download a JSON key. Note the SA's email (`...@...iam.gserviceaccount.com`).
3. Share each sheet with the SA email:
   - **Editor**: budget sheet (`SOURCES__SPREADSHEET_URL__BUDGET`) — needs write for phase-03.
   - **Viewer**: the other 5 (`MARKETING_SPEND`, `TARGETS`, `TEAM_CONFIG`, `US_SHIPMENT_PRICES`, `OVERHEAD_CLASSIFICATION`).
   - Do **not** grant Editor broadly — scope Editor to exactly the budget sheet (risk noted in plan.md).
4. Place the JSON key at `app_data/secrets/gsheets-service-account.json` (host). `app_data/` is already fully gitignored (`.gitignore:11`) — no new ignore rule needed, and this matches the repo's existing pattern of persistent/private files living under `./app_data/<name>`, bind-mounted into containers (`data_lake`, `dagster_home`, `backups`, etc. all follow this shape; there's no prior Docker-secret-file pattern to match against, and Swarm-style `secrets:` is overkill for single-host compose).
5. Do **not** turn off "Anyone with link" on the 5 read sheets yet — that happens at the end of phase-02, after SA-based reads are verified working. Leaves a safe rollback window.

## Mount + env wiring

**`docker-compose.yml`** — add to `data_platform.volumes` (same shape as every other `./app_data/X:/app/var/X` line already there):
```yaml
- ./app_data/secrets:/app/var/secrets:ro
```

**`.env.docker`** (container — real value, gitignored file):
```
GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH=/app/var/secrets/gsheets-service-account.json
```

**`.env.local`** (Windows-native run — real value, gitignored file; every `gsheet_*` script already calls `_load_dotenv_local()` so this needs no new loader code):
```
GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH=D:\Vantt\app\data-integration\app_data\secrets\gsheets-service-account.json
```

One physical file, two paths (container path vs host path) under the same env var name — same env-var-same-name-different-value-per-environment shape already used for every other setting in this repo.

Only `data_platform` needs this mount — `metabase`/`rill`/`evidence`/`crm` don't run any `gsheet_*` code.

**Before first real use:** confirm `scripts/backup/backup.sh` does not glob `app_data/secrets/` into any backup archive (the archived hardening plan already flagged this script for verbatim-copying `.env.docker` into backups — same risk class applies to a credential file; exclude it the same way if it's not already scoped to specific subdirs).

## Code — centralized auth helper

New module `ingestion/src/gsheet_auth.py` (single source of the `gspread` client + generic fetch, used by phase-02 and phase-03):

```python
import os
import pandas as pd

GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH_ENV = "GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH"


def get_gspread_client():
    """Authenticated gspread client. Raises RuntimeError with setup instructions if
    the key path env var is unset/missing, or if gspread isn't installed — mirrors the
    existing lazy-import pattern in gsheet_budget_sync/sheet_writeback.py so module import
    always succeeds regardless of GCP setup state."""
    key_path = os.environ.get(GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH_ENV, "").strip()
    if not key_path:
        raise RuntimeError(
            f"{GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH_ENV} chưa được cấu hình — xem "
            f"plans/260707-1201-google-sheets-service-account/phase-01-service-account-setup.md"
        )
    if not os.path.exists(key_path):
        raise RuntimeError(f"Service account key không tồn tại tại {key_path}")
    import gspread
    return gspread.service_account(filename=key_path)


def fetch_tab_as_dataframe(sheet_url: str, gid: str) -> pd.DataFrame:
    """One worksheet (by gid) -> raw all-string DataFrame, header=None (row 0 = header
    row as data), matching the shape gsheet_budget_sync.fetch._fetch_tab_csv already
    returns — so callers that expect that raw-grid shape need zero downstream changes."""
    gc = get_gspread_client()
    sh = gc.open_by_url(sheet_url)
    ws = sh.get_worksheet_by_id(int(gid))
    values = ws.get_all_values()
    return pd.DataFrame(values)


def fetch_workbook_tabs(sheet_url: str) -> dict:
    """All tabs by name -> {tab_name: DataFrame with row 0 as column headers}. For
    multi-tab-by-name readers (team_config), replacing pd.read_excel(sheet_name=name)."""
    gc = get_gspread_client()
    sh = gc.open_by_url(sheet_url)
    result = {}
    for ws in sh.worksheets():
        values = ws.get_all_values()
        if not values:
            continue
        header, *rows = values
        result[ws.title] = pd.DataFrame(rows, columns=header)
    return result
```

Two fetch shapes because the 5 readers split into two access patterns today:
- gid-targeted CSV export (`marketing_spend`, `targets`, `us_shipment_prices`, `overhead_classification`) → `fetch_tab_as_dataframe`.
- whole-workbook xlsx export, multi-tab-by-name (`team_config`) → `fetch_workbook_tabs`.

## Config

- Add `GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH` to `.env.example` + `.env.docker.example` (placeholder path, same pattern as existing `GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH` entry which phase-03 will retire in favor of this one generic var).

## Validation

- `python -c "from ingestion.src.gsheet_auth import get_gspread_client; get_gspread_client()"` succeeds with the real key path set, fails with a clear message when unset (test both).
- `fetch_tab_as_dataframe(BUDGET_URL, GID_ALLOCATION_POLICY)` returns the same shape as the existing `_fetch_tab_csv` (row count, column count) — direct diff against a dry-run of the current budget sync, since that sheet already works today via public CSV and gives a known-good baseline.

## Files touched

- `ingestion/src/gsheet_auth.py` (new)
- `.env.example`, `.env.docker.example` (edit — add new env var)
- `ingestion/requirements.txt` (no change expected — `gspread` already present; add `google-auth`/`gspread`'s own deps only if `pip install` surfaces a missing transitive dep)
