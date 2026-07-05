# Phase 3 — Scorecard Scope Fix — Implementation Report

## Executed Phase
- Phase: phase-03-scorecard-scope-fix
- Plan: `plans/260705-1459-budget-cashflow-workable-loop/`
- Status: completed

## Files Modified
- `docs/analytics-handbook/blueprints/metabase/finance_cashflow_budget.md` (only file touched, as scoped)

## Tasks Completed
- [x] "A1 - Tong thuc te" / "A1 - Chenh lech" / "A1 - Ti le thuc hien": added `WHERE coverage = 'both'`, kept `[[AND {{period_month}}]] [[AND {{cashflow_line}}]]`, updated descriptions to state scope = plan coverage.
- [x] New card "A1 - Ngoai ke hoach" (scalar): `SUM(actual_amount) WHERE coverage='actual_only'`, same currency viz style (`number_style: currency, VND, decimals 0, compact`), description notes the design signal (unusually large card = add more budget lines).
- [x] Row-3 layout resized to fit 5 scorecards in 18 cols with zero gaps/overlap: col 0(4)/4(3)/7(3)/10(4)/14(4) = 18. No rows below needed to shift.
- [x] "A3 - Bang chenh lech chi tiet": added `coverage` column to SELECT; `ORDER BY` now sorts `coverage='both'` rows first, then `ABS(variance_pct) DESC` within each group.
- [x] "A2" bar chart: untouched (per spec — mismatch already visible there).
- [x] "Source Freshness BvA" text: added a caveat sentence documenting the new coverage scoping and pointer to the new card.
- [x] Deployed via `node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/metabase/finance_cashflow_budget.md` (no manual Metabase edits).

## Unplanned Fix (found + fixed, in-scope file only)
Found this blueprint's 10 `#### 🔘 Text:` headings used emoji `🔘`, but `markdown_parser.js`'s `textMatch` regex only recognizes `📝` (confirmed: all other 42 blueprint files in the repo use `📝`; this file was the sole outlier). Effect: parser silently dropped every text heading, and — because the parser doesn't reset `currentQuestion` on an unmatched line — each Question's own `metabase-pos` got clobbered by the immediately-following (unparsed) Text heading's pos block. This pre-dated my change (verified: dashcard `updated_at` timestamps for A2/A3/A4 predate this session) and explains why, after my first deploy, the new card landed at `row 7, col 0, size 18x1` instead of `row 3, col 14, size 4x4`, and why A2/A3/A4 were already at drifted rows.

Fix: corrected all 10 `🔘` → `📝` in this file only (no changes to shared `lib/markdown_parser.js`, staying inside file ownership). Re-verified via a standalone parse dump that every question's pos now matches its own declared `metabase-pos` block, and all 10 text cards now parse. Redeployed — dashboard now has 26 cards (16 questions + 10 text), all positions match blueprint, zero overlaps (verified programmatically for both tabs).

## Verification
- Parser dry-run dump: every question's `pos` matches its declared blueprint block exactly (row 3 five-card row: cols 0/4/7/10/14, sizes 4/3/3/4/4 = 18, no gaps).
- Overlap check script over both tabs (`Budget vs Actual`, `Reserve & Allocation`): 0 overlaps.
- Metabase `/api/dataset` sanity query against `main_marts.mart_cashflow_budget_vs_actual`:
  - `coverage='both'`: 4 rows, `SUM(actual_amount)` = 192,445,945
  - `coverage='actual_only'`: 54 rows, `SUM(actual_amount)` = 5,896,263,331
  - `both + actual_only` = 6,088,709,276 = what the old unscoped "Tong thuc te" card summed (budget_only rows have `actual_amount=0` by construction, contribute nothing) — confirms no money vanished, it's just split visually.
  - Confirms the phase's design note in practice: "Ngoai ke hoach" (~5.9B) dwarfs "Tong thuc te" (~192M) — a strong, correct signal that the budget sheet under-covers actual cashflow lines.
- `parameter_mappings` confirmed wired for `period_month`/`cashflow_line` on all 4 touched/new A1 cards (dashcard dump).
- Dashboard 113 and all other blueprint files: untouched.

## Tests Status
- Type check: n/a (Markdown blueprint, no build step)
- Unit tests: n/a
- Deploy script: pass (2nd redeploy after emoji fix — clean, no warnings besides one pre-existing unrelated warning on "Chu ky bao cao" cashflow_line mapping, not in phase scope)

## Issues Encountered
- Pre-existing, file-local parser-compatibility bug (see above) — fixed within file ownership, no shared-lib changes.
- Note for later phase (per task instructions): a subsequent phase will also edit this same file for an unrelated filter-default change — diff kept minimal/scoped to this phase's concerns only.

## Next Steps
- None blocking. Dashboard 114 tabs "Budget vs Actual" and "Reserve & Allocation" both render correctly with fixed positions as a side effect of the emoji fix.

## Unresolved Questions
- None.
