# Design Dashboard

Design a dashboard using the Analytics Design framework (Phase 0-6 only). Does NOT create Metabase blueprint or deploy.

## Context

Read this file before proceeding:
- `.skills/analytics-design/SKILL.md` — Full process guide with Phase 0-6 details

**Do NOT read** `.skills/metabase-automation/*` during this command — stay in analyst mindset.

## Steps

1. **Phase 0 — Domain Modeling**: Check/create domain file in `docs/analytics-handbook/domains/`. Read `DOMAIN_MODELING.md` for conventions.

2. **Phase 1 — Playbook Creation**: Check/create playbook in `docs/analytics-handbook/playbooks/`. Define audience, purpose, cadence.

3. **Phase 2 — Guide Creation** (if needed): Only if complex concepts need standalone explanation.

4. **Phase 3 — Design Brief**: Define audience, primary question, hero metric, comparison frame, archetype. Read `COMPOSITION_PATTERNS.md`.

5. **Phase 4 — Composition Design**: Assign card roles, narrative flow, spatial grouping, view grouping, filter design. Read `COMPOSITION_PATTERNS.md`.

6. **Phase 5 — Visualization Selection**: Choose viz types using standard vocabulary. Read `VISUALIZATION_VOCABULARY.md`. Use decision tree.

7. **Phase 6 — Enrichment Check**: Verify comparisons, data completeness, narrative support. Read `COMPARATIVE_FRAMING.md` + `VISUAL_LANGUAGE.md`.

## Output

- Domain file: `docs/analytics-handbook/domains/<domain>.md`
- Playbook: `docs/analytics-handbook/playbooks/<name>.md`
- **Design Spec**: `docs/analytics-handbook/designs/<name>.md` (the main deliverable)

To implement in Metabase, use `/create-metabase-blueprint` (which includes Phase 7-10).

## User Arguments

$ARGUMENTS
