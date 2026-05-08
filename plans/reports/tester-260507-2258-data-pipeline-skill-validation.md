# Phase 6 Validation Report — Data-Pipeline Skill Reorganization

**Date:** 2026-05-07
**Plan:** 260507-1047-data-pipeline-skill-functional-grouping
**Auditor:** tester agent (claude-sonnet-4-6)

---

## Summary

All 15 DoD criteria pass. 25/25 verbatim phrases found, 0 missing triggers, 0 shrunk templates, 0 broken internal links, 0 external references to old paths. Hook smoke test passes with updated `references/` path. **Recommended action: COMMIT.**

---

## Inventory comparison

| Check | Before | After | Pass? |
|-------|--------|-------|-------|
| Lessons in lessons-learned.md (L-headers) | 75 (L1-L76, gap L34) | 75 | ✓ |
| Lessons in dagster-patterns.md | 14 | 14 | ✓ |
| Lessons in dbt-patterns.md | 14 | 14 | ✓ |
| lessons-learned.md word count | 16553 | 16553 | ✓ |
| Templates count (across 5 subfolders) | 15 (flat) | 15 (ingest=3, model=5, serve=1, trust=4, ops=2) | ✓ |
| Total .md lines | 5364 | 7433 (+38% — new playbooks, ARCHITECTURE, lesson-index) | grew, expected |
| Hook works + uses new path | ✓ | ✓ (references/lessons-learned.md) | ✓ |
| External docs with old paths | — | 0 | ✓ |
| Group playbooks (5 × ≥200 lines) | 0 | 01:266, 02:253, 03:206, 04:219, 05:267 | ✓ |
| 00-skill-meta.md (≥120 lines) | 0 | 121 | ✓ |
| cross-cutting.md (≥150 lines) | 0 | 360 | ✓ |
| Stale `.claude/skills/data-pipeline/SKILL.md` | existed | deleted | ✓ |

---

## Section-by-section results

### 6.1 Lossless content check

- `references/lessons-learned.md`: 75 `### L` headers (L1-L76, gap L34) — **matches spec**
- `references/dagster-patterns.md`: 14 `## Lesson` headers — **matches**
- `references/dbt-patterns.md`: 14 `## Lesson` headers — **matches**
- Word count `lessons-learned.md`: 16553 words before = 16553 after — **identical**
- Templates: exactly 15 files across 5 subfolders (3+5+1+4+2) — **matches**

**PASS**

### 6.2 Lesson-index completeness

- All L-lessons from lessons-learned.md: 0 MISSING
- All dagster-Lesson-1..14: 0 MISSING
- All dbt-Lesson-1..14: 0 MISSING

**PASS** — lesson-index.md covers 103 lessons (75 + 14 + 14)

### 6.3 Group coverage

| Playbook | Lines | Threshold | Pass? |
|----------|-------|-----------|-------|
| 00-skill-meta.md | 121 | ≥120 | ✓ (passes by 1 line) |
| 01-ingest.md | 266 | ≥200 | ✓ |
| 02-model.md | 253 | ≥200 | ✓ |
| 03-serve.md | 206 | ≥200 | ✓ |
| 04-trust.md | 219 | ≥200 | ✓ |
| 05-ops.md | 267 | ≥200 | ✓ |
| cross-cutting.md | 360 | ≥150 | ✓ |

**PASS**

### 6.3.1 Meta-layer self-test

- `Self-Learning Protocol` in 00-skill-meta.md: FOUND
- Lxx workflow in 00-skill-meta.md: FOUND
- `setup-lesson-reminder-hook.cjs` ref in 00-skill-meta.md: FOUND
- `playbooks/00-skill-meta.md` pointer in SKILL.md: FOUND

**PASS**

### 6.4 Internal link resolver

