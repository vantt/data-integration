# Phase 5 — Update Entry Points

**Status:** pending
**Depends on:** Phase 4 (paths đã settle)
**Blocks:** Phase 6
**Estimated effort:** 2-3 giờ (rewrite SKILL.md + nhiều cross-references)

## Mục tiêu

Sau khi files đã move (Phase 4), update tất cả tham chiếu nội bộ + external để skill mới hoạt động trơn tru. Không có "half-broken" state.

## Steps

### 5.1 Rewrite `SKILL.md` (root entry point)

#### Preservation list (MANDATORY — không rewrite, chỉ relocate hoặc keep)

Trước khi viết SKILL.md mới, phân loại từng item của bản gốc:

| # | Item gốc (line) | Disposition |
|---|----------------|-------------|
| 1 | Title + 1-line description (L1-3) | KEEP root SKILL.md (nâng cấp 5-group flavor) |
| 2 | "Kích hoạt" triggers (L6-13) | KEEP all + reorganize by group; KHÔNG drop trigger nào |
| 3 | "Environment Setup (one-time per machine)" (L16-32) | KEEP root SKILL.md verbatim + thêm pointer `playbooks/00-skill-meta.md` |
| 4 | "Architecture Overview" ASCII diagram + 5-hop flow + Dagster DAG note (L36-66) | MOVE verbatim → `ARCHITECTURE.md` (Phase 2 đã include) |
| 5 | "Bước 1: Chọn Pattern Ingestion" decision tree (L70-91) | MOVE verbatim → `playbooks/01-ingest.md` (Phase 3.1 đã include) |
| 6 | "Pattern B" inline 5-line example (L82-88) | MOVE verbatim → `playbooks/01-ingest.md` |
| 7 | "Quick Reference Docs" table (L97-109) | KEEP root SKILL.md, chỉ update path → `references/{file}.md`. **Descriptions verbatim.** |
| 8 | "Quick Reference Templates" table (L111-127) | KEEP root SKILL.md, update path → `templates/{group}/{file}`. **Descriptions verbatim.** |
| 9 | "Key Paths > Local Development" tree (L131-184) | KEEP root SKILL.md verbatim |
| 10 | "Key Paths > Docker Volume Mapping" + "Path Resolution Pattern" (L186-214) | KEEP root SKILL.md verbatim |
| 11 | "Critical Rules > Serving Views & Absolute Paths" runbook (L220-247) | MOVE verbatim → `playbooks/cross-cutting.md` Runbook A (Phase 3.6 đã include) |
| 12 | "Critical Rules > dbt Target Cache & Rolling Parquet Paths" runbook (L249-271) | MOVE verbatim → `playbooks/cross-cutting.md` Runbook B (Phase 3.6 đã include) |
| 13 | 17 numbered Critical Rules — **FULL TEXT including justifications/dates/examples** (L273-290) | KEEP root SKILL.md với **NGUYÊN VĂN body** mỗi rule + thêm `[GROUP]` tag. KHÔNG đơn giản hóa thành table. Rule 11's "post-mortem 2026-04-08/09" example PHẢI giữ. |

**Sau preservation:** SKILL.md mới ≈ original content + 5-group navigation layer + reduced Pattern A/B section (đã move sang INGEST playbook). Net change: SKILL.md có thể nhỏ hơn (vì 2 runbooks chuyển sang cross-cutting + Pattern section chuyển sang playbook), nhưng KHÔNG có item nào biến mất.

**Cấu trúc mới:**

