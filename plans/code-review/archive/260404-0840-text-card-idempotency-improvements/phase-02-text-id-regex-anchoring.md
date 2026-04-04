# Phase 2: TEXT_ID_REGEX Anchoring

**Status:** Planned  
**Priority:** Very Low (pathological edge case)  
**Estimated Effort:** 15 min

## Context Links

- Code: `.skills/metabase-automation/lib/text-card-helpers.js:10`
- Report: `plans/reports/code-reviewer-260402-1809-p0-text-card-idempotency.md`

## Problem

Current regex:
```js
const TEXT_ID_REGEX = /<!-- text-id:([a-z0-9-]+) -->/;
```

Matches anywhere in content. If content has multiple markers (pathological):
```markdown
Some text <!-- text-id:foo --> more text <!-- text-id:bar -->
```

- `extractTextId()` returns `foo` (first match)
- `injectTextId()` with `replace()` only strips first occurrence
- Result: `bar` marker remains orphaned

## Solution

Two options:

### Option A: Match last marker (recommended)
Use global flag + take last match. Markers are appended at end, so last is canonical.

```js
const TEXT_ID_REGEX = /<!-- text-id:([a-z0-9-]+) -->/g;

function extractTextId(markdownText) {
  if (!markdownText) return null;
  const matches = [...markdownText.matchAll(TEXT_ID_REGEX)];
  return matches.length > 0 ? matches[matches.length - 1][1] : null;
}

function injectTextId(markdownText, slug) {
  if (!markdownText) return `<!-- text-id:${slug} -->`;
  // Strip ALL markers, then append correct one
  const cleaned = markdownText.replace(TEXT_ID_REGEX, '').trimEnd();
  return `${cleaned}\n<!-- text-id:${slug} -->`;
}
```

### Option B: Anchor to end of content
```js
const TEXT_ID_REGEX = /<!-- text-id:([a-z0-9-]+) -->\s*$/;
```

Problem: Fails if marker not at exact end (whitespace variations).

**Recommendation:** Option A (global + last match)

## Related Code Files

| File | Action |
|------|--------|
| `text-card-helpers.js` | Modify regex handling |

## Implementation Steps

1. Open `text-card-helpers.js`
2. Change `TEXT_ID_REGEX` to global: `/<!-- text-id:([a-z0-9-]+) -->/g`
3. Update `extractTextId()` to use `matchAll()` and return last match
4. Update `injectTextId()` to strip ALL markers with global replace
5. Test with content having multiple markers

## Todo List

- [ ] Add global flag to TEXT_ID_REGEX
- [ ] Update extractTextId() for last-match behavior
- [ ] Update injectTextId() to strip all markers
- [ ] Test: single marker (normal case)
- [ ] Test: multiple markers (edge case)
- [ ] Test: no marker (normal case)

## Test Cases

```js
// Normal
extractTextId("# Title\n<!-- text-id:foo -->") // → "foo"

// Pathological (multiple markers)
extractTextId("<!-- text-id:old --> text <!-- text-id:new -->") // → "new" (last)

// Inject strips all
injectTextId("<!-- text-id:a --> text <!-- text-id:b -->", "c")
// → "text\n<!-- text-id:c -->"
```

## Success Criteria

- [ ] Last marker is always the canonical one
- [ ] All markers stripped on inject (no orphans)
- [ ] Normal single-marker case unchanged
