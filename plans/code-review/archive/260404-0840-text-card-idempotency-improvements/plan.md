# Text Card Idempotency Improvements

**Created:** 2026-04-04  
**Status:** Planned  
**Priority:** Low (NIT-level improvements)  
**Source:** `plans/reports/code-reviewer-260402-1809-p0-text-card-idempotency.md`

## Overview

Two remaining improvements from the P0 Text Card Idempotency code review. All major/minor issues were already fixed. These are NIT-level enhancements for edge case robustness.

## Phases

| Phase | Name | Status | Priority |
|-------|------|--------|----------|
| 1 | [Per-tab Slug Scoping](./phase-01-per-tab-slug-scoping.md) | Planned | Low |
| 2 | [TEXT_ID_REGEX Anchoring](./phase-02-text-id-regex-anchoring.md) | Planned | Very Low |

## Dependencies

- None (standalone improvements)

## Risk Assessment

- **Low risk** - Both changes are additive/defensive
- No breaking changes to existing blueprints
- Per-tab scoping is backward-compatible (existing slugs still work)

## Success Criteria

- [ ] Phase 1: Duplicate text card names in different tabs get unique slugs
- [ ] Phase 2: Only first text-id marker is matched, extras ignored cleanly
- [ ] All existing blueprints continue to deploy correctly
