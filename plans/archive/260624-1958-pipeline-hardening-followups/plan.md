# Pipeline Hardening — Follow-ups

**Created:** 2026-06-24 | **Status:** DONE — archived. Secret rotation + remaining infra items deferred indefinitely (out of scope for this plan). | **Branch:** main | **Predecessor:** [260624-1158-pipeline-health-remediation](../archive/260624-1158-pipeline-health-remediation/plan.md) (DONE, archived)

Unfinished / deferred items split out from the completed health-remediation plan. Execute per-item with approval.

## 🚨 CRITICAL — secret rotation (from push-protection incident 2026-06-24)
- [ ] **Rotate the Cloudflare API token** — a live token (`cfut_…`) was found exposed (audit finding C1): in `app_data/backups/*/config/.env.docker` (7 plaintext copies), the live `.env.docker`, and prior git history (scrubbed from origin via filter-branch, but treat as compromised). It controls ACME DNS-01 cert issuance for `*.lan.fwg.vn` → compromise = subdomain takeover. **Rotate in Cloudflare dashboard**, update `.env.docker` (+ root `.env`), restart Caddy/ACME consumer.
- [ ] **Fix C1 root cause** — backup script copies `.env.docker` verbatim into `app_data/backups/`. Change `scripts/backup/backup.sh` to exclude/sanitize secrets (copy a redacted manifest, or encrypt the archive). Add a backup-content audit.
- [ ] **Local git hygiene** (optional) — token still in local object store: `git reflog expire --expire=now --all && git gc --prune=now`. (Origin already clean.)

## Activation — code done, needs an infra step
- [?] **Apply `evidence` non-root** — `Dockerfile.evidence` has `USER 1001` (committed); rebuild status unverified. Run `docker compose up -d --build evidence` if not done.
- [ ] **Non-root `data_platform` / `crm` / `rill`** — skipped during hardening: they write to named volumes (monitoring_db, crm_data) owned by root → non-root needs a uid + volume-ownership strategy. Design + test carefully (must not break Dagster/CRM writes).

## Deferred (user decision)
- [ ] **[Google Sheets → service account](phase-01-gsheets-service-account.md)** — DEFERRED: needs a GCP service-account JSON key. Removes public-link exposure of 5 sheets; also resolves the tracked-`config.toml`-sheet-IDs item.
- [⏸️] **CRM Messenger ingest HMAC** (`conversation_handler.py:101`) — no live Messenger data flow yet; add `X-Hub-Signature-256` before go-live.
- [⏸️] **Ports `0.0.0.0` bypass Caddy** — firewall-check deferred; bind app ports to `127.0.0.1` so only Caddy is exposed.
- [ ] **Worker HMAC replay protection** — add timestamp/nonce check (Sapo must send a timestamp header; verify before enforcing, else it breaks the live HMAC).
- [ ] **`HUG_ZALO_OA_URL` placeholder** (`wrangler.toml:23`) — set the real Zalo OA URL (customer-facing link currently broken).
- [ ] **sheets assets `rows_written=None`** — runner returns no row count → freshness-only signal. Wire row counts through `gsheet_*.run()`.
- [ ] **Modularize >200 LOC files** — e.g. CRM `screen_customer_360.py` (598), some ingestion files. Low priority, churn risk.

## Notes
- Everything else from the audit is DONE + deployed + verified (see archived predecessor plan + reports in `plans/reports/`).
