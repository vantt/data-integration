# Phase 2 — Migrate 5 Read-Only Sheets to Service-Account Auth

**Depends on:** phase-01 (SA key live, `gsheet_auth.py` helper working)
**Blocks:** none (independent of phase-03; safe to run in parallel)

## Readers affected

| Reader | Current fetch | Tabs read | New fetch call |
|---|---|---|---|
| `ingestion/src/gsheet_marketing_spend.py` | CSV export, no gid (first tab) | 1 | `fetch_tab_as_dataframe(SHEET_URL, gid="0")` |
| `ingestion/src/gsheet_targets.py` | CSV export, no gid (first tab) | 1 | `fetch_tab_as_dataframe(SHEET_URL, gid="0")` |
| `ingestion/src/gsheet_overhead_classification.py` | CSV export, `gid=0` | 1 | `fetch_tab_as_dataframe(SHEET_URL, gid="0")` |
| `ingestion/src/gsheet_us_shipment_prices.py` | CSV export, `gid=304875363` | 1 | `fetch_tab_as_dataframe(SHEET_URL, gid="304875363")` |
| `ingestion/src/gsheet_team_config.py` | XLSX export, whole workbook | 2 (`teams`, `team_members`) | `fetch_workbook_tabs(SHEET_URL)` |

Each reader keeps its own validation/normalization logic untouched — only the fetch call changes. This is the DRY boundary: one auth+fetch helper (phase-01), N unchanged parsers.

## Per-reader migration steps

For each of the 4 CSV-style readers (`marketing_spend`, `targets`, `overhead_classification`, `us_shipment_prices`):
1. Replace the `requests.get(csv_url)` + `pd.read_csv(...)` block with `gsheet_auth.fetch_tab_as_dataframe(SHEET_URL, gid)`.
2. Check the existing `pd.read_csv` call's `header=`/`dtype=` args — if the reader currently relies on `pandas` auto-detecting header row 0 (default `header=0`), promote row 0 of the raw grid to column names before handing off to the rest of the function (`df.columns = df.iloc[0]; df = df[1:].reset_index(drop=True)`), so downstream code addressing columns by name keeps working unchanged.
3. Run the reader against the real sheet **before** touching the URL constant, capture output (row count, `df.columns.tolist()`, a hash or sample of the seed/parquet it writes).
4. Switch `SHEET_URL` env var resolution unchanged (still comes from `SOURCES__SPREADSHEET_URL__*`) — only the fetch mechanism changes, not where the URL comes from.
5. Re-run, diff against the phase-3 baseline capture. Row count + columns + written output must match exactly.

For `gsheet_team_config.py`:
1. Replace `_fetch_sheets_from_xlsx(SHEET_URL)` with `gsheet_auth.fetch_workbook_tabs(SHEET_URL)`.
2. Same before/after diff on both `teams` and `team_members` tabs (row count, columns, downstream SCD2 output).

## Config cleanup (the original security finding)

1. Remove the 3 real sheet IDs currently committed in `ingestion/.dlt/config.toml` (`[sources.spreadsheet_url]` section — `marketing_spend`, `targets`, `us_shipment_prices`) — verified tracked in git (`git ls-files` includes this file). Replace with a comment pointing to the env vars (`SOURCES__SPREADSHEET_URL__*` in `.env.docker`, untracked) as the actual source.
2. Confirm nothing else reads sheet IDs from `config.toml` directly (grep for `spreadsheet_url` beyond the readers already covered here) before deleting the section.
3. Once all 5 readers verified working via SA auth (steps above), turn off "Anyone with link" on all 5 sheets in the Sheets UI (human step) — this is the actual security fix; the code migration alone doesn't close the exposure until link-sharing is off.

## Validation

- Each of the 5 readers: row count, column names, and final parquet/seed output byte-identical (or field-for-field equal, if formatting like whitespace changes) before vs. after migration.
- `git ls-files -- ingestion/.dlt/config.toml` diff shows the 3 sheet IDs removed.
- With "Anyone with link" OFF on all 5 sheets: re-run each reader once more — must still succeed (proves SA auth, not link-sharing, is what's making it work).

## Risks

- Sheets API (`get_all_values()`) returns cell values as plain strings always (like CSV `dtype=str`), whereas the current XLSX path for `team_config` gives `pd.read_excel` native dtypes (numbers as int/float, not str) — check `gsheet_team_config.py`'s validation logic for any dtype-sensitive comparison (e.g. `isinstance(x, (int, float))`) that would break once everything arrives as string; adjust the reader's parsing, not the shared helper.
- Turning off link-sharing before all 5 are confirmed migrated breaks the old readers mid-flight — do this only after every reader is verified, as the last step, not per-reader.

## Files touched

- `ingestion/src/gsheet_marketing_spend.py`, `gsheet_targets.py`, `gsheet_overhead_classification.py`, `gsheet_us_shipment_prices.py`, `gsheet_team_config.py` (edit — fetch call only)
- `ingestion/.dlt/config.toml` (edit — remove tracked sheet IDs)
