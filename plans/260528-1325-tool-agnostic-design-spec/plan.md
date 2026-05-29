---
title: "Tool-Agnostic Design Spec"
status: active
created: 2026-05-28
updated: 2026-05-28
---

# Tool-Agnostic Design Spec

**Goal**: Tách dashboard "intent" khỏi BI tool. Design Spec = tool-agnostic source of truth; mỗi tool có deployer riêng đọc spec → gọi tool API trực tiếp.

**Principle**: YAGNI/KISS/DRY. Endgame = semantic layer (metric_ref → SQL generated from domain defs). Inline SQL là stepping stone.

---

## Decisions (LOCKED)

| ID | Decision | Choice | Link |
|----|----------|--------|------|
| D1 | Skip blueprint file | Spec → deployer → API direct | [D1](decisions.md#d1-skip-blueprint-file-direct-deploy) |
| D2 | Data binding model | Hybrid: metric_ref + inline SQL | [D2](decisions.md#d2-endgame--semantic-layer-hybrid-spec) |
| D3 | Migration strategy | Capture-first (auto-migrate 30 dashboards) | [D3](decisions.md#d3-capture-first-migration-strategy) |
| D4 | Spec versioning | spec_version field, v1→v2 parser support | [D4](decisions.md#d4-spec-versioning-spec_version-field) |
| D5 | Deployer pattern | Per-tool deployer (not converter) | [D5](decisions.md#d5-per-tool-deployer-pattern) |
| D6 | Portability reporting | Badge per deployer, explicit warnings | [D6](decisions.md#d6-portability-badge-honest-reporting) |
| D7 | JSON Schema | Publish from Phase 0, editor validation | [D7](decisions.md#d7-json-schema-from-day-1) |
| D8 | Schema location | analytics-design owns spec; tool-skill owns catalog | [D8](decisions.md#d8-spec-schema-location-analytics-design) |

---

## Phases

| # | Title | Status | Priority | Depends on | Duration | Link |
|---|-------|--------|----------|------------|----------|------|
| 0 | Schema spike — transcribe 5 widgets, validate schema | not_started | P0 | — | 1d | [phase-00](phases/phase-00-schema-spike.md) |
| 1 | Capture enhancement — emit v2 Design Spec | not_started | P0 | phase-00 | 1-2d | [phase-01](phases/phase-01-capture-enhancement.md) |
| 2 | Direct deploy — Spec → Metabase API | not_started | P0 | phase-00,01 | 2-3d | [phase-02](phases/phase-02-direct-deploy.md) |
| 3 | Dashboard migration — 25-26 production specs | not_started | P1 | phase-01,02 | 3-5d | [phase-03](phases/phase-03-dashboard-migration.md) |
| 4 | Aggregation engine — semantic layer stage 1 | not_started | P2 | phase-02,03 | 3-5d | [phase-04](phases/phase-04-aggregation-engine.md) |
| 5 | Blueprint sunset — archive legacy | not_started | P3 | phase-03 | 0.5d | [phase-05](phases/phase-05-blueprint-sunset.md) |

**Total**: ~10-15 days active work. Phase 6 (Evidence/Superset deployers) = on-demand/deferred.

---

## Review Updates (2026-05-28 1745)

2 adversarial reviews by sonnet agents:
- → [reports/review-decisions-260528-1745.md](reports/review-decisions-260528-1745.md) — D1-D8 verdict: D4/D7 solid, D1/D2/D3/D5/D6/D8 questionable. Proposes **D9** (parser location), **D10** (SQL authoring ownership).
- → [reports/review-problems-260528-1745.md](reports/review-problems-260528-1745.md) — Reclassified C4/C5 → M, escalated M4/M5 → C8/C9, added C7 (Phase 0 day-1 hard block), M16/M17/Q7.

**Critical actions pending user confirm** (see [critical-problems.md §5](critical-problems.md#section-5-proposed-decisions-await-user-confirm--from-review-2026-05-28)):
1. D9 — parser at `analytics-design/lib/` (recommend approve)
2. D10 — SQL authoring ownership (recommend: auto-captured only)
3. D2 forcing function — `status: final` require `metric_ref` post-Phase 4?
4. D3 pilot gate — Phase 3 contingent on Phase 1 3-dashboard pilot?

---

## Quick Links

- → [critical-problems.md](critical-problems.md) — open issues, deferred decisions, open questions (+ Section 5 proposed decisions)
- → [reports/](reports/) — review reports (decisions + problems)
- → [reference/architecture.md](reference/architecture.md) — system design, hybrid spec, validation layers
- → [reference/spec-format-design.md](reference/spec-format-design.md) — enhanced spec format v2
- → [reference/parser-deployer-spec.md](reference/parser-deployer-spec.md) — parser/deployer implementation spec
- → [reference/research-foundation.md](reference/research-foundation.md) — research backing for all decisions
- → [reference/key-files.md](reference/key-files.md) — file index, existing blueprints/designs
