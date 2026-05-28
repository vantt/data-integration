# Phase 07: Validation Script & Rollout Communication

> **Status:** Pending
> **Owner:** Data Team
> **Estimated:** 2-3h (script) + 1h (communication)
> **Depends:** Phase 02, 03, 04, 06 done
> **Blocks:** None (final phase)

---

## Context Links

- Drift discovered: `plans/reports/audit-260527-1202-metabase-collection-tree.md` §3, §4
- Deploy script: `.skills/metabase-automation/scripts/deploy_from_markdown.js`
- Existing validator: `.skills/metabase-automation/scripts/validate-analytics-artifacts.js`

## Overview

Sau khi cleanup xong, cần **chống tái phát**. Phase này build:
1. CI validation script chống drift spec↔live
2. Archive policy doc + hook vào deploy script
3. Rollout communication tới user

## Key Insights

- Root cause của 7 cặp duplicate: migration tạo bản mới NHƯNG **không có policy archive bản cũ**
- Root cause của drift: blueprint dùng collection path không đăng ký → deploy script tự tạo silent
- Cả 2 đều fix được bằng validation pre-commit / pre-deploy

## Architecture

```
Developer flow:                Deploy flow:                CI flow (nightly):
─────────────────              ─────────────                ──────────────────
1. Edit blueprint              1. deploy_from_markdown.js   1. validate-collections.js
2. git commit                  2. Check collection in       2. Compare registry vs
3. pre-commit hook                registry first              live Metabase
4. validate-collections.js     3. Fail if not registered    3. Report drift to Lark
5. Block commit if drift       4. Apply archive policy      4. Auto-create issue
```

## Deliverables

### Deliverable 1: `validate-collections.js` script

**Location:** `.skills/metabase-automation/scripts/validate-collections.js`

**Function:**

```javascript
// Pseudocode
async function validateCollections() {
  const registry = parseYaml('docs/analytics-handbook/collection_registry.yml');
  const blueprints = globSync('docs/analytics-handbook/blueprints/*.md');
  const liveTree = await metabaseApi.get('/api/collection/tree?tree=true');

  const errors = [];

  // Check 1: All blueprint collection paths exist in registry
  for (const file of blueprints) {
    const collection = parseCollectionFromBlueprint(file);
    if (!registryContains(registry, collection)) {
      errors.push(`BLUEPRINT_DRIFT: ${file} uses unregistered "${collection}"`);
    }
  }

  // Check 2: Registry matches live Metabase
  for (const regColl of flattenRegistry(registry)) {
    const liveColl = findInTree(liveTree, regColl.path);
    if (!liveColl) {
      errors.push(`REGISTRY_DRIFT: "${regColl.path}" in registry but not live`);
    }
  }

  // Check 3: No duplicate dashboard names within a collection
  for (const coll of flattenLive(liveTree)) {
    const dashes = await metabaseApi.get(`/api/collection/${coll.id}/items?models=dashboard`);
    const names = dashes.data.map(d => d.name);
    const dupes = findDuplicates(names);
    if (dupes.length) {
      errors.push(`DUPLICATE: "${coll.name}" has duplicate names: ${dupes}`);
    }
  }

  // Check 4: Sub-collection with only 1 dashboard (warn only)
  for (const coll of flattenLive(liveTree)) {
    if (coll.parent_id && coll.dashboards.length === 1 && !coll.exemptFromMinDashboardRule) {
      errors.push(`WARN: Sub-collection "${coll.name}" has only 1 dashboard`);
    }
  }

  // Check 5: Every dashboard has scope suffix
  for (const dash of allDashboards(liveTree)) {
    if (!/\[(All|Retail|B2B|Cross|US|Internal)\]$/.test(dash.name)) {
      errors.push(`MISSING_SUFFIX: "${dash.name}" lacks scope indicator`);
    }
  }

  // Check 6: Every dashboard has description
  for (const dash of allDashboards(liveTree)) {
    if (!dash.description || dash.description.length < 10) {
      errors.push(`MISSING_DESC: "${dash.name}" has no description`);
    }
  }

  return errors;
}
```

**Output modes:**
- `--mode=pre-commit`: exit 1 if errors, print to stderr
- `--mode=ci`: write JSON report, exit 1 if errors
- `--mode=daily`: write to Lark via notification helper
- `--mode=fix` (optional): auto-suggest fixes (rename, archive)

### Deliverable 2: Pre-commit hook integration

**Location:** `.husky/pre-commit` or `.git/hooks/pre-commit` (or `lefthook.yml` if used)

```bash
#!/bin/sh
# Only check blueprints if changed
changed=$(git diff --cached --name-only --diff-filter=ACM | grep "docs/analytics-handbook/blueprints/")
if [ -n "$changed" ]; then
  node .skills/metabase-automation/scripts/validate-collections.js --mode=pre-commit --files "$changed"
fi
```

### Deliverable 3: Archive policy hook trong deploy script

**File:** `.skills/metabase-automation/scripts/deploy_from_markdown.js`

**Modification:**

```javascript
// New behavior when deploying a renamed dashboard:
// 1. Search for existing dashboard with old name (from blueprint history)
// 2. If found AND new dashboard is being created → archive old one
// 3. Log archive action with reason

async function deployBlueprint(file) {
  const blueprint = parseBlueprint(file);
  const liveDashboard = await findDashboardByName(blueprint.name);

  // NEW: detect rename via aliases
  if (!liveDashboard && blueprint.aliases) {
    for (const oldName of blueprint.aliases) {
      const old = await findDashboardByName(oldName);
      if (old) {
        console.log(`ARCHIVE: ${oldName} → renamed to ${blueprint.name}`);
        await metabaseApi.put(`/api/dashboard/${old.id}`, { archived: true });
      }
    }
  }
  // ... rest of deploy
}
```

