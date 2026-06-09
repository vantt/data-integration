# Phase 6 — Validate

**Status:** pending
**Depends on:** Phase 5
**Blocks:** none (final phase)
**Estimated effort:** 1-2 giờ (verification + smoke test)

## Mục tiêu

Đảm bảo migration **lossless** và **functional**. Không lesson nào miss, không broken link, hook chạy được, agent có thể navigate skill mới đúng cách.

## Verification matrix

### 6.1 Lossless content check (KEY validation)

**Lessons count must match:**
```bash
# Count lessons trong references/lessons-learned.md
grep -c "^### L" .skills/data-pipeline/references/lessons-learned.md
# Expected: 76 (L1-L76, gap L34)

# Count lessons trong dagster-patterns
grep -c "^## Lesson " .skills/data-pipeline/references/dagster-patterns.md
# Expected: 14

# Count lessons trong dbt-patterns
grep -c "^## Lesson " .skills/data-pipeline/references/dbt-patterns.md
# Expected: 14
```

**Word count diff before/after (using git):**
```bash
# So sánh nội dung lessons-learned.md trước/sau move (must be identical)
git show HEAD~5:.skills/data-pipeline/lessons-learned.md | wc -w > /tmp/before.txt
wc -w .skills/data-pipeline/references/lessons-learned.md > /tmp/after.txt
diff /tmp/before.txt /tmp/after.txt
# Expected: difference chỉ do filename, not content
```

**Templates count:**
```bash
find .skills/data-pipeline/templates/{ingest,model,serve,trust,ops} -type f \( -name "*.py" -o -name "*.sql" -o -name "*.yml" \) | wc -l
# Expected: 15 (3+5+1+4+2)
```

### 6.2 Lesson-index completeness check

```bash
# Mỗi lesson L_xx phải xuất hiện trong lesson-index.md
for lesson in $(grep -oE "^### L[0-9]+" .skills/data-pipeline/references/lessons-learned.md | sed 's/### //'); do
  grep -q "$lesson " .skills/data-pipeline/lesson-index.md || echo "MISSING in index: $lesson"
done

# Tương tự cho dagster + dbt patterns
for n in $(seq 1 14); do
  grep -q "dagster-Lesson-$n " .skills/data-pipeline/lesson-index.md || echo "MISSING dagster: $n"
  grep -q "dbt-Lesson-$n " .skills/data-pipeline/lesson-index.md || echo "MISSING dbt: $n"
done
```

**Acceptance:** 0 MISSING outputs.

### 6.3 Group coverage check

Mỗi nhóm phải có:
- 1 playbook file ≥ 200 lines (5 nhóm), 00-skill-meta ≥ 120 lines
- ≥ 1 entry trong lesson-index.md (5 nhóm; meta không cần vì không gắn Lxx)
- ≥ 1 template (trừ SERVE chỉ có 1 template, OK)

```bash
# Meta playbook (smaller threshold)
meta_lines=$(wc -l < .skills/data-pipeline/playbooks/00-skill-meta.md)
echo "00-skill-meta: $meta_lines lines"
test "$meta_lines" -ge 120 || echo "  WARN: meta < 120 lines"

# 5 group playbooks
for group in 01-ingest 02-model 03-serve 04-trust 05-ops; do
  lines=$(wc -l < .skills/data-pipeline/playbooks/$group.md)
  echo "$group: $lines lines"
  test "$lines" -ge 200 || echo "  WARN: < 200 lines"
done

# Cross-cutting playbook
wc -l .skills/data-pipeline/playbooks/cross-cutting.md
```

### 6.3.1 Meta-layer self-test

```bash
# 00-skill-meta.md phải có Self-Learning Protocol section
grep -q "Self-Learning Protocol" .skills/data-pipeline/playbooks/00-skill-meta.md || \
  echo "MISSING: Self-Learning Protocol in 00-skill-meta.md"

# Phải có workflow "thêm lesson Lxx mới"
grep -qE "(Workflow.*lesson|Lxx.*mới|append.*Lxx)" .skills/data-pipeline/playbooks/00-skill-meta.md || \
  echo "MISSING: Lxx workflow in 00-skill-meta.md"

# Hook setup commands trong meta playbook
grep -q "setup-lesson-reminder-hook.cjs" .skills/data-pipeline/playbooks/00-skill-meta.md || \
  echo "MISSING: hook setup reference in 00-skill-meta.md"

# SKILL.md phải pointer tới 00-skill-meta.md
grep -q "playbooks/00-skill-meta.md" .skills/data-pipeline/SKILL.md || \
  echo "MISSING: 00-skill-meta.md pointer in SKILL.md"
```

### 6.4 Internal link resolver

