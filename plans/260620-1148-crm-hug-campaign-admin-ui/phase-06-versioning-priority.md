# Phase 6 — Versioning / Rollback + Priority Enforcement

## Context Links
- History table: `crm_hug_campaign_history` (Phase 1 migration 0024)
- Repository: `crm/src/hug/campaign_repository.py` — `list_history`, `restore_snapshot`, `suggest_next_priority`
- Edit form: `crm/src/adapters/inbound/web/screen_hug_campaign.py` (Phase 4)
- Push: `crm/src/hug/campaign_push.py` (Phase 2) — restore triggers a push

## Overview
- **Priority:** P3 (quality-of-life; does not block go-live)
- **Status:** pending (blocked on Phases 1, 4)
- **Goal:** Surface history snapshots in the edit form + a restore action. Soft-enforce priority uniqueness in the UI (warn, don't block). Both are thin additions — repository functions already exist from Phase 1.

## Key Insights
- `crm_hug_campaign_history` stores a full JSON snapshot of the row at each save. Restore = parse snapshot JSON → `upsert_campaign` with that dict → push to edge. A restore creates a new history row (so the rollback itself is auditable).
- Priority uniqueness: a hard `UNIQUE` constraint on `priority` would block valid tie scenarios (two campaigns for completely different contexts). Soft enforcement is correct: suggest the next free slot, warn on duplicate, allow save. The edge `selectCampaign` breaks ties by `campaign_id` string order (implicit, not documented in TS — verify before relying on it).
- History list should be compact: show at most 10 snapshots per campaign. Each row: saved_at timestamp + targeting summary + a "Khôi phục" button (POST form).
- The "suggest priority" feature is a small UX affordance: on `GET /hug/campaign/new`, pre-fill the priority field with `suggest_next_priority()`. On existing campaign edit, show "Gợi ý: {n}" next to the field if the current priority is duplicated.

## Requirements

### Functional
- `GET /hug/campaign/{id}/history` → HTML page listing up to 20 snapshots for a campaign, each with a "Khôi phục về phiên bản này" POST button.
- `POST /hug/campaign/{id}/restore/{snapshot_id}` → restore the snapshot: `restore_snapshot(conn, id, snapshot_id)` → `push_campaign(restored_row)` → redirect to `/hug/campaign/{id}/edit` with flash "Đã khôi phục phiên bản {ts}".
- Priority duplicate warning: in `POST /hug/campaign/new` and `POST /hug/campaign/{id}/edit` save path — after `validate_targeting`, check if `priority` value already exists for a different `campaign_id`; if so, append a warning to flash but still save (soft enforcement only).
- Priority suggestion: `GET /hug/campaign/new` pre-fills priority input with `suggest_next_priority(conn)`.

### Non-Functional
- No new modules required — history routes added to `screen_hug_campaign.py` (check line count; split to `screen_hug_campaign_history.py` if file would exceed 200 lines).
- `_render_history_page(campaign_id, snapshots)` added to `screen_hug_campaign_html.py` (or `_history.py` sibling if needed).
- Restore is idempotent: restoring to current state is harmless (upsert + push, new history row).

## Architecture

```
crm/src/adapters/inbound/web/screen_hug_campaign.py
  ← ADD: GET /hug/campaign/{id}/history
  ← ADD: POST /hug/campaign/{id}/restore/{snapshot_id}
  ← ADD: priority duplicate check in save path

crm/src/adapters/inbound/web/screen_hug_campaign_html.py
  ← ADD: _render_history_page(campaign_id, snapshots)
  ← ADD: _render_snapshot_row(snapshot) helper
```

**Data flow (history view):**
```
GET /hug/campaign/{id}/history
  → campaign_repository.list_history(conn, id, limit=20)
  → _render_history_page(id, snapshots)
```

**Data flow (restore):**
```
POST /hug/campaign/{id}/restore/{snapshot_id}
  → campaign_repository.restore_snapshot(conn, id, snapshot_id)
     → parse snapshot JSON → upsert_campaign (new history row created)
  → campaign_push.push_campaign(restored_row)
  → redirect /hug/campaign/{id}/edit + flash
```

**Data flow (priority duplicate check in save):**
```python
# In save path, after upsert_campaign:
existing = [c for c in list_campaigns(conn) if c["priority"] == priority
            and c["campaign_id"] != campaign_id]
if existing:
    flash += f" ⚠️ Priority {priority} cũng dùng bởi '{existing[0]['name']}' — tie-break theo campaign_id."
```

## Related Code Files

**Modify:**
- `crm/src/adapters/inbound/web/screen_hug_campaign.py` — add 2 routes + priority check
- `crm/src/adapters/inbound/web/screen_hug_campaign_html.py` — add `_render_history_page`

**Read-only (already implemented in Phase 1):**
- `crm/src/hug/campaign_repository.py` — `list_history`, `restore_snapshot`, `suggest_next_priority`

## Implementation Steps

1. Add history endpoint to router:
   ```python
   @router.get("/hug/campaign/{campaign_id}/history", response_class=HTMLResponse)
   async def campaign_history(campaign_id: str) -> HTMLResponse:
       snapshots = campaign_repository.list_history(conn, campaign_id, limit=20)
       return HTMLResponse(_render_history_page(campaign_id, snapshots))
   ```

2. Add restore endpoint:
   ```python
   @router.post("/hug/campaign/{campaign_id}/restore/{snapshot_id}", response_class=HTMLResponse)
   async def campaign_restore(campaign_id: str, snapshot_id: int) -> HTMLResponse:
       row = campaign_repository.restore_snapshot(conn, campaign_id, snapshot_id)
       push_result = campaign_push.push_campaign(dict(row))
       flash = f"Đã khôi phục. Đẩy D1: {'✓' if push_result['ok'] else '✗'}"
       return RedirectResponse(f"/hug/campaign/{campaign_id}/edit?flash={quote(flash)}", status_code=303)
   ```

3. Add `_render_history_page` to `screen_hug_campaign_html.py`:
   - Table: `saved_at` (ICT formatted), targeting summary (truncated), "Khôi phục" POST button.
   - Back link to edit form.
   - "Lịch sử thay đổi" heading, matching dark-card style.

4. Add "Lịch sử" link to the edit form (`_render_form`): small link below the form heading → `/hug/campaign/{id}/history`.

5. Priority check in save path (both new and edit): after upsert succeeds, query for duplicate priority and append warning to flash if found.

6. Priority suggestion: pass `suggest_next_priority(conn)` to `_render_form` for the new campaign form; pre-fill the input value.

## Todo

- [ ] Add `GET /hug/campaign/{id}/history` route
- [ ] Add `POST /hug/campaign/{id}/restore/{snapshot_id}` route
- [ ] Add `_render_history_page` to `_html.py`
- [ ] Add "Lịch sử" link on edit form
- [ ] Add priority duplicate check in save path (both create and edit)
- [ ] Pass `suggest_next_priority` result to new-campaign form
- [ ] Test: restore snapshot → row reverts + new history row created + push called

## Success Criteria

- History page shows correct number of snapshots for a campaign.
- Restore sets the row back to the snapshot values and creates a new history row.
- After restore, push is called and flash shows push status.
- Duplicate priority warning appears in flash when two campaigns share a priority.
- New campaign form pre-fills priority with `suggest_next_priority()` result.
- `screen_hug_campaign.py` still ≤ 200 lines after additions (split to `screen_hug_campaign_history.py` if exceeded).

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Snapshot JSON parsing fails (e.g. old format) | Low | Low | Wrap in try/except; show "snapshot không thể khôi phục (format cũ)" |
| Restore pushes a paused/archived campaign as-is (edge sees `status=paused`) | Low | Medium | Edge `fetchActiveCampaigns` filters `status='active'` — a paused snapshot restore is safe (edge ignores it). Document this. |
| `screen_hug_campaign.py` exceeds 200 lines | Medium | Low | Extract history routes to `screen_hug_campaign_history.py`; mount both in composition.py |
| Priority suggestion gets stale between tab open and submit | Low | Low | It's a hint, not a reservation. The duplicate check on save catches it. |

## Security Considerations
- `snapshot_id` from URL is an `INTEGER` PK — validate it's a positive integer before querying.
- Snapshot JSON is authored by the server (inserted by `upsert_campaign`) — not user input. No need to sanitise on restore, but parse with `json.loads` inside a try/except.

## Next Steps
- Phase 7 (deferred): extend attribute catalog once Worker + ScanContext support `order_value`, `scan_index`, `geo`.
- Post-launch: add a "Compare" view showing diff between two history snapshots.