**Blueprint frontmatter addition:**

```yaml
---
title: CEO Weekly Pulse [All]
aliases:
  - CEO Weekly Pulse  # previous name, auto-archive on next deploy
---
```

### Deliverable 4: Dagster scheduled job

**Location:** `dagster_project/jobs/collection_validation_job.py`

Run daily 06:00 ICT, post Lark notification if drift detected.

```python
# Pseudocode
@op
def run_validation():
    result = subprocess.run([
        'node',
        '.skills/metabase-automation/scripts/validate-collections.js',
        '--mode=daily'
    ], capture_output=True)
    if result.returncode != 0:
        send_lark_notification(
            title="🚨 ChợPulse BI — Collection drift detected",
            body=result.stdout.decode()
        )

@job(schedule="0 6 * * *")
def collection_validation_job():
    run_validation()
```

### Deliverable 5: Rollout communication

**User-facing message (Lark broadcast):**

```
🎉 ChợPulse BI — Cleanup hoàn tất (2026-05-XX)

Tổng kết:
• Archive 7 dashboards trùng (CEO Weekly/Monthly, Order Profitability, Daily Sales, Yesterday's, Marketing Weekly, Customer Op) — bản cũ có scope sai
• 4 collection mới: 📍 Start Here, Finance, Analytics, + Operations subs (Logistics, Data Platform)
• 13 dashboards đã được move/rename để có suffix scope rõ ràng
• 3 sub-folder 1-board đã được flatten

Bạn cần làm gì:
1. Mở 📍 Start Here để xem map mới
2. Update bookmark nếu có
3. Mọi dashboard giờ có suffix: [All]/[Retail]/[B2B]/[Cross]/[US]
4. Nếu bookmark cũ 404 → vào Trash collection restore nếu thật sự cần

Có thắc mắc? @Data Team
```

**Internal handover note (Data Team Slack):**

```
Restructure complete. Key changes:
- collection_registry.yml is now FROZEN single source of truth
- Pre-commit hook blocks blueprint with unregistered collection
- Daily Dagster job posts to Lark if drift
- All future migrations MUST use blueprint `aliases:` for auto-archive

If you create a new dashboard:
1. Update collection_registry.yml FIRST
2. Then create blueprint with full header + aliases (if rename)
3. Run validate-collections.js locally before commit
```

## Implementation Steps

### Step 1: Build `validate-collections.js`

- Implement 6 checks
- Test on current state (should pass after Phase 02-06)
- Test on intentional drift (rename a blueprint collection path, run, expect fail)

### Step 2: Install pre-commit hook

- Add to `.husky/pre-commit` (check if husky installed; if not, use `.git/hooks/`)
- Smoke test: try committing a blueprint with bad path

### Step 3: Modify deploy script

- Add aliases support
- Test: take a blueprint, rename it + add alias, deploy → verify old archived

### Step 4: Dagster job

- Create asset/job file
- Register in workspace
- Test manual run
- Verify Lark message format

### Step 5: Document the process

- Add `docs/analytics-handbook/guides/archive_policy.md` (new file) explaining:
  - When to use aliases
  - How auto-archive works
  - How to restore from Trash
- Link from AGENTS.md "Collection Governance"

### Step 6: Send rollout communications

- Lark broadcast to user channel
- Slack DM to data team

## Todo List

- [ ] Step 1a: Write `validate-collections.js`
- [ ] Step 1b: Unit test 6 checks
- [ ] Step 2: Install pre-commit hook
- [ ] Step 3a: Modify `deploy_from_markdown.js` for aliases
- [ ] Step 3b: Test alias auto-archive
- [ ] Step 4a: Write Dagster job
- [ ] Step 4b: Schedule + test Lark notification
- [ ] Step 5: Write `archive_policy.md` guide
- [ ] Step 6a: Send Lark broadcast to users
- [ ] Step 6b: Send Slack DM to data team

## Success Criteria

- [ ] Validation script chạy clean (0 errors) trên current state
- [ ] Pre-commit hook block commit khi cố tạo blueprint với collection sai
- [ ] Deploy script với alias auto-archive bản cũ
- [ ] Dagster job chạy daily, log thành công
- [ ] Lark notification gửi đi
- [ ] Archive policy guide tồn tại + link từ AGENTS.md

## Risk Assessment

| Risk | Mitigation |
|:---|:---|
| Pre-commit hook fail false positive → dev frustration | `--mode=warn` flag để cho phép bypass, log warning |
| Validation script chậm (gọi nhiều API) | Cache live tree per run, parallel requests |
| Dagster job spam Lark khi có drift dài hạn | Add debounce: chỉ alert 1 lần/24h cho mỗi error type |
| Auto-archive nhầm dashboard có user dùng heavy | aliases require explicit declaration in frontmatter; default off |

## Security Considerations

- Validation script dùng read-only API call → an toàn
- Auto-archive (deploy script) dùng PUT → require explicit alias, không tự suy diễn
- Dagster job dùng same API key → already secured

## Next Steps (post-plan)

- Monitor Lark drift alerts 1 tuần đầu → fine-tune
- Phase 05 backlog: build 5 Finance dashboards
- Quarterly review: check if any sub-collection cần promote thành top-level (vd Logistics nếu team grow)
