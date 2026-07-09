# Code Review: ICT date-parsing gap + duplicated "ICT" text fix

## Scope
- Files: `crm/src/adapters/inbound/web/fmt_date.py`, `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html`, `crm/src/adapters/inbound/web/templates/fragments/order_context_tab.html`
- LOC: ~30 changed lines total
- Focus: targeted bug fix, verified against the 6 numbered questions in the task

## Overall Assessment
Correct, well-scoped fix. Verified the root cause empirically: `order_mappers.py::_s()` calls `str(v)` on DuckDB `TIMESTAMPTZ` values (`fo.ordered_at`, `first_shipped_at`, `updated_at` — confirmed TIMESTAMPTZ per project convention), and Python's `str(datetime)` for an offset-aware datetime produces exactly `"YYYY-MM-DD HH:MM:SS[.ffffff]+HH:MM"` — the format that was previously unparseable and silently fell through to returning the raw string. No breaking changes, no scope drift.

## Verification of the 6 questions

1. **`format_date_ict`/`format_ict` never append "ICT"** — confirmed by reading `fmt_date.py` lines 56-64: returns only `local.strftime("%d/%m/%Y")`. `format_ict = format_date_ict` alias (line 151). The 5th `order_context_tab.html` `return_date` case was correctly left with its trailing `<span>ICT</span>` — it's not part of this bug.

2. **`strptime(..., "%z")` colon-offset support** — confirmed empirically on Python 3.12.13 (both host and the running `crm` container, via `docker compose exec crm python3 --version`): `datetime.strptime('2026-03-03 09:51:56+07:00', '%Y-%m-%d %H:%M:%S%z')` and the `.%f%z` variant both parse correctly and produce `tzinfo=UTC+07:00`. This is documented CPython behavior since 3.7 (colon support), not just an accident of this version.

3. **New `":" not in iso_str` heuristic re-checked against all current callers** — grepped all 12 `format_datetime_ict` call sites across templates (`conversation_detail.html`, `dismissed_actions.html`×2, `c360_call_cockpit_panel.html`×2, `order_context_tab.html`×4, `task_detail.html`, `inbox.html`, `tasks_board.html`). All pass full ISO datetime strings (with `T`/`Z` or space+offset) sourced from DB timestamp columns or `_ict_local_to_utc()`-produced UTC ISO strings — none pass a bare `YYYY-MM-DD` date to this filter. Test fixtures (`test_web_templating.py`, `test_worklist_ranking.py`) do use bare `due_at="2026-06-23"` style strings, but those produce the *same* date-only classification under both the old and new heuristic (no `T`/no `Z` under old; no `:` under new) — not a regression.

4. **Swept whole `templates/` tree for missed double-ICT occurrences** — checked all remaining `format_datetime_ict` call sites (item 3 list) for a trailing literal "ICT"; none found. The fix's 6 removed occurrences (2 in `c360_call_cockpit_panel.html`, 4 in `order_context_tab.html`) were the complete set.

5. **Other `_parse_iso` callers (`format_relative`, `days_since`)** — both only compute elapsed-time deltas via `datetime.now(_UTC) - dt`, which works correctly for both aware-UTC and aware-offset datetimes (Python normalizes via absolute instant on subtraction). No hardcoded format assumption in either function; both benefit from the widened parsing without introducing regressions. `recency_days_label`/`fmt_date_key` operate on integer `date_key`, not `_parse_iso` — unaffected, correctly out of scope.

6. **No overlap with `plans/260709-1034-card-badge-macro-consolidation/`** — confirmed via `git status`: only the 3 stated files are modified under `crm/src`. That plan's phase-02 doc references `order_context_tab.html` only as prose (an existing `.scard--lead` CSS variant example), and no code changes for that plan have landed yet. No file or line-range conflict.

## Additional checks performed
- Ran `src/tests/test_web_templating.py` inside the `crm` container: 56 passed.
- Ran broader targeted subset (`fmt_date`, `web_templat`, `claim_context_snooze`, `task_detail_and_cockpit`, `health_domain_collect`, excluding the known-broken `test_approach_script_handler.py` collection error which is pre-existing and unrelated per prior context): 128 passed.
- Manually verified strptime pattern ordering causes no cross-format collisions (Z-suffixed, offset-suffixed, and bare-date inputs each match only their intended pattern).

## Critical Issues
None.

## High Priority
None.

## Medium Priority
- **No dedicated unit test added for `fmt_date.py`.** There is no `test_fmt_date.py` covering `_parse_iso`/`format_datetime_ict` directly — coverage is incidental, via template-rendering tests that happen to pass ISO strings through. This is exactly the kind of small pure-function logic (multi-format date parsing with a fragile string-based heuristic) that regresses silently on the next format change. Given the fix was "verified live against the real running server" rather than with an automated case, recommend adding a small parametrized unit test for `_parse_iso`/`format_datetime_ict` covering: Z-suffixed, offset-suffixed (with and without microseconds), and bare-date inputs — cheap insurance against the next silent-fallback regression this exact bug class represents.

## Low Priority
None.

## Edge Cases Found by Scout
- None beyond what's covered in items 1-6 above; the DuckDB `TIMESTAMPTZ` → `str(datetime)` origin of the new format was traced and confirms the fix targets the real production data path, not a hypothetical one.

## Positive Observations
- The `astimezone(_ICT)` conversion is correct regardless of which offset the source string carries (UTC `Z` vs `+07:00`), since conversion is instant-based — the fix is robust to whichever timezone the upstream DuckDB session is configured with.
- `dt.tzinfo is None` guard in `_parse_iso` correctly skips forcing UTC onto the newly-added offset-aware patterns, preserving the real parsed offset.

## Recommended Actions
1. (Medium, non-blocking) Add a unit test file for `fmt_date.py` covering the format matrix now supported by `_parse_iso`.

## Metrics
- Tests run: 56 (`test_web_templating.py`) + 128 (broader targeted subset) — all passed.
- Pre-existing unrelated failure: `test_approach_script_handler.py` (import error, not touched by this diff).

## Unresolved Questions
None — all 6 items in the task were verifiable directly against the repo and a live container.