```bash
# Check tất cả links trong playbooks resolve
for f in .skills/data-pipeline/playbooks/*.md .skills/data-pipeline/SKILL.md .skills/data-pipeline/ARCHITECTURE.md; do
  echo "=== $f ==="
  # Find local links (relative paths)
  grep -oE "\([a-z0-9./-]+\.md[^)]*\)" "$f" | sed 's/[()]//g' | while read link; do
    # Resolve relative to playbook dir
    base=$(dirname "$f")
    resolved="$base/$link"
    # Strip anchor
    file=$(echo "$resolved" | cut -d'#' -f1)
    test -f "$file" || echo "  BROKEN: $link → $file"
  done
done
```

**Acceptance:** 0 BROKEN outputs.

### 6.5 Hook smoke test

```bash
# Trigger hook manually
echo '{"tool_input":{"command":"git commit -m \"fix: smoke test\""},"cwd":"'$(pwd)'"}' | \
  node .skills/data-pipeline/hooks/data-pipeline-lesson-reminder.cjs > /tmp/hook_output.json

# Verify output structure
python -c "
import json
data = json.load(open('/tmp/hook_output.json'))
assert data.get('continue') is True, 'Hook did not return continue=true'
assert 'LESSON TRIGGER' in data.get('hookSpecificOutput', {}).get('additionalContext', ''), 'Reminder text missing'
print('Hook OK')
"
```

### 6.5.1 Lossless content audit (CRITICAL — verbatim phrase check)

Verify các phrase đặc trưng từ SKILL.md gốc vẫn tồn tại đâu đó trong cấu trúc mới.

```bash
ROOT=.skills/data-pipeline

# Phrases must exist in NEW structure (somewhere — root SKILL, ARCHITECTURE, playbooks, references):
phrases=(
  "API Source ─┐"                                  # ASCII diagram start (ARCHITECTURE.md)
  "5-hop transform flow"                            # 5-hop flow note
  "Dagster DAG.*ingestion_asset.*dbt_assets"        # DAG note
  "Source đã có trong dlt hub"                      # Pattern A/B decision (01-ingest)
  "Pattern B — Native dlt source"                   # Pattern B (01-ingest)
  "from dlt.sources.facebook_ads import"            # Pattern B example (01-ingest)
  "Stop Metabase first.*releases DuckDB lock"       # Serving views runbook (cross-cutting)
  "rm -rf /app/transformation/target"               # dbt target cache runbook (cross-cutting)
  "DagsterDbtManifestNotFoundError"                 # Order-matters note (cross-cutting)
  "data_lake/{entity}/ingest_method"                # Layout convention (ARCHITECTURE/INGEST)
  "Mart models MUST have"                           # Critical Rule 1
  "argv=\\[\\]"                                     # Critical Rule 5
  "deps=\\[dbt_assets\\]"                           # Critical Rule 7
  "Telemetry vars"                                  # Critical Rule 9
  "drop_sources"                                    # Critical Rule 12 (NEVER use)
  # Pass 3 additions:
  "Verify DuckDB file lock status empirically"      # Debug recipe name (troubleshooting)
  "trap rotate_old_backups EXIT"                    # Bash incantation (L50)
  "DECLARED_IN_CODE"                                # Dagster state (L49)
  "drop_pending_packages"                           # dlt API (clean_dlt_state.py)
  "extra_placeholders"                              # dlt partition config
  "DIGEST_DRY_RUN"                                  # TRUST env var (Production Checklist)
  "Maintenance Cron Design Principles"              # Synthesis block (lessons-learned L1595)
  "Khi Nào Gọi Script Nào"                          # Decision table (supporting-scripts.md)
  "Production checklist"                            # ingestion-health-digest.md 12 items
  "Rollback Plan"                                   # checklist.md 4 scenarios
)

for p in "${phrases[@]}"; do
  if grep -rqE "$p" "$ROOT/SKILL.md" "$ROOT/ARCHITECTURE.md" "$ROOT/playbooks/" "$ROOT/references/" 2>/dev/null; then
    echo "  ✓ found: $p"
  else
    echo "  ✗ MISSING: $p"
  fi
done
```

**Acceptance:** 0 MISSING outputs. Bất kỳ MISSING nào = LOSS, phải re-add.

### 6.5.2 Trigger keyword preservation check

```bash
# Đọc triggers từ git history của SKILL.md gốc, verify mỗi trigger có trong SKILL.md mới
old_triggers=$(git show HEAD~5:.skills/data-pipeline/SKILL.md | sed -n '/^## Kích hoạt/,/^---/p' | grep -oE '"[^"]+"' | sort -u)
new_skill=.skills/data-pipeline/SKILL.md

echo "$old_triggers" | while read trigger; do
  grep -q "$trigger" "$new_skill" || echo "MISSING trigger: $trigger"
done
```

