# Phase 03 — Google Sheets via service account (remove public exposure)

**Priority:** Medium (security) | **Status:** SUPERSEDED (2026-07-07) — merged into `plans/260707-1201-google-sheets-service-account`, which combines this read-only SA need with a new write-access need (budget sheet suggestions write-back). Do not implement from this file; see the new plan.
**Context:** [plan](plan.md) · audit finding "Google Sheets public + IDs tracked in config.toml"

## Problem
5 sheet readers fetch via **public CSV/xlsx export URLs** (`/export?format=csv`) → sheets must be "Anyone with link". Sheet IDs are also tracked in `ingestion/.dlt/config.toml` (committed). Business data (marketing spend, targets, team config, shipment prices) is world-readable to anyone with the ID.

## Readers affected
- `ingestion/src/gsheet_marketing_spend.py`
- `ingestion/src/gsheet_targets.py`
- `ingestion/src/gsheet_overhead_classification.py`
- `ingestion/src/gsheet_team_config.py`
- `ingestion/src/gsheet_us_shipment_prices.py`

## Approach (simplest secure = service account)
1. **User/GCP:** create a service account, enable Google Sheets API, download JSON key.
2. **Secrets:** store key in `ingestion/.dlt/secrets.toml` (untracked) or as an env var; NEVER commit.
3. **Sharing:** share each sheet to the SA email (Viewer); then turn OFF "Anyone with link".
4. **Code:** switch each reader from public CSV/xlsx GET to authenticated read via `gspread` (or `google-api-python-client`). Centralize the auth + fetch in ONE helper (DRY) returning the same DataFrame shape each reader already expects — readers keep their parsing/normalization.
5. **Config:** remove the real sheet URLs/IDs from tracked `config.toml`; reference via secrets/env.
6. **Deps:** add `gspread` (+ `google-auth`) to `ingestion/requirements.txt`.

## Risks
- Each reader currently parses a specific export format (csv vs xlsx, specific gid). The API returns values differently → must preserve column names/dtypes. **Test each reader** against the same sheet before/after (row count + columns identical).
- Container needs the SA key mounted/available; verify both Windows-native and Docker paths.

## Success criteria
- All 5 readers load identical data via SA auth; sheets no longer "Anyone with link"; no IDs/keys in tracked files; `git ls-files` shows no sheet URLs in config.toml.

## Blocked on
- GCP service-account JSON key (user to provide).
