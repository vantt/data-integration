---
title: "Hug Campaign: sku+not_in targeting, customer_type edge field, D1 preview endpoint"
description: "Three phased additions: catalog-only sku attr, not_in negation operator (TS+Python parity), customer_type edge column + content-diff resync, and a new Worker preview endpoint replacing cache.db for live match counts."
status: implemented (pending coordinated deploy)
# (updated 2026-06-24: P1+P2 code done (ed6bdfa, 43c6b65); P3 preview endpoint code done; Worker deploy + D1 migration + full resync still pending — see deploy note in plan body)
priority: P1
effort: 10h
branch: main
tags: [hug, cloudflare-worker, crm, targeting, d1, preview]
created: 2026-06-23
---

## Problem

Three gaps block current Hug campaign operations:

1. `sku` is already in D1 and `ScanContext` but cannot be used as a targeting rule (not in catalog).
2. Excluding B2B accounts (`WHOLESALE`, `STAFF`, `KOL`) requires enumerating every positive tier value — fragile and verbose. A `not_in` negation operator is needed on both the TS edge and the Python mirror.
3. The admin campaign preview counts customers from a nightly `cache.db` snapshot that lacks the CRM contactability overlay; it has no live D1 signal. A new Worker endpoint reusing `matchesTargeting` fixes accuracy and unlocks match-count + customer listing directly from D1.

## Phases

| # | Name | Status | Effort | Key risk |
|---|------|--------|--------|----------|
| 1 | `sku` catalog entry + `not_in` operator (TS + Python) | ✅ DONE (`ed6bdfa`) | 3h | TS↔Python drift on new operator shape |
| 2 | `customer_type` edge column + content-diff resync | ✅ DONE (`43c6b65`) | 3.5h | Full re-push on rollout; D1 migration ordering |
| 3 | `POST /hug/campaign/preview` Worker endpoint + CRM UI | ✅ DONE (code; needs deploy) | 4h | Worker deploy prerequisite; D1 scan latency |

**Pending coordinated deploy** (all three phases share one Worker deploy): run the D1 migration `webhook_receiver/cloudflareD1/migrations/add_hug_customer_type_column.sql` FIRST, then `wrangler deploy` (ships not_in matcher + customer_type scan/upsert + the preview endpoint), then trigger a CRM full resync (`HUG_CUSTOMER_PUSH_FULL=1`) so hug_customer rows carry customer_type. Until deployed: not_in/customer_type are inert (only the `default {}` campaign exists) and the preview falls back to cache.db.

## Sequencing rationale

Phase 1: `sku` is catalog-only (no Worker change), but `not_in` DOES change the edge `matchesTargeting` → one Worker deploy required (no schema). Phase 2 adds `customer_type` to `hug_customer`, making it countable in Phase 3 (customer-level). Phase 3 reuses the exact `matchesTargeting` function from Phase 1 (inheriting `not_in` for free) and counts `customer_type` added in Phase 2. Each phase is independently deployable.

⚠️ `not_in` MUST land in the Worker matcher before any campaign uses it: the current matcher treats an object rule as a numeric range, so an unrecognised `{not_in:[...]}` falls through all range checks and returns TRUE (matches everyone) — a B2B-exclusion campaign would silently match all customers. Worker change is non-optional.

## Key files (all verified against live code)

**Edge Worker (TS)**
- `webhook_receiver/cloudflareD1/src/hug-handler.ts` — `matchesTargeting` (lines 148–189), `ScanContext` (lines 79–90), `handleHugScan` (lines 217–275), `handleHugCustomerUpsert` (lines 423–473), `verifyAdminHmac` (lines 317–327)
- `webhook_receiver/cloudflareD1/src/index.ts` — route table (lines 18–36)
- `webhook_receiver/cloudflareD1/schema_hug.sql` — `hug_customer` (lines 35–42), `hug_token` (lines 13–25)
- `webhook_receiver/cloudflareD1/src/index.test.ts` — inline schema mirror (lines 45–52, no `customer_type` yet)

