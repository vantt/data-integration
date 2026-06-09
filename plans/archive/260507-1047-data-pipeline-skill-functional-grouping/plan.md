---
name: Data-Pipeline Skill — Functional Grouping Reorganization
status: done
created: 2026-05-07
approved: 2026-05-07
owner: Vantt
blockedBy: []
blocks: []
---

# Data-Pipeline Skill — Functional Grouping Reorganization

## Mục tiêu

Tổ chức lại `.skills/data-pipeline/` để skill có **ý thức về 5 nhóm chức năng** đã định nghĩa cho ecosystem (INGEST / MODEL / SERVE / TRUST / OPS). Khi triển khai (deploy, thêm source, debug), agent phải mở đúng playbook nhóm tương ứng và **không bị sót** vì kiến thức bị phân tán.

**Nguyên tắc cốt lõi (NON-NEGOTIABLE):**
- Lossless — không xóa/làm mất chi tiết hiện có (76+ lessons, ~24 patterns, 15 templates).
- Backward compatible — hook + template docstrings tham chiếu paths cũ phải vẫn chạy hoặc được cập nhật cùng lúc.
- Single source of truth — mỗi lesson có canonical home; cross-reference từ playbook khác chỉ là pointer, không clone nội dung.

## Bối cảnh

Skill hiện tại tổ chức theo **technology** (dlt, dbt, dagster, serving) chứ không phải theo **functional group**. Hệ quả: khi thêm 1 source mới, agent phải tự nhặt lessons từ:
- `lessons-learned.md` (2557 lines, 76 lessons mix INGEST + OPS + TRUST)
- `dagster-patterns.md` (836 lines, 14 lessons OPS + 2 MODEL)
- `dbt-patterns.md` (479 lines, 14 lessons MODEL)
- `troubleshooting.md`, `serving-layer.md`, `ingestion-health-digest.md`, `supporting-scripts.md`

Không có index nào nói "khi thêm INGEST source, đây là 8 lessons + 5 templates + 3 cross-cutting concerns mày phải nhớ". Đó là gốc rủi ro miss.

## Inventory (snapshot trước khi tái tổ chức)

| Loại | Số lượng | Files |
|------|----------|-------|
| Markdown docs | 9 (5364 lines tổng) | SKILL.md, checklist.md, lessons-learned.md, dagster-patterns.md, dbt-patterns.md, serving-layer.md, supporting-scripts.md, troubleshooting.md, ingestion-health-digest.md |
| Templates | 15 | source, run-entry-point, dagster-asset, dagster-serving-asset, dagster-reactive-sensor, src/dim/fact/sources/schema (dbt), 4 health templates, stuck-run-alerter |
| Hooks | 1 | data-pipeline-lesson-reminder.cjs (hardcodes path tới lessons-learned.md) |
| Scripts | 1 | setup-lesson-reminder-hook.cjs |
| Lessons enumerated | 76 (L1-L76, gap L34) | trong lessons-learned.md |
| Lessons enumerated | 14 (Lesson 1-14) | trong dagster-patterns.md |
| Lessons enumerated | 14 (Lesson 1-14) | trong dbt-patterns.md |

### Self-Setup / Meta-Layer (preserved — KHÔNG thuộc 5 nhóm chức năng)

Skill này có cơ chế **tự cài đặt** + **kỷ luật ghi lesson** đáng kể, vận hành ở meta-layer trên 5 nhóm:

| Component | Path | Vai trò |
|-----------|------|---------|
| `hooks/data-pipeline-lesson-reminder.cjs` | giữ nguyên ở root | Hook PostToolUse fire sau `fix:` commit, nhắc agent ghi lesson mới |
| `scripts/setup-lesson-reminder-hook.cjs` | giữ nguyên ở root | Idempotent setup: copy hook → `~/.claude/hooks/` + merge vào `.claude/settings.local.json` |
| SKILL.md `## Environment Setup` section | giữ nguyên | Hướng dẫn one-time setup, check existence, re-run khi missing |
| Lesson numbering convention | trong `lessons-learned.md` (L1-L76, gap L34) | Append-only, gap không filled (preserve audit trail) |
| Self-Learning Protocol format | trong các lesson hiện tại | Symptom / Root cause / Fix / Rules / Reference |

**Tại sao tách meta-layer:**
- Knowledge về cách skill tự duy trì (record lesson, deploy hook, naming convention) khác với knowledge về data pipeline.
- Không thuộc INGEST/MODEL/SERVE/TRUST/OPS — đây là **agent infrastructure** chứ không phải data infrastructure.
- Cần discoverable: agent fresh-context cần biết "khi tôi fix bug, hệ thống có nhắc tôi ghi lesson không, ghi vào đâu, format gì".

