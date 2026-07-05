---
name: pkf
description: "PKF (Project Knowledge Framework): a compounding project-knowledge system for this repo, built on Open Knowledge Format (OKF): issues, PM-level docs in dynamic topics, and a chronological log — plain Markdown with YAML frontmatter. Complements, never replaces, other skills/workflows: consult it for context before substantial work through any tool, and feed learnings back after. Triggers on `/pkf` (and `/pkf issue|research|work|status|query|validate|viz|update|init`). Use to file a bug/feature/docs request, plan and execute an issue, check status, answer a question from the bundle, or capture a decision/insight from work done anywhere."
compatibility: Requires Python 3 with PyYAML for scripts/validate.py and scripts/visualize.py.
metadata:
  format: Open Knowledge Format (OKF) v0.1
  redesigned: "2026-07-04"
---

# /pkf — Project Knowledge Framework (issue + docs + log)

**PKF** stands for **Project Knowledge Framework**. `pkf/` is a **compounding knowledge base**
for this project: an Open Knowledge Format (OKF) bundle — plain Markdown files with YAML
frontmatter, linked into a graph. The more the project gets worked on, the more it knows — every
issue resolved, every research pass, every decision made adds to `pkf/docs/` and `log.md`.

**This skill coordinates with every other skill/workflow in this repo — it never replaces one.**
Two moments matter regardless of which tool does the actual work:
- **Before** substantial work: check `pkf/docs/` and open `pkf/issues/` for relevant context —
  don't re-derive what's already known.
- **After** substantial work: fold what was learned back in via [update](references/commands/update.md)
  (works even with no pkf issue involved) or a full [issue](references/commands/issue.md) if the
  work itself should have gone through discuss→plan→execute→review.

`pkf/issues/` is the structured path for work that benefits from that full cycle — it is not a
mandatory front door for everything in the project. `plans/` and `docs/` at the project root keep
doing whatever other tools already use them for; `pkf/` is the layer where durable, cross-cutting
project knowledge accumulates and where any work gets context from / returns learnings to.

This file stays short; command flows and shared rules live in
[references/index.md](references/index.md), read on demand. **This skill's PRD** — the
requirements any change to it must satisfy — is [references/philosophy.md](references/philosophy.md)
(plain-language version: [PHILOSOPHY.md](PHILOSOPHY.md)). Check it before adding or changing a
command, template, or workflow here.

## Usage

```
/pkf                          # default = /pkf status; when pkf/ doesn't exist, status proposes init
/pkf init [path]               # one-time: toolchain check (PyYAML) + scaffold issues/, docs/, log.md, index.md
/pkf issue "<request>"         # file a new issue; ask clarifying questions if needed; draft a Plan
/pkf research [issue] "<topic>" # bounded research loop; with issue → feeds it, without → enriches docs/
/pkf work [issue-slug]         # execute a planned issue; no slug → list open issues, user picks
/pkf status                    # dashboard: issues grouped by status
/pkf query "<question>"        # answer by navigating the bundle, index-first (no full-file dumps)
/pkf update [path]             # reconcile a named drift; bare, auto-extracts an insight/decision
/pkf validate [path]           # run conformance + lint checks
/pkf viz [path]                # (re)generate viz.html + graph.mmd
```

Default bundle directory: **`pkf/`** in the current project (override with `[path]`).

## Routing

`/pkf` triggers the skill — the exact command word after it is **not required**. Match intent,
in Vietnamese or English, then act:

1. **No argument, or just "pkf"** → run [status](references/commands/status.md) — always;
   `status` itself proposes [init](references/commands/init.md) when `pkf/` doesn't exist yet.
2. **Filing a problem, request, or idea** ("bug", "lỗi", "feature", "tính năng", "yêu cầu", or
   simply describing something that needs doing) → [issue](references/commands/issue.md) —
   "pkf báo lỗi X" and "pkf issue X" route the same way.
3. **"Khởi tạo" / "tạo bundle" / "setup" / "init"** → [init](references/commands/init.md).
4. **"Nghiên cứu" / "tìm hiểu về..." / "research"** — with or without an issue to feed →
   [research](references/commands/research.md).
