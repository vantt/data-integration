---
title: "C2 — Hug Campaign Admin UI"
description: "Self-serve admin to create/edit Hug campaign routing rules with preview and overlap warning."
status: pending
# (updated 2026-06-24: untouched by 260623 audit work; all phases 1-6 pending; Phase 7 deferred)
priority: P2
effort: 10h
branch: main
tags: [crm, hug, admin-ui, campaign, routing]
created: 2026-06-20
---

# C2 — Hug Campaign Admin UI

> M6 task. Context: [`build-order.md`](../260619-1030-crm-nba-resell-engine/build-order.md) · [`discussion-hug.md §7,§9`](../260619-1030-crm-nba-resell-engine/discussion-hug.md)

## Phases

| # | Phase | Status | Est |
|---|-------|--------|-----|
| 1 | [Data model — crm.db migration + repository](./phase-01-data-model.md) | pending | 1.5h |
| 2 | [campaign_push.py — HMAC push to Worker](./phase-02-campaign-push.md) | pending | 1h |
| 3 | [Targeting predicate engine in Python](./phase-03-targeting-engine.md) | pending | 1.5h |
| 4 | [Admin UI screens — list / create / edit](./phase-04-admin-ui.md) | pending | 3h |
| 5 | [Preview + overlap warning](./phase-05-preview-overlap.md) | pending | 2h |
| 6 | [Versioning / rollback + priority enforcement](./phase-06-versioning-priority.md) | pending | 1h |
| 7 | [Future: extend attributes (order_value / scan_index / geo)](./phase-07-future-attrs.md) | deferred | — |

## Key Dependencies

- Phase 1 must complete before all others.
- Phase 2 depends on Phase 1 (needs `crm_hug_campaign` table).
- Phase 3 must complete before Phases 4 and 5.
- Phase 4 depends on Phase 2 (push on save) and Phase 3 (validate).
- Phase 5 depends on Phase 3 (predicate engine).
- Phase 6 integrates with Phase 4 (UI save hook).

## Architecture Decision (confirm before Phase 1 starts)

**Local-mirror approach (recommended):** `crm_hug_campaign` table in crm.db → CRUD locally → push to edge D1 via `campaign_push.py`. No GET route needed on Worker. Consistent with token/customer push pattern.

See Phase 1 Open Questions for the alternative.

## Open Questions

1. **[CONFIRM]** Local-mirror vs. edit-edge-directly? (Local mirror recommended — see Phase 1.)
2. **[CONFIRM]** Overlap detection scope: exact 6-attribute pairwise intersection or simpler "has any shared active campaign" warning?
3. **[CONFIRM]** Versioning depth: snapshot-on-every-save (proposed) vs. only on publish/activate?
4. **[CLARIFY]** Preview accuracy: wh_customer_tier in cache.db covers customer-level attrs only; op_type/channel are per-scan, not per-customer. UI must label this limitation — confirm wording acceptable.
5. **[MINOR]** Priority soft-unique: warn on dup in UI (proposed) vs. hard UNIQUE constraint in crm_hug_campaign? (Hard constraint in crm DB could be widened later.)
