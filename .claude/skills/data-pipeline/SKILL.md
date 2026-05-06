---
name: data-pipeline
description: End-to-end data pipeline patterns (dlt → dbt → DuckDB → Dagster). Activate when adding new data sources, creating dbt models, debugging ingestion/transformation, or working on serving layer and orchestration.
---

# Data Pipeline Skill

**Full instructions**: Read `.skills/data-pipeline/SKILL.md` before proceeding.

---

## Self-Learning Protocol

### Khi nào ghi nhận lesson (triggers)
1. **Sau mỗi `fix:` commit** có root cause không trivial → check ngay xem đã có trong lessons-learned.md chưa
2. **Sau khi resolve incident** (job stuck, data corruption, lock, OOM, auth fail, daemon crash) → ghi lesson trước khi đóng session
3. **Khi gặp behavior bất ngờ** không nằm trong L1–hiện tại → note lại ngay cả khi chưa fix xong
4. **Khi user nói**: "ghi nhận", "record lesson", "học từ lần này", "đừng quên" → ghi ngay vào `lessons-learned.md`

### Cách tự check gap
```bash
# Tìm fix commits chưa được document (chạy khi activate skill)
git log --oneline -20 | grep -iE "fix|bug|stuck|error|broken|revert"

# So sánh với lesson cuối
grep "^### L" .skills/data-pipeline/lessons-learned.md | tail -5
```

Nếu có commit `fix:` trong 5 ngày qua mà không có lesson mới tương ứng → **chủ động hỏi user xem có cần ghi nhận không**.

### Format lesson mới
Append vào `.skills/data-pipeline/lessons-learned.md`, đánh số tiếp theo (Lxx):
```markdown
### Lxx — [Tên ngắn mô tả failure pattern]

**Symptom:** [Điều user/hệ thống quan sát được]

**Root cause:** [Tại sao xảy ra — cụ thể]

**Fix:** [Đã thay đổi gì]

**Rules:**
1. [Quy tắc ngăn tái phát]

**Reference:** [file paths liên quan]
```

### Lesson quality check
Trước khi ghi, tự hỏi:
- Root cause có khác với lessons đã có không? (tránh duplicate)
- Rule có đủ actionable để ngăn lần sau không?
- Có nên thêm vào checklist `dagster-patterns.md` không?

### Weekly audit cadence
Nếu user chạy `/data-pipeline` và có >5 ngày không có lesson mới, nhắc:
"Có muốn chạy git audit để kiểm tra lessons nào chưa ghi nhận không?"
