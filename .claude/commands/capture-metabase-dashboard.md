# Capture Metabase Dashboard

Capture a live Metabase dashboard into a blueprint, or sync positions/sizes from live layout back to an existing blueprint.

Read `.skills/metabase-automation/SKILL.md` for full context before running.

## Steps

### 1 — Resolve dashboard & blueprint

First argument (`$ARGUMENTS`) may be:
- A full dashboard URL: `http://bi.lan.fwg.vn/dashboard/42-slug?tab=123-name`
- A numeric ID: `42`

Pass it directly to the script — URL parsing (dashboard ID + tab ID) is automatic.

Find the matching blueprint file:
```bash
grep -ril "<dashboard name keyword>" docs/analytics-handbook/blueprints/
```

### 2 — Choose mode and run

**Fresh capture** (no existing blueprint):
```bash
METABASE_URL="http://127.0.0.1:3001" METABASE_API_KEY="$(grep METABASE_API_KEY .env.docker | cut -d= -f2- | tr -d '\"')" \
  node .skills/metabase-automation/scripts/capture_dashboard.js "$ARGUMENTS" docs/analytics-handbook/blueprints/<name>.md
```

**Positions/sizes only** (user rearranged layout, keep SQL/viz/prose untouched):
```bash
METABASE_URL="http://127.0.0.1:3001" METABASE_API_KEY="$(grep METABASE_API_KEY .env.docker | cut -d= -f2- | tr -d '\"')" \
  node .skills/metabase-automation/scripts/capture_dashboard.js "$ARGUMENTS" docs/analytics-handbook/blueprints/<name>.md --positions-only
```
- If URL contains `?tab=<id>` → only that tab's positions are updated; other tabs unchanged.
- Add `--tab <id>` to override or specify a tab when using a plain numeric ID.

**Full merge** (update SQL + viz + positions, keep prose/Semantic Contract/frontmatter):
```bash
# Same as fresh capture — merge mode activates automatically when output file exists.
# ⚠️  Overwrites SQL from live Metabase. Only use after all live cards match the blueprint.
```

### 3 — Post-capture

- Review diff: `git diff docs/analytics-handbook/blueprints/<name>.md`
- For fresh captures: add Semantic Contract, domain references, descriptions
- Commit when satisfied

## User Arguments

$ARGUMENTS
