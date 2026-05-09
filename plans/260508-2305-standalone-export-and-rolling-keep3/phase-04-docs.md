# Phase 04 — Documentation Update

## Context Links

- Plan: [plan.md](plan.md)
- Existing docs: `docs/architecture/data-flow.md`, `docs/architecture/locking-and-concurrency.md`, `.skills/data-pipeline/playbooks/03-serve.md`

## Overview

- **Priority:** P2
- **Status:** Pending (gated by Phase 1-3 complete)
- **Description:** Update architecture docs để reflect 2 cơ chế mới: standalone export branch + rolling KEEP=3. Cập nhật skill playbook để future agents hiểu pattern.

## Key Insights

- Existing `data-flow.md` mô tả serving = `olap.duckdb` (views) + Metabase. Cần thêm branch standalone export → fileserver.
- Existing `locking-and-concurrency.md` đã verify Metabase coexistence. Cần thêm 1 dòng cho standalone build (read-only ATTACH, file mới — no lock impact).
- Skill playbook `03-serve.md` là canonical reference cho serving patterns. Add section "Standalone Export Pattern" để codify.

## Requirements

- Tất cả markdown updates < 100 lines bổ sung tổng cộng (concision principle).
- Diagrams (ASCII) khớp implementation thực.
- URL examples đầy đủ (cả internal + public form `https://files.etl.local/...`).

## Related Code Files

**MODIFY (markdown only):**
- `docs/architecture/data-flow.md` — append "Standalone Export Branch" section
- `docs/architecture/locking-and-concurrency.md` — add row to Layer Map + 1 paragraph for new asset
- `docs/operations/operations.md` — add ops note: how to download, where to find URL/auth
- `.skills/data-pipeline/playbooks/03-serve.md` — add "Standalone Export Pattern" + "Rolling Retention Tuning"
- `AGENTS.md` (project root) — quick reference if standalone is operationally important

## Implementation Steps

1. **`docs/architecture/data-flow.md`:**
   - Append section after current "Serving Layer":
     ```
     ### Standalone Export Branch
     
     `sapo_standalone_export` (Dagster asset, downstream of `sapo_serving_db`)
     materializes all olap.duckdb views into a self-contained file:
     
       app_data/data_lake/serving/standalone/sapo_export_<TS>.duckdb
                                              sapo_export_latest.duckdb (alias)
     
     Exposed read-only via `fileserver` service at https://files.etl.local/.
     Use case: offline / AI analysis without parquet path dependency.
     ```
   - ASCII diagram update.

2. **`docs/architecture/locking-and-concurrency.md`:**
   - Add row to Layer Map table:
     | OS file | Standalone export build (single-writer on tmp + os.replace) | `scripts/provisioning/build_standalone_export.py` | writer isolation | ✅ |
   - Add 1 paragraph in §"Detailed Inventory" → "DB-level":
     ```
     #### sapo_export_*.duckdb (standalone export)
     
     - Path: /app/var/data_lake/serving/standalone/sapo_export_*.duckdb
     - Writers: build_standalone_export.py (one tmp file per run, atomic os.replace)
     - Readers: external clients via fileserver (HTTP, file copies — no lock)
     - Inputs: olap.duckdb ATTACH READ_ONLY (no lock per L18) + parquet mmap (no lock)
     - No lock contention possible by design — all inputs read-only, output is fresh file.
     ```

3. **`docs/operations/operations.md`:**
   - Add subsection "Downloading Standalone Export":
     ```
     URL: https://files.etl.local/sapo_export_latest.duckdb
     Auth: basic — credentials stored in 1Password "Data Platform / fileserver"
     
     Download: curl -u $USER:$PWD <url> -o sapo.duckdb
     Open: duckdb sapo.duckdb -c "SELECT count(*) FROM fact_orders;"
     ```

4. **`.skills/data-pipeline/playbooks/03-serve.md`:**
   - New section "Pattern 4 — Standalone Export":
     - Problem statement (parquet path dependency)
     - Mechanism (ATTACH READ_ONLY + CREATE TABLE)
     - Lock analysis (no contention by design)
     - Use cases (offline analysis, AI tools, distribution)
   - Update "Rolling Self-Refresh" section: note `ROLLING_KEEP_VERSIONS=3` default, rationale (rollback + audit, not crash safety).

5. **`AGENTS.md` (root):**
   - Update §"Architecture & Deployment Criticals" → "Dual DuckDB Strategy" — add 3rd file:
     ```
     3. Standalone Export DB (data_lake/serving/standalone/sapo_export_*.duckdb):
        Self-contained snapshot for offline / AI analysis. Built nightly.
        Exposed via https://files.etl.local/.
     ```

6. **Verify links:** sau khi viết xong, grep tất cả relative paths trong docs để confirm chính xác.

## Todo List

- [ ] Update `data-flow.md` (append Standalone Export Branch section)
- [ ] Update `locking-and-concurrency.md` (Layer Map row + paragraph)
- [ ] Update `operations.md` (download instructions + auth)
- [ ] Update skill playbook `03-serve.md` (Pattern 4 + retention notes)
- [ ] Update root `AGENTS.md` (Dual DuckDB → Triple, brief)
- [ ] Verify all relative links resolve

## Success Criteria

- New agent reading docs cold understands standalone export purpose, location, lock semantics in < 5 minutes.
- Ops team can download + use file from URL + auth alone (no Slack ping needed).
- Future serving improvements reference `03-serve.md` Pattern 4 as canonical.

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Docs drift after subsequent code changes | Cross-link doc → code path; mention version in skill playbook |
| Credential exposure in docs | Reference 1Password / vault entry, never inline credentials |

## Security Considerations

- Không inline password trong markdown.
- Reference vault/secret manager for credential lookup.
- IP allowlist policy (nếu có) document trong ops doc.

## Next Steps

- Project complete — mark plan as DONE.
- Optional follow-ups (out of scope):
  - Atomic `.tmp+rename` cho rolling COPY (defer until incident)
  - Sensor-based standalone export ad-hoc trigger
  - MotherDuck integration (push file lên cloud cho remote query)