**CRM Python**
- `crm/src/hug/targeting_catalog.py` — `TARGETING_CATALOG` (lines 27–68), `validate_targeting` (lines 77–148)
- `crm/src/hug/targeting_engine.py` — `matches_targeting` (lines 48–106), `preview_match_customers` (lines 113–180)
- `crm/src/hug/customer_push.py` — `_build_edge_rows` (lines 127–149), `_content_str` (lines 183–189), `run()` (lines 256–338)
- `crm/src/hug/d1_transport.py` — `post_signed` (lines 34–71), `sign` (lines 28–31)
- `crm/src/hug/config.py` — `push_enabled()` (lines 54–56)
- `crm/src/adapters/inbound/web/screen_hug_campaign.py` — `_rerender_with_preview` (lines 310–344)
- `crm/src/adapters/inbound/web/screen_hug_campaign_html_preview.py` — `render_preview_panel` (lines 14–136)

**Mart / sync**
- `transformation/models/marts/customer/mart_customer_tier.sql` — selects `customer_type` at line 65
- `crm/sync/duckdb_reader.py` — `fetch_customer_tier` selects `customer_type` at line 308
- `crm/sync/cache_schema.sql` — `wh_customer_tier` has `customer_type TEXT` at line 98

**Tests**
- `crm/src/tests/test_hug_targeting_engine.py` — parity matrix M01–M18, validate V01–V09, preview P01–P03
- `crm/src/tests/test_hug_customer_push.py` — C1–C8, D1–D7

## Deploy / rollout notes

- CRM: deployed as Docker container built from `Dockerfile.crm`. Source code is volume-mounted (`./crm/src:/app/crm/src`), so Python-only edits (catalog, engine, transport, screen) are live without rebuild. A container rebuild (`docker compose up -d --build crm`) is only needed when `Dockerfile.crm` or non-mounted files change.
- Worker: deployed via `wrangler deploy` from `webhook_receiver/cloudflareD1/`. Each phase that touches Worker code requires a deploy. ALL THREE phases need one Worker deploy each (Phase 1 for `not_in` in `matchesTargeting`; Phase 2 for the `customer_type` read path; Phase 3 for the preview endpoint). Only `sku` within Phase 1 is Worker-free.
- D1 schema migration: `wrangler d1 execute fgcare-webhook-db --remote --file=<migration.sql>`. Must run BEFORE the Worker deploy that reads the new column.
- Full resync after Phase 2: set `HUG_CUSTOMER_PUSH_FULL=1` and trigger `/admin/refresh` or run `customer_push.run(force=True)` once after Worker + D1 migration are live.

## Permanent caveats (document in UI and code)

Touchpoint-level attrs (`op_type`, `channel`, `sku`) live in `hug_token`, not `hug_customer`. A preview over `hug_customer` cannot count them per-customer — the count is an UPPER BOUND. Customer-level attrs (`tier`, `recency_days`, `value_group`, `is_contactable`, `customer_type` after Phase 2) are exact.

## Resolutions to planner's open questions (decided 2026-06-23)

1. **`not_in` + null context (Q1, Q4 unified):** null/unknown PASSES a `not_in` rule (it is not in the excluded set — intuitive for an exclusion operator; consistent set logic with the positive-list rule which fails null). Same rule for `tier` and `customer_type`.
2. **`sku` admin input (Q2):** free-text field (open domain — sku has no fixed catalog).
3. **`not_in` UI (Q3):** backend + catalog/validator first (rule expressible via API/save). A polished include/exclude toggle in the rule-builder is a follow-up, NOT in this plan's scope.
4. **D1 migration convention (Q5):** no `migrations/` dir exists; schema is applied via `wrangler d1 execute fgcare-webhook-db --remote --file=<f.sql>` (README.md:56, docs/DEPLOYMENT.md:53). Phase 2 ships a standalone `migration_hug_customer_type.sql` (`ALTER TABLE hug_customer ADD COLUMN customer_type TEXT;`) applied that way, once, before the Worker deploy.
5. **Preview spinner (Q6):** deferred for v1 (cold D1 scan ~800ms acceptable; no loading state).
6. **`data_as_of` formatting (Q7):** Python-side `datetime.fromisoformat(...).astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))` — matches the repo's ICT serving convention.
7. **Pagination (Q8):** flat 50-row list for v1; "Tải thêm" / offset navigation deferred.
