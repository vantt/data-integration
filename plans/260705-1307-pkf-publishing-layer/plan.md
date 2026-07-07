---
status: discussion
created: 2026-07-05
updated: 2026-07-07
---

# PKF Publishing Layer — Gap Analysis & Proposed Direction

Tài liệu ghi lại trao đổi ngày 2026-07-05 về khả năng của PKF trong việc produce consumer documents từ kiến thức tích lũy. Bổ sung 2026-07-07: đánh giá hữu dụng/rủi ro trước khi adopt (xem cuối file).

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

**2026-07-07:** bảng trên thiếu tiền đề — semantic contract metadata (mục 3 bên dưới) phải xong TRƯỚC P0, nếu không bridge chỉ là LLM đọc prose và đoán.

---

## Đánh Giá 2026-07-07 — Hữu Dụng & Rủi Ro Trước Khi Adopt

Trạng thái lúc đánh giá: skill commit 2026-07-05, chưa từng init, `pkf/` bundle không tồn tại, không hook/CLAUDE.md nào trỏ về pkf. Use case đích: **wiki project — atomic knowledge có cấu trúc + semantic contracts, làm nguồn cho các doc skills publish theo thể loại** (doc-domain-knowledge, doc-decision-brief, doc-user-guide tương lai).

### Fit assessment (~70%)

Khớp tốt: atomic (1 concept/file, ID=path, `# Related` 2 chiều, orphan bị validator flag); độ cao PM-level + `sources` trỏ code = đúng altitude cho publishing; `version`/`updated` + `log.md` append-only = feed incremental republish; index-first query tiết kiệm token; research raw/compile tách biệt, compile phải human-approve.

Yếu nhất: **"semantic contract" hiện chỉ là format contract.** `type` free string không có schema per-type (doc `Decision` không bắt buộc field options/rejected/rationale — nằm trong prose); docs KHÔNG có field `confidence`/`status` (confidence chỉ có ở research raw); không có `audience`. Evidence model của doc-domain-knowledge (Confirmed/Proposal/Open Question) không map với metadata pkf nào → publishing skill phải đọc prose suy diễn thay vì filter frontmatter.

### Vai trò issues/ — Chốt: KHÔNG bỏ, là điểm xuất phát curation

Đề xuất ban đầu (adopt subset docs-only, bỏ issues) bị bác đúng: issue không phải work-tracker mà là **máy sản xuất bối cảnh** — Request nguyên văn → Discussion (quote user, `**Chốt:**`) → Research (nguồn+confidence) → Decision (phương án bị loại + lý do) → Resolution (explain-back + evidence). Dữ liệu "phương án bị loại" mà doc-decision-brief bắt buộc phải có (và cấm bịa) **chỉ tồn tại nếu ghi tại thời điểm quyết định** — tức trong issue. Bỏ issues → wiki giàu "cái gì" nghèo "tại sao", trong khi "tại sao" là thứ publish cần nhất.

**Phân công issues/ vs plans/ — tách theo loại nội dung, không theo loại việc:**
- PKF issue giữ phần tri thức sống lâu hơn việc: Request, Discussion, Decision, Resolution.
- `plans/` giữ phần cơ khí thực thi: phases, file lists, implementation steps.
- Việc lớn có plan dir: `# Plan` của issue = 1 dòng trỏ sang `plans/<dir>/` (hợp lệ theo tenet toolkit-not-checklist); report của plan được cite trong Resolution. Không file đôi.
- Việc nhỏ không đáng plan dir (quyết định policy, domain rule, câu hỏi metric — loại việc hiện "vô gia cư", rơi vào chat rồi mất) → pkf issue trọn vẹn.
- Ngưỡng đề xuất: việc tạo ra quyết định mà 6 tháng sau cần giải thích → qua pkf issue; fix cơ học/chore không có "tại sao" đáng nhớ → thẳng plans/ hoặc làm luôn.

### Rủi ro chính