5. **"Làm" / "thực thi" / "resolve" / "execute"** an issue → [work](references/commands/work.md).
6. **"Tình trạng" / "đang chờ gì" / "dashboard" / "status"** → [status](references/commands/status.md).
7. **A free question, when `pkf/` exists** ("X hoạt động sao", "vì sao chọn Y") →
   [query](references/commands/query.md).
8. **"Cập nhật" / "lưu lại" / "ghi nhớ cái này" / "save this" / "update"** →
   [update](references/commands/update.md) — targeted if a path/doc is named, untargeted
   ("lưu lại", "ghi nhớ") otherwise.
9. **"Kiểm tra" / "validate" / "check lỗi format"** → [validate](references/commands/validate.md).
10. **"Vẽ đồ thị" / "graph" / "visualize" / "viz"** → [viz](references/commands/viz.md).
11. **Ambiguous** → ask, don't guess. Offer the command table below as a menu.

## What to do when invoked

1. Route the request per above to a command.
2. Read the matching command reference under `references/commands/<name>.md` and follow it. It
   links out to whichever `references/concepts/*.md` it depends on (see
   [references/concepts/index.md](references/concepts/index.md)) — read those too — and to a
   copy-paste skeleton under `assets/templates/` when it's creating a new file.
3. **Always finish a mutating flow by validating** and fixing every error:
   `python <skill-dir>/scripts/validate.py pkf --strict`
   (`<skill-dir>` = this SKILL.md's directory; `scripts/`, `references/`, and `assets/` are its
   siblings. Needs PyYAML — `pip install pyyaml`.)

---

## The format in one screen

- **A concept = one `.md` file.** Concept ID = its path within the bundle minus `.md`
  (`docs/transcription/transcribe-audio.md` → `docs/transcription/transcribe-audio`).
- **Frontmatter** is delimited by `---`. OKF itself only requires `type` (a non-empty string,
  not centrally registered) — but every `docs/` and `issues/` concept in this project also
  requires `title`, `description`, `tags`, `created`, `updated` (`created` set once; `updated`
  bumps on any meaningful change). Docs additionally carry `version` and `sources` (an array,
  not a single URI — see [docs-topics](references/concepts/docs-topics.md)); issues carry
  `status` and an integer `id` (assigned once, `max existing id + 1`, drives the filename
  `issues/issue-<id>-<type>-<slug>.md`) — see [issue-lifecycle](references/concepts/issue-lifecycle.md).
  Every doc/issue closes with a `# Related` section linking connected concepts.
- **Links** use ordinary Markdown, keep `.md`, and are **relative** from the linking file's own
  directory (not `/`-rooted).
- **Reserved files at every level:** `index.md` (navigation) and `log.md` (chronological history,
  newest first). They carry **no `type`**. Only the bundle-root `index.md` may carry frontmatter,
  and only `okf_version: "0.1"`.
- **Directory layout is producer-defined, not fixed** — see
  [docs-topics](references/concepts/docs-topics.md) for how `docs/` grows.
- **Honesty:** never invent a `sources` entry, a date, or a `description`; never create a broken
  link; one concept per file; keep every concept reachable from an `index.md`.

---

## Commands

See [references/commands/index.md](references/commands/index.md) for the full list; each links
to its own concept file with the exact flow and (where relevant) a template.

| Command | Role |
|---|---|
| [init](references/commands/init.md) | one-time scaffold |
| [issue](references/commands/issue.md) | file + clarify + plan |
| [research](references/commands/research.md) | bounded research loop into an issue |
| [work](references/commands/work.md) | execute a planned issue |
| [status](references/commands/status.md) | dashboard (read-only) |
| [query](references/commands/query.md) | answer a question (read-only) |
| [update](references/commands/update.md) | reconcile a drift, or capture an insight/decision |
| [validate](references/commands/validate.md) | conformance + lint check |
| [viz](references/commands/viz.md) | regenerate the graph visualization |
