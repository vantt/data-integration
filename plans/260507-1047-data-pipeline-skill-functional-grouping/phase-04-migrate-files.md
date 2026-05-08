# Phase 4 — Migrate Existing Files

**Status:** pending
**Depends on:** Phase 3 (playbooks must reference `references/X.md` paths trước khi move)
**Blocks:** Phase 5
**Estimated effort:** 30 phút (atomic git ops)

## Mục tiêu

Di chuyển 7 .md files (lessons-learned, dagster-patterns, dbt-patterns, serving-layer, supporting-scripts, troubleshooting, ingestion-health-digest) → `references/`. Move 15 templates → `templates/{group}/`.

**KHÔNG đổi tên file** — preserve git history, simplify reference updates.
**KHÔNG sửa nội dung file** — content-preserving move only.

## Steps

### 4.1 Move .md files → references/
```bash
cd D:/Vantt/app/data-integration/.skills/data-pipeline

git mv lessons-learned.md references/lessons-learned.md
git mv dagster-patterns.md references/dagster-patterns.md
git mv dbt-patterns.md references/dbt-patterns.md
git mv serving-layer.md references/serving-layer.md
git mv supporting-scripts.md references/supporting-scripts.md
git mv troubleshooting.md references/troubleshooting.md
git mv ingestion-health-digest.md references/ingestion-health-digest.md
```

**Files KHÔNG move:**
- `SKILL.md` (root entry point — Phase 5 rewrite)
- `checklist.md` (gắn với SKILL.md, root level — Phase 5 annotate)
- `ARCHITECTURE.md` (Phase 2 mới tạo, ở root)

### 4.2 Move templates → group subfolders
```bash
# INGEST
git mv templates/source-template.py templates/ingest/
git mv templates/run-entry-point-template.py templates/ingest/
git mv templates/dagster-asset-template.py templates/ingest/

# MODEL
git mv templates/src-model-template.sql templates/model/
git mv templates/dim-model-template.sql templates/model/
git mv templates/fact-model-template.sql templates/model/
git mv templates/sources-yml-template.yml templates/model/
git mv templates/schema-yml-template.yml templates/model/

# SERVE
git mv templates/dagster-serving-asset-template.py templates/serve/

# TRUST
git mv templates/ingestion-health-recorder-template.py templates/trust/
git mv templates/ingestion-health-digest-template.py templates/trust/
git mv templates/dlt-row-count-extractor-template.py templates/trust/
git mv templates/backfill-health-rows-written-template.py templates/trust/

# OPS
git mv templates/dagster-reactive-sensor-template.py templates/ops/
git mv templates/stuck-run-alerter-template.py templates/ops/
```

### 4.3 Cleanup
```bash
# Xóa pycache nếu có
rm -rf templates/__pycache__/
```

### 4.4 Verify post-move structure
```bash
tree .skills/data-pipeline/ -L 3 --dirsfirst
# Expected:
# .skills/data-pipeline/
# ├── ARCHITECTURE.md
# ├── SKILL.md
# ├── checklist.md
# ├── lesson-index.md
# ├── hooks/
# ├── playbooks/
# │   ├── 01-ingest.md
# │   ├── 02-model.md
# │   ├── 03-serve.md
# │   ├── 04-trust.md
# │   ├── 05-ops.md
# │   └── cross-cutting.md
# ├── references/
# │   ├── dagster-patterns.md
# │   ├── dbt-patterns.md
# │   ├── ingestion-health-digest.md
# │   ├── lessons-learned.md
# │   ├── serving-layer.md
# │   ├── supporting-scripts.md
# │   └── troubleshooting.md
# ├── scripts/
# └── templates/
#     ├── INDEX.md
#     ├── ingest/      (3 files)
#     ├── model/       (5 files)
#     ├── ops/         (2 files)
#     ├── serve/       (1 file)
#     └── trust/       (4 files)
```