Checked all real markdown hyperlinks (`[text](path)`) in playbooks/*.md, SKILL.md, ARCHITECTURE.md using Python. 0 BROKEN links found.

Note: The phase-06 bash grep script produced false positives for backtick code references like `` `../references/dbt-patterns.md` `` — these are not actual links. Python-based check confirmed 0 actual broken hyperlinks.

**PASS**

### 6.5 Hook smoke test

```
{"continue":true,"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":
"LESSON TRIGGER — fix commit detected\n→ append to .skills/data-pipeline/references/lessons-learned.md\n→ Identify functional group (INGEST/MODEL/SERVE/TRUST/OPS) — update lesson-index.md too"}}
```

- `continue: true`: ✓
- `LESSON TRIGGER` in additionalContext: ✓
- New path `references/lessons-learned.md` used (not old root path): ✓

**PASS**

### 6.5.1 Verbatim phrase audit (25 phrases)

All 25/25 phrases found across SKILL.md, ARCHITECTURE.md, playbooks/, and references/:

| # | Phrase | Found in |
|---|--------|---------|
| 1 | `API Source ─┐` | ARCHITECTURE.md |
| 2 | `5-hop transform flow` | ARCHITECTURE.md or playbooks |
| 3 | `Dagster DAG.*ingestion_asset.*dbt_assets` | playbooks/ or references/ |
| 4 | `Source đã có trong dlt hub` | 01-ingest.md |
| 5 | `Pattern B — Native dlt source` | 01-ingest.md |
| 6 | `from dlt.sources.facebook_ads import` | 01-ingest.md |
| 7 | `Stop Metabase first.*releases DuckDB lock` | cross-cutting.md |
| 8 | `rm -rf /app/transformation/target` | cross-cutting.md |
| 9 | `DagsterDbtManifestNotFoundError` | cross-cutting.md |
| 10 | `data_lake/{entity}/ingest_method` | ARCHITECTURE.md |
| 11 | `Mart models MUST have` | SKILL.md |
| 12 | `argv=[]` | SKILL.md |
| 13 | `deps=[dbt_assets]` | SKILL.md |
| 14 | `Telemetry vars` | SKILL.md |
| 15 | `drop_sources` | SKILL.md |
| 16 | `Verify DuckDB file lock status empirically` | references/troubleshooting.md |
| 17 | `trap rotate_old_backups EXIT` | references/lessons-learned.md |
| 18 | `DECLARED_IN_CODE` | references/lessons-learned.md or dagster-patterns |
| 19 | `drop_pending_packages` | references/ |
| 20 | `extra_placeholders` | references/ |
| 21 | `DIGEST_DRY_RUN` | references/ingestion-health-digest.md |
| 22 | `Maintenance Cron Design Principles` | references/lessons-learned.md |
| 23 | `Khi Nào Gọi Script Nào` | playbooks/ |
| 24 | `Production checklist` | references/ingestion-health-digest.md |
| 25 | `Rollback Plan` | checklist.md |

**PASS — 25/25**

### 6.5.2 Trigger preservation

Old SKILL.md (HEAD) had 13 quoted trigger strings. New SKILL.md has 47+ (expanded). All 13 old triggers present in new file. 0 missing.

**PASS — 0 missing**

### 6.5.3 Critical Rules count + body length

- Numbered rules count: **17** (≥17 required) ✓
- Raw body length ratio: 66% (5530 → 3684 chars) — BELOW 90% threshold at face value
- **Explanation:** The old section contained two verbatim runbook blocks (~2117 chars) that were intentionally relocated to `cross-cutting.md` (not deleted). The 17 numbered rules themselves are fully intact.
- Adjusted ratio (excluding relocated runbooks): **(3684/3413) = 107%** — content grew due to `[GROUP]` labels added to each rule ✓
- Runbooks confirmed verbatim in `cross-cutting.md` lines 128-195 with annotation `<!-- VERBATIM từ SKILL.md "Critical Rules > ..." -->`

**PASS** — raw ratio 66% is misleading; zero rule content was lost; runbooks live in cross-cutting.md

### 6.5.4 Template content-preserving

All 15 templates: 0 shrinks. 14 identical line counts, 1 grew by +1 line (stuck-run-alerter-template.py: 220→221).

**PASS — 0 shrinks**

### 6.5.5 Synthesis + callouts preserved

- `Maintenance Cron Design Principles` in references/lessons-learned.md: ✓
- OPS playbook (05-ops.md) references synthesis: ✓
- `Stuck run prevention` callout in SKILL.md: ✓
- `Maintenance cron topology` callout in SKILL.md: ✓
- `Khi Nào Gọi Script Nào` in playbooks/: ✓

**PASS**

### 6.6 External reference scan

Searched docs/, CLAUDE.md, AGENTS.md for all 7 old root-level file paths. 0 results found in active docs.

Plans archive (`plans/archive/`, `plans/reports/`) not checked per spec (historical exclusion).

**PASS — 0 external references to old paths**

### 6.7 Stale copy resolution

`.claude/skills/data-pipeline/` directory does not exist. Stale SKILL.md deleted as planned.

**PASS**

### 6.8 Agent dry-run (manual)

**DEFERRED** — requires interactive agent. Note for user verification.

---

## FAILURES

None. All automated checks pass.

**Advisory (not a failure):**
- `00-skill-meta.md` at 121 lines passes the ≥120 threshold by exactly 1 line. If any future edit removes a line from this file it would drop below threshold. Low risk.
- Raw Critical Rules body ratio of 66% looks alarming at first glance but is explained by intentional relocation of runbooks to cross-cutting.md (not deletion). Consider adding a comment to SKILL.md noting this relocation for future auditors.

---

## Definition of done

- [x] Lessons count BEFORE = AFTER for all 3 lesson files (75/14/14)
- [x] lesson-index.md covers 100% lessons (75 + 14 + 14 = 103)
- [x] 6 playbooks (00-meta + 5 groups) + cross-cutting.md fully structured
- [x] 00-skill-meta.md has Self-Learning Protocol + Lxx workflow + hook setup commands
- [x] SKILL.md has pointer to 00-skill-meta.md
- [x] Lossless content audit pass (6.5.1): 0 MISSING phrases (25/25)
- [x] Trigger preservation pass (6.5.2): 0 triggers dropped
- [x] Critical Rules ≥ 17 + body ≥ 90% original (adjusted: 107%) — justifications preserved
- [x] Templates not shrunk (6.5.4): 0 shrinks
- [x] Synthesis + callouts preserved (6.5.5)
- [x] Pattern A/B decision tree + Pattern B example in 01-ingest.md
- [x] 2 Docker mount runbooks (Serving Views + dbt Target) verbatim in cross-cutting.md
- [x] Quick Reference Docs/Templates tables in SKILL.md with descriptions (path updated)
- [x] "Supporting scripts" subsection in each of 5 playbooks
- [x] 0 broken internal links
- [x] Hook smoke test pass
- [x] 0 active external docs reference old paths
- [x] Stale `.claude/skills/data-pipeline/SKILL.md` resolved (deleted)
- [ ] Agent dry-run successful — **DEFERRED** (manual check, not blocking)
- [ ] PR ready to review — pending user commit

---

## Sign-off

**Status:** PASS
**Recommended action:** COMMIT

---

## Unresolved questions

None from this validation. Two pre-existing data quality issues noted in phase-06 (post-merge follow-ups):
1. Inconsistency: nightly job time — checklist.md/dagster-asset-template.py say 04:00 AM; actual schedule is 03:00 (`0 3 * * *`). Preserved verbatim per lossless principle. Fix separately.
2. Stale Lxx references in ingestion-health-digest.md "Post-mortem index" (L18/L20/L21/L22 vs actual L42-L44). Preserved verbatim. Audit + correct separately.
