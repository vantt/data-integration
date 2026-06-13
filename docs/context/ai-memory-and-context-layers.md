# AI Memory & Context Layers

Cách Claude Code lưu/đọc "trí nhớ" và ngữ cảnh cho project này. 4 tầng bền + 1 tầng tạm.

> **Lưu ý:** Tầng 1 (auto-memory) nằm NGOÀI git, trên máy mỗi người — không chia team, không backup theo repo. Các tầng 2–4 nằm trong git (trừ tầng 2 là instructions cá nhân).

## Bản đồ theo tầng

| # | Tầng | Phạm vi | Vị trí | Trong git? | Khi nào đọc |
|---|---|---|---|---|---|
| 1 | **Auto-memory** (động, Claude tự ghi facts) | Riêng project này | `~/.claude/projects/D--Vantt-app-data-integration/memory/` (`MEMORY.md` + 1 file/fact) | ❌ ngoài git (user profile) | `MEMORY.md` load mỗi session; fact riêng recall khi liên quan |
| 2 | **Global instructions** (rule cá nhân) | Mọi project | `~/.claude/CLAUDE.md` + `~/.claude/rules/*.md` | ❌ (per-machine) | mỗi session, mọi project |
| 3 | **Project instructions** (rule repo) | Repo này | `./CLAUDE.md` + `./AGENTS.md` + `./transformation/AGENTS.md` | ✅ | mỗi session trong repo |
| 4 | **Knowledge base** (kiến thức tham chiếu) | Repo này, theo chủ đề | `./docs/**` + `.skills/data-pipeline/references/lessons-learned.md` | ✅ | on-demand khi cần |
| — | **Ephemeral** (ngữ cảnh phiên) | Phiên hiện tại | RAM (summarize khi dài) | ❌ | chỉ trong phiên |

## Tầng 1 — Auto-memory (chi tiết)

- **Đây là "memory" đúng nghĩa**: động, tự cập nhật qua các session. Claude ghi vào đây các sự thật phi-hiển-nhiên về dự án/cách làm việc.
- **Per-project**: tên thư mục `D--Vantt-app-data-integration` = chính path `D:\Vantt\app\data-integration` (đổi `:` `\` → `-`). Project khác → thư mục memory khác, KHÔNG dùng chung.
- **Cấu trúc**: `MEMORY.md` = mục lục (1 dòng/fact, luôn nạp vào context); thân mỗi fact ở 1 file `.md` riêng có frontmatter.
- **4 loại fact** (`metadata.type`):
  - `user` — anh là ai (vai trò, preference)
  - `feedback` — cách anh muốn Claude làm việc (correction/approach + lý do)
  - `project` — bối cảnh dự án không suy ra được từ code/git
  - `reference` — trỏ tài nguyên ngoài (URL, dashboard, path)
- **Ngoài git** → chỉ trên máy người chạy; không chia team, không versioned theo repo.

## Phân biệt quan trọng

- **Memory động = duy nhất 1 chỗ**: tầng 1 (`~/.claude/projects/<project>/memory/`).
- Mọi thứ trong `docs/`, `CLAUDE.md`, `AGENTS.md`, `lessons-learned.md` là **instructions / knowledge tay viết** (bền, trong git) — KHÔNG phải memory tự sinh.
- **Tầng 2 vs 3**: instructions phân cấp — global (mọi nơi) → project (repo này, bổ sung/ghi đè).

## Muốn team dùng chung 1 "memory"?

Auto-memory (tầng 1) không chia team được (ngoài git). Nếu cần kiến thức bền + chia sẻ → ghi vào tầng 3/4 (`docs/`, `AGENTS.md`, `lessons-learned.md`) thay vì auto-memory.
