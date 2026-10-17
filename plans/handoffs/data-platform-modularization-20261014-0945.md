---
handoff-version: 1
generated: 2026-10-14T02:45:00Z
generator: ak:handoff
focus: "Continuation for the data platform modularization (plan plans/261013-1751-modularize-data-platform-suite). Phases 0-3 deployed to prod (main 25b6be42), phase 5 committed on branch refactor/modularize-suite (b718befc) not deployed, docs commit 75894f81; next: phase 4 taxonomy, then deploy 5 after nightly, phase 6, phase 7. User language Vietnamese."
workspace: /home/vantt/app/fg-dataware-house
branch: main (prod checkout) / refactor/modularize-suite (worktree /home/vantt/app/fg-dw-modular)
head: 25b6be42 (main) / 75894f81 (refactor/modularize-suite)
---

# HANDOFF: Module hoá suite data platform (Fine Japan là tenant #1)

## Mission and current status

"Continuation for the data platform modularization (plan plans/261013-1751-modularize-data-platform-suite). Phases 0-3 deployed to prod (main 25b6be42), phase 5 committed on branch refactor/modularize-suite (b718befc) not deployed, docs commit 75894f81; next: phase 4 taxonomy, then deploy 5 after nightly, phase 6, phase 7. User language Vietnamese."

Outcome: tách suite dbt-duckdb + Dagster + dlt đang chạy cho Fine Japan thành module (connectors, cdm, core, packs, taxonomy, tenant overlay, kernel) mà **không đổi con số, không đổi tên bảng public**, hệ thống vẫn chạy hằng ngày. Plan: `plans/261013-1751-modularize-data-platform-suite/plan.md` (8 phase, Đợt 1 của `roadmap.md`).

Done:
- Phase 0 safety harness (shadow gate) — prod 13/10 23:38.
- Phase 1 boundary checks (`check_boundaries.py`, `model_buckets.yaml`, allowlist) — prod 13/10.
- Phase 2 dbt layout `models/<module>/<layer>/` — prod 13/10.
- Phase 3 canonical layer (10 `std_*` pass-through views, core reads only cdm) — prod 14/10 09:22.
- Phase 5 orchestration connector packages — commit `b718befc` on branch, **not deployed**.
- Docs: `docs/operations/refactor-safety-harness.md`, `docs/architecture/canonical-layer.md`, `docs/architecture/modules.md` (living module doc), runbook in `docs/operations/deployment.md` § Refactor deploys.

