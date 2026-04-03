---
name: analytics-design
description: Design analytics dashboards with tool-agnostic framework (Phase 0-6). Use when user asks to design dashboard, define metrics, create analytics domain/playbook/design-spec. Analyst brain — defines WHAT to measure, WHY, and HOW to communicate data visually.
---

# Analytics Design Skill

Tool-agnostic analyst brain for dashboard design. Owns Phase 0-6 of the analytics workflow.

**Full instructions**: Read `.skills/analytics-design/SKILL.md` before proceeding.

## When to Activate

- User asks to "design a dashboard", "define metrics", "create analytics"
- User mentions domains, playbooks, design specs
- Any analytics design work that is NOT Metabase-specific implementation

## Key Constraint

Do NOT read `.skills/metabase-automation/*` during Phase 0-6. Stay in analyst mindset.

## Quick Phase Reference

| Phase | What | Key Doc |
|-------|------|---------|
| 0 | Domain Modeling | `.skills/analytics-design/DOMAIN_MODELING.md` |
| 1 | Playbook Creation | `.skills/analytics-design/templates/playbook_template.md` |
| 2 | Guide (if needed) | `.skills/analytics-design/templates/guide_template.md` |
| 3-4 | Composition Design | `.skills/analytics-design/COMPOSITION_PATTERNS.md` |
| 5 | Viz Selection | `.skills/analytics-design/VISUALIZATION_VOCABULARY.md` |
| 6 | Enrichment Check | `.skills/analytics-design/COMPARATIVE_FRAMING.md` + `VISUAL_LANGUAGE.md` |

## Output Artifacts

- Domain: `docs/analytics-handbook/domains/<domain>.md`
- Playbook: `docs/analytics-handbook/playbooks/<name>.md`
- Design Spec: `docs/analytics-handbook/designs/<name>.md`

To implement in Metabase after design, use the `metabase-automation` skill (Phase 7-10).