**Quyết định:** Thêm `playbooks/00-skill-meta.md` làm canonical home cho meta-layer, được SKILL.md + ARCHITECTURE.md reference rõ ràng. Hooks/scripts giữ nguyên path (zero break risk cho `setup-lesson-reminder-hook.cjs` đã deployed).

**Constraints phát hiện được:**
1. Hook script `data-pipeline-lesson-reminder.cjs` hardcode path `.skills/data-pipeline/lessons-learned.md` (line 35)
2. Template `stuck-run-alerter-template.py` docstring tham chiếu `.skills/data-pipeline/dagster-patterns.md` và `lessons-learned.md`
3. Có file lạc `.claude/skills/data-pipeline/SKILL.md` (2228 bytes, khác bản chính) — cần reconcile hoặc xóa
4. `docs/architecture/locking-and-concurrency.md` có thể tham chiếu paths
5. Plans archive (`plans/archive/...`) tham chiếu paths cũ — KHÔNG cần fix (historical)

## Cấu trúc đề xuất (BEFORE / AFTER)

### BEFORE (hiện tại)
```
.skills/data-pipeline/
├── SKILL.md
├── checklist.md
├── lessons-learned.md          (2557 lines, mixed groups)
├── dagster-patterns.md         (836 lines, OPS+)
├── dbt-patterns.md             (479 lines, MODEL)
├── serving-layer.md            (SERVE)
├── supporting-scripts.md       (cross-cutting)
├── troubleshooting.md          (cross-cutting)
├── ingestion-health-digest.md  (TRUST)
├── hooks/, scripts/
└── templates/                  (15 files, flat)
```

### AFTER (đề xuất)
```
.skills/data-pipeline/
├── SKILL.md                       # ENTRY: triggers + 5-group mental model + nav
├── ARCHITECTURE.md                # NEW: Bản đồ 5 nhóm + critical path + dependencies
├── checklist.md                   # 6-phase checklist (annotated với group label)
│
├── playbooks/                     # NEW: Group-specific deployment playbooks
│   ├── 00-skill-meta.md           # META: hook setup, lesson protocol, naming conventions
│   ├── 01-ingest.md               # INGEST: thu thập (Sapo 3-channel, file-drop, sheets)
│   ├── 02-model.md                # MODEL: dbt 5-hop (src→stg→std→int→mart)
│   ├── 03-serve.md                # SERVE: rolling views, dual DuckDB, GC
│   ├── 04-trust.md                # TRUST: 4-tier pyramid, digest, recon, KPI closure
│   ├── 05-ops.md                  # OPS: sensors, schedules, concurrency, maintenance
│   └── cross-cutting.md           # NEW: DuckDB lock, Docker paths, env vars, telemetry
│
├── references/                    # MOVED: existing source-of-truth files (unrenamed)
│   ├── lessons-learned.md         # 76 lessons (canonical, không đổi tên)
│   ├── dagster-patterns.md        # OPS deep-dive
│   ├── dbt-patterns.md            # MODEL deep-dive
│   ├── serving-layer.md           # SERVE deep-dive
│   ├── ingestion-health-digest.md # TRUST deep-dive
│   ├── supporting-scripts.md      # scripts catalog
│   └── troubleshooting.md         # symptom → cause → fix
│
├── lesson-index.md                # NEW: Master cross-reference L1-L76 → group(s) + post-mortem date
│
├── templates/
│   ├── INDEX.md                   # NEW: templates by group
│   ├── ingest/                    # NEW subfolder
│   │   ├── source-template.py
│   │   ├── run-entry-point-template.py
│   │   └── dagster-asset-template.py
│   ├── model/
│   │   ├── src-model-template.sql
│   │   ├── dim-model-template.sql
│   │   ├── fact-model-template.sql
│   │   ├── sources-yml-template.yml
│   │   └── schema-yml-template.yml
│   ├── serve/
│   │   └── dagster-serving-asset-template.py
│   ├── trust/
│   │   ├── ingestion-health-recorder-template.py
│   │   ├── ingestion-health-digest-template.py
│   │   ├── dlt-row-count-extractor-template.py
│   │   └── backfill-health-rows-written-template.py
│   └── ops/
│       ├── dagster-reactive-sensor-template.py
│       └── stuck-run-alerter-template.py
│
├── hooks/                         # Update lesson-reminder.cjs path
└── scripts/
```

### Quyết định thiết kế (đã chốt)

| # | Quyết định | Lý do |
|---|-----------|-------|
| 1 | Move .md → `references/`, KHÔNG rename | Preserve git history + simplify migration; tên file đã quen |
| 2 | Templates → subfolder theo group | Parallel với playbooks, dễ Glob theo group |
| 3 | Playbooks là entry layer mới, references là deep layer | Lossless: nội dung gốc giữ nguyên trong references |
| 4 | Cross-cutting riêng 1 file | Tránh duplicate trong 5 playbooks; canonical home cho concern xuyên suốt |
| 5 | lesson-index.md riêng | Bảng tra cứu — L_xx tới group nào — phục vụ search ngược |
| 6 | Update hook + template docstrings cùng PR | Atomic; tránh half-broken state |
| 7 | Reconcile/xóa `.claude/skills/data-pipeline/SKILL.md` | File lạc, gây confusion |

