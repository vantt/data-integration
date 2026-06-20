# Phase 2 — campaign_push.py: HMAC Push to Worker

## Context Links
- Pattern to copy: `crm/src/hug/customer_push.py` (batch push, config-gated, post_signed)
- Transport: `crm/src/hug/d1_transport.py` — `post_signed(url, secret, payload)`, never raises
- Worker endpoint already exists: `POST /hug/campaign/upsert` (hug-handler.ts line 9, HMAC-secured)
- Edge contract: `{"rows": [HugCampaign]}` — same shape as `hug_campaign` D1 table
- Config: `hug/config.py` — `push_enabled()`, `worker_url()`, `admin_secret()`
- Repository (Phase 1): `crm/src/hug/campaign_repository.py`

## Overview
- **Priority:** P1 (Phase 4 UI save calls this)
- **Status:** pending (blocked on Phase 1)
- **Goal:** One-way push of a single campaign row (or batch) from crm.db to edge D1 after every admin save. Mirror the `customer_push.py` pattern exactly — config-gated, never raises, logs clearly.

## Key Insights
- Worker's `/hug/campaign/upsert` does `INSERT OR REPLACE` on `campaign_id` PK and invalidates `_campaignCache` (hug-handler.ts:120). So a push is idempotent.
- Worker contract: body `{"rows": [CampaignRow]}`. CampaignRow fields: `campaign_id, name, targeting, destination_type, destination_url, offer_ref, priority, schedule_start, schedule_end, quota_total, quota_used, status`. We must send `quota_used=0` on create (we don't own that counter; edge owns it). On updates, we should NOT overwrite `quota_used` — but Worker does `INSERT OR REPLACE` which would reset it. **Resolution:** push only fields that are authoring-owned; ask Worker to PATCH quota_used via `conflict_action: 'ignore_quota'` — BUT this requires a Worker change. **Simpler KISS alternative (v1):** always send `quota_used=0` (authoring sets quota_total as a cap; actual usage is eventually consistent via scan path). Document this as a known limitation: editing a live campaign resets quota_used to 0 on D1. Flag for user confirmation.
- Push is called synchronously from the UI save handler but is fire-and-forget (result logged, UI shows push status in response).

## Requirements

### Functional
- `push_campaign(campaign_row: dict) → dict` — push one campaign row to Worker. Returns `{"ok": bool, "skipped": bool, ...}`.
- `push_all_campaigns(conn) → dict` — reconcile push: read all non-archived campaigns from crm.db and push in one batch. Used for initial sync or recovery.
- Config-gated: if `HUG_WORKER_URL` unset → skip + log (identical pattern to d1_push.py).

### Non-Functional
- No new runtime dependencies (stdlib only, reuse `d1_transport.post_signed`).
- Module ≤ 150 lines.
- FastAPI-free (testable without HTTP framework).

## Architecture

```
crm/src/hug/
  campaign_push.py     ← NEW (mirrors customer_push.py pattern)
```

**Data flow (single campaign push on save):**
```
UI save → campaign_repository.upsert_campaign(conn, row)   [Phase 1]
        → campaign_push.push_campaign(row_dict)
            → d1_transport.post_signed(worker_url+"/hug/campaign/upsert", secret,
                                       {"rows": [edge_row]})
            → {"ok": True/False, "skipped": bool, ...}
        → UI response includes push status
```

**Data flow (reconcile push for full sync):**
```
CLI / cron → campaign_push.push_all_campaigns(conn)
           → campaign_repository.list_campaigns(conn, status=None, exclude_archived=True)
           → _to_edge_row() × N → post_signed in one batch (≤100 rows, no chunking needed)
```

## Related Code Files

**Create:**
- `crm/src/hug/campaign_push.py`

**Read-only references:**
- `crm/src/hug/d1_transport.py` — `post_signed`, `sign`
- `crm/src/hug/config.py` — `push_enabled`, `worker_url`, `admin_secret`
- `crm/src/hug/customer_push.py` — structural template

**Modified in Phase 4:**
- `crm/src/adapters/inbound/web/screen_hug_campaign.py` — calls `push_campaign` after upsert

## Implementation Steps

1. Write `campaign_push.py`:

   ```python
   _UPSERT_PATH = "/hug/campaign/upsert"

   def _to_edge_row(row: dict) -> dict:
       """Project crm_hug_campaign dict to Worker HugCampaign contract.
       quota_used is NOT stored in crm.db (edge-owned); send 0 on push.
       Callers that need to preserve quota_used must fetch from edge first
       (no GET route exists in v1 — accepted limitation, see plan notes).
       """
       return {
           "campaign_id":      row["campaign_id"],
           "name":             row["name"],
           "targeting":        row["targeting"],
           "destination_type": row["destination_type"],
           "destination_url":  row["destination_url"],
           "offer_ref":        row.get("offer_ref"),
           "priority":         row["priority"],
           "schedule_start":   row.get("schedule_start"),
           "schedule_end":     row.get("schedule_end"),
           "quota_total":      row.get("quota_total"),
           "quota_used":       0,   # edge-owned; reset on push (v1 known limitation)
           "status":           row["status"],
           "updated_at":       row.get("updated_at"),
       }

   def push_campaign(row: dict) -> dict: ...

   def push_all_campaigns(conn) -> dict: ...
   ```

2. Unit tests in `crm/tests/hug/test_campaign_push.py`:
   - Push skipped when `HUG_WORKER_URL` unset (monkeypatch env).
   - `_to_edge_row` maps all fields correctly, `quota_used=0`.
   - Push succeeds: mock `post_signed` returns `{"ok": True, "status": 200}`.
   - Push failure (network): mock `post_signed` returns `{"ok": False, "error": "..."}` — function returns ok=False without raising.

## Todo

- [ ] Write `campaign_push.py` (≤150 lines)
- [ ] Write unit tests `test_campaign_push.py`
- [ ] Confirm `quota_used=0` on push with user (see Open Questions in plan.md)

## Success Criteria

- `push_campaign` returns `{"ok": True}` when Worker mock returns 200.
- `push_campaign` returns `{"ok": False, "skipped": False, "error": ...}` on HTTP error — does not raise.
- `push_campaign` returns `{"ok": False, "skipped": True}` when `HUG_WORKER_URL` unset.
- `push_all_campaigns` pushes all non-archived rows in one batch call.
- All tests pass without a live Worker.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| quota_used reset to 0 on every campaign edit | High (certain) | Medium | Document in UI ("chỉnh sửa sẽ reset bộ đếm quota_used về 0 trên edge — xác nhận?"). Flag in Open Questions. |
| Worker /hug/campaign/upsert rejects unknown extra fields | Low | Low | Edge uses `INSERT OR REPLACE` on explicit column list; extra JSON keys ignored by D1 |
| Batch size: all campaigns pushed at once | Low | Low | Campaign count ≤ 50 expected; no chunking needed. Add comment for future |

## Security Considerations
- HMAC secret never sent to browser; lives in `.env` server-side only.
- `post_signed` already enforces `User-Agent: FineJapan-Hug-Push/1.0` (Cloudflare Bot Fight Mode bypass).

## Next Steps
- Phase 4 UI save handler imports and calls `push_campaign`.
- Future: add Worker GET `/hug/campaign/list` route to fetch `quota_used` before edit (removes the quota_used reset limitation).
