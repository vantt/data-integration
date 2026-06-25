# Phase 05 — Worklist "Có kịch bản" filter — Implementation Report

**Date:** 2026-06-25 · **Plan:** plans/260625-1808-s14-approach-script-backend-feed/phase-05-worklist-has-script-filter.md

---

## Files Changed

| File | Change |
|------|--------|
| `crm/src/domain/entities/cache_insight.py` | Add `customer_id: Optional[int] = None` to `ActionQueueItem` |
| `crm/src/adapters/outbound/sqlite/cache_repository.py` | `list_all_action_queue`: reorder JOIN (`wh_customer_base` directly on `customer_key`), select `bc.customer_id`; map into entity |
| `crm/src/domain/ports/approach_script_repository.py` | Add `list_customer_ids() -> set[int]` to Protocol |
| `crm/src/adapters/outbound/file/approach_script_file_repository.py` | Implement `list_customer_ids()` via `os.scandir`, regex `^\d+\.json$`, no cache |
| `crm/src/application/worklist_filters.py` | `parse_filters`: add `has_script`; `active_filter_count`: count it; `apply_filters`: new `script_cids` param, narrows actions when `has_script=1` |
| `crm/src/adapters/inbound/web/screen_worklist.py` | Add `_get_script_cids(request)` helper; pass `script_cids` to `_load_worklist_data`; include `script_cids` in template context |
| `crm/src/adapters/inbound/web/templates/fragments/_wl_filter_bar.html` | Add "📋 Có kịch bản" checkbox following `hide_contacted` chip pattern |
| `crm/src/adapters/inbound/web/templates/fragments/_wl_row.html` | `wl_row` macro: add `script_cids=none` param; compute `_has_script`; badge in `.wl-row__top`; "📋 Gọi" button → `/customers/{pid}?tab=call_cockpit` |
| `crm/src/adapters/inbound/web/templates/fragments/_wl_bands.html` | Pass `script_cids` through to `wl_row(...)` calls |
| `crm/docs/ui-spec/screens/S01-worklist-dashboard.md` | Add A-S01-010, A-S01-011, A-S01-LSN09 interactions |
| `crm/docs/ui-spec/components/C05-filter-bar.md` | Document `has_script` filter |
| `crm/src/tests/test_worklist_filters.py` | Updated `parse_filters` defaults test; added 6 `has_script` tests |
| `crm/src/tests/test_approach_script_file_repository.py` | Added 4 `list_customer_ids` tests (set, empty, ignores garbage, auto-reflects new file) |
| `crm/src/tests/test_cache_repository_customer_id.py` | New file: 2 tests for `customer_id` present/None in `list_all_action_queue` |

---

## Test Results

```
docker compose exec -T crm python -m pytest \
  crm/src/tests/test_worklist_filters.py \
  crm/src/tests/test_approach_script_file_repository.py \
  crm/src/tests/test_cache_repository_customer_id.py -v

31 passed in 0.75s
```

Full suite (excluding 2 pre-existing httpx-broken test files):
- 535 passed, 13 skipped, 2 failed (both pre-existing — `TestWorlistFilterBar::test_action_type_chips_rendered_for_available_types` and `test_all_new_action_types_have_chips` — confirmed failing identically before my changes via `git stash` test)
- 0 new failures introduced

---

## npm check

```
npm run check → ✓ validation passed (14 warning(s)) — same 14 pre-existing R1-R14 warnings
surfaces=53 actions=279 flows=6
0 new errors
```

---

## E2E Verification

```
# After docker compose restart crm:
GET /worklist → 200 OK

# Unfiltered: 516 action rows
# With ?has_script=1: 20 action rows (31 script files, 20 with open actions)
curl "http://localhost:3007/worklist/fragment?has_script=1" → 20 wl-row--action

# Badge + Gọi button present in response:
grep output: badge--info "📋 Có kịch bản", href "?tab=call_cockpit"

# Auto-handle new file (NO restart):
# 1. Drop /data/approach_scripts/929184461.json
# 2. GET /worklist/fragment?has_script=1 → 21 rows (new customer auto-detected)
# 3. Remove file → 20 rows (auto-removed from filter set)
```

---

## Design Deviations from Plan

None. All 7 implementation steps followed exactly.

One minor note: `A-S01-LSN09` (badge render interaction) modeled as `listens_to: worklist.load_complete` instead of `trigger: render` (not a valid schema trigger) — semantically equivalent.

---

## Unresolved Questions

None.