1. **Không có cơ chế adoption**: skill chỉ load khi gõ `/pkf`; 2 điểm chạm "trước/sau việc lớn" nằm trong SKILL.md — không có trong context khi workflow khác chạy. Không nối vào hook/CLAUDE.md thì compounding không xảy ra.
2. **Kinh tế capture**: mỗi capture = classify → topic → doc + version bump → sync 2-3 index → log → validate. Capture đắt → bị bỏ qua → wiki stale → publishing xuất bản từ dữ liệu cũ **mà không biết là cũ** (lỗi lộ ở document đưa biz user, không lộ ở wiki).
3. **Validator mù invariant ngữ nghĩa**: `validate.py` chỉ check frontmatter parse, `type` non-empty, broken links, orphans. KHÔNG check: status enum, id unique, `blocked_by`/`blocks` đối xứng, issues/index.md table ↔ frontmatter status sync, gate verdict recorded. Phần ceremony nặng nhất được bảo vệ bằng văn xuôi + trí nhớ LLM.
4. **Cold start**: wiki rỗng = giá trị âm. Backfill từ MEMORY.md (~50 facts), plan reports archive, AGENTS.md là vài ngày công curation — không cam kết được thì đừng init.
5. **Dual-store drift với memory**: cần quy tắc — memory = fact vận hành cho Claude (tự động); pkf/docs = tri thức human+AI cùng đọc/sửa, nguồn publish; fact có thể "tốt nghiệp" memory → pkf.
6. **Xung đột rule vị trí**: hook cấm markdown ngoài `plans/`/`docs/`; `pkf init` scaffold `pkf/*.md` ở root → cần exception hook hoặc đặt bundle trong `docs/pkf/`.
7. Phụ: PHILOSOPHY.md vs references/philosophy.md là 2 bản sync tay của cùng nội dung; skill port từ project khác (ví dụ transcription-app); citation OKF spec (GoogleCloudPlatform/knowledge-catalog) chưa verify tồn tại.

### Lộ Trình Adopt (thay thế thứ tự P0-P3 cũ)

1. **Contract metadata trước backfill** (rẻ nhất, tác động lớn nhất, retrofit sau rất đắt): thêm frontmatter docs `status: confirmed|proposal|open-question` (khớp evidence model doc-domain-knowledge), `audience: biz|tech|both`, schema bắt buộc per-type (Decision: options/rejected/picked). Mở rộng `validate.py` enforce per-type schema.
2. **Cơ giới hóa chống drift**: generate `issues/index.md` từ frontmatter bằng script (không sync tay); validator check invariant issue (mục rủi ro 3).
3. **Giải xung đột vị trí bundle + nối dây**: quyết `pkf/` (exception hook) hay `docs/pkf/`; thêm 1 dòng routing vào project CLAUDE.md/hook: trước việc substantial check pkf, sau việc substantial `/pkf update`, kèm ngưỡng issue ở trên.
4. **Init + backfill pilot 1 topic** giàu nhất (revenue/COGS/channel — nhiều tension, biz quan tâm nhất) từ MEMORY.md + reports.
5. **Pilot end-to-end cả con đường curation**: 1 issue thật → work → Decision/Resolution → compile doc → publish thử bằng doc-decision-brief. Đo: document ra nhanh hơn/đúng hơn so với đọc source trực tiếp không. Có bằng chứng mới mở rộng; không hơn thì dừng, tiết kiệm backfill vô ích.
6. Sau pilot mới làm bridge chính thức (P0-P3 bảng cũ: `--from-pkf`, doc-user-guide, publish command).

---

## Câu Hỏi Còn Mở

1. User Guide viết cho loại product nào cụ thể? (dashboard, CLI tool, web app?) — ảnh hưởng đến template và structure.
2. Design Rationale: audience là biz user đọc lại sau 6 tháng, hay stakeholder đọc lần đầu? — ảnh hưởng đến assumed context.
3. Domain Knowledge và Design Rationale có cùng document hay tách riêng? (một số dự án merge cả hai thành 1 doc).
4. Output format: Markdown file trong `docs/`? Hay artifact (HTML/PDF) để share?
5. (2026-07-07) Ngôn ngữ chuẩn cho nội dung wiki: VN, EN, hay VN-cho-biz/EN-cho-tech? — ảnh hưởng trực tiếp publishing (doc-decision-brief viết tiếng Việt).
6. (2026-07-07) Ai review compile: mọi doc mới vào wiki đều qua user duyệt (chậm, sạch) hay chỉ gate doc `status: confirmed` (nhanh, cần discipline)?
7. (2026-07-07) Vị trí bundle: `pkf/` root + exception hook, hay `docs/pkf/`?
8. (2026-07-07) OKF spec citation có tồn tại công khai không? — cần verify nếu giữ claim "conformant".
