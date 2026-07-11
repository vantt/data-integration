# Phase 04 — Tests + manual verify

**Status:** ✅ done — 928 passed / 1 deselected (pre-existing, unrelated) in container. Live
curl smoke test against the restarted container confirmed the 3-section layout, correct
kind-separation, and the auth-gated Nhận button. ui-spec doc updated (including the
overflow-route correction from the phase 02 fix).

## Requirement

1. Run full CRM test suite in container (not host — see project memory: CRM tests run inside
   the `crm` Docker container):
   `docker compose exec -T crm sh -c "cd /app/crm/src && python -m pytest -q"`
   All pre-existing tests must still pass (no regressions) plus new tests from phases 01-03.
2. `docker compose restart crm` (bind-mounted templates/code — no rebuild needed unless a
   Python dependency changed, which it shouldn't here).
3. Manual walkthrough on `/worklist`:
   - Confirm 3 sections render top-to-bottom: Hàng Đợi Chung → Cơ Hội Hệ Thống → urgency bands
     (Đã liên hệ first/collapsed, then Quá hạn/Hôm nay/Trong hạn — band "Treo lâu" absent since
     it's always empty of tasks now).
   - Pick one unclaimed action in "Cơ Hội Hệ Thống", click "Nhận việc" → confirm it disappears
     from the queue section and the customer's task now appears in the correct urgency band
     after the container's full-fragment reload (claim already triggers
     `hx-target="#worklist-container" hx-swap="outerHTML"` — verify this still fires correctly
     post-restructure).
   - Pick one unassigned custom task in "Hàng Đợi Chung", click "Nhận" → confirm row deletes
     client-side (per phase 03's `hx-swap="delete"` contract).
   - Confirm no action row ever appears inside the urgency-band area, and no task row appears
     inside "Cơ Hội Hệ Thống".
   - Confirm KPI strip counts ("Task mở", "Hành động AQ", "Cần xử lý ngay") still look sane
     against the visible rows.
4. Update `crm/docs/ui-spec/screens/S01-worklist-dashboard.md`'s "Band structure" table and
   row-detail sections to describe the new 3-section layout (this doc is the source of truth
   referenced elsewhere — keep it in sync since it's an active screen spec, not a stale note).

## Acceptance

- All tests green.
- Manual walkthrough above passes with no visual kind-mixing.
- ui-spec doc updated to match shipped behavior.

## Rollback

- Each phase's file-level rollback notes apply. If phase 04 manual verify surfaces a problem
  traceable to a specific phase, revert that phase's files only — phases are additive/isolated
  enough that a partial revert (e.g. keep phase 01+02, revert phase 03's row redesign) is safe.
