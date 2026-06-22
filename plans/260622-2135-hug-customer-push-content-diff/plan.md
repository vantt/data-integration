---
title: "Hug Customer Push — Incremental Content-Diff"
description: "Per-row content-diff + push state store to eliminate ~99% of redundant D1 upserts (480 full pushes/day → 1–2 changed-rows-only pushes/day)"
status: done
priority: P1
effort: 3h
branch: main
tags: [hug, cloudflare-d1, performance, sqlite, crm]
created: 2026-06-22
---

## Problem

`customer_push.run()` fires ~480×/day (every 3 min cron + 10 min incremental),
pushing ALL ~7.5k rows each time (~15 API batches/push × 480 = ~7 200 D1 API calls/day).
`recency_days` is day-granular (constant intra-day); no other field changes more than
once per mart refresh. True change rate: ~0 rows intra-day; ~7.5k rows at ICT midnight.
Content-diff collapses ~99% of those API calls.

## Phases

| # | File | Status |
|---|------|--------|
| Phase 1 | [State store design + schema](phase-01-state-store.md) | done |
| Phase 2 | [customer_push.py algorithm changes](phase-02-algorithm.md) | done |
| Phase 3 | [Force-flag wiring](phase-03-force-flag.md) | done |
| Phase 4 | [Test matrix extension](phase-04-tests.md) | done |

Implemented on branch `feat/hug-customer-push-content-diff`. 15/15 tests pass (C1–C8 + D1–D7).

## Key Files

- `crm/src/hug/customer_push.py` — sole file modified for Phases 2+3
- `crm/src/hug/db.py` — NOT modified (hug.db schema is token lifecycle only)
- `crm/sync/cache_schema.sql` — NOT modified (see Phase 1 rationale)
- `crm/src/tests/test_hug_customer_push.py` — extended in Phase 4

## Dependencies (sequential — no parallelism needed)

Phase 1 → Phase 2 → Phase 3 → Phase 4

## Resolutions (verified 2026-06-22)

- **State persists across container restarts** — `docker-compose.yml` mounts the CRM
  databases via named volume `crm_data:/data` (`:181,:197`) with `CRM_DATA_DIR=/data`
  (`:163`). It mounts the whole `/data` directory, not individual files, so
  `/data/hug_push_state.db` survives restarts. Phase-1 q1 resolved — no full-push-per-restart.
- **`post_signed` failure shape** — returns `{"ok": False, "error": "http <code>"}` (no
  `status` key) and never raises (`crm/src/hug/d1_transport.py`). Phase-4 D4 mock must return
  `{"ok": False, "error": "http 500"}` (no `status`). `_push_batches` only reads `result["ok"]`,
  so the diff/state logic is unaffected.