## Phases

| # | Phase | File | Mục tiêu |
|---|-------|------|----------|
| 1 | Content mapping (DONE) | `phase-01-content-mapping.md` | Document mapping của 76 lessons + 14 dagster + 14 dbt + 15 templates → 5 groups |
| 2 | Scaffolding (DONE) | `phase-02-scaffolding.md` | Tạo folders mới, viết ARCHITECTURE.md, viết INDEX placeholders |
| 3 | Viết playbooks (DONE) | `phase-03-write-playbooks.md` | 5 group playbooks + cross-cutting.md + lesson-index.md (đầy đủ nội dung) |
| 4 | Migrate files (DONE) | `phase-04-migrate-files.md` | git mv references/ + templates/{group}/ |
| 5 | Update entry points (DONE) | `phase-05-update-entry-points.md` | SKILL.md, checklist.md, hook path updated, stale copy deleted |
| 6 | Validate (DONE) | `phase-06-validate.md` | Structure verified 2026-06-09 — matches AFTER target exactly |

## Critical path

```
Phase 1 (DONE in conversation)
  → Phase 2 (scaffolding — additive, không phá gì)
    → Phase 3 (write playbooks — chỉ viết, chưa di chuyển)
      → Phase 4 (migrate — atomic git mv)
        → Phase 5 (update references — depends on Phase 4 paths)
          → Phase 6 (validate)
```

## Success criteria

1. **Lossless:** Diff toàn bộ nội dung lessons + patterns + templates BEFORE = SUM(playbooks + references + cross-cutting) AFTER. Không câu nào biến mất.
2. **Group coverage:** Mỗi nhóm có 1 playbook ≥ 200 dòng với pre-flight checklist + lessons cross-ref + templates list + common pitfalls.
3. **Lesson index complete:** Mỗi L1..L76 + Lesson1..14 (dagster) + Lesson1..14 (dbt) đều có dòng trong lesson-index.md với group(s) gán.
4. **Backward compat:** Hook chạy bình thường (path cập nhật), templates copy ra dùng được.
5. **No broken links:** `grep -r ".skills/data-pipeline/" .skills/ docs/` không còn link tới path cũ trong file mới.
6. **Meta-layer discoverable:** Agent fresh-context đọc SKILL.md → biết về `playbooks/00-skill-meta.md` → hiểu hook auto-reminder + Self-Learning Protocol + cách thêm lesson Lxx mới → cách update lesson-index.md.

## Risks & mitigation

| Risk | Mitigation |
|------|-----------|
| Move file phá git history | Dùng `git mv` (Bash) thay vì delete + create |
| Hook script break sau di chuyển | Phase 5 update path; Phase 6 smoke test bằng commit fix: thử |
| Playbook duplicate nội dung references | Quy ước: playbook = checklist + pointers; references = deep-dive |
| Cross-cutting concern kẹt giữa 2 nhóm | cross-cutting.md là canonical; playbook chỉ link tới |
| File `.claude/skills/data-pipeline/SKILL.md` lạc | Phase 5 reconcile (xóa hoặc cập nhật) |
| Templates docstring stale paths | Phase 5 grep + replace `.skills/data-pipeline/{file}.md` → `.skills/data-pipeline/references/{file}.md` |

## Rollback plan

Nếu phát hiện regression:
1. `git revert` PR — vì tất cả thay đổi atomic trong 1 PR/branch.
2. Files ở `references/` move trở lại root: `git mv .skills/data-pipeline/references/*.md .skills/data-pipeline/`
3. Xóa folders mới: `rm -rf .skills/data-pipeline/playbooks .skills/data-pipeline/references`

## Out of scope (defer)

- Hook script enhancement để suggest target group khi reminder fire (out of scope, ticket riêng).
- Cập nhật `analytics-design-skill` hoặc `metabase-automation` skills (tách biệt).
- Redesign `troubleshooting.md` thành group-organized (giữ nguyên format hiện tại; chỉ move vào references/).
- Restructure ingestion/ codebase (chỉ về skill, không chạm code thật).

## Confirmed decisions (user-approved 2026-05-07)

| # | Decision | Confirmed |
|---|----------|-----------|
| 1 | Move 7 .md files vào `references/` | ✅ Move |
| 2 | Templates subfolder theo group | ✅ Subfolders (ingest/model/serve/trust/ops) |
| 3 | Commit strategy | ✅ 1 PR atomic |
| 4 | `.claude/skills/data-pipeline/SKILL.md` stale copy | ✅ Delete |
| 5 | checklist.md (defer to implementation) | Annotate inline với group labels (default) |
