# META Playbook — Skill Self-Maintenance

**Vai trò:** Document cơ chế tự duy trì của skill — hook deployment, lesson recording
protocol, naming conventions. Đây là **agent infrastructure**, không phải data infrastructure.
Không thuộc INGEST/MODEL/SERVE/TRUST/OPS.

---

## Pre-flight Checklist (khi join project mới hoặc setup máy mới)

- [ ] Hook deployed: `ls "$HOME/.claude/hooks/data-pipeline-lesson-reminder.cjs" 2>/dev/null && echo "OK" || echo "MISSING"`
- [ ] Nếu MISSING → `node .skills/data-pipeline/scripts/setup-lesson-reminder-hook.cjs`
- [ ] Reload Claude Code (`/hooks` hoặc restart) để hook active
- [ ] Verify hook trigger: thực hiện commit `fix:` thử nghiệm → phải thấy "📝 LESSON TRIGGER" reminder
- [ ] `.claude/settings.local.json` có entry hook (setup script tự merge, không cần sửa tay)

---

## Cơ chế Hook

**Trigger:** `PostToolUse` matcher `Bash`, fire sau khi Bash tool chạy xong.

**Logic xử lý:**

1. Parse stdin JSON từ Claude harness
2. Check nếu command có `git commit` không
3. Extract `-m` message; check prefix `fix:` hoặc `fix(`
4. Đọc `references/lessons-learned.md` (path sau Phase 4 reorganization), tìm Lxx cuối cùng
5. Output `additionalContext` reminder nhắc agent ghi lesson

**Fail-open:** lỗi parse → `process.exit(0)`, commit KHÔNG bị block.

**Source file:** `hooks/data-pipeline-lesson-reminder.cjs`  
**Installed copy:** `~/.claude/hooks/data-pipeline-lesson-reminder.cjs`  
**Setup script:** `scripts/setup-lesson-reminder-hook.cjs` (idempotent)

---

## Self-Learning Protocol (format ghi lesson)

Mỗi lesson Lxx mới thêm vào `references/lessons-learned.md` PHẢI có đủ 5 phần:

```markdown
### Lxx — [Title ngắn gọn, mô tả pattern/bug]

**Symptom:** [Triệu chứng quan sát được — log error, behavior bất thường]
**Root cause:** [Nguyên nhân gốc rễ — tại sao xảy ra, không phải fix gì]
**Fix:** [Code/config thay đổi cụ thể; link commit nếu có]
**Rules (rút ra):** [Generalize thành rule/anti-pattern để áp dụng tương lai]
**Reference:** [Files/lines bị ảnh hưởng, post-mortem date, related Lxx]
```

**Tiêu chí "đáng ghi":** Root cause non-trivial (không phải typo), hoặc behavior surprising
dù đã đọc docs, hoặc lần đầu gặp platform-specific issue.

---

## Naming Conventions

| Convention | Áp dụng | Ví dụ |
|-----------|---------|-------|
| Lessons trong `lessons-learned.md` | `### L<n> — Title` | `### L57 — history_log double-fetch` |
| Số Lxx KHÔNG fill gap | Append-only — gap là audit trail | L34 đã skip — không reuse số này |
| Lessons trong `dagster-patterns.md` | `## Lesson <n>: Title` | `## Lesson 14: Maintenance Schedule Topology` |
| Lessons trong `dbt-patterns.md` | `## Lesson <n>: Title` | `## Lesson 5: Rolling Location` |
| Post-mortem date | Trong section header | `## Stuck Run Prevention (post-mortem 2026-04-24)` |
| References trong playbooks | `../references/lessons-learned.md#Lxx` | `../references/lessons-learned.md#L25` |
| Templates (sau Phase 4) | `../templates/{group}/{file}` | `../templates/ingest/source-template.py` |

**Quan trọng:** Lessons trong `lessons-learned.md` khác với Lessons trong
`dagster-patterns.md` / `dbt-patterns.md` — không nhầm lẫn anchor format khi cross-ref.

---

## Workflow: Thêm Lesson Lxx Mới (7 bước)

1. Sau commit `fix:` → hook reminder fire → đánh giá: root cause có non-trivial không?
2. Tìm số Lxx tiếp theo:
   ```bash
   grep "^### L" .skills/data-pipeline/references/lessons-learned.md | tail -5
   ```
3. Append `### L<next> — Title` ở cuối section phù hợp (topical) hoặc cuối file (chronological)
4. Điền đủ 5-part Self-Learning Protocol (Symptom / Root cause / Fix / Rules / Reference)
5. **PHẢI update `lesson-index.md`** — thêm 1 dòng với: ID, Title, Date, Group(s), Link
6. Nếu lesson liên quan cross-cutting concern → thêm bullet vào section tương ứng trong `playbooks/cross-cutting.md`
7. Nếu lesson liên quan template → update template docstring `See:` line với Lxx

**Lưu ý bước 5 là bắt buộc** — thiếu dòng trong `lesson-index.md` làm index incomplete và
mất utility tìm kiếm theo group.

---

## Files của Meta-Layer

| File | Vai trò | Khi nào sửa |
|------|---------|-------------|
| `hooks/data-pipeline-lesson-reminder.cjs` | Hook source (committed) | Khi đổi reminder text, path, hoặc trigger logic |
| `scripts/setup-lesson-reminder-hook.cjs` | Idempotent installer | Khi đổi hook entry structure trong settings.local.json |
| `~/.claude/hooks/data-pipeline-lesson-reminder.cjs` | Deployed copy (runtime) | Re-run setup script sau khi update source hook |
| `.claude/settings.local.json` (project) | Hook registration | Setup script tự merge — không sửa tay |
| `references/lessons-learned.md` | Lessons store (canonical) | Append Lxx sau mỗi fix non-trivial |
| `lesson-index.md` | Cross-ref index: Lxx → group + link | Update mỗi lần thêm Lxx |
| `playbooks/00-skill-meta.md` | This file — meta-layer docs | Khi đổi convention hoặc protocol |

---

## Mở Rộng Tương Lai (ngoài scope reorganization này)

Các enhancement này **KHÔNG thuộc scope** của Phase 3-6. Ghi nhận để tránh scope creep:

- Hook detect commit file paths → suggest target group khi reminder fire
  (e.g., commit chạm `transformation/` → "consider MODEL group")
- Auto-update `lesson-index.md` từ git log (automated CI step)
- Linter check format compliance của Lxx (5-part protocol enforcement)
- Hook suggest related Lxx khi ghi lesson mới (similarity search)

---

## Cross-cutting Refs

Không có — meta-layer độc lập, không phụ thuộc DuckDB / Docker / env vars của data pipeline.