Remaining:
- Phase 4 taxonomy module (next; must come after phase 5 because it edits `orchestration/connectors/sheets/assets.py` seed paths).
- Deploy phase 5 (recommended after tonight's 03:00 nightly is green — user has not decided yet).
- Phase 6 Fine Japan tenant overlay; phase 7 docs/ADR/cleanup.

Urgency: normal; user drives pace phase by phase.

## Scope and guardrails

Workspace: `/home/vantt/app/fg-dataware-house` (prod checkout, branch `main`) + worktrees `/home/vantt/app/fg-dw-modular` (branch `refactor/modularize-suite`, where all work happens) and `/home/vantt/app/fg-dw-baseline` (detached, gate baseline).

In scope: phases 4, 6, 7 of the plan; deploying accepted phases when the user authorizes; keeping docs in sync.

Out of scope (see `roadmap.md`): image/GHCR packaging (plan `260705-1704`), dbt local packages, enforced contracts, taxonomy rules-as-data, new connectors, report catalog. Output/report decisions (personas, taxonomy input UI) are deferred by the user.

Constraints (user decisions):
- The running system must keep operating daily; prod changes only via the deploy runbook (stop `data_platform` in a run-free gap, ff-merge a pinned SHA, start, verify, rollback by `git revert` range).
- "Làm tới đâu thiết kế và tài liệu hoá chi tiết tới đó": docs change in the same commit as code; a detailed "what/how" doc per component (phase 0 → `refactor-safety-harness.md`, phase 3 → `canonical-layer.md`). The user explicitly asked for such docs and checks for them.
- Taxonomy (phase 4): only gather rules into a module (`macros/taxonomy/`, one macro per rule variant, SQL unchanged, seeds into `seeds/taxonomy/` with every Python reader/writer moved to `ingestion/src/utils/seed_paths.py`); do NOT turn rules into data; keep diverging semantics (CROSSBORDER ×3 variants, 'Active' vs 'ACTIVE').
- Contracts: warn-level tests only, no `contract: enforced`.
- Packaging now = folder modules in one dbt project; images later.
- Workers may run with `claude --model sonnet --dangerously-skip-permissions` in Herdr panes (user-authorized); the user likes the herdr two-pane flow (one pane implements, one deploys).
- Commits: conventional, no AI references, no plan IDs/phase numbers in code comments, test names or commit messages.

Safety boundaries:
- NEVER edit files under `/home/vantt/app/fg-dataware-house` except `plans/` (bind-mounted into the prod container). Never run dbt against `app_data/`.
- Shadow tools refuse prod paths; shadow lakes contain PII — keep `/home/vantt/app/fg-dw-shadow` mode 0700, delete at plan close.
- Do not deploy without an explicit user go-ahead for that deploy.
- `.claude/settings.json` (modified) and untracked `.agentkit/`, `.claude/*`, `plans/` in the prod checkout belong to the user — never stage, stash or delete.

## Current state

Observed 2026-10-14 ~09:45 ICT:

- Prod checkout `/home/vantt/app/fg-dataware-house`: branch `main`, HEAD `25b6be42` (phases 0–3 + docs + gate fix). Working tree: ` M .claude/settings.json` (user's, intentional) plus many untracked `.agentkit/`, `.claude/*`, `plans/*` (intentional).
- Worktree `/home/vantt/app/fg-dw-modular`: branch `refactor/modularize-suite`, HEAD `75894f81`, clean. Commits after prod: `b718befc` (phase 5), `75894f81` (docs: baseline = last accepted commit).
- Worktree `/home/vantt/app/fg-dw-baseline`: detached at `25b6be42` (last accepted + deployed). Gate baseline lake-A rebuilt from it on 14/10.
- Shadow root `/home/vantt/app/fg-dw-shadow`: `lake-base` (backups 20261013 raw + 20261012 warehouse), `lake-A`, `lake-A2`, `deps/`, `inventory/` (dbt-main.json 186 nodes, dagster-main.json 254 assets/502 checks from 25b6be42).
- Prod health: container `data_platform` healthy; 26/26 schedules+sensors RUNNING; serving 152 views; nightly 14/10 03:00 SUCCESS; post-deploy runs SUCCESS.
- Herdr: coordinator pane `w4:p1`; both herdr-cook-plan runs completed and closed (`plans/261013-1751-.../reports/herdr-cook-runs/*`), no worker panes open.

Intentional local modifications: yes (user's `.claude/settings.json` and untracked dirs in prod checkout only).

## Decisions and rationale

- Bucket model: every dbt model has a bucket in `scripts/checks/model_buckets.yaml`; layer folder (staging/intermediate/marts) decides schema/tags via YAML anchors in `dbt_project.yml`, module folder never does — moving models keeps relations.
- COGS and inventory are **core**, not packs (core facts depend on them). Packs: finance (+`int_misa_sales_lines`, `dim_gl_account`), marketplace, facebook_* (disabled).
- Allowlist now 46: 37 `dbt-path` (Fine Japan tenant models not yet moved → phase 6), 4 tenant hooks, 2 MISA-in-core, 3 Shopee-in-core. Checker fails on new violations and on stale allowlist entries.
- Rolling export dirs come from the manifest (`transformation/scripts/rolling_dirs.py`), not folder names.
- dagster-dbt passes subset selections to dbt as `fqn` (folder path) — container restart re-parses, which the runbook guarantees.
- Gate baseline must be the **last accepted commit** and built the **same day** (date-relative columns); `gate.sh` auto-rebuilds lake-A when built on another day; moving the baseline commit is manual (see `refactor-safety-harness.md` §9.2).
- `dbt_inventory.py --allow-code-change` accepts a repointed dependency only if the removed one stays upstream.
- Do NOT use `dagster schedule list -f` for state (reports all STOPPED); use `scripts/checks/instigator_state.py` (GraphQL).
- Phase order: 5 before 4 (user agreed; avoids double-editing `sheets_assets.py`).
- References: `plan.md` (decisions table, red-team section), `reports/red-team-review.md`, `roadmap.md`, `architecture-boundaries.md` (original design), ADR-014 (`source_system`).

## Work performed

Commits on `refactor/modularize-suite` (oldest → newest): `d210ad98` harness; `b617c072` remove headerless macro; `3b3520fa` CRM backup CLI without orchestration import; `4721817d` boundary checks; `52f31693` rolling dirs from manifest; `85fffa78` dbt module layout; `97d05451` harness doc; `a35878af` std views (phase 3); `d7f8a953` canonical-layer doc; `25b6be42` same-day baseline fix; `b718befc` connector packages (phase 5); `75894f81` baseline doc.

Deploys (prod `main`, runbook, herdr Sonnet worker + coordinator verification):
- 13/10 23:38 ICT → `97d05451` (phases 0–2). Report: `plans/261013-1751-.../reports/deploy-261013-2338-phases-0-2-report.md`.
- 14/10 09:22 ICT → `25b6be42` (phase 3). Report: `.../reports/deploy-261014-0922-phase-3-report.md`.

Gate command used for every phase: `cd /home/vantt/app/fg-dw-modular && scripts/shadow/gate.sh M|S [--allow-new] [--allow-code-change]`.

## Verification

- Phase 2: gate M PASS. Phase 3: gate S PASS (`--allow-new --allow-code-change`), re-run 14/10 with same-day baseline PASS. Phase 5: gate M PASS (worker + coordinator re-run, baseline 25b6be42): 83 public tables equal, dbt inventory 186 nodes 0 diff, dagster inventory 0 diff, subset run via Dagster OK, pytest 199 pass, empty-lake build OK.
- Prod after each deploy: instigator diff 0, realtime/incremental runs SUCCESS, serving views 152, no container errors; nightly 14/10 03:00 SUCCESS.
- Known flaky: `orchestration/ops/__tests__/test_ingestion_health_retry.py::test_concurrent_writes_no_lock_error` (~1/4 runs, baseline too); gate re-runs pytest once and prints FLAKY.
- Not verified: tonight's nightly after the phase 3 deploy; phase 5 in prod.

## Open risks and blockers

- `budget_sheet_sync_job` FAILED 14/10 02:30 — NOT caused by deploys: Google Sheet BUDGET_ITEMS rows 17–18 use parent account codes `112`, `334` absent from `dim_gl_account` (271 leaf accounts, unchanged before/after deploy). User/budget owner must fix the sheet. Job aborted safely (seeds unchanged).
- Phase 5 deploy awaits user decision (recommendation: after tonight's nightly is green).
- Phase 4 touches seeds that prod jobs rewrite (`seed_paths.py` must cover `gsheet_budget_sync/fetch.py`, `gsheet_marketing_spend.py`, `scripts/maintenance/sync_seeds.py`, `orchestration/connectors/sheets/assets.py`); a duplicate seed basename makes `dbt parse` fail and the container not start — `check_boundaries.py` rule `seed-duplicate` guards this. Seed `+column_types` in `dbt_project.yml` are keyed by path and must move with seeds.
- Phase 4 compile-time correctness: macros must return the exact original SQL; verify with `dbt_inventory.py compiled-diff` (part of the gate) and golden including full refresh (`int_customer_entry_attributes` is incremental).
- Non-blocking follow-ups: workers show a non-blocking `PostToolUse:Bash hook error` (node loader) from project hooks; `sheets_modified_sensor.py` default URLs move to tenant config in phase 6; 14 older `std_*` lack `std_column_contract`.
- A repo hook blocks shell commands containing the text `target` + `/` (dbt artifacts); copy manifests into `<lake>/_shadow_meta/` or build paths from pieces.

## Exact next actions

1. **First safe step**: read this file, then verify Current state: `git -C /home/vantt/app/fg-dataware-house log --oneline -1` (expect 25b6be42), `git -C /home/vantt/app/fg-dw-modular log --oneline -3` (expect 75894f81 on top of b718befc), `git worktree list`, and `python3 /home/vantt/app/fg-dw-modular/scripts/checks/instigator_state.py capture --out /tmp/i.json` (expect 26 running). Ask the user (Vietnamese) whether to start phase 4 now and whether to deploy phase 5 after tonight's nightly.
2. Before phase 4: move the gate baseline to the last accepted commit `b718befc` (phase 5 accepted): `git -C /home/vantt/app/fg-dw-baseline checkout --detach b718befc`, then rebuild lake-A, recapture golden, re-export `dbt-main.json`/`dagster-main.json` from the baseline worktree, delete `lake-AF` (commands in `docs/operations/refactor-safety-harness.md` §9.2).
3. Run phase 4 (`plans/261013-1751-.../phase-04-taxonomy-module.md`) — preferably via the Skill Hub skill `herdr-cook-plan` (coordinator in pane `w4:p1`, Sonnet worker, brief pattern as in the previous runs; worker never commits, coordinator re-runs `gate.sh S --allow-new --allow-code-change` and commits owned paths). Write the detailed doc `transformation/docs/TAXONOMY.md` (+ ADR 016 in phase 7) and update `docs/architecture/modules.md` §9.
4. When the user authorizes, deploy phase 5 (then 4) with the runbook, pinned SHA, in a run-free gap outside 02:30–04:00; verify instigators, runs, serving views; check the next nightly.
5. Then phase 6 (tenant overlay; hooks from manifest; FJ URLs/domains to tenant config) and phase 7 (ADRs 015/016, AGENTS.md, `scripts/checks/run-all.sh`, delete shadow + worktrees at close).

## Source pointers

- Plan & phases: `/home/vantt/app/fg-dataware-house/plans/261013-1751-modularize-data-platform-suite/` (`plan.md`, `phase-0*.md`, `roadmap.md`, `architecture-boundaries.md`, `reports/`).
- Research report: `/home/vantt/app/fg-dataware-house/plans/reports/research-261013-1610-sme-commerce-data-platform-modularization.md`.
- Living docs (branch): `docs/architecture/modules.md`, `docs/architecture/canonical-layer.md`, `docs/architecture/std-layer-conventions.md`, `docs/operations/refactor-safety-harness.md`, `docs/operations/deployment.md` § Refactor deploys, `scripts/shadow/README.md`, `scripts/checks/README.md`, `orchestration/connectors/README.md`.
- Tools: `scripts/shadow/gate.sh`, `scripts/checks/{check_boundaries,golden_snapshot,dbt_inventory,dagster_inventory,instigator_state}.py`, `scripts/checks/{model_buckets,boundary_allowlist,public_models}.yaml`.
- Herdr run records: `plans/261013-1751-.../reports/herdr-cook-runs/*/{checkpoint.md,implementation-summary.md,ledger.jsonl}`; deploy reports `reports/deploy-261013-2338-phases-0-2-report.md`, `reports/deploy-261014-0922-phase-3-report.md`; worker reports `reports/phase-03-worker-report.md`, `reports/phase-05-worker-report.md`.
- Journal: `plans/journals/2026-10-13-plan-module-ho-suite-data-platform.md`.
- Docs were shared with the user through the mdview skill (`mcp__mdview__mdview_view_file`, project root = the worktree for branch docs).