```markdown
# Data Pipeline Skill (5 Functional Groups)

Skill hỗ trợ thêm/fix/deploy data pipeline end-to-end. Tổ chức theo **5 nhóm chức năng**:
INGEST · MODEL · SERVE · TRUST · OPS.

## Kích hoạt
[ĐẦY ĐỦ triggers cũ — không drop bất kỳ — phân lại theo group:]

**INGEST:**
- "thêm source mới", "add new ingestion", "integrate [source_name]"
- "envelope schema", "dedup strategy", "auth dlt"
- "webhook consumer", "history log", "file-drop"

**MODEL:**
- "tạo dbt model mới", "thêm src_/stg_/dim_/fact_ model"
- "incremental dbt", "OOM dbt", "rolling snapshots"

**SERVE:**
- "Metabase nhìn dữ liệu cũ", "rolling self-refresh views", "serving DB lock"
- "empty folder", "GC parquet"

**TRUST:**
- "morning digest", "health report", "ingestion_runs", "rows_written=0 bug"
- "daily health card", "Lark/Slack health alert", "per-source SLA", "recon drift report"
- "asset check", "KPI closure"

**OPS:**
- "schedule", "sensor", "stuck run", "concurrency", "purge", "backup"
- "Dagster asset fail", "schedule offset", "zombie thread"

**Cross-cutting:**
- "DuckDB lock", "Docker mount", "env var", "Windows file lock"

**Meta:**
- "setup hook", "ghi lesson Lxx", "Self-Learning Protocol"

## Quick Start

### Tôi đang làm gì?
| Task | Đọc trước |
|------|-----------|
| Setup máy mới / hook không nhắc / ghi lesson Lxx mới | `playbooks/00-skill-meta.md` |
| Thêm source mới | `playbooks/01-ingest.md` + `checklist.md` |
| Fix dbt | `playbooks/02-model.md` |
| Fix Metabase data cũ | `playbooks/03-serve.md` |
| Health monitoring | `playbooks/04-trust.md` |
| Schedule/sensor | `playbooks/05-ops.md` |
| Lock/path/env issue | `playbooks/cross-cutting.md` |
| Tra Lxx | `lesson-index.md` |

## Architecture
[Link tới ARCHITECTURE.md với mental model 5 nhóm + critical path diagram]

## Environment Setup (one-time per machine)
[Giữ nguyên hook setup section, update path comment]
[THÊM: pointer rõ ràng tới `playbooks/00-skill-meta.md` cho deep-dive về hook + Self-Learning Protocol]

## Critical Rules (PRESERVE NGUYÊN VĂN — thêm `[GROUP]` tag đầu mỗi rule)

**FORMAT:** Giữ nguyên 17 rules với numbered list + body verbatim. Chỉ thêm `[GROUP_LABEL]` ở đầu rule sau số. Ví dụ:

```markdown
1. `[MODEL]` **Mart models MUST have** `location="{{ get_rolling_location() }}"` — nếu thiếu, `generate_serving_db.py` báo "Empty folder" và drop view
...
11. `[META]` **Khi fix anti-pattern trong prod code** → `grep` `templates/` cho cùng pattern và fix luôn. Templates là hạt giống bug tương lai — bất kỳ asset mới copy từ template cũ sẽ kế thừa bug. Đã xảy ra thực tế 2026-04-08: serving subprocess fix ở prod, nhưng template vẫn giữ `capture_output=True` cho tới audit 2026-04-09.
```

**Group mapping** (nội bộ — không có nghĩa rút gọn rule):
1. `[MODEL]` Mart location | 2. `[MODEL]` src_ incremental | 3. `[MODEL]` src_/stg_ split | 4. `[OPS+MODEL]` DuckDB writer concurrency | 5. `[INGEST]` argv=[] | 6. `[INGEST]` os.chdir + load_dlt_configuration | 7. `[SERVE]` deps=[dbt_assets] | 8. `[MODEL]` Pre-create rolling dirs | 9. `[OPS]` Telemetry vars | 10. `[OPS]` Multi-source upstream inject | 11. `[META]` Fix prod → fix template | 12. `[INGEST]` NEVER drop_sources | 13. `[MODEL]` Dedup modified_on DESC | 14. `[MODEL]` Incremental _dlt_load_id | 15. `[MODEL]` Schema migration self-heal | 16. `[OPS+MODEL]` Nightly vs full-refresh | 17. `[INGEST]` --full-refresh state reset

## Quick Reference

### Playbooks (group-specific deployment guides)
| File | Role |
|------|------|
| `playbooks/00-skill-meta.md` | META: hook setup, Self-Learning Protocol, Lxx workflow |
| `playbooks/01-ingest.md` | INGEST playbook |
| `playbooks/02-model.md` | MODEL playbook |
| `playbooks/03-serve.md` | SERVE playbook |
| `playbooks/04-trust.md` | TRUST playbook |
| `playbooks/05-ops.md` | OPS playbook |
| `playbooks/cross-cutting.md` | Shared concerns (DuckDB lock, paths, env) |

### Deep references (source-of-truth, đọc khi cần chi tiết)
| File | Group | Lines |
|------|-------|-------|
| `references/lessons-learned.md` | INGEST + others | 2557 (76 lessons) |
| `references/dagster-patterns.md` | OPS | 836 (14 lessons) |
| `references/dbt-patterns.md` | MODEL | 479 (14 lessons) |
| `references/serving-layer.md` | SERVE | 269 |
| `references/ingestion-health-digest.md` | TRUST | 333 |
| `references/supporting-scripts.md` | cross-cutting | 197 |
| `references/troubleshooting.md` | cross-cutting | 211 |

### Index
- `lesson-index.md` — Master cross-ref of L1-L76 + 14 dagster + 14 dbt → group(s)
- `templates/INDEX.md` — Templates by group

### Templates (organized by group)
[Giữ bảng templates hiện tại, update paths thành `templates/{group}/{file}`]

## Key Paths
[Giữ nguyên section "Local Development" + "Docker Volume Mapping" + "Path Resolution Pattern"]
```