### 6.5.3 Critical Rules count + body length check

```bash
# 17 Critical Rules numbered list trong SKILL.md
count=$(grep -cE "^[0-9]+\." .skills/data-pipeline/SKILL.md)
test "$count" -ge 17 || echo "Critical Rules count = $count (expected ≥ 17)"

# Critical Rules body must be substantive (justification text preserved)
# Get total chars of Critical Rules section vs original
old_len=$(git show HEAD~5:.skills/data-pipeline/SKILL.md 2>/dev/null | sed -n '/^## Critical Rules/,$p' | wc -c)
new_len=$(sed -n '/^## Critical Rules/,$p' .skills/data-pipeline/SKILL.md | wc -c)
ratio=$((new_len * 100 / old_len))
echo "Critical Rules body: old=$old_len new=$new_len ratio=${ratio}%"
test "$ratio" -ge 90 || echo "WARN: Critical Rules body shrunk (lost justification text?)"
```

### 6.5.4 Template content-preserving check

Đảm bảo move template không xóa educational docstring content. Mọi template grow hoặc same — KHÔNG shrink.

```bash
for f in .skills/data-pipeline/templates/{ingest,model,serve,trust,ops}/*.{py,sql,yml}; do
  rel=${f#.skills/data-pipeline/}
  # Find original at root templates/
  orig=".skills/data-pipeline/templates/$(basename $f)"
  before=$(git show "HEAD~5:$orig" 2>/dev/null | wc -l)
  after=$(wc -l < "$f")
  if [ "$before" -gt 0 ]; then
    delta=$((after - before))
    test "$delta" -ge 0 || echo "WARN: $rel shrunk by $delta lines"
  fi
done
```

### 6.5.5 Synthesis blocks + emphasized callouts preserved

```bash
# Maintenance Cron Design Principles synthesis still in references/
grep -q "Maintenance Cron Design Principles" .skills/data-pipeline/references/lessons-learned.md || \
  echo "MISSING: Maintenance Cron Design Principles synthesis"

# OPS playbook references the synthesis
grep -q "Maintenance Cron Design Principles" .skills/data-pipeline/playbooks/05-ops.md || \
  echo "MISSING: synthesis cross-ref in OPS playbook"

# Stuck run prevention callout preserved
grep -qE "(Stuck run prevention|Lesson 10-13)" .skills/data-pipeline/SKILL.md || \
  echo "MISSING: Stuck run prevention emphasized callout in SKILL.md"

# Maintenance cron topology callout
grep -qE "Maintenance cron topology|Lesson 14.*L49-L52" .skills/data-pipeline/SKILL.md || \
  echo "MISSING: Maintenance cron topology emphasized callout in SKILL.md"

# "Khi Nào Gọi Script Nào" decision table referenced
grep -rq "Khi Nào Gọi Script Nào" .skills/data-pipeline/playbooks/ || \
  echo "MISSING: 'Khi Nào Gọi Script Nào' decision table reference in playbooks"
```

### 6.6 External reference scan

```bash
# Tìm any active doc còn tham chiếu old paths
grep -rn "\.skills/data-pipeline/lessons-learned\.md" docs/ CLAUDE.md AGENTS.md 2>/dev/null
grep -rn "\.skills/data-pipeline/dagster-patterns\.md" docs/ CLAUDE.md AGENTS.md 2>/dev/null
grep -rn "\.skills/data-pipeline/dbt-patterns\.md" docs/ CLAUDE.md AGENTS.md 2>/dev/null
# (lặp cho 7 files)
```

**Acceptance:** 0 results trong active docs (plans/archive/ excluded).

### 6.7 Stale copy resolution

```bash
ls .claude/skills/data-pipeline/ 2>&1
# Expected: "No such file or directory" (if deleted)
# OR: SKILL.md identical to .skills/data-pipeline/SKILL.md (if synced)
```

### 6.8 Agent dry-run (manual)

Spawn fresh agent với prompt "Tôi muốn thêm 1 source mới (ví dụ: TikTok Shop API)". Quan sát:
- [ ] Agent đọc SKILL.md đầu tiên
- [ ] Agent navigate tới `playbooks/01-ingest.md`
- [ ] Agent reference checklist phase 1-2
- [ ] Agent identify cross-cutting concerns (env vars, DuckDB lock)
- [ ] Agent biết check `references/lessons-learned.md` cho deep-dive

**Nếu agent vẫn miss group concept** → SKILL.md cần restructure rõ hơn.

## Inventory comparison