### 4.5 Inventory verification
```bash
# Count files in references/ — should be 7
ls .skills/data-pipeline/references/*.md | wc -l

# Count templates per group
find .skills/data-pipeline/templates/ -name "*.py" -o -name "*.sql" -o -name "*.yml" | sort

# Verify lessons count unchanged in moved file
grep -c "^### L" .skills/data-pipeline/references/lessons-learned.md
# Expected: 76

# Verify dagster-patterns lesson count
grep -c "^## Lesson " .skills/data-pipeline/references/dagster-patterns.md
# Expected: 14

# Verify dbt-patterns lesson count
grep -c "^## Lesson " .skills/data-pipeline/references/dbt-patterns.md
# Expected: 14
```

## Files moved

| From | To | Type |
|------|-----|------|
| `lessons-learned.md` | `references/lessons-learned.md` | doc |
| `dagster-patterns.md` | `references/dagster-patterns.md` | doc |
| `dbt-patterns.md` | `references/dbt-patterns.md` | doc |
| `serving-layer.md` | `references/serving-layer.md` | doc |
| `supporting-scripts.md` | `references/supporting-scripts.md` | doc |
| `troubleshooting.md` | `references/troubleshooting.md` | doc |
| `ingestion-health-digest.md` | `references/ingestion-health-digest.md` | doc |
| `templates/source-template.py` | `templates/ingest/source-template.py` | template |
| `templates/run-entry-point-template.py` | `templates/ingest/run-entry-point-template.py` | template |
| `templates/dagster-asset-template.py` | `templates/ingest/dagster-asset-template.py` | template |
| `templates/src-model-template.sql` | `templates/model/src-model-template.sql` | template |
| `templates/dim-model-template.sql` | `templates/model/dim-model-template.sql` | template |
| `templates/fact-model-template.sql` | `templates/model/fact-model-template.sql` | template |
| `templates/sources-yml-template.yml` | `templates/model/sources-yml-template.yml` | template |
| `templates/schema-yml-template.yml` | `templates/model/schema-yml-template.yml` | template |
| `templates/dagster-serving-asset-template.py` | `templates/serve/dagster-serving-asset-template.py` | template |
| `templates/ingestion-health-recorder-template.py` | `templates/trust/ingestion-health-recorder-template.py` | template |
| `templates/ingestion-health-digest-template.py` | `templates/trust/ingestion-health-digest-template.py` | template |
| `templates/dlt-row-count-extractor-template.py` | `templates/trust/dlt-row-count-extractor-template.py` | template |
| `templates/backfill-health-rows-written-template.py` | `templates/trust/backfill-health-rows-written-template.py` | template |
| `templates/dagster-reactive-sensor-template.py` | `templates/ops/dagster-reactive-sensor-template.py` | template |
| `templates/stuck-run-alerter-template.py` | `templates/ops/stuck-run-alerter-template.py` | template |

**Total: 7 .md + 15 templates = 22 file moves**

## Definition of done

- [ ] 7 .md files trong `references/`, 0 .md files (trừ ARCHITECTURE, SKILL, checklist, lesson-index) ở root
- [ ] 15 templates trong subfolders đúng group
- [ ] `git status` confirm tất cả là `renamed` (không có `deleted`/`new file` cho cùng nội dung)
- [ ] Lessons count post-move = pre-move (76 + 14 + 14)
- [ ] No broken file refs in newly created Phase 3 playbooks (sẽ check bằng grep ở Phase 6)
- [ ] `__pycache__` đã xóa

## Rollback

```bash
cd D:/Vantt/app/data-integration/.skills/data-pipeline

# Reverse moves
for f in references/*.md; do git mv "$f" "$(basename $f)"; done
for f in templates/{ingest,model,serve,trust,ops}/*; do git mv "$f" "templates/$(basename $f)"; done
rmdir references templates/{ingest,model,serve,trust,ops}
```

## Risk

**Risk 1:** Templates docstring tham chiếu `.skills/data-pipeline/dagster-patterns.md` (cũ path). Mitigation: Phase 5 update.

**Risk 2:** Hook script `data-pipeline-lesson-reminder.cjs` hardcode `lessons-learned.md` path. Mitigation: Phase 5 update path tới `references/lessons-learned.md`.

**Risk 3:** External docs (`docs/architecture/locking-and-concurrency.md`, plans/reports/...) tham chiếu paths cũ. Mitigation: Phase 5 grep + update active docs (KHÔNG update plans/archive/).
