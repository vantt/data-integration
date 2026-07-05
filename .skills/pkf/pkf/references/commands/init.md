---
type: Command
title: /pkf init
description: One-time scaffold of the PM structure — issues/, docs/, log.md, index.md.
tags: [pkf, command]
timestamp: 2026-07-05
---

# Schema

1. **Guard — init is one-time.** If the bundle directory already exists, stop: never scaffold
   over a living bundle (no silent overwrites). Point to [update](update.md) for reconciling
   drift or [status](status.md) for a dashboard.
2. **Set up the toolchain environment.** The validator and graph renderer
   (`scripts/validate.py`, `scripts/visualize.py`) need Python 3 + PyYAML, nothing else. Check,
   and install if missing:
   ```
   python -c "import yaml"        # exit 0 → done, skip install
   python -m pip install pyyaml   # only when the check fails, then re-check
   ```
   If Python is absent or pip can't install (offline/locked-down machine), continue the init
   but state plainly that [validate](validate.md) and [viz](viz.md) won't run until PyYAML is
   available — don't fail the whole init over the toolchain.
3. Create `pkf/index.md` (`okf_version: "0.1"`; follow the
   [index-root template](../../assets/templates/index-root.md) — project intro + links to the
   child indexes; the Docs line names topics, none yet at init), `pkf/log.md`, `pkf/issues/index.md`,
   `pkf/docs/index.md` (empty topic map — topics get added as they're needed, don't pre-create
   folders speculatively — see [docs-topics](../concepts/docs-topics.md)).
   The root intro comes from an existing source (README, project docs); **greenfield with
   nothing to distill from → ask the user for a 1–2 sentence description — never invent one**.
4. **Seed `docs/` proportionally to what the project already knows.**
   - **Greenfield** (little/no code): leave `docs/` empty — issues ([issue](issue.md) →
     [work](work.md)) populate it over time.
   - **Brownfield** (existing codebase): seed a PM-level map — **one doc per major user-facing
     capability or domain area, ceiling one doc per topic at init**; the rest accrues via
     issues. Mine what already exists — README, `docs/`, `CLAUDE.md`, ADRs, plans — and point
     each seeded doc's `sources` at the real files it was distilled from.
   - Either way, **never front-load a full code inventory** — no function signatures, no
     per-module docs; that produces code-detail docs this PM system explicitly avoids
     ([docs-topics](../concepts/docs-topics.md)).
5. Log `**Initialization**` in `log.md`, noting what was seeded and from which sources.
   Validate `--strict` ([validate](validate.md)) — the toolchain from step 2 makes this work
   out of the box. Offer [viz](viz.md) for a first look at the graph.

# Template

[assets/templates/index-root.md](../../assets/templates/index-root.md) for `pkf/index.md`;
[assets/templates/index-section.md](../../assets/templates/index-section.md) for
`issues/index.md` and `docs/index.md`; [assets/templates/log.md](../../assets/templates/log.md)
for `log.md`.