**Mục tiêu kích thước SKILL.md mới:** ~250-300 lines (compact hơn 290 hiện tại nhưng nhiều navigation hơn).

### 5.2 Annotate `checklist.md` với group labels

Thêm group label vào mỗi phase header:

```markdown
## Phase 1 — dlt Config  `[INGEST]`
[nội dung giữ nguyên]

## Phase 2 — dlt Source Code  `[INGEST]`

## Phase 3 — dbt Transformation  `[MODEL]`

## Phase 4 — Serving Layer  `[SERVE]`

## Phase 5 — Dagster Orchestration  `[OPS + INGEST asset wiring]`

## Phase 6 — Verify End-to-End  `[TRUST]`
```

Thêm 1 dòng đầu file:
```markdown
> Mỗi phase mapped vào 1 functional group. Đọc playbook tương ứng (`playbooks/0X-{group}.md`) song song với checklist này.
```

### 5.3 Update hook script — `data-pipeline-lesson-reminder.cjs`

Path cũ (line 35):
```javascript
const lessonsPath = path.join(cwd, '.skills', 'data-pipeline', 'lessons-learned.md');
```

Path mới (with backward compat fallback):
```javascript
// Try new path first (post-2026-05-07 reorganization), fallback to old path
const lessonsPathNew = path.join(cwd, '.skills', 'data-pipeline', 'references', 'lessons-learned.md');
const lessonsPathOld = path.join(cwd, '.skills', 'data-pipeline', 'lessons-learned.md');
const lessonsPath = fs.existsSync(lessonsPathNew) ? lessonsPathNew : lessonsPathOld;
```

