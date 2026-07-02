---
name: ui-spec
description: "Generate, validate, and interpret UI specifications from PRD. Creates machine-readable interaction contracts embedded in human-readable Markdown. Use when building UI spec for any app with ≥20 surfaces or complex domain rules."
argument-hint: "[command] [args] — commands: generate, validate, build, check, interpret, init, add-surface, context"
---

# UI Spec Skill (thin wrapper)

**Full instructions**: Read `.agents/skills/ui-spec/SKILL.md` before proceeding.
**Source of truth**: `.agents/skills/ui-spec/` owns all ui-spec instructions, references (`CONVENTION.md`, `METHODOLOGY.md`), templates, and compiler tools (`tools/`).
**Tool invocation**: centralized at `.agents/skills/ui-spec/tools/`. Run from repo root: `node .agents/skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec` (or any spec root). Each spec root keeps only `schema/`.

Do not duplicate instructions here. Keep this wrapper thin so updates only need to happen in `.agents/skills/ui-spec/`.
