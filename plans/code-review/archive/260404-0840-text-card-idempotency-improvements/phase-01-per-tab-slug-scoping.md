# Phase 1: Per-tab Slug Scoping

**Status:** Planned  
**Priority:** Low  
**Estimated Effort:** 30 min

## Context Links

- Code: `.skills/metabase-automation/scripts/deploy_from_markdown.js:324-332`
- Helper: `.skills/metabase-automation/lib/text-card-helpers.js`
- Docs: `.skills/metabase-automation/STRATEGY.md:87`

## Problem

Current slug disambiguation uses a dashboard-wide counter:

```js
const slugCounts = {};
for (const tc of (dashboard.textCards || [])) {
  let slug = slugify(tc.name);
  slugCounts[slug] = (slugCounts[slug] || 0) + 1;
  if (slugCounts[slug] > 1) slug = `${slug}-${slugCounts[slug]}`;
  // ...
}
```

If dashboard has tabs `[Overview, Details]` each with a text card named "Summary":
- Current: `summary`, `summary-2` (global counter)
- Problem: Removing Overview's "Summary" shifts Details' slug from `summary-2` to `summary`
- Result: Card recreation instead of update

## Solution

Scope slugCounts per-tab. Tab name becomes part of slug namespace.

```js
// Before: const slugCounts = {};
const slugCounts = {}; // key = `${tab}:${slug}` or just `slug` if no tab

for (const tc of (dashboard.textCards || [])) {
  let slug = slugify(tc.name);
  const scopeKey = tc.tab ? `${tc.tab}:${slug}` : slug;
  slugCounts[scopeKey] = (slugCounts[scopeKey] || 0) + 1;
  if (slugCounts[scopeKey] > 1) slug = `${slug}-${slugCounts[scopeKey]}`;
  // ...
}
```

Now each tab has independent slug namespace:
- Overview/Summary → `summary` (scope: `Overview:summary`)
- Details/Summary → `summary` (scope: `Details:summary`)

## Related Code Files

| File | Action |
|------|--------|
| `deploy_from_markdown.js` | Modify slug scoping logic |
| `STRATEGY.md` | Update "Known limitations" note |

## Implementation Steps

1. Open `deploy_from_markdown.js`
2. Locate text card processing loop (~line 324)
3. Change `slugCounts` key to include tab name
4. Test with blueprint having duplicate text card names across tabs
5. Update `STRATEGY.md:87` to note this improvement

## Todo List

- [ ] Modify slug scoping in `deploy_from_markdown.js`
- [ ] Test: same text card name in different tabs
- [ ] Test: same text card name in same tab (counter still works)
- [ ] Test: text card with no tab (fallback to global scope)
- [ ] Update STRATEGY.md documentation

## Test Cases

```markdown
### Tab: Overview
#### Text: Summary
...

### Tab: Details  
#### Text: Summary
...
```

Expected slugs: both get `summary` (unique per tab context).

## Success Criteria

- [ ] Duplicate names across tabs get same base slug (unique per-tab)
- [ ] Duplicate names within same tab still get counter suffix
- [ ] Existing blueprints deploy without recreation