Reminder text update:
```javascript
const reminder = [
  `\n\n📝 **LESSON TRIGGER — fix commit detected**`,
  `Commit: "${msg}"`,
  `Last recorded lesson: ${lastLesson}`,
  ``,
  `→ If root cause is non-trivial, append a new lesson to \`.skills/data-pipeline/references/lessons-learned.md\``,
  `→ Identify functional group (INGEST/MODEL/SERVE/TRUST/OPS) — update lesson-index.md too`,
  `→ Use Self-Learning Protocol format (Symptom / Root cause / Fix / Rules / Reference)`,
  `→ Run: \`grep "^### L" .skills/data-pipeline/references/lessons-learned.md | tail -5\` to see recent`,
].join('\n');
```

**Re-run setup script** sau khi update để deploy hook mới về `$HOME/.claude/hooks/`:
```bash
node .skills/data-pipeline/scripts/setup-lesson-reminder-hook.cjs
```

### 5.4 Update template docstrings (CONTENT-PRESERVING)

**Nguyên tắc bất biến:** Template docstrings có nội dung educational substantial (Job Selection Guide, full-refresh design notes, variable replacement guides, cross-refs Lxx). **CHỈ update path references; KHÔNG xóa/giảm nội dung educational.**

#### Audit từng template (15 files)

```bash
# Tìm path references trong tất cả templates (cũ format)
grep -rn "\.skills/data-pipeline/[a-z-]\+\.md" .skills/data-pipeline/templates/
# Expected: chỉ trả về dòng path, KHÔNG dòng nào liên quan giải thích pattern
```

#### Update rule (per template)

| Match pattern | Replacement |
|---------------|-------------|
| `.skills/data-pipeline/lessons-learned.md` | `.skills/data-pipeline/references/lessons-learned.md` |
| `.skills/data-pipeline/dagster-patterns.md` | `.skills/data-pipeline/references/dagster-patterns.md` |
| `.skills/data-pipeline/dbt-patterns.md` | `.skills/data-pipeline/references/dbt-patterns.md` |
| `.skills/data-pipeline/serving-layer.md` | `.skills/data-pipeline/references/serving-layer.md` |
| `.skills/data-pipeline/supporting-scripts.md` | `.skills/data-pipeline/references/supporting-scripts.md` |
| `.skills/data-pipeline/troubleshooting.md` | `.skills/data-pipeline/references/troubleshooting.md` |
| `.skills/data-pipeline/ingestion-health-digest.md` | `.skills/data-pipeline/references/ingestion-health-digest.md` |

#### Thêm playbook cross-ref (mỗi template)

Sau path update, thêm 1 dòng `See:` pointer tới playbook nhóm tương ứng. Ví dụ:

`templates/ingest/dagster-asset-template.py` thêm:
```python
See: .skills/data-pipeline/playbooks/01-ingest.md (group playbook)
See: .skills/data-pipeline/references/lessons-learned.md L32 (full-refresh design)
```

`templates/ops/stuck-run-alerter-template.py` (existing 2 lines + thêm):
```python
See: .skills/data-pipeline/references/dagster-patterns.md Lesson 10
See: .skills/data-pipeline/references/lessons-learned.md L45-L48
See: .skills/data-pipeline/playbooks/05-ops.md (group playbook)
```

#### Verify content-preserving

```bash
# Diff before/after — chỉ dòng path thay đổi, mọi educational content nguyên si
for f in templates/ingest/*.py templates/model/*.{sql,yml} templates/serve/*.py templates/trust/*.py templates/ops/*.py; do
  before=$(git show HEAD:.skills/data-pipeline/$f 2>/dev/null | wc -l)
  after=$(wc -l < .skills/data-pipeline/$f)
  delta=$((after - before))
  # Acceptable: +1 to +3 (thêm "See:" lines), KHÔNG được -N (mất content)
  test "$delta" -ge 0 || echo "WARN: $f shrunk by ${delta} lines (content loss?)"
done
```

**Acceptance:** 0 WARN outputs. Mọi template grow hoặc same — không shrink.

### 5.5 Update internal references trong references/ files

Sau khi files đã trong `references/`, các tham chiếu nội bộ giữa chúng có thể bị stale.

**Audit:**
```bash
# Tìm tham chiếu giữa references/ files
grep -rn "\.skills/data-pipeline/[a-z-]*\.md" .skills/data-pipeline/references/
```

**Note:** Các tham chiếu kiểu `[xem dbt-patterns.md](dbt-patterns.md)` (relative within same folder) sẽ vẫn hoạt động sau move vì cả 2 file đều ở `references/`. Chỉ cần update khi tham chiếu kiểu absolute path.

### 5.6 Update active external docs

```bash
# Find external active references (skip plans/archive/)
grep -rn "\.skills/data-pipeline/[a-z-]*\.md" docs/ --include="*.md" 2>/dev/null
grep -rn "\.skills/data-pipeline/templates/" docs/ --include="*.md" 2>/dev/null
```

**Update docs:** Đổi từ `.skills/data-pipeline/lessons-learned.md` → `.skills/data-pipeline/references/lessons-learned.md` (tương tự cho 7 files khác).

**KHÔNG update:**
- `plans/archive/...` (historical, đóng băng)
- `plans/reports/...` (historical reports)

### 5.7 Reconcile stale copy `.claude/skills/data-pipeline/SKILL.md`

```bash
# Inspect stale copy
cat .claude/skills/data-pipeline/SKILL.md
```

**3 options:**
1. **Delete:** Nếu chỉ là duplicate cũ và `.skills/data-pipeline/SKILL.md` mới là source of truth.
2. **Sync:** Replace nội dung bằng SKILL.md mới (nếu Claude Code lookup `.claude/skills/`).
3. **Symlink:** Make it point to main SKILL.md (Linux) — không hoạt động trên Windows.

**Đề xuất:** Hỏi user, default Option 1 (delete) — file 2228 bytes nhỏ, có thể là test/cũ.

### 5.8 Update CLAUDE.md / AGENTS.md references (nếu có)

```bash
grep -n "data-pipeline" CLAUDE.md AGENTS.md 2>/dev/null
```

Nếu có references, update tới ARCHITECTURE.md hoặc playbooks layer.

## Files modified

| File | Type of change |
|------|---------------|
| `.skills/data-pipeline/SKILL.md` | REWRITE (5-group aware entry point) |
| `.skills/data-pipeline/checklist.md` | ANNOTATE (group labels per phase) |
| `.skills/data-pipeline/hooks/data-pipeline-lesson-reminder.cjs` | UPDATE path + reminder text |
| `.skills/data-pipeline/templates/ops/stuck-run-alerter-template.py` | UPDATE docstring paths |
| `~/.claude/hooks/data-pipeline-lesson-reminder.cjs` | RE-DEPLOY (via setup script) |
| `.claude/skills/data-pipeline/SKILL.md` | DELETE (or sync) — pending user decision |
| External `docs/**.md` referencing skill paths | UPDATE active references only |
| `CLAUDE.md` / `AGENTS.md` | UPDATE if needed |

## Verification commands

```bash
# 1. Hook still works (run hook manually with mock input)
echo '{"tool_input":{"command":"git commit -m \"fix: test\""},"cwd":"'$(pwd)'"}' | \
  node .skills/data-pipeline/hooks/data-pipeline-lesson-reminder.cjs

# 2. Templates still parseable (sample one)
python -c "exec(open('.skills/data-pipeline/templates/ops/stuck-run-alerter-template.py').read())" 2>&1 | head -5
# Expect: ImportError on dagster (acceptable, just verifying syntax)

# 3. SKILL.md links resolve
grep -oE "playbooks/[a-z0-9-]+\.md" .skills/data-pipeline/SKILL.md | while read f; do
  test -f ".skills/data-pipeline/$f" || echo "MISSING: $f"
done

# 4. References paths resolve
grep -oE "references/[a-z-]+\.md" .skills/data-pipeline/SKILL.md | while read f; do
  test -f ".skills/data-pipeline/$f" || echo "MISSING: $f"
done
```

## Definition of done

- [ ] SKILL.md rewritten với 5-group structure, ≤ 300 lines, tất cả links resolve
- [ ] checklist.md annotated với group labels
- [ ] Hook script update path + redeployed via setup script
- [ ] Template docstrings updated (grep returns 0 references tới old paths)
- [ ] Active external docs updated
- [ ] `.claude/skills/data-pipeline/SKILL.md` reconciled (deleted or synced per user choice)
- [ ] Verification commands pass

## Rollback

```bash
# Revert SKILL.md
git checkout HEAD -- .skills/data-pipeline/SKILL.md
git checkout HEAD -- .skills/data-pipeline/checklist.md
git checkout HEAD -- .skills/data-pipeline/hooks/data-pipeline-lesson-reminder.cjs
git checkout HEAD -- .skills/data-pipeline/templates/ops/stuck-run-alerter-template.py

# Re-run hook setup with old version
node .skills/data-pipeline/scripts/setup-lesson-reminder-hook.cjs
```

## Risk

**Risk 1:** Hook setup script copies cũ version về `$HOME/.claude/hooks/` — user lỡ run trước khi update sẽ stuck. Mitigation: emphasize re-run sau Phase 5 update.

**Risk 2:** External docs có link sâu (anchor) — update path nhưng quên anchor. Mitigation: Phase 6 link checker.

**Risk 3:** SKILL.md rewrite mất "feel" của bản gốc → reviewer phản đối. Mitigation: preserve all 17 Critical Rules + Environment Setup section, chỉ thay phần navigation/quick-reference.
