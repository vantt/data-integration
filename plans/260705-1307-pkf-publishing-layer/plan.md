---
status: discussion
created: 2026-07-05
updated: 2026-07-05
---

# PKF Publishing Layer — Gap Analysis & Proposed Direction

Tài liệu ghi lại trao đổi ngày 2026-07-05 về khả năng của PKF trong việc produce consumer documents từ kiến thức tích lũy.

---

## Bối cảnh

**PKF (Project Knowledge Framework)** là skill mới được add vào `.skills/pkf/`, với thin wrapper tại `.claude/commands/pkf.md` và `.agents/skills/pkf/SKILL.md`.

PKF là hệ **knowledge accumulation** — plain Markdown + YAML frontmatter theo chuẩn OKF v0.1. Tích lũy issues, decisions, research qua thời gian, không mất giữa các session. Stack: Python 3 + PyYAML cho validate/visualize; LLM làm phần intelligence.

Hai điểm chạm bắt buộc với mọi workflow khác:
- **Trước** khi làm việc lớn → `/pkf query` lấy context đã biết
- **Sau** khi hoàn thành → `/pkf update` ghi lại những gì học được

---

## 3 Consumer Document Types Cần Produce

Cuối mỗi sản phẩm, có 3 loại tài liệu cần tạo cho người dùng:

| # | Loại | Consumer | Mục đích |
|---|---|---|---|
| 1 | **User Guide** | End-user | Task-oriented, "cách dùng X"; không cần biết implementation |
| 2 | **Domain Knowledge** | Biz user + Technical | Correct mental model về business domain; giải thích terminology, tensions, tính toán metrics |
| 3 | **Design Rationale** | Biz user muốn hiểu sâu | Tại sao chọn thiết kế như vậy; alternatives đã xem xét và bị loại; trade-offs |

---

## Mapping với Ecosystem Hiện Tại

### Doc Type 1 — User Guide
- **Skill hiện tại:** `doc-workflow` — thiên về process/pipeline (stages, triggers, actors, data flow), viết cho operator/maintainer.
- **Gap:** chưa có skill dedicated cho end-user task-oriented guide.
- **Status: ❌ Chưa có**

### Doc Type 2 — Domain Knowledge
- **Skill hiện tại:** `doc-domain-knowledge` — khớp trực tiếp. Dual-audience design (Part A: biz, Part B: technical). Domain tension analysis. Evidence model (Confirmed / Proposal / Open Question).
- **Gap:** skill đọc từ source material trực tiếp, không consume PKF bundle — bridge còn là thủ công.
- **Status: ✅ Skill có, ⚠️ chưa connected với PKF**

### Doc Type 3 — Design Rationale
- **Skill hiện tại:** Không có dedicated skill. PKF lưu `type: Decision` trong `docs/<topic>/` và `# Decision` trong issues — đây là raw material đúng chỗ.
- **Gap:** PKF có raw material nhưng không có extraction + publishing flow thành biz-readable document.
- **Status: ⚠️ Raw material có trong PKF, ❌ publishing flow chưa có**

---

## Vấn đề Cốt Lõi: Thiếu Bridge

```
PKF bundle
(decisions, features,
domain tensions,
confirmed facts)
        │
        │  ← manual copy-paste hiện tại
        ↓
doc-domain-knowledge / doc-workflow skills
        │
        ↓
Consumer documents
```

PKF và các doc skills tồn tại **độc lập**. Không có pipeline tự động từ PKF knowledge → consumer document output.

---

## Semantic Concepts của PKF (tham chiếu)

PKF có 3 cross-cutting concepts:

**`issue-lifecycle`** — state machine (`open → in-progress → review → resolved`), body sections (Request, Discussion, Research, Decision, Plan, Worklog, Resolution, Related), importance gate.

**`docs-topics`** — dynamic topic model cho `docs/`; type vocabulary: `Feature`, `Architecture Note`, `Design`, `Data Model`, `Guide`, `Decision`.

**`research` raw layer** — `pkf/research/raw/` immutable captures; confidence rubric (high/medium/low); compile vào `docs/` chỉ sau human approval.

---

## Hướng Giải Quyết Đề Xuất

### Option A — Extend PKF (thêm `publish` command)
Thêm `/pkf publish [consumer] [doc-type]` vào `.skills/pkf/pkf/`:
- Consumer profiles: `biz-user`, `developer`, `end-user`
- Output types: `user-guide`, `domain-knowledge`, `design-rationale`
- Command đọc PKF bundle → filter relevant content → apply template per consumer

**Pros:** tập trung một chỗ, PKF là single entry point  
**Cons:** làm phình PKF ra khỏi phạm vi ban đầu (accumulation, không phải publication)

### Option B — Skill riêng consume PKF (recommended)
PKF giữ nguyên là pure knowledge accumulation. Build bridge riêng hoặc thêm "PKF-aware mode" vào các doc skills:

```
/pkf query → export relevant PKF content as context
    ↓
/doc-domain-knowledge --from-pkf pkf/
/doc-user-guide --from-pkf pkf/        ← skill mới cần build
/pkf publish design-rationale          ← thin extraction từ PKF Decision docs
```

**Pros:** sạch theo PHILOSOPHY của PKF ("Không thay thế các công cụ khác"), mỗi skill làm đúng 1 việc  
**Cons:** user phải biết orchestrate nhiều commands

---

## Công Việc Cần Làm (Ưu tiên)

| Priority | Việc | Effort | Notes |
|---|---|---|---|
| P0 | Convention: document bridge thủ công PKF → doc-domain-knowledge | Thấp | Chỉ cần viết bước "export PKF context trước khi gọi skill" |
| P1 | User Guide skill mới | Trung bình | `doc-user-guide` — task-oriented, end-user consumption |
| P2 | Design Rationale extraction từ PKF Decision docs | Thấp–trung bình | Có thể là template + 1 command trong PKF |
| P3 | Formal bridge PKF → doc skills | Cao | Automation, không cần làm ngay |

---

## Câu Hỏi Còn Mở

1. User Guide viết cho loại product nào cụ thể? (dashboard, CLI tool, web app?) — ảnh hưởng đến template và structure.
2. Design Rationale: audience là biz user đọc lại sau 6 tháng, hay stakeholder đọc lần đầu? — ảnh hưởng đến assumed context.
3. Domain Knowledge và Design Rationale có cùng document hay tách riêng? (một số dự án merge cả hai thành 1 doc).
4. Output format: Markdown file trong `docs/`? Hay artifact (HTML/PDF) để share?
