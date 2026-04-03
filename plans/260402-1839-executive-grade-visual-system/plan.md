# P2: Executive-Grade Visual System

## Status: Planned (not started)

## Context

The 2-skill pipeline now has a closed deploy/capture loop (P0), clean skill boundaries (P1), and artifact validation (P1). The remaining gap: dashboards are **clean but not premium**. Visual output is tidy but not memorable or brand-consistent.

**Assessment source**: `plans/analytics-design-skill/research-260402-v3-2skill_assessment_report.md` — Section "P2. Raise the aesthetic ceiling"

## Goal

Make dashboard outputs look intentionally designed, not merely tidy. Establish repeatable visual quality standards.

## Phases

### Phase 1: Branded Visual Extension (2-3 days)
- [ ] Define palette variants: executive, operations, marketing contexts
- [ ] Number format conventions (VND currency, compact notation, decimal rules)
- [ ] Title/copy conventions in Vietnamese
- [ ] Extend `.skills/analytics-design/VISUAL_LANGUAGE.md` with branded tokens

### Phase 2: Screenshot Review Rubric (1 day)
- [ ] Define scoring dimensions: hierarchy clarity, glanceability, action clarity, annotation quality, clutter score
- [ ] Create rubric template (1-5 scale per dimension)
- [ ] Add to validator or as standalone review checklist

### Phase 3: Canonical Exemplars (3-5 days)
- [ ] Create true Executive Pulse exemplar (single view, ≤10 cards, no tables)
- [ ] Create true Operational Cockpit exemplar (multi-tab, filters, detail tables)
- [ ] Create true Exploratory Tool exemplar (many filters, pivot/scatter)
- [ ] Each exemplar: design spec + blueprint + deployed + screenshot

### Phase 4: Anti-Pattern Library (1 day)
- [ ] Document common anti-patterns with examples:
  - Wall of scalars (no visual hierarchy)
  - Tab sprawl (>5 tabs)
  - Generic section headings ("Overview", "Details")
  - Tables inside pulse dashboards
  - Pie charts for >5 categories

## Success Criteria

- Reviewers can reject "technically correct but visually mediocre" outputs using the rubric
- Design quality becomes teachable and repeatable via exemplars
- Branded palette is used consistently across new dashboards

## Estimated Effort: 1-2 weeks

## Dependencies
- None (P0/P1 already complete)
