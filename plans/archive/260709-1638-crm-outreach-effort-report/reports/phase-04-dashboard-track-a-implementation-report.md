# Phase 4 — Dashboard Track A implementation report

## Status: BLOCKED (at time of writing) → RESOLVED same day 2026-07-10

> Update 2026-07-10 (post-report): serving view was rebuilt (`olap.duckdb` mtime 15:41, now exposes all 26 columns) and the blueprint was deployed minutes later — Metabase log confirms `POST /api/dashboard`, 8× `POST /api/card`, dashboard id **147** created ~15:43. Verified live: `GET/POST /api/dashboard/147/dashcard/*/query` at 22:54 same day returned 200/202 with no Binder Errors. Track A dashboard is deployed and working; the blocker described below no longer applies.

## Summary

Blueprint `docs/analytics-handbook/blueprints/metabase/crm_outreach_effort_weekly.md` written and ready to deploy (1 tab, 8 cards: chu kỳ báo cáo, 4 scalar KPI, staff×tuần table, funnel trend chart, độ tươi dữ liệu + source/freshness text). **Not deployed** — the live Metabase serving view for `mart_staff_performance_weekly` is stale and missing every column the dashboard needs. Deploying now would create a dashboard where every card errors with a DuckDB Binder Error.

## Root cause (verified via DuckDB, read_only=True)

`app_data/data_lake/serving/olap.duckdb` (host path = `OLAP_DB_PATH` container path `/app/var/data_lake/serving/olap.duckdb`, confirmed via `docker-compose.yml` bind mount `./app_data/data_lake:/app/var/data_lake`) is the DB Metabase actually queries.

- `main.mart_staff_performance_weekly` and `main_marts.mart_staff_performance_weekly` (checked via `information_schema.columns`) both only expose **14 columns** (`staff_key` … `revenue_vnd`) — the pre-2026-07-10 schema.
- The view's `CREATE VIEW` SQL is `SELECT * FROM read_parquet(<rolling glob>)`. Confirmed empirically that DuckDB binds and freezes this `SELECT *` column list **at `CREATE VIEW` time**, not at query time — `duckdb_views().sql` shows the view text is unchanged since it was last created, and the `olap.duckdb` file's own mtime (`2026-07-08 17:32`) predates all 3 parquet versions currently in `rolling/mart_staff_performance_weekly/` (`...082615`, `...083119`, `...083407`, all today 2026-07-10).
- The **underlying rolling parquet already has all 25 columns** including `calls_dialed`, `contacts_reached`, `conversations_count`, `wrong_number_count`, `outcome_notes_count`, `health_concern_tags_new`, `other_tags_new`, `activities_call/chat/email/visit/other/unknown` — verified via `DESCRIBE SELECT * FROM read_parquet(<latest file>)` directly (bypassing the DuckDB view). dbt has already run today; the gap is purely the serving-view staleness, matching the documented "DuckDB view column rebuild" lesson.

This is exactly the scenario the task brief pre-flagged: fix requires `bootstrap_serving_views.py`, which requires stopping Metabase first. Per instruction, stopped here instead of doing that myself.

## Required fix (human/orchestrator action, not done by this agent)

```bash
docker compose stop metabase
docker compose exec -T data_platform python scripts/provisioning/bootstrap_serving_views.py
docker compose start metabase
```

Then deploy:

```bash
node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/metabase/crm_outreach_effort_weekly.md
```

Then verify each card returns 200 + rows (script's own verify step, or manual `GET /api/card/:id/query`).

## What was completed

- Read `.skills/metabase-automation/STRATEGY.md`, `SKILL.md`, `references/filter-date-range-pattern.md`, `templates/blueprint_template.md`.
- Confirmed no existing staff-performance/outreach blueprint in `docs/analytics-handbook/blueprints/metabase/` (37 files listed, none match) — created new one per instructions.
- Read `mart_staff_performance_weekly.sql` + `schema.yml` (crm) to get exact column semantics for all Sprint Gọi Ra columns (`calls_dialed`, `contacts_reached` new definition incl. `callback`/`refused`/`purchased`, `conversations_count` 60s-or-note-attached proxy, `wrong_number_count`).
- Read `plans/260709-1638-crm-outreach-effort-report/phase-04-reporting-surface-and-validation.md` for surface spec (used Track A section only, per task scope — Track B intentionally out of scope here, dashboard note references it).
- Confirmed DB registration name is `Sapo` (all CRM/finance blueprints use this name for the same DuckDB datalake, despite the name) via grepping `> **Database:**` headers across existing blueprints.
- Wrote blueprint with `FROM main_marts.mart_staff_performance_weekly` (unaliased) in every card per the task's schema-qualification constraint. No dashboard filters used (task didn't request date/staff filters; dashboard is always "latest week vs prior week" by `MAX(week_start_date)`), so the field-filter-injection gotcha in `filter-date-range-pattern.md` does not directly apply here — schema qualification was still followed as instructed.
- Scalar comparison cards use the existing proven "2-column result set, `display: scalar`" pattern (same as `sales_ops_weekly_review.md`'s Total Orders/Net Revenue/AOV cards) rather than the newer `scalar.comparisons` setting — that setting is flagged in project memory as "expected to work on v0.60.2 but not yet re-verified end-to-end," and this task had no way to verify it given the block. Noted as a follow-up in the blueprint frontmatter.

## Cards in the blueprint (none deployed/verified yet)

1. Chu kỳ báo cáo (cycle indicator scalar)
2. Text: Sprint Gọi Ra note (exact text from task brief)
3. Cuộc gọi (`calls_dialed`, this week vs last week)
4. Reach rate % (`SUM(contacts_reached)/SUM(activities_outbound)`, this week vs last week)
5. Hội thoại thật (`conversations_count`, this week vs last week)
6. SĐT chết (`wrong_number_count`, this week vs last week)
7. Staff × Tuần — Chi tiết (table, 8 weeks, sorted week desc)
8. Phễu tiếp cận theo tuần (line chart: calls_dialed / contacts_reached / conversations_count, 8 weeks)
9. Độ tươi dữ liệu + Source & Freshness text

## Unresolved questions

1. Should `scalar.comparisons` be attempted once the serving view is fixed, or keep the proven 2-column fallback permanently? Left as a note in the blueprint; needs a human call once deploy is unblocked.
2. Track B (`mart_crm_outreach_effort_by_action_weekly`) not addressed here — per phase-04 plan, it depends on Phase 1-3 cutover accumulating a few weeks of data first. No action needed yet.
3. `contact_quality='masked'` risk (flagged in phase-04 plan's open question) not addressed with a separate card — same reasoning as the plan: wait for real data before deciding if a split card is needed.
