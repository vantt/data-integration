# Code Review: P0 Text Card Idempotency

**Reviewer:** code-reviewer  
**Date:** 2026-04-02  
**Scope:** 4 code files + 8 migrated blueprints  
**Focus:** Correctness, edge cases, backward compat, code quality

---

## Overall Assessment

Solid implementation. The `text-id` marker approach is a clean, minimal solution for stable text card identity. The helper module is well-factored, and the three consumers (deploy, capture, syncCards) all use it consistently. No critical bugs found. A few medium-priority edge cases and one notable backward-compat behavior worth documenting.

---

## Issues

### [MAJOR] First redeploy of legacy dashboards duplicates all text cards

**File:** `Dashboard.js` syncCards, line 107  
**Problem:** When a dashboard has existing text cards (created before this change, no `text-id` marker), `extractTextId()` returns `null` for both the config and the existing dashcard. The code path:
```js
existing = configTextId ? currentCards.find(...) : null;
```
When `configTextId` is falsy (should never happen post-deploy since deploy always injects markers), `existing` is forced to `null`. But the **real concern** is the inverse: existing Metabase text cards that were created *before* this feature have no `text-id` marker in their content. On first redeploy, the new configs will have markers (injected by deploy_from_markdown), but old dashcards won't match because their content lacks the marker. Result: **old text cards remain orphaned, new ones get created = duplication**.

**Impact:** Every text card gets duplicated on first redeploy of a legacy dashboard. Manual cleanup needed.  
**Severity:** Major (one-time migration pain, not recurring)  
**Fix options:**
1. Document this as expected first-deploy behavior + provide a cleanup script
2. Add a fallback match: if no text-id match found, try matching text cards by tab + position (row/col) as a heuristic
3. Accept duplication on first deploy since subsequent deploys will be idempotent (pragmatic choice if documented)

### [MINOR] Slug counter produces inconsistent IDs when blueprint order changes

**File:** `deploy_from_markdown.js`, lines 329-331  
**Problem:** Duplicate slug disambiguation uses a sequential counter:
```js
slugCounts[slug] = (slugCounts[slug] || 0) + 1;
if (slugCounts[slug] > 1) slug = `${slug}-${slugCounts[slug]}`;
```
If blueprint has text cards ["Foo", "Foo", "Foo"], slugs become: `foo`, `foo-2`, `foo-3`. If the second "Foo" is removed, the third becomes `foo-2` -- different slug than before. This breaks idempotency for that card.

**Impact:** Low in practice (duplicate text card names within one tab is unusual). But if it happens, reordering/removing duplicates causes recreation.  
**Severity:** Minor  
**Fix:** Use content hash or position as part of slug instead of counter. Or document as known limitation.

### [MINOR] `injectTextId` silently replaces an existing different marker

**File:** `text-card-helpers.js`, line 43-46  
**Problem:** If content already has a `text-id` marker with a *different* slug (e.g. from a name rename), `injectTextId` strips the old one and injects the new one. This means a renamed text card loses its stable identity and gets recreated rather than updated.

**Impact:** Renamed text card = orphaned old + new created. Acceptable behavior but worth documenting.  
**Severity:** Minor (expected for rename semantics)

### [MINOR] `parseExistingBlueprint` doesn't preserve text card content in merge mode

**File:** `capture_dashboard.js`, line 257  
**Problem:** `generateMerged()` passes `existing.questions` to `renderTabGroups()` for prose preservation, but **never passes `existing.textCards`**. The `renderTabGroups()` function doesn't accept or use existing text card data. Text cards are always re-captured from Metabase, so existing blueprint prose for text cards is effectively discarded on merge.

**Impact:** If someone manually edited text card content in the blueprint, a merge-mode capture would overwrite those edits. Low risk since text cards are typically section headings with no manual prose.  
**Severity:** Minor

### [NIT] `TEXT_ID_REGEX` doesn't anchor to end of line

**File:** `text-card-helpers.js`, line 10  
**Problem:** `/<!-- text-id:([a-z0-9-]+) -->/` matches anywhere in the content. If someone writes `<!-- text-id:foo --> some text <!-- text-id:bar -->`, only the first match is extracted, and `replace()` only strips the first occurrence.

**Impact:** Pathological edge case, not realistic in practice.  
**Severity:** Nit

### [NIT] Markdown parser strips heading lines from text card content

**File:** `markdown_parser.js`, line 243  
**Problem:** The parser collects text card content with `!trimmed.startsWith('#')`. This means if a text card's markdown content starts with `# Heading`, that line is silently dropped. The deploy script compensates with `tc.text || '# ${tc.name}'` (line 328), but if the heading text differs from the `#### Text: Name` header, the heading content is lost.

**Impact:** Text cards whose heading text differs from their name lose the heading line. Low risk since convention is they match.  
**Severity:** Nit

---

## Backward Compatibility

| Scenario | Behavior | OK? |
|----------|----------|-----|
| Existing dashboard, no text cards | No change | Yes |
| Existing dashboard, text cards without markers | First redeploy duplicates text cards (see MAJOR above) | Needs doc |
| Blueprint without `#### Text:` blocks | No text cards processed, same as before | Yes |
| Blueprint with old `<!-- Text annotations -->` comments | Comments are plain HTML, ignored by parser | Yes |
| Capture of dashboard with marker-injected text cards | Markers stripped in output, re-injected on deploy | Yes |

---

## Blueprint Migration Quality

Spot-checked `ceo_weekly_pulse.md` and `sales_daily_operation.md`:
- Old `<!-- Text annotations to add manually after deploy -->` blocks fully removed (grep confirms 0 remaining)
- New `#### Text:` blocks follow correct format: header, blank line, markdown content, blank line, metabase-pos JSON block
- Position data preserved correctly
- Vietnamese text (both with and without diacritics) handled properly
- No orphaned or misplaced sections

**Verdict:** Migration is clean and complete across all 8 files.

---

## Positive Observations

1. **Clean separation of concerns** -- text-card-helpers.js is a focused, well-documented module with no side effects
2. **Defensive coding** -- `extractTextId` handles null/undefined input, `injectTextId` is idempotent for same slug
3. **Tab-aware matching** in syncCards prevents cross-tab false matches
4. **Capture strips markers** -- blueprint files stay clean, markers only exist at runtime in Metabase
5. **slugify handles Vietnamese** diacritics via NFD normalization

---

## Recommended Actions

1. **[Should Do]** Document the first-redeploy duplication behavior for legacy dashboards. Add a note in STRATEGY.md or a migration guide.
2. **[Nice to Have]** Consider a position-based fallback match for text cards without markers (mitigates first-deploy duplication).
3. **[Nice to Have]** Pass `existing.textCards` into merge-mode rendering so text card prose survives capture merges.

---

## Unresolved Questions

1. Is the first-deploy duplication of legacy text cards acceptable, or should a migration path be provided?
2. Should `slugCounts` scope be per-tab rather than per-dashboard to reduce collision chance?