**Output format cho audit:**
```markdown
| Check | Before | After | Pass? |
|-------|--------|-------|-------|
| L1-L76 lessons in lessons-learned.md | 76 | 76 | ✓ |
| dagster-patterns lessons | 14 | 14 | ✓ |
| dbt-patterns lessons | 14 | 14 | ✓ |
| .md files (excluding SKILL.md, checklist.md, ARCHITECTURE.md, lesson-index.md) | 7 (root) | 7 (references/) | ✓ |
| templates count | 15 (flat) | 15 (5 subfolders) | ✓ |
| Total .md content (wc -l) | 5364 | 5364 + new playbooks | grew, expected |
| Hook works | ✓ | ✓ | ✓ |
| External docs updated | N/A | 0 broken refs | ✓ |
| Group coverage (5 playbooks) | 0 | 5 ≥200 lines each | ✓ |
| Cross-cutting concerns documented | scattered | 8 in cross-cutting.md | ✓ |
```

## Definition of done

- [ ] Lessons count BEFORE = AFTER cho tất cả 3 lesson files
- [ ] lesson-index.md cover 100% lessons (76 + 14 + 14)
- [ ] **6 playbooks** (00-meta + 5 nhóm) + cross-cutting.md đủ structure
- [ ] 00-skill-meta.md có Self-Learning Protocol + Lxx workflow + hook setup commands
- [ ] SKILL.md có pointer rõ ràng tới 00-skill-meta.md
- [ ] **Lossless content audit pass** (6.5.1): 0 MISSING phrases từ SKILL.md gốc
- [ ] **Trigger preservation pass** (6.5.2): 0 trigger nào bị drop
- [ ] **Critical Rules ≥ 17 + body ≥ 90% original length** (6.5.3) — justifications preserved
- [ ] **Templates không shrink** (6.5.4) — educational docstrings preserved
- [ ] **Synthesis + callouts preserved** (6.5.5) — Maintenance Cron synthesis, Stuck-run prevention callout, Khi-Nào-Gọi decision table referenced
- [ ] **Pattern A/B decision tree + Pattern B example** trong 01-ingest.md
- [ ] **2 Docker mount runbooks** (Serving Views + dbt Target) verbatim trong cross-cutting.md
- [ ] **Quick Reference Docs/Templates tables** trong SKILL.md với descriptions verbatim (path updated)
- [ ] **"Supporting scripts" subsection** trong mỗi 5 playbook
- [ ] 0 broken internal links
- [ ] Hook smoke test pass
- [ ] 0 active external docs reference old paths
- [ ] Stale `.claude/skills/data-pipeline/SKILL.md` resolved
- [ ] Agent dry-run thành công (manual check)
- [ ] PR ready để review

## Sign-off checklist (before merging)

- [ ] User reviewed plan and approved 5 unresolved questions (xem plan.md)
- [ ] Phase 1-6 đã chạy theo thứ tự
- [ ] Final commit message: `refactor(skill): reorganize data-pipeline skill into 5 functional groups`
- [ ] Update `.skills/data-pipeline/SKILL.md` version comment với date 2026-05-07
- [ ] Add changelog entry trong `docs/project-changelog.md` (nếu file đó tồn tại)

## Post-merge follow-ups (separate tickets)

1. Hook enhancement: detect committed file paths để suggest target group khi reminder fire
2. Update `analytics-design-skill` và `metabase-automation` skills với cùng pattern (nếu áp dụng)
3. CLAUDE.md / AGENTS.md cập nhật reference tới ARCHITECTURE.md mental model
4. Thêm `data-pipeline:scaffold-{group}` slash command để bootstrap nhanh

### Data-quality issues TRONG SKILL GỐC (preserve nguyên văn, fix sau)

5. **Inconsistency: nightly job time** — `checklist.md` Phase 5 + `templates/ingest/dagster-asset-template.py` docstring nói "04:00 AM"; nhưng `lessons-learned.md` + actual Dagster schedule là `0 3 * * *` (03:00). Plan preserve nguyên văn (lossless). Cần verify nguồn nào đúng + sync 2 chỗ còn lại.
6. **Stale Lxx references** — `ingestion-health-digest.md` "Post-mortem index" reference `lessons-learned.md L18, L20, L21, L22` nhưng current Lxx numbering thực sự là L42-L44. Có thể reference này từ phase-04 plan dating, không phải lesson-numbering. Plan preserve nguyên văn. Cần audit + correct hoặc clarify reference notation.

## Rollback (final escape hatch)

Nếu Phase 6 phát hiện regression nghiêm trọng:
```bash
# Atomic revert toàn bộ migration
git revert HEAD~6..HEAD  # Adjust based on commit count
# Hoặc
git reset --hard <pre-migration-sha>
```

Sau đó:
1. Document lý do regression vào journal entry
2. Spawn researcher agent tìm root cause
3. Re-plan với fix
