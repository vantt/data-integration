---
phase: 3
title: "DR Runbook"
status: pending
priority: P2
effort: "0.5d"
dependencies: [1, 2]
---

# Phase 3: DR Runbook

## Overview
A concise operator runbook so a human can **actually recover the CRM in a real incident** (not just run the automated drill). Plus how to run backups + the verify drill, and how to read results. User explicitly asked for a manual-recovery guide.

## Requirements
- **Functional:** step-by-step real-incident restore of prod CRM from a backup; how to take a backup; how to run + interpret the restore-verify drill; retention/locations; manifest meaning.
- **Non-functional:** copy-paste-able commands; safe (rollback/abort points); honest about scope (what is / isn't recoverable).

## Architecture
- **Doc:** `crm/docs/backup-restore-runbook.md` (CRM-owned docs; linked from `crm/README.md` and `docs/operations/`).
- Sections:
  1. **What's protected** — `crm.db` (source of truth) + `cache.db` (snapshot); NOT recovered here: warehouse/`olap.duckdb` (separate), regenerable cache (rebuildable via `/admin/refresh`).
  2. **Take a backup** — the Phase-1 command + where it lands + rotation.
  3. **Verify a backup** — the Phase-2 drill command; what PASS/FAIL means; "untested backup = no backup".
  4. **Real-incident restore** (the critical part) — ordered, safe procedure:
     - Stop the live `crm` container.
     - **Safety copy** current `crm_data` aside first (in case the restore is wrong).
     - Restore `crm.db`(+`cache.db`) from the chosen backup into the `crm_data` volume.
     - Start `crm`; confirm migrations OK + `/health` healthy + spot-check data.
     - Rollback: if wrong, stop, restore the safety copy, start.
  5. **Cadence + retention** recommendation; where backups live; manifest fields explained.
  6. **Future:** how this wires into Dagster (pointer to Phase 4 / scheduling).

## Related Code Files
- Create: `crm/docs/backup-restore-runbook.md`
- Modify: `crm/README.md` (link the runbook), `docs/operations/operations.md` (cross-link)

## Implementation Steps
1. Draft the runbook with exact commands from Phases 1-2 (verified against the real CLI flags).
2. Dry-run the **real-incident restore** procedure end-to-end against a throwaway/staging crm_data to confirm every command + the safety-copy/rollback path actually works.
3. Cross-link from `crm/README.md` + ops docs.

## Success Criteria
- [ ] Runbook lets someone unfamiliar restore CRM from a backup using only the doc.
- [ ] The real-incident restore procedure was **dry-run executed once** (not just written) and works, including rollback.
- [ ] Commands match the actual Phase-1/2 CLIs; no placeholders.

## Risk Assessment
- **Runbook drift** → commands diverge from code over time; keep commands minimal + point to the modules as source of truth.
- **Untested procedure** → mitigated by the mandatory dry-run in step 2 (don't ship an unrun runbook).

## Red-Team Hardening (must-fix, 2026-06-24)
- **"This is NOT full DR" section (honesty).** Backups are local-only on the same Windows host as prod → host/disk loss = total loss. State this explicitly + give a **minimal offsite path** (e.g. robocopy to a NAS, or upload the snapshot dir to R2/S3). Even one offsite copy changes "checkpoint" into "DR".
- **Mandatory post-restore cache refresh.** After restoring (cache.db is a *stale* warehouse snapshot), the runbook MUST run `reverse_etl` + `sync_parties` (or `POST /admin/refresh`) before routing real traffic — else the app serves stale/partial warehouse-derived data. Drill report labels cache age.
- **Old-backup recovery (the realistic case).** Add a procedure for restoring a backup from N migrations ago against current code: forward-migrate, watch for migration failure, and a rollback/abort step if migration corrupts data. State the **RPO** explicitly (keep-N × backup interval = max data loss window; silent corruption older than retention = unrecoverable).
- **"Are backups even running?" check.** A backup-age check (alert if newest backup > SLA) — silent backup stoppage is invisible otherwise (same failure class as the zombie-run incident). Document the check + where the alert goes.
- **Authority over `backup.sh`.** State that this tool's snapshots are authoritative for CRM and the raw `crm_data` legs in `backup.sh`/`backup.ps1` are deprecated/disabled (Phase 1) — so an operator never restores from the wrong/torn copy mid-incident.
