---
title: "Research Foundation — Index & Cross-Reference"
status: reference
created: 2026-05-28
updated: 2026-05-28
---

## 1. Research Reports Index

All 6 reports in `../../reports/` (relative to this file). **Do not skip** — contain data + rationale for every decision.

| # | File | Mục đích | Phase nào dùng |
|---|------|---------|---------------|
| 1 | [research-260527-2300-tool-agnostic-design-spec.md](../../reports/research-260527-2300-tool-agnostic-design-spec.md) | Main research — gap analysis Design Spec vs Blueprint, cross-BI-tool deep analysis, enhanced format design v2, conversion architecture | All phases |
| 2 | [researcher-260527-2300-bi-dashboard-formats.md](../../reports/researcher-260527-2300-bi-dashboard-formats.md) | Cross-tool format analysis: Tableau XML, Looker LookML, Power BI Layout.json, Superset position_json, Metabase visualization_settings, Grafana JSON schema v2 | Phase 0 (schema), Phase 6 (other deployers) |
| 3 | [researcher-260527-2348-dashboard-definition-formats.md](../../reports/researcher-260527-2348-dashboard-definition-formats.md) | Model-based BI deep-dive: Looker LookML / Lightdash dbt-native / Evidence.dev markdown — semantic layer trade-offs | Phase 4 (semantic layer endgame), Phase 6 (Evidence/Looker deployers) |
| 4 | [researcher-260527-2348-dashboard-json-formats.md](../../reports/researcher-260527-2348-dashboard-json-formats.md) | SQL-based BI export JSON: Superset position_json grid + chart params, Grafana gridPos + fieldConfig + templating | Phase 6 (Superset/Grafana deployers) |
| 5 | [researcher-260527-visualization-type-mapping.md](../../reports/researcher-260527-visualization-type-mapping.md) | 25 viz types × 6 tools support matrix, fallback recommendations, conversion effort estimates | Phase 0 (schema fallback rules), Phase 6 |
| 6 | [handoff-260528-1300-tool-agnostic-design-spec.md](../../reports/handoff-260528-1300-tool-agnostic-design-spec.md) | Original session handoff prompt — historical context; **superseded by plan dir** after ultrathink revision | Historical only |

---

## 2. Cross-Reference Map

How each report backs decisions, architecture sections, and surfaced risks.

### Report 1 — research-260527-2300-tool-agnostic-design-spec.md

- Backs: ADR-2 (§3 Enhanced Format Design → hybrid spec schema), ADR-4 (spec versioning), ADR-7 (JSON Schema from day 1)
- Cited in: [spec-format-design.md](spec-format-design.md) §1-7 (primary source for v2 format), [parser-deployer-spec.md](parser-deployer-spec.md) §3 (validation strategy extends §6 of this report)
- Surfaced concerns: A.1 (goal ambiguity), B.1 (blueprint as middleman), D.1 (capture-first vs forward-first) — all resolved in `../decisions.md`

### Report 2 — researcher-260527-2300-bi-dashboard-formats.md

- Backs: ADR-5 (per-tool deployer pattern — common grid/viz/filter patterns across tools), ADR-8 (schema location in analytics-design)
- Cited in: [parser-deployer-spec.md](parser-deployer-spec.md) §1 (parser grid/viz patterns), [architecture.md](architecture.md) §2 (deployer pattern)
- Surfaced concerns: C.6 (single source of truth), B.4 (tab standards tool-specific impl)

### Report 3 — researcher-260527-2348-dashboard-definition-formats.md

- Backs: ADR-2 (semantic layer endgame rationale — Looker/Lightdash/Evidence comparison), [spec-format-design.md](spec-format-design.md) §7 (migration path stages)
- Cited in: [architecture.md](architecture.md) §2 (domain files → semantic source)
- Surfaced concerns: B.2 (SQL-in-spec vs semantic layer — resolved hybrid), B.3 (cross-skill boundary with semantic layer — deferred Phase 4)

### Report 4 — researcher-260527-2348-dashboard-json-formats.md

- Backs: ADR-5 (Superset position_json / Grafana gridPos → confirms per-tool deployer must handle different grid systems), [parser-deployer-spec.md](parser-deployer-spec.md) §2 deploy step 5 (grid coordinate translation)
- Cited in: [architecture.md](architecture.md) §2 (Superset deployer)
- Surfaced concerns: E.1 (file diff as validation fragile — JSON key order noise confirmed)

### Report 5 — researcher-260527-visualization-type-mapping.md

- Backs: ADR-6 (portability badge — 7/25 viz types non-universal, most popular ones affected), [parser-deployer-spec.md](parser-deployer-spec.md) §2 (portability report format)
- Cited in: [spec-format-design.md](spec-format-design.md) §6 (per-tool rendering table), [architecture.md](architecture.md) §2 (VIZ_CATALOG per deployer)
- Surfaced concerns: C.2 (fallback semantics for non-universal viz types — mitigated by ADR-6)

### Report 6 — handoff-260528-1300-tool-agnostic-design-spec.md

- Historical baseline; ultrathink session **overrides** several handoff assumptions:
  - ADR-1 overrides: "blueprint as generated artifact" → skip blueprint entirely
  - ADR-2 overrides: "SQL-in-spec only" → hybrid metric_ref + inline SQL
  - ADR-3 overrides: "forward-first migration" → capture-first
- Cited in: [architecture.md](architecture.md) §2 note on deviations, `../decisions.md` ADR-1/2/3 context sections
- Surfaced concerns: B.1, B.2, D.1 (all resolved in `../decisions.md`)
